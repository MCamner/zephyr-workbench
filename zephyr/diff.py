from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from zephyr.models import Architecture, Component, Control, Flow, Meta, Risk, Stakeholder

Status = Literal["added", "removed", "modified"]


@dataclass
class Change:
    status: Status
    label: str
    fields: list[tuple[str, str, str]] = field(default_factory=list)
    # fields: [(field_name, old_value, new_value)] — only for "modified"


@dataclass
class ArchitectureDiff:
    source: str
    target: str
    meta: Change | None
    components: list[Change]
    flows: list[Change]
    risks: list[Change]
    controls: list[Change]
    stakeholders: list[Change]

    def is_empty(self) -> bool:
        return not any([
            self.meta,
            self.components,
            self.flows,
            self.risks,
            self.controls,
            self.stakeholders,
        ])


def diff_architectures(
    a: Architecture,
    b: Architecture,
    source: str = "",
    target: str = "",
) -> ArchitectureDiff:
    return ArchitectureDiff(
        source=source,
        target=target,
        meta=_diff_meta(a.meta, b.meta),
        components=_diff_components(a.components, b.components),
        flows=_diff_flows(a.flows, b.flows),
        risks=_diff_risks(a.risks, b.risks),
        controls=_diff_controls(a.controls, b.controls),
        stakeholders=_diff_stakeholders(a.stakeholders, b.stakeholders),
    )


def format_diff(diff: ArchitectureDiff) -> str:
    lines = [f"Architecture diff: {diff.source} → {diff.target}", ""]

    if diff.is_empty():
        lines.append("No changes detected.")
        return "\n".join(lines)

    if diff.meta:
        lines.append("Meta:")
        symbol = {"added": "+", "removed": "-", "modified": "~"}[diff.meta.status]
        lines.append(f"  {symbol} {diff.meta.label}")
        for fname, old_val, new_val in diff.meta.fields:
            lines.append(f"      {fname}: {old_val or '(empty)'} → {new_val or '(empty)'}")
        lines.append("")

    sections = [
        ("Components", diff.components),
        ("Flows", diff.flows),
        ("Risks", diff.risks),
        ("Controls", diff.controls),
        ("Stakeholders", diff.stakeholders),
    ]

    unchanged = [name for name, changes in sections if not changes]
    if diff.meta is None:
        unchanged = ["meta"] + unchanged

    for name, changes in sections:
        if not changes:
            continue
        lines.append(f"{name}:")
        for change in changes:
            symbol = {"added": "+", "removed": "-", "modified": "~"}[change.status]
            lines.append(f"  {symbol} {change.label}")
            for fname, old_val, new_val in change.fields:
                lines.append(f"      {fname}: {old_val or '(empty)'} → {new_val or '(empty)'}")
        lines.append("")

    if unchanged:
        lines.append(f"No changes: {', '.join(n.lower() for n in unchanged)}")

    return "\n".join(lines)


# ── per-type diff helpers ────────────────────────────────────────────────────

def _diff_components(old: list[Component], new: list[Component]) -> list[Change]:
    old_map = {c.name: c for c in old}
    new_map = {c.name: c for c in new}
    changes: list[Change] = []

    for name, item in old_map.items():
        if name not in new_map:
            changes.append(Change(status="removed", label=f"{name} ({item.type})"))

    for name, item in new_map.items():
        if name not in old_map:
            changes.append(Change(status="added", label=f"{name} ({item.type})"))
        else:
            modified = _field_changes(
                old_map[name], item,
                ("type", "domain", "criticality", "exposure", "lifecycle"),
            )
            if modified:
                changes.append(Change(status="modified", label=name, fields=modified))

    return changes


def _diff_flows(old: list[Flow], new: list[Flow]) -> list[Change]:
    # key: (source, target, label) — label disambiguates parallel flows
    def key(f: Flow) -> tuple[str, str, str]:
        return (f.source, f.target, f.label)

    old_map = {key(f): f for f in old}
    new_map = {key(f): f for f in new}
    changes: list[Change] = []

    for k, item in old_map.items():
        if k not in new_map:
            changes.append(Change(status="removed", label=f"{item.source} → {item.target} ({item.label})"))

    for k, item in new_map.items():
        if k not in old_map:
            changes.append(Change(status="added", label=f"{item.source} → {item.target} ({item.label})"))
        else:
            modified = _field_changes(
                old_map[k], item,
                ("protocol", "authentication", "encryption", "direction"),
            )
            if modified:
                label = f"{item.source} → {item.target} ({item.label})"
                changes.append(Change(status="modified", label=label, fields=modified))

    return changes


def _diff_risks(old: list[Risk], new: list[Risk]) -> list[Change]:
    old_map = {r.id: r for r in old}
    new_map = {r.id: r for r in new}
    changes: list[Change] = []

    for rid, item in old_map.items():
        if rid not in new_map:
            changes.append(Change(status="removed", label=f"{rid}: {item.title} [{item.severity}]"))

    for rid, item in new_map.items():
        if rid not in old_map:
            changes.append(Change(status="added", label=f"{rid}: {item.title} [{item.severity}]"))
        else:
            modified = _field_changes(
                old_map[rid], item,
                ("title", "severity", "likelihood", "impact"),
            )
            if modified:
                changes.append(Change(status="modified", label=f"{rid}: {item.title}", fields=modified))

    return changes


def _diff_controls(old: list[Control], new: list[Control]) -> list[Change]:
    old_map = {c.name: c for c in old}
    new_map = {c.name: c for c in new}
    changes: list[Change] = []

    for name, item in old_map.items():
        if name not in new_map:
            changes.append(Change(status="removed", label=f"{name} [{item.type}]"))

    for name, item in new_map.items():
        if name not in old_map:
            changes.append(Change(status="added", label=f"{name} [{item.type}]"))
        else:
            o, n = old_map[name], item
            modified: list[tuple[str, str, str]] = []
            if o.type != n.type:
                modified.append(("type", o.type, n.type))
            old_targets = ", ".join(o.applies_to)
            new_targets = ", ".join(n.applies_to)
            if old_targets != new_targets:
                modified.append(("applies_to", old_targets, new_targets))
            if modified:
                changes.append(Change(status="modified", label=name, fields=modified))

    return changes


def _diff_stakeholders(old: list[Stakeholder], new: list[Stakeholder]) -> list[Change]:
    old_map = {s.name: s for s in old}
    new_map = {s.name: s for s in new}
    changes: list[Change] = []

    for name, item in old_map.items():
        if name not in new_map:
            changes.append(Change(status="removed", label=f"{name} ({item.role})"))

    for name, item in new_map.items():
        if name not in old_map:
            changes.append(Change(status="added", label=f"{name} ({item.role})"))
        else:
            if old_map[name].role != item.role:
                changes.append(Change(
                    status="modified",
                    label=name,
                    fields=[("role", old_map[name].role, item.role)],
                ))

    return changes


def _diff_meta(a: Meta | None, b: Meta | None) -> Change | None:
    if a is None and b is None:
        return None
    if a is None:
        return Change(status="added", label="meta")
    if b is None:
        return Change(status="removed", label="meta")
    fields = _field_changes(a, b, ("owner", "version", "criticality"))
    a_env = ", ".join(a.environment)
    b_env = ", ".join(b.environment)
    if a_env != b_env:
        fields.append(("environment", a_env, b_env))
    return Change(status="modified", label="meta", fields=fields) if fields else None


def _field_changes(old, new, attrs: tuple[str, ...]) -> list[tuple[str, str, str]]:
    result = []
    for attr in attrs:
        ov = str(getattr(old, attr, "") or "")
        nv = str(getattr(new, attr, "") or "")
        if ov != nv:
            result.append((attr, ov, nv))
    return result
