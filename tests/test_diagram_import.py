"""Tests for diagram_import: Mermaid and draw.io parsing."""

from __future__ import annotations

import textwrap

import pytest

from zephyr.diagram_import import (
    DiagramImportResult,
    detect_format,
    parse_diagram,
    parse_drawio,
    parse_mermaid,
)
from zephyr.image_import import is_image_path, parse_image
from zephyr.diagram import to_mermaid
from zephyr.loader import architecture_from_data


# ── helpers ───────────────────────────────────────────────────────────────────


def _dedent(s: str) -> str:
    return textwrap.dedent(s).strip()


def _minimal_arch() -> dict:
    return {
        "name": "test-arch",
        "components": [
            {"name": "Web App", "type": "application"},
            {"name": "API Gateway", "type": "access-gateway"},
            {"name": "Database", "type": "on-prem-resource"},
        ],
        "flows": [
            {"from": "Web App", "to": "API Gateway", "label": "HTTPS"},
            {"from": "API Gateway", "to": "Database"},
        ],
    }


# ── detect_format ─────────────────────────────────────────────────────────────


def test_detect_format_mmd():
    assert detect_format("diagram.mmd") == "mermaid"


def test_detect_format_md():
    assert detect_format("notes.md") == "mermaid"


def test_detect_format_drawio():
    assert detect_format("arch.drawio") == "drawio"


def test_detect_format_xml():
    assert detect_format("diagram.xml") == "drawio"


def test_detect_format_unknown_defaults_mermaid():
    assert detect_format("diagram.txt") == "mermaid"


# ── parse_mermaid: basic structure ────────────────────────────────────────────

def test_is_image_path_png():
    assert is_image_path("diagram.png")
    assert is_image_path("diagram.JPG")
    assert not is_image_path("diagram.mmd")


def test_parse_image_uses_ocr_text(monkeypatch, tmp_path):
    image_path = tmp_path / "diagram.png"
    image_path.write_text("fake image data")

    def fake_ocr(path):
        return "graph TD\n    A[\"Node A (application)\"]"

    monkeypatch.setattr("zephyr.image_import.extract_text_from_image", fake_ocr)
    result = parse_image(image_path, format="mermaid")
    assert len(result.components) == 1
    assert result.components[0]["name"] == "Node A"
    assert result.components[0]["type"] == "application"

# ── parse_mermaid: basic structure ────────────────────────────────────────────


def test_parse_mermaid_name_from_comment():
    mmd = _dedent("""
        %% My Architecture
        graph TD
            A["Node A (application)"]
    """)
    result = parse_mermaid(mmd)
    assert result.name == "My Architecture"


def test_parse_mermaid_default_name_when_no_comment():
    mmd = _dedent("""
        graph TD
            A["Node A (application)"]
    """)
    result = parse_mermaid(mmd)
    assert result.name == "imported-architecture"


def test_parse_mermaid_simple_components():
    mmd = _dedent("""
        graph TD
            WebApp["Web App (application)"]
            GW["API GW (access-gateway)"]
    """)
    result = parse_mermaid(mmd)
    names = [c["name"] for c in result.components]
    types = [c["type"] for c in result.components]
    assert "Web App" in names
    assert "API GW" in names
    assert "application" in types
    assert "access-gateway" in types


def test_parse_mermaid_edge_with_label():
    mmd = _dedent("""
        graph TD
            A["Node A (application)"]
            B["Node B (endpoint)"]
            A -->|HTTPS| B
    """)
    result = parse_mermaid(mmd)
    assert len(result.flows) == 1
    flow = result.flows[0]
    assert flow["source"] == "Node A"
    assert flow["target"] == "Node B"
    assert flow["label"] == "HTTPS"


def test_parse_mermaid_edge_without_label():
    mmd = _dedent("""
        graph TD
            A["Node A (application)"]
            B["Node B (application)"]
            A --> B
    """)
    result = parse_mermaid(mmd)
    assert len(result.flows) == 1
    flow = result.flows[0]
    assert flow["source"] == "Node A"
    assert flow["target"] == "Node B"
    assert "label" not in flow


def test_parse_mermaid_trust_boundary_from_subgraph():
    mmd = _dedent("""
        graph TD
            subgraph Corp ["Corporate Network"]
                A["Service A (application)"]
            end
            B["External (endpoint)"]
    """)
    result = parse_mermaid(mmd)
    assert len(result.trust_boundaries) == 1
    assert result.trust_boundaries[0]["name"] == "Corporate Network"
    comp_a = next(c for c in result.components if c["name"] == "Service A")
    assert comp_a["trust_boundary"] == "Corporate Network"
    comp_b = next(c for c in result.components if c["name"] == "External")
    assert "trust_boundary" not in comp_b


# ── parse_mermaid: shape → type mapping ──────────────────────────────────────


def test_parse_mermaid_cylinder_shape():
    mmd = "graph TD\n    DB[(Database)]"
    result = parse_mermaid(mmd)
    assert result.components[0]["type"] == "on-prem-resource"


def test_parse_mermaid_circle_shape():
    mmd = "graph TD\n    User((User))"
    result = parse_mermaid(mmd)
    assert result.components[0]["type"] == "actor"


def test_parse_mermaid_rhombus_shape():
    mmd = "graph TD\n    Policy{Access Policy}"
    result = parse_mermaid(mmd)
    assert result.components[0]["type"] == "access-policy"


def test_parse_mermaid_asymm_shape():
    mmd = "graph TD\n    EP>External Endpoint]"
    result = parse_mermaid(mmd)
    assert result.components[0]["type"] == "endpoint"


def test_parse_mermaid_rect_defaults_to_application():
    mmd = 'graph TD\n    X["Some Service"]'
    result = parse_mermaid(mmd)
    assert result.components[0]["type"] == "application"


def test_parse_mermaid_zephyr_type_hint_wins_over_shape():
    mmd = 'graph TD\n    X["Identity Provider (identity-provider)"]'
    result = parse_mermaid(mmd)
    assert result.components[0]["name"] == "Identity Provider"
    assert result.components[0]["type"] == "identity-provider"


# ── parse_mermaid: Zephyr round-trip ─────────────────────────────────────────


def test_parse_mermaid_roundtrip_names_and_types():
    """Generate Mermaid from a Zephyr model, parse it back, check names+types."""
    data = _minimal_arch()
    arch = architecture_from_data(data)
    mmd = to_mermaid(arch)
    result = parse_mermaid(mmd)

    original_names = {c["name"] for c in data["components"]}
    parsed_names = {c["name"] for c in result.components}
    assert original_names == parsed_names


def test_parse_mermaid_roundtrip_types_preserved():
    data = _minimal_arch()
    arch = architecture_from_data(data)
    mmd = to_mermaid(arch)
    result = parse_mermaid(mmd)

    original_types = {c["name"]: c["type"] for c in data["components"]}
    parsed_types = {c["name"]: c["type"] for c in result.components}
    for name, expected_type in original_types.items():
        assert parsed_types.get(name) == expected_type, f"{name}: expected {expected_type}, got {parsed_types.get(name)}"


def test_parse_mermaid_roundtrip_flows():
    data = _minimal_arch()
    arch = architecture_from_data(data)
    mmd = to_mermaid(arch)
    result = parse_mermaid(mmd)

    original_flows = {(f["from"], f["to"]) for f in data["flows"]}
    parsed_flows = {(f["source"], f["target"]) for f in result.flows}
    assert original_flows == parsed_flows


def test_parse_mermaid_roundtrip_trust_boundaries():
    data = {
        "name": "bounded-arch",
        "components": [
            {"name": "Service A", "type": "application", "trust_boundary": "Internal"},
            {"name": "Gateway", "type": "access-gateway"},
        ],
        "trust_boundaries": [{"name": "Internal", "description": "Internal zone"}],
        "flows": [{"from": "Gateway", "to": "Service A"}],
    }
    arch = architecture_from_data(data)
    mmd = to_mermaid(arch)
    result = parse_mermaid(mmd)

    assert any(b["name"] == "Internal" for b in result.trust_boundaries)
    service_a = next(c for c in result.components if c["name"] == "Service A")
    assert service_a["trust_boundary"] == "Internal"


# ── parse_mermaid: edge cases ─────────────────────────────────────────────────


def test_parse_mermaid_classDef_lines_ignored():
    mmd = _dedent("""
        graph TD
            classDef actor fill:#d4edda
            A["Node A (application)"]
    """)
    result = parse_mermaid(mmd)
    assert len(result.components) == 1
    assert result.components[0]["name"] == "Node A"


def test_parse_mermaid_class_assignment_ignored():
    mmd = _dedent("""
        graph TD
            A["Node A (application)"]
            class A actor
    """)
    result = parse_mermaid(mmd)
    assert len(result.components) == 1


def test_parse_mermaid_duplicate_node_not_doubled():
    mmd = _dedent("""
        graph TD
            A["Node A (application)"]
            A["Node A (application)"]
    """)
    result = parse_mermaid(mmd)
    assert len(result.components) == 1


def test_parse_mermaid_edge_id_resolved_to_name():
    mmd = _dedent("""
        graph TD
            Web_App["Web App (application)"]
            API_GW["API GW (access-gateway)"]
            Web_App -->|HTTPS| API_GW
    """)
    result = parse_mermaid(mmd)
    assert result.flows[0]["source"] == "Web App"
    assert result.flows[0]["target"] == "API GW"


# ── parse_drawio ──────────────────────────────────────────────────────────────


_DRAWIO_MINIMAL = """\
<mxGraphModel>
  <root>
    <mxCell id="0" />
    <mxCell id="1" parent="0" />
    <mxCell id="2" value="Web App" style="rounded=1;" vertex="1" parent="1">
      <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="3" value="API" style="rounded=1;" vertex="1" parent="1">
      <mxGeometry x="300" y="100" width="120" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="4" value="HTTPS" edge="1" source="2" target="3" parent="1">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>"""


def test_parse_drawio_components():
    result = parse_drawio(_DRAWIO_MINIMAL)
    names = [c["name"] for c in result.components]
    assert "Web App" in names
    assert "API" in names


def test_parse_drawio_flow():
    result = parse_drawio(_DRAWIO_MINIMAL)
    assert len(result.flows) == 1
    assert result.flows[0]["source"] == "Web App"
    assert result.flows[0]["target"] == "API"
    assert result.flows[0]["label"] == "HTTPS"


def test_parse_drawio_trust_boundary_swimlane():
    xml = """\
<mxGraphModel>
  <root>
    <mxCell id="0" />
    <mxCell id="1" parent="0" />
    <mxCell id="10" value="DMZ" style="swimlane;" vertex="1" parent="1">
      <mxGeometry x="0" y="0" width="400" height="300" as="geometry"/>
    </mxCell>
    <mxCell id="11" value="Web Server" style="rounded=1;" vertex="1" parent="10">
      <mxGeometry x="50" y="100" width="120" height="60" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>"""
    result = parse_drawio(xml)
    assert any(b["name"] == "DMZ" for b in result.trust_boundaries)
    ws = next(c for c in result.components if c["name"] == "Web Server")
    assert ws["trust_boundary"] == "DMZ"


def test_parse_drawio_bad_xml_returns_warning():
    result = parse_drawio("<not valid xml<<")
    assert result.warnings
    assert "parse" in result.warnings[0].lower() or "failed" in result.warnings[0].lower()


def test_parse_drawio_missing_graph_model_returns_warning():
    result = parse_drawio("<root><something/></root>")
    assert result.warnings


def test_parse_drawio_cylinder_style_maps_to_datastore():
    xml = """\
<mxGraphModel>
  <root>
    <mxCell id="0" /><mxCell id="1" parent="0" />
    <mxCell id="2" value="Database" style="shape=cylinder;" vertex="1" parent="1">
      <mxGeometry as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>"""
    result = parse_drawio(xml)
    db = next(c for c in result.components if c["name"] == "Database")
    assert db["type"] == "on-prem-resource"


def test_parse_drawio_ellipse_maps_to_actor():
    xml = """\
<mxGraphModel>
  <root>
    <mxCell id="0" /><mxCell id="1" parent="0" />
    <mxCell id="2" value="User" style="ellipse;" vertex="1" parent="1">
      <mxGeometry as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>"""
    result = parse_drawio(xml)
    user = next(c for c in result.components if c["name"] == "User")
    assert user["type"] == "actor"


# ── DiagramImportResult ───────────────────────────────────────────────────────


def test_to_yaml_data_has_required_keys():
    result = DiagramImportResult(
        name="test",
        source_format="mermaid",
        components=[{"name": "A", "type": "application"}],
        flows=[{"source": "A", "target": "B"}],
    )
    data = result.to_yaml_data()
    assert "name" in data
    assert "components" in data
    assert "flows" in data


def test_to_yaml_data_omits_empty_strings():
    result = DiagramImportResult(
        name="test",
        source_format="mermaid",
        components=[{"name": "A", "type": "application", "description": ""}],
        flows=[{"source": "A", "target": "B", "label": ""}],
    )
    data = result.to_yaml_data()
    assert "description" not in data["components"][0]
    assert "label" not in data["flows"][0]


def test_to_yaml_data_includes_trust_boundaries_when_present():
    result = DiagramImportResult(
        name="test",
        source_format="mermaid",
        trust_boundaries=[{"name": "Zone A", "description": ""}],
        components=[],
        flows=[],
    )
    data = result.to_yaml_data()
    assert "trust_boundaries" in data


def test_to_yaml_data_omits_trust_boundaries_when_empty():
    result = DiagramImportResult(name="test", source_format="mermaid")
    data = result.to_yaml_data()
    assert "trust_boundaries" not in data


def test_to_yaml_string_is_valid_yaml():
    import yaml

    result = DiagramImportResult(
        name="test",
        source_format="mermaid",
        components=[{"name": "A", "type": "application"}],
        flows=[{"source": "A", "target": "B"}],
    )
    parsed = yaml.safe_load(result.to_yaml_string())
    assert parsed["name"] == "test"
    assert len(parsed["components"]) == 1


# ── parse_diagram dispatch ────────────────────────────────────────────────────


def test_parse_diagram_dispatches_mermaid():
    mmd = "graph TD\n    A[Node A]"
    result = parse_diagram(mmd, "mermaid")
    assert result.source_format == "mermaid"


def test_parse_diagram_dispatches_drawio():
    result = parse_diagram(_DRAWIO_MINIMAL, "drawio")
    assert result.source_format == "drawio"


def test_parse_diagram_raises_on_unknown_format():
    with pytest.raises(ValueError, match="Unsupported format"):
        parse_diagram("", "unknown")
