import pytest

from zephyr.validation import ValidationError, load_validated_architecture


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
