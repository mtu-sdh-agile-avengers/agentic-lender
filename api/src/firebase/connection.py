"""Firebase Admin SDK setup.
NOTE: "`app`" parameter is not utilized, since only one, i.e. default, Firebase app being used by AL-Core.
"""

import json
import os

import firebase_admin
from firebase_admin import credentials, firestore_async
from google.auth.credentials import AnonymousCredentials
from google.cloud.firestore import AsyncClient
from loguru import logger

from src.config import get_config

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
    """Loads and initializes a credential from a Google service account certificate.

    Args:
        path (str): Path to a certificate file or a dict representing the contents of a certificate.

    Raises:
        IOError: If file was not found or could not be read.
    """
    try:
        return credentials.Certificate(path)
    except OSError:
        logger.error("Service account key .json file not found or could not be read.")
        raise


def _cloud_credential() -> credentials.Certificate:
    """Loads credential for the Cloud Firebase project. Fails fast with a readable message instead of a Firebase stack trace.

    NOTE: FIREBASE_SERVICE_ACCOUNT_JSON (the key itself) wins over GOOGLE_APPLICATION_CREDENTIALS (a path to it).
    """
    if not get_config().firestore_prod_database_name:
        raise RuntimeError("Cloud Firebase needs FIRESTORE_PROD_DATABASE_NAME")

    if get_config().firebase_service_account_json:
        try:
            return credentials.Certificate(
                json.loads(get_config().firebase_service_account_json)
            )
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON"
            ) from exc

    if not get_config().google_application_credentials:
        raise RuntimeError(
            "Cloud Firebase needs a service account key: "
            "FIREBASE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS"
        )
    if not os.path.isfile(get_config().google_application_credentials):
        raise FileNotFoundError(
            f"Service account key not found at {get_config().google_application_credentials}. "
            "Download it from Firebase Console -> Project settings -> Service accounts."
        )
    return _load_certificate(get_config().google_application_credentials)


def init_firebase() -> None:
    """Initializes Firebase Admin SDK. Safe to call more than once.

    Returns:
        None: nothing, since firebase_admin contains list of apps and by default always referes to `_DEFAULT_APP_NAME`.

    Raises:
        RuntimeError: cloud Firebase requested, but required settings are missing or broken.
        FileNotFoundError: if private service account key `.json` file was not found.
    """
    try:
        firebase_admin.get_app()  # if app isn't initialized, then rises ValueError; otherwise retrieves default app instance (_DEFAULT_APP_NAME)
    except ValueError:
        if get_config().use_emulators:
            os.environ[_FIRESTORE_EMULATOR_ENV] = (
                get_config().firestore_emulator_host
            )  # allows automatically connect to Cloud Firestore emulator

            os.environ[_FIREBASE_AUTH_EMULATOR_ENV] = (
                get_config().firebase_auth_emulator_host
            )  # allows automatically connect to Firebase Auth emulator

            cred = (
                _EmulatorCredential()
            )  # emulators accept any credentials, service account key is not required
            options = {
                "projectId": get_config().firebase_project_id
            }  # emulator suit starts with "--project demo-agentic-lender" CLA, therefore app should have the same project_id to connect
            target = f"emulators: {get_config().firebase_project_id}"
        else:
            os.environ.pop(_FIRESTORE_EMULATOR_ENV, None)
            os.environ.pop(_FIREBASE_AUTH_EMULATOR_ENV, None)

            cred = _cloud_credential()
            options = None  # explicit projectId is not required, since credentials are used (service account key)
            target = f"cloud: {cred.project_id}"

        firebase_admin.initialize_app(cred, options)
        logger.success(f"Firebase initialized successfully ({target})")


# "`db_id`" parameter may be required in the future, when there is possibly will be more than one Cloud Firestore database
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
