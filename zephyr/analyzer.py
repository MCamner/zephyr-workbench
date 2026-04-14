from __future__ import annotations

from pathlib import Path
from typing import Union

from zephyr.models import Architecture
from zephyr.validation import load_validated_architecture


def load_architecture(path: Union[str, Path]) -> Architecture:
    return load_validated_architecture(path)


def summarize_architecture(architecture: Architecture) -> str:
    lines = [
        f"Architecture: {architecture.name}",
        f"Components: {len(architecture.components)}",
        f"Flows: {len(architecture.flows)}",
        f"Risks: {len(architecture.risks)}",
        "",
    ]

    if architecture.risks:
        lines.append("Risks:")
        for risk in architecture.risks:
            lines.append(f"- [{risk.severity.upper()}] {risk.id}: {risk.title}")

    return "\n".join(lines)
