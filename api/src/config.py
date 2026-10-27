"""App configuration.

Settings are loaded by pydantic-settings from the `.env` file; access ONLY through `get_config()`
rather than creating `Config` instance directly.

NOTE: real environment variables override local `.env`; pydentic-settings does not load `.env` vars into os.environ.
"""

from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# default name of the Firestore database is "(default)"; does not depends on type (standard / enterprise)
_DEFAULT_DATABASE = "(default)"


class RunMode(StrEnum):
    PROD = "prod"
    DEV = "dev"


class Config(BaseSettings):
    run_mode: Literal[RunMode.PROD, RunMode.DEV]
    
    google_application_credentials: str
    firestore_prod_database_name: str
    firestore_emulator_host: str
    firebase_auth_emulator_host: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # required, since prod database has differenet name (is not default one)
    @property
    def firestore_database_name(self) -> str:
        return (
            _DEFAULT_DATABASE
            if self.run_mode == RunMode.DEV
            else self.firestore_prod_database_name
        )


@lru_cache  # allows Config object to be created only once, the first time it's called
def get_config() -> Config:
    """Returns the application settings (cached).

    Returns:
        Config: application config object
    """

    # Pyright sees required field(s) with no arguments passed and reports
    # "Argument(s) missing for parameter(s)" error; pydantic-settings fills Config() from the `.env` fileuvicorn src.main:app --reload
    return Config()  # pyright: ignore[reportCallIssue]
