"""Contract tests for the Zephyr Python runtime API (zephyr/runtime.py).

These tests verify that the Python API returns ZephyrResult objects with
the correct shape, status, and data — matching the zephyr-result.v1 contract.
mq-mcp and agents rely on this API being stable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zephyr.result import SCHEMA_VERSION, ZephyrResult
from zephyr.runtime import (
    diff_models,
    diagram_model,
    search_model,
    summary_model,
    validate_model,
)


# ── ZephyrResult ─────────────────────────────────────────────────────────────

def test_result_ok_properties() -> None:
    r = ZephyrResult(status="ok", command="validate", source="f.yaml")
    assert r.ok is True
    assert r.failed is False


def test_result_warning_properties() -> None:
    r = ZephyrResult(status="warning", command="validate", source="f.yaml")
    assert r.ok is True
    assert r.failed is False


def test_result_error_properties() -> None:
    r = ZephyrResult(status="error", command="validate", source="f.yaml")
    assert r.ok is False
    assert r.failed is True


def test_result_to_dict_envelope_shape() -> None:
    r = ZephyrResult(
        status="ok",
        command="validate",
        source="examples/identity-flow.yaml",
        warnings=["one warning"],
        data={"valid": True},
        artifacts=[{"type": "diagram"}],
    )
    d = r.to_dict()
    assert d["status"] == "ok"
    assert d["errors"] == []
    assert d["warnings"] == ["one warning"]
    assert d["data"] == {"valid": True}
    assert d["artifacts"] == [{"type": "diagram"}]
    assert d["metadata"]["command"] == "validate"
    assert d["metadata"]["source"] == "examples/identity-flow.yaml"
    assert d["metadata"]["schema_version"] == SCHEMA_VERSION


# ── validate_model ────────────────────────────────────────────────────────────

def test_validate_model_ok() -> None:
    result = validate_model("examples/identity-flow.yaml")
    assert isinstance(result, ZephyrResult)
    assert result.status == "ok"
    assert result.errors == []
    assert result.data["valid"] is True
    assert result.data["name"] == "identity-flow"
    assert result.command == "validate"
    assert result.source == "examples/identity-flow.yaml"


def test_validate_model_warning() -> None:
    result = validate_model("examples/macos-intune-windows-domain.yaml")
    assert result.status == "warning"
    assert result.ok is True
    assert result.data["valid"] is True
    assert len(result.warnings) > 0


def test_validate_model_error_missing_name() -> None:
    result = validate_model("tests/fixtures/invalid/missing-name.yaml")
    assert result.status == "error"
    assert result.failed is True
    assert result.data == {"valid": False}
    assert any("missing required top-level field: name" in e for e in result.errors)


def test_validate_model_error_invalid_type() -> None:
    result = validate_model("tests/fixtures/invalid/invalid-component-type.yaml")
    assert result.status == "error"
    assert result.errors


def test_validate_model_to_dict_is_valid_envelope() -> None:
    result = validate_model("examples/identity-flow.yaml")
    d = result.to_dict()
    assert d["metadata"]["schema_version"] == SCHEMA_VERSION
    assert d["metadata"]["command"] == "validate"
    assert "valid" in d["data"]


# ── summary_model ─────────────────────────────────────────────────────────────

def test_summary_model_ok() -> None:
    result = summary_model("examples/secure-workplace.yaml")
    assert result.status == "ok"
    assert result.command == "summary"
    assert result.data["name"] == "secure-workplace"
    assert result.data["components"] == 7
    assert result.data["risks"] == 2
    assert isinstance(result.data["risk_details"], list)


def test_summary_model_error_on_invalid() -> None:
    result = summary_model("tests/fixtures/invalid/missing-name.yaml")
    assert result.status == "error"
    assert result.failed is True


# ── diagram_model ─────────────────────────────────────────────────────────────

def test_diagram_model_mermaid_stdout() -> None:
    result = diagram_model("examples/identity-flow.yaml", format="mermaid")
    assert result.status == "ok"
    assert result.command == "diagram"
    assert len(result.artifacts) == 1
    artifact = result.artifacts[0]
    assert artifact["type"] == "diagram"
    assert artifact["format"] == "mermaid"
    assert "graph TD" in artifact["content"]
    assert "path" not in artifact


def test_diagram_model_html_stdout() -> None:
    result = diagram_model("examples/identity-flow.yaml", format="html")
    assert result.status == "ok"
    artifact = result.artifacts[0]
    assert artifact["format"] == "html"
    assert "<html" in artifact["content"].lower()


def test_diagram_model_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "arch.mmd"
    result = diagram_model("examples/identity-flow.yaml", format="mermaid", output=out)
    assert result.status == "ok"
    artifact = result.artifacts[0]
    assert artifact["path"] == str(out)
    assert "content" not in artifact
    assert out.exists()
    assert "graph TD" in out.read_text(encoding="utf-8")


def test_diagram_model_invalid_format() -> None:
    result = diagram_model("examples/identity-flow.yaml", format="svg")
    assert result.status == "error"
    assert any("unsupported format" in e for e in result.errors)


def test_diagram_model_error_on_invalid_model() -> None:
    result = diagram_model("tests/fixtures/invalid/missing-name.yaml", format="mermaid")
    assert result.status == "error"


# ── diff_models ───────────────────────────────────────────────────────────────

def test_diff_models_identical() -> None:
    result = diff_models("examples/identity-flow.yaml", "examples/identity-flow.yaml")
    assert result.status == "ok"
    assert result.ok is True
    assert result.data["changed"] is False
    assert result.data["components"] == []
    assert result.data["flows"] == []
    assert result.data["source"] == "examples/identity-flow.yaml"
    assert result.data["target"] == "examples/identity-flow.yaml"


def test_diff_models_changed(tmp_path: Path) -> None:
    import yaml

    base = {
        "name": "arch-a",
        "components": [
            {"name": "svc", "type": "application"},
            {"name": "db", "type": "on-prem-resource"},
        ],
        "flows": [{"from": "svc", "to": "db", "label": "query"}],
    }
    extended = {
        "name": "arch-b",
        "components": [
            {"name": "svc", "type": "application"},
            {"name": "db", "type": "on-prem-resource"},
            {"name": "cache", "type": "on-prem-resource"},
        ],
        "flows": [
            {"from": "svc", "to": "db", "label": "query"},
            {"from": "svc", "to": "cache", "label": "read"},
        ],
    }
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    a.write_text(yaml.safe_dump(base), encoding="utf-8")
    b.write_text(yaml.safe_dump(extended), encoding="utf-8")

    result = diff_models(a, b)
    assert result.status == "warning"
    assert result.data["changed"] is True
    added = [c for c in result.data["components"] if c["status"] == "added"]
    assert any(c["label"].startswith("cache") for c in added)


def test_diff_models_invalid_source() -> None:
    result = diff_models("tests/fixtures/invalid/missing-name.yaml", "examples/identity-flow.yaml")
    assert result.status == "error"
    assert any("source model invalid" in e for e in result.errors)


# ── search_model ──────────────────────────────────────────────────────────────

def test_search_model_by_type() -> None:
    result = search_model("examples/identity-flow.yaml", "type=endpoint")
    assert result.status == "ok"
    assert result.command == "search"
    assert result.data["query"] == "type=endpoint"
    assert isinstance(result.data["total"], int)
    assert all(c["type"] == "endpoint" for c in result.data["components"])


def test_search_model_no_results() -> None:
    result = search_model("examples/identity-flow.yaml", "type=nonexistent")
    assert result.status == "ok"
    assert result.data["total"] == 0
    assert result.data["components"] == []
    assert result.data["flows"] == []


def test_search_model_missing_field() -> None:
    result = search_model("examples/secure-workplace.yaml", "missing=mitigation")
    assert result.status == "ok"
    assert result.data["total"] >= 0


def test_search_model_error_on_invalid() -> None:
    result = search_model("tests/fixtures/invalid/missing-name.yaml", "type=endpoint")
    assert result.status == "error"


# ── contracts ─────────────────────────────────────────────────────────────────

def test_contracts_tool_registry() -> None:
    from zephyr.contracts import TOOLS, is_safe_for_agents, requires_write_intent

    assert "validate" in TOOLS
    assert "summary" in TOOLS
    assert "diagram_stdout" in TOOLS
    assert "diagram_file" in TOOLS
    assert "diff" in TOOLS
    assert "search" in TOOLS
    assert "init" in TOOLS


def test_contracts_read_only_tools_safe_for_agents() -> None:
    from zephyr.contracts import is_safe_for_agents

    for tool in ("validate", "summary", "diagram_stdout", "diff", "search"):
        assert is_safe_for_agents(tool), f"{tool} should be safe for agents"


def test_contracts_forbidden_tools_not_safe() -> None:
    from zephyr.contracts import is_safe_for_agents

    for tool in ("init", "add"):
        assert not is_safe_for_agents(tool), f"{tool} should not be safe for agents"


def test_contracts_write_creating_requires_intent() -> None:
    from zephyr.contracts import requires_write_intent

    assert requires_write_intent("diagram_file") is True
    assert requires_write_intent("run") is True
    assert requires_write_intent("validate") is False
    assert requires_write_intent("search") is False
