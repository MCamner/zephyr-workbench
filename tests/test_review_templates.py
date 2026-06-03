"""Tests for zephyr/review_templates.py and runtime template functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from zephyr.intelligence import Finding
from zephyr.models import (
    Architecture, Component, Control, Flow, Meta, Risk, TrustBoundary,
)
from zephyr.review_templates import (
    ReviewTemplate,
    ReviewTemplateResult,
    format_review_template_result,
    format_template_list,
    get_review_template,
    list_review_templates,
    review_with_template,
)
from zephyr.runtime import list_templates_model, review_template_model


EXAMPLES = Path(__file__).parent.parent / "examples"


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _secure_arch() -> Architecture:
    """A reasonably well-structured architecture."""
    return Architecture(
        name="secure",
        meta=Meta(owner="team", version="1.0", criticality="high"),
        components=[
            Component(name="gw", type="access-gateway", criticality="high",
                      description="Gateway", lifecycle="active"),
            Component(name="idp", type="identity-provider", criticality="high",
                      description="IdP", lifecycle="active", trust_boundary="internal"),
            Component(name="api", type="service", criticality="medium",
                      description="API", lifecycle="active", trust_boundary="internal"),
            Component(name="ext", type="endpoint", criticality="low",
                      description="External client", exposure="external",
                      lifecycle="active", trust_boundary="external"),
        ],
        flows=[
            Flow(source="ext", target="gw", authentication="oauth2", encryption="tls"),
            Flow(source="gw", target="api", authentication="jwt", encryption="tls"),
            Flow(source="api", target="idp", authentication="jwt", encryption="tls"),
        ],
        controls=[
            Control(name="mfa", type="technical", applies_to=["gw", "api", "idp"],
                    description="MFA enforcement"),
        ],
        risks=[
            Risk(id="R01", title="Auth bypass", severity="high",
                 mitigation="Covered by mfa", likelihood="low", impact="high"),
        ],
        trust_boundaries=[TrustBoundary(name="internal"), TrustBoundary(name="external")],
    )


def _insecure_arch() -> Architecture:
    """An architecture with many problems."""
    return Architecture(
        name="insecure",
        components=[
            Component(name="api", type="service"),
            Component(name="db", type="data-store"),
            Component(name="ext", type="endpoint", exposure="external"),
        ],
        flows=[
            Flow(source="ext", target="api"),
            Flow(source="ext", target="db"),   # bypasses any gateway
            Flow(source="api", target="db"),
        ],
        risks=[
            Risk(id="R01", title="Unauth access", severity="high"),  # no mitigation
        ],
    )


def _resilient_arch() -> Architecture:
    return Architecture(
        name="resilient",
        components=[
            Component(name="a", type="service", lifecycle="active", criticality="high",
                      description="Service A"),
            Component(name="b", type="service", lifecycle="active", criticality="medium",
                      description="Service B"),
            Component(name="c", type="service", lifecycle="active", criticality="low",
                      description="Service C"),
        ],
        flows=[
            Flow(source="a", target="b"),
            Flow(source="b", target="c"),
        ],
    )


def _compliance_arch() -> Architecture:
    return Architecture(
        name="compliant",
        meta=Meta(owner="team", version="1.0", criticality="high"),
        components=[
            Component(name="api", type="service", criticality="high",
                      description="Main API", lifecycle="active"),
        ],
        risks=[
            Risk(id="R01", title="Risk", severity="medium",
                 mitigation="Handled", likelihood="low", impact="medium"),
        ],
        controls=[
            Control(name="ctrl", type="technical", applies_to=["api"],
                    description="Control description"),
        ],
    )


# ── list_review_templates ─────────────────────────────────────────────────────

def test_list_returns_four_templates() -> None:
    templates = list_review_templates()
    assert len(templates) == 4


def test_list_template_names() -> None:
    names = {t.name for t in list_review_templates()}
    assert names == {"security", "zero-trust", "resilience", "compliance"}


def test_each_template_has_description() -> None:
    for t in list_review_templates():
        assert t.description


def test_each_template_has_checklist() -> None:
    for t in list_review_templates():
        assert len(t.checklist) >= 3


def test_each_template_has_focus_areas() -> None:
    for t in list_review_templates():
        assert len(t.focus_areas) >= 2


# ── get_review_template ───────────────────────────────────────────────────────

def test_get_known_template() -> None:
    tmpl = get_review_template("security")
    assert isinstance(tmpl, ReviewTemplate)
    assert tmpl.name == "security"


def test_get_unknown_template_returns_none() -> None:
    assert get_review_template("nonexistent") is None


# ── review_with_template return type ─────────────────────────────────────────

def test_returns_review_template_result() -> None:
    result = review_with_template(_secure_arch(), "security")
    assert isinstance(result, ReviewTemplateResult)


def test_unknown_template_raises() -> None:
    with pytest.raises(ValueError, match="Unknown review template"):
        review_with_template(_secure_arch(), "bogus")


# ── security template ─────────────────────────────────────────────────────────

def test_security_secure_arch_has_findings() -> None:
    result = review_with_template(_secure_arch(), "security")
    assert isinstance(result.template_findings, list)


def test_security_insecure_has_risk_findings() -> None:
    result = review_with_template(_insecure_arch(), "security")
    risk_codes = [f.code for f in result.template_findings if f.severity == "risk"]
    assert any("security" in c for c in risk_codes)


def test_security_unmitigated_risk_detected() -> None:
    result = review_with_template(_insecure_arch(), "security")
    codes = [f.code for f in result.template_findings]
    assert "security/unmitigated-high-risk" in codes


def test_security_no_gateway_detected() -> None:
    result = review_with_template(_insecure_arch(), "security")
    codes = [f.code for f in result.template_findings]
    assert "security/no-gateway-defined" in codes


# ── zero-trust template ───────────────────────────────────────────────────────

def test_zero_trust_no_idp_detected() -> None:
    arch = Architecture(
        name="no-idp",
        components=[Component(name="api", type="service")],
        flows=[],
    )
    result = review_with_template(arch, "zero-trust")
    codes = [f.code for f in result.template_findings]
    assert "zero-trust/no-identity-provider" in codes


def test_zero_trust_no_boundaries_detected() -> None:
    arch = Architecture(
        name="no-bounds",
        components=[Component(name="api", type="service")],
    )
    result = review_with_template(arch, "zero-trust")
    codes = [f.code for f in result.template_findings]
    assert "zero-trust/no-trust-boundaries" in codes


def test_zero_trust_unauthenticated_flow_detected() -> None:
    arch = Architecture(
        name="no-auth",
        components=[
            Component(name="ext", type="endpoint", exposure="external"),
            Component(name="api", type="service"),
        ],
        flows=[Flow(source="ext", target="api")],  # no authentication
    )
    result = review_with_template(arch, "zero-trust")
    codes = [f.code for f in result.template_findings]
    assert "zero-trust/unauthenticated-external-flow" in codes


# ── resilience template ───────────────────────────────────────────────────────

def test_resilience_deprecated_in_use_detected() -> None:
    arch = Architecture(
        name="deprecated",
        components=[
            Component(name="active", type="service", lifecycle="active"),
            Component(name="old", type="service", lifecycle="deprecated"),
        ],
        flows=[Flow(source="active", target="old")],
    )
    result = review_with_template(arch, "resilience")
    codes = [f.code for f in result.template_findings]
    assert "resilience/deprecated-in-use" in codes


def test_resilience_isolated_critical_detected() -> None:
    arch = Architecture(
        name="isolated",
        components=[
            Component(name="active", type="service", lifecycle="active",
                      criticality="high"),
            Component(name="isolated", type="service", lifecycle="active",
                      criticality="high"),
        ],
        flows=[Flow(source="active", target="active")],
    )
    result = review_with_template(arch, "resilience")
    codes = [f.code for f in result.template_findings]
    assert "resilience/critical-component-isolated" in codes


def test_resilience_clean_arch_no_critical_findings() -> None:
    result = review_with_template(_resilient_arch(), "resilience")
    critical = [f for f in result.template_findings if f.severity == "risk"]
    assert len(critical) == 0


# ── compliance template ───────────────────────────────────────────────────────

def test_compliance_no_meta_detected() -> None:
    arch = Architecture(name="no-meta", components=[Component(name="a", type="service")])
    result = review_with_template(arch, "compliance")
    codes = [f.code for f in result.template_findings]
    assert "compliance/no-meta" in codes


def test_compliance_missing_mitigation_detected() -> None:
    arch = Architecture(
        name="bad-risks",
        risks=[Risk(id="R01", title="Risk", severity="high")],  # no mitigation
    )
    result = review_with_template(arch, "compliance")
    codes = [f.code for f in result.template_findings]
    assert "compliance/risk-missing-mitigation" in codes


def test_compliance_clean_arch_no_warnings() -> None:
    result = review_with_template(_compliance_arch(), "compliance")
    bad = [f for f in result.template_findings if f.severity in ("risk", "warning")]
    assert len(bad) == 0


# ── ReviewTemplateResult properties ──────────────────────────────────────────

def test_all_findings_combines_both_lists() -> None:
    result = review_with_template(_insecure_arch(), "security")
    total = len(result.template_findings) + len(result.generic_findings)
    assert len(result.all_findings) == total


def test_all_findings_sorted_by_severity() -> None:
    result = review_with_template(_insecure_arch(), "security")
    severities = [f.severity for f in result.all_findings]
    order = {"risk": 0, "warning": 1, "suggestion": 2, "note": 3}
    ranks = [order.get(s, 99) for s in severities]
    assert ranks == sorted(ranks)


def test_summary_non_empty() -> None:
    result = review_with_template(_insecure_arch(), "security")
    assert len(result.summary) > 0
    assert "security" in result.summary


# ── to_dict serialization ─────────────────────────────────────────────────────

def test_to_dict_has_required_keys() -> None:
    d = review_with_template(_insecure_arch(), "security").to_dict()
    for key in ("template", "description", "summary", "template_findings",
                "generic_findings", "all_findings", "checklist", "counts"):
        assert key in d


def test_to_dict_checklist_non_empty() -> None:
    d = review_with_template(_secure_arch(), "security").to_dict()
    assert len(d["checklist"]) > 0


def test_to_dict_counts_all_severities() -> None:
    d = review_with_template(_secure_arch(), "security").to_dict()
    for s in ("risk", "warning", "suggestion", "note"):
        assert s in d["counts"]


# ── format functions ──────────────────────────────────────────────────────────

def test_format_result_returns_string() -> None:
    result = review_with_template(_insecure_arch(), "security")
    text = format_review_template_result(result, "insecure")
    assert isinstance(text, str)


def test_format_result_contains_template_name() -> None:
    result = review_with_template(_insecure_arch(), "security")
    text = format_review_template_result(result, "insecure")
    assert "security" in text


def test_format_result_contains_checklist() -> None:
    result = review_with_template(_insecure_arch(), "security")
    text = format_review_template_result(result, "insecure")
    assert "Checklist" in text


def test_format_template_list_contains_all_names() -> None:
    text = format_template_list()
    for name in ("security", "zero-trust", "resilience", "compliance"):
        assert name in text


# ── runtime functions ─────────────────────────────────────────────────────────

def test_runtime_review_template_ok() -> None:
    result = review_template_model(EXAMPLES / "identity-flow.yaml", "security")
    assert result.ok or result.status == "warning"


def test_runtime_review_template_command() -> None:
    result = review_template_model(EXAMPLES / "identity-flow.yaml", "security")
    assert result.command == "review"


def test_runtime_review_template_data_has_template() -> None:
    result = review_template_model(EXAMPLES / "identity-flow.yaml", "security")
    assert "template" in result.data
    assert result.data["template"] == "security"


def test_runtime_review_template_data_has_checklist() -> None:
    result = review_template_model(EXAMPLES / "identity-flow.yaml", "security")
    assert "checklist" in result.data
    assert len(result.data["checklist"]) > 0


def test_runtime_review_template_unknown_name_error() -> None:
    result = review_template_model(EXAMPLES / "identity-flow.yaml", "bogus")
    assert result.failed


def test_runtime_review_template_missing_file_error() -> None:
    result = review_template_model("nonexistent.yaml", "security")
    assert result.failed


def test_runtime_all_templates_run_on_example() -> None:
    for name in ("security", "zero-trust", "resilience", "compliance"):
        result = review_template_model(EXAMPLES / "identity-flow.yaml", name)
        assert not result.failed, f"Template '{name}' failed: {result.errors}"


def test_runtime_list_templates_ok() -> None:
    result = list_templates_model()
    assert result.ok


def test_runtime_list_templates_data_has_four() -> None:
    result = list_templates_model()
    assert len(result.data["templates"]) == 4


def test_runtime_list_templates_each_has_name() -> None:
    result = list_templates_model()
    for t in result.data["templates"]:
        assert "name" in t
        assert "checklist" in t
