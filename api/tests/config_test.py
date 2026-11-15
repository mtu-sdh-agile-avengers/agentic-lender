import pytest

from src.config import Config, FirebaseMode, RunMode

BASE = {
    "firestore_emulator_host": "127.0.0.1:8080",
    "firebase_auth_emulator_host": "127.0.0.1:9099",
    "cors_origins": [],
    "firestore_prod_database_name": "default",
}


@pytest.mark.parametrize(
    ("run_mode", "firebase_mode", "emulators", "database"),
    [
        (RunMode.DEV, None, True, "(default)"),                    # old behaviour: dev -> emulators
        (RunMode.PROD, None, False, "default"),                    # old behaviour: prod -> real project
        (RunMode.DEV, FirebaseMode.CLOUD, False, "default"),       # real Firebase, dev conveniences
        (RunMode.PROD, FirebaseMode.EMULATOR, True, "(default)"),
    ],
)
def test_firebase_mode_decides_emulators(run_mode, firebase_mode, emulators, database):
    config = Config(**BASE, run_mode=run_mode, firebase_mode=firebase_mode, _env_file=None)
    assert config.use_emulators is emulators
    assert config.firestore_database_name == database


def test_emulator_hosts_have_local_defaults():
    config = Config(run_mode=RunMode.PROD, cors_origins=[], _env_file=None)
    assert config.firestore_emulator_host == "127.0.0.1:8080"
    assert config.firebase_auth_emulator_host == "127.0.0.1:9099"
