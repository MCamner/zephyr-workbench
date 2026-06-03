"""Zephyr Architecture Governance Workflows.

Validates an architecture model against a governance policy file (YAML).
Each policy defines a set of rules; violations produce structured findings
that gate CI pipelines or review approvals.

Policy YAML schema:

  name: "Enterprise Security Policy"
  version: "1.0"
  default_severity: error   # error | warning (default: error)

  rules:
    - id: GOV-01
      description: "All components must have a description"
      type: require_field
      target: components
      field: description
      severity: warning          # override default_severity

    - id: GOV-02
      description: "At least one access-gateway must exist"
      type: require_component_type
      component_type: access-gateway

    - id: GOV-03
      description: "Architecture meta must define an owner"
      type: require_meta_field
      field: owner

    - id: GOV-04
      description: "Trust boundaries must be defined"
      type: require_trust_boundaries

    - id: GOV-05
      description: "No external component bypasses an access-gateway"
      type: prohibit_external_bypass

    - id: GOV-06
      description: "High-criticality components must have control coverage"
      type: require_control_coverage
      target: high_criticality   # all | high_criticality (default: all)

Supported rule types:
  require_field          — all items of `target` (components/risks/controls/flows)
                           must have a non-empty value for `field`
  require_component_type — at least one component of `component_type` must exist
  require_meta_field     — meta block must exist and `field` must be non-empty
  require_meta           — meta block must exist
  require_trust_boundaries — at least one trust boundary must be defined
  prohibit_external_bypass — external components must route through an access-gateway
  require_control_coverage — components matching `target` must each have ≥1 control

Entry points:
  load_governance_policy(path) -> GovernancePolicy
  check_governance(arch, policy) -> GovernanceResult
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from zephyr.models import Architecture


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class GovernanceRule:
    id: str
    description: str
    type: str
    severity: str                      # "error" | "warning"
    params: dict[str, Any]             # rule-type-specific parameters


@dataclass
class GovernancePolicy:
    name: str
    version: str
    rules: list[GovernanceRule]


@dataclass
class GovernanceViolation:
    rule_id: str
    description: str
    severity: str                      # "error" | "warning"
    message: str
    affected: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "severity": self.severity,
            "message": self.message,
            "affected": self.affected,
        }


@dataclass
class GovernanceResult:
    policy_name: str
    policy_version: str
    violations: list[GovernanceViolation]
    passed_rule_ids: list[str]

    @property
    def status(self) -> str:
        return "failed" if any(v.severity == "error" for v in self.violations) else "passed"

    @property
    def has_errors(self) -> bool:
        return any(v.severity == "error" for v in self.violations)

    def to_dict(self) -> dict:
        return {
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
            "status": self.status,
            "violations": [v.to_dict() for v in self.violations],
            "passed_rule_ids": self.passed_rule_ids,
            "counts": {
                "total_rules": len(self.violations) + len(self.passed_rule_ids),
                "passed": len(self.passed_rule_ids),
                "violations": len(self.violations),
                "errors": sum(1 for v in self.violations if v.severity == "error"),
                "warnings": sum(1 for v in self.violations if v.severity == "warning"),
            },
        }


class GovernancePolicyError(Exception):
    pass


# ── Policy loading ────────────────────────────────────────────────────────────

def load_governance_policy(path: str | Path) -> GovernancePolicy:
    """Load and parse a governance policy YAML file.

    Raises GovernancePolicyError on missing file or schema errors.
    """
    p = Path(path)
    if not p.exists():
        raise GovernancePolicyError(f"Policy file not found: {path}")
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise GovernancePolicyError(f"Invalid YAML in policy file: {exc}") from exc
    if not isinstance(data, dict):
        raise GovernancePolicyError("Policy file root must be a YAML mapping.")

    name = data.get("name", "")
    version = str(data.get("version", ""))
    default_sev = str(data.get("default_severity", "error")).lower()
    if default_sev not in ("error", "warning"):
        default_sev = "error"

    raw_rules = data.get("rules", [])
    if not isinstance(raw_rules, list):
        raise GovernancePolicyError("'rules' must be a list.")

    rules: list[GovernanceRule] = []
    for i, raw in enumerate(raw_rules):
        if not isinstance(raw, dict):
            raise GovernancePolicyError(f"Rule {i} must be a mapping.")
        rule_id = str(raw.get("id", f"RULE-{i}"))
        desc = str(raw.get("description", ""))
        rtype = str(raw.get("type", ""))
        if not rtype:
            raise GovernancePolicyError(f"Rule '{rule_id}' is missing 'type'.")
        sev = str(raw.get("severity", default_sev)).lower()
        if sev not in ("error", "warning"):
            sev = default_sev
        params = {k: v for k, v in raw.items()
                  if k not in ("id", "description", "type", "severity")}
        rules.append(GovernanceRule(id=rule_id, description=desc, type=rtype,
                                    severity=sev, params=params))

    return GovernancePolicy(name=name, version=version, rules=rules)


# ── Governance checking ───────────────────────────────────────────────────────

def check_governance(
    arch: Architecture,
    policy: GovernancePolicy,
) -> GovernanceResult:
    """Evaluate an architecture against a governance policy."""
    violations: list[GovernanceViolation] = []
    passed: list[str] = []

    for rule in policy.rules:
        violation = _evaluate_rule(arch, rule)
        if violation is not None:
            violations.append(violation)
        else:
            passed.append(rule.id)

    return GovernanceResult(
        policy_name=policy.name,
        policy_version=policy.version,
        violations=violations,
        passed_rule_ids=passed,
    )


def _evaluate_rule(arch: Architecture, rule: GovernanceRule) -> GovernanceViolation | None:
    """Return a violation if the rule is breached, None if it passes."""
    rtype = rule.type
    if rtype == "require_field":
        return _rule_require_field(arch, rule)
    if rtype == "require_component_type":
        return _rule_require_component_type(arch, rule)
    if rtype == "require_meta_field":
        return _rule_require_meta_field(arch, rule)
    if rtype == "require_meta":
        return _rule_require_meta(arch, rule)
    if rtype == "require_trust_boundaries":
        return _rule_require_trust_boundaries(arch, rule)
    if rtype == "prohibit_external_bypass":
        return _rule_prohibit_external_bypass(arch, rule)
    if rtype == "require_control_coverage":
        return _rule_require_control_coverage(arch, rule)
    return GovernanceViolation(
        rule_id=rule.id,
        description=rule.description,
        severity=rule.severity,
        message=f"Unknown rule type '{rtype}'. Check policy file.",
    )


def _violation(rule: GovernanceRule, message: str, affected: list[str] | None = None) -> GovernanceViolation:
    return GovernanceViolation(
        rule_id=rule.id,
        description=rule.description,
        severity=rule.severity,
        message=message,
        affected=affected or [],
    )


# ── Rule implementations ──────────────────────────────────────────────────────

def _rule_require_field(arch: Architecture, rule: GovernanceRule) -> GovernanceViolation | None:
    target = rule.params.get("target", "components")
    field_name = rule.params.get("field", "")
    if not field_name:
        return _violation(rule, "Rule misconfigured: 'field' is required for require_field.")

    if target == "components":
        items = arch.components
    elif target == "risks":
        items = arch.risks  # type: ignore[assignment]
    elif target == "controls":
        items = arch.controls  # type: ignore[assignment]
    elif target == "flows":
        items = arch.flows  # type: ignore[assignment]
    else:
        return _violation(rule, f"Rule misconfigured: unknown target '{target}'.")

    missing = [
        getattr(item, "name", getattr(item, "id", str(item)))
        for item in items
        if not getattr(item, field_name, None)
    ]
    if missing:
        return _violation(
            rule,
            f"{len(missing)} {target} missing '{field_name}': {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}.",
            missing,
        )
    return None


def _rule_require_component_type(arch: Architecture, rule: GovernanceRule) -> GovernanceViolation | None:
    comp_type = rule.params.get("component_type", "")
    if not comp_type:
        return _violation(rule, "Rule misconfigured: 'component_type' is required.")
    exists = any(c.type == comp_type for c in arch.components)
    if not exists:
        return _violation(rule, f"No component of type '{comp_type}' found.")
    return None


def _rule_require_meta_field(arch: Architecture, rule: GovernanceRule) -> GovernanceViolation | None:
    field_name = rule.params.get("field", "")
    if not field_name:
        return _violation(rule, "Rule misconfigured: 'field' is required for require_meta_field.")
    if arch.meta is None:
        return _violation(rule, f"Architecture has no meta block (required for '{field_name}').")
    if not getattr(arch.meta, field_name, None):
        return _violation(rule, f"Meta field '{field_name}' is empty or missing.")
    return None


def _rule_require_meta(arch: Architecture, rule: GovernanceRule) -> GovernanceViolation | None:
    if arch.meta is None:
        return _violation(rule, "Architecture has no meta block.")
    return None


def _rule_require_trust_boundaries(arch: Architecture, rule: GovernanceRule) -> GovernanceViolation | None:
    if not arch.trust_boundaries:
        return _violation(rule, "No trust boundaries are defined.")
    return None


def _rule_prohibit_external_bypass(arch: Architecture, rule: GovernanceRule) -> GovernanceViolation | None:
    gateway_names = {c.name for c in arch.components if c.type == "access-gateway"}
    external_names = {c.name for c in arch.components if c.exposure == "external"}

    if not external_names:
        return None
    if not gateway_names:
        return _violation(
            rule,
            "External components exist but no access-gateway is defined.",
            sorted(external_names),
        )

    bypass_flows: list[str] = []
    for f in arch.flows:
        if f.source in external_names and f.target not in gateway_names:
            bypass_flows.append(f"{f.source} → {f.target}")
        if f.direction == "bidirectional" and f.target in external_names and f.source not in gateway_names:
            bypass_flows.append(f"{f.target} → {f.source}")

    if bypass_flows:
        return _violation(
            rule,
            f"{len(bypass_flows)} flow(s) bypass the access-gateway: {', '.join(bypass_flows[:3])}{'...' if len(bypass_flows) > 3 else ''}.",
            bypass_flows,
        )
    return None


def _rule_require_control_coverage(arch: Architecture, rule: GovernanceRule) -> GovernanceViolation | None:
    target = rule.params.get("target", "all")
    covered = set()
    for ctrl in arch.controls:
        covered.update(ctrl.applies_to)

    _HIGH_CRIT = {"high", "mission-critical"}
    if target == "high_criticality":
        candidates = [c for c in arch.components if c.criticality in _HIGH_CRIT]
    else:
        candidates = list(arch.components)

    if not candidates:
        return None

    uncovered = [c.name for c in candidates if c.name not in covered]
    if uncovered:
        scope = "high-criticality " if target == "high_criticality" else ""
        return _violation(
            rule,
            f"{len(uncovered)} {scope}component(s) have no control coverage: {', '.join(uncovered[:5])}{'...' if len(uncovered) > 5 else ''}.",
            uncovered,
        )
    return None


# ── Human-readable output ─────────────────────────────────────────────────────

def format_governance_result(result: GovernanceResult, policy_path: str, arch_name: str) -> str:
    total = len(result.violations) + len(result.passed_rule_ids)
    status_icon = "✗ FAILED" if result.has_errors else ("~ WARNINGS" if result.violations else "✓ PASSED")

    lines = [
        f"Governance: {arch_name}",
        f"Policy: {result.policy_name or policy_path}"
        + (f" v{result.policy_version}" if result.policy_version else ""),
        "",
    ]

    all_rule_ids = result.passed_rule_ids + [v.rule_id for v in result.violations]
    violation_map = {v.rule_id: v for v in result.violations}

    for rule_id in sorted(all_rule_ids):
        if rule_id in violation_map:
            v = violation_map[rule_id]
            sym = "✗" if v.severity == "error" else "~"
            lines.append(f"  [{sym}] {rule_id}: {v.description}")
            lines.append(f"        {v.message}")
        else:
            lines.append(f"  [✓] {rule_id}: passed")

    lines += [
        "",
        f"Result: {status_icon}  "
        f"({len(result.passed_rule_ids)}/{total} rules passed"
        + (f", {sum(1 for v in result.violations if v.severity == 'error')} error(s)"
           if result.has_errors else "")
        + ")",
    ]
    return "\n".join(lines)
