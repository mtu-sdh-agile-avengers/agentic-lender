import os
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.ai_engine_client.client import AIEngineClient
from src.ai_engine_client.dependencies import AIEngineClientDep
from src.assessments.v1.router import router as assessments_router
from src.audit_packs.v1.router import router as audit_packs_router
from src.config import get_config
from src.conversations.v1.router import router as conversations_router
from src.firebase.connection import init_firebase
from src.loan_applications.v1.router import router as loan_applications_router
from src.rate_limiting import limiter
from src.reviews.v1.router import router as reviews_router
from src.stress_tests.v1.router import router as stress_tests_router
from src.support_tickets.v1.router import router as support_tickets_router
from src.users.v1.router import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug(f"Server startup [{get_config().run_mode}]")

    init_firebase()
    logger.debug(
        f"database_string={get_config().firestore_database_name}, emulator={os.environ.get('FIRESTORE_EMULATOR_HOST')}"
    )

    app.state.ai_engine_client = AIEngineClient(
        get_config().ai_engine_url, get_config().internal_api_key
    )
    try:
        yield
    finally:
        await app.state.ai_engine_client.aclose()
        logger.debug("Server shutdown")


def load_routers(api: FastAPI, *routers: APIRouter):
    for router in routers:
        api.include_router(router)


app = FastAPI(
    lifespan=lifespan,
    title="AL-Core",
    description="REST API for Agentic Lender.",
    version="0.3.0",
    docs_url="/docs/swagger",
    openapi_url="/docs/openapi.json",
    redoc_url="/docs",
)

# rate limiting set up
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # pyright: ignore[reportArgumentType]

# CORS configuration
logger.debug("Configuring CORS...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_config().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["root"], description='Redirects to "/health".')
@limiter.limit("1/second")
async def root(request: Request):
    logger.debug("GET root route requested")
    return RedirectResponse("/health")


@app.get(
    "/health", tags=["health"], description="Returns server status if it's available."
)
@limiter.limit("1/second")
async def health(request: Request):
    logger.debug("GET health route requested")
    return {"status": "ok"}


@app.get(
    "/health/dependencies",
    tags=["health"],
    description="Checks availability of required services. AI engine: reachable, X-Internal-Key accepted, model loaded.",
)
@limiter.limit("1/second")
async def health_dependencies(request: Request, ai_engine: AIEngineClientDep):
    logger.debug("GET health/dependencies route requested")
    ai_status = await ai_engine.status()
    healthy = ai_status.reachable and ai_status.internal_key_accepted
    return {
        "status": "ok" if healthy else "degraded",
        "ai_engine_client": ai_status.model_dump(),
    }


logger.debug("Loading routers...")
load_routers(
    app,
    users_router,
    loan_applications_router,
    conversations_router,
    assessments_router,
    stress_tests_router,
    support_tickets_router,
    reviews_router,
    audit_packs_router,
)


# uvicorn src.main:app --port 8000 --reload | uv run pytest -v
if __name__ == "__main__":
    # to run locally first: npx firebase emulators:start --project demo-agentic-lender
    import uvicorn

    uvicorn.run("src.main:app", reload=True, port=8000)
