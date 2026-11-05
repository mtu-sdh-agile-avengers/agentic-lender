"""Health and readiness endpoints.

/health   - is the process alive? (used by Docker Compose and AL-Core)
/ready    - is it actually able to serve? model loaded, providers configured
"""

import httpx
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.deps import SettingsDep

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


class ReadyResponse(BaseModel):
    ready: bool
    model_loaded: bool
    model_version: str | None = None
    providers: dict[str, bool]
    ollama_reachable: bool


@router.get("/health", response_model=HealthResponse)
async def health(settings: SettingsDep) -> HealthResponse:
    """Liveness. Must stay cheap: no model, no network calls."""
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.version,
        environment=settings.environment,
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready(request: Request, settings: SettingsDep) -> JSONResponse:
    """Readiness. Reports what this service can actually do right now."""
    bundle = getattr(request.app.state, "model_bundle", None)

    ollama_up = False
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            ollama_up = response.status_code == 200
    except httpx.HTTPError:
        ollama_up = False

    body = ReadyResponse(
        ready=bundle is not None,
        model_loaded=bundle is not None,
        model_version=bundle.get("version") if bundle else None,
        providers={
            "groq": bool(settings.groq_api_key),
            "gemini": bool(settings.gemini_api_key),
            "ollama": ollama_up,
        },
        ollama_reachable=ollama_up,
    )
    code = status.HTTP_200_OK if body.ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=body.model_dump())
