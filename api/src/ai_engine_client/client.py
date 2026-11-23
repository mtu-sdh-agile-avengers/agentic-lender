from enum import Enum
from typing import Any, Literal

import httpx
from fastapi import status
from pydantic import BaseModel

from src.ai_engine_client.exceptions import (
    AIEngineAuthError,
    AIEngineNotFoundError,
    AIEngineRejectedError,
    AIEngineUnavailableError,
)

_INTERNAL_KEY_HEADER = "X-Internal-Key"


class AIEngineTimeout(float, Enum):
    """Seconds to wait for AL-AI Engine; applies to each phase of a request (connect, write, read)."""

    HEALTH = 2.0  # health checks must answer fast, three of them run one after another
    DEFAULT = 5.0  # default value for all requests without explicit timeout
    DELIBERATION = 7.5  # the engine answers 202 at once; the committee itself runs in the background


class AIEngineStatus(BaseModel):
    """What AL-Core can see of AL-AI Engine right now (`GET /health/dependencies`).

    Attributes:
        url: base URL of AL-AI Engine the client talks to.
        reachable: `True` if `GET /health` answered 200.
        internal_key_accepted: `True` if `GET /internal/ping` accepted `X-Internal-Key`.
        ready: `True` if `GET /ready` reports the engine as ready.
        model_loaded: `True` if the valuation model is loaded.
        model_version: version of the loaded valuation model; `None` if no model is loaded.
        error: what went wrong (network error or rejected key); `None` if every check passed.
    """

    url: str
    reachable: bool
    internal_key_accepted: bool = False
    ready: bool = False
    model_loaded: bool = False
    model_version: str | None = None
    error: str | None = None


class DeliberationJob(BaseModel):
    """One AI committee run as AL-AI Engine reports it.

    Mirrors `DeliberationAccepted` (answer of `POST /v1/deliberations`) and `DeliberationStatus`
    (answer of `GET /v1/deliberations/{job_id}`) of `ai/app/routers/deliberations.py`; extra fields
    such as `poll_url` or `created_at` are ignored.

    Attributes:
        job_id: ID of the run inside AL-AI Engine; used to poll it.
        application_id: loan application the run is about.
        status: `queued` -> `running` -> `done` | `failed`.
        result: final state of the committee (decision, votes, figures, reasoning trail); only when `done`.
        error: why the run failed; only when `failed`.
    """

    job_id: str
    application_id: str
    status: Literal["queued", "running", "done", "failed"]
    result: dict[str, Any] | None = None
    error: str | None = None


def _json_or_empty(response: httpx.Response) -> dict[str, Any]:
    """Reads the JSON object of a response without raising.

    Args:
        response: any response of AL-AI Engine.

    Returns:
        dict[str, Any]: the JSON object; `{}` if the body is empty, not JSON, or JSON but not an object.
    """
    try:
        body = response.json()
    except ValueError:
        return {}

    return body if isinstance(body, dict) else {}


def _detail(response: httpx.Response) -> object:
    """Reads `detail` of a FastAPI error response (e.g. the list of 422 validation errors).

    Args:
        response: error response of AL-AI Engine.

    Returns:
        object: the `detail` field, or the raw response text if there is none.
    """
    return _json_or_empty(response).get("detail", response.text)


class AIEngineClient:
    """HTTP client for AL-AI Engine (internal service).

    AL-Core is the only caller of the AI engine. Every request carries the shared secret in the
    `X-Internal-Key` header; the engine rejects anything without it (401).

    Besides the wiring checks (`/health`, `/ready`, `/internal/ping`), AL-Core starts AI committee runs
    (`POST /v1/deliberations`) and polls them (`GET /v1/deliberations/{job_id}`).

    One client (and so only one TCP connection pool) lives for the whole app: it is created in `main.lifespan`
    and closed on shutdown with `aclose()` (if a new client is created for every request, the response time
    will be considerably longer).
    """

    def __init__(
        self,
        base_url: str,
        internal_key: str,
        *,
        transport: httpx.AsyncBaseTransport
        | None = None,  # required for tests (they pass httpx.MockTransport),
        use_http2: bool = False,
    ) -> None:
        """Creates the client and its connection pool; nothing is sent until the first request.

        Args:
            base_url: base URL of AL-AI Engine, e.g. `http://ai:8001`; a trailing `/` is removed.
            internal_key: shared secret sent as `X-Internal-Key`; empty means no header (local development,
            the engine then skips the check).
            transport: custom httpx transport; tests pass `httpx.MockTransport` to answer without a network.
            `None` (default) means the real network.
        """
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={_INTERNAL_KEY_HEADER: internal_key} if internal_key else {},
            timeout=AIEngineTimeout.DEFAULT,
            transport=transport,
            http2=use_http2,
        )

    async def aclose(self) -> None:
        """Closes the connection pool; called once on app shutdown (`main.lifespan`)."""
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        timeout: AIEngineTimeout = AIEngineTimeout.DEFAULT,
    ) -> dict[str, Any]:
        """Sends a request and turns every failure into a typed `AIEngineError`.

        Used by business calls, where only a 2xx answer is a success (health checks use `status`).

        Args:
            method: HTTP method, e.g. `GET` or `POST`.
            path: path relative to the base URL, e.g. `/v1/deliberations`.
            json: request body, serialized to JSON; `None` sends no body.
            timeout: seconds to wait for each phase of the request.

        Returns:
            dict[str, Any]: JSON body of the successful answer.

        Raises:
            AIEngineAuthError: 401, `X-Internal-Key` was rejected.
            AIEngineNotFoundError: 404, e.g. an unknown job.
            AIEngineRejectedError: any other 4xx, e.g. 422 when AL-Core sent invalid data.
            AIEngineUnavailableError: 5xx, timeout, network error or an answer that is not JSON.
        """
        try:
            response = await self._client.request(
                method, path, json=json, timeout=timeout
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            match status_code:
                case status.HTTP_401_UNAUTHORIZED:
                    raise AIEngineAuthError(path) from e
                case status.HTTP_404_NOT_FOUND:
                    raise AIEngineNotFoundError(path) from e
                case _ if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
                    raise AIEngineUnavailableError(f"{status_code} on {path}") from e
                case _:
                    raise AIEngineRejectedError(
                        path, status_code, _detail(e.response)
                    ) from e
        except httpx.TimeoutException as e:
            raise AIEngineUnavailableError(f"Timeout on {path}") from e
        except httpx.RequestError as e:
            raise AIEngineUnavailableError(
                f"Network error on {path}: {type(e).__name__}"
            ) from e

        try:
            return response.json()
        except ValueError as e:
            raise AIEngineUnavailableError(f"Invalid JSON on {path}") from e

    async def status(self) -> AIEngineStatus:
        """Checks liveness, the shared key and readiness of AL-AI Engine in one go. Never raises.

        Unlike `_request`, every HTTP answer is data here: 401 from `/internal/ping` means the keys
        differ, 503 from `/ready` means the valuation model is missing. Only a network error (engine
        down, timeout) ends the checks early; the checks that did not run stay `False`.

        Returns:
            AIEngineStatus: result of the three checks; `error` explains what went wrong, if anything.
        """
        result = AIEngineStatus(url=self._base_url, reachable=False)

        try:
            health = await self._client.get("/health", timeout=AIEngineTimeout.HEALTH)
            result.reachable = health.status_code == status.HTTP_200_OK

            ping = await self._client.get(
                "/internal/ping", timeout=AIEngineTimeout.HEALTH
            )
            result.internal_key_accepted = ping.status_code == status.HTTP_200_OK
            if ping.status_code == status.HTTP_401_UNAUTHORIZED:
                result.error = (
                    "AI engine rejected X-Internal-Key (INTERNAL_API_KEY differs)"
                )

            # /ready answers 503 with the same body when the model is missing
            ready = _json_or_empty(
                await self._client.get("/ready", timeout=AIEngineTimeout.HEALTH)
            )
            result.ready = bool(ready.get("ready"))
            result.model_loaded = bool(ready.get("model_loaded"))
            result.model_version = ready.get("model_version")

        except httpx.HTTPError as exc:
            # some httpx errors have no message (e.g. ConnectTimeout): then the class name alone
            result.error = (
                f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            )

        return result

    async def start_deliberation(self, application: dict[str, Any]) -> DeliberationJob:
        """Starts an AI committee run (`POST /v1/deliberations`).

        The engine only queues the run and answers at once (202) with a job ID; the committee itself
        runs in the background, so poll it with `get_deliberation`.

        Args:
            application: `ApplicationInput` of AL-AI Engine (built by `assessments.mapping.to_engine_input`).

        Returns:
            DeliberationJob: the queued run (`status` is `queued`, `result` is `None`).

        Raises:
            AIEngineAuthError: `X-Internal-Key` was rejected (INTERNAL_API_KEY differs).
            AIEngineRejectedError: the engine did not accept the application data (e.g. 422).
            AIEngineUnavailableError: the engine is down, too slow or failed (network error, timeout, 5xx).
        """
        body = await self._request(
            "POST",
            "/v1/deliberations",
            json=application,
            timeout=AIEngineTimeout.DELIBERATION,
        )

        return DeliberationJob.model_validate(body)

    async def get_deliberation(self, job_id: str) -> DeliberationJob | None:
        """Reads the state of an AI committee run (`GET /v1/deliberations/{job_id}`).

        Args:
            job_id: ID returned by `start_deliberation`.

        Returns:
            DeliberationJob | None: the run, with `result` once `status` is `done`; `None` if the engine
            does not know the job (it keeps jobs in memory only, so a restart of the engine loses them).

        Raises:
            AIEngineAuthError: `X-Internal-Key` was rejected (INTERNAL_API_KEY differs).
            AIEngineUnavailableError: the engine is down, too slow or failed (network error, timeout, 5xx).
        """
        try:
            body = await self._request(
                "GET",
                f"/v1/deliberations/{job_id}",
                timeout=AIEngineTimeout.DELIBERATION,
            )
        except AIEngineNotFoundError:
            return None

        return DeliberationJob.model_validate(body)
