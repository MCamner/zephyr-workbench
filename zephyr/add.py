from __future__ import annotations

from pathlib import Path

from zephyr._prompts import _prompt_choice, write_yaml_file
from zephyr.init_wizard import (
    prompt_components,
    prompt_controls,
    prompt_flows,
    prompt_risks,
    prompt_stakeholders,
)
from zephyr.validation import ValidationError, load_architecture_data, load_validated_architecture

_SECTIONS = ["component", "flow", "risk", "control", "stakeholder"]


def run_add(file_path: str) -> int:
    path = Path(file_path)

    try:
        data = load_architecture_data(path)
    except ValidationError as err:
        print("Could not load model:")
        for msg in err.errors:
            print(f"  - {msg}")
        return 1

    name = data.get("name", path.stem)
    n_components = len(data.get("components") or [])
    n_flows = len(data.get("flows") or [])
    n_risks = len(data.get("risks") or [])
    n_controls = len(data.get("controls") or [])
    n_stakeholders = len(data.get("stakeholders") or [])
    print(
        f"{name} — {n_components} components, {n_flows} flows, "
        f"{n_risks} risks, {n_controls} controls, {n_stakeholders} stakeholders"
    )
    print("")

    section = _prompt_choice("What to add", _SECTIONS)

    component_names = [c["name"] for c in (data.get("components") or []) if isinstance(c, dict)]

    if section == "component":
        new_items = prompt_components(minimal=False)
        data.setdefault("components", []).extend(new_items)
        component_names += [c["name"] for c in new_items]

    elif section == "flow":
        if not component_names:
            print("No components defined yet — add components first.")
            return 1
        new_items = prompt_flows(component_names, minimal=False)
        data.setdefault("flows", []).extend(new_items)

    elif section == "risk":
        new_items = prompt_risks(minimal=False)
        data.setdefault("risks", []).extend(new_items)

    elif section == "control":
        if not component_names:
            print("No components defined yet — add components first.")
            return 1
        new_items = prompt_controls(component_names)
        data.setdefault("controls", []).extend(new_items)

    elif section == "stakeholder":
        new_items = prompt_stakeholders()
        data.setdefault("stakeholders", []).extend(new_items)

    write_yaml_file(data, str(path))
    print(f"\nSaved: {path}")

    try:
        load_validated_architecture(path)
        print("Validation passed.")
    except ValidationError as err:
        print("Validation failed:")
        for msg in err.errors:
            print(f"  - {msg}")
        return 1

    return 0
