"""Zephyr Architecture Scoring.

Computes a multi-dimensional quality score for an architecture model.
All scoring is deterministic and rule-based — no LLM calls required.

Five dimensions (weights):
  risk_health          (30%) — mitigation coverage and risk definition quality
  control_coverage     (20%) — controls relative to risks
  component_maturity   (20%) — description, lifecycle, criticality completeness
  structural_health    (15%) — dependency balance, hub coupling, isolated nodes
  definition_completeness (15%) — flow security fields, meta fields, domain coverage
"""

from __future__ import annotations

from dataclasses import dataclass, field

from zephyr.models import Architecture


# ── Constants ─────────────────────────────────────────────────────────────────

_SEVERITY_PENALTY = {"critical": 25, "high": 15, "medium": 8, "low": 3}
_GRADE_THRESHOLDS = [(90, "A"), (75, "B"), (60, "C"), (45, "D")]

_WEIGHTS = {
    "risk_health": 0.30,
    "control_coverage": 0.20,
    "component_maturity": 0.20,
    "structural_health": 0.15,
    "definition_completeness": 0.15,
}


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class DimensionScore:
    name: str
    score: int          # 0–100
    weight: float
    notes: list[str] = field(default_factory=list)

    @property
    def weighted(self) -> float:
        return self.score * self.weight


@dataclass
class ArchitectureScore:
    overall: int                          # 0–100
    grade: str                            # A / B / C / D / F
    dimensions: list[DimensionScore]
    summary: str

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "grade": self.grade,
            "summary": self.summary,
            "dimensions": [
                {
                    "name": d.name,
                    "score": d.score,
                    "weight": d.weight,
                    "weighted_contribution": round(d.weighted, 1),
                    "notes": d.notes,
                }
                for d in self.dimensions
            ],
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def _grade(score: int) -> str:
    for threshold, letter in _GRADE_THRESHOLDS:
        if score >= threshold:
            return letter
    return "F"


def _ratio_score(numerator: int, denominator: int) -> int:
    if denominator == 0:
        return 100
    return _clamp(100 * numerator / denominator)


# ── Dimension scorers ─────────────────────────────────────────────────────────

def _score_risk_health(arch: Architecture) -> DimensionScore:
    notes: list[str] = []
    if not arch.risks:
        return DimensionScore("risk_health", 100, _WEIGHTS["risk_health"], ["No risks defined — full score by default"])

    score = 100
    unmitigated = [r for r in arch.risks if not r.mitigation]
    for r in unmitigated:
        penalty = _SEVERITY_PENALTY.get(r.severity, 5)
        score -= penalty

    incomplete = [r for r in arch.risks if not r.likelihood or not r.impact]
    score -= len(incomplete) * 5

    if unmitigated:
        notes.append(f"{len(unmitigated)} unmitigated risk(s)")
    if incomplete:
        notes.append(f"{len(incomplete)} risk(s) missing likelihood/impact")
    if not notes:
        notes.append("All risks mitigated and fully defined")

    return DimensionScore("risk_health", _clamp(score), _WEIGHTS["risk_health"], notes)


def _score_control_coverage(arch: Architecture) -> DimensionScore:
    notes: list[str] = []
    n_risks = len(arch.risks)
    n_controls = len(arch.controls)

    if n_risks == 0 and n_controls == 0:
        return DimensionScore("control_coverage", 100, _WEIGHTS["control_coverage"], ["No risks or controls — full score by default"])

    raw = _ratio_score(n_controls, n_risks)

    with_applies = sum(1 for c in arch.controls if c.applies_to)
    coverage_bonus = 5 if with_applies == n_controls and n_controls > 0 else 0

    score = _clamp(raw + coverage_bonus)
    notes.append(f"{n_controls} control(s) for {n_risks} risk(s)")
    if coverage_bonus:
        notes.append("All controls have applies_to populated")
    elif n_controls > 0:
        missing = n_controls - with_applies
        notes.append(f"{missing} control(s) missing applies_to")

    return DimensionScore("control_coverage", score, _WEIGHTS["control_coverage"], notes)


def _score_component_maturity(arch: Architecture) -> DimensionScore:
    notes: list[str] = []
    n = len(arch.components)
    if n == 0:
        return DimensionScore("component_maturity", 0, _WEIGHTS["component_maturity"], ["No components defined"])

    score = 100
    no_description = [c for c in arch.components if not c.description]
    no_criticality = [c for c in arch.components if not c.criticality]
    deprecated = [c for c in arch.components if c.lifecycle == "deprecated"]
    has_boundaries = bool(arch.trust_boundaries)
    no_boundary = [c for c in arch.components if has_boundaries and not c.trust_boundary]

    score -= len(no_description) * 5
    score -= len(no_criticality) * 4
    score -= len(deprecated) * 10
    score -= len(no_boundary) * 3

    if no_description:
        notes.append(f"{len(no_description)} component(s) without description")
    if no_criticality:
        notes.append(f"{len(no_criticality)} component(s) without criticality")
    if deprecated:
        notes.append(f"{len(deprecated)} deprecated component(s)")
    if no_boundary:
        notes.append(f"{len(no_boundary)} component(s) without trust boundary assignment")
    if not notes:
        notes.append("All components well-defined")

    return DimensionScore("component_maturity", _clamp(score), _WEIGHTS["component_maturity"], notes)


def _score_structural_health(arch: Architecture) -> DimensionScore:
    notes: list[str] = []
    n = len(arch.components)
    if n == 0:
        return DimensionScore("structural_health", 0, _WEIGHTS["structural_health"], ["No components defined"])

    # Build degree map
    degree: dict[str, int] = {c.name: 0 for c in arch.components}
    component_names = set(degree)
    connected: set[str] = set()
    for f in arch.flows:
        if f.source in degree:
            degree[f.source] += 1
            connected.add(f.source)
        if f.target in degree:
            degree[f.target] += 1
            connected.add(f.target)

    isolated = [name for name in component_names if name not in connected]
    hub_threshold = max(5, n // 2)
    hubs = [(name, deg) for name, deg in degree.items() if deg > hub_threshold]

    score = 100
    score -= len(isolated) * 8
    score -= len(hubs) * 10

    if isolated:
        notes.append(f"{len(isolated)} isolated component(s) (no flows)")
    if hubs:
        names = ", ".join(f"{name}({deg})" for name, deg in hubs[:3])
        notes.append(f"High-coupling hub(s): {names}")
    if not isolated and not hubs:
        notes.append("Balanced dependency structure")

    return DimensionScore("structural_health", _clamp(score), _WEIGHTS["structural_health"], notes)


def _score_definition_completeness(arch: Architecture) -> DimensionScore:
    notes: list[str] = []
    parts: list[int] = []

    # Flow security fields
    n_flows = len(arch.flows)
    if n_flows > 0:
        auth_score = _ratio_score(sum(1 for f in arch.flows if f.authentication), n_flows)
        enc_score = _ratio_score(sum(1 for f in arch.flows if f.encryption), n_flows)
        parts.extend([auth_score, enc_score])
        if auth_score < 100:
            notes.append(f"{n_flows - sum(1 for f in arch.flows if f.authentication)} flow(s) without authentication")
        if enc_score < 100:
            notes.append(f"{n_flows - sum(1 for f in arch.flows if f.encryption)} flow(s) without encryption")
    else:
        parts.append(100)

    # Component domain coverage
    n_comp = len(arch.components)
    if n_comp > 0:
        domain_score = _ratio_score(sum(1 for c in arch.components if c.domain), n_comp)
        parts.append(domain_score)
        if domain_score < 100:
            notes.append(f"{n_comp - sum(1 for c in arch.components if c.domain)} component(s) without domain")

    # Meta completeness
    meta_fields = 0
    meta_total = 3
    if arch.meta:
        if arch.meta.owner:
            meta_fields += 1
        if arch.meta.version:
            meta_fields += 1
        if arch.meta.criticality:
            meta_fields += 1
    parts.append(_ratio_score(meta_fields, meta_total))
    if meta_fields < meta_total:
        notes.append(f"Meta incomplete ({meta_fields}/{meta_total} fields set)")

    score = _clamp(sum(parts) / len(parts)) if parts else 0
    if not notes:
        notes.append("All definition fields populated")

    return DimensionScore("definition_completeness", score, _WEIGHTS["definition_completeness"], notes)


# ── Public API ────────────────────────────────────────────────────────────────

def score_architecture(arch: Architecture) -> ArchitectureScore:
    dimensions = [
        _score_risk_health(arch),
        _score_control_coverage(arch),
        _score_component_maturity(arch),
        _score_structural_health(arch),
        _score_definition_completeness(arch),
    ]

    overall = _clamp(sum(d.weighted for d in dimensions))
    grade = _grade(overall)

    grade_labels = {"A": "excellent", "B": "good", "C": "fair", "D": "poor", "F": "critical"}
    label = grade_labels.get(grade, "unknown")
    n_issues = sum(len(d.notes) for d in dimensions if d.score < 80)
    summary = (
        f"Architecture scores {overall}/100 (grade {grade} — {label}). "
        f"{n_issues} dimension(s) below 80 with improvement opportunities."
        if n_issues else
        f"Architecture scores {overall}/100 (grade {grade} — {label}). All dimensions healthy."
    )

    return ArchitectureScore(overall=overall, grade=grade, dimensions=dimensions, summary=summary)
