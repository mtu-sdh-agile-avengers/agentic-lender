"""Firebase Admin SDK setup.
NOTE: "`app`" parameter is not utilized, since only one, i.e. default, Firebase app being used by AL-Core.
"""

import os

import firebase_admin
from firebase_admin import credentials, firestore_async
from google.auth.credentials import AnonymousCredentials
from google.cloud.firestore import AsyncClient
from loguru import logger
from src.config import RunMode, get_config

_FIRESTORE_EMULATOR_ENV = "FIRESTORE_EMULATOR_HOST"
_FIREBASE_AUTH_EMULATOR_ENV = "FIREBASE_AUTH_EMULATOR_HOST"


class _EmulatorCredential(credentials.Base):
    """Placeholder credential for the emulator suite (dev only).

    Emulators accept any credentials, so a service account key is not required to run AL-Core locally
    or in Docker Compose. Never used in prod.
    """

    def get_credential(self):
        return AnonymousCredentials()


def _load_certificate(path: str) -> credentials.Certificate:
    try:
        return credentials.Certificate(path)
    except FileNotFoundError:
        logger.error("Service account key .json file not found")
        raise


def init_firebase() -> None:
    """Initializes Firebase Admin SDK. Safe to call more than once.

    Returns:
        None: nothing, since firebase_admin contains list of apps and by default always referes to `_DEFAULT_APP_NAME`.

    Raises:
        FileNotFoundError: if private service account key `.json` file was not found.
    """
    try:
        firebase_admin.get_app()  # if app isn't init, then rises ValueError; otherwise retrieves default app instance (_DEFAULT_APP_NAME)
    except ValueError:
        config = get_config()

        # "demo" prefix allows app and code to interact with emulators only (all is local)
        if config.run_mode == RunMode.DEV:
            os.environ[_FIRESTORE_EMULATOR_ENV] = (
                config.firestore_emulator_host
            )  # allows automatically connect to Cloud Firestore emulator
            os.environ[_FIREBASE_AUTH_EMULATOR_ENV] = (
                config.firebase_auth_emulator_host
            )  # allows automatically connect to Firebase Auth emulator

            # emulator suit starts with "--project demo-agentic-lender" CLA, therefore app should have the same project_id to connect
            if config.google_application_credentials:
                cred = _load_certificate(config.google_application_credentials)
                project_id = f"demo-{cred.project_id}"
            else:
                cred = _EmulatorCredential()
                project_id = config.firebase_project_id
            options = {"projectId": project_id}
        else:
            cred = _load_certificate(config.google_application_credentials)
            os.environ.pop(_FIRESTORE_EMULATOR_ENV, None)
            os.environ.pop(_FIREBASE_AUTH_EMULATOR_ENV, None)
            options = None # explicit projectId is not required, since credentials are used (service account key)

        firebase_admin.initialize_app(cred, options)
        logger.success("Firebase initialized successfully")


# "`db_id`" parameter may be required in the future, when there is possibly will be more than one Cloud Firestore database.
def get_firestore(db_id: str | None = None) -> AsyncClient:
    """Returns a (async) Firestore client object for interacting with Google Cloud Firestore API.

    Args:
        db_id (str, optional): Firestore database ID. Defaults to default Firestore database ID, i.e. "`(default)`".

    Returns:
        AsyncClient: async Firestore client object.
    """
    return firestore_async.client(
        database_id=db_id or get_config().firestore_database_name
    )
