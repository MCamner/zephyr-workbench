"""Tests for zephyr/scoring.py — ArchitectureScore and score_architecture()."""

from __future__ import annotations

from pathlib import Path

import pytest

from zephyr.models import Architecture, Component, Control, Flow, Meta, Risk, TrustBoundary
from zephyr.scoring import ArchitectureScore, DimensionScore, score_architecture
from zephyr.runtime import score_model


EXAMPLES = Path(__file__).parent.parent / "examples"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _minimal() -> Architecture:
    return Architecture(name="minimal")


def _well_defined() -> Architecture:
    return Architecture(
        name="well-defined",
        description="A thorough example",
        meta=Meta(owner="team", version="1.0", criticality="high"),
        trust_boundaries=[TrustBoundary(name="internal"), TrustBoundary(name="external")],
        components=[
            Component(
                name="api",
                type="service",
                description="API gateway",
                domain="networking",
                criticality="high",
                lifecycle="active",
                trust_boundary="internal",
            ),
            Component(
                name="idp",
                type="identity-provider",
                description="Identity provider",
                domain="identity",
                criticality="high",
                lifecycle="active",
                trust_boundary="internal",
            ),
        ],
        flows=[
            Flow(
                source="api",
                target="idp",
                label="auth",
                authentication="oauth2",
                encryption="tls",
            )
        ],
        risks=[
            Risk(
                id="R1",
                title="Token theft",
                severity="high",
                mitigation="short-lived tokens",
                likelihood="medium",
                impact="high",
            )
        ],
        controls=[
            Control(name="MFA", type="technical", applies_to=["idp"], description="Multi-factor auth")
        ],
    )


def _risky() -> Architecture:
    return Architecture(
        name="risky",
        components=[Component(name="svc", type="service")],
        risks=[
            Risk(id="R1", title="Critical unmitigated", severity="critical"),
            Risk(id="R2", title="High unmitigated", severity="high"),
            Risk(id="R3", title="No likelihood", severity="medium", mitigation="fixed"),
        ],
    )


# ── ArchitectureScore shape ───────────────────────────────────────────────────

def test_score_returns_architecture_score() -> None:
    result = score_architecture(_minimal())
    assert isinstance(result, ArchitectureScore)


def test_score_overall_in_range() -> None:
    for arch in [_minimal(), _well_defined(), _risky()]:
        score = score_architecture(arch)
        assert 0 <= score.overall <= 100


def test_score_grade_valid() -> None:
    for arch in [_minimal(), _well_defined(), _risky()]:
        score = score_architecture(arch)
        assert score.grade in ("A", "B", "C", "D", "F")


def test_score_has_five_dimensions() -> None:
    score = score_architecture(_minimal())
    assert len(score.dimensions) == 5


def test_dimension_names() -> None:
    score = score_architecture(_minimal())
    names = {d.name for d in score.dimensions}
    assert names == {
        "risk_health",
        "control_coverage",
        "component_maturity",
        "structural_health",
        "definition_completeness",
    }


def test_dimension_scores_in_range() -> None:
    score = score_architecture(_well_defined())
    for d in score.dimensions:
        assert 0 <= d.score <= 100


def test_weights_sum_to_one() -> None:
    score = score_architecture(_minimal())
    total = sum(d.weight for d in score.dimensions)
    assert abs(total - 1.0) < 1e-9


def test_summary_is_non_empty_string() -> None:
    score = score_architecture(_minimal())
    assert isinstance(score.summary, str)
    assert len(score.summary) > 0


# ── Grade thresholds ──────────────────────────────────────────────────────────

def test_well_defined_scores_higher_than_risky() -> None:
    good = score_architecture(_well_defined())
    bad = score_architecture(_risky())
    assert good.overall > bad.overall


def test_grade_a_requires_high_score() -> None:
    score = score_architecture(_well_defined())
    if score.grade == "A":
        assert score.overall >= 90


def test_risky_arch_gets_lower_grade() -> None:
    score = score_architecture(_risky())
    assert score.grade in ("C", "D", "F")


# ── Risk health dimension ─────────────────────────────────────────────────────

def test_risk_health_penalizes_unmitigated_critical() -> None:
    arch_with = Architecture(
        name="a",
        risks=[Risk(id="R1", title="t", severity="critical")],
    )
    arch_without = Architecture(
        name="b",
        risks=[Risk(id="R1", title="t", severity="critical", mitigation="done", likelihood="low", impact="high")],
    )
    rh_with = next(d for d in score_architecture(arch_with).dimensions if d.name == "risk_health")
    rh_without = next(d for d in score_architecture(arch_without).dimensions if d.name == "risk_health")
    assert rh_with.score < rh_without.score


def test_risk_health_full_when_no_risks() -> None:
    score = score_architecture(_minimal())
    rh = next(d for d in score.dimensions if d.name == "risk_health")
    assert rh.score == 100


# ── Control coverage dimension ────────────────────────────────────────────────

def test_control_coverage_full_when_no_risks_no_controls() -> None:
    score = score_architecture(_minimal())
    cc = next(d for d in score.dimensions if d.name == "control_coverage")
    assert cc.score == 100


def test_control_coverage_increases_with_more_controls() -> None:
    arch_few = Architecture(
        name="few",
        risks=[Risk(id="R1", title="t", severity="high"), Risk(id="R2", title="t2", severity="high")],
        controls=[Control(name="C1", type="technical")],
    )
    arch_many = Architecture(
        name="many",
        risks=[Risk(id="R1", title="t", severity="high"), Risk(id="R2", title="t2", severity="high")],
        controls=[
            Control(name="C1", type="technical"),
            Control(name="C2", type="technical"),
        ],
    )
    cc_few = next(d for d in score_architecture(arch_few).dimensions if d.name == "control_coverage")
    cc_many = next(d for d in score_architecture(arch_many).dimensions if d.name == "control_coverage")
    assert cc_many.score >= cc_few.score


# ── Structural health dimension ───────────────────────────────────────────────

def test_structural_health_penalizes_isolated_components() -> None:
    connected = Architecture(
        name="connected",
        components=[
            Component(name="a", type="service"),
            Component(name="b", type="service"),
        ],
        flows=[Flow(source="a", target="b")],
    )
    isolated = Architecture(
        name="isolated",
        components=[
            Component(name="a", type="service"),
            Component(name="b", type="service"),
            Component(name="orphan", type="service"),
        ],
        flows=[Flow(source="a", target="b")],
    )
    sh_conn = next(d for d in score_architecture(connected).dimensions if d.name == "structural_health")
    sh_iso = next(d for d in score_architecture(isolated).dimensions if d.name == "structural_health")
    assert sh_conn.score > sh_iso.score


# ── to_dict serialization ─────────────────────────────────────────────────────

def test_to_dict_has_required_keys() -> None:
    d = score_architecture(_well_defined()).to_dict()
    assert "overall" in d
    assert "grade" in d
    assert "summary" in d
    assert "dimensions" in d


def test_to_dict_dimensions_have_required_keys() -> None:
    d = score_architecture(_well_defined()).to_dict()
    for dim in d["dimensions"]:
        assert "name" in dim
        assert "score" in dim
        assert "weight" in dim
        assert "weighted_contribution" in dim
        assert "notes" in dim


# ── runtime.score_model ───────────────────────────────────────────────────────

def test_score_model_returns_zephyr_result() -> None:
    from zephyr.result import ZephyrResult
    result = score_model(EXAMPLES / "identity-flow.yaml")
    assert isinstance(result, ZephyrResult)


def test_score_model_status_ok() -> None:
    result = score_model(EXAMPLES / "identity-flow.yaml")
    assert result.status == "ok"
    assert result.ok is True


def test_score_model_data_has_overall_and_grade() -> None:
    result = score_model(EXAMPLES / "identity-flow.yaml")
    assert "overall" in result.data
    assert "grade" in result.data
    assert isinstance(result.data["overall"], int)
    assert result.data["grade"] in ("A", "B", "C", "D", "F")


def test_score_model_error_on_missing_file() -> None:
    result = score_model("nonexistent.yaml")
    assert result.failed is True


def test_score_model_zero_trust_example() -> None:
    result = score_model(EXAMPLES / "zero-trust-access.yaml")
    assert result.ok
    assert result.data["overall"] >= 0


def test_score_model_command_field() -> None:
    result = score_model(EXAMPLES / "identity-flow.yaml")
    assert result.command == "score"
