from copy import deepcopy

import pytest
import yaml

from zephyr.diff import diff_architectures
from zephyr.models import Architecture, Component, Flow, Risk, TrustBoundary
from zephyr.runtime import import_diagram_model


def model():
    return Architecture(
        "demo",
        components=[Component("client", "endpoint"), Component("api", "application")],
        flows=[Flow("client", "api")],
        risks=[Risk("R1", "Access", "high", mitigation="MFA")],
        trust_boundaries=[TrustBoundary("internal")],
    )


@pytest.mark.parametrize(
    "field,value",
    [("description", "new"), ("trust_boundary", "internal"), ("tags", ["pii"])],
)
def test_component_diff_covers_fields(field, value):
    a = model()
    b = deepcopy(a)
    setattr(b.components[0], field, value)
    assert not diff_architectures(a, b).is_empty()


@pytest.mark.parametrize("field", ["name", "description", "trust_boundaries"])
def test_architecture_diff_covers_fields(field):
    a = model()
    b = deepcopy(a)
    setattr(b, field, [] if field == "trust_boundaries" else "changed")
    assert not diff_architectures(a, b).is_empty()


def test_removed_mitigation_is_detected():
    from zephyr.impact import analyze_impact

    a = model()
    b = deepcopy(a)
    b.risks[0].mitigation = ""
    diff = diff_architectures(a, b)
    assert not diff.is_empty()
    impact = analyze_impact(a, b, diff)
    assert impact.unmitigated_risk_ids == ["R1"]
    assert impact.severity == "high"


def test_image_runtime_returns_detected_format(monkeypatch):
    from zephyr.diagram_import import parse_diagram

    monkeypatch.setattr(
        "zephyr.image_import.parse_image",
        lambda *a: parse_diagram(
            "graph TD\n A[Client]\n B[Server]\n A --> B", "mermaid"
        ),
    )
    result = import_diagram_model("diagram.png")
    assert result.status in ("ok", "warning")
    assert result.data["format"] == "mermaid"


def test_risk_references_are_validated_and_explained():
    from zephyr.intelligence import explain_risk
    from zephyr.loader import architecture_from_data
    from zephyr.validation import ValidationError, validate_architecture_data

    data = {
        "name": "demo",
        "components": [
            {"name": "api", "type": "application"},
            {"name": "other", "type": "endpoint", "criticality": "high"},
        ],
        "flows": [{"from": "other", "to": "api", "label": "request"}],
        "controls": [{"name": "MFA", "type": "technical", "applies_to": ["api"]}],
        "risks": [
            {
                "id": "R1",
                "title": "Access",
                "severity": "high",
                "components": ["api"],
                "flows": [{"from": "other", "to": "api", "label": "request"}],
                "controls": ["MFA"],
            }
        ],
    }
    validate_architecture_data(data)
    ctx = explain_risk(architecture_from_data(data), "R1")
    assert ctx.affected_components == ["api"]
    assert ctx.affected_flows == ["other → api"]
    assert ctx.controls == ["MFA"]
    data["risks"][0]["components"] = ["missing"]
    with pytest.raises(ValidationError):
        validate_architecture_data(data)


def test_unlinked_risk_does_not_claim_affected_components():
    from zephyr.intelligence import explain_risk

    a = model()
    a.components[0].criticality = "high"
    ctx = explain_risk(a, "R1")
    assert ctx.affected_components == []
    assert "No explicit" in ctx.explanation


def test_memory_marks_changed_and_missing_sources(tmp_path):
    from zephyr.memory import add_to_memory, list_memory, search_memory

    p = tmp_path / "demo.yaml"
    idx = tmp_path / "index"
    p.write_text(
        "name: demo\ncomponents: [{name: api, type: application}]\nflows: []\n"
    )
    add_to_memory(p, idx)
    assert list_memory(idx)[0].source_status == "current"
    p.write_text(p.read_text() + "description: changed\n")
    assert list_memory(idx)[0].source_status == "changed"
    p.unlink()
    assert list_memory(idx)[0].source_status == "missing"
    assert search_memory("demo", idx)[0].model.source_status == "missing"


def test_similarity_distinguishes_topology_and_preserves_renames():
    from zephyr.memory import compare_architectures

    a = model()
    b = deepcopy(a)
    b.flows = [Flow("api", "client")]
    assert compare_architectures(a, b).structural_similarity < 1
    b = deepcopy(a)
    b.components[0].name = "renamed"
    b.flows[0].source = "renamed"
    assert compare_architectures(a, b).structural_similarity == 1


def test_all_runtime_operations_have_safety_contracts():
    from zephyr.contracts import TOOLS, requires_write_intent

    for name in [
        "analyze",
        "review",
        "explain",
        "import_stdout",
        "import_file",
        "govern",
        "impact",
        "snapshot_save",
        "snapshot_list",
        "snapshot_diff",
        "snapshot_impact",
        "snapshot_delete",
        "history",
        "memory_add",
        "memory_remove",
        "memory_list",
        "memory_search",
        "memory_compare",
        "review_templates",
    ]:
        assert name in TOOLS
    assert requires_write_intent("memory_add")
    assert TOOLS["snapshot_delete"].safety == "forbidden"


def test_refresh_updates_changed_sources_and_reports_missing(tmp_path):
    from zephyr.memory import add_to_memory, list_memory, refresh_memory

    p = tmp_path / "model.yaml"
    idx = tmp_path / "index"
    p.write_text("name: old\ncomponents: [{name: api, type: application}]\nflows: []\n")
    add_to_memory(p, idx)
    p.write_text(p.read_text().replace("old", "new"))
    result = refresh_memory(idx)
    assert result["updated"] == [str(p.resolve())]
    assert list_memory(idx)[0].name == "new"
    p.unlink()
    assert refresh_memory(idx)["missing"] == [str(p.resolve())]


def test_import_invalid_format_and_bad_model_use_error_envelope(tmp_path):
    p = tmp_path / "bad.mmd"
    p.write_text("not a diagram")
    assert import_diagram_model(p, "unsupported").failed
    assert import_diagram_model(p).failed


@pytest.mark.parametrize(
    "field,value",
    [("domains", ["technology"]), ("rules", {"require": {"risk": ["mitigation"]}})],
)
def test_diff_preserves_model_configuration(field, value):
    from zephyr.loader import architecture_from_data

    a = {
        "name": "demo",
        "components": [{"name": "api", "type": "application"}],
        "flows": [],
    }
    b = deepcopy(a)
    b[field] = value
    assert not diff_architectures(
        architecture_from_data(a), architecture_from_data(b)
    ).is_empty()


def test_runtime_diff_serializes_boundary_changes(tmp_path):
    from zephyr.runtime import diff_models

    a = {
        "name": "demo",
        "components": [{"name": "api", "type": "application"}],
        "flows": [],
        "trust_boundaries": [{"name": "internal"}],
    }
    b = deepcopy(a)
    b["trust_boundaries"][0]["description"] = "updated"
    pa = tmp_path / "a.yaml"
    pb = tmp_path / "b.yaml"
    pa.write_text(yaml.safe_dump(a))
    pb.write_text(yaml.safe_dump(b))
    result = diff_models(pa, pb)
    assert result.data["trust_boundaries"][0]["fields"][0]["field"] == "description"


@pytest.mark.parametrize(
    "field,value",
    [
        ("controls", ["missing"]),
        ("flows", [{"from": "missing", "to": "api"}]),
        ("components", "api"),
    ],
)
def test_bad_risk_scope_is_rejected(field, value):
    from zephyr.validation import ValidationError, validate_architecture_data

    data = {
        "name": "demo",
        "components": [{"name": "api", "type": "application"}],
        "flows": [],
        "risks": [{"id": "R1", "title": "Access", "severity": "high", field: value}],
    }
    with pytest.raises(ValidationError):
        validate_architecture_data(data)


def test_corrupt_memory_index_returns_error_envelopes(tmp_path, monkeypatch):
    from zephyr.runtime import memory_list, memory_refresh, memory_search

    monkeypatch.setattr("zephyr.memory.default_index_dir", lambda: tmp_path)
    (tmp_path / "index.json").write_text("broken")
    assert memory_list().failed
    assert memory_search("api").failed
    assert memory_refresh().failed
    assert (tmp_path / "index.json").read_text() == "broken"


def test_graph_similarity_counts_duplicate_components():
    from zephyr.memory import compare_architectures

    a = model()
    b = deepcopy(a)
    b.components.append(Component("second-api", "application"))
    assert compare_architectures(a, b).structural_similarity < 1
