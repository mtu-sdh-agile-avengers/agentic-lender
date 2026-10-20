import os
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.responses import RedirectResponse
from loguru import logger
from src.config import get_config
from src.firebase.connection import get_firestore, init_firebase


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug(f"Server startup [{get_config().run_mode}]")

    init_firebase()
    db = get_firestore()
    logger.debug(
        f"database_string={db._database_string}, emulator={os.environ.get('FIRESTORE_EMULATOR_HOST')}"
    )

    yield
    logger.debug("Server shutdown")


def load_routers(api: FastAPI, *routers: APIRouter):
    for router in routers:
        api.include_router(router)


app = FastAPI(
    lifespan=lifespan,
    title="AL-Core",
    description="REST API for Agentic Lender!",
    docs_url="/docs/swagger",
    openapi_url="/docs/openapi.json",
    redoc_url="/docs",
)

load_routers(app)


@app.get("/", tags=["root"])
async def root():
    logger.debug("GET root route requested")
    return RedirectResponse("/health")


@app.get("/health", tags=["health"])
async def health():
    logger.debug("GET health route requested")
    return {"status": "ok"}


# uvicorn src.main:app --port 8000 --reload | uv run pytest -v
if __name__ == "__main__":
    # to run locally first: npx firebase emulators:start --project demo-agentic-lender
    import uvicorn

    uvicorn.run("src.main:app", reload=True, port=8000)
