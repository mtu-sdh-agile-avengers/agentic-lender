from fastapi import FastAPI
from fastapi import status
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager

from loguru import logger

from src.firebase.connection import init_firebase


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("Server startup")
    await init_firebase()
    await load_routers(app)
    yield
    logger.debug("Server shutdown")
    
async def load_routers(app: FastAPI):
    ...


api = FastAPI(
    lifespan=lifespan,
    title="AL-Core",
    description="REST API for Agentic Lender!",
    root_path="/api/v1",
    docs_url=None,
    openapi_url="/docs/openapi.json",
    redoc_url="/docs",
    )


@api.get("/")
async def root():
    logger.debug("GET root route requested") 
    return RedirectResponse("/health")

@api.get("/health")
async def health():
    logger.debug("GET health route requested")
    return {"status": "ok"}


# uvicorn main:api --app-dir src --reload | uv run pytest -v
if __name__ == "__main__":    
    import uvicorn
    uvicorn.run("main:api", reload = True, port = 8000)