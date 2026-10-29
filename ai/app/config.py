"""Settings for the AL-AI Engine.

Everything configurable lives here and is read from environment variables or
the .env file, so no key, URL or model name is ever hardcoded in the code.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=SERVICE_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # service
    service_name: str = "al-ai-engine"
    version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    # AL-Core calls us with this header; see the internal endpoints contract
    internal_api_key: str = ""
    # AL-Core's base URL, for posting deliberation results back
    core_base_url: str = "http://localhost:8000"
    # Only AL-Core and local tools should reach this service

    # machine learning
    model_path: Path = SERVICE_ROOT / "ml" / "models" / "avm_v1.joblib"

    # LLM providers (names only; keys stay in their own variables)
    groq_api_key: str = ""
    gemini_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    gemini_model: str = ""
    ollama_model: str = "llama3.2"
    ollama_url: str = "http://localhost:11434"


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is parsed once per process."""
    return Settings()
