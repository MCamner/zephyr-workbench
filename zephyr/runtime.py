"""Zephyr Python runtime API.

Thin stable layer over the Zephyr engine modules. Returns ZephyrResult for every
operation — callers (mq-mcp, agents, scripts) never need to parse CLI text.

All read-only functions are safe to call freely. Write-creating functions
(diagram_model with output path) write exactly one file and nothing else.

Call pattern for agents:
    result = validate_model(path)
    if result.failed:
        return result  # surface errors, do not proceed
    summary = summary_model(path)
    diagram = diagram_model(path)
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from zephyr.analyzer import summarize_architecture_data
from zephyr.diff import ArchitectureDiff, Change, diff_architectures
from zephyr.diagram import to_html, to_mermaid
from zephyr.intelligence import (
    ArchitectureAnalysis,
    RiskContext,
    analyze_architecture,
    explain_risk,
    review_architecture,
)
from zephyr.loader import ValidationError, architecture_from_data, load_architecture_data
from zephyr.result import ZephyrResult
from zephyr.search import search_architecture_data
from zephyr.validation import collect_validation_warnings, validate_architecture_data


# ── helpers ─────────────────────────────────────────────────────────────────

def _load(path: str | Path):
    """Load, validate, and return (data, architecture, warnings). Raises ValidationError."""
    p = str(path)
    data = load_architecture_data(p)
    validate_architecture_data(data)
    arch = architecture_from_data(data)
    warnings = collect_validation_warnings(data)
    return data, arch, warnings


def _validation_data(arch, warnings: list[str]) -> dict:
    return {
        "name": arch.name,
        "summary": summarize_architecture_data(arch),
        "valid": True,
    }


def _change_to_dict(change: Change) -> dict:
    return {
        "status": change.status,
        "label": change.label,
        "fields": [{"field": f, "old": old, "new": new} for f, old, new in change.fields],
    }


def _diff_to_dict(diff: ArchitectureDiff) -> dict:
    return {
        "source": diff.source,
        "target": diff.target,
        "changed": not diff.is_empty(),
        "meta": _change_to_dict(diff.meta) if diff.meta else None,
        "components": [_change_to_dict(c) for c in diff.components],
        "flows": [_change_to_dict(f) for f in diff.flows],
        "risks": [_change_to_dict(r) for r in diff.risks],
        "controls": [_change_to_dict(c) for c in diff.controls],
        "stakeholders": [_change_to_dict(s) for s in diff.stakeholders],
    }


# ── public API ───────────────────────────────────────────────────────────────

def validate_model(path: str | Path) -> ZephyrResult:
    """Validate an architecture YAML file.

    Read-only. Safe to call without side effects.
    Returns status "error" if the model is structurally invalid.
    Returns status "warning" if valid but warnings exist.
    """
    p = str(path)
    try:
        data, arch, warnings = _load(p)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="validate",
            source=p,
            errors=exc.errors,
            data={"valid": False},
        )
    return ZephyrResult(
        status="warning" if warnings else "ok",
        command="validate",
        source=p,
        warnings=warnings,
        data=_validation_data(arch, warnings),
    )


def summary_model(path: str | Path) -> ZephyrResult:
    """Return a structured summary of an architecture model.

    Read-only. Does not surface validation warnings — call validate_model
    first if warning state matters.
    """
    p = str(path)
    try:
        _, arch, _ = _load(p)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="summary",
            source=p,
            errors=exc.errors,
        )
    return ZephyrResult(
        status="ok",
        command="summary",
        source=p,
        data=summarize_architecture_data(arch),
    )


def diagram_model(
    path: str | Path,
    format: str = "mermaid",
    output: str | Path | None = None,
) -> ZephyrResult:
    """Render a diagram for an architecture model.

    Read-only when output is None (diagram content in artifact).
    Write-creating when output is a path (writes exactly one file).
    Supported formats: "mermaid", "html".
    """
    p = str(path)
    try:
        _, arch, _ = _load(p)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="diagram",
            source=p,
            errors=exc.errors,
        )

    if format == "mermaid":
        content = to_mermaid(arch)
    elif format == "html":
        content = to_html(arch)
    else:
        return ZephyrResult(
            status="error",
            command="diagram",
            source=p,
            errors=[f"unsupported format '{format}'; expected mermaid or html"],
        )

    if output is not None:
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        artifact: dict = {"type": "diagram", "format": format, "path": str(out)}
    else:
        artifact = {"type": "diagram", "format": format, "content": content}

    return ZephyrResult(
        status="ok",
        command="diagram",
        source=p,
        artifacts=[artifact],
    )


def diff_models(
    path_a: str | Path,
    path_b: str | Path,
) -> ZephyrResult:
    """Compare two architecture YAML files.

    Read-only. Returns status "warning" when changes exist, "ok" when identical.
    Check data["changed"] for boolean control flow.
    """
    a, b = str(path_a), str(path_b)
    try:
        _, arch_a, _ = _load(a)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="diff",
            source=a,
            errors=[f"source model invalid: {e}" for e in exc.errors],
        )
    try:
        _, arch_b, _ = _load(b)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="diff",
            source=a,
            errors=[f"target model invalid: {e}" for e in exc.errors],
        )

    diff = diff_architectures(arch_a, arch_b, source=a, target=b)
    return ZephyrResult(
        status="warning" if not diff.is_empty() else "ok",
        command="diff",
        source=a,
        data=_diff_to_dict(diff),
    )


def analyze_model(path: str | Path) -> ZephyrResult:
    """Run full architecture intelligence analysis.

    Read-only. Returns anti-patterns, suggestions, risk analysis,
    dependency insights, and a narrative summary.
    status="warning" when blocking risk-level findings exist.
    """
    p = str(path)
    try:
        _, arch, _ = _load(p)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="analyze",
            source=p,
            errors=exc.errors,
        )
    analysis = analyze_architecture(arch)
    return ZephyrResult(
        status="warning" if analysis.has_blocking() else "ok",
        command="analyze",
        source=p,
        data={
            "narrative": analysis.narrative,
            "antipatterns": [
                {"severity": f.severity, "code": f.code,
                 "message": f.message, "affected": f.affected}
                for f in analysis.antipatterns
            ],
            "suggestions": [
                {"severity": f.severity, "code": f.code,
                 "message": f.message, "affected": f.affected}
                for f in analysis.suggestions
            ],
            "risk_analysis": analysis.risk_analysis,
            "dependency_insights": {
                "external_reachable": analysis.dependency_insights.external_reachable,
                "hub_components": [
                    {"name": n, "degree": d}
                    for n, d in analysis.dependency_insights.hub_components
                ],
                "isolated_components": analysis.dependency_insights.isolated_components,
            },
        },
    )


def review_model(path: str | Path) -> ZephyrResult:
    """Return all architecture review findings in severity order.

    Read-only. Combines anti-patterns and improvement suggestions.
    status="warning" when risk-level findings exist.
    data["counts"] gives per-severity breakdown.
    """
    p = str(path)
    try:
        _, arch, _ = _load(p)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="review",
            source=p,
            errors=exc.errors,
        )
    findings = review_architecture(arch)
    return ZephyrResult(
        status="warning" if any(f.severity == "risk" for f in findings) else "ok",
        command="review",
        source=p,
        data={
            "findings": [
                {"severity": f.severity, "code": f.code,
                 "message": f.message, "affected": f.affected}
                for f in findings
            ],
            "counts": {
                sev: sum(1 for f in findings if f.severity == sev)
                for sev in ("risk", "warning", "suggestion", "note")
            },
        },
    )


def explain_risk_model(path: str | Path, risk_id: str) -> ZephyrResult:
    """Explain a specific risk in its architectural context.

    Read-only. Returns severity, likelihood, impact, mitigation status,
    affected components, and relevant flows.
    status="error" if the risk_id is not found.
    """
    p = str(path)
    try:
        _, arch, _ = _load(p)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="explain",
            source=p,
            errors=exc.errors,
        )
    ctx = explain_risk(arch, risk_id)
    if ctx is None:
        return ZephyrResult(
            status="error",
            command="explain",
            source=p,
            errors=[f"risk '{risk_id}' not found"],
        )
    return ZephyrResult(
        status="ok",
        command="explain",
        source=p,
        data={
            "risk_id": ctx.risk_id,
            "title": ctx.title,
            "severity": ctx.severity,
            "likelihood": ctx.likelihood,
            "impact": ctx.impact,
            "mitigation": ctx.mitigation,
            "affected_components": ctx.affected_components,
            "affected_flows": ctx.affected_flows,
            "explanation": ctx.explanation,
        },
    )


def import_diagram_model(
    path: str | Path,
    format: str | None = None,
    output: str | Path | None = None,
) -> ZephyrResult:
    """Import a diagram file into a Zephyr YAML data structure.

    Read-only when output is None (YAML content returned in artifact).
    Write-creating when output is a path (writes exactly one file).
    Supported formats: 'mermaid', 'drawio'. Auto-detected from extension when None.

    data keys: format, name, component_count, flow_count, trust_boundary_count
    artifacts[0]: type='yaml', format='zephyr', content=<yaml> or path=<path>
    """
    from zephyr.diagram_import import detect_format, parse_diagram

    p = str(path)
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return ZephyrResult(
            status="error",
            command="import",
            source=p,
            errors=[str(exc)],
        )

    fmt = format or detect_format(path)
    result = parse_diagram(text, fmt)
    yaml_str = result.to_yaml_string()

    if output is not None:
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml_str, encoding="utf-8")
        artifact: dict = {"type": "yaml", "format": "zephyr", "path": str(out)}
    else:
        artifact = {"type": "yaml", "format": "zephyr", "content": yaml_str}

    return ZephyrResult(
        status="warning" if result.warnings else "ok",
        command="import",
        source=p,
        warnings=result.warnings,
        data={
            "format": fmt,
            "name": result.name,
            "component_count": len(result.components),
            "flow_count": len(result.flows),
            "trust_boundary_count": len(result.trust_boundaries),
        },
        artifacts=[artifact],
    )


def search_model(path: str | Path, query: str) -> ZephyrResult:
    """Filter components, flows, risks, controls, and stakeholders by field value.

    Read-only. Query syntax: field=value or missing=field, comma-separated for AND.
    Returns status "ok" always; check data["total"] for match count.
    """
    p = str(path)
    try:
        _, arch, _ = _load(p)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="search",
            source=p,
            errors=exc.errors,
        )
    return ZephyrResult(
        status="ok",
        command="search",
        source=p,
        data=search_architecture_data(arch, query),
    )
