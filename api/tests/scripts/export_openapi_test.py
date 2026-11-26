"""ALG4-153: the OpenAPI export."""

import yaml

from src.scripts import export_openapi


def test_spec_describes_the_api():
    spec = export_openapi.build_spec()
    assert spec["openapi"].startswith("3.")
    assert "/api/v1/loan-applications/{loan_application_id}/audit-pack" in spec["paths"]
    assert yaml.safe_load(export_openapi.render(spec, "yaml")) == spec


def test_check_fails_until_the_file_is_written(tmp_path, capsys):
    out = tmp_path / "openapi.yaml"
    assert export_openapi.main(["--check", "--out", str(out)]) == 1
    assert export_openapi.main(["--out", str(out)]) == 0
    assert export_openapi.main(["--check", "--out", str(out)]) == 0
    assert (
        export_openapi.main(
            ["--format", "json", "--out", str(tmp_path / "openapi.json")]
        )
        == 0
    )
    assert "paths" in capsys.readouterr().out
