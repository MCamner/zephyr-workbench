"""Tests for zephyr/impact.py and runtime.impact_models()."""

from __future__ import annotations

from pathlib import Path

from zephyr.diff import diff_architectures
from zephyr.impact import (
    ChangeImpactReport,
    ComponentImpact,
    ControlCoverageChange,
    analyze_impact,
    format_impact,
)
from zephyr.models import Architecture, Component, Control, Flow, Risk
from zephyr.runtime import impact_models


EXAMPLES = Path(__file__).parent.parent / "examples"


# ── Fixture helpers ───────────────────────────────────────────────────────────

def _base() -> Architecture:
    return Architecture(
        name="base",
        components=[
            Component(name="gw", type="access-gateway", criticality="high"),
            Component(name="api", type="service", criticality="medium"),
            Component(name="db", type="data-store", criticality="high"),
        ],
        flows=[
            Flow(source="gw", target="api"),
            Flow(source="api", target="db"),
        ],
        controls=[
            Control(name="mfa", type="technical", applies_to=["gw", "api"]),
        ],
        risks=[
            Risk(id="R01", title="Unauth access", severity="high",
                 mitigation="Covered by mfa control"),
        ],
    )


def _no_changes() -> Architecture:
    return _base()


def _gateway_removed() -> Architecture:
    arch = _base()
    arch.components = [c for c in arch.components if c.name != "gw"]
    arch.flows = [f for f in arch.flows if f.source != "gw" and f.target != "gw"]
    return arch


def _control_removed() -> Architecture:
    arch = _base()
    arch.controls = []
    return arch


def _component_added() -> Architecture:
    arch = _base()
    arch.components.append(Component(name="cache", type="service", criticality="low"))
    arch.flows.append(Flow(source="api", target="cache"))
    return arch


def _component_modified_crit() -> Architecture:
    arch = _base()
    for c in arch.components:
        if c.name == "api":
            c.criticality = "mission-critical"
    return arch


def _control_coverage_reduced() -> Architecture:
    arch = _base()
    for c in arch.controls:
        if c.name == "mfa":
            c.applies_to = ["gw"]   # api no longer covered
    return arch


def _run(before: Architecture, after: Architecture) -> ChangeImpactReport:
    diff = diff_architectures(before, after, source="before.yaml", target="after.yaml")
    return analyze_impact(before, after, diff)


# ── Return type ───────────────────────────────────────────────────────────────

def test_returns_change_impact_report() -> None:
    assert isinstance(_run(_base(), _no_changes()), ChangeImpactReport)


# ── No changes → severity none ────────────────────────────────────────────────

def test_no_changes_severity_none() -> None:
    report = _run(_base(), _no_changes())
    assert report.severity == "none"


def test_no_changes_empty_impacts() -> None:
    report = _run(_base(), _no_changes())
    assert report.component_impacts == []
    assert report.control_changes == []
    assert report.unmitigated_risk_ids == []


# ── Gateway removed → critical ────────────────────────────────────────────────

def test_gateway_removed_severity_critical() -> None:
    report = _run(_base(), _gateway_removed())
    assert report.severity == "critical"


def test_gateway_removed_has_component_impact() -> None:
    report = _run(_base(), _gateway_removed())
    names = [ci.component for ci in report.component_impacts]
    assert "gw" in names


def test_gateway_removed_flags_gateway() -> None:
    report = _run(_base(), _gateway_removed())
    gw_impact = next(ci for ci in report.component_impacts if ci.component == "gw")
    assert "gateway" in gw_impact.flags


def test_gateway_removed_change_type() -> None:
    report = _run(_base(), _gateway_removed())
    gw_impact = next(ci for ci in report.component_impacts if ci.component == "gw")
    assert gw_impact.change_type == "removed"


def test_gateway_removed_downstream() -> None:
    report = _run(_base(), _gateway_removed())
    gw_impact = next(ci for ci in report.component_impacts if ci.component == "gw")
    assert "api" in gw_impact.downstream


def test_gateway_removed_has_recommendation() -> None:
    report = _run(_base(), _gateway_removed())
    assert any("gw" in r for r in report.recommendations)


# ── Control removed → high/critical severity ──────────────────────────────────

def test_control_removed_severity_high_or_critical() -> None:
    report = _run(_base(), _control_removed())
    assert report.severity in ("critical", "high")


def test_control_removed_surfaces_control_change() -> None:
    report = _run(_base(), _control_removed())
    names = [cc.control for cc in report.control_changes]
    assert "mfa" in names


def test_control_removed_unprotected_components() -> None:
    report = _run(_base(), _control_removed())
    cc = next(c for c in report.control_changes if c.control == "mfa")
    assert set(cc.unprotected) == {"gw", "api"}


def test_control_removed_status_removed() -> None:
    report = _run(_base(), _control_removed())
    cc = next(c for c in report.control_changes if c.control == "mfa")
    assert cc.status == "removed"


def test_control_removed_unmitigated_risk() -> None:
    report = _run(_base(), _control_removed())
    assert "R01" in report.unmitigated_risk_ids


# ── Component added → low severity ───────────────────────────────────────────

def test_component_added_severity_low() -> None:
    report = _run(_base(), _component_added())
    assert report.severity == "low"


def test_component_added_change_type() -> None:
    report = _run(_base(), _component_added())
    added = [ci for ci in report.component_impacts if ci.change_type == "added"]
    assert any(ci.component == "cache" for ci in added)


# ── Component modified criticality → medium ───────────────────────────────────

def test_modified_criticality_severity_medium() -> None:
    report = _run(_base(), _component_modified_crit())
    assert report.severity in ("medium", "high", "critical")


def test_modified_component_in_impacts() -> None:
    report = _run(_base(), _component_modified_crit())
    names = [ci.component for ci in report.component_impacts]
    assert "api" in names


# ── Coverage reduced → control_change recorded ───────────────────────────────

def test_coverage_reduced_surfaces_change() -> None:
    report = _run(_base(), _control_coverage_reduced())
    assert any(cc.status == "coverage-reduced" for cc in report.control_changes)


def test_coverage_reduced_unprotected_api() -> None:
    report = _run(_base(), _control_coverage_reduced())
    cc = next(c for c in report.control_changes if c.control == "mfa")
    assert "api" in cc.unprotected


# ── to_dict serialization ─────────────────────────────────────────────────────

def test_to_dict_has_required_keys() -> None:
    d = _run(_base(), _gateway_removed()).to_dict()
    for key in ("source", "target", "severity", "summary",
                "component_impacts", "control_changes",
                "unmitigated_risk_ids", "recommendations"):
        assert key in d


def test_to_dict_component_impact_shape() -> None:
    d = _run(_base(), _gateway_removed()).to_dict()
    ci = next(c for c in d["component_impacts"] if c["component"] == "gw")
    for key in ("component", "change_type", "criticality", "upstream",
                "downstream", "lost_controls", "flags"):
        assert key in ci


def test_to_dict_control_change_shape() -> None:
    d = _run(_base(), _control_removed()).to_dict()
    cc = next(c for c in d["control_changes"] if c["control"] == "mfa")
    for key in ("control", "status", "previously_covered", "now_covered", "unprotected"):
        assert key in cc


# ── format_impact ─────────────────────────────────────────────────────────────

def test_format_impact_returns_string() -> None:
    report = _run(_base(), _gateway_removed())
    assert isinstance(format_impact(report), str)


def test_format_impact_contains_severity() -> None:
    report = _run(_base(), _gateway_removed())
    text = format_impact(report)
    assert "CRITICAL" in text or "critical" in text.lower()


def test_format_impact_no_changes_message() -> None:
    report = _run(_base(), _no_changes())
    text = format_impact(report)
    assert "No changes detected" in text


# ── runtime.impact_models ─────────────────────────────────────────────────────

def test_runtime_impact_models_ok_on_identical() -> None:
    result = impact_models(EXAMPLES / "identity-flow.yaml", EXAMPLES / "identity-flow.yaml")
    assert result.ok


def test_runtime_impact_models_command_field() -> None:
    result = impact_models(EXAMPLES / "identity-flow.yaml", EXAMPLES / "identity-flow.yaml")
    assert result.command == "impact"


def test_runtime_impact_models_data_has_severity() -> None:
    result = impact_models(EXAMPLES / "identity-flow.yaml", EXAMPLES / "identity-flow.yaml")
    assert "severity" in result.data
    assert result.data["severity"] in ("critical", "high", "medium", "low", "none")


def test_runtime_impact_models_error_on_missing_file() -> None:
    result = impact_models("nonexistent.yaml", EXAMPLES / "identity-flow.yaml")
    assert result.failed


def test_runtime_impact_models_data_has_recommendations() -> None:
    result = impact_models(EXAMPLES / "identity-flow.yaml", EXAMPLES / "identity-flow.yaml")
    assert "recommendations" in result.data
