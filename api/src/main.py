from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.responses import RedirectResponse
from loguru import logger

from src.firebase.connection import init_firebase


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("Server startup")
    init_firebase()
    yield
    logger.debug("Server shutdown")


def load_routers(api: FastAPI, *routers: APIRouter):
    for router in routers:
        api.include_router(router)


app = FastAPI(
    lifespan=lifespan,
    title="AL-Core",
    description="REST API for Agentic Lender!",
    root_path="/api/v1",
    docs_url=None,
    openapi_url="/docs/openapi.json",
    redoc_url="/docs",
)

load_routers(app)


@app.get("/")
async def root():
    logger.debug("GET root route requested")
    return RedirectResponse("/health")


@app.get("/health", tags=["health"])
async def health():
    logger.debug("GET health route requested")
    return {"status": "ok"}


# uvicorn src.main:app --port 8000 --reload | uv run pytest -v
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", reload=True, port=8000)
