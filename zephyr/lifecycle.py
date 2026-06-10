"""Zephyr Architecture Lifecycle Tracking.

Analyses component lifecycle states across an architecture model:
  - Distribution by state (planned / active / deprecated / unset)
  - Deprecated components still referenced in active flows
  - Planned components with no flows (not yet integrated)
  - Components missing a lifecycle field
  - High-impact deprecations (deprecated components with many flows)

Entry point: analyze_lifecycle(arch) -> LifecycleReport
"""

from __future__ import annotations

from dataclasses import dataclass, field

from zephyr.models import Architecture


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class DeprecatedInUse:
    name: str
    flow_count: int
    flows: list[str]   # "source → target" strings


@dataclass
class PlannedUnconnected:
    name: str
    description: str


@dataclass
class LifecycleReport:
    distribution: dict[str, int]       # {"active": 5, "deprecated": 2, "planned": 1, "unset": 0}
    deprecated_in_use: list[DeprecatedInUse]
    planned_unconnected: list[PlannedUnconnected]
    no_lifecycle: list[str]            # component names with empty lifecycle field
    health: str                        # "healthy" | "warning" | "critical"
    summary: str

    def to_dict(self) -> dict:
        return {
            "distribution": self.distribution,
            "deprecated_in_use": [
                {"name": d.name, "flow_count": d.flow_count, "flows": d.flows}
                for d in self.deprecated_in_use
            ],
            "planned_unconnected": [
                {"name": p.name, "description": p.description}
                for p in self.planned_unconnected
            ],
            "no_lifecycle": self.no_lifecycle,
            "health": self.health,
            "summary": self.summary,
        }


# ── Analysis ──────────────────────────────────────────────────────────────────

def analyze_lifecycle(arch: Architecture) -> LifecycleReport:
    """Analyse component lifecycle states and surface lifecycle health issues."""
    components = arch.components
    flows = arch.flows

    # Distribution
    distribution: dict[str, int] = {"active": 0, "deprecated": 0, "planned": 0, "unset": 0}
    for c in components:
        key = c.lifecycle if c.lifecycle in distribution else "unset"
        distribution[key] += 1

    # Build flow involvement per component
    component_flows: dict[str, list[str]] = {c.name: [] for c in components}
    for f in flows:
        label = f"{f.source} → {f.target}"
        if f.source in component_flows:
            component_flows[f.source].append(label)
        if f.target in component_flows:
            component_flows[f.target].append(label)

    # Deprecated components still referenced in flows
    deprecated_in_use: list[DeprecatedInUse] = []
    for c in components:
        if c.lifecycle == "deprecated":
            involved = component_flows.get(c.name, [])
            if involved:
                deprecated_in_use.append(
                    DeprecatedInUse(name=c.name, flow_count=len(involved), flows=involved)
                )

    # Planned components with no flows
    planned_unconnected: list[PlannedUnconnected] = []
    for c in components:
        if c.lifecycle == "planned" and not component_flows.get(c.name):
            planned_unconnected.append(
                PlannedUnconnected(name=c.name, description=c.description)
            )

    # Components with no lifecycle set
    no_lifecycle = [c.name for c in components if not c.lifecycle]

    # Health assessment
    if deprecated_in_use:
        health = "critical"
    elif planned_unconnected or no_lifecycle:
        health = "warning"
    else:
        health = "healthy"

    # Summary
    n = len(components)
    parts = []
    if distribution["active"]:
        parts.append(f"{distribution['active']} active")
    if distribution["deprecated"]:
        parts.append(f"{distribution['deprecated']} deprecated")
    if distribution["planned"]:
        parts.append(f"{distribution['planned']} planned")
    if distribution["unset"]:
        parts.append(f"{distribution['unset']} unset")

    dist_str = ", ".join(parts) if parts else "no components"
    issues = []
    if deprecated_in_use:
        issues.append(f"{len(deprecated_in_use)} deprecated component(s) still active in flows")
    if planned_unconnected:
        issues.append(f"{len(planned_unconnected)} planned component(s) not yet connected")
    if no_lifecycle:
        issues.append(f"{len(no_lifecycle)} component(s) missing lifecycle field")

    if issues:
        summary = f"{n} component(s) — {dist_str}. Issues: {'; '.join(issues)}."
    else:
        summary = f"{n} component(s) — {dist_str}. Lifecycle health: {health}."

    return LifecycleReport(
        distribution=distribution,
        deprecated_in_use=deprecated_in_use,
        planned_unconnected=planned_unconnected,
        no_lifecycle=no_lifecycle,
        health=health,
        summary=summary,
    )
