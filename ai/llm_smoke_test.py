"""
AL: Agentic Lender - LLM access check (backlog task AGT-02).

Sends the same prompt to three providers at once and prints what each
returned, how long it took, and whether it failed. No agent framework here on
purpose: this only proves our keys work and shows how the models differ.

Setup:
    pip install requests
    ollama pull llama3.2          # for the local model

Keys (PowerShell, current window only):
    $env:GROQ_API_KEY   = "gsk_..."
    $env:GEMINI_API_KEY = "AIza..."

Usage:
    python llm_smoke_test.py --check
    python llm_smoke_test.py
    python llm_smoke_test.py --prompt "Explain LTV in one sentence"
    python llm_smoke_test.py --json
"""

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests

# Optional: load keys from a .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TIMEOUT = 60

# Model names change often. Override with env vars instead of editing code.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
# Gemini free tier gets busy, so we try several models in order until one works
GEMINI_MODELS = [m.strip() for m in os.getenv(
    "GEMINI_MODELS",
    "gemini-3.5-flash,gemini-3.5-flash-lite,gemini-2.5-flash,gemini-2.5-flash-lite"
).split(",") if m.strip()]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

DEFAULT_PROMPT = (
    "A borrower earns 65000 EUR gross per year, has 4000 EUR of existing debt "
    "repayments per year, and wants a 300000 EUR mortgage on a 350000 EUR "
    "property. In two sentences: is this affordable under Irish lending rules?"
)

JSON_PROMPT = (
    "Return ONLY valid JSON, no markdown, no explanation, with exactly these "
    'keys: {"decision": "Approve" | "Decline", "ltv_percent": number, '
    '"reason": string}. Loan 300000 EUR on a property worth 350000 EUR.'
)


# Status codes worth retrying: rate limited, overloaded, server hiccup
RETRYABLE = {429, 500, 502, 503, 529}
ATTEMPTS = 3


def post_with_retry(url: str, **kwargs) -> requests.Response:
    """POST, retrying overloaded providers with a growing wait between tries."""
    last = None
    for attempt in range(1, ATTEMPTS + 1):
        response = requests.post(url, **kwargs)
        if response.status_code not in RETRYABLE:
            response.raise_for_status()
            return response
        last = response
        if attempt < ATTEMPTS:
            wait = 2 ** attempt           # 2s, then 4s
            print(f"    retry {attempt}/{ATTEMPTS - 1} after HTTP "
                  f"{response.status_code}, waiting {wait}s")
            time.sleep(wait)
    last.raise_for_status()
    return last


# ---------------------------------------------------------------------------
# One function per provider. Each returns the answer text or raises.
# ---------------------------------------------------------------------------
def call_groq(prompt: str) -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")

    response = post_with_retry(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_gemini(prompt: str) -> str:
    """Tries each model in GEMINI_MODELS until one is available."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    models = [GEMINI_MODEL] if GEMINI_MODEL else GEMINI_MODELS
    errors = []
    for model in models:
        try:
            response = post_with_retry(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent",
                headers={"x-goog-api-key": key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2},
                },
                timeout=int(os.getenv("GEMINI_TIMEOUT", "20")),
            )
            if model != models[0]:
                print(f"    fell back to {model}")
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except requests.RequestException as exc:
            status = getattr(exc.response, "status_code", type(exc).__name__)
            errors.append(f"{model}: {status}")
            continue
    raise RuntimeError("all Gemini models failed -> " + "; ".join(errors))


def call_ollama(prompt: str) -> str:
    """Local model. No key needed, but `ollama serve` must be running."""
    response = post_with_retry(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def call_mistral(prompt: str) -> str:
    """Optional third cloud provider, used only if MISTRAL_API_KEY is set."""
    key = os.getenv("MISTRAL_API_KEY")
    if not key:
        raise RuntimeError("MISTRAL_API_KEY is not set")

    response = post_with_retry(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": MISTRAL_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


PROVIDERS = {
    f"groq ({GROQ_MODEL})": call_groq,
    f"gemini ({GEMINI_MODEL or 'auto'})": call_gemini,
    f"ollama ({OLLAMA_MODEL}, local)": call_ollama,
}
# Mistral joins in only if a key is present
if os.getenv("MISTRAL_API_KEY"):
    PROVIDERS[f"mistral ({MISTRAL_MODEL})"] = call_mistral


# ---------------------------------------------------------------------------
# Run them in parallel and report
# ---------------------------------------------------------------------------
def ask(name: str, func, prompt: str) -> dict:
    started = time.perf_counter()
    try:
        answer = func(prompt)
        return {"name": name, "ok": True, "answer": answer.strip(),
                "seconds": time.perf_counter() - started}
    except requests.HTTPError as exc:
        # The response body usually says exactly what is wrong
        detail = exc.response.text[:300] if exc.response is not None else str(exc)
        return {"name": name, "ok": False, "error": f"HTTP {exc.response.status_code}: {detail}",
                "seconds": time.perf_counter() - started}
    except Exception as exc:
        return {"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}",
                "seconds": time.perf_counter() - started}


def ask_all(prompt: str) -> list:
    """All three at once, so total time is the slowest one, not the sum."""
    with ThreadPoolExecutor(max_workers=len(PROVIDERS)) as pool:
        futures = [pool.submit(ask, name, func, prompt)
                   for name, func in PROVIDERS.items()]
        return [f.result() for f in futures]


def check_setup() -> None:
    print("Environment check")
    for var in ["GROQ_API_KEY", "GEMINI_API_KEY", "MISTRAL_API_KEY"]:
        value = os.getenv(var)
        status = f"set ({value[:6]}...)" if value else "not set"
        print(f"  {var:<16} {status}")
    try:
        tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()
        models = [m["name"] for m in tags.get("models", [])]
        print(f"  ollama           running, models: {', '.join(models) or 'none pulled'}")
    except Exception as exc:
        print(f"  ollama           not reachable at {OLLAMA_URL} ({type(exc).__name__})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default=None, help="your own prompt")
    parser.add_argument("--json", action="store_true",
                        help="ask for strict JSON and check it parses")
    parser.add_argument("--check", action="store_true",
                        help="only verify keys and Ollama, send nothing")
    args = parser.parse_args()

    check_setup()
    if args.check:
        return

    prompt = args.prompt or (JSON_PROMPT if args.json else DEFAULT_PROMPT)
    print(f"\nPrompt:\n  {prompt}\n")

    started = time.perf_counter()
    results = ask_all(prompt)
    total = time.perf_counter() - started

    for result in results:
        print("=" * 70)
        print(f"{result['name']}   ({result['seconds']:.1f}s)")
        print("=" * 70)
        if not result["ok"]:
            print(f"  FAILED: {result['error']}\n")
            continue

        print(result["answer"][:1200])
        if args.json:
            # Models often wrap JSON in ```json fences, so strip them first
            cleaned = result["answer"].strip().removeprefix("```json") \
                .removeprefix("```").removesuffix("```").strip()
            try:
                parsed = json.loads(cleaned)
                print(f"\n  -> valid JSON, keys: {list(parsed)}")
            except json.JSONDecodeError as exc:
                print(f"\n  -> NOT valid JSON: {exc}")
        print()

    working = sum(r["ok"] for r in results)
    print(f"Summary: {working}/{len(results)} providers responded, "
          f"{total:.1f}s wall clock (slowest provider decides)")


if __name__ == "__main__":
    main()