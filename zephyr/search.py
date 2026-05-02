from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from zephyr.models import Architecture


@dataclass
class _Filter:
    kind: Literal["eq", "missing"]
    field: str
    value: str = ""


def _parse_filters(query: str) -> list[_Filter]:
    filters: list[_Filter] = []
    for part in query.split(","):
        part = part.strip()
        if not part:
            continue
        if part.startswith("missing="):
            filters.append(_Filter(kind="missing", field=part[len("missing="):].strip()))
        elif "=" in part:
            field, value = part.split("=", 1)
            filters.append(_Filter(kind="eq", field=field.strip(), value=value.strip()))
    return filters


def _matches(item_dict: dict, filters: list[_Filter]) -> bool:
    for f in filters:
        if f.kind == "missing":
            if item_dict.get(f.field):
                return False
        else:
            val = str(item_dict.get(f.field, "")).lower()
            if val != f.value.lower():
                return False
    return True


def search_architecture(architecture: Architecture, query: str) -> str:
    """Filter components, flows, risks, controls, and stakeholders by field=value.

    Supports single and multi-filter queries (comma-separated, all must match):
      type=endpoint
      severity=high,missing=mitigation
      type=endpoint,exposure=external
      missing=mitigation
    """
    filters = _parse_filters(query.strip())
    lines: list[str] = []

    comp_hits = [
        c for c in architecture.components
        if _matches({"name": c.name, "type": c.type, "domain": c.domain,
                     "criticality": c.criticality, "exposure": c.exposure,
                     "lifecycle": c.lifecycle, "description": c.description}, filters)
    ]
    if comp_hits:
        lines.append("Components:")
        for c in comp_hits:
            meta = [c.type]
            if c.criticality:
                meta.append(c.criticality)
            if c.exposure:
                meta.append(c.exposure)
            lines.append(f"  {c.name}  [{', '.join(meta)}]")

    flow_hits = [
        f for f in architecture.flows
        if _matches({"from": f.source, "to": f.target, "label": f.label,
                     "protocol": f.protocol, "authentication": f.authentication,
                     "encryption": f.encryption, "direction": f.direction}, filters)
    ]
    if flow_hits:
        if lines:
            lines.append("")
        lines.append("Flows:")
        for f in flow_hits:
            meta = []
            if f.authentication:
                meta.append(f"auth:{f.authentication}")
            if f.encryption:
                meta.append(f"enc:{f.encryption}")
            suffix = f"  [{', '.join(meta)}]" if meta else ""
            lines.append(f"  {f.source} → {f.target} ({f.label}){suffix}")

    risk_hits = [
        r for r in architecture.risks
        if _matches({"id": r.id, "title": r.title, "severity": r.severity,
                     "likelihood": r.likelihood, "impact": r.impact,
                     "mitigation": r.mitigation, "description": r.description}, filters)
    ]
    if risk_hits:
        if lines:
            lines.append("")
        lines.append("Risks:")
        for r in risk_hits:
            lines.append(f"  [{r.severity.upper()}] {r.id}: {r.title}")
            if r.mitigation:
                lines.append(f"    Mitigation: {r.mitigation}")

    ctrl_hits = [
        c for c in architecture.controls
        if _matches({"name": c.name, "type": c.type, "description": c.description}, filters)
    ]
    if ctrl_hits:
        if lines:
            lines.append("")
        lines.append("Controls:")
        for c in ctrl_hits:
            targets = ", ".join(c.applies_to)
            lines.append(f"  [{c.type}] {c.name} → {targets}")

    sh_hits = [
        s for s in architecture.stakeholders
        if _matches({"name": s.name, "role": s.role}, filters)
    ]
    if sh_hits:
        if lines:
            lines.append("")
        lines.append("Stakeholders:")
        for s in sh_hits:
            lines.append(f"  {s.name} ({s.role})")

    if not lines:
        return f'No results for "{query}".'

    return "\n".join(lines)
