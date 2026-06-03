"""Zephyr Architecture Intelligence.

Rule-based architectural analysis: anti-pattern detection, dependency reasoning,
risk analysis, narrative summarization, and improvement suggestions.
All analysis is deterministic and requires no external AI/LLM calls.

The ten v0.3.0 capabilities exposed here:
  detect_antipatterns     — architecture anti-pattern detection
  suggest_improvements    — YAML improvement suggestions
  analyze_risks           — architecture risk analysis
  explain_risk            — risk explanation workflow
  dependency_insights     — dependency reasoning
  narrative_summary       — architecture summarization
  review_architecture     — AI-assisted architecture review (rule-based)
  analyze_architecture    — full analysis combining all of the above
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

from zephyr.models import Architecture, Component, Flow, Risk


# ── Severity ordering ─────────────────────────────────────────────────────────

_SEVERITY_ORDER = {"risk": 0, "warning": 1, "suggestion": 2, "note": 3}


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    severity: str  # "risk" | "warning" | "suggestion" | "note"
    code: str
    message: str
    affected: list[str] = field(default_factory=list)

    def __lt__(self, other: Finding) -> bool:
        return _SEVERITY_ORDER.get(self.severity, 99) < _SEVERITY_ORDER.get(other.severity, 99)


@dataclass
class RiskContext:
    risk_id: str
    title: str
    severity: str
    likelihood: str
    impact: str
    mitigation: str
    affected_components: list[str]
    affected_flows: list[str]
    explanation: str


@dataclass
class DependencyInsights:
    external_reachable: dict[str, list[str]]   # external component → reachable components
    hub_components: list[tuple[str, int]]       # (name, total_flow_degree), top-5
    isolated_components: list[str]             # not reachable from any external node


@dataclass
class ArchitectureAnalysis:
    antipatterns: list[Finding]
    suggestions: list[Finding]
    risk_analysis: dict
    dependency_insights: DependencyInsights
    narrative: str

    def all_findings(self) -> list[Finding]:
        return sorted(self.antipatterns + self.suggestions)

    def has_blocking(self) -> bool:
        return any(f.severity == "risk" for f in self.antipatterns)


# ── Graph helpers ─────────────────────────────────────────────────────────────

def _build_graph(architecture: Architecture) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {c.name: set() for c in architecture.components}
    for f in architecture.flows:
        graph.setdefault(f.source, set()).add(f.target)
        if f.direction == "bidirectional":
            graph.setdefault(f.target, set()).add(f.source)
    return graph


def _reachable_from(start: str, graph: dict[str, set[str]]) -> set[str]:
    visited: set[str] = set()
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        for nbr in graph.get(node, set()):
            if nbr not in visited and nbr != start:
                visited.add(nbr)
                queue.append(nbr)
    return visited


# ── Anti-pattern detection ────────────────────────────────────────────────────

def detect_antipatterns(architecture: Architecture) -> list[Finding]:
    """Detect structural anti-patterns beyond basic validation warnings."""
    findings: list[Finding] = []

    gateway_names = {c.name for c in architecture.components if c.type == "access-gateway"}
    external_names = {c.name for c in architecture.components if c.exposure == "external"}
    _identity_types = {"identity", "identity-provider", "cloud-identity", "on-prem-identity"}
    idp_names = {c.name for c in architecture.components if c.type in _identity_types}
    _critical_levels = {"high", "mission-critical"}

    graph = _build_graph(architecture)
    total = len(architecture.components)

    # 1. External component flows directly to non-gateway (bypass)
    if gateway_names:
        for ext in external_names:
            direct_targets = graph.get(ext, set())
            unsafe = direct_targets - gateway_names
            if unsafe:
                findings.append(Finding(
                    severity="risk",
                    code="external-endpoint-unrestricted",
                    message=(
                        f"'{ext}' (external) flows directly to "
                        f"{', '.join(sorted(unsafe))} bypassing access-gateway"
                    ),
                    affected=[ext] + sorted(unsafe),
                ))

    # 2. Identity-provider exists but no authenticated flows target it
    if idp_names:
        auth_targets = {f.target for f in architecture.flows if f.authentication in ("mfa", "certificate")}
        for idp in idp_names - auth_targets:
            findings.append(Finding(
                severity="warning",
                code="identity-provider-unused",
                message=f"Identity component '{idp}' has no authenticated flows (mfa/certificate) targeting it",
                affected=[idp],
            ))

    # 3. High/mission-critical component with no controls applied
    controlled = {target for ctrl in architecture.controls for target in ctrl.applies_to}
    for c in architecture.components:
        if c.criticality in _critical_levels and c.name not in controlled:
            findings.append(Finding(
                severity="warning",
                code="critical-component-uncontrolled",
                message=f"'{c.name}' (criticality: {c.criticality}) has no controls applied",
                affected=[c.name],
            ))

    # 4. All components in one trust boundary — no zone isolation
    assigned = [c.trust_boundary for c in architecture.components if c.trust_boundary]
    if assigned and len(set(assigned)) == 1 and total > 3:
        findings.append(Finding(
            severity="note",
            code="trust-boundary-monozone",
            message=(
                f"All components share trust boundary '{assigned[0]}' — "
                "consider splitting into isolated zones"
            ),
        ))

    # 5. High/critical risk missing likelihood or impact
    for risk in architecture.risks:
        if risk.severity in ("high", "critical"):
            missing_fields = [f for f in ("likelihood", "impact") if not getattr(risk, f)]
            if missing_fields:
                findings.append(Finding(
                    severity="warning",
                    code="risk-definition-incomplete",
                    message=(
                        f"Risk '{risk.id}' is {risk.severity} severity "
                        f"but missing: {', '.join(missing_fields)}"
                    ),
                    affected=[risk.id],
                ))

    # 6. External component can reach >50% of the architecture (high blast radius)
    if total > 2:
        for ext in external_names:
            reachable = _reachable_from(ext, graph)
            if len(reachable) / (total - 1) > 0.5:
                findings.append(Finding(
                    severity="warning",
                    code="high-blast-radius",
                    message=(
                        f"'{ext}' (external) can reach {len(reachable)}/{total - 1} components "
                        "— high blast radius if compromised"
                    ),
                    affected=[ext],
                ))

    # 7. security-control type component with no inbound flows — not on any path
    inbound: dict[str, int] = defaultdict(int)
    for f in architecture.flows:
        inbound[f.target] += 1
    for c in architecture.components:
        if c.type == "security-control" and inbound[c.name] == 0:
            findings.append(Finding(
                severity="note",
                code="security-control-isolated",
                message=(
                    f"Security control '{c.name}' receives no flows — "
                    "may not be enforced in any data path"
                ),
                affected=[c.name],
            ))

    return sorted(findings)


# ── Improvement suggestions ───────────────────────────────────────────────────

def suggest_improvements(architecture: Architecture) -> list[Finding]:
    """Return actionable YAML improvement suggestions."""
    findings: list[Finding] = []

    # Missing mitigation for high/critical risks
    for risk in architecture.risks:
        if risk.severity in ("high", "critical") and not risk.mitigation:
            findings.append(Finding(
                severity="suggestion",
                code="add-risk-mitigation",
                message=f"Add mitigation for {risk.severity} risk '{risk.id}: {risk.title}'",
                affected=[risk.id],
            ))

    # Multiple components missing descriptions
    no_desc = [c.name for c in architecture.components if not c.description]
    if len(no_desc) >= 2:
        sample = ", ".join(no_desc[:5]) + ("..." if len(no_desc) > 5 else "")
        findings.append(Finding(
            severity="note",
            code="missing-component-descriptions",
            message=f"{len(no_desc)} components missing description: {sample}",
            affected=no_desc,
        ))

    # Flows to identity components without authentication
    _identity_types = {"identity", "identity-provider", "cloud-identity", "on-prem-identity"}
    idp_names = {c.name for c in architecture.components if c.type in _identity_types}
    for f in architecture.flows:
        if f.target in idp_names and not f.authentication:
            findings.append(Finding(
                severity="suggestion",
                code="unauthenticated-identity-flow",
                message=(
                    f"Flow '{f.source} → {f.target}' targets an identity component "
                    "but specifies no authentication"
                ),
                affected=[f.source, f.target],
            ))

    # Components with criticality but no trust boundaries defined
    has_criticality = any(c.criticality for c in architecture.components)
    if has_criticality and not architecture.trust_boundaries and len(architecture.components) > 3:
        findings.append(Finding(
            severity="suggestion",
            code="define-trust-boundaries",
            message=(
                "Components have criticality classifications "
                "but no trust_boundaries are defined"
            ),
        ))

    # Medium risks missing likelihood (scoring improvement)
    for risk in architecture.risks:
        if risk.severity == "medium" and not risk.likelihood:
            findings.append(Finding(
                severity="note",
                code="risk-missing-likelihood",
                message=f"Risk '{risk.id}' missing likelihood — needed for risk scoring",
                affected=[risk.id],
            ))

    return sorted(findings)


# ── Risk analysis ─────────────────────────────────────────────────────────────

def analyze_risks(architecture: Architecture) -> dict:
    """Return structured risk distribution and posture summary."""
    _severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    by_severity: dict[str, list[str]] = defaultdict(list)
    for risk in architecture.risks:
        by_severity[risk.severity].append(risk.id)

    unmitigated = [r for r in architecture.risks if not r.mitigation]
    unmitigated_high = [r for r in unmitigated if r.severity in ("high", "critical")]
    incomplete = [r for r in architecture.risks if not r.likelihood or not r.impact]
    fully_defined = [
        r for r in architecture.risks if r.likelihood and r.impact and r.mitigation
    ]

    return {
        "total": len(architecture.risks),
        "by_severity": {
            k: by_severity[k]
            for k in sorted(by_severity, key=lambda s: _severity_rank.get(s, 99))
        },
        "unmitigated": [r.id for r in unmitigated],
        "unmitigated_high_critical": [r.id for r in unmitigated_high],
        "incomplete_definitions": [r.id for r in incomplete],
        "fully_defined": [r.id for r in fully_defined],
    }


# ── Risk explanation ──────────────────────────────────────────────────────────

def explain_risk(architecture: Architecture, risk_id: str) -> Optional[RiskContext]:
    """Return contextual explanation for a specific risk."""
    risk = next((r for r in architecture.risks if r.id == risk_id), None)
    if risk is None:
        return None

    _critical_levels = {"high", "mission-critical"}
    affected_components = [
        c.name for c in architecture.components if c.criticality in _critical_levels
    ]

    # Flows that pass through controlled components or are external-facing
    external_names = {c.name for c in architecture.components if c.exposure == "external"}
    relevant_flows = [
        f"{f.source} → {f.target}"
        for f in architecture.flows
        if f.source in external_names or not f.encryption or f.encryption == "none"
    ][:5]

    parts: list[str] = []
    parts.append(f"Severity: {risk.severity}")
    if risk.likelihood:
        parts.append(f"Likelihood: {risk.likelihood}")
    if risk.impact:
        parts.append(f"Impact: {risk.impact}")
    if risk.description:
        parts.append(f"Description: {risk.description}")
    if risk.mitigation:
        parts.append(f"Mitigation: {risk.mitigation}")
    else:
        parts.append("Mitigation: none — this risk is unmitigated")
    if affected_components:
        parts.append(f"High-criticality components in scope: {', '.join(affected_components)}")
    else:
        parts.append("No high-criticality components declared in this architecture")

    return RiskContext(
        risk_id=risk_id,
        title=risk.title,
        severity=risk.severity,
        likelihood=risk.likelihood,
        impact=risk.impact,
        mitigation=risk.mitigation,
        affected_components=affected_components,
        affected_flows=relevant_flows,
        explanation="\n".join(parts),
    )


# ── Dependency reasoning ──────────────────────────────────────────────────────

def dependency_insights(architecture: Architecture) -> DependencyInsights:
    """Analyze dependency chains: external reach, hubs, isolated components."""
    graph = _build_graph(architecture)
    external_names = {c.name for c in architecture.components if c.exposure == "external"}

    external_reachable: dict[str, list[str]] = {
        ext: sorted(_reachable_from(ext, graph)) for ext in external_names
    }

    # Hub components: highest total degree (inbound + outbound)
    degree: dict[str, int] = defaultdict(int)
    for src, targets in graph.items():
        degree[src] += len(targets)
        for tgt in targets:
            degree[tgt] += 1
    hub_components = sorted(
        [(name, deg) for name, deg in degree.items() if deg > 1],
        key=lambda x: -x[1],
    )[:5]

    # Isolated from external: not reachable from any external node
    all_reachable: set[str] = set()
    for reachable in external_reachable.values():
        all_reachable.update(reachable)
    all_reachable.update(external_names)

    isolated = [
        c.name for c in architecture.components
        if c.name not in all_reachable and c.exposure != "external"
    ]

    return DependencyInsights(
        external_reachable=external_reachable,
        hub_components=hub_components,
        isolated_components=isolated,
    )


# ── Narrative summary ─────────────────────────────────────────────────────────

def narrative_summary(architecture: Architecture) -> str:
    """Generate a prose architectural assessment."""
    comp_count = len(architecture.components)
    flow_count = len(architecture.flows)
    risk_count = len(architecture.risks)
    boundary_count = len(architecture.trust_boundaries)

    external = [c for c in architecture.components if c.exposure == "external"]
    critical = [c for c in architecture.components if c.criticality in ("high", "mission-critical")]
    unmitigated_high = [
        r for r in architecture.risks
        if r.severity in ("high", "critical") and not r.mitigation
    ]
    auth_flows = [f for f in architecture.flows if f.authentication]
    encrypted_flows = [
        f for f in architecture.flows if f.encryption and f.encryption != "none"
    ]

    type_counts: dict[str, int] = defaultdict(int)
    for c in architecture.components:
        type_counts[c.type] += 1
    dominant = sorted(type_counts.items(), key=lambda x: -x[1])[:3]

    lines: list[str] = []

    zone_str = f"{boundary_count} trust boundary zone{'s' if boundary_count != 1 else ''}"
    lines.append(
        f"'{architecture.name}' models {comp_count} component{'s' if comp_count != 1 else ''} "
        f"across {zone_str}."
    )

    if dominant:
        type_str = ", ".join(f"{n} {t}" for t, n in dominant)
        lines.append(f"Primary types: {type_str}.")

    if external:
        names = ", ".join(c.name for c in external)
        lines.append(
            f"External attack surface: {len(external)} exposed component{'s' if len(external) != 1 else ''} ({names})."
        )
    else:
        lines.append("No externally-exposed components declared.")

    if critical:
        lines.append(
            f"High-criticality components: {', '.join(c.name for c in critical)}."
        )

    if flow_count > 0:
        auth_pct = round(len(auth_flows) / flow_count * 100)
        enc_pct = round(len(encrypted_flows) / flow_count * 100)
        lines.append(
            f"Flows: {flow_count} total — {auth_pct}% authenticated, {enc_pct}% encrypted."
        )

    if risk_count > 0:
        high_crit = [r for r in architecture.risks if r.severity in ("critical", "high")]
        lines.append(
            f"Risk posture: {risk_count} risk{'s' if risk_count != 1 else ''} defined, "
            f"{len(high_crit)} high or critical."
        )
        if unmitigated_high:
            ids = ", ".join(r.id for r in unmitigated_high)
            lines.append(f"Unmitigated high/critical risks: {len(unmitigated_high)} ({ids}).")
        else:
            lines.append("All high/critical risks have mitigations defined.")
    else:
        lines.append("No risks declared — consider adding risk definitions.")

    ctrl_count = len(architecture.controls)
    if ctrl_count:
        lines.append(f"Controls: {ctrl_count} defined.")
    else:
        lines.append("No controls defined.")

    return "\n".join(lines)


# ── Review (combined findings) ────────────────────────────────────────────────

def review_architecture(architecture: Architecture) -> list[Finding]:
    """Return all findings in severity order: anti-patterns + improvement suggestions."""
    return sorted(detect_antipatterns(architecture) + suggest_improvements(architecture))


# ── Full analysis ─────────────────────────────────────────────────────────────

def analyze_architecture(architecture: Architecture) -> ArchitectureAnalysis:
    """Run all intelligence passes and return a combined analysis."""
    return ArchitectureAnalysis(
        antipatterns=detect_antipatterns(architecture),
        suggestions=suggest_improvements(architecture),
        risk_analysis=analyze_risks(architecture),
        dependency_insights=dependency_insights(architecture),
        narrative=narrative_summary(architecture),
    )


# ── Text formatters (for CLI human output) ────────────────────────────────────

def format_findings(findings: list[Finding], title: str = "Findings") -> str:
    if not findings:
        return f"{title}: none"
    lines = [f"{title} ({len(findings)}):"]
    for f in findings:
        lines.append(f"  [{f.severity.upper():<10}] {f.code}")
        lines.append(f"    {f.message}")
    return "\n".join(lines)


def format_analysis(analysis: ArchitectureAnalysis, name: str) -> str:
    lines = [f"Architecture Analysis: {name}", ""]

    lines.append(analysis.narrative)
    lines.append("")

    ap = analysis.antipatterns
    if ap:
        lines.append(f"Anti-patterns ({len(ap)}):")
        for f in ap:
            lines.append(f"  [{f.severity.upper():<10}] {f.code}")
            lines.append(f"    {f.message}")
    else:
        lines.append("Anti-patterns: none detected")
    lines.append("")

    sg = analysis.suggestions
    if sg:
        lines.append(f"Suggestions ({len(sg)}):")
        for f in sg:
            lines.append(f"  [{f.severity.upper():<10}] {f.message}")
    else:
        lines.append("Suggestions: none")
    lines.append("")

    di = analysis.dependency_insights
    if di.external_reachable:
        lines.append("Dependency insights:")
        for ext, reach in di.external_reachable.items():
            reach_str = ", ".join(reach) if reach else "none"
            lines.append(f"  {ext} → {reach_str}")
        if di.hub_components:
            hubs = ", ".join(f"{n} ({d})" for n, d in di.hub_components)
            lines.append(f"  Hubs: {hubs}")
        if di.isolated_components:
            lines.append(f"  Isolated from external: {', '.join(di.isolated_components)}")
        lines.append("")

    ra = analysis.risk_analysis
    if ra["total"] > 0:
        by_sev = ", ".join(f"{s}: {len(ids)}" for s, ids in ra["by_severity"].items())
        lines.append(f"Risk analysis: {ra['total']} total — {by_sev}")
        if ra["unmitigated_high_critical"]:
            lines.append(f"  Unmitigated high/critical: {', '.join(ra['unmitigated_high_critical'])}")
        if ra["incomplete_definitions"]:
            lines.append(f"  Incomplete definitions: {', '.join(ra['incomplete_definitions'])}")

    return "\n".join(lines)


def format_review(findings: list[Finding], name: str) -> str:
    lines = [f"Architecture Review: {name}", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines)

    for f in findings:
        lines.append(f"  [{f.severity.upper():<10}] {f.message}")

    by_sev: dict[str, int] = defaultdict(int)
    for f in findings:
        by_sev[f.severity] += 1
    summary_parts = [f"{n} {s}" for s, n in sorted(by_sev.items(), key=lambda x: _SEVERITY_ORDER.get(x[0], 99))]
    lines.append("")
    lines.append(f"Status: {', '.join(summary_parts)}")
    return "\n".join(lines)


def format_risk_context(ctx: RiskContext) -> str:
    lines = [
        f"Risk Explanation: {ctx.risk_id} — {ctx.title}",
        "",
        ctx.explanation,
    ]
    if ctx.affected_flows:
        lines.append("")
        lines.append(f"Relevant flows: {', '.join(ctx.affected_flows)}")
    return "\n".join(lines)
