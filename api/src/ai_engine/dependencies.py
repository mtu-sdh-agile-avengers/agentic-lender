from typing import Annotated

from fastapi import Depends

from src.ai_engine.client import AIEngineClient
from src.config import get_config


def get_ai_engine_client() -> AIEngineClient:
    config = get_config()
    return AIEngineClient(config.ai_engine_url, config.internal_api_key)


AIEngineClientDep = Annotated[AIEngineClient, Depends(get_ai_engine_client)]
