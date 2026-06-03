"""Diagram intelligence: parse Mermaid and draw.io diagrams into Zephyr YAML data."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from zephyr.datamodel import COMPONENT_TYPES

_KNOWN_TYPES: frozenset[str] = frozenset(COMPONENT_TYPES)

# Mermaid shape → fallback Zephyr component type
_SHAPE_TYPE: dict[str, str] = {
    "rect": "application",
    "round": "application",
    "cylinder": "on-prem-resource",
    "circle": "actor",
    "rhombus": "access-policy",
    "asymm": "endpoint",
}

# ── Mermaid regex patterns ────────────────────────────────────────────────────

_RE_COMMENT = re.compile(r"^\s*%%\s+(.+)\s*$")
_RE_GRAPH_START = re.compile(r"^\s*(graph|flowchart)\s+", re.IGNORECASE)
_RE_CLASSDEF = re.compile(r"^\s*classDef\s+", re.IGNORECASE)
_RE_CLASS_ASSIGN = re.compile(r"^\s*class\s+[\w,]+\s+\w+\s*$")
_RE_SUBGRAPH_START = re.compile(r'^\s*subgraph\s+(\S+)(?:\s+\[?"?([^"\]]*)"?\]?)?\s*$')
_RE_SUBGRAPH_END = re.compile(r"^\s*end\s*$")

# Arrow pattern covers: -->, ---, ===, ==>. -.-> and variants
_ARROW = r"(?:-{2,}>?|={2,}>?|-\.-+>?|--[ox])"

_RE_EDGE_LABELED = re.compile(rf"^\s*(\w+)\s*{_ARROW}\|([^|]*)\|\s*(\w+)")
_RE_EDGE_PLAIN = re.compile(rf"^\s*(\w+)\s*{_ARROW}\s*(\w+)\s*$")

# Node shape patterns (checked in order)
_RE_NODE_CYLINDER = re.compile(r'^\s*(\w+)\[\("?([^")\]]*)"?\)\]')  # [(text)]
_RE_NODE_CIRCLE = re.compile(r'^\s*(\w+)\(\("?([^")]*)"?\)\)')       # ((text))
_RE_NODE_RHOMBUS = re.compile(r'^\s*(\w+)\{"?([^"}\]]*)"?\}')        # {text}
_RE_NODE_ASYMM = re.compile(r'^\s*(\w+)>"?([^"\]]*)"?\]')            # >text]
_RE_NODE_RECT = re.compile(r'^\s*(\w+)\["?([^"\]]*)"?\]')            # [text]
_RE_NODE_ROUND = re.compile(r'^\s*(\w+)\("?([^")]*)"?\)\s*$')        # (text)

# Extract Zephyr type hint from label "Component Name (type)"
_RE_LABEL_TYPE = re.compile(r"^(.+?)\s+\(([^)]+)\)\s*$")


# ── data type ────────────────────────────────────────────────────────────────


@dataclass
class DiagramImportResult:
    name: str
    source_format: str
    components: list[dict] = field(default_factory=list)
    flows: list[dict] = field(default_factory=list)
    trust_boundaries: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_yaml_data(self) -> dict:
        data: dict = {
            "name": self.name,
            "description": f"Imported from {self.source_format} diagram",
        }
        if self.trust_boundaries:
            data["trust_boundaries"] = self.trust_boundaries

        data["components"] = [_clean(c) for c in self.components]
        flows = []
        for flow in self.flows:
            cleaned = _clean(flow)
            if "source" in cleaned:
                cleaned["from"] = cleaned.pop("source")
            if "target" in cleaned:
                cleaned["to"] = cleaned.pop("target")
            flows.append(cleaned)
        data["flows"] = flows
        return data

    def to_yaml_string(self) -> str:
        return yaml.dump(
            self.to_yaml_data(),
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )


# ── helpers ───────────────────────────────────────────────────────────────────


def _clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if v not in ("", None, [])}


def _parse_label(label: str, shape_type: str) -> tuple[str, str]:
    """Return (display_name, zephyr_type) from a Mermaid node label."""
    label = label.strip().strip('"').strip()
    m = _RE_LABEL_TYPE.match(label)
    if m:
        candidate = m.group(2).strip()
        if candidate in _KNOWN_TYPES:
            return m.group(1).strip(), candidate
    return label, _SHAPE_TYPE.get(shape_type, "application")


def _register_node(
    node_to_name: dict[str, str],
    node_to_comp: dict[str, dict],
    node_id: str,
    raw_label: str,
    shape_type: str,
    trust_boundary: str | None,
) -> None:
    if node_id in node_to_comp:
        return
    name, ztype = _parse_label(raw_label, shape_type)
    comp: dict = {"name": name, "type": ztype}
    if trust_boundary:
        comp["trust_boundary"] = trust_boundary
    node_to_name[node_id] = name
    node_to_comp[node_id] = comp


# ── Mermaid parser ────────────────────────────────────────────────────────────


def parse_mermaid(text: str) -> DiagramImportResult:
    """Parse a Mermaid graph/flowchart diagram into a DiagramImportResult."""
    arch_name = "imported-architecture"
    node_to_name: dict[str, str] = {}
    node_to_comp: dict[str, dict] = {}
    raw_edges: list[tuple[str, str, str]] = []  # (src_id, label, tgt_id)
    boundaries: list[dict] = []
    warnings: list[str] = []
    current_boundary: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Architecture name from first %% comment
        if m := _RE_COMMENT.match(line):
            if arch_name == "imported-architecture":
                arch_name = m.group(1).strip()
            continue

        # Skip structural/style lines
        if _RE_GRAPH_START.match(line) or _RE_CLASSDEF.match(line):
            continue
        if _RE_CLASS_ASSIGN.match(line):
            continue

        # Subgraph → trust boundary
        if m := _RE_SUBGRAPH_START.match(line):
            bname = (m.group(2) or m.group(1)).strip().strip('"')
            current_boundary = bname
            boundaries.append({"name": bname, "description": ""})
            continue

        if _RE_SUBGRAPH_END.match(line):
            current_boundary = None
            continue

        # Edges — check before nodes (both start with word chars)
        if m := _RE_EDGE_LABELED.match(line):
            raw_edges.append((m.group(1), m.group(2).strip(), m.group(3)))
            continue

        if m := _RE_EDGE_PLAIN.match(line):
            raw_edges.append((m.group(1), "", m.group(2)))
            continue

        # Nodes by shape
        if m := _RE_NODE_CYLINDER.match(line):
            _register_node(node_to_name, node_to_comp, m.group(1), m.group(2), "cylinder", current_boundary)
            continue

        if m := _RE_NODE_CIRCLE.match(line):
            _register_node(node_to_name, node_to_comp, m.group(1), m.group(2), "circle", current_boundary)
            continue

        if m := _RE_NODE_RHOMBUS.match(line):
            _register_node(node_to_name, node_to_comp, m.group(1), m.group(2), "rhombus", current_boundary)
            continue

        if m := _RE_NODE_ASYMM.match(line):
            _register_node(node_to_name, node_to_comp, m.group(1), m.group(2), "asymm", current_boundary)
            continue

        if m := _RE_NODE_RECT.match(line):
            _register_node(node_to_name, node_to_comp, m.group(1), m.group(2), "rect", current_boundary)
            continue

        if m := _RE_NODE_ROUND.match(line):
            _register_node(node_to_name, node_to_comp, m.group(1), m.group(2), "round", current_boundary)
            continue

    # Resolve edge node IDs to display names
    flows: list[dict] = []
    for src_id, label, tgt_id in raw_edges:
        src = node_to_name.get(src_id, src_id.replace("_", " "))
        tgt = node_to_name.get(tgt_id, tgt_id.replace("_", " "))
        flow: dict = {"source": src, "target": tgt}
        if label:
            flow["label"] = label
        flows.append(flow)

    return DiagramImportResult(
        name=arch_name,
        source_format="mermaid",
        components=list(node_to_comp.values()),
        flows=flows,
        trust_boundaries=boundaries,
        warnings=warnings,
    )


# ── draw.io parser ────────────────────────────────────────────────────────────


def _infer_drawio_type(style: str) -> str:
    s = style.lower()
    if "shape=cylinder" in s or "shape=mxgraph.flowchart.database" in s:
        return "on-prem-resource"
    if "ellipse" in s:
        return "actor"
    if "rhombus" in s:
        return "access-policy"
    if "shape=cloud" in s or "shape=mxgraph.cisco" in s:
        return "endpoint"
    return "application"


def parse_drawio(text: str) -> DiagramImportResult:
    """Parse a draw.io (mxGraph XML) diagram into a DiagramImportResult."""
    try:
        root_el = ET.fromstring(text)
    except ET.ParseError as exc:
        return DiagramImportResult(
            name="imported-architecture",
            source_format="drawio",
            warnings=[f"Failed to parse draw.io XML: {exc}"],
        )

    graph_model = (
        root_el
        if root_el.tag == "mxGraphModel"
        else root_el.find(".//mxGraphModel")
    )
    if graph_model is None:
        return DiagramImportResult(
            name="imported-architecture",
            source_format="drawio",
            warnings=["No mxGraphModel element found in draw.io file"],
        )

    cells: dict[str, ET.Element] = {}
    containers: set[str] = set()

    for cell in graph_model.iter("mxCell"):
        cid = cell.get("id", "")
        cells[cid] = cell
        style = cell.get("style", "")
        if cell.get("vertex") == "1" and ("swimlane" in style or "group" in style.lower()):
            containers.add(cid)

    components: list[dict] = []
    flows: list[dict] = []
    trust_boundaries: list[dict] = []
    warnings: list[str] = []
    id_to_name: dict[str, str] = {}

    # Collect containers as trust boundaries
    for cid in containers:
        cell = cells[cid]
        bname = cell.get("value", "").strip() or f"Group-{cid}"
        trust_boundaries.append({"name": bname, "description": ""})
        id_to_name[cid] = bname

    # Collect vertices as components
    for cid, cell in cells.items():
        if cell.get("vertex") != "1" or cid in containers or cid in ("0", "1"):
            continue
        value = cell.get("value", "").strip()
        if not value:
            continue
        style = cell.get("style", "")
        ztype = _infer_drawio_type(style)
        parent_id = cell.get("parent", "")
        comp: dict = {"name": value, "type": ztype}
        if parent_id in containers:
            comp["trust_boundary"] = id_to_name[parent_id]
        components.append(comp)
        id_to_name[cid] = value

    # Collect edges as flows
    for cid, cell in cells.items():
        if cell.get("edge") != "1":
            continue
        src_id = cell.get("source", "")
        tgt_id = cell.get("target", "")
        label = cell.get("value", "").strip()
        src_name = id_to_name.get(src_id, "")
        tgt_name = id_to_name.get(tgt_id, "")
        if not src_name or not tgt_name:
            warnings.append(f"Edge {cid}: unresolved source or target")
            continue
        flow: dict = {"source": src_name, "target": tgt_name}
        if label:
            flow["label"] = label
        flows.append(flow)

    # Extract diagram name from <diagram name="..."> if present
    arch_name = "imported-architecture"
    if (diagram_el := root_el.find("diagram")) is not None:
        page_name = diagram_el.get("name", "").strip()
        if page_name:
            arch_name = page_name

    return DiagramImportResult(
        name=arch_name,
        source_format="drawio",
        components=components,
        flows=flows,
        trust_boundaries=trust_boundaries,
        warnings=warnings,
    )


# ── public API ────────────────────────────────────────────────────────────────


def detect_format(path: str | Path) -> str:
    """Detect diagram format from file extension. Returns 'mermaid' or 'drawio'."""
    suffix = Path(path).suffix.lower()
    if suffix in (".xml", ".drawio"):
        return "drawio"
    return "mermaid"  # .mmd, .md, or unknown


def parse_diagram(text: str, format: str) -> DiagramImportResult:
    """Parse a diagram string into a DiagramImportResult.

    format: 'mermaid' or 'drawio'
    """
    if format == "mermaid":
        return parse_mermaid(text)
    if format == "drawio":
        return parse_drawio(text)
    raise ValueError(f"Unsupported format: {format!r}. Expected 'mermaid' or 'drawio'.")
