from __future__ import annotations

import pytest

from zephyr.analyzer import summarize_architecture, summarize_architecture_data
from zephyr.datamodel import RISK_SCORE_MATRIX
from zephyr.diagram import to_mermaid
from zephyr.models import Architecture, Component, Flow, Risk, TrustBoundary
from zephyr.validation import collect_validation_warnings, ValidationError, validate_architecture_data


# --- TrustBoundary model ---

def test_trust_boundary_dataclass_defaults() -> None:
    b = TrustBoundary(name="internal")
    assert b.name == "internal"
    assert b.description == ""
    assert b.color == ""


def test_component_trust_boundary_field() -> None:
    c = Component(name="vpn", type="access-gateway", trust_boundary="internal")
    assert c.trust_boundary == "internal"


def test_component_tags_field() -> None:
    c = Component(name="app", type="application", tags=["critical", "public-facing"])
    assert c.tags == ["critical", "public-facing"]


def test_architecture_trust_boundaries_field() -> None:
    arch = Architecture(
        name="test",
        components=[Component(name="vpn", type="access-gateway")],
        flows=[],
        trust_boundaries=[TrustBoundary(name="internal"), TrustBoundary(name="dmz")],
    )
    assert len(arch.trust_boundaries) == 2
    assert arch.trust_boundaries[0].name == "internal"


# --- Validation ---

def test_validate_trust_boundaries_requires_name() -> None:
    data = {
        "name": "test",
        "components": [{"name": "vpn", "type": "access-gateway"}],
        "flows": [],
        "trust_boundaries": [{"description": "no name here"}],
    }
    with pytest.raises(ValidationError) as exc:
        validate_architecture_data(data)
    assert "trust_boundaries[1].name is required" in str(exc.value)


def test_validate_trust_boundaries_rejects_duplicate_names() -> None:
    data = {
        "name": "test",
        "components": [{"name": "vpn", "type": "access-gateway"}],
        "flows": [],
        "trust_boundaries": [
            {"name": "internal"},
            {"name": "internal"},
        ],
    }
    with pytest.raises(ValidationError) as exc:
        validate_architecture_data(data)
    assert "duplicate trust_boundary name: internal" in str(exc.value)


def test_validate_trust_boundaries_accepts_valid() -> None:
    data = {
        "name": "test",
        "components": [{"name": "vpn", "type": "access-gateway"}],
        "flows": [],
        "trust_boundaries": [
            {"name": "internal", "description": "corp network"},
            {"name": "dmz", "description": "demilitarized zone"},
        ],
    }
    validate_architecture_data(data)


def test_collect_warnings_flags_unknown_trust_boundary() -> None:
    data = {
        "name": "test",
        "components": [
            {"name": "vpn", "type": "access-gateway", "trust_boundary": "nonexistent"},
        ],
        "flows": [],
        "trust_boundaries": [{"name": "internal"}],
    }
    warnings = collect_validation_warnings(data)
    assert any("unknown trust_boundary 'nonexistent'" in w for w in warnings)


def test_collect_warnings_no_flag_when_boundary_matches() -> None:
    data = {
        "name": "test",
        "components": [
            {"name": "vpn", "type": "access-gateway", "trust_boundary": "internal"},
        ],
        "flows": [],
        "trust_boundaries": [{"name": "internal"}],
    }
    warnings = collect_validation_warnings(data)
    assert not any("unknown trust_boundary" in w for w in warnings)


def test_collect_warnings_no_flag_when_no_boundaries_defined() -> None:
    data = {
        "name": "test",
        "components": [
            {"name": "vpn", "type": "access-gateway", "trust_boundary": "anything"},
        ],
        "flows": [],
    }
    warnings = collect_validation_warnings(data)
    assert not any("unknown trust_boundary" in w for w in warnings)


# --- Risk scoring ---

def test_risk_score_matrix_high_high() -> None:
    assert RISK_SCORE_MATRIX[("high", "high")] == 9


def test_risk_score_matrix_critical_high() -> None:
    assert RISK_SCORE_MATRIX[("critical", "high")] == 12


def test_risk_score_matrix_low_low() -> None:
    assert RISK_SCORE_MATRIX[("low", "low")] == 1


def test_summarize_data_includes_risk_score_when_likelihood_set() -> None:
    arch = Architecture(
        name="scored",
        components=[Component(name="svc", type="application")],
        flows=[],
        risks=[Risk(id="R1", title="Example", severity="high", likelihood="high")],
    )
    data = summarize_architecture_data(arch)
    assert data["risk_details"][0]["score"] == 9


def test_summarize_data_risk_score_none_when_no_likelihood() -> None:
    arch = Architecture(
        name="unscored",
        components=[Component(name="svc", type="application")],
        flows=[],
        risks=[Risk(id="R1", title="Example", severity="high")],
    )
    data = summarize_architecture_data(arch)
    assert data["risk_details"][0]["score"] is None


def test_summarize_shows_risk_score_in_output() -> None:
    arch = Architecture(
        name="scored-output",
        components=[Component(name="svc", type="application")],
        flows=[],
        risks=[Risk(id="R1", title="Example", severity="critical", likelihood="high")],
    )
    summary = summarize_architecture(arch)
    assert "score:12" in summary


# --- Diagram subgraphs ---

def test_to_mermaid_uses_subgraphs_when_boundaries_defined() -> None:
    arch = Architecture(
        name="zoned",
        trust_boundaries=[
            TrustBoundary(name="internal"),
            TrustBoundary(name="external"),
        ],
        components=[
            Component(name="user", type="actor", trust_boundary="external"),
            Component(name="vpn", type="access-gateway", trust_boundary="internal"),
        ],
        flows=[Flow(source="user", target="vpn", label="connect")],
    )
    diagram = to_mermaid(arch)
    assert "subgraph internal" in diagram
    assert "subgraph external" in diagram
    assert 'user["user (actor)"]' in diagram
    assert 'vpn["vpn (access-gateway)"]' in diagram


def test_to_mermaid_no_subgraphs_when_no_boundaries() -> None:
    arch = Architecture(
        name="flat",
        components=[
            Component(name="user", type="actor"),
            Component(name="vpn", type="access-gateway"),
        ],
        flows=[Flow(source="user", target="vpn")],
    )
    diagram = to_mermaid(arch)
    assert "subgraph" not in diagram


def test_to_mermaid_unbounded_components_outside_subgraphs() -> None:
    arch = Architecture(
        name="mixed",
        trust_boundaries=[TrustBoundary(name="internal")],
        components=[
            Component(name="vpn", type="access-gateway", trust_boundary="internal"),
            Component(name="user", type="actor"),
        ],
        flows=[Flow(source="user", target="vpn")],
    )
    diagram = to_mermaid(arch)
    assert "subgraph internal" in diagram
    assert 'user["user (actor)"]' in diagram


# --- Analyzer boundary summary ---

def test_summarize_shows_boundary_count() -> None:
    arch = Architecture(
        name="bounded",
        components=[Component(name="svc", type="application")],
        flows=[],
        trust_boundaries=[TrustBoundary(name="internal"), TrustBoundary(name="dmz")],
    )
    summary = summarize_architecture(arch)
    assert "Boundaries:   2" in summary


def test_summarize_shows_trust_boundaries_section() -> None:
    arch = Architecture(
        name="bounded",
        components=[Component(name="svc", type="application")],
        flows=[],
        trust_boundaries=[
            TrustBoundary(name="internal", description="Corporate LAN"),
            TrustBoundary(name="dmz"),
        ],
    )
    summary = summarize_architecture(arch)
    assert "Trust Boundaries:" in summary
    assert "- internal — Corporate LAN" in summary
    assert "- dmz" in summary


def test_summarize_omits_boundary_section_when_none() -> None:
    arch = Architecture(
        name="flat",
        components=[Component(name="svc", type="application")],
        flows=[],
    )
    summary = summarize_architecture(arch)
    assert "Trust Boundaries:" not in summary
    assert "Boundaries:" not in summary
