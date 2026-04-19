from zephyr.validation import collect_validation_warnings


def _data(**overrides) -> dict:
    base = {
        "name": "test",
        "components": [{"name": "api", "type": "application"}],
        "flows": [],
        "risks": [],
    }
    base.update(overrides)
    return base


def test_require_component_field_generates_warning() -> None:
    data = _data(rules={"require": {"component": ["criticality"]}})
    warnings = collect_validation_warnings(data)
    assert any("criticality" in w and "api" in w for w in warnings)


def test_no_warning_when_field_present() -> None:
    data = _data(
        components=[{"name": "api", "type": "application", "criticality": "high"}],
        rules={"require": {"component": ["criticality"]}},
    )
    warnings = collect_validation_warnings(data)
    assert not any("criticality" in w for w in warnings)


def test_require_risk_field_generates_warning() -> None:
    data = _data(
        risks=[{"id": "R1", "title": "Risk", "severity": "high", "mitigation": ""}],
        rules={"require": {"risk": ["mitigation"]}},
    )
    warnings = collect_validation_warnings(data)
    assert any("mitigation" in w and "R1" in w for w in warnings)


def test_no_rules_block_produces_no_extra_warnings() -> None:
    data = _data()
    warnings = collect_validation_warnings(data)
    # only built-in warnings possible, none from rules
    assert not any("missing required field" in w for w in warnings)


def test_multiple_require_fields() -> None:
    data = _data(rules={"require": {"component": ["criticality", "domain"]}})
    warnings = collect_validation_warnings(data)
    assert any("criticality" in w for w in warnings)
    assert any("domain" in w for w in warnings)
