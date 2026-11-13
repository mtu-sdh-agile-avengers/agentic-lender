import asyncio

import httpx

from src.ai_engine.client import AIEngineClient

KEY = "shared-secret"


def fake_ai_engine(request: httpx.Request) -> httpx.Response:
    """Mimics AL-AI Engine: /internal/ping needs the right X-Internal-Key."""
    if request.url.path == "/health":
        return httpx.Response(200, json={"status": "ok"})
    if request.url.path == "/internal/ping":
        if request.headers.get("X-Internal-Key") != KEY:
            return httpx.Response(401, json={"detail": "invalid or missing X-Internal-Key"})
        return httpx.Response(200, json={"status": "ok", "internal_auth": "enforced"})
    if request.url.path == "/ready":
        return httpx.Response(200, json={"ready": True, "model_loaded": True, "model_version": "v1"})
    return httpx.Response(404)


def status(key: str):
    client = AIEngineClient("http://ai:8001", key, transport=httpx.MockTransport(fake_ai_engine))
    return asyncio.run(client.status())


def test_matching_key_is_accepted():
    result = status(KEY)
    assert result.reachable and result.internal_key_accepted
    assert result.model_loaded and result.model_version == "v1"
    assert result.error is None


def test_wrong_key_is_reported():
    result = status("not-the-key")
    assert result.reachable
    assert not result.internal_key_accepted
    assert "INTERNAL_API_KEY" in result.error


def test_unreachable_engine_does_not_raise():
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = AIEngineClient("http://ai:8001", KEY, transport=httpx.MockTransport(refuse))
    result = asyncio.run(client.status())
    assert not result.reachable
    assert result.error.startswith("ConnectError")
