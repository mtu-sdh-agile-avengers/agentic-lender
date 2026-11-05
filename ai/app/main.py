"""AL-AI Engine: FastAPI service (backlog task ALG4-79).

This service is the AI half of the backend. AL-Core calls it; mobile and web
never do. It will expose:

    POST /v1/valuations      property features -> price estimate   (ALG4-77)
    POST /v1/deliberations   application -> agent committee run    (ALG4-80)
    GET  /health, /ready     liveness and readiness                (this task)

Run locally:
    uvicorn app.main:app --reload --port 8001
    open http://localhost:8001/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.requests import Request

from app.config import get_settings
from app.routers import deliberations, health, valuations

settings = get_settings()
logging.basicConfig(level=settings.log_level,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown.

    The valuation model is loaded once here, not per request: unpickling it
    takes time and memory, and every request would otherwise pay that cost.
    """
    app.state.model_bundle = None

    if settings.model_path.exists():
        try:
            import joblib
            app.state.model_bundle = joblib.load(settings.model_path)
            logger.info("loaded valuation model %s from %s",
                        app.state.model_bundle.get("version"), settings.model_path)
        except Exception:
            logger.exception("failed to load valuation model")
    else:
        logger.warning("no model at %s - run ml/train_avm.py first",
                       settings.model_path)

    if not settings.internal_api_key:
        logger.warning("INTERNAL_API_KEY is empty: internal auth is disabled")

    yield

    app.state.model_bundle = None
    logger.info("shutting down")


app = FastAPI(
    title="AL-AI Engine",
    description="Property valuation and multi-agent credit deliberation "
                "for AL (Agentic Lender). Internal service, called by AL-Core.",
    version=settings.version,
    lifespan=lifespan,
)


app.include_router(health.router)
app.include_router(valuations.router)
app.include_router(deliberations.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Never leak a stack trace to the caller; log it and return a clean error."""
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500,
                        content={"detail": "internal server error"})


@app.get("/", include_in_schema=False)
async def root():
    return {"service": settings.service_name, "docs": "/docs"}
