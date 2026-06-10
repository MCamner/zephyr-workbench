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
from zephyr.impact import analyze_impact, ChangeImpactReport
from zephyr.history import analyze_history
from zephyr.memory import (
    MemoryError as ArchMemoryError,
    add_to_memory,
    compare_architectures,
    list_memory,
    remove_from_memory,
    search_memory,
)
from zephyr.governance import (
    GovernancePolicyError,
    check_governance,
    load_governance_policy,
)
from zephyr.review_templates import list_review_templates, review_with_template
from zephyr.snapshots import (
    SnapshotError,
    delete_snapshot,
    list_snapshots,
    load_snapshot_architecture,
    save_snapshot,
)
from zephyr.lifecycle import analyze_lifecycle
from zephyr.reporter import ReportFormat, generate_report
from zephyr.scoring import score_architecture
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
    path_obj = Path(path)
    if path_obj.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif"}:
        from zephyr.image_import import parse_image

        image_format = None if format in (None, "auto") else format
        try:
            result = parse_image(path_obj, image_format)
        except Exception as exc:
            return ZephyrResult(
                status="error",
                command="import",
                source=p,
                errors=[str(exc)],
            )
    else:
        try:
            text = path_obj.read_text(encoding="utf-8")
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


def lifecycle_model(path: str | Path) -> ZephyrResult:
    """Analyse component lifecycle states across an architecture model.

    Read-only. Returns distribution, deprecated_in_use, planned_unconnected,
    no_lifecycle, health ("healthy" | "warning" | "critical"), and summary.
    status="warning" when health is not "healthy".
    """
    p = str(path)
    try:
        _, arch, _ = _load(p)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="lifecycle",
            source=p,
            errors=exc.errors,
        )
    report = analyze_lifecycle(arch)
    return ZephyrResult(
        status="warning" if report.health != "healthy" else "ok",
        command="lifecycle",
        source=p,
        data=report.to_dict(),
    )


def report_model(
    path: str | Path,
    format: ReportFormat = "md",
    output: str | Path | None = None,
) -> ZephyrResult:
    """Generate a comprehensive architecture review report.

    Read-only when output is None (report content in artifact).
    Write-creating when output is a path (writes exactly one file).
    Supported formats: "md" (Markdown), "html".

    data keys: format, name
    artifacts[0]: type='report', format=<fmt>, content=<str> or path=<str>
    """
    p = str(path)
    try:
        _, arch, _ = _load(p)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="report",
            source=p,
            errors=exc.errors,
        )
    if format not in ("md", "html"):
        return ZephyrResult(
            status="error",
            command="report",
            source=p,
            errors=[f"unsupported format '{format}'; expected md or html"],
        )
    content = generate_report(arch, format=format)
    if output is not None:
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        artifact: dict = {"type": "report", "format": format, "path": str(out)}
    else:
        artifact = {"type": "report", "format": format, "content": content}
    return ZephyrResult(
        status="ok",
        command="report",
        source=p,
        data={"format": format, "name": arch.name},
        artifacts=[artifact],
    )


def score_model(path: str | Path) -> ZephyrResult:
    """Compute a multi-dimensional quality score for an architecture model.

    Read-only. Returns overall score (0–100), grade (A–F), and per-dimension
    breakdown: risk_health, control_coverage, component_maturity,
    structural_health, definition_completeness.
    """
    p = str(path)
    try:
        _, arch, _ = _load(p)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="score",
            source=p,
            errors=exc.errors,
        )
    score = score_architecture(arch)
    return ZephyrResult(
        status="ok",
        command="score",
        source=p,
        data=score.to_dict(),
    )


def history_model(path: str | Path) -> ZephyrResult:
    """Build a scored snapshot timeline and evolution trend for an architecture.

    Read-only. Loads all snapshots, scores each, diffs consecutive pairs,
    and computes the overall evolution direction.
    data keys: path, arch_name, entries, trend, summary.
    """
    p = str(path)
    report = analyze_history(p)
    return ZephyrResult(
        status="ok",
        command="history",
        source=p,
        data=report.to_dict(),
    )


def memory_add(path: str | Path) -> ZephyrResult:
    """Index an architecture YAML into the semantic memory store.

    Write-creating: updates .zephyr/memory/index.json in cwd.
    status="error" if the file cannot be loaded.
    data keys: path, name, component_count, score, grade, component_types, keywords.
    """
    p = str(path)
    try:
        model = add_to_memory(path)
    except ArchMemoryError as exc:
        return ZephyrResult(status="error", command="memory-add", source=p,
                            errors=[str(exc)])
    return ZephyrResult(status="ok", command="memory-add", source=p,
                        data=model.to_dict())


def memory_remove(path: str | Path) -> ZephyrResult:
    """Remove an architecture from the memory index.

    status="error" if the path is not indexed.
    """
    p = str(path)
    try:
        remove_from_memory(path)
    except ArchMemoryError as exc:
        return ZephyrResult(status="error", command="memory-remove", source=p,
                            errors=[str(exc)])
    return ZephyrResult(status="ok", command="memory-remove", source=p,
                        data={"removed": p})


def memory_list() -> ZephyrResult:
    """List all indexed architectures in the memory store.

    Read-only. Always returns status "ok".
    data keys: models (list of indexed model dicts).
    """
    models = list_memory()
    return ZephyrResult(
        status="ok",
        command="memory-list",
        source="",
        data={"models": [m.to_dict() for m in models]},
    )


def memory_search(query: str, top_k: int = 10) -> ZephyrResult:
    """Semantic keyword search across all indexed architectures.

    Read-only. Returns results sorted by descending similarity.
    data keys: query, results (list of {model, similarity, matched_terms}).
    """
    results = search_memory(query, top_k=top_k)
    return ZephyrResult(
        status="ok",
        command="memory-search",
        source="",
        data={"query": query, "results": [r.to_dict() for r in results]},
    )


def memory_compare(
    path_a: str | Path,
    path_b: str | Path,
) -> ZephyrResult:
    """Cross-project structural comparison between two architecture models.

    Read-only. Returns shared/unique component types, Jaccard similarity,
    architectural pattern comparison, and shared risk themes.
    """
    a, b = str(path_a), str(path_b)
    try:
        _, arch_a, _ = _load(a)
    except ValidationError as exc:
        return ZephyrResult(status="error", command="memory-compare", source=a,
                            errors=[f"model A invalid: {e}" for e in exc.errors])
    try:
        _, arch_b, _ = _load(b)
    except ValidationError as exc:
        return ZephyrResult(status="error", command="memory-compare", source=a,
                            errors=[f"model B invalid: {e}" for e in exc.errors])
    result = compare_architectures(arch_a, arch_b, name_a=a, name_b=b)
    return ZephyrResult(
        status="ok",
        command="memory-compare",
        source=a,
        data=result.to_dict(),
    )


def govern_model(
    path: str | Path,
    policy_path: str | Path,
) -> ZephyrResult:
    """Validate an architecture model against a governance policy file.

    Read-only. Loads the policy YAML and evaluates all rules against the model.
    status="error" when any error-severity rule is violated.
    status="warning" when only warning-severity rules are violated.
    status="ok" when all rules pass.
    data keys: policy_name, policy_version, status, violations,
               passed_rule_ids, counts.
    """
    p = str(path)
    pp = str(policy_path)
    try:
        policy = load_governance_policy(pp)
    except GovernancePolicyError as exc:
        return ZephyrResult(
            status="error",
            command="govern",
            source=p,
            errors=[f"Policy load error: {exc}"],
        )
    try:
        _, arch, _ = _load(p)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="govern",
            source=p,
            errors=exc.errors,
        )
    result = check_governance(arch, policy)
    if result.has_errors:
        status = "error"
    elif result.violations:
        status = "warning"
    else:
        status = "ok"
    return ZephyrResult(
        status=status,
        command="govern",
        source=p,
        data=result.to_dict(),
    )


def review_template_model(path: str | Path, template_name: str) -> ZephyrResult:
    """Run a focused template review on an architecture model.

    Read-only. Available templates: security, zero-trust, resilience, compliance.
    status="warning" when risk-level findings exist.
    data keys: template, description, summary, template_findings, generic_findings,
               all_findings, checklist, counts.
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
    try:
        result = review_with_template(arch, template_name)
    except ValueError as exc:
        return ZephyrResult(
            status="error",
            command="review",
            source=p,
            errors=[str(exc)],
        )
    return ZephyrResult(
        status="warning" if any(f.severity == "risk" for f in result.all_findings) else "ok",
        command="review",
        source=p,
        data=result.to_dict(),
    )


def list_templates_model() -> ZephyrResult:
    """Return the list of available review templates.

    Read-only. Always returns status "ok".
    data keys: templates (list of {name, description, focus_areas, checklist}).
    """
    templates = list_review_templates()
    return ZephyrResult(
        status="ok",
        command="review-templates",
        source="",
        data={
            "templates": [
                {
                    "name": t.name,
                    "description": t.description,
                    "focus_areas": t.focus_areas,
                    "checklist": t.checklist,
                }
                for t in templates
            ]
        },
    )


def impact_models(
    path_before: str | Path,
    path_after: str | Path,
) -> ZephyrResult:
    """Analyse the blast radius and security implications of architecture changes.

    Read-only. Compares two models and returns a ChangeImpactReport describing
    affected components, control coverage gaps, and potentially unmitigated risks.
    status="warning" when severity is critical or high.
    data keys: source, target, severity, summary, component_impacts,
               control_changes, unmitigated_risk_ids, recommendations.
    """
    a, b = str(path_before), str(path_after)
    try:
        _, arch_a, _ = _load(a)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="impact",
            source=a,
            errors=[f"before model invalid: {e}" for e in exc.errors],
        )
    try:
        _, arch_b, _ = _load(b)
    except ValidationError as exc:
        return ZephyrResult(
            status="error",
            command="impact",
            source=a,
            errors=[f"after model invalid: {e}" for e in exc.errors],
        )
    diff = diff_architectures(arch_a, arch_b, source=a, target=b)
    report = analyze_impact(arch_a, arch_b, diff)
    return ZephyrResult(
        status="warning" if report.severity in ("critical", "high") else "ok",
        command="impact",
        source=a,
        data=report.to_dict(),
    )


def snapshot_save(
    path: str | Path,
    tag: str,
    description: str = "",
) -> ZephyrResult:
    """Save a named snapshot of the current architecture YAML state.

    Write-creating: copies the file to .zephyr/snapshots/<stem>/<tag>.yaml.
    status="error" if the tag already exists, is invalid, or the file is missing.
    data keys: tag, created_at, description.
    """
    p = str(path)
    try:
        meta = save_snapshot(path, tag, description=description)
    except SnapshotError as exc:
        return ZephyrResult(
            status="error",
            command="snapshot-save",
            source=p,
            errors=[str(exc)],
        )
    return ZephyrResult(
        status="ok",
        command="snapshot-save",
        source=p,
        data=meta.to_dict(),
    )


def snapshot_list(path: str | Path) -> ZephyrResult:
    """List all named snapshots for an architecture file.

    Read-only. Always returns status "ok".
    data keys: snapshots (list of {tag, created_at, description}).
    """
    p = str(path)
    snaps = list_snapshots(path)
    return ZephyrResult(
        status="ok",
        command="snapshot-list",
        source=p,
        data={"snapshots": [s.to_dict() for s in snaps]},
    )


def snapshot_delete(path: str | Path, tag: str) -> ZephyrResult:
    """Delete a named snapshot.

    status="error" if the snapshot does not exist.
    """
    p = str(path)
    try:
        delete_snapshot(path, tag)
    except SnapshotError as exc:
        return ZephyrResult(
            status="error",
            command="snapshot-delete",
            source=p,
            errors=[str(exc)],
        )
    return ZephyrResult(
        status="ok",
        command="snapshot-delete",
        source=p,
        data={"tag": tag},
    )


def snapshot_diff(path: str | Path, tag_a: str, tag_b: str) -> ZephyrResult:
    """Diff two named snapshots of an architecture file.

    Read-only. Returns status "warning" when changes exist, "ok" when identical.
    status="error" if either snapshot is missing.
    """
    p = str(path)
    try:
        arch_a = load_snapshot_architecture(path, tag_a)
        arch_b = load_snapshot_architecture(path, tag_b)
    except SnapshotError as exc:
        return ZephyrResult(
            status="error",
            command="snapshot-diff",
            source=p,
            errors=[str(exc)],
        )
    diff = diff_architectures(
        arch_a, arch_b,
        source=f"{p}@{tag_a}",
        target=f"{p}@{tag_b}",
    )
    return ZephyrResult(
        status="warning" if not diff.is_empty() else "ok",
        command="snapshot-diff",
        source=p,
        data=_diff_to_dict(diff),
    )


def snapshot_impact(path: str | Path, tag_a: str, tag_b: str) -> ZephyrResult:
    """Change impact analysis between two named snapshots.

    Read-only. Returns status "warning" when severity is critical or high.
    status="error" if either snapshot is missing.
    data keys: source, target, severity, summary, component_impacts,
               control_changes, unmitigated_risk_ids, recommendations.
    """
    p = str(path)
    try:
        arch_a = load_snapshot_architecture(path, tag_a)
        arch_b = load_snapshot_architecture(path, tag_b)
    except SnapshotError as exc:
        return ZephyrResult(
            status="error",
            command="snapshot-impact",
            source=p,
            errors=[str(exc)],
        )
    diff = diff_architectures(
        arch_a, arch_b,
        source=f"{p}@{tag_a}",
        target=f"{p}@{tag_b}",
    )
    report = analyze_impact(arch_a, arch_b, diff)
    return ZephyrResult(
        status="warning" if report.severity in ("critical", "high") else "ok",
        command="snapshot-impact",
        source=p,
        data=report.to_dict(),
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
