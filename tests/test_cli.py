from __future__ import annotations

import subprocess
import sys


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
    assert "Validation passed: macos-intune-windows-domain" in result.stdout


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


def test_diagram_command_renders_mermaid_for_valid_input() -> None:
    result = run_cli("diagram", "examples/identity-flow.yaml", "--format", "mermaid")

    assert result.returncode == 0
    assert "graph TD" in result.stdout
    assert 'idp["idp (identity-provider)"]' in result.stdout
