from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml

from zephyr.models import Architecture, Component, Flow, Risk


def load_architecture(path: Union[str, Path]) -> Architecture:
    file_path = Path(path)
    data = yaml.safe_load(file_path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"{file_path} does not contain a YAML mapping")

    return Architecture(
        name=data["name"],
        components=[
            Component(name=item["name"], type=item["type"])
            for item in data.get("components", [])
        ],
        flows=[
            Flow(
                source=item["from"],
                target=item["to"],
                label=item.get("label", ""),
            )
            for item in data.get("flows", [])
        ],
        risks=[
            Risk(
                id=item["id"],
                title=item["title"],
                severity=item["severity"],
            )
            for item in data.get("risks", [])
        ],
    )


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
