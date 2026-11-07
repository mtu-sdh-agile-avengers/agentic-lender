"""Tests for model resolution (local file or Hugging Face Hub)."""

from pathlib import Path

from app.config import Settings
from app.services.model_loader import load_model, resolve_model_path


def settings(**overrides) -> Settings:
    base = {"model_path": Path("/does/not/exist.joblib"), "hf_repo_id": "",
            "hf_token": "", "internal_api_key": ""}
    return Settings(**{**base, **overrides})


def test_local_model_is_preferred(tmp_path):
    local = tmp_path / "avm_v1.joblib"
    local.write_bytes(b"not a real model")
    assert resolve_model_path(settings(model_path=local)) == local


def test_no_local_model_and_no_repo_returns_none():
    assert resolve_model_path(settings()) is None


def test_download_failure_is_not_fatal(monkeypatch):
    """A missing model must degrade to 503, never crash startup."""
    import app.services.model_loader as loader

    def explode(**_kwargs):
        raise OSError("hub unreachable")

    monkeypatch.setattr(loader, "resolve_model_path", lambda _s: None)
    assert load_model(settings(hf_repo_id="team/al-avm")) is None


def test_unreadable_file_returns_none(tmp_path):
    broken = tmp_path / "avm_v1.joblib"
    broken.write_bytes(b"definitely not a pickle")
    assert load_model(settings(model_path=broken)) is None
