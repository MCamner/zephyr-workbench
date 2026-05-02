from __future__ import annotations

from pathlib import Path

import yaml

_LIST_THRESHOLD = 4


def write_yaml_file(model: dict, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    contents = yaml.safe_dump(model, sort_keys=False, allow_unicode=False)
    path.write_text(contents, encoding="utf-8")


def _print_section(title: str) -> None:
    width = 48
    dashes = "─" * max(0, width - len(title) - 3)
    print(f"\n── {title} {dashes}")


def _prompt_text(label: str, default: str | None = None) -> str:
    prompt = f"  {label}"
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
        print(f"  {label} is required.")


def _prompt_multi_choice(label: str, options: list[str]) -> list[str]:
    selected: list[str] = []
    while True:
        print(f"\n  {label} (empty line when done):")
        for i, opt in enumerate(options, 1):
            check = "✓" if opt in selected else " "
            print(f"    [{check}] {i:2}. {opt}")
        value = input("  → ").strip()
        if not value:
            if selected:
                return selected
            print("  At least one selection is required.")
            continue
        resolved = _resolve_option(value, options)
        if resolved is None:
            print(f"  Invalid. Enter a number (1–{len(options)}) or exact name.")
            continue
        if resolved in selected:
            print(f"  Already added: {resolved}")
            continue
        selected.append(resolved)


def _prompt_choice(label: str, options: list[str], default: str | None = None) -> str:
    if len(options) > _LIST_THRESHOLD:
        return _prompt_choice_list(label, options, default)
    return _prompt_choice_inline(label, options, default)


def _prompt_choice_inline(label: str, options: list[str], default: str | None = None) -> str:
    option_text = "/".join(options)
    prompt = f"  {label} [{option_text}]"
    if default is not None:
        prompt += f" [{default}]"
    prompt += ": "
    while True:
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        if value in options:
            return value
        print(f"  Invalid selection. Choose one of: {option_text}")


def _prompt_choice_list(label: str, options: list[str], default: str | None = None) -> str:
    while True:
        print(f"\n  {label}:")
        for i, opt in enumerate(options, 1):
            marker = "  ← default" if opt == default else ""
            print(f"    {i:2}. {opt}{marker}")
        hint = f" [{default}]" if default else ""
        value = input(f"  → {hint}: ").strip()
        if not value and default is not None:
            return default
        resolved = _resolve_option(value, options)
        if resolved is not None:
            return resolved
        print(f"  Invalid. Enter a number (1–{len(options)}) or exact name.")


def _resolve_option(value: str, options: list[str]) -> str | None:
    if value.isdigit():
        idx = int(value) - 1
        if 0 <= idx < len(options):
            return options[idx]
        return None
    return value if value in options else None


def _prompt_yes_no(label: str, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    prompt = f"  {label} [{suffix}]: "
    while True:
        value = input(prompt).strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("  Please answer y or n.")
