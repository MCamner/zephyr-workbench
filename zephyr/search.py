from __future__ import annotations

from zephyr.models import Architecture


def search_architecture(architecture: Architecture, query: str) -> str:
    """Filter components, flows, risks, controls, and stakeholders by field=value.

    Supports:
      - type=endpoint
      - severity=high
      - encryption=none
      - authentication=mfa
      - criticality=mission-critical
      - missing=mitigation   (items where the field is empty)

    If no filter is given, all items across all sections are listed.
    """
    query = query.strip()
    missing_field: str | None = None
    filter_field: str | None = None
    filter_value: str | None = None

    if query.startswith("missing="):
        missing_field = query[len("missing="):]
    elif "=" in query:
        filter_field, filter_value = query.split("=", 1)

    lines: list[str] = []

    def _matches(item_dict: dict) -> bool:
        if missing_field:
            return not item_dict.get(missing_field)
        if filter_field:
            val = str(item_dict.get(filter_field, "")).lower()
            return val == filter_value.lower()
        return True

    # components
    comp_hits = [
        c for c in architecture.components
        if _matches({"name": c.name, "type": c.type, "domain": c.domain,
                     "criticality": c.criticality, "exposure": c.exposure,
                     "lifecycle": c.lifecycle, "description": c.description})
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

    # flows
    flow_hits = [
        f for f in architecture.flows
        if _matches({"from": f.source, "to": f.target, "label": f.label,
                     "protocol": f.protocol, "authentication": f.authentication,
                     "encryption": f.encryption, "direction": f.direction})
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

    # risks
    risk_hits = [
        r for r in architecture.risks
        if _matches({"id": r.id, "title": r.title, "severity": r.severity,
                     "likelihood": r.likelihood, "impact": r.impact,
                     "mitigation": r.mitigation, "description": r.description})
    ]
    if risk_hits:
        if lines:
            lines.append("")
        lines.append("Risks:")
        for r in risk_hits:
            lines.append(f"  [{r.severity.upper()}] {r.id}: {r.title}")
            if r.mitigation:
                lines.append(f"    Mitigation: {r.mitigation}")

    # controls
    ctrl_hits = [
        c for c in architecture.controls
        if _matches({"name": c.name, "type": c.type, "description": c.description})
    ]
    if ctrl_hits:
        if lines:
            lines.append("")
        lines.append("Controls:")
        for c in ctrl_hits:
            targets = ", ".join(c.applies_to)
            lines.append(f"  [{c.type}] {c.name} → {targets}")

    # stakeholders
    sh_hits = [
        s for s in architecture.stakeholders
        if _matches({"name": s.name, "role": s.role})
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
