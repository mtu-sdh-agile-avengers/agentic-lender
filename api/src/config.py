"""App configuration.

Settings are loaded by pydantic-settings from the `.env` file; access ONLY through `get_config()`
rather than creating `Config` instance directly.

NOTE: real environment variables override local `.env`.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    google_application_credentials: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache  # allows Config object to be created only once, the first time it's called
def get_config() -> Config:
    """Returns the application settings (cached).

    Returns:
        Config: application config object
    """

    # Pyright sees required field(s) with no arguments passed and reports
    # "Argument(s) missing for parameter(s)" error; pydantic-settings fills Config() from the `.env` fileuvicorn src.main:app --reload
    return Config()  # pyright: ignore[reportCallIssue]
