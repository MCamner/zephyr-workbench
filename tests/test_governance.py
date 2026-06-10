"""Tests for zephyr/governance.py and runtime.govern_model()."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from zephyr.governance import (
    GovernancePolicy,
    GovernancePolicyError,
    GovernanceResult,
    GovernanceViolation,
    check_governance,
    format_governance_result,
    load_governance_policy,
)
from zephyr.models import (
    Architecture, Component, Control, Flow, Meta, Risk, TrustBoundary,
)
from zephyr.runtime import govern_model


EXAMPLES = Path(__file__).parent.parent / "examples"
EXAMPLE_POLICY = EXAMPLES / "governance-policy.yaml"


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _write_policy(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "policy.yaml"
    p.write_text(dedent(content), encoding="utf-8")
    return p


def _secure_arch() -> Architecture:
    return Architecture(
        name="secure",
        meta=Meta(owner="team", version="1.0", criticality="high"),
        components=[
            Component(name="gw", type="access-gateway", criticality="high",
                      description="Gateway", lifecycle="active"),
            Component(name="api", type="service", criticality="high",
                      description="API", lifecycle="active", trust_boundary="internal"),
            Component(name="ext", type="endpoint", criticality="low",
                      description="External", exposure="external",
                      lifecycle="active", trust_boundary="external"),
        ],
        flows=[
            Flow(source="ext", target="gw", authentication="oauth2", encryption="tls"),
            Flow(source="gw", target="api", authentication="jwt", encryption="tls"),
        ],
        controls=[
            Control(name="mfa", type="technical", applies_to=["gw", "api"],
                    description="MFA"),
        ],
        risks=[
            Risk(id="R01", title="Risk", severity="high",
                 mitigation="Mitigated", likelihood="low", impact="high"),
        ],
        trust_boundaries=[
            TrustBoundary(name="internal"), TrustBoundary(name="external"),
        ],
    )


def _bare_arch() -> Architecture:
    return Architecture(
        name="bare",
        components=[
            Component(name="api", type="service"),
            Component(name="ext", type="endpoint", exposure="external"),
        ],
        flows=[Flow(source="ext", target="api")],
        risks=[Risk(id="R01", title="Risk", severity="high")],
    )


# ── load_governance_policy ────────────────────────────────────────────────────

def test_load_example_policy(tmp_path):
    policy = load_governance_policy(EXAMPLE_POLICY)
    assert isinstance(policy, GovernancePolicy)


def test_load_policy_name(tmp_path):
    policy = load_governance_policy(EXAMPLE_POLICY)
    assert "Enterprise" in policy.name


def test_load_policy_version(tmp_path):
    policy = load_governance_policy(EXAMPLE_POLICY)
    assert policy.version == "1.0"


def test_load_policy_rules_count(tmp_path):
    policy = load_governance_policy(EXAMPLE_POLICY)
    assert len(policy.rules) >= 5


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(GovernancePolicyError, match="not found"):
        load_governance_policy(tmp_path / "nonexistent.yaml")


def test_load_invalid_yaml_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("key: [unclosed", encoding="utf-8")
    with pytest.raises(GovernancePolicyError, match="Invalid YAML"):
        load_governance_policy(bad)


def test_load_non_mapping_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(GovernancePolicyError):
        load_governance_policy(bad)


def test_load_default_severity_applied(tmp_path):
    p = _write_policy(tmp_path, """
        name: test
        default_severity: warning
        rules:
          - id: R01
            description: desc
            type: require_meta
    """)
    policy = load_governance_policy(p)
    assert policy.rules[0].severity == "warning"


def test_load_rule_severity_override(tmp_path):
    p = _write_policy(tmp_path, """
        name: test
        default_severity: error
        rules:
          - id: R01
            description: desc
            type: require_meta
            severity: warning
    """)
    policy = load_governance_policy(p)
    assert policy.rules[0].severity == "warning"


# ── check_governance — require_meta ──────────────────────────────────────────

def test_require_meta_passes_when_meta_present(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: meta required
            type: require_meta
    """)
    policy = load_governance_policy(p)
    result = check_governance(_secure_arch(), policy)
    assert "G01" in result.passed_rule_ids


def test_require_meta_fails_when_absent(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: meta required
            type: require_meta
    """)
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    assert any(v.rule_id == "G01" for v in result.violations)


# ── require_meta_field ────────────────────────────────────────────────────────

def test_require_meta_field_passes(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: owner required
            type: require_meta_field
            field: owner
    """)
    policy = load_governance_policy(p)
    result = check_governance(_secure_arch(), policy)
    assert "G01" in result.passed_rule_ids


def test_require_meta_field_fails_no_meta(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: owner required
            type: require_meta_field
            field: owner
    """)
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    assert any(v.rule_id == "G01" for v in result.violations)


# ── require_component_type ────────────────────────────────────────────────────

def test_require_component_type_passes(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: gateway required
            type: require_component_type
            component_type: access-gateway
    """)
    policy = load_governance_policy(p)
    result = check_governance(_secure_arch(), policy)
    assert "G01" in result.passed_rule_ids


def test_require_component_type_fails(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: gateway required
            type: require_component_type
            component_type: access-gateway
    """)
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    assert any(v.rule_id == "G01" for v in result.violations)


# ── require_trust_boundaries ──────────────────────────────────────────────────

def test_require_trust_boundaries_passes(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: trust boundaries
            type: require_trust_boundaries
    """)
    policy = load_governance_policy(p)
    result = check_governance(_secure_arch(), policy)
    assert "G01" in result.passed_rule_ids


def test_require_trust_boundaries_fails(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: trust boundaries
            type: require_trust_boundaries
    """)
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    assert any(v.rule_id == "G01" for v in result.violations)


# ── prohibit_external_bypass ──────────────────────────────────────────────────

def test_prohibit_external_bypass_passes(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: no bypass
            type: prohibit_external_bypass
    """)
    policy = load_governance_policy(p)
    result = check_governance(_secure_arch(), policy)
    assert "G01" in result.passed_rule_ids


def test_prohibit_external_bypass_fails_direct_flow(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: no bypass
            type: prohibit_external_bypass
    """)
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    assert any(v.rule_id == "G01" for v in result.violations)


def test_prohibit_external_bypass_passes_no_external(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: no bypass
            type: prohibit_external_bypass
    """)
    policy = load_governance_policy(p)
    arch = Architecture(
        name="internal",
        components=[Component(name="a", type="service"), Component(name="b", type="service")],
        flows=[Flow(source="a", target="b")],
    )
    result = check_governance(arch, policy)
    assert "G01" in result.passed_rule_ids


# ── require_field ─────────────────────────────────────────────────────────────

def test_require_field_components_passes(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: desc required
            type: require_field
            target: components
            field: description
    """)
    policy = load_governance_policy(p)
    result = check_governance(_secure_arch(), policy)
    assert "G01" in result.passed_rule_ids


def test_require_field_components_fails(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: desc required
            type: require_field
            target: components
            field: description
    """)
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    assert any(v.rule_id == "G01" for v in result.violations)


def test_require_field_risks_mitigation_fails(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: mitigation required
            type: require_field
            target: risks
            field: mitigation
    """)
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    assert any(v.rule_id == "G01" for v in result.violations)


def test_require_field_risks_mitigation_passes(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: mitigation required
            type: require_field
            target: risks
            field: mitigation
    """)
    policy = load_governance_policy(p)
    result = check_governance(_secure_arch(), policy)
    assert "G01" in result.passed_rule_ids


# ── require_control_coverage ──────────────────────────────────────────────────

def test_require_control_coverage_high_criticality_passes(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: control coverage for critical components
            type: require_control_coverage
            target: high_criticality
    """)
    policy = load_governance_policy(p)
    result = check_governance(_secure_arch(), policy)
    assert "G01" in result.passed_rule_ids


def test_require_control_coverage_all_fails(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: control coverage
            type: require_control_coverage
            target: all
    """)
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    assert any(v.rule_id == "G01" for v in result.violations)


def test_require_control_coverage_high_criticality(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: control coverage for critical
            type: require_control_coverage
            target: high_criticality
    """)
    policy = load_governance_policy(p)
    arch = Architecture(
        name="test",
        components=[
            Component(name="api", type="service", criticality="high"),
            Component(name="db", type="data-store", criticality="low"),
        ],
    )
    result = check_governance(arch, policy)
    assert any(v.rule_id == "G01" for v in result.violations)
    v = next(v for v in result.violations if v.rule_id == "G01")
    assert "api" in v.affected


# ── GovernanceResult ─────────────────────────────────────────────────────────

def test_result_status_passed_when_no_violations(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: meta
            type: require_meta
    """)
    policy = load_governance_policy(p)
    result = check_governance(_secure_arch(), policy)
    assert result.status == "passed"


def test_result_status_failed_on_error_violation(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: gateway
            type: require_component_type
            component_type: access-gateway
            severity: error
    """)
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    assert result.status == "failed"
    assert result.has_errors


def test_result_status_passed_on_only_warning_violations(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: gateway
            type: require_component_type
            component_type: access-gateway
            severity: warning
    """)
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    assert result.status == "passed"
    assert not result.has_errors
    assert len(result.violations) == 1


def test_result_to_dict_keys(tmp_path):
    p = _write_policy(tmp_path, "name: t\nrules:\n  - id: G01\n    description: d\n    type: require_meta\n")
    policy = load_governance_policy(p)
    d = check_governance(_bare_arch(), policy).to_dict()
    for key in ("policy_name", "policy_version", "status", "violations",
                "passed_rule_ids", "counts"):
        assert key in d


def test_violation_to_dict_keys(tmp_path):
    p = _write_policy(tmp_path, "name: t\nrules:\n  - id: G01\n    description: d\n    type: require_meta\n")
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    assert result.violations
    d = result.violations[0].to_dict()
    for key in ("rule_id", "description", "severity", "message", "affected"):
        assert key in d


# ── format_governance_result ──────────────────────────────────────────────────

def test_format_returns_string(tmp_path):
    p = _write_policy(tmp_path, "name: t\nrules:\n  - id: G01\n    description: d\n    type: require_meta\n")
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    text = format_governance_result(result, str(p), "bare")
    assert isinstance(text, str)


def test_format_shows_failed_status(tmp_path):
    p = _write_policy(tmp_path, "name: t\nrules:\n  - id: G01\n    description: d\n    type: require_meta\n")
    policy = load_governance_policy(p)
    result = check_governance(_bare_arch(), policy)
    text = format_governance_result(result, str(p), "bare")
    assert "FAILED" in text


def test_format_shows_passed_status(tmp_path):
    p = _write_policy(tmp_path, "name: t\nrules:\n  - id: G01\n    description: d\n    type: require_meta\n")
    policy = load_governance_policy(p)
    result = check_governance(_secure_arch(), policy)
    text = format_governance_result(result, str(p), "secure")
    assert "PASSED" in text


# ── runtime.govern_model ──────────────────────────────────────────────────────

def test_runtime_govern_ok_on_passing_arch():
    result = govern_model(EXAMPLES / "identity-flow.yaml", EXAMPLE_POLICY)
    assert result.status in ("ok", "warning", "error")
    assert result.command == "govern"


def test_runtime_govern_data_has_status():
    result = govern_model(EXAMPLES / "identity-flow.yaml", EXAMPLE_POLICY)
    assert "status" in result.data


def test_runtime_govern_data_has_violations():
    result = govern_model(EXAMPLES / "identity-flow.yaml", EXAMPLE_POLICY)
    assert "violations" in result.data


def test_runtime_govern_missing_arch_error():
    result = govern_model("nonexistent.yaml", EXAMPLE_POLICY)
    assert result.failed


def test_runtime_govern_missing_policy_error():
    result = govern_model(EXAMPLES / "identity-flow.yaml", "nonexistent-policy.yaml")
    assert result.failed


def test_runtime_govern_returns_structured_data(tmp_path):
    p = _write_policy(tmp_path, """
        name: t
        rules:
          - id: G01
            description: at least one service
            type: require_component_type
            component_type: service
    """)
    arch_file = EXAMPLES / "identity-flow.yaml"
    result = govern_model(arch_file, p)
    assert "counts" in result.data
    assert "violations" in result.data
