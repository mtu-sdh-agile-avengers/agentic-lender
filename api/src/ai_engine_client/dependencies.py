from typing import Annotated

from fastapi import Depends, Request

from src.ai_engine_client.client import AIEngineClient


def get_ai_engine_client(request: Request) -> AIEngineClient:
    return request.app.state.ai_engine_client


AIEngineClientDep = Annotated[AIEngineClient, Depends(get_ai_engine_client)]
