from __future__ import annotations

from zephyr.datamodel import (
    AUTH_TYPES,
    COMPONENT_TYPES,
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
    SEVERITIES,
    STAKEHOLDER_ROLES,
)

_WIDTH = 50


def _section(title: str) -> str:
    dashes = "─" * max(0, _WIDTH - len(title) - 4)
    return f"\n─── {title} {dashes}"


def _row(label: str, values: list[str], col: int = 18, max_width: int = 80) -> str:
    prefix = f"  {label:<{col}}"
    indent = " " * len(prefix)
    lines: list[str] = []
    current = prefix
    for i, value in enumerate(values):
        sep = ", " if i > 0 else ""
        if len(current) + len(sep) + len(value) > max_width and len(current) > len(prefix):
            lines.append(current)
            current = indent + value
        else:
            current += sep + value
    lines.append(current)
    return "\n".join(lines)


def build_reference() -> str:
    blocks: list[str] = ["Zephyr Field Reference", ""]

    # Component
    blocks.append(_section("Component"))
    blocks.append(_row("type", COMPONENT_TYPES))
    blocks.append(_row("domain", DOMAINS))
    blocks.append(_row("criticality", CRITICALITIES))
    blocks.append(_row("exposure", EXPOSURES))
    blocks.append(_row("lifecycle", LIFECYCLES))

    # Flow
    blocks.append(_section("Flow"))
    blocks.append(_row("authentication", AUTH_TYPES))
    blocks.append(_row("encryption", ENCRYPTION_TYPES))
    blocks.append(_row("direction", FLOW_DIRECTIONS))

    # Risk
    blocks.append(_section("Risk"))
    blocks.append(_row("severity", SEVERITIES))
    blocks.append(_row("likelihood", LIKELIHOODS))
    blocks.append(_row("impact", IMPACTS))

    # Control
    blocks.append(_section("Control"))
    blocks.append(_row("type", CONTROL_TYPES))

    # Stakeholder
    blocks.append(_section("Stakeholder"))
    blocks.append(_row("role", STAKEHOLDER_ROLES))

    # Architecture meta
    blocks.append(_section("Architecture meta"))
    blocks.append(_row("meta.environment", ENVIRONMENTS))
    blocks.append(_row("meta.criticality", CRITICALITIES))

    blocks.append("")
    return "\n".join(blocks)
