from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Union

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

    if summary["risk_details"]:
        lines.append("")
        lines.append("Risks:")
        for risk in summary["risk_details"]:
            severity = risk["severity"].upper()
            lines.append(f"- [{severity}] {risk['id']}: {risk['title']}")
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

    return "\n".join(lines)


def summarize_architecture_data(architecture: Architecture) -> dict:
    return {
        "name": architecture.name,
        "description": architecture.description,
        "meta": asdict(architecture.meta) if architecture.meta else None,
        "components": len(architecture.components),
        "flows": len(architecture.flows),
        "risks": len(architecture.risks),
        "controls": len(architecture.controls),
        "stakeholders": len(architecture.stakeholders),
        "risk_details": [asdict(risk) for risk in architecture.risks],
        "control_details": [asdict(control) for control in architecture.controls],
        "stakeholder_details": [asdict(s) for s in architecture.stakeholders],
    }
