"""Locate and load the valuation model (backlog ML-06 follow-up).

Two sources, in order:

1. a local file, if someone has trained one (ml/models/avm_v1.joblib)
2. Hugging Face Hub, so AL-Core, CI and a deployed container can run the
   service without the dataset or a training run

The Hub download is cached by `huggingface_hub`, so it happens once per
machine and not on every restart.
"""

import logging
from pathlib import Path

from app.config import Settings

logger = logging.getLogger(__name__)


def resolve_model_path(settings: Settings) -> Path | None:
    """Return a path to the model file, downloading it if necessary."""
    if settings.model_path.exists():
        logger.info("using local model at %s", settings.model_path)
        return settings.model_path

    if not settings.hf_repo_id:
        logger.warning("no local model and HF_REPO_ID is not set")
        return None

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        logger.warning("huggingface_hub is not installed; cannot fetch the model")
        return None

    try:
        logger.info("downloading %s from %s (first run only)",
                    settings.hf_model_filename, settings.hf_repo_id)
        path = hf_hub_download(
            repo_id=settings.hf_repo_id,
            filename=settings.hf_model_filename,
            revision=settings.hf_revision,
            token=settings.hf_token or None,
        )
        return Path(path)
    except Exception:
        # A missing model is not fatal: /ready reports it and valuation
        # endpoints answer 503, while the rest of the service still works.
        logger.exception("could not download the model from the Hub")
        return None


def load_model(settings: Settings) -> dict | None:
    path = resolve_model_path(settings)
    if path is None:
        return None

    try:
        import joblib
        bundle = joblib.load(path)
        logger.info("loaded valuation model %s", bundle.get("version"))
        return bundle
    except Exception:
        logger.exception("failed to load the model file at %s", path)
        return None
