"""HTTP client for AL-AI Engine (internal service).

AL-Core is the only caller of the AI engine. Every request carries the shared secret in the
`X-Internal-Key` header; the engine rejects anything without it (401).

This sprint only the wiring is exercised (`/health`, `/ready`, `/internal/ping`); valuation and
deliberation calls are added together with the loan application endpoints.
"""

from typing import Any

import httpx
from pydantic import BaseModel

_INTERNAL_KEY_HEADER = "X-Internal-Key"


class AIEngineStatus(BaseModel):
    """What AL-Core can see of the AI engine right now."""

    url: str
    reachable: bool
    internal_key_accepted: bool = False
    ready: bool = False
    model_loaded: bool = False
    model_version: str | None = None
    error: str | None = None


class AIEngineClient:
    def __init__(
        self,
        base_url: str,
        internal_key: str,
        timeout: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,  # tests pass httpx.MockTransport
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {_INTERNAL_KEY_HEADER: internal_key} if internal_key else {}
        self._timeout = timeout
        self._transport = transport

    async def _get(self, client: httpx.AsyncClient, path: str) -> tuple[int, dict[str, Any]]:
        response = await client.get(path)
        try:
            body = response.json()
        except ValueError:
            body = {}
        return response.status_code, body

    async def status(self) -> AIEngineStatus:
        """Liveness, shared-key check and readiness in one go. Never raises."""
        result = AIEngineStatus(url=self._base_url, reachable=False)

        async with httpx.AsyncClient(
            base_url=self._base_url, headers=self._headers, timeout=self._timeout, transport=self._transport
        ) as client:
            try:
                code, _ = await self._get(client, "/health")
                result.reachable = code == 200

                code, _ = await self._get(client, "/internal/ping")
                result.internal_key_accepted = code == 200
                if code == 401:
                    result.error = "AI engine rejected X-Internal-Key (INTERNAL_API_KEY differs)"

                # /ready answers 503 with the same body when the model is missing
                _, ready = await self._get(client, "/ready")
                result.ready = bool(ready.get("ready"))
                result.model_loaded = bool(ready.get("model_loaded"))
                result.model_version = ready.get("model_version")
            except httpx.HTTPError as exc:
                result.error = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__

        return result
