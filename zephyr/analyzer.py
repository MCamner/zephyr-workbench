from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Union

from zephyr.datamodel import RISK_SCORE_MATRIX
from zephyr.models import Architecture, Meta
from zephyr.validation import load_validated_architecture


def load_architecture(path: Union[str, Path]) -> Architecture:
    return load_validated_architecture(path)


def summarize_architecture(architecture: Architecture) -> str:
    summary = summarize_architecture_data(architecture)

    lines = [
        f"Architecture: {summary['name']}",
    ]
    if summary["description"]:
        lines.append(f"Description: {summary['description']}")

    meta = summary.get("meta")
    if meta:
        if meta.get("owner"):
            lines.append(f"Owner:        {meta['owner']}")
        if meta.get("version"):
            lines.append(f"Version:      {meta['version']}")
        if meta.get("criticality"):
            lines.append(f"Criticality:  {meta['criticality']}")
        if meta.get("environment"):
            lines.append(f"Environment:  {', '.join(meta['environment'])}")

    lines += [
        f"Components:   {summary['components']}",
        f"Flows:        {summary['flows']}",
        f"Risks:        {summary['risks']}",
    ]
    if summary["controls"] > 0:
        lines.append(f"Controls:     {summary['controls']}")
    if summary["stakeholders"] > 0:
        lines.append(f"Stakeholders: {summary['stakeholders']}")
    if summary["trust_boundaries"] > 0:
        lines.append(f"Boundaries:   {summary['trust_boundaries']}")

    if architecture.components:
        lines.append("")
        name_w = max(len(c.name) for c in architecture.components)
        type_w = max(len(c.type) for c in architecture.components)
        for c in architecture.components:
            desc = c.description.strip().replace("\n", " ") if c.description else ""
            if len(desc) > 58:
                desc = desc[:55] + "..."
            row = f"  {c.name:<{name_w}}  {c.type:<{type_w}}  {desc}"
            lines.append(row.rstrip())

    if architecture.flows:
        lines.append("")
        for f in architecture.flows:
            route = f"{f.source} → {f.target}"
            label_parts = [p for p in [f.label, f.authentication, f.encryption] if p]
            label = " | ".join(label_parts)
            if label:
                lines.append(f"  {route:<42}  {label}")
            else:
                lines.append(f"  {route}")

    if summary["risk_details"]:
        lines.append("")
        lines.append("Risks:")
        for risk in summary["risk_details"]:
            severity = risk["severity"].upper()
            score_str = ""
            score = risk.get("score")
            if score is not None:
                score_str = f" score:{score}"
            lines.append(f"- [{severity}{score_str}] {risk['id']}: {risk['title']}")
            meta_parts = []
            if risk.get("likelihood"):
                meta_parts.append(f"likelihood: {risk['likelihood']}")
            if risk.get("impact"):
                meta_parts.append(f"impact: {risk['impact']}")
            if meta_parts:
                lines.append(f"  {' | '.join(meta_parts)}")
            if risk.get("mitigation"):
                lines.append(f"  Mitigation: {risk['mitigation']}")

    if summary["control_details"]:
        lines.append("")
        lines.append("Controls:")
        for control in summary["control_details"]:
            targets = ", ".join(control["applies_to"]) if control["applies_to"] else "—"
            lines.append(f"- [{control['type']}] {control['name']} → {targets}")
            if control.get("description"):
                lines.append(f"  {control['description']}")

    if summary["stakeholder_details"]:
        lines.append("")
        lines.append("Stakeholders:")
        for s in summary["stakeholder_details"]:
            lines.append(f"- {s['name']} ({s['role']})")

    if summary["boundary_details"]:
        lines.append("")
        lines.append("Trust Boundaries:")
        for b in summary["boundary_details"]:
            desc = f" — {b['description']}" if b.get("description") else ""
            lines.append(f"- {b['name']}{desc}")

    return "\n".join(lines)


def _risk_score(severity: str, likelihood: str) -> int | None:
    if not likelihood:
        return None
    return RISK_SCORE_MATRIX.get((severity.lower(), likelihood.lower()))


def summarize_architecture_data(architecture: Architecture) -> dict:
    risk_details = []
    for risk in architecture.risks:
        d = asdict(risk)
        d["score"] = _risk_score(risk.severity, risk.likelihood)
        risk_details.append(d)

    return {
        "name": architecture.name,
        "description": architecture.description,
        "meta": asdict(architecture.meta) if architecture.meta else None,
        "components": len(architecture.components),
        "flows": len(architecture.flows),
        "risks": len(architecture.risks),
        "controls": len(architecture.controls),
        "stakeholders": len(architecture.stakeholders),
        "trust_boundaries": len(architecture.trust_boundaries),
        "risk_details": risk_details,
        "control_details": [asdict(control) for control in architecture.controls],
        "stakeholder_details": [asdict(s) for s in architecture.stakeholders],
        "boundary_details": [asdict(b) for b in architecture.trust_boundaries],
    }
