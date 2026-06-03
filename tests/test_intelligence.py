"""Tests for zephyr/intelligence.py and v0.3.0 CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from zephyr.intelligence import (
    ArchitectureAnalysis,
    Finding,
    analyze_architecture,
    analyze_risks,
    dependency_insights,
    detect_antipatterns,
    explain_risk,
    narrative_summary,
    review_architecture,
    suggest_improvements,
)
from zephyr.loader import architecture_from_data
from zephyr.runtime import analyze_model, explain_risk_model, review_model
from tests.test_cli import run_cli


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _arch(data: dict):
    from zephyr.validation import validate_architecture_data
    validate_architecture_data(data)
    return architecture_from_data(data)


@pytest.fixture
def simple_arch():
    return _arch({
        "name": "test-arch",
        "components": [
            {"name": "client", "type": "endpoint", "exposure": "external"},
            {"name": "gateway", "type": "access-gateway"},
            {"name": "api", "type": "application", "criticality": "high"},
        ],
        "flows": [
            {"from": "client", "to": "gateway", "label": "auth", "authentication": "mfa", "encryption": "tls"},
            {"from": "gateway", "to": "api", "label": "proxy", "encryption": "tls"},
        ],
    })


@pytest.fixture
def risky_arch():
    """Architecture with known anti-patterns."""
    return _arch({
        "name": "risky-arch",
        "components": [
            {"name": "laptop", "type": "endpoint", "exposure": "external"},
            {"name": "gateway", "type": "access-gateway"},
            {"name": "db", "type": "on-prem-resource", "criticality": "high"},
            {"name": "idp", "type": "identity-provider"},
        ],
        "flows": [
            {"from": "laptop", "to": "db", "label": "direct"},   # bypass!
            {"from": "laptop", "to": "gateway", "label": "web"},
        ],
        "risks": [
            {"id": "R1", "title": "SQL injection", "severity": "high"},  # no mitigation
        ],
    })


# ── detect_antipatterns ───────────────────────────────────────────────────────

def test_detect_antipatterns_clean_arch(simple_arch) -> None:
    findings = detect_antipatterns(simple_arch)
    codes = {f.code for f in findings}
    # client routes through gateway — no bypass
    assert "external-endpoint-unrestricted" not in codes


def test_detect_antipatterns_external_bypass(risky_arch) -> None:
    findings = detect_antipatterns(risky_arch)
    codes = {f.code for f in findings}
    assert "external-endpoint-unrestricted" in codes
    bypass = next(f for f in findings if f.code == "external-endpoint-unrestricted")
    assert "laptop" in bypass.affected
    assert bypass.severity == "risk"


def test_detect_antipatterns_identity_provider_unused(risky_arch) -> None:
    findings = detect_antipatterns(risky_arch)
    codes = {f.code for f in findings}
    assert "identity-provider-unused" in codes


def test_detect_antipatterns_critical_uncontrolled(risky_arch) -> None:
    findings = detect_antipatterns(risky_arch)
    codes = {f.code for f in findings}
    assert "critical-component-uncontrolled" in codes
    f = next(x for x in findings if x.code == "critical-component-uncontrolled")
    assert "db" in f.affected


def test_detect_antipatterns_risk_definition_incomplete(risky_arch) -> None:
    findings = detect_antipatterns(risky_arch)
    codes = {f.code for f in findings}
    assert "risk-definition-incomplete" in codes
    f = next(x for x in findings if x.code == "risk-definition-incomplete")
    assert "R1" in f.affected


def test_detect_antipatterns_sorted_by_severity(risky_arch) -> None:
    findings = detect_antipatterns(risky_arch)
    severities = [f.severity for f in findings]
    order = {"risk": 0, "warning": 1, "suggestion": 2, "note": 3}
    assert severities == sorted(severities, key=lambda s: order.get(s, 99))


# ── suggest_improvements ──────────────────────────────────────────────────────

def test_suggest_improvements_unmitigated_risk(risky_arch) -> None:
    suggestions = suggest_improvements(risky_arch)
    codes = {f.code for f in suggestions}
    assert "add-risk-mitigation" in codes
    f = next(x for x in suggestions if x.code == "add-risk-mitigation")
    assert "R1" in f.affected


def test_suggest_improvements_no_issues(simple_arch) -> None:
    suggestions = suggest_improvements(simple_arch)
    # simple_arch has no high risks without mitigation
    codes = {f.code for f in suggestions}
    assert "add-risk-mitigation" not in codes


# ── analyze_risks ─────────────────────────────────────────────────────────────

def test_analyze_risks_empty(simple_arch) -> None:
    result = analyze_risks(simple_arch)
    assert result["total"] == 0
    assert result["unmitigated"] == []
    assert result["unmitigated_high_critical"] == []


def test_analyze_risks_with_risk(risky_arch) -> None:
    result = analyze_risks(risky_arch)
    assert result["total"] == 1
    assert "R1" in result["unmitigated"]
    assert "R1" in result["unmitigated_high_critical"]
    assert "R1" in result["incomplete_definitions"]
    assert "R1" not in result["fully_defined"]


# ── explain_risk ──────────────────────────────────────────────────────────────

def test_explain_risk_found(risky_arch) -> None:
    ctx = explain_risk(risky_arch, "R1")
    assert ctx is not None
    assert ctx.risk_id == "R1"
    assert ctx.title == "SQL injection"
    assert ctx.severity == "high"
    assert ctx.mitigation == ""
    assert "unmitigated" in ctx.explanation.lower()


def test_explain_risk_not_found(simple_arch) -> None:
    ctx = explain_risk(simple_arch, "NONEXISTENT")
    assert ctx is None


# ── dependency_insights ───────────────────────────────────────────────────────

def test_dependency_insights_external_reach(risky_arch) -> None:
    di = dependency_insights(risky_arch)
    assert "laptop" in di.external_reachable
    reachable = di.external_reachable["laptop"]
    assert "db" in reachable or "gateway" in reachable


def test_dependency_insights_no_external(simple_arch) -> None:
    # simple_arch has external=client
    di = dependency_insights(simple_arch)
    assert "client" in di.external_reachable


def test_dependency_insights_hub_components(risky_arch) -> None:
    di = dependency_insights(risky_arch)
    hub_names = [name for name, _ in di.hub_components]
    assert isinstance(hub_names, list)


# ── narrative_summary ─────────────────────────────────────────────────────────

def test_narrative_summary_contains_name(simple_arch) -> None:
    text = narrative_summary(simple_arch)
    assert "test-arch" in text


def test_narrative_summary_mentions_external(risky_arch) -> None:
    text = narrative_summary(risky_arch)
    assert "external" in text.lower() or "laptop" in text


def test_narrative_summary_mentions_risk(risky_arch) -> None:
    text = narrative_summary(risky_arch)
    assert "risk" in text.lower()


# ── review_architecture ───────────────────────────────────────────────────────

def test_review_architecture_returns_sorted_findings(risky_arch) -> None:
    findings = review_architecture(risky_arch)
    assert isinstance(findings, list)
    order = {"risk": 0, "warning": 1, "suggestion": 2, "note": 3}
    severities = [f.severity for f in findings]
    assert severities == sorted(severities, key=lambda s: order.get(s, 99))


def test_review_architecture_clean_has_fewer_findings(simple_arch, risky_arch) -> None:
    clean = review_architecture(simple_arch)
    risky = review_architecture(risky_arch)
    assert len(risky) > len(clean)


# ── analyze_architecture ──────────────────────────────────────────────────────

def test_analyze_architecture_shape(simple_arch) -> None:
    analysis = analyze_architecture(simple_arch)
    assert isinstance(analysis, ArchitectureAnalysis)
    assert isinstance(analysis.antipatterns, list)
    assert isinstance(analysis.suggestions, list)
    assert isinstance(analysis.risk_analysis, dict)
    assert isinstance(analysis.narrative, str)
    assert "total" in analysis.risk_analysis


def test_analyze_architecture_has_blocking_risky(risky_arch) -> None:
    analysis = analyze_architecture(risky_arch)
    assert analysis.has_blocking() is True


def test_analyze_architecture_no_blocking_clean(simple_arch) -> None:
    analysis = analyze_architecture(simple_arch)
    assert analysis.has_blocking() is False


# ── Runtime API ───────────────────────────────────────────────────────────────

def test_analyze_model_ok(tmp_path: Path) -> None:
    data = {
        "name": "clean",
        "components": [
            {"name": "svc", "type": "application"},
            {"name": "db", "type": "on-prem-resource"},
        ],
        "flows": [{"from": "svc", "to": "db", "label": "query"}],
    }
    p = tmp_path / "clean.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    result = analyze_model(p)
    assert result.status in ("ok", "warning")
    assert result.command == "analyze"
    assert "narrative" in result.data
    assert "antipatterns" in result.data
    assert "risk_analysis" in result.data


def test_analyze_model_warning_on_blocking(tmp_path: Path) -> None:
    data = {
        "name": "risky",
        "components": [
            {"name": "user", "type": "endpoint", "exposure": "external"},
            {"name": "gw", "type": "access-gateway"},
            {"name": "db", "type": "on-prem-resource"},
        ],
        "flows": [
            {"from": "user", "to": "db", "label": "bypass"},  # anti-pattern
            {"from": "user", "to": "gw", "label": "safe"},
        ],
    }
    p = tmp_path / "risky.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    result = analyze_model(p)
    assert result.status == "warning"


def test_review_model_returns_findings(tmp_path: Path) -> None:
    data = {
        "name": "arch",
        "components": [{"name": "svc", "type": "application"}],
        "flows": [],
        "risks": [{"id": "R1", "title": "Risk", "severity": "high"}],
    }
    p = tmp_path / "arch.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    result = review_model(p)
    assert result.ok
    assert "findings" in result.data
    assert "counts" in result.data
    assert isinstance(result.data["findings"], list)


def test_explain_risk_model_found() -> None:
    result = explain_risk_model("examples/identity-flow.yaml", "R1")
    assert result.status == "ok"
    assert result.data["risk_id"] == "R1"
    assert "explanation" in result.data


def test_explain_risk_model_not_found() -> None:
    result = explain_risk_model("examples/identity-flow.yaml", "NOPE")
    assert result.status == "error"
    assert any("not found" in e for e in result.errors)


# ── CLI integration ───────────────────────────────────────────────────────────

def test_cli_analyze_human_output() -> None:
    result = run_cli("analyze", "examples/identity-flow.yaml")
    assert result.returncode == 0
    assert "Architecture Analysis:" in result.stdout
    assert "identity-flow" in result.stdout


def test_cli_analyze_json_output() -> None:
    result = run_cli("analyze", "examples/identity-flow.yaml", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["metadata"]["command"] == "analyze"
    assert payload["metadata"]["schema_version"] == "zephyr-result.v1"
    assert "narrative" in payload["data"]
    assert "antipatterns" in payload["data"]
    assert "risk_analysis" in payload["data"]


def test_cli_review_human_output() -> None:
    result = run_cli("review", "examples/identity-flow.yaml")
    assert result.returncode == 0
    assert "Architecture Review:" in result.stdout


def test_cli_review_json_output() -> None:
    result = run_cli("review", "examples/identity-flow.yaml", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["metadata"]["command"] == "review"
    assert "findings" in payload["data"]
    assert "counts" in payload["data"]


def test_cli_explain_human_output() -> None:
    result = run_cli("explain", "examples/identity-flow.yaml", "R1")
    assert result.returncode == 0
    assert "R1" in result.stdout


def test_cli_explain_json_output() -> None:
    result = run_cli("explain", "examples/identity-flow.yaml", "R1", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["metadata"]["command"] == "explain"
    assert payload["data"]["risk_id"] == "R1"
    assert "explanation" in payload["data"]


def test_cli_explain_missing_risk() -> None:
    result = run_cli("explain", "examples/identity-flow.yaml", "NOPE")
    assert result.returncode == 1


# ── Search: has: and no: syntax ───────────────────────────────────────────────

def test_search_has_syntax() -> None:
    result = run_cli("search", "examples/secure-workplace.yaml", "has:description")
    assert result.returncode == 0


def test_search_no_syntax() -> None:
    result = run_cli("search", "examples/secure-workplace.yaml", "no:description")
    assert result.returncode == 0


def test_search_has_json() -> None:
    result = run_cli("search", "examples/identity-flow.yaml", "has:authentication", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
