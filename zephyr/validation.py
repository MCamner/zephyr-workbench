from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from zephyr.models import (
    ALLOWED_COMPONENT_TYPES,
    ALLOWED_RISK_SEVERITIES,
    Architecture,
    Component,
    Flow,
    Risk,
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


def validate_architecture_data(data: dict[str, Any]) -> None:
    errors: list[str] = []

    for field in ("name", "components", "flows"):
        if field not in data:
            errors.append(f"missing required top-level field: {field}")

    name = data.get("name")
    if name is not None and not isinstance(name, str):
        errors.append("field 'name' must be a string")

    description = data.get("description")
    if description is not None and not isinstance(description, str):
        errors.append("field 'description' must be a string")

    components = data.get("components", [])
    flows = data.get("flows", [])
    risks = data.get("risks", [])

    if "components" in data and not isinstance(components, list):
        errors.append("field 'components' must be a list")
        components = []
    elif isinstance(components, list) and not components:
        errors.append("field 'components' must contain at least one component")

    if "flows" in data and not isinstance(flows, list):
        errors.append("field 'flows' must be a list")
        flows = []

    if "risks" in data and not isinstance(risks, list):
        errors.append("field 'risks' must be a list")
        risks = []

    component_names: set[str] = set()
    risk_ids: set[str] = set()

    for index, component in enumerate(components, start=1):
        location = f"components[{index}]"
        if not isinstance(component, dict):
            errors.append(f"{location} must be a mapping")
            continue

        component_name = component.get("name")
        component_type = component.get("type")

        if not component_name:
            errors.append(f"{location}.name is required")
        elif not isinstance(component_name, str):
            errors.append(f"{location}.name must be a string")
        elif component_name in component_names:
            errors.append(f"duplicate component name: {component_name}")
        else:
            component_names.add(component_name)

        if not component_type:
            errors.append(f"{location}.type is required")
        elif not isinstance(component_type, str):
            errors.append(f"{location}.type must be a string")
        elif component_type not in ALLOWED_COMPONENT_TYPES:
            allowed = ", ".join(sorted(ALLOWED_COMPONENT_TYPES))
            errors.append(
                f"{location}.type '{component_type}' is invalid; expected one of: {allowed}"
            )

    for index, flow in enumerate(flows, start=1):
        location = f"flows[{index}]"
        if not isinstance(flow, dict):
            errors.append(f"{location} must be a mapping")
            continue

        source = flow.get("from")
        target = flow.get("to")

        if not source:
            errors.append(f"{location}.from is required")
        elif not isinstance(source, str):
            errors.append(f"{location}.from must be a string")
        elif source not in component_names:
            errors.append(f"{location}.from '{source}' does not match any component")

        if not target:
            errors.append(f"{location}.to is required")
        elif not isinstance(target, str):
            errors.append(f"{location}.to must be a string")
        elif target not in component_names:
            errors.append(f"{location}.to '{target}' does not match any component")

        label = flow.get("label", "")
        if label and not isinstance(label, str):
            errors.append(f"{location}.label must be a string when provided")

    for index, risk in enumerate(risks, start=1):
        location = f"risks[{index}]"
        if not isinstance(risk, dict):
            errors.append(f"{location} must be a mapping")
            continue

        risk_id = risk.get("id")
        title = risk.get("title")
        severity = risk.get("severity")

        if not risk_id:
            errors.append(f"{location}.id is required")
        elif not isinstance(risk_id, str):
            errors.append(f"{location}.id must be a string")
        elif risk_id in risk_ids:
            errors.append(f"duplicate risk id: {risk_id}")
        else:
            risk_ids.add(risk_id)

        if not title:
            errors.append(f"{location}.title is required")
        elif not isinstance(title, str):
            errors.append(f"{location}.title must be a string")

        if not severity:
            errors.append(f"{location}.severity is required")
        elif not isinstance(severity, str):
            errors.append(f"{location}.severity must be a string")
        elif severity not in ALLOWED_RISK_SEVERITIES:
            allowed = ", ".join(sorted(ALLOWED_RISK_SEVERITIES))
            errors.append(
                f"{location}.severity '{severity}' is invalid; expected one of: {allowed}"
            )

    if errors:
        raise ValidationError(errors)


def architecture_from_data(data: dict[str, Any]) -> Architecture:
    return Architecture(
        name=data["name"],
        description=data.get("description", ""),
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


def load_validated_architecture(path: str | Path) -> Architecture:
    data = load_architecture_data(path)
    validate_architecture_data(data)
    return architecture_from_data(data)
