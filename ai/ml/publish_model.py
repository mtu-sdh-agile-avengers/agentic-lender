"""Publish the trained valuation model to Hugging Face Hub.

The model bundle is about 95 MB, which does not belong in Git: GitHub warns
above 50 MB, every retrain would add another copy to history forever, and the
datasets it is built from are not ours to redistribute.

Hosting it on the Hub means AL-Core and CI can fetch a known version without
training anything, and each upload is a commit we can roll back.

Setup (once):
    pip install huggingface_hub
    # create a token at https://huggingface.co/settings/tokens (write access)
    setx HF_TOKEN "hf_..."          # Windows, new terminal afterwards

Usage:
    python ml/publish_model.py
    python ml/publish_model.py --repo-id my-team/al-avm --private
"""

import argparse
import json
import os
import sys
from pathlib import Path

import joblib
from huggingface_hub import HfApi

DEFAULT_REPO = os.getenv("HF_REPO_ID", "agentic-lender/al-avm")
MODEL_PATH = Path(__file__).resolve().parent / "models" / "avm_v1.joblib"
METRICS_PATH = Path(__file__).resolve().parent / "reports" / "model_metrics.md"

MODEL_CARD = """---
license: mit
tags:
  - tabular-regression
  - property-valuation
---

# AL-AVM: Automated Valuation Model for Irish residential property

Part of **AL (Agentic Lender)**, a student project at MTU. The model estimates
the market asking value of a residential property in the Republic of Ireland.

## Inputs

County, floor area (m2), bedrooms, bathrooms, property type, BER rating, and
latitude/longitude. Missing floor area and BER are imputed inside the pipeline,
with `area_known` and `ber_known` flags marking those rows.

## Training data

{rows} listings from the Ireland House Properties Dataset 2024 (Daft.ie),
after cleaning: dwellings only, Northern Ireland excluded, implausible floor
areas removed, duplicate listings dropped.

## Performance

{metrics}

## Limitations

- Trained on **asking prices**, not sale prices. Outputs are an estimated
  market asking value, not a valuation for lending purposes.
- Error is concentrated in inexpensive rural property (around 32% in the
  cheapest fifth of the market versus about 11% mid-market).
- A single 2024 snapshot, so it cannot capture price movement over time.

## Usage

```python
import joblib, pandas as pd
from huggingface_hub import hf_hub_download

bundle = joblib.load(hf_hub_download("{repo_id}", "avm_v1.joblib"))
row = pd.DataFrame([{{...}}])          # see numeric_features / categorical_features
estimate = bundle["model"].predict(row)[0]
```
"""


def build_card(repo_id: str, bundle: dict) -> str:
    metrics = bundle.get("metrics", {})
    table = "\n".join(f"- **{name}**: {value:,.1f}" for name, value in metrics.items())
    return MODEL_CARD.format(
        repo_id=repo_id,
        rows=f"{bundle.get('trained_rows', 0):,}",
        metrics=table or "_see reports/model_metrics.md_",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", default=DEFAULT_REPO,
                        help="owner/name on the Hub")
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--message", default=None, help="commit message")
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN")
    if not token:
        sys.exit("HF_TOKEN is not set. Create a write token at "
                 "https://huggingface.co/settings/tokens")
    if not MODEL_PATH.exists():
        sys.exit(f"No model at {MODEL_PATH}. Run ml/train_avm.py first.")

    bundle = joblib.load(MODEL_PATH)
    version = bundle.get("version", "unknown")
    size_mb = MODEL_PATH.stat().st_size / 1_000_000
    print(f"Publishing {version} ({size_mb:.0f} MB) to {args.repo_id}")

    api = HfApi(token=token)
    api.create_repo(args.repo_id, repo_type="model", private=args.private,
                    exist_ok=True)

    api.upload_file(path_or_fileobj=str(MODEL_PATH),
                    path_in_repo=MODEL_PATH.name,
                    repo_id=args.repo_id,
                    commit_message=args.message or f"model {version}")

    # A small metadata file lets callers check the version without downloading
    # 95 MB of model first.
    meta = {"version": version,
            "metrics": bundle.get("metrics", {}),
            "trained_rows": bundle.get("trained_rows"),
            "numeric_features": bundle.get("numeric_features"),
            "categorical_features": bundle.get("categorical_features")}
    api.upload_file(path_or_fileobj=json.dumps(meta, indent=2).encode(),
                    path_in_repo="model_info.json",
                    repo_id=args.repo_id,
                    commit_message=f"metadata for {version}")

    api.upload_file(path_or_fileobj=build_card(args.repo_id, bundle).encode(),
                    path_in_repo="README.md",
                    repo_id=args.repo_id,
                    commit_message=f"model card for {version}")

    if METRICS_PATH.exists():
        api.upload_file(path_or_fileobj=str(METRICS_PATH),
                        path_in_repo="model_metrics.md",
                        repo_id=args.repo_id)

    print(f"Done: https://huggingface.co/{args.repo_id}")


if __name__ == "__main__":
    main()
