"""Reusable FastAPI dependencies.

AL-AI Engine is never exposed to borrowers or brokers. Only AL-Core calls it,
over the internal Docker network, carrying a shared secret header.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def require_internal_key(
    settings: SettingsDep,
    x_internal_key: Annotated[str | None, Header()] = None,
) -> None:
    """Reject anything that is not AL-Core.

    If no key is configured (local development), the check is skipped and a
    warning is logged at startup instead.
    """
    if not settings.internal_api_key:
        return
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing X-Internal-Key",
        )


InternalAuth = Depends(require_internal_key)


def get_model(request: Request):
    """The valuation model, loaded once at startup (see main.lifespan)."""
    bundle = getattr(request.app.state, "model_bundle", None)
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="valuation model is not loaded",
        )
    return bundle


ModelDep = Annotated[dict, Depends(get_model)]
