"""Zephyr Review Templates.

Predefined, focused review templates that target specific architecture
concerns. Each template runs its own rule set in addition to (or as an
alternative to) the generic review, and includes a manual checklist.

Built-in templates: security, zero-trust, resilience, compliance.

Entry points:
  list_review_templates() -> list[ReviewTemplate]
  get_review_template(name) -> ReviewTemplate | None
  review_with_template(arch, template_name) -> ReviewTemplateResult
"""

from __future__ import annotations

from dataclasses import dataclass, field

from zephyr.intelligence import Finding, review_architecture
from zephyr.models import Architecture


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class ReviewTemplate:
    name: str
    description: str
    focus_areas: list[str]
    checklist: list[str]


@dataclass
class ReviewTemplateResult:
    template: ReviewTemplate
    template_findings: list[Finding]
    generic_findings: list[Finding]

    @property
    def all_findings(self) -> list[Finding]:
        return sorted(self.template_findings + self.generic_findings)

    @property
    def summary(self) -> str:
        total = len(self.all_findings)
        by_sev = {s: sum(1 for f in self.all_findings if f.severity == s)
                  for s in ("risk", "warning", "suggestion", "note")}
        parts = [f"{v} {k}" for k, v in by_sev.items() if v]
        body = ", ".join(parts) if parts else "no findings"
        return f"[{self.template.name}] {total} finding(s): {body}."

    def to_dict(self) -> dict:
        return {
            "template": self.template.name,
            "description": self.template.description,
            "summary": self.summary,
            "template_findings": [_finding_to_dict(f) for f in self.template_findings],
            "generic_findings": [_finding_to_dict(f) for f in self.generic_findings],
            "all_findings": [_finding_to_dict(f) for f in self.all_findings],
            "checklist": self.template.checklist,
            "counts": {
                s: sum(1 for f in self.all_findings if f.severity == s)
                for s in ("risk", "warning", "suggestion", "note")
            },
        }


def _finding_to_dict(f: Finding) -> dict:
    return {"severity": f.severity, "code": f.code, "message": f.message, "affected": f.affected}


# ── Built-in templates ────────────────────────────────────────────────────────

_TEMPLATES: list[ReviewTemplate] = [
    ReviewTemplate(
        name="security",
        description="Security-focused review: controls, encryption, authentication, trust boundaries, and exposure.",
        focus_areas=[
            "Trust boundary definitions and enforcement",
            "External component exposure and gateway routing",
            "Authentication and encryption on flows",
            "Control coverage for high-criticality components",
            "Unmitigated high/critical severity risks",
        ],
        checklist=[
            "All external-facing endpoints are behind an access-gateway",
            "All flows to/from external components use encryption",
            "All flows to/from external components require authentication",
            "Every high-criticality component has at least one control",
            "All high/critical risks have documented mitigations",
            "Trust boundaries are defined and components are assigned to them",
            "No direct internal-to-external flow bypasses security controls",
        ],
    ),
    ReviewTemplate(
        name="zero-trust",
        description="Zero-trust review: identity verification, least privilege, micro-segmentation, and no implicit trust.",
        focus_areas=[
            "Identity provider presence and coverage",
            "Explicit authentication on all flows",
            "Trust boundary micro-segmentation",
            "No implicit trust between components",
            "External exposure without verification controls",
        ],
        checklist=[
            "At least one identity provider component is defined",
            "Every flow involving an external component has authentication set",
            "Trust boundaries are defined for all components",
            "No component trusts another implicitly (authentication on every cross-boundary flow)",
            "High-criticality components have an explicit trust_boundary assignment",
            "Access gateways front all external-to-internal flows",
            "Identity providers cover all authentication flows",
        ],
    ),
    ReviewTemplate(
        name="resilience",
        description="Resilience review: lifecycle health, isolation, hubs, deprecated usage, and single points of failure.",
        focus_areas=[
            "Deprecated components still referenced in active flows",
            "Isolated components with no connections",
            "Hub components with excessive flow degree",
            "High-criticality components with no redundancy signals",
            "Missing lifecycle fields",
        ],
        checklist=[
            "No deprecated components are still referenced in active flows",
            "No critical component is isolated (zero flows)",
            "Hub components with degree > 5 have documented redundancy or HA strategy",
            "All high-criticality components have lifecycle set",
            "Planned components have a clear integration path (flows defined)",
            "No single component is the sole path between external and internal systems",
        ],
    ),
    ReviewTemplate(
        name="compliance",
        description="Compliance review: documentation completeness, risk coverage, control descriptions, and meta fields.",
        focus_areas=[
            "Component and control description completeness",
            "Risk mitigation documentation",
            "Risk likelihood and impact fields",
            "Architecture meta (owner, version, criticality)",
            "Control coverage completeness",
        ],
        checklist=[
            "All components have a non-empty description field",
            "All risks have a documented mitigation",
            "All risks have likelihood and impact set",
            "Architecture meta defines owner, version, and criticality",
            "All controls have a description",
            "All components have criticality set",
            "Risk IDs follow a consistent naming convention",
        ],
    ),
]

_TEMPLATE_MAP: dict[str, ReviewTemplate] = {t.name: t for t in _TEMPLATES}


# ── Public API ────────────────────────────────────────────────────────────────

def list_review_templates() -> list[ReviewTemplate]:
    return list(_TEMPLATES)


def get_review_template(name: str) -> ReviewTemplate | None:
    return _TEMPLATE_MAP.get(name)


def review_with_template(
    arch: Architecture,
    template_name: str,
) -> ReviewTemplateResult:
    """Run a template-focused review plus the generic review.

    Raises ValueError for an unknown template name.
    """
    tmpl = get_review_template(template_name)
    if tmpl is None:
        valid = ", ".join(t.name for t in _TEMPLATES)
        raise ValueError(f"Unknown review template '{template_name}'. Valid: {valid}.")

    template_findings = _RUNNERS[template_name](arch)
    generic_findings = review_architecture(arch)

    return ReviewTemplateResult(
        template=tmpl,
        template_findings=sorted(template_findings),
        generic_findings=sorted(generic_findings),
    )


# ── Template rule runners ─────────────────────────────────────────────────────

def _run_security(arch: Architecture) -> list[Finding]:
    findings: list[Finding] = []
    comp_map = {c.name: c for c in arch.components}
    gateway_names = {c.name for c in arch.components if c.type == "access-gateway"}
    external_names = {c.name for c in arch.components if c.exposure == "external"}
    ctrl_covered: set[str] = set()
    for ctrl in arch.controls:
        ctrl_covered.update(ctrl.applies_to)

    # External components without a gateway path
    if gateway_names:
        for name in external_names:
            direct_targets = {f.target for f in arch.flows if f.source == name}
            direct_targets |= {f.source for f in arch.flows
                                if f.target == name and f.direction == "bidirectional"}
            unsafe = direct_targets - gateway_names
            if unsafe:
                findings.append(Finding(
                    severity="risk",
                    code="security/external-bypasses-gateway",
                    message=f"'{name}' flows to internal component(s) without passing through an access-gateway.",
                    affected=[name] + sorted(unsafe),
                ))
    elif external_names:
        findings.append(Finding(
            severity="risk",
            code="security/no-gateway-defined",
            message="External components are present but no access-gateway is defined.",
            affected=sorted(external_names),
        ))

    # Flows involving external components lacking encryption or authentication
    for f in arch.flows:
        involves_external = f.source in external_names or f.target in external_names
        if not involves_external:
            continue
        label = f"{f.source} → {f.target}"
        if not f.encryption:
            findings.append(Finding(
                severity="warning",
                code="security/flow-unencrypted",
                message=f"Flow '{label}' involves an external component but has no encryption set.",
                affected=[f.source, f.target],
            ))
        if not f.authentication:
            findings.append(Finding(
                severity="warning",
                code="security/flow-unauthenticated",
                message=f"Flow '{label}' involves an external component but has no authentication set.",
                affected=[f.source, f.target],
            ))

    # High-criticality components with no control coverage
    _HIGH_CRIT = {"high", "mission-critical"}
    uncovered_critical = [
        c.name for c in arch.components
        if c.criticality in _HIGH_CRIT and c.name not in ctrl_covered
    ]
    if uncovered_critical:
        findings.append(Finding(
            severity="warning",
            code="security/critical-component-uncontrolled",
            message=f"{len(uncovered_critical)} high-criticality component(s) have no control coverage.",
            affected=uncovered_critical,
        ))

    # No trust boundaries defined at all
    if external_names and not arch.trust_boundaries:
        findings.append(Finding(
            severity="suggestion",
            code="security/no-trust-boundaries",
            message="External components exist but no trust boundaries are defined.",
            affected=[],
        ))

    # Unmitigated high/critical severity risks
    _HIGH_SEV = {"high", "critical"}
    unmitigated = [
        r.id for r in arch.risks
        if r.severity in _HIGH_SEV and not r.mitigation
    ]
    if unmitigated:
        findings.append(Finding(
            severity="risk",
            code="security/unmitigated-high-risk",
            message=f"{len(unmitigated)} high/critical risk(s) have no mitigation: {', '.join(unmitigated)}.",
            affected=unmitigated,
        ))

    return findings


def _run_zero_trust(arch: Architecture) -> list[Finding]:
    findings: list[Finding] = []
    _IDENTITY_TYPES = {"identity", "identity-provider", "cloud-identity", "on-prem-identity"}
    idp_names = {c.name for c in arch.components if c.type in _IDENTITY_TYPES}
    external_names = {c.name for c in arch.components if c.exposure == "external"}
    gateway_names = {c.name for c in arch.components if c.type == "access-gateway"}
    assigned_boundaries = {c.name for c in arch.components if c.trust_boundary}

    # No identity providers
    if not idp_names:
        findings.append(Finding(
            severity="risk",
            code="zero-trust/no-identity-provider",
            message="No identity provider component is defined. Zero-trust requires explicit identity verification.",
            affected=[],
        ))

    # No trust boundaries defined
    if not arch.trust_boundaries:
        findings.append(Finding(
            severity="risk",
            code="zero-trust/no-trust-boundaries",
            message="No trust boundaries are defined. Zero-trust requires explicit network segmentation.",
            affected=[],
        ))

    # External flows without authentication
    unauthenticated_ext = []
    for f in arch.flows:
        if (f.source in external_names or f.target in external_names) and not f.authentication:
            unauthenticated_ext.append(f"{f.source} → {f.target}")
    if unauthenticated_ext:
        findings.append(Finding(
            severity="risk",
            code="zero-trust/unauthenticated-external-flow",
            message=f"{len(unauthenticated_ext)} flow(s) involving external components have no authentication.",
            affected=unauthenticated_ext,
        ))

    # High-criticality components without trust_boundary assignment
    _HIGH_CRIT = {"high", "mission-critical"}
    no_boundary = [
        c.name for c in arch.components
        if c.criticality in _HIGH_CRIT and not c.trust_boundary
    ]
    if no_boundary and arch.trust_boundaries:
        findings.append(Finding(
            severity="warning",
            code="zero-trust/critical-component-no-boundary",
            message=f"{len(no_boundary)} high-criticality component(s) have no trust_boundary assigned.",
            affected=no_boundary,
        ))

    # External components not fronted by a gateway
    if gateway_names:
        for name in external_names:
            direct = {f.target for f in arch.flows if f.source == name}
            direct |= {f.source for f in arch.flows
                       if f.target == name and f.direction == "bidirectional"}
            if direct and not direct & gateway_names:
                findings.append(Finding(
                    severity="warning",
                    code="zero-trust/external-not-via-gateway",
                    message=f"'{name}' (external) connects to internal components without going through an access-gateway.",
                    affected=[name] + sorted(direct),
                ))

    return findings


def _run_resilience(arch: Architecture) -> list[Finding]:
    from zephyr.lifecycle import analyze_lifecycle
    findings: list[Finding] = []

    # Lifecycle issues (delegated)
    lc = analyze_lifecycle(arch)
    _HIGH_CRIT = {"high", "mission-critical"}
    for d in lc.deprecated_in_use:
        findings.append(Finding(
            severity="risk",
            code="resilience/deprecated-in-use",
            message=f"'{d.name}' is deprecated but still referenced in {d.flow_count} active flow(s).",
            affected=[d.name],
        ))

    # Isolated components (no flows at all)
    flow_participants = set()
    for f in arch.flows:
        flow_participants.add(f.source)
        flow_participants.add(f.target)
    isolated_high = [
        c.name for c in arch.components
        if c.name not in flow_participants and c.criticality in _HIGH_CRIT
    ]
    isolated_all = [c.name for c in arch.components if c.name not in flow_participants]
    if isolated_high:
        findings.append(Finding(
            severity="risk",
            code="resilience/critical-component-isolated",
            message=f"{len(isolated_high)} high-criticality component(s) have no flows — possible dead code or broken integration.",
            affected=isolated_high,
        ))
    elif isolated_all:
        findings.append(Finding(
            severity="warning",
            code="resilience/component-isolated",
            message=f"{len(isolated_all)} component(s) have no flows.",
            affected=isolated_all,
        ))

    # Hub components: degree > 5 is a resilience risk
    degree: dict[str, int] = {}
    for f in arch.flows:
        degree[f.source] = degree.get(f.source, 0) + 1
        degree[f.target] = degree.get(f.target, 0) + 1
    hubs = [name for name, deg in degree.items() if deg > 5]
    if hubs:
        findings.append(Finding(
            severity="warning",
            code="resilience/high-degree-hub",
            message=f"{len(hubs)} component(s) have degree > 5, creating potential single points of failure: {', '.join(hubs)}.",
            affected=hubs,
        ))

    # Missing lifecycle on high-criticality components
    no_lc_critical = [
        c.name for c in arch.components
        if c.criticality in _HIGH_CRIT and not c.lifecycle
    ]
    if no_lc_critical:
        findings.append(Finding(
            severity="warning",
            code="resilience/critical-missing-lifecycle",
            message=f"{len(no_lc_critical)} high-criticality component(s) have no lifecycle field.",
            affected=no_lc_critical,
        ))

    # General: components without lifecycle (suggestion)
    if lc.no_lifecycle:
        findings.append(Finding(
            severity="suggestion",
            code="resilience/missing-lifecycle",
            message=f"{len(lc.no_lifecycle)} component(s) are missing a lifecycle field.",
            affected=lc.no_lifecycle,
        ))

    return findings


def _run_compliance(arch: Architecture) -> list[Finding]:
    findings: list[Finding] = []

    # Components without description
    no_desc = [c.name for c in arch.components if not c.description]
    if no_desc:
        findings.append(Finding(
            severity="suggestion",
            code="compliance/component-missing-description",
            message=f"{len(no_desc)} component(s) have no description.",
            affected=no_desc,
        ))

    # Components without criticality
    no_crit = [c.name for c in arch.components if not c.criticality]
    if no_crit:
        findings.append(Finding(
            severity="suggestion",
            code="compliance/component-missing-criticality",
            message=f"{len(no_crit)} component(s) have no criticality set.",
            affected=no_crit,
        ))

    # Risks without mitigation
    no_mit = [r.id for r in arch.risks if not r.mitigation]
    if no_mit:
        findings.append(Finding(
            severity="warning",
            code="compliance/risk-missing-mitigation",
            message=f"{len(no_mit)} risk(s) have no mitigation documented: {', '.join(no_mit)}.",
            affected=no_mit,
        ))

    # Risks without likelihood or impact
    no_likelihood = [r.id for r in arch.risks if not r.likelihood]
    no_impact = [r.id for r in arch.risks if not r.impact]
    if no_likelihood:
        findings.append(Finding(
            severity="suggestion",
            code="compliance/risk-missing-likelihood",
            message=f"{len(no_likelihood)} risk(s) have no likelihood set.",
            affected=no_likelihood,
        ))
    if no_impact:
        findings.append(Finding(
            severity="suggestion",
            code="compliance/risk-missing-impact",
            message=f"{len(no_impact)} risk(s) have no impact set.",
            affected=no_impact,
        ))

    # Controls without description
    no_ctrl_desc = [c.name for c in arch.controls if not c.description]
    if no_ctrl_desc:
        findings.append(Finding(
            severity="suggestion",
            code="compliance/control-missing-description",
            message=f"{len(no_ctrl_desc)} control(s) have no description.",
            affected=no_ctrl_desc,
        ))

    # Meta completeness
    if arch.meta is None:
        findings.append(Finding(
            severity="warning",
            code="compliance/no-meta",
            message="Architecture has no meta block (owner, version, criticality).",
            affected=[],
        ))
    else:
        missing_meta = [f for f in ("owner", "version", "criticality") if not getattr(arch.meta, f)]
        if missing_meta:
            findings.append(Finding(
                severity="suggestion",
                code="compliance/meta-incomplete",
                message=f"Meta block is missing: {', '.join(missing_meta)}.",
                affected=[],
            ))

    return findings


_RUNNERS = {
    "security": _run_security,
    "zero-trust": _run_zero_trust,
    "resilience": _run_resilience,
    "compliance": _run_compliance,
}


# ── Human-readable output ─────────────────────────────────────────────────────

def format_review_template_result(result: ReviewTemplateResult, arch_name: str) -> str:
    tmpl = result.template
    lines = [
        f"Review [{tmpl.name}]: {arch_name}",
        f"  {tmpl.description}",
        "",
    ]

    all_f = result.all_findings
    if not all_f:
        lines.append("  No findings.")
    else:
        _SEV_SYM = {"risk": "✗", "warning": "!", "suggestion": "~", "note": "-"}
        lines.append(f"Findings ({len(all_f)}):")
        for f in all_f:
            sym = _SEV_SYM.get(f.severity, "?")
            lines.append(f"  [{sym}] [{f.severity.upper():<10}] {f.code}")
            lines.append(f"        {f.message}")
        lines.append("")
        by_sev = {s: sum(1 for f in all_f if f.severity == s)
                  for s in ("risk", "warning", "suggestion", "note")}
        summary_parts = [f"{v} {k}" for k, v in by_sev.items() if v]
        lines.append(f"Summary: {', '.join(summary_parts)}")

    lines += ["", "Checklist (manual verification):"]
    for item in tmpl.checklist:
        lines.append(f"  [ ] {item}")

    return "\n".join(lines)


def format_template_list() -> str:
    lines = ["Available review templates:", ""]
    for t in _TEMPLATES:
        lines.append(f"  {t.name:<14} {t.description}")
    return "\n".join(lines)
