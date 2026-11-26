"""Exports the OpenAPI description of AL-Core into `docs/api/` (ALG4-153).

FastAPI builds the description (`openapi.json`) from the routes and Pydantic schemas; this script writes it to a file
so the REST API is documented in the repository and can be read without running the server (e.g. in Swagger Editor,
Postman or Redocly). Nothing is sent anywhere; no Firebase or AI engine is needed.

Usage (from `api/`):
    uv run python -m src.scripts.export_openapi                  # docs/api/openapi.yaml
    uv run python -m src.scripts.export_openapi --format json    # docs/api/openapi.json
    uv run python -m src.scripts.export_openapi --out ../somewhere/openapi.yaml
    uv run python -m src.scripts.export_openapi --check          # exit 1 if the file is out of date

Run it after changing a route or a schema and commit the result.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

DOCS_API = Path(__file__).resolve().parents[3] / "docs" / "api"


def build_spec() -> dict[str, Any]:
    """Builds the OpenAPI description of AL-Core, exactly as `GET /openapi.json` serves it."""
    # the app reads its settings on import; values that only matter for a running server get harmless defaults
    os.environ.setdefault("RUN_MODE", "dev")
    os.environ.setdefault("CORS_ORIGINS", "[]")

    from src.main import app  # imported here, after the defaults are set

    return app.openapi()


def render(spec: dict[str, Any], fmt: str) -> str:
    """Serializes the description; keys keep FastAPI's order, so diffs stay small between exports."""
    if fmt == "json":
        return json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
    return yaml.safe_dump(spec, sort_keys=False, allow_unicode=True, width=120)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--format", choices=["yaml", "json"], default="yaml")
    parser.add_argument(
        "--out", type=Path, help="output file (default: docs/api/openapi.<format>)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; fail if the file differs from the current API",
    )
    args = parser.parse_args(argv)

    out: Path = args.out or DOCS_API / f"openapi.{args.format}"
    text = render(build_spec(), args.format)

    if args.check:
        current = out.read_text(encoding="utf-8") if out.exists() else ""
        if current != text:
            print(
                f"{out} is out of date: run `uv run python -m src.scripts.export_openapi`",
                file=sys.stderr,
            )
            return 1
        print(f"{out} is up to date")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    spec = yaml.safe_load(text) if args.format == "yaml" else json.loads(text)
    print(
        f"wrote {out} ({len(spec.get('paths', {}))} paths, OpenAPI {spec.get('openapi')})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
