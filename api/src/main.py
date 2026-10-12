from fastapi import FastAPI
from fastapi import status
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager

from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("Server startup")
    yield
    logger.debug("Server shutdown")
    

app = FastAPI(
    lifespan=lifespan,
    title="AL-Core"
    )

@app.get("/")
async def root():
    logger.debug("GET root route requested")
    return RedirectResponse("/health")

@app.get("/health")
async def health():
    logger.debug("GET health route requested")
    return {"status": status.HTTP_200_OK}

# uvicorn main:app --app-dir src --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True)