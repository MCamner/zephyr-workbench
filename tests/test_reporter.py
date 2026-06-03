"""Tests for zephyr/reporter.py and runtime.report_model()."""

from __future__ import annotations

from pathlib import Path

import pytest

from zephyr.models import Architecture, Component, Control, Flow, Meta, Risk, TrustBoundary
from zephyr.reporter import generate_report
from zephyr.runtime import report_model


EXAMPLES = Path(__file__).parent.parent / "examples"


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _minimal() -> Architecture:
    return Architecture(name="minimal-arch")


def _full() -> Architecture:
    return Architecture(
        name="full-arch",
        description="Complete architecture for testing",
        meta=Meta(owner="ops-team", version="2.1", criticality="high", environment=["prod"]),
        trust_boundaries=[TrustBoundary(name="internal")],
        components=[
            Component(name="api", type="service", description="API layer", domain="networking",
                      criticality="high", lifecycle="active", trust_boundary="internal"),
            Component(name="db", type="data-store", description="Database", domain="data",
                      criticality="critical", lifecycle="active", trust_boundary="internal"),
        ],
        flows=[
            Flow(source="api", target="db", label="query", protocol="tcp",
                 authentication="mtls", encryption="tls"),
        ],
        risks=[
            Risk(id="R1", title="SQL injection", severity="high",
                 mitigation="parameterized queries", likelihood="medium", impact="high"),
            Risk(id="R2", title="Unencrypted backup", severity="medium",
                 likelihood="low", impact="medium"),
        ],
        controls=[
            Control(name="WAF", type="technical", applies_to=["api"], description="Web app firewall"),
        ],
    )


# ── Markdown output ───────────────────────────────────────────────────────────

def test_md_report_returns_string() -> None:
    result = generate_report(_minimal(), format="md")
    assert isinstance(result, str)
    assert len(result) > 0


def test_md_report_contains_architecture_name() -> None:
    result = generate_report(_full(), format="md")
    assert "full-arch" in result


def test_md_report_contains_score_section() -> None:
    result = generate_report(_full(), format="md")
    assert "Score Card" in result
    assert "overall" in result.lower() or "/100" in result


def test_md_report_contains_narrative_section() -> None:
    result = generate_report(_full(), format="md")
    assert "Narrative" in result


def test_md_report_contains_risks_section() -> None:
    result = generate_report(_full(), format="md")
    assert "Risks" in result
    assert "R1" in result
    assert "SQL injection" in result


def test_md_report_contains_findings_section() -> None:
    result = generate_report(_full(), format="md")
    assert "Findings" in result


def test_md_report_contains_controls_section() -> None:
    result = generate_report(_full(), format="md")
    assert "Controls" in result
    assert "WAF" in result


def test_md_report_contains_dependency_insights() -> None:
    result = generate_report(_full(), format="md")
    assert "Dependency Insights" in result


def test_md_report_shows_meta_owner() -> None:
    result = generate_report(_full(), format="md")
    assert "ops-team" in result


def test_md_report_minimal_arch_no_crash() -> None:
    result = generate_report(_minimal(), format="md")
    assert "minimal-arch" in result
    assert "No risks defined" in result
    assert "No controls defined" in result


# ── HTML output ───────────────────────────────────────────────────────────────

def test_html_report_returns_string() -> None:
    result = generate_report(_full(), format="html")
    assert isinstance(result, str)


def test_html_report_is_valid_html_envelope() -> None:
    result = generate_report(_full(), format="html")
    assert "<!DOCTYPE html>" in result
    assert "</html>" in result


def test_html_report_contains_architecture_name() -> None:
    result = generate_report(_full(), format="html")
    assert "full-arch" in result


def test_html_report_contains_grade_badge() -> None:
    result = generate_report(_full(), format="html")
    assert "grade-badge" in result


def test_html_report_contains_risk_table() -> None:
    result = generate_report(_full(), format="html")
    assert "SQL injection" in result
    assert "R1" in result


def test_html_report_minimal_no_crash() -> None:
    result = generate_report(_minimal(), format="html")
    assert "minimal-arch" in result


# ── runtime.report_model ──────────────────────────────────────────────────────

def test_report_model_returns_ok() -> None:
    result = report_model(EXAMPLES / "identity-flow.yaml")
    assert result.ok is True
    assert result.status == "ok"


def test_report_model_command_field() -> None:
    result = report_model(EXAMPLES / "identity-flow.yaml")
    assert result.command == "report"


def test_report_model_artifact_present() -> None:
    result = report_model(EXAMPLES / "identity-flow.yaml")
    assert len(result.artifacts) == 1
    assert result.artifacts[0]["type"] == "report"
    assert "content" in result.artifacts[0]


def test_report_model_md_format() -> None:
    result = report_model(EXAMPLES / "identity-flow.yaml", format="md")
    assert result.artifacts[0]["format"] == "md"
    assert "# Architecture Review:" in result.artifacts[0]["content"]


def test_report_model_html_format() -> None:
    result = report_model(EXAMPLES / "identity-flow.yaml", format="html")
    assert result.artifacts[0]["format"] == "html"
    assert "<!DOCTYPE html>" in result.artifacts[0]["content"]


def test_report_model_error_on_missing_file() -> None:
    result = report_model("nonexistent.yaml")
    assert result.failed is True


def test_report_model_error_on_bad_format() -> None:
    result = report_model(EXAMPLES / "identity-flow.yaml", format="pdf")
    assert result.failed is True


def test_report_model_writes_file(tmp_path) -> None:
    out = tmp_path / "report.md"
    result = report_model(EXAMPLES / "identity-flow.yaml", output=out)
    assert result.ok
    assert out.exists()
    assert result.artifacts[0]["path"] == str(out)


def test_report_model_data_fields() -> None:
    result = report_model(EXAMPLES / "identity-flow.yaml")
    assert "format" in result.data
    assert "name" in result.data


def test_report_model_zero_trust_example() -> None:
    result = report_model(EXAMPLES / "zero-trust-access.yaml")
    assert result.ok
    content = result.artifacts[0]["content"]
    assert "zero" in content.lower() or "trust" in content.lower()
