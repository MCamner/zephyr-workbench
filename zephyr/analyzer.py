from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Union

from zephyr.models import Architecture
from zephyr.validation import load_validated_architecture


def load_architecture(path: Union[str, Path]) -> Architecture:
    return load_validated_architecture(path)


def summarize_architecture(architecture: Architecture) -> str:
    summary = summarize_architecture_data(architecture)
    lines = [
        f"Architecture: {summary['name']}",
        f"Components: {summary['components']}",
        f"Flows: {summary['flows']}",
        f"Risks: {summary['risks']}",
        "",
    ]

    if summary["risk_details"]:
        lines.append("Risks:")
        for risk in summary["risk_details"]:
            lines.append(f"- [{risk['severity'].upper()}] {risk['id']}: {risk['title']}")

    return "\n".join(lines)


def summarize_architecture_data(architecture: Architecture) -> dict:
    return {
        "name": architecture.name,
        "description": architecture.description,
        "components": len(architecture.components),
        "flows": len(architecture.flows),
        "risks": len(architecture.risks),
        "risk_details": [asdict(risk) for risk in architecture.risks],
    }
