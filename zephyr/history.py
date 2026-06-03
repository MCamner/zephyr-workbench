"""Zephyr Architecture History Tracking and Evolution Analysis.

Builds a timeline from named snapshots of an architecture file. For each
consecutive snapshot pair it computes the structural diff and change impact.
Across the full timeline it tracks the architecture score trend and produces
an evolution assessment.

v0.6.0 capabilities:
  Architecture history tracking  — per-snapshot timeline with diffs
  Architecture evolution analysis — score trend and quality direction

Entry points:
  analyze_history(path) -> HistoryReport
  format_history(report)  -> str
"""

from __future__ import annotations

from dataclasses import dataclass, field

from zephyr.diff import diff_architectures
from zephyr.impact import analyze_impact
from zephyr.models import Architecture
from zephyr.scoring import score_architecture
from zephyr.snapshots import list_snapshots, load_snapshot_architecture


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class HistoryEntry:
    tag: str
    created_at: str
    description: str
    score: int | None
    grade: str | None
    change_count: int          # total items changed from previous snapshot
    impact_severity: str | None  # "none" | "low" | "medium" | "high" | "critical"


@dataclass
class EvolutionTrend:
    direction: str             # "improving" | "degrading" | "stable" | "insufficient_data"
    score_delta: int | None    # last score minus first score
    notes: list[str] = field(default_factory=list)


@dataclass
class HistoryReport:
    path: str
    arch_name: str
    entries: list[HistoryEntry]
    trend: EvolutionTrend
    summary: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "arch_name": self.arch_name,
            "entries": [_entry_to_dict(e) for e in self.entries],
            "trend": {
                "direction": self.trend.direction,
                "score_delta": self.trend.score_delta,
                "notes": self.trend.notes,
            },
            "summary": self.summary,
        }


def _entry_to_dict(e: HistoryEntry) -> dict:
    return {
        "tag": e.tag,
        "created_at": e.created_at,
        "description": e.description,
        "score": e.score,
        "grade": e.grade,
        "change_count": e.change_count,
        "impact_severity": e.impact_severity,
    }


# ── Analysis ──────────────────────────────────────────────────────────────────

def analyze_history(path: str) -> HistoryReport:
    """Build a scored timeline from all snapshots of an architecture model.

    Loads every snapshot, scores it, diffs consecutive pairs, and computes
    the overall evolution trend. Returns HistoryReport.

    If no snapshots exist the report has an empty timeline.
    """
    snapshots = list_snapshots(path)
    entries: list[HistoryEntry] = []
    prev_arch: Architecture | None = None

    for snap in snapshots:
        try:
            arch = load_snapshot_architecture(path, snap.tag)
        except Exception:
            continue

        # Score this snapshot
        try:
            sc = score_architecture(arch)
            score_val: int | None = sc.overall
            grade_val: str | None = sc.grade
        except Exception:
            score_val = None
            grade_val = None

        # Diff + impact vs previous
        if prev_arch is not None:
            diff = diff_architectures(prev_arch, arch)
            total_changes = (
                len(diff.components) + len(diff.flows) +
                len(diff.risks) + len(diff.controls) + len(diff.stakeholders)
            )
            try:
                impact = analyze_impact(prev_arch, arch, diff)
                impact_sev: str | None = impact.severity
            except Exception:
                impact_sev = None
        else:
            total_changes = 0
            impact_sev = None

        entries.append(HistoryEntry(
            tag=snap.tag,
            created_at=snap.created_at,
            description=snap.description,
            score=score_val,
            grade=grade_val,
            change_count=total_changes,
            impact_severity=impact_sev,
        ))
        prev_arch = arch

    # Determine the architecture name from any loaded snapshot
    arch_name = _resolve_arch_name(path, snapshots)
    trend = _compute_trend(entries)
    summary = _build_summary(path, entries, trend)

    return HistoryReport(
        path=path,
        arch_name=arch_name,
        entries=entries,
        trend=trend,
        summary=summary,
    )


def _resolve_arch_name(path: str, snapshots) -> str:
    if not snapshots:
        return path
    try:
        arch = load_snapshot_architecture(path, snapshots[-1].tag)
        return arch.name
    except Exception:
        return path


def _compute_trend(entries: list[HistoryEntry]) -> EvolutionTrend:
    scored = [e for e in entries if e.score is not None]
    if len(scored) < 2:
        return EvolutionTrend(
            direction="insufficient_data",
            score_delta=None,
            notes=["At least two scored snapshots are needed to assess evolution."],
        )

    first_score = scored[0].score
    last_score = scored[-1].score
    delta = last_score - first_score  # type: ignore[operator]
    notes: list[str] = []

    if delta >= 10:
        direction = "improving"
        notes.append(f"Score rose from {first_score} to {last_score} (+{delta}).")
    elif delta <= -10:
        direction = "degrading"
        notes.append(f"Score fell from {first_score} to {last_score} ({delta}).")
    else:
        direction = "stable"
        notes.append(f"Score moved from {first_score} to {last_score} (Δ{delta:+d}).")

    # Note any high-impact changes
    high_impact = [e for e in entries if e.impact_severity in ("critical", "high")]
    if high_impact:
        tags = ", ".join(e.tag for e in high_impact)
        notes.append(f"High-impact changes at: {tags}.")

    return EvolutionTrend(direction=direction, score_delta=delta, notes=notes)


def _build_summary(path: str, entries: list[HistoryEntry], trend: EvolutionTrend) -> str:
    n = len(entries)
    if n == 0:
        return f"No snapshots found for {path}."
    scored = [e for e in entries if e.score is not None]
    score_str = ""
    if scored:
        score_str = f" Latest score: {scored[-1].score} ({scored[-1].grade})."
    total_changes = sum(e.change_count for e in entries)
    return (
        f"{n} snapshot(s), {total_changes} total changes across the timeline."
        f" Trend: {trend.direction}.{score_str}"
    )


# ── Human-readable output ─────────────────────────────────────────────────────

def format_history(report: HistoryReport) -> str:
    _DIR_ICON = {
        "improving": "↑", "degrading": "↓", "stable": "→", "insufficient_data": "?"
    }
    icon = _DIR_ICON.get(report.trend.direction, "?")
    lines = [
        f"History: {report.arch_name}",
        f"Trend:   [{icon}] {report.trend.direction}",
        "",
        report.summary,
    ]

    if not report.entries:
        lines += ["", "No snapshots found."]
        return "\n".join(lines)

    lines += ["", f"{'Tag':<24} {'Date':<22} {'Score':>5}  {'Grade':>5}  {'Changes':>7}  Impact"]
    lines.append("─" * 78)
    for e in report.entries:
        score_str = str(e.score) if e.score is not None else "  —"
        grade_str = e.grade if e.grade else "—"
        impact_str = e.impact_severity or "—"
        lines.append(
            f"  {e.tag:<22} {e.created_at[:19]:<22} {score_str:>5}  {grade_str:>5}  "
            f"{e.change_count:>7}  {impact_str}"
        )
        if e.description:
            lines.append(f"    {e.description}")

    if report.trend.notes:
        lines += ["", "Notes:"]
        for note in report.trend.notes:
            lines.append(f"  {note}")

    return "\n".join(lines)
