"""LLM providers for the AI Engine (backlog ALG4-85 / AGT-02).

Two cloud providers plus one local model, behind one interface, so the agents
never care which vendor answered. Grown out of the ALG4-62 smoke-test script;
the retry and fallback behaviour here comes from real failures we hit:

  - model identifiers change between releases (404 from Groq, Gemini)
  - free tiers return 503 under load, sometimes instantly
  - a local model on CPU answers in 8-12 seconds and is occasionally absent
"""

import logging
import time
from dataclasses import dataclass
from typing import Callable

import requests

from app.config import Settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 60
RETRYABLE_STATUS = {429, 500, 502, 503, 529}
MAX_ATTEMPTS = 3

# Tried in order when no explicit GEMINI_MODEL is configured
GEMINI_FALLBACKS = ["gemini-3.5-flash", "gemini-3.5-flash-lite",
                    "gemini-2.5-flash", "gemini-2.5-flash-lite"]


class ProviderError(RuntimeError):
    """Raised when a provider cannot answer at all."""


@dataclass(frozen=True)
class Provider:
    name: str
    model: str
    call: Callable[[str], str]
    is_local: bool = False


def _post_with_retry(url: str, **kwargs) -> requests.Response:
    """POST, waiting longer after each retryable failure."""
    response = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = requests.post(url, **kwargs)
        if response.status_code not in RETRYABLE_STATUS:
            response.raise_for_status()
            return response
        if attempt < MAX_ATTEMPTS:
            wait = 2 ** attempt
            logger.info("retrying after HTTP %s in %ss", response.status_code, wait)
            time.sleep(wait)
    response.raise_for_status()
    return response


def make_groq(settings: Settings) -> Provider | None:
    if not settings.groq_api_key:
        return None

    def call(prompt: str) -> str:
        response = _post_with_retry(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={"model": settings.groq_model,
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.2},
            timeout=TIMEOUT_SECONDS)
        return response.json()["choices"][0]["message"]["content"]

    return Provider(name="groq", model=settings.groq_model, call=call)


def make_gemini(settings: Settings) -> Provider | None:
    if not settings.gemini_api_key:
        return None

    models = [settings.gemini_model] if settings.gemini_model else GEMINI_FALLBACKS

    def call(prompt: str) -> str:
        errors = []
        for model in models:
            try:
                response = _post_with_retry(
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model}:generateContent",
                    headers={"x-goog-api-key": settings.gemini_api_key},
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"temperature": 0.2}},
                    timeout=TIMEOUT_SECONDS)
                parts = response.json()["candidates"][0]["content"]["parts"]
                return parts[0]["text"]
            except requests.RequestException as exc:
                status = getattr(exc.response, "status_code", type(exc).__name__)
                errors.append(f"{model}: {status}")
        raise ProviderError("all Gemini models failed -> " + "; ".join(errors))

    label = settings.gemini_model or "auto"
    return Provider(name="gemini", model=label, call=call)


def make_ollama(settings: Settings) -> Provider | None:
    """Local model. No key, but the daemon has to be running."""

    def call(prompt: str) -> str:
        response = _post_with_retry(
            f"{settings.ollama_url}/api/chat",
            json={"model": settings.ollama_model,
                  "messages": [{"role": "user", "content": prompt}],
                  "stream": False,
                  "options": {"temperature": 0.2}},
            timeout=TIMEOUT_SECONDS)
        return response.json()["message"]["content"]

    return Provider(name="ollama", model=settings.ollama_model, call=call,
                    is_local=True)


def available_providers(settings: Settings) -> list[Provider]:
    """Everything configured right now, cloud first then local.

    Ollama is included without probing: a health check here would add a round
    trip to every deliberation, and a failure is handled by the vote anyway.
    """
    providers = [make_groq(settings), make_gemini(settings), make_ollama(settings)]
    return [provider for provider in providers if provider is not None]
