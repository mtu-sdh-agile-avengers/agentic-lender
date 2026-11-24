"""App configuration.

Settings are loaded by pydantic-settings from the `.env` file; access ONLY through `get_config()`
rather than creating `Config` instance directly.

NOTE: real environment variables override local `.env`; pydentic-settings does not load `.env` vars into os.environ.
"""

from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# default name of the Firestore database is "(default)"; does not depend on type (standard / enterprise)
_DEFAULT_DATABASE = "(default)"


class RunMode(StrEnum):
    PROD = "prod"
    DEV = "dev"


# Required which Firebase is used (local or cloud). Allows use the real project while keeping dev behavior (no rate limiting + debug logs).
class FirebaseMode(StrEnum):
    EMULATOR = "emulator"  # Firebase Local Emulator Suite, no real credentials required
    CLOUD = "cloud"  # Actual Firebase project, service account key required


class Config(BaseSettings):
    run_mode: Literal[RunMode.PROD, RunMode.DEV]
    firebase_mode: FirebaseMode | None = None

    # service Account key for the Firebase project, either as .json path to local file OR as the JSON string itself
    # (hosts that keep secrets in environment variables: Azure Container Apps, GitHub Actions); optional for emulators
    google_application_credentials: str = ""
    firebase_service_account_json: str = ""

    firestore_prod_database_name: str = ""
    firestore_emulator_host: str = "127.0.0.1:8080"
    firebase_auth_emulator_host: str = "127.0.0.1:9099"

    # ref: https://firebase.google.com/docs/emulator-suite/connect_firestore#choose_a_firebase_project
    # project ID the emulator suite runs under (`firebase emulators:start --project demo-agentic-lender`);
    # used when FIREBASE_MODE=emulators or RUN_MODE=dev and FIREBASE_MODE= (is empty); "demo" prefix allows app to interact with emulators only
    firebase_project_id: str = "demo-agentic-lender"

    # if initialized, could be overridden by CORS_ORIGINS in .env for other ports
    cors_origins: list[str]

    # AL-Core sends `internal_api_key` as X-Internal-Key header to AI-Engine
    ai_engine_url: str = "http://localhost:8001"
    internal_api_key: str = ""

    # Stripe (payments, ALG4-101). Empty = payments are switched off (endpoints answer 503).
    # Outside production only test-mode keys (sk_test_..., pk_test_...) are accepted, so no real money can move.
    # ref: docs/api/payments.md
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = (
        ""  # whsec_...; from `stripe listen` locally, from the Dashboard when deployed
    )
    payments_merchant_name: str = "Agentic Lender"  # shown in the mobile payment sheet

    # env_ignore_empty: `FIREBASE_MODE=` (empty) in .env means "not set", not an invalid value
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True
    )

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
