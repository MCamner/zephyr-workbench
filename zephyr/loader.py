from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from zephyr.models import (
    Architecture,
    Component,
    Control,
    Flow,
    Meta,
    Risk,
    Stakeholder,
)


class ValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def load_architecture_data(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    try:
        contents = file_path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ValidationError([f"{file_path}: file not found"]) from error

    try:
        data = yaml.safe_load(contents)
    except yaml.YAMLError as error:
        raise ValidationError([f"{file_path}: invalid YAML: {error}"]) from error

    if not isinstance(data, dict):
        raise ValidationError([f"{file_path}: root document must be a YAML mapping"])

    return data


def _meta_from_data(data: dict[str, Any]) -> Meta | None:
    raw = data.get("meta")
    if not isinstance(raw, dict):
        return None
    return Meta(
        owner=raw.get("owner", ""),
        version=raw.get("version", ""),
        criticality=raw.get("criticality", ""),
        environment=raw.get("environment") or [],
    )


def architecture_from_data(data: dict[str, Any]) -> Architecture:
    return Architecture(
        name=data["name"],
        description=data.get("description", ""),
        meta=_meta_from_data(data),
        components=[
            Component(
                name=item["name"],
                type=item["type"],
                description=item.get("description", ""),
                domain=item.get("domain", ""),
                criticality=item.get("criticality", ""),
                exposure=item.get("exposure", ""),
                lifecycle=item.get("lifecycle", ""),
            )
            for item in data.get("components", [])
        ],
        flows=[
            Flow(
                source=item["from"],
                target=item["to"],
                label=item.get("label", ""),
                protocol=item.get("protocol", ""),
                authentication=item.get("authentication", ""),
                encryption=item.get("encryption", ""),
                direction=item.get("direction", ""),
            )
            for item in data.get("flows", [])
        ],
        risks=[
            Risk(
                id=item["id"],
                title=item["title"],
                severity=item["severity"],
                description=item.get("description", ""),
                mitigation=item.get("mitigation", ""),
                likelihood=item.get("likelihood", ""),
                impact=item.get("impact", ""),
            )
            for item in data.get("risks", [])
        ],
        controls=[
            Control(
                name=item["name"],
                type=item["type"],
                applies_to=item.get("applies_to", []),
                description=item.get("description", ""),
            )
            for item in data.get("controls", [])
        ],
        stakeholders=[
            Stakeholder(
                name=item["name"],
                role=item["role"],
            )
            for item in data.get("stakeholders", [])
        ],
    )
