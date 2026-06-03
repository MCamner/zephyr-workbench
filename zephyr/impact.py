"""Zephyr Change Impact Analysis.

Given two architecture models (before/after) and a diff, analyses the blast
radius and security implications of each change: upstream/downstream component
reach, lost control coverage, and potentially unmitigated risks.

Entry point: analyze_impact(before, after, diff) -> ChangeImpactReport
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Literal

from zephyr.diff import ArchitectureDiff
from zephyr.models import Architecture, Component


Severity = Literal["critical", "high", "medium", "low", "none"]

_CRIT_RANK: dict[str, int] = {
    "": 0, "low": 1, "medium": 2, "high": 3, "mission-critical": 4
}
_HIGH_CRIT = {"high", "mission-critical"}
_CRITICAL_FLAGS = {"high-criticality", "gateway", "identity-provider"}


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class ComponentImpact:
    component: str
    change_type: str            # "removed" | "added" | "modified"
    criticality: str
    upstream: list[str]         # components that flow into this one
    downstream: list[str]       # components reachable from this one
    lost_controls: list[str]    # controls removed that previously covered this component
    flags: list[str]            # "high-criticality", "external-exposed", "gateway", "identity-provider"


@dataclass
class ControlCoverageChange:
    control: str
    status: str                 # "removed" | "coverage-reduced"
    previously_covered: list[str]
    now_covered: list[str]
    unprotected: list[str]      # previously_covered minus now_covered


@dataclass
class ChangeImpactReport:
    source: str
    target: str
    severity: Severity
    summary: str
    component_impacts: list[ComponentImpact]
    control_changes: list[ControlCoverageChange]
    unmitigated_risk_ids: list[str]
    recommendations: list[str]

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "severity": self.severity,
            "summary": self.summary,
            "component_impacts": [_ci_to_dict(c) for c in self.component_impacts],
            "control_changes": [_cc_to_dict(c) for c in self.control_changes],
            "unmitigated_risk_ids": self.unmitigated_risk_ids,
            "recommendations": self.recommendations,
        }


# ── Graph helpers ─────────────────────────────────────────────────────────────

def _forward_graph(arch: Architecture) -> dict[str, set[str]]:
    g: dict[str, set[str]] = {c.name: set() for c in arch.components}
    for f in arch.flows:
        g.setdefault(f.source, set()).add(f.target)
        if f.direction == "bidirectional":
            g.setdefault(f.target, set()).add(f.source)
    return g


def _reverse_graph(arch: Architecture) -> dict[str, set[str]]:
    g: dict[str, set[str]] = {c.name: set() for c in arch.components}
    for f in arch.flows:
        g.setdefault(f.target, set()).add(f.source)
        if f.direction == "bidirectional":
            g.setdefault(f.source, set()).add(f.target)
    return g


def _reachable(start: str, graph: dict[str, set[str]]) -> list[str]:
    visited: set[str] = set()
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        for nbr in graph.get(node, set()):
            if nbr not in visited and nbr != start:
                visited.add(nbr)
                queue.append(nbr)
    return sorted(visited)


# ── Flag helpers ──────────────────────────────────────────────────────────────

def _flags(comp: Component | None) -> list[str]:
    if comp is None:
        return []
    result = []
    if comp.criticality in _HIGH_CRIT:
        result.append("high-criticality")
    if comp.exposure == "external":
        result.append("external-exposed")
    if comp.type == "access-gateway":
        result.append("gateway")
    if comp.type in {"identity", "identity-provider", "cloud-identity", "on-prem-identity"}:
        result.append("identity-provider")
    return result


def _label_to_name_paren(label: str) -> str:
    """Extract name from 'Name (type)' labels produced by _diff_components."""
    idx = label.rfind(" (")
    return label[:idx] if idx != -1 else label


def _label_to_name_bracket(label: str) -> str:
    """Extract name from 'Name [type]' labels produced by _diff_controls."""
    idx = label.rfind(" [")
    return label[:idx] if idx != -1 else label


# ── Core analysis ─────────────────────────────────────────────────────────────

def analyze_impact(
    before: Architecture,
    after: Architecture,
    diff: ArchitectureDiff,
) -> ChangeImpactReport:
    """Analyse blast radius and security implications of architecture changes."""
    fwd_before = _forward_graph(before)
    rev_before = _reverse_graph(before)
    fwd_after = _forward_graph(after)
    rev_after = _reverse_graph(after)

    before_comps = {c.name: c for c in before.components}
    after_comps = {c.name: c for c in after.components}
    before_ctrls = {c.name: c for c in before.controls}
    after_ctrls = {c.name: c for c in after.controls}

    component_impacts: list[ComponentImpact] = []
    control_changes: list[ControlCoverageChange] = []

    # ── Component changes ────────────────────────────────────────────────────
    removed_ctrl_names: set[str] = {
        _label_to_name_bracket(ch.label)
        for ch in diff.controls
        if ch.status == "removed"
    }

    for change in diff.components:
        status = change.status

        if status == "removed":
            name = _label_to_name_paren(change.label)
            comp = before_comps.get(name)
            lost = [
                n for n, c in before_ctrls.items()
                if name in c.applies_to and n in removed_ctrl_names
            ]
            component_impacts.append(ComponentImpact(
                component=name,
                change_type="removed",
                criticality=comp.criticality if comp else "",
                upstream=sorted(rev_before.get(name, set())),
                downstream=_reachable(name, fwd_before),
                lost_controls=lost,
                flags=_flags(comp),
            ))

        elif status == "added":
            name = _label_to_name_paren(change.label)
            comp = after_comps.get(name)
            component_impacts.append(ComponentImpact(
                component=name,
                change_type="added",
                criticality=comp.criticality if comp else "",
                upstream=sorted(rev_after.get(name, set())),
                downstream=_reachable(name, fwd_after),
                lost_controls=[],
                flags=_flags(comp),
            ))

        elif status == "modified":
            name = change.label  # modified label is the bare name
            comp_b = before_comps.get(name)
            comp_a = after_comps.get(name)
            fl = _flags(comp_a)
            if (comp_b and comp_a and
                    _CRIT_RANK.get(comp_a.criticality, 0) > _CRIT_RANK.get(comp_b.criticality, 0)):
                fl = [f for f in fl if f != "high-criticality"] + ["criticality-escalated"]
            component_impacts.append(ComponentImpact(
                component=name,
                change_type="modified",
                criticality=comp_a.criticality if comp_a else "",
                upstream=sorted(rev_after.get(name, set())),
                downstream=_reachable(name, fwd_after),
                lost_controls=[],
                flags=fl,
            ))

    # ── Control coverage changes ─────────────────────────────────────────────
    for change in diff.controls:
        name = _label_to_name_bracket(change.label) if change.status != "modified" else change.label

        if change.status == "removed":
            ctrl = before_ctrls.get(name)
            prev = sorted(ctrl.applies_to) if ctrl else []
            control_changes.append(ControlCoverageChange(
                control=name,
                status="removed",
                previously_covered=prev,
                now_covered=[],
                unprotected=prev,
            ))

        elif change.status == "modified":
            old_c = before_ctrls.get(name)
            new_c = after_ctrls.get(name)
            prev_set = set(old_c.applies_to) if old_c else set()
            now_set = set(new_c.applies_to) if new_c else set()
            lost = sorted(prev_set - now_set)
            if lost:
                control_changes.append(ControlCoverageChange(
                    control=name,
                    status="coverage-reduced",
                    previously_covered=sorted(prev_set),
                    now_covered=sorted(now_set),
                    unprotected=lost,
                ))

    # ── Unmitigated risks ────────────────────────────────────────────────────
    after_risk_ids = {r.id for r in after.risks}
    unmitigated_risk_ids: list[str] = []
    for risk in before.risks:
        if risk.id not in after_risk_ids:
            continue
        mitigation_lower = (risk.mitigation or "").lower()
        if any(n.lower() in mitigation_lower for n in removed_ctrl_names):
            unmitigated_risk_ids.append(risk.id)

    # ── Severity ─────────────────────────────────────────────────────────────
    severity = _compute_severity(component_impacts, control_changes, unmitigated_risk_ids, diff)

    # ── Summary & recommendations ────────────────────────────────────────────
    summary = _build_summary(diff, severity, component_impacts, control_changes, unmitigated_risk_ids)
    recommendations = _build_recommendations(component_impacts, control_changes, unmitigated_risk_ids)

    return ChangeImpactReport(
        source=diff.source,
        target=diff.target,
        severity=severity,
        summary=summary,
        component_impacts=component_impacts,
        control_changes=control_changes,
        unmitigated_risk_ids=unmitigated_risk_ids,
        recommendations=recommendations,
    )


# ── Severity computation ──────────────────────────────────────────────────────

def _compute_severity(
    ci: list[ComponentImpact],
    cc: list[ControlCoverageChange],
    unmitigated: list[str],
    diff: ArchitectureDiff,
) -> Severity:
    if not ci and not cc and not unmitigated and diff.is_empty():
        return "none"

    critical_removals = [
        c for c in ci
        if c.change_type == "removed" and any(f in _CRITICAL_FLAGS for f in c.flags)
    ]
    control_removals = [c for c in cc if c.status == "removed"]

    if critical_removals or (control_removals and unmitigated):
        return "critical"
    if control_removals or unmitigated:
        return "high"
    medium_flags = _CRITICAL_FLAGS | {"criticality-escalated"}
    high_crit_changes = [
        c for c in ci if any(f in medium_flags for f in c.flags)
    ]
    if high_crit_changes:
        return "medium"
    if ci or cc:
        return "low"
    return "none"


# ── Summary & recommendations ────────────────────────────────────────────────

def _build_summary(
    diff: ArchitectureDiff,
    severity: Severity,
    ci: list[ComponentImpact],
    cc: list[ControlCoverageChange],
    unmitigated: list[str],
) -> str:
    if diff.is_empty():
        return "No changes detected — no impact assessment needed."
    parts = []
    if ci:
        by_type = {"removed": 0, "added": 0, "modified": 0}
        for c in ci:
            by_type[c.change_type] += 1
        desc = ", ".join(f"{v} {k}" for k, v in by_type.items() if v)
        parts.append(f"{len(ci)} component change(s) ({desc})")
    if cc:
        parts.append(f"{len(cc)} control coverage change(s)")
    if unmitigated:
        parts.append(f"{len(unmitigated)} potentially unmitigated risk(s)")
    body = "; ".join(parts) if parts else "structural changes detected"
    return f"Impact severity: {severity.upper()}. {body}."


def _build_recommendations(
    ci: list[ComponentImpact],
    cc: list[ControlCoverageChange],
    unmitigated: list[str],
) -> list[str]:
    recs: list[str] = []
    for c in ci:
        if c.change_type != "removed":
            continue
        if "gateway" in c.flags:
            targets = ", ".join(c.downstream[:3]) + ("..." if len(c.downstream) > 3 else "")
            recs.append(
                f"'{c.component}' (access-gateway) removed"
                + (f" — {len(c.downstream)} downstream component(s) may be exposed: {targets}." if c.downstream else ".")
                + " Verify a replacement gateway is in place."
            )
        elif "identity-provider" in c.flags:
            targets = ", ".join(c.downstream[:3]) + ("..." if len(c.downstream) > 3 else "")
            recs.append(
                f"'{c.component}' (identity provider) removed"
                + (f" — authentication may break for: {targets}." if c.downstream else ".")
                + " Confirm an alternative IdP covers affected components."
            )
        elif "high-criticality" in c.flags and c.downstream:
            recs.append(
                f"'{c.component}' (high criticality) removed — "
                f"{len(c.downstream)} downstream component(s) may be affected."
            )
    for ctrl_change in cc:
        names = ", ".join(ctrl_change.unprotected[:3]) + ("..." if len(ctrl_change.unprotected) > 3 else "")
        if ctrl_change.status == "removed":
            recs.append(
                f"Control '{ctrl_change.control}' removed — {len(ctrl_change.unprotected)} component(s) now unprotected: "
                f"{names}. Ensure replacement controls are in place."
            )
        else:
            recs.append(
                f"Control '{ctrl_change.control}' no longer covers: {names}. "
                "Review whether these components need alternative protection."
            )
    if unmitigated:
        ids = ", ".join(unmitigated)
        recs.append(
            f"Risk(s) {ids} may be unmitigated after control removal. "
            "Update risk mitigations or add replacement controls."
        )
    return recs


# ── Human-readable output ────────────────────────────────────────────────────

def format_impact(report: ChangeImpactReport) -> str:
    _SEV_ICON = {"critical": "✗", "high": "!", "medium": "~", "low": "-", "none": "✓"}
    icon = _SEV_ICON.get(report.severity, "?")
    lines = [
        f"Change impact: {report.source} → {report.target}",
        f"Severity: [{icon}] {report.severity.upper()}",
        "",
        report.summary,
    ]

    if report.component_impacts:
        lines += ["", "Component impacts:"]
        for ci in report.component_impacts:
            sym = {"removed": "-", "added": "+", "modified": "~"}[ci.change_type]
            flag_str = f"  [{', '.join(ci.flags)}]" if ci.flags else ""
            crit = f" ({ci.criticality})" if ci.criticality else ""
            lines.append(f"  {sym} {ci.component}{crit}{flag_str}")
            if ci.upstream:
                lines.append(f"      upstream:      {', '.join(ci.upstream)}")
            if ci.downstream:
                lines.append(f"      downstream:    {', '.join(ci.downstream)}")
            if ci.lost_controls:
                lines.append(f"      lost controls: {', '.join(ci.lost_controls)}")

    if report.control_changes:
        lines += ["", "Control coverage changes:"]
        for cc in report.control_changes:
            sym = "-" if cc.status == "removed" else "~"
            lines.append(f"  {sym} {cc.control}  ({cc.status})")
            if cc.unprotected:
                lines.append(f"      unprotected: {', '.join(cc.unprotected)}")

    if report.unmitigated_risk_ids:
        lines += ["", "Potentially unmitigated risks:"]
        for rid in report.unmitigated_risk_ids:
            lines.append(f"  ! {rid}")

    if report.recommendations:
        lines += ["", "Recommendations:"]
        for rec in report.recommendations:
            lines.append(f"  • {rec}")

    return "\n".join(lines)


# ── Serialisation helpers (used by cli.py and runtime.py) ────────────────────

def _ci_to_dict(ci: ComponentImpact) -> dict:
    return {
        "component": ci.component,
        "change_type": ci.change_type,
        "criticality": ci.criticality,
        "upstream": ci.upstream,
        "downstream": ci.downstream,
        "lost_controls": ci.lost_controls,
        "flags": ci.flags,
    }


def _cc_to_dict(cc: ControlCoverageChange) -> dict:
    return {
        "control": cc.control,
        "status": cc.status,
        "previously_covered": cc.previously_covered,
        "now_covered": cc.now_covered,
        "unprotected": cc.unprotected,
    }
