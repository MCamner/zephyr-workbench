from __future__ import annotations

from zephyr.analyzer import load_architecture, summarize_architecture, summarize_architecture_data
from zephyr.models import Architecture, Component, Control, Flow, Risk, Stakeholder


def test_load_and_summarize() -> None:
    architecture = load_architecture("examples/secure-workplace.yaml")
    summary = summarize_architecture(architecture)

    assert architecture.name == "secure-workplace"
    assert "Architecture: secure-workplace" in summary
    assert "Risks:" in summary


def test_summarize_architecture_data_returns_structured_counts() -> None:
    architecture = load_architecture("examples/secure-workplace.yaml")

    summary = summarize_architecture_data(architecture)

    assert summary["name"] == "secure-workplace"
    assert summary["components"] == 6
    assert summary["flows"] == 5
    assert summary["risks"] == 2
    assert summary["risk_details"][0]["id"] == "R1"


def test_summarize_includes_controls_and_stakeholders() -> None:
    architecture = Architecture(
        name="test-arch",
        components=[Component(name="vpn", type="access-gateway")],
        flows=[Flow(source="vpn", target="vpn", label="self")],
        risks=[
            Risk(
                id="R1",
                title="Single gateway",
                severity="high",
                mitigation="Add redundancy",
                likelihood="medium",
                impact="high",
            )
        ],
        controls=[
            Control(
                name="enforce-mfa",
                type="technical",
                applies_to=["vpn"],
                description="Require MFA for all VPN access",
            )
        ],
        stakeholders=[
            Stakeholder(name="security-team", role="security"),
        ],
    )

    summary = summarize_architecture(architecture)

    assert "Controls:     1" in summary
    assert "Stakeholders: 1" in summary
    assert "Controls:" in summary
    assert "[technical] enforce-mfa → vpn" in summary
    assert "Require MFA for all VPN access" in summary
    assert "Stakeholders:" in summary
    assert "security-team (security)" in summary
    assert "likelihood: medium | impact: high" in summary
    assert "Mitigation: Add redundancy" in summary


def test_summarize_architecture_data_includes_control_and_stakeholder_details() -> None:
    architecture = Architecture(
        name="test-arch",
        components=[Component(name="db", type="application")],
        flows=[],
        controls=[Control(name="audit-log", type="process", applies_to=["db"])],
        stakeholders=[Stakeholder(name="ops", role="operator")],
    )

    summary = summarize_architecture_data(architecture)

    assert summary["controls"] == 1
    assert summary["control_details"][0]["name"] == "audit-log"
    assert summary["stakeholders"] == 1
    assert summary["stakeholder_details"][0]["role"] == "operator"


def test_summarize_omits_empty_sections() -> None:
    architecture = load_architecture("examples/secure-workplace.yaml")
    summary = summarize_architecture(architecture)

    assert "Controls:" not in summary
    assert "Stakeholders:" not in summary
