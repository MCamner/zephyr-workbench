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
