"""Credential selection for the real Firebase project (no network: credentials are only parsed)."""

import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from src.config import Config, FirebaseMode, RunMode
from src.firebase import connection


def _service_account() -> dict:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    return {
        "type": "service_account",
        "project_id": "agentic-lender",
        "private_key_id": "test",
        "private_key": pem,
        "client_email": "ci@agentic-lender.iam.gserviceaccount.com",
        "client_id": "1",
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def _use(monkeypatch, **settings):
    config = Config(
        run_mode=RunMode.DEV, firebase_mode=FirebaseMode.CLOUD, cors_origins=[], _env_file=None, **settings
    )
    monkeypatch.setattr(connection, "get_config", lambda: config)


def test_json_in_env_var_is_enough(monkeypatch):
    _use(monkeypatch, firestore_prod_database_name="default",
         firebase_service_account_json=json.dumps(_service_account()))
    assert connection._cloud_credential().project_id == "agentic-lender"


def test_key_file_still_works(monkeypatch, tmp_path):
    key = tmp_path / "service-account.json"
    key.write_text(json.dumps(_service_account()))
    _use(monkeypatch, firestore_prod_database_name="default", google_application_credentials=str(key))
    assert connection._cloud_credential().project_id == "agentic-lender"


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"firebase_service_account_json": "{}"}, "FIRESTORE_PROD_DATABASE_NAME"),
        ({"firestore_prod_database_name": "default"}, "service account key"),
        ({"firestore_prod_database_name": "default", "firebase_service_account_json": "not json"}, "not valid JSON"),
    ],
)
def test_missing_or_broken_settings_fail_with_a_readable_message(monkeypatch, settings, message):
    _use(monkeypatch, **settings)
    with pytest.raises(RuntimeError, match=message):
        connection._cloud_credential()
