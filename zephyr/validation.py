from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from zephyr.models import (
    ALLOWED_COMPONENT_TYPES,
    ALLOWED_RISK_SEVERITIES,
    Architecture,
    Component,
    Control,
    Flow,
    Risk,
    Stakeholder,
)
from zephyr.datamodel import (
    AUTH_TYPES,
    CONTROL_TYPES,
    CRITICALITIES,
    DOMAINS,
    ENCRYPTION_TYPES,
    ENVIRONMENTS,
    EXPOSURES,
    FLOW_DIRECTIONS,
    IMPACTS,
    LIKELIHOODS,
    LIFECYCLES,
    STAKEHOLDER_ROLES,
)


class ValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


@dataclass
class ValidationResult:
    architecture: Architecture
    warnings: list[str]


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
    controls = data.get("controls", [])
    stakeholders = data.get("stakeholders", [])
    domains = data.get("domains")
    meta = data.get("meta")

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

    if domains is not None:
        if not isinstance(domains, list):
            errors.append("field 'domains' must be a list")
            domains = []
        else:
            for index, domain in enumerate(domains, start=1):
                if not isinstance(domain, str):
                    errors.append(f"domains[{index}] must be a string")
                elif domain not in DOMAINS:
                    allowed = ", ".join(DOMAINS)
                    errors.append(
                        f"domains[{index}] '{domain}' is invalid; expected one of: {allowed}"
                    )

    if meta is not None:
        if not isinstance(meta, dict):
            errors.append("field 'meta' must be a mapping")
        else:
            owner = meta.get("owner")
            if owner is not None and not isinstance(owner, str):
                errors.append("meta.owner must be a string")

            criticality = meta.get("criticality")
            if criticality is not None:
                if not isinstance(criticality, str):
                    errors.append("meta.criticality must be a string")
                elif criticality not in CRITICALITIES:
                    allowed = ", ".join(CRITICALITIES)
                    errors.append(
                        f"meta.criticality '{criticality}' is invalid; expected one of: {allowed}"
                    )

            environment = meta.get("environment")
            if environment is not None:
                if not isinstance(environment, list):
                    errors.append("meta.environment must be a list")
                else:
                    for index, value in enumerate(environment, start=1):
                        if not isinstance(value, str):
                            errors.append(f"meta.environment[{index}] must be a string")
                        elif value not in ENVIRONMENTS:
                            allowed = ", ".join(ENVIRONMENTS)
                            errors.append(
                                f"meta.environment[{index}] '{value}' is invalid; expected one of: {allowed}"
                            )

    if "controls" in data and not isinstance(controls, list):
        errors.append("field 'controls' must be a list")
        controls = []

    if "stakeholders" in data and not isinstance(stakeholders, list):
        errors.append("field 'stakeholders' must be a list")
        stakeholders = []

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

        component_domain = component.get("domain")
        if component_domain is not None:
            if not isinstance(component_domain, str):
                errors.append(f"{location}.domain must be a string")
            elif component_domain not in DOMAINS:
                allowed = ", ".join(DOMAINS)
                errors.append(
                    f"{location}.domain '{component_domain}' is invalid; expected one of: {allowed}"
                )

        component_description = component.get("description")
        if component_description is not None and not isinstance(component_description, str):
            errors.append(f"{location}.description must be a string")

        component_criticality = component.get("criticality")
        if component_criticality is not None:
            if not isinstance(component_criticality, str):
                errors.append(f"{location}.criticality must be a string")
            elif component_criticality not in CRITICALITIES:
                allowed = ", ".join(CRITICALITIES)
                errors.append(
                    f"{location}.criticality '{component_criticality}' is invalid; expected one of: {allowed}"
                )

        component_exposure = component.get("exposure")
        if component_exposure is not None:
            if not isinstance(component_exposure, str):
                errors.append(f"{location}.exposure must be a string")
            elif component_exposure not in EXPOSURES:
                allowed = ", ".join(EXPOSURES)
                errors.append(
                    f"{location}.exposure '{component_exposure}' is invalid; expected one of: {allowed}"
                )

        component_lifecycle = component.get("lifecycle")
        if component_lifecycle is not None:
            if not isinstance(component_lifecycle, str):
                errors.append(f"{location}.lifecycle must be a string")
            elif component_lifecycle not in LIFECYCLES:
                allowed = ", ".join(LIFECYCLES)
                errors.append(
                    f"{location}.lifecycle '{component_lifecycle}' is invalid; expected one of: {allowed}"
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

        protocol = flow.get("protocol")
        if protocol is not None and not isinstance(protocol, str):
            errors.append(f"{location}.protocol must be a string")

        authentication = flow.get("authentication")
        if authentication is not None:
            if not isinstance(authentication, str):
                errors.append(f"{location}.authentication must be a string")
            elif authentication not in AUTH_TYPES:
                allowed = ", ".join(AUTH_TYPES)
                errors.append(
                    f"{location}.authentication '{authentication}' is invalid; expected one of: {allowed}"
                )

        encryption = flow.get("encryption")
        if encryption is not None:
            if not isinstance(encryption, str):
                errors.append(f"{location}.encryption must be a string")
            elif encryption not in ENCRYPTION_TYPES:
                allowed = ", ".join(ENCRYPTION_TYPES)
                errors.append(
                    f"{location}.encryption '{encryption}' is invalid; expected one of: {allowed}"
                )

        direction = flow.get("direction")
        if direction is not None:
            if not isinstance(direction, str):
                errors.append(f"{location}.direction must be a string")
            elif direction not in FLOW_DIRECTIONS:
                allowed = ", ".join(FLOW_DIRECTIONS)
                errors.append(
                    f"{location}.direction '{direction}' is invalid; expected one of: {allowed}"
                )

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

        description = risk.get("description")
        if description is not None and not isinstance(description, str):
            errors.append(f"{location}.description must be a string")

        mitigation = risk.get("mitigation")
        if mitigation is not None and not isinstance(mitigation, str):
            errors.append(f"{location}.mitigation must be a string")

        likelihood = risk.get("likelihood")
        if likelihood is not None:
            if not isinstance(likelihood, str):
                errors.append(f"{location}.likelihood must be a string")
            elif likelihood not in LIKELIHOODS:
                allowed = ", ".join(LIKELIHOODS)
                errors.append(
                    f"{location}.likelihood '{likelihood}' is invalid; expected one of: {allowed}"
                )

        impact = risk.get("impact")
        if impact is not None:
            if not isinstance(impact, str):
                errors.append(f"{location}.impact must be a string")
            elif impact not in IMPACTS:
                allowed = ", ".join(IMPACTS)
                errors.append(
                    f"{location}.impact '{impact}' is invalid; expected one of: {allowed}"
                )

    for index, control in enumerate(controls, start=1):
        location = f"controls[{index}]"
        if not isinstance(control, dict):
            errors.append(f"{location} must be a mapping")
            continue

        control_name = control.get("name")
        control_type = control.get("type")
        applies_to = control.get("applies_to")
        control_description = control.get("description")

        if not control_name:
            errors.append(f"{location}.name is required")
        elif not isinstance(control_name, str):
            errors.append(f"{location}.name must be a string")

        if not control_type:
            errors.append(f"{location}.type is required")
        elif not isinstance(control_type, str):
            errors.append(f"{location}.type must be a string")
        elif control_type not in CONTROL_TYPES:
            allowed = ", ".join(CONTROL_TYPES)
            errors.append(
                f"{location}.type '{control_type}' is invalid; expected one of: {allowed}"
            )

        if applies_to is None:
            errors.append(f"{location}.applies_to is required")
        elif not isinstance(applies_to, list):
            errors.append(f"{location}.applies_to must be a list")
        else:
            for target_index, target in enumerate(applies_to, start=1):
                if not isinstance(target, str):
                    errors.append(f"{location}.applies_to[{target_index}] must be a string")
                elif target not in component_names:
                    errors.append(
                        f"{location}.applies_to[{target_index}] '{target}' does not match any component"
                    )

        if control_description is not None and not isinstance(control_description, str):
            errors.append(f"{location}.description must be a string")

    for index, stakeholder in enumerate(stakeholders, start=1):
        location = f"stakeholders[{index}]"
        if not isinstance(stakeholder, dict):
            errors.append(f"{location} must be a mapping")
            continue

        stakeholder_name = stakeholder.get("name")
        stakeholder_role = stakeholder.get("role")

        if not stakeholder_name:
            errors.append(f"{location}.name is required")
        elif not isinstance(stakeholder_name, str):
            errors.append(f"{location}.name must be a string")

        if not stakeholder_role:
            errors.append(f"{location}.role is required")
        elif not isinstance(stakeholder_role, str):
            errors.append(f"{location}.role must be a string")
        elif stakeholder_role not in STAKEHOLDER_ROLES:
            allowed = ", ".join(STAKEHOLDER_ROLES)
            errors.append(
                f"{location}.role '{stakeholder_role}' is invalid; expected one of: {allowed}"
            )

    if errors:
        raise ValidationError(errors)


def collect_validation_warnings(data: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    components = data.get("components", [])
    flows = data.get("flows", [])

    component_types = {
        item["name"]: item["type"]
        for item in components
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and isinstance(item.get("type"), str)
    }

    gateway_names = [
        name for name, component_type in component_types.items() if component_type == "access-gateway"
    ]
    if len(gateway_names) == 1:
        warnings.append(f"only one access-gateway detected ({gateway_names[0]})")

    identity_types = {"identity", "identity-provider", "cloud-identity", "on-prem-identity"}

    for flow in flows:
        if not isinstance(flow, dict):
            continue

        source = flow.get("from")
        target = flow.get("to")

        if component_types.get(source) == "endpoint" and component_types.get(target) == "endpoint":
            warnings.append(f"endpoint-to-endpoint flow detected ({source} -> {target})")

        if flow.get("authentication") == "mfa" and component_types.get(target) not in identity_types:
            warnings.append(
                f"MFA flow target should be an identity component ({source} -> {target})"
            )

    return warnings


def architecture_from_data(data: dict[str, Any]) -> Architecture:
    return Architecture(
        name=data["name"],
        description=data.get("description", ""),
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


def load_validated_architecture(path: str | Path) -> Architecture:
    return load_validation_result(path).architecture


def load_validation_result(path: str | Path) -> ValidationResult:
    data = load_architecture_data(path)
    validate_architecture_data(data)
    return ValidationResult(
        architecture=architecture_from_data(data),
        warnings=collect_validation_warnings(data),
    )
