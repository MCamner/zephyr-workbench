from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "zephyr.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_validate_command_passes_on_valid_example() -> None:
    result = run_cli("validate", "examples/macos-intune-windows-domain.yaml")

    assert result.returncode == 0
    assert "macos-intune-windows-domain" in result.stdout
    assert result.returncode == 0


def test_validate_command_reports_errors() -> None:
    result = run_cli("validate", "tests/fixtures/invalid/missing-name.yaml")

    assert result.returncode == 1
    assert "Validation failed:" in result.stderr
    assert "missing required top-level field: name" in result.stderr


def test_validate_command_reports_malformed_yaml_cleanly() -> None:
    result = run_cli("validate", "tests/fixtures/invalid/malformed.yaml")

    assert result.returncode == 1
    assert "Validation failed:" in result.stderr
    assert "invalid YAML" in result.stderr
    assert "Traceback" not in result.stderr


def test_validate_command_supports_json_valid_result() -> None:
    result = run_cli("validate", "examples/identity-flow.yaml", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["errors"] == []
    assert payload["warnings"] == []
    assert payload["data"]["valid"] is True
    assert payload["data"]["name"] == "identity-flow"
    assert payload["metadata"] == {
        "command": "validate",
        "source": "examples/identity-flow.yaml",
        "schema_version": "zephyr-result.v1",
    }


def test_validate_command_supports_json_warning_result() -> None:
    result = run_cli("validate", "examples/macos-intune-windows-domain.yaml", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "warning"
    assert payload["errors"] == []
    assert payload["warnings"] == ["component 'windows-domain' has no flows (orphaned)"]
    assert payload["data"]["valid"] is True
    assert payload["data"]["name"] == "macos-intune-windows-domain"
    assert payload["metadata"]["schema_version"] == "zephyr-result.v1"


def test_validate_command_supports_json_error_result() -> None:
    result = run_cli("validate", "tests/fixtures/invalid/missing-name.yaml", "--json")

    assert result.returncode == 1
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert "missing required top-level field: name" in payload["errors"]
    assert payload["warnings"] == []
    assert payload["data"] == {"valid": False}
    assert payload["metadata"] == {
        "command": "validate",
        "source": "tests/fixtures/invalid/missing-name.yaml",
        "schema_version": "zephyr-result.v1",
    }


def test_diagram_command_renders_mermaid_for_valid_input() -> None:
    result = run_cli("diagram", "examples/identity-flow.yaml", "--format", "mermaid")

    assert result.returncode == 0
    assert "graph TD" in result.stdout
    assert 'idp["idp (identity-provider)"]' in result.stdout


def test_summary_command_supports_json_output() -> None:
    result = run_cli("summary", "examples/secure-workplace.yaml", "--json")

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["name"] == "secure-workplace"
    assert data["components"] == 7
    assert data["risks"] == 2


def test_run_command_generates_summary_and_diagram(tmp_path: Path) -> None:
    result = run_cli(
        "run",
        "examples/identity-flow.yaml",
        "--output-dir",
        str(tmp_path),
    )

    diagram_path = tmp_path / "identity-flow.mmd"

    assert result.returncode == 0
    assert "Validation passed" in result.stdout
    assert "Architecture: identity-flow" in result.stdout
    assert f"Diagram generated: {diagram_path}" in result.stdout
    assert diagram_path.exists()
    assert "graph TD" in diagram_path.read_text(encoding="utf-8")


def test_validate_command_reports_warnings_for_smart_rules(tmp_path: Path) -> None:
    path = tmp_path / "warnings.yaml"
    data = {
        "name": "warning-case",
        "components": [
            {"name": "laptop-a", "type": "endpoint"},
            {"name": "laptop-b", "type": "endpoint"},
            {"name": "vpn-gateway", "type": "access-gateway"},
        ],
        "flows": [
            {"from": "laptop-a", "to": "laptop-b", "label": "peer sync"},
            {"from": "laptop-a", "to": "vpn-gateway", "label": "login", "authentication": "mfa"},
        ],
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    result = run_cli("validate", str(path))

    assert result.returncode == 0
    assert "Warnings:" in result.stdout
    assert "W1:" in result.stdout
    assert "Validation passed with warnings: warning-case" in result.stdout


def test_help_command_prints_usage_guide() -> None:
    result = run_cli("help")

    assert result.returncode == 0
    assert "Quick start" in result.stdout
    assert "Commands" in result.stdout
    assert "Model structure" in result.stdout
    assert "Tips" in result.stdout
    for cmd in ("run", "validate", "summary", "diagram", "diff", "init", "templates", "reference"):
        assert cmd in result.stdout


def test_no_command_prints_help() -> None:
    result = run_cli()

    assert result.returncode == 0
    assert "Quick start" in result.stdout


def test_run_command_reports_warnings_when_present(tmp_path: Path) -> None:
    path = tmp_path / "warnings.yaml"
    data = {
        "name": "warning-case",
        "components": [
            {"name": "laptop-a", "type": "endpoint"},
            {"name": "laptop-b", "type": "endpoint"},
        ],
        "flows": [
            {"from": "laptop-a", "to": "laptop-b", "label": "peer sync"},
        ],
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    result = run_cli("run", str(path), "--output-dir", str(tmp_path / "out"))

    assert result.returncode == 0
    assert "Warnings:" in result.stdout
    assert "Validation passed with warnings" in result.stdout
