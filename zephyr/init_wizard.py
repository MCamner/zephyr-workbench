from __future__ import annotations

from pathlib import Path

import yaml

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
from zephyr.validation import ValidationError, load_validated_architecture


def run_init_wizard(
    output_path: str | None = None,
    validate: bool = True,
    minimal: bool = False,
    template: str | None = None,
) -> int:
    if template:
        print(f"Template '{template}' is not implemented yet; continuing with the default model.")

    print("Zephyr Init Wizard")
    print("Mode: minimal V1" if minimal else "Mode: guided V1")
    print("")

    model = build_architecture_model(minimal=minimal)
    default_path = output_path or f"examples/{model['name']}.yaml"
    chosen_path = output_path or _prompt_text("Output file", default=default_path)

    should_validate = validate
    if output_path is None and validate:
        should_validate = _prompt_yes_no("Run validation now?", default=True)

    write_yaml_file(model, chosen_path)
    print(f"Saved: {chosen_path}")

    if not should_validate:
        return 0

    try:
        load_validated_architecture(chosen_path)
    except ValidationError as error:
        print("Validation failed:")
        for message in error.errors:
            print(f"- {message}")
        return 1

    print("Validation succeeded.")
    return 0


def prompt_meta(minimal: bool) -> dict:
    meta = {
        "name": _prompt_required_text("Architecture name"),
        "description": _prompt_text("Description", default=""),
    }
    if not minimal:
        meta["owner"] = _prompt_text("Owner", default="")
        meta["environment"] = [_prompt_choice("Environment", ENVIRONMENTS, default="prod")]
        meta["criticality"] = _prompt_choice("Criticality", CRITICALITIES, default="medium")
    return meta


def prompt_components(minimal: bool) -> list[dict]:
    components: list[dict] = []

    while _prompt_yes_no("Add component?", default=not components):
        name = _prompt_required_text("Name")
        component_type = _prompt_choice("Type", COMPONENT_TYPES)
        suggested_domain = TYPE_TO_DOMAIN.get(component_type)

        if suggested_domain:
            print(f"Suggested domain: {suggested_domain}")
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

    return components


def prompt_flows(component_names: list[str], minimal: bool) -> list[dict]:
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

    return flows


def prompt_risks(minimal: bool) -> list[dict]:
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

    return risks


def prompt_controls(component_names: list[str]) -> list[dict]:
    controls: list[dict] = []

    if not component_names:
        return controls

    while _prompt_yes_no("Add control?", default=False):
        controls.append(
            {
                "name": _prompt_required_text("Name"),
                "type": _prompt_choice("Control type", CONTROL_TYPES),
                "applies_to": _prompt_multi_choice("Applies to", component_names),
                "description": _prompt_text("Description", default=""),
            }
        )

    return controls


def prompt_stakeholders() -> list[dict]:
    stakeholders: list[dict] = []

    while _prompt_yes_no("Add stakeholder?", default=not stakeholders):
        stakeholders.append(
            {
                "name": _prompt_required_text("Name"),
                "role": _prompt_choice("Role", STAKEHOLDER_ROLES),
            }
        )

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


def write_yaml_file(model: dict, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    contents = yaml.safe_dump(model, sort_keys=False, allow_unicode=False)
    path.write_text(contents, encoding="utf-8")


def _prompt_text(label: str, default: str | None = None) -> str:
    prompt = f"{label}"
    if default is not None:
        prompt += f" [{default}]"
    prompt += ": "

    value = input(prompt).strip()
    if value:
        return value
    if default is not None:
        return default
    return ""


def _prompt_required_text(label: str) -> str:
    while True:
        value = _prompt_text(label)
        if value:
            return value
        print(f"{label} is required.")


def _prompt_multi_choice(label: str, options: list[str]) -> list[str]:
    """Prompt the user to select one or more items from a list."""
    option_text = "/".join(options)
    print(f"{label} — pick one or more from: {option_text}")
    print("Enter each selection on its own line. Empty line when done.")
    selected: list[str] = []
    while True:
        value = input(f"  {label}: ").strip()
        if not value:
            if selected:
                return selected
            print("At least one selection is required.")
            continue
        if value not in options:
            print(f"Invalid selection. Choose one of: {option_text}")
            continue
        if value in selected:
            print(f"Already added: {value}")
            continue
        selected.append(value)


def _prompt_choice(label: str, options: list[str], default: str | None = None) -> str:
    option_text = "/".join(options)
    prompt = f"{label} [{option_text}]"
    if default is not None:
        prompt += f" [{default}]"
    prompt += ": "

    while True:
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        if value in options:
            return value
        print(f"Invalid selection. Choose one of: {option_text}")


def _prompt_yes_no(label: str, default: bool) -> bool:
    suffix = "y/n"
    prompt = f"{label} ({suffix})"
    prompt += ": " if default is None else f" [{'Y/n' if default else 'y/N'}]: "

    while True:
        value = input(prompt).strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer y or n.")
