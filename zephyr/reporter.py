"""Zephyr Architecture Review Reports.

Generates comprehensive Markdown or HTML review reports combining scoring,
intelligence analysis, risk tables, and dependency insights into one document.

Entry point: generate_report(arch, format="md") -> str
"""

from __future__ import annotations

import datetime
from typing import Literal

from zephyr.intelligence import ArchitectureAnalysis, analyze_architecture
from zephyr.models import Architecture
from zephyr.scoring import ArchitectureScore, score_architecture

ReportFormat = Literal["md", "html"]

_SEVERITY_ICON = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
    "risk": "🔴",
    "warning": "🟡",
    "suggestion": "🔵",
    "note": "⚪",
}

_GRADE_LABEL = {"A": "Excellent", "B": "Good", "C": "Fair", "D": "Poor", "F": "Critical"}


# ── Markdown generation ────────────────────────────────────────────────────────

def _md_report(arch: Architecture, score: ArchitectureScore, analysis: ArchitectureAnalysis) -> str:
    date = datetime.date.today().isoformat()
    lines: list[str] = []

    # Header
    lines += [
        f"# Architecture Review: {arch.name}",
        "",
        f"**Date:** {date}  ",
        f"**Score:** {score.overall}/100 — Grade {score.grade} ({_GRADE_LABEL.get(score.grade, '')})",
    ]
    if arch.meta:
        if arch.meta.owner:
            lines.append(f"**Owner:** {arch.meta.owner}  ")
        if arch.meta.version:
            lines.append(f"**Version:** {arch.meta.version}  ")
        if arch.meta.environment:
            lines.append(f"**Environment:** {', '.join(arch.meta.environment)}  ")
    lines += ["", "---", ""]

    # Score card
    lines += ["## Score Card", ""]
    lines += ["| Dimension | Score | Weight | Notes |", "|---|---|---|---|"]
    for d in score.dimensions:
        bar = "█" * round(d.score / 10) + "░" * (10 - round(d.score / 10))
        note = "; ".join(d.notes[:2]) if d.notes else "—"
        lines.append(f"| {d.name} | {bar} {d.score} | {int(d.weight * 100)}% | {note} |")
    lines += ["", f"**Summary:** {score.summary}", "", "---", ""]

    # Narrative
    lines += ["## Narrative", "", analysis.narrative, "", "---", ""]

    # Risks
    lines += ["## Risks", ""]
    if arch.risks:
        lines += ["| ID | Severity | Title | Mitigated | Likelihood | Impact |", "|---|---|---|---|---|---|"]
        for r in sorted(arch.risks, key=lambda x: ["critical", "high", "medium", "low"].index(x.severity) if x.severity in ["critical", "high", "medium", "low"] else 99):
            icon = _SEVERITY_ICON.get(r.severity, "")
            mitigated = "✅" if r.mitigation else "❌"
            lines.append(f"| {r.id} | {icon} {r.severity} | {r.title} | {mitigated} | {r.likelihood or '—'} | {r.impact or '—'} |")
    else:
        lines.append("_No risks defined._")
    lines += ["", "---", ""]

    # Findings
    findings = analysis.all_findings()
    lines += ["## Findings", ""]
    if findings:
        for f in findings:
            icon = _SEVERITY_ICON.get(f.severity, "•")
            affected = f", ".join(f.affected) if f.affected else "—"
            lines.append(f"- {icon} **[{f.severity.upper()}]** `{f.code}` — {f.message}")
            if f.affected:
                lines.append(f"  _Affected: {affected}_")
    else:
        lines.append("_No findings._")
    lines += ["", "---", ""]

    # Dependency insights
    di = analysis.dependency_insights
    lines += ["## Dependency Insights", ""]
    if di.hub_components:
        lines.append("**Hub components** (high coupling):")
        for name, degree in di.hub_components:
            lines.append(f"- `{name}` ({degree} flows)")
        lines.append("")
    if di.isolated_components:
        lines.append("**Isolated components** (no flows):")
        for name in di.isolated_components:
            lines.append(f"- `{name}`")
        lines.append("")
    if di.external_reachable:
        lines.append("**External reach** (reachable from external nodes):")
        for ext, reachable in list(di.external_reachable.items())[:5]:
            lines.append(f"- `{ext}` → {', '.join(f'`{r}`' for r in reachable[:4])}")
        lines.append("")
    if not di.hub_components and not di.isolated_components and not di.external_reachable:
        lines.append("_No dependency concerns detected._")
    lines += ["", "---", ""]

    # Controls
    lines += ["## Controls", ""]
    if arch.controls:
        lines += ["| Name | Type | Applies To |", "|---|---|---|"]
        for c in arch.controls:
            applies = ", ".join(c.applies_to) if c.applies_to else "—"
            lines.append(f"| {c.name} | {c.type} | {applies} |")
    else:
        lines.append("_No controls defined._")
    lines += [""]

    return "\n".join(lines)


# ── HTML generation ────────────────────────────────────────────────────────────

def _html_report(arch: Architecture, score: ArchitectureScore, analysis: ArchitectureAnalysis) -> str:
    md = _md_report(arch, score, analysis)
    grade_color = {"A": "#22c55e", "B": "#84cc16", "C": "#eab308", "D": "#f97316", "F": "#ef4444"}
    color = grade_color.get(score.grade, "#6b7280")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Architecture Review: {arch.name}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; color: #1f2937; background: #f9fafb; }}
  h1 {{ font-size: 1.8rem; margin-bottom: 0.25rem; }}
  h2 {{ font-size: 1.2rem; color: #374151; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3rem; margin-top: 2rem; }}
  .grade-badge {{ display: inline-block; background: {color}; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-weight: 700; font-size: 1.1rem; margin-left: 0.5rem; }}
  .score-bar {{ font-family: monospace; color: #6366f1; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; margin: 1rem 0; }}
  th {{ background: #f3f4f6; text-align: left; padding: 0.5rem 0.75rem; font-weight: 600; }}
  td {{ padding: 0.4rem 0.75rem; border-bottom: 1px solid #e5e7eb; }}
  code {{ background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 3px; font-size: 0.85em; }}
  .narrative {{ background: white; border-left: 3px solid #6366f1; padding: 1rem 1.25rem; border-radius: 0 4px 4px 0; white-space: pre-wrap; font-size: 0.95rem; line-height: 1.6; }}
  .finding {{ margin: 0.4rem 0; padding: 0.4rem 0.75rem; border-radius: 4px; background: white; border-left: 3px solid #d1d5db; }}
  .finding.risk {{ border-color: #ef4444; }}
  .finding.warning {{ border-color: #eab308; }}
  .finding.suggestion {{ border-color: #6366f1; }}
  .finding.note {{ border-color: #9ca3af; }}
  .meta {{ color: #6b7280; font-size: 0.9rem; margin-bottom: 1rem; }}
  hr {{ border: none; border-top: 1px solid #e5e7eb; margin: 1.5rem 0; }}
</style>
</head>
<body>
<h1>{arch.name} <span class="grade-badge">Grade {score.grade}</span></h1>
<div class="meta">
  Score: <strong>{score.overall}/100</strong> &nbsp;·&nbsp;
  {_GRADE_LABEL.get(score.grade, '')} &nbsp;·&nbsp;
  {datetime.date.today().isoformat()}
  {"&nbsp;·&nbsp; Owner: " + arch.meta.owner if arch.meta and arch.meta.owner else ""}
</div>

<h2>Score Card</h2>
<table>
  <thead><tr><th>Dimension</th><th>Score</th><th>Weight</th><th>Notes</th></tr></thead>
  <tbody>
{"".join(
    f'  <tr><td>{d.name}</td>'
    f'<td><span class="score-bar">{"█" * round(d.score/10)}{"░" * (10 - round(d.score/10))}</span> {d.score}</td>'
    f'<td>{int(d.weight*100)}%</td>'
    f'<td>{"; ".join(d.notes[:2]) if d.notes else "—"}</td></tr>'
    for d in score.dimensions
)}
  </tbody>
</table>
<p>{score.summary}</p>
<hr>

<h2>Narrative</h2>
<div class="narrative">{analysis.narrative}</div>
<hr>

<h2>Risks</h2>
{_html_risks(arch)}
<hr>

<h2>Findings</h2>
{_html_findings(analysis)}
<hr>

<h2>Dependency Insights</h2>
{_html_deps(analysis)}
<hr>

<h2>Controls</h2>
{_html_controls(arch)}

</body>
</html>"""


def _html_risks(arch: Architecture) -> str:
    if not arch.risks:
        return "<p><em>No risks defined.</em></p>"
    severity_order = ["critical", "high", "medium", "low"]
    rows = sorted(arch.risks, key=lambda r: severity_order.index(r.severity) if r.severity in severity_order else 99)
    html = '<table><thead><tr><th>ID</th><th>Severity</th><th>Title</th><th>Mitigated</th><th>Likelihood</th><th>Impact</th></tr></thead><tbody>'
    for r in rows:
        icon = _SEVERITY_ICON.get(r.severity, "")
        mit = "✅" if r.mitigation else "❌"
        html += f'<tr><td><code>{r.id}</code></td><td>{icon} {r.severity}</td><td>{r.title}</td><td>{mit}</td><td>{r.likelihood or "—"}</td><td>{r.impact or "—"}</td></tr>'
    return html + "</tbody></table>"


def _html_findings(analysis: ArchitectureAnalysis) -> str:
    findings = analysis.all_findings()
    if not findings:
        return "<p><em>No findings.</em></p>"
    parts = []
    for f in findings:
        icon = _SEVERITY_ICON.get(f.severity, "•")
        affected = f"<br><small>Affected: {', '.join(f.affected)}</small>" if f.affected else ""
        parts.append(
            f'<div class="finding {f.severity}">'
            f'{icon} <strong>[{f.severity.upper()}]</strong> <code>{f.code}</code> — {f.message}'
            f'{affected}</div>'
        )
    return "\n".join(parts)


def _html_deps(analysis: ArchitectureAnalysis) -> str:
    di = analysis.dependency_insights
    parts = []
    if di.hub_components:
        parts.append("<p><strong>Hub components</strong> (high coupling):</p><ul>")
        for name, deg in di.hub_components:
            parts.append(f"<li><code>{name}</code> ({deg} flows)</li>")
        parts.append("</ul>")
    if di.isolated_components:
        parts.append("<p><strong>Isolated components</strong> (no flows):</p><ul>")
        for name in di.isolated_components:
            parts.append(f"<li><code>{name}</code></li>")
        parts.append("</ul>")
    if di.external_reachable:
        parts.append("<p><strong>External reach:</strong></p><ul>")
        for ext, reachable in list(di.external_reachable.items())[:5]:
            parts.append(f"<li><code>{ext}</code> → {', '.join(f'<code>{r}</code>' for r in reachable[:4])}</li>")
        parts.append("</ul>")
    if not parts:
        return "<p><em>No dependency concerns detected.</em></p>"
    return "\n".join(parts)


def _html_controls(arch: Architecture) -> str:
    if not arch.controls:
        return "<p><em>No controls defined.</em></p>"
    html = '<table><thead><tr><th>Name</th><th>Type</th><th>Applies To</th></tr></thead><tbody>'
    for c in arch.controls:
        applies = ", ".join(c.applies_to) if c.applies_to else "—"
        html += f"<tr><td>{c.name}</td><td>{c.type}</td><td>{applies}</td></tr>"
    return html + "</tbody></table>"


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_report(arch: Architecture, format: ReportFormat = "md") -> str:
    """Generate a comprehensive review report for an architecture model.

    Runs scoring and full intelligence analysis internally.
    format: "md" (Markdown) or "html" (self-contained HTML page).
    """
    score = score_architecture(arch)
    analysis = analyze_architecture(arch)
    if format == "html":
        return _html_report(arch, score, analysis)
    return _md_report(arch, score, analysis)
