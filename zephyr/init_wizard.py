from __future__ import annotations

from zephyr._prompts import (
    _print_section,
    _prompt_choice,
    _prompt_multi_choice,
    _prompt_required_text,
    _prompt_text,
    _prompt_yes_no,
    write_yaml_file,
)
from zephyr.datamodel import (
    AUTH_TYPES,
    COMPONENT_TYPES,
    CONTROL_TYPES,
    CRITICALITIES,
    DEFAULT_VERSION,
    DOMAINS,
    ENCRYPTION_TYPES,
    ENVIRONMENTS,
    EXPOSURES,
    FLOW_DIRECTIONS,
    IMPACTS,
    LIKELIHOODS,
    LIFECYCLES,
    SEVERITIES,
    STAKEHOLDER_ROLES,
    TYPE_TO_DOMAIN,
)
from zephyr.templates import get_template, list_templates, template_names
from zephyr.validation import ValidationError, load_validated_architecture


def run_init_wizard(
    output_path: str | None = None,
    validate: bool = True,
    minimal: bool = False,
    template: str | None = None,
) -> int:
    if template:
        return _run_from_template(template, output_path=output_path, validate=validate)

    print("Zephyr Init Wizard")
    print("Mode: minimal V1" if minimal else "Mode: guided V1")

    model = build_architecture_model(minimal=minimal)
    default_path = output_path or f"examples/{model['name']}.yaml"
    chosen_path = output_path or _prompt_text("Output file", default=default_path)

    should_validate = validate
    if output_path is None and validate:
        should_validate = _prompt_yes_no("Run validation now?", default=True)

    write_yaml_file(model, chosen_path)
    print(f"\nSaved: {chosen_path}")

    if not should_validate:
        return 0

    try:
        load_validated_architecture(chosen_path)
    except ValidationError as error:
        print("Validation failed:")
        for message in error.errors:
            print(f"  - {message}")
        return 1

    print("Validation passed.")
    return 0


def _run_from_template(
    template_name: str,
    output_path: str | None = None,
    validate: bool = True,
) -> int:
    model = get_template(template_name)
    if model is None:
        available = ", ".join(template_names())
        print(f"Unknown template '{template_name}'. Available: {available}")
        return 1

    print(f"Template: {template_name}")
    name = _prompt_text("Architecture name", default=model["name"])
    model["name"] = name

    default_path = output_path or f"examples/{name}.yaml"
    chosen_path = output_path or _prompt_text("Output file", default=default_path)

    write_yaml_file(model, chosen_path)
    print(f"\nSaved: {chosen_path}")

    if not validate:
        return 0

    try:
        load_validated_architecture(chosen_path)
    except ValidationError as error:
        print("Validation failed:")
        for message in error.errors:
            print(f"  - {message}")
        return 1

    print("Validation passed.")
    return 0


def prompt_meta(minimal: bool) -> dict:
    _print_section("Architecture")
    meta = {
        "name": _prompt_required_text("Name"),
        "description": _prompt_text("Description", default=""),
    }
    if not minimal:
        meta["owner"] = _prompt_text("Owner", default="")
        meta["environment"] = [_prompt_choice("Environment", ENVIRONMENTS, default="prod")]
        meta["criticality"] = _prompt_choice("Criticality", CRITICALITIES, default="medium")
    return meta


def prompt_components(minimal: bool) -> list[dict]:
    _print_section("Components")
    components: list[dict] = []

    while _prompt_yes_no("Add component?", default=not components):
        name = _prompt_required_text("Name")
        component_type = _prompt_choice("Type", COMPONENT_TYPES)
        suggested_domain = TYPE_TO_DOMAIN.get(component_type)

        if suggested_domain:
            domain = _prompt_choice("Domain", DOMAINS, default=suggested_domain)
        else:
            domain = _prompt_choice("Domain", DOMAINS)

        component = {
            "name": name,
            "type": component_type,
            "domain": domain,
            "criticality": "medium",
            "exposure": "internal",
            "lifecycle": "active",
        }

        if not minimal:
            description = _prompt_text("Description", default="")
            if description:
                component["description"] = description
            component["criticality"] = _prompt_choice(
                "Criticality", CRITICALITIES, default="medium"
            )
            component["exposure"] = _prompt_choice("Exposure", EXPOSURES, default="internal")
            component["lifecycle"] = _prompt_choice("Lifecycle", LIFECYCLES, default="active")

        components.append(component)
        print(f"  Added: {name} ({component_type})")

    return components


def prompt_flows(component_names: list[str], minimal: bool) -> list[dict]:
    _print_section("Flows")
    flows: list[dict] = []

    while _prompt_yes_no("Add flow?", default=bool(component_names) and not flows):
        flow = {
            "from": _prompt_choice("From", component_names),
            "to": _prompt_choice("To", component_names),
            "label": _prompt_required_text("Label"),
            "direction": "outbound",
        }

        if not minimal:
            protocol = _prompt_text("Protocol", default="")
            authentication = _prompt_choice("Authentication", AUTH_TYPES, default="none")
            encryption = _prompt_choice("Encryption", ENCRYPTION_TYPES, default="none")
            direction = _prompt_choice("Direction", FLOW_DIRECTIONS, default="outbound")

            if protocol:
                flow["protocol"] = protocol
            if authentication != "none":
                flow["authentication"] = authentication
            if encryption != "none":
                flow["encryption"] = encryption
            flow["direction"] = direction

        flows.append(flow)
        print(f"  Added: {flow['from']} → {flow['to']}")

    return flows


def prompt_risks(minimal: bool) -> list[dict]:
    _print_section("Risks")
    risks: list[dict] = []

    while _prompt_yes_no("Add risk?", default=False):
        risk = {
            "id": _prompt_required_text("Risk ID"),
            "title": _prompt_required_text("Title"),
            "severity": _prompt_choice("Severity", SEVERITIES),
            "likelihood": "medium",
            "impact": "medium",
        }

        if not minimal:
            risk["likelihood"] = _prompt_choice("Likelihood", LIKELIHOODS, default="medium")
            risk["impact"] = _prompt_choice("Impact", IMPACTS, default="medium")

            description = _prompt_text("Description", default="")
            mitigation = _prompt_text("Mitigation", default="")
            if description:
                risk["description"] = description
            if mitigation:
                risk["mitigation"] = mitigation

        risks.append(risk)
        print(f"  Added: [{risk['severity'].upper()}] {risk['id']}: {risk['title']}")

    return risks


def prompt_controls(component_names: list[str]) -> list[dict]:
    _print_section("Controls")
    controls: list[dict] = []

    if not component_names:
        return controls

    while _prompt_yes_no("Add control?", default=False):
        name = _prompt_required_text("Name")
        control = {
            "name": name,
            "type": _prompt_choice("Control type", CONTROL_TYPES),
            "applies_to": _prompt_multi_choice("Applies to", component_names),
            "description": _prompt_text("Description", default=""),
        }
        controls.append(control)
        targets = ", ".join(control["applies_to"])
        print(f"  Added: {name} [{control['type']}] → {targets}")

    return controls


def prompt_stakeholders() -> list[dict]:
    _print_section("Stakeholders")
    stakeholders: list[dict] = []

    while _prompt_yes_no("Add stakeholder?", default=not stakeholders):
        name = _prompt_required_text("Name")
        role = _prompt_choice("Role", STAKEHOLDER_ROLES)
        stakeholders.append({"name": name, "role": role})
        print(f"  Added: {name} ({role})")

    return stakeholders


def build_architecture_model(minimal: bool = False) -> dict:
    meta = prompt_meta(minimal=minimal)
    components = prompt_components(minimal=minimal)
    component_names = [component["name"] for component in components]

    meta_block = {"version": DEFAULT_VERSION}

    owner = meta.get("owner")
    if owner:
        meta_block["owner"] = owner

    environment = meta.get("environment")
    if environment:
        meta_block["environment"] = environment

    criticality = meta.get("criticality")
    if criticality:
        meta_block["criticality"] = criticality

    model = {
        "name": meta["name"],
        "description": meta["description"],
        "meta": meta_block,
        "domains": list(DOMAINS),
        "components": components,
        "flows": prompt_flows(component_names, minimal=minimal),
        "risks": prompt_risks(minimal=minimal),
    }

    if not minimal:
        model["controls"] = prompt_controls(component_names)
        model["stakeholders"] = prompt_stakeholders()

    return model
