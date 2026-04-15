from pathlib import Path

import pytest
import yaml

from zephyr.validation import (
    ValidationError,
    collect_validation_warnings,
    load_validation_result,
    load_validated_architecture,
)


def test_load_valid_architecture() -> None:
    architecture = load_validated_architecture("examples/macos-intune-windows-domain.yaml")

    assert architecture.name == "macos-intune-windows-domain"
    assert len(architecture.components) == 8
    assert len(architecture.flows) == 6
    assert len(architecture.risks) == 3


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("tests/fixtures/invalid/missing-name.yaml", "missing required top-level field: name"),
        ("tests/fixtures/invalid/empty-components.yaml", "field 'components' must contain at least one component"),
        ("tests/fixtures/invalid/duplicate-component.yaml", "duplicate component name: laptop"),
        ("tests/fixtures/invalid/unknown-flow-target.yaml", "flows[1].to 'directory' does not match any component"),
        ("tests/fixtures/invalid/invalid-risk-severity.yaml", "risks[1].severity 'urgent' is invalid"),
        ("tests/fixtures/invalid/invalid-component-type.yaml", "components[1].type 'database' is invalid"),
        ("tests/fixtures/invalid/invalid-description.yaml", "field 'description' must be a string"),
    ],
)
def test_invalid_architecture_reports_clear_error(path: str, message: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        load_validated_architecture(path)

    assert message in str(excinfo.value)


def test_collect_validation_warnings_detects_endpoint_and_gateway_patterns() -> None:
    data = {
        "name": "warning-case",
        "components": [
            {"name": "laptop-a", "type": "endpoint"},
            {"name": "laptop-b", "type": "endpoint"},
            {"name": "vpn-gateway", "type": "access-gateway"},
        ],
        "flows": [
            {"from": "laptop-a", "to": "laptop-b", "label": "peer sync"},
        ],
    }

    warnings = collect_validation_warnings(data)

    assert "endpoint-to-endpoint flow detected (laptop-a -> laptop-b)" in warnings
    assert "only one access-gateway detected (vpn-gateway)" in warnings


def test_collect_validation_warnings_detects_mfa_target_mismatch() -> None:
    data = {
        "name": "warning-case",
        "components": [
            {"name": "user-device", "type": "endpoint"},
            {"name": "app", "type": "application"},
        ],
        "flows": [
            {"from": "user-device", "to": "app", "label": "sign-in", "authentication": "mfa"},
        ],
    }

    warnings = collect_validation_warnings(data)

    assert "MFA flow target should be an identity component (user-device -> app)" in warnings


def test_load_validation_result_returns_architecture_and_warnings(tmp_path: Path) -> None:
    path = tmp_path / "warning-case.yaml"
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

    result = load_validation_result(path)

    assert result.architecture.name == "warning-case"
    assert result.warnings == ["endpoint-to-endpoint flow detected (laptop-a -> laptop-b)"]
