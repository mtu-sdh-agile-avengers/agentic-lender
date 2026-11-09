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


class FirebaseMode(StrEnum):
    EMULATOR = "emulator"   # local Firebase emulator suite, no real credentials
    CLOUD = "cloud"         # real Firebase project, service account key required


class Config(BaseSettings):
    run_mode: Literal[RunMode.PROD, RunMode.DEV]

    # Which Firebase AL-Core talks to. Not set: follows run_mode (dev -> emulator, prod -> cloud).
    # Set FIREBASE_MODE=cloud to use the real project while keeping dev behaviour (no rate limiting, debug logs).
    firebase_mode: FirebaseMode | None = None

    # service account key (.json); required for the real Firebase project, optional for the emulators
    google_application_credentials: str = ""
    firestore_prod_database_name: str = ""
    firestore_emulator_host: str
    firebase_auth_emulator_host: str
    # project ID the emulator suite runs under (`firebase emulators:start --project demo-agentic-lender`);
    # used in dev when no service account key is provided
    firebase_project_id: str = "demo-agentic-lender"

    # if init. overriden by CORS_ORIGINS in .env for other ports
    cors_origins: list[str]

    # AL-AI Engine (internal service); AL-Core sends `internal_api_key` as X-Internal-Key header
    ai_engine_url: str = "http://localhost:8001"
    internal_api_key: str = ""

    # env_ignore_empty: `FIREBASE_MODE=` (empty) in .env means "not set", not an invalid value
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True)

    @property
    def use_emulators(self) -> bool:
        if self.firebase_mode is not None:
            return self.firebase_mode == FirebaseMode.EMULATOR
        return self.run_mode == RunMode.DEV

    # required, since prod database has differenet name (is not default one)
    @property
    def firestore_database_name(self) -> str:
        return (
            _DEFAULT_DATABASE
            if self.use_emulators
            else self.firestore_prod_database_name
        )


@lru_cache  # allows Config object to be created only once, the first time it's called
def get_config() -> Config:
    """Returns the application settings (cached).

    Returns:
        Config: application config object
    """

    # Pyright sees required field(s) with no arguments passed and reports
    # "Argument(s) missing for parameter(s)" error; pydantic-settings fills Config() from the `.env` file
    return Config()  # pyright: ignore[reportCallIssue]
