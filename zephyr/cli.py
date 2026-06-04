from __future__ import annotations

import argparse
import json
import sys
import time
import threading
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

from zephyr.add import run_add
from zephyr.lifecycle import analyze_lifecycle, LifecycleReport
from zephyr.reporter import generate_report
from zephyr.scoring import ArchitectureScore, score_architecture
from zephyr.intelligence import (
    analyze_architecture,
    explain_risk,
    format_analysis,
    format_review,
    format_risk_context,
    review_architecture,
)
from zephyr.search import search_architecture, search_architecture_data
from zephyr.analyzer import load_architecture, summarize_architecture, summarize_architecture_data
from zephyr.diagram import to_html, to_mermaid
from zephyr.diff import ArchitectureDiff, Change, diff_architectures, format_diff
from zephyr.history import analyze_history, format_history
from zephyr.impact import ChangeImpactReport, analyze_impact, format_impact
from zephyr.memory import (
    MemoryError as ArchMemoryError,
    add_to_memory,
    compare_architectures,
    format_comparison,
    format_memory_list,
    format_search_results,
    list_memory,
    remove_from_memory,
    search_memory,
)
from zephyr.governance import (
    GovernancePolicyError,
    check_governance,
    format_governance_result,
    load_governance_policy,
)
from zephyr.review_templates import (
    ReviewTemplateResult,
    format_review_template_result,
    format_template_list,
    list_review_templates,
    review_with_template,
)
from zephyr.snapshots import (
    SnapshotError,
    delete_snapshot,
    format_snapshot_list,
    list_snapshots,
    load_snapshot_architecture,
    save_snapshot,
)
from zephyr.reference import build_reference
from zephyr.templates import list_templates
from zephyr.init_wizard import run_init_wizard
from zephyr.validation import ValidationError, load_validation_result


_HELP_TEXT = """\
Zephyr Workbench — model, validate, and visualize architecture.

Describe your infrastructure in YAML. Zephyr validates it, summarizes it,
and generates diagrams. Every model is version-controllable and diffable.

Quick start
  1. zephyr templates                   browse starter models
  2. zephyr init --template <name>      create a model from a template
  3. zephyr run <file>                  validate + summary + diagram

Commands

  run <file>
    Full pipeline in one step: validate, print summary, write diagram.
    • --format mermaid      write a .mmd file (default)
    • --format html         write an .html file — open directly in browser
    • --output-dir <dir>    where to write the diagram [default: output/]

  validate <file>
    Check a model for errors and warnings.
    • Errors block the pipeline (missing fields, invalid values, bad references)
    • Warnings flag risky patterns (single gateway, endpoint-to-endpoint flows)

  summary <file>
    Print a structured summary: components, flows, risks, controls, stakeholders.
    • --json    output as machine-readable JSON

  diagram <file> --format <fmt>
    Generate a diagram without running the full pipeline.
    • --format mermaid      Mermaid graph syntax
    • --format html         self-contained HTML page
    • --output <path>       write to file instead of stdout

  diff <file-a> <file-b>
    Compare two models and show what changed.
    • + added   - removed   ~ modified (with old → new values per field)
    • Exits 1 when changes exist, 0 when identical — use in CI pipelines

  impact <before> <after>
    Analyse the blast radius and security implications of architecture changes.
    Shows affected upstream/downstream components, lost control coverage, and
    potentially unmitigated risks.
    • Exits 1 when severity is critical or high — use as a CI gate
    • --json    output as machine-readable JSON envelope

  govern <policy> <file> [--json]
    Validate an architecture against a governance policy YAML file.
    Policy rules: require_field, require_component_type, require_meta_field,
    require_meta, require_trust_boundaries, prohibit_external_bypass,
    require_control_coverage.
    • Exits 1 when any error-severity rule is violated — use as a CI gate
    • --json    output as machine-readable JSON envelope

  snapshot save <tag> <file> [--description <text>]
    Save a named snapshot of the current model state.

  snapshot list <file> [--json]
    List all snapshots for a model.

  snapshot diff <tag-a> <tag-b> <file> [--json]
    Diff two named snapshots.

  snapshot impact <tag-a> <tag-b> <file> [--json]
    Change impact analysis between two named snapshots.

  snapshot delete <tag> <file>
    Delete a named snapshot.

  history <file> [--json]
    Show a scored timeline across all snapshots: per-snapshot architecture
    score, grade, change count, and impact severity. Tracks overall evolution
    trend (improving / degrading / stable).

  memory add <file>
    Index an architecture file into the semantic memory store.
    Re-running updates the existing entry.

  memory remove <file>
    Remove an architecture from the memory index.

  memory list [--json]
    List all indexed architectures with component and risk counts.

  memory search <query> [--json]
    Semantic keyword search across all indexed architectures.

  memory compare <file-a> <file-b> [--json]
    Cross-project structural comparison: shared types, unique patterns,
    Jaccard similarity, and shared risk themes.

  init
    Create a new model interactively (guided wizard).
    • --template <name>     start from a template, skip the wizard
    • --minimal             skip optional fields for a faster flow
    • --no-validate         skip validation after writing

  templates
    List available starter templates with descriptions.

  import <file>
    Import a diagram file (Mermaid or draw.io) and generate a Zephyr YAML model.
    • --format auto|mermaid|drawio   format (default: auto-detect from extension)
    • --output <path>                write YAML to file instead of stdout
    • --validate                     validate the generated model after import
    • --json                         output as machine-readable JSON envelope

  search <file> <query>
    Filter components, flows, risks, controls, and stakeholders by field value.
    • type=endpoint           match a specific field value
    • missing=mitigation      items where the field is empty
    • no:mitigation           alias for missing=
    • has:description         items where the field is non-empty
    • severity=high,missing=mitigation   comma-separate to AND multiple filters

  analyze <file>
    Full intelligence analysis: narrative, anti-patterns, suggestions, dependency
    insights, and risk distribution.
    • --json    output as machine-readable JSON envelope

  review <file> [--template <name>]
    Architecture review: all findings (anti-patterns + suggestions) in severity order.
    • --template security|zero-trust|resilience|compliance   focused template review
    • --json    output as machine-readable JSON envelope

  review-templates
    List all available review templates with descriptions.

  score <file>
    Multi-dimensional quality score: risk health, control coverage, component
    maturity, structural health, and definition completeness.
    • --json    output as machine-readable JSON envelope

  lifecycle <file>
    Analyse component lifecycle states: distribution, deprecated components
    still referenced in active flows, planned components not yet connected,
    and components missing a lifecycle field.
    • --json    output as machine-readable JSON envelope

  report <file>
    Generate a comprehensive architecture review report combining score,
    narrative, risk table, findings, dependency insights, and controls.
    • --format md       Markdown output (default)
    • --format html     self-contained HTML page
    • --output <path>   write to file instead of stdout
    • --json            output as machine-readable JSON envelope

  explain <file> <risk-id>
    Explain a specific risk in architectural context: affected components, flows,
    mitigation status.
    • --json    output as machine-readable JSON envelope

  reference
    Show all valid values for every enum field (type, criticality, auth...).

  help
    Show this message.

Model structure
  Every model is a YAML file. Required fields:
  • name          identifier for this architecture
  • components    systems, endpoints, identities, and controls
  • flows         directed connections between components

  Optional but recommended:
  • risks         weaknesses with severity, likelihood, impact, mitigation
  • controls      technical, policy, or process measures with applies_to
  • stakeholders  people or teams and their roles
  • meta          owner, environment, criticality, version

Tips
  • Not sure what value to use? Run: zephyr reference
  • Want a head start?        Run: zephyr templates
  • Automate change detection:     zephyr diff v1.yaml v2.yaml (CI-friendly)
  • Fast HTML diagram:             zephyr run <file> --format html
"""


def print_help() -> None:
    print(_HELP_TEXT)


def _print_validation_error(error: ValidationError) -> None:
    print("Validation failed:", file=sys.stderr)
    for message in error.errors:
        print(f"- {message}", file=sys.stderr)


def _print_warnings(warnings: list[str]) -> None:
    if not warnings:
        return

    print("Warnings:")
    for index, warning in enumerate(warnings, start=1):
        print(f"- W{index}: {warning}")
    print("")


def _result_envelope(
    *,
    command: str,
    source: str | None,
    status: str,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    data: dict | None = None,
    artifacts: list[dict] | None = None,
) -> dict:
    return {
        "status": status,
        "errors": errors or [],
        "warnings": warnings or [],
        "data": data or {},
        "artifacts": artifacts or [],
        "metadata": {
            "command": command,
            "source": source,
            "schema_version": "zephyr-result.v1",
        },
    }


def _validation_data(result) -> dict:
    summary = summarize_architecture_data(result.architecture)
    return {
        "name": result.architecture.name,
        "summary": summary,
        "valid": True,
    }


def _print_json_result(payload: dict) -> None:
    print(json.dumps(payload, indent=2))


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zephyr")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate", help="Validate an architecture YAML file")
    validate_parser.add_argument("file")
    validate_parser.add_argument(
        "--json",
        action="store_true",
        help="Output validation result as a stable JSON envelope",
    )

    summary_parser = subparsers.add_parser("summary", help="Show a text summary for an architecture")
    summary_parser.add_argument("file")
    summary_parser.add_argument(
        "--json",
        action="store_true",
        help="Output the summary as JSON",
    )

    diagram_parser = subparsers.add_parser("diagram", help="Render a diagram from an architecture")
    diagram_parser.add_argument("file")
    diagram_parser.add_argument("--format", choices=["mermaid", "html", "png"], required=True)
    diagram_parser.add_argument("--output", help="Write diagram output to a file instead of stdout")
    diagram_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as a stable JSON envelope",
    )

    add_parser = subparsers.add_parser("add", help="Add items to an existing architecture model")
    add_parser.add_argument("file")

    search_parser = subparsers.add_parser("search", help="Filter components, flows, risks by field value")
    search_parser.add_argument("file")
    search_parser.add_argument(
        "query",
        help="Filter expression: type=endpoint, severity=high,missing=mitigation (comma-separated for AND)",
    )
    search_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as a stable JSON envelope",
    )

    analyze_parser = subparsers.add_parser(
        "analyze", help="Full intelligence analysis: anti-patterns, risks, dependencies"
    )
    analyze_parser.add_argument("file")
    analyze_parser.add_argument(
        "--json", action="store_true", help="Output result as a stable JSON envelope"
    )

    review_parser = subparsers.add_parser(
        "review", help="Architecture review: all findings in severity order"
    )
    review_parser.add_argument("file")
    review_parser.add_argument(
        "--template",
        choices=["security", "zero-trust", "resilience", "compliance"],
        default=None,
        help="Run a focused template review instead of the generic review",
    )
    review_parser.add_argument(
        "--json", action="store_true", help="Output result as a stable JSON envelope"
    )

    subparsers.add_parser(
        "review-templates", help="List available focused review templates"
    )

    score_parser = subparsers.add_parser(
        "score", help="Multi-dimensional quality score for an architecture model"
    )
    score_parser.add_argument("file")
    score_parser.add_argument(
        "--json", action="store_true", help="Output result as a stable JSON envelope"
    )

    lifecycle_parser = subparsers.add_parser(
        "lifecycle", help="Analyse component lifecycle states and health"
    )
    lifecycle_parser.add_argument("file")
    lifecycle_parser.add_argument(
        "--json", action="store_true", help="Output result as a stable JSON envelope"
    )

    report_parser = subparsers.add_parser(
        "report", help="Generate a comprehensive architecture review report"
    )
    report_parser.add_argument("file")
    report_parser.add_argument(
        "--format", choices=["md", "html"], default="md",
        help="Report format: md (Markdown, default) or html",
    )
    report_parser.add_argument("--output", help="Write report to file instead of stdout")
    report_parser.add_argument(
        "--json", action="store_true", help="Output result as a stable JSON envelope"
    )

    explain_parser = subparsers.add_parser(
        "explain", help="Explain a specific risk in architectural context"
    )
    explain_parser.add_argument("file")
    explain_parser.add_argument("risk_id", metavar="RISK_ID")
    explain_parser.add_argument(
        "--json", action="store_true", help="Output result as a stable JSON envelope"
    )

    subparsers.add_parser("reference", help="Show all valid field values")
    subparsers.add_parser("templates", help="List available starter templates")
    subparsers.add_parser("help", help="Show detailed usage guide")

    diff_parser = subparsers.add_parser("diff", help="Compare two architecture YAML files")
    diff_parser.add_argument("file_a", metavar="FILE_A")
    diff_parser.add_argument("file_b", metavar="FILE_B")
    diff_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as a stable JSON envelope",
    )

    impact_parser = subparsers.add_parser(
        "impact", help="Analyse blast radius and security implications of architecture changes"
    )
    impact_parser.add_argument("before", metavar="BEFORE")
    impact_parser.add_argument("after", metavar="AFTER")
    impact_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as a stable JSON envelope",
    )

    govern_parser = subparsers.add_parser(
        "govern", help="Validate an architecture against a governance policy"
    )
    govern_parser.add_argument("policy", metavar="POLICY", help="Governance policy YAML file")
    govern_parser.add_argument("file", metavar="FILE", help="Architecture YAML file")
    govern_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as a stable JSON envelope",
    )

    history_parser = subparsers.add_parser(
        "history", help="Show scored snapshot timeline and evolution trend"
    )
    history_parser.add_argument("file", metavar="FILE")
    history_parser.add_argument("--json", action="store_true",
                                help="Output result as a stable JSON envelope")

    memory_parser = subparsers.add_parser(
        "memory", help="Manage the multi-model semantic architecture memory"
    )
    mem_sub = memory_parser.add_subparsers(dest="mem_action")

    mem_add = mem_sub.add_parser("add", help="Index an architecture file")
    mem_add.add_argument("file", metavar="FILE")

    mem_remove = mem_sub.add_parser("remove", help="Remove an architecture from the index")
    mem_remove.add_argument("file", metavar="FILE")

    mem_list = mem_sub.add_parser("list", help="List all indexed architectures")
    mem_list.add_argument("--json", action="store_true", help="Output as JSON envelope")

    mem_search = mem_sub.add_parser("search", help="Semantic search across indexed models")
    mem_search.add_argument("query", metavar="QUERY")
    mem_search.add_argument("--json", action="store_true", help="Output as JSON envelope")

    mem_compare = mem_sub.add_parser("compare", help="Cross-project structural comparison")
    mem_compare.add_argument("file_a", metavar="FILE_A")
    mem_compare.add_argument("file_b", metavar="FILE_B")
    mem_compare.add_argument("--json", action="store_true", help="Output as JSON envelope")

    snapshot_parser = subparsers.add_parser(
        "snapshot", help="Manage named architecture snapshots"
    )
    snap_sub = snapshot_parser.add_subparsers(dest="snap_action")

    snap_save = snap_sub.add_parser("save", help="Save a named snapshot of the current model")
    snap_save.add_argument("tag", metavar="TAG")
    snap_save.add_argument("file", metavar="FILE")
    snap_save.add_argument("--description", default="", help="Optional description")

    snap_list = snap_sub.add_parser("list", help="List all snapshots for a model")
    snap_list.add_argument("file", metavar="FILE")
    snap_list.add_argument("--json", action="store_true", help="Output as JSON envelope")

    snap_diff = snap_sub.add_parser("diff", help="Diff two named snapshots")
    snap_diff.add_argument("tag_a", metavar="TAG_A")
    snap_diff.add_argument("tag_b", metavar="TAG_B")
    snap_diff.add_argument("file", metavar="FILE")
    snap_diff.add_argument("--json", action="store_true", help="Output as JSON envelope")

    snap_impact = snap_sub.add_parser(
        "impact", help="Change impact analysis between two named snapshots"
    )
    snap_impact.add_argument("tag_a", metavar="TAG_A")
    snap_impact.add_argument("tag_b", metavar="TAG_B")
    snap_impact.add_argument("file", metavar="FILE")
    snap_impact.add_argument("--json", action="store_true", help="Output as JSON envelope")

    snap_delete = snap_sub.add_parser("delete", help="Delete a named snapshot")
    snap_delete.add_argument("tag", metavar="TAG")
    snap_delete.add_argument("file", metavar="FILE")

    import_parser = subparsers.add_parser(
        "import", help="Import a diagram into a Zephyr architecture YAML"
    )
    import_parser.add_argument(
        "file",
        help=(
            "Diagram or image file to import "
            "(.mmd for Mermaid, .xml/.drawio for draw.io, .png/.jpg/.jpeg/.bmp/.gif for OCR image import)"
        ),
    )
    import_parser.add_argument(
        "--format",
        choices=["auto", "mermaid", "drawio"],
        default="auto",
        help="Diagram format for OCR image imports, or auto-detect from file extension/text.",
    )
    import_parser.add_argument(
        "--output",
        help="Write resulting YAML to this path instead of stdout",
    )
    import_parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the generated YAML after import",
    )
    import_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as a stable JSON envelope",
    )

    init_parser = subparsers.add_parser("init", help="Create a new architecture YAML file")
    init_parser.add_argument("--output", help="Output YAML path")
    init_parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip validation after generation",
    )
    init_parser.add_argument(
        "--minimal",
        action="store_true",
        help="Use the fastest V1 wizard path with minimal prompts",
    )
    init_parser.add_argument("--template", help="Optional starter template name")

    run_parser = subparsers.add_parser(
        "run", help="Validate an architecture, print a summary, and generate a diagram"
    )
    run_parser.add_argument("file")
    run_parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for generated artifacts",
    )
    run_parser.add_argument(
        "--format",
        choices=["mermaid", "html"],
        default="mermaid",
        help="Diagram format to generate",
    )
    run_parser.add_argument(
        "--open",
        action="store_true",
        help="Open the diagram after generating",
    )
    run_parser.add_argument(
        "--watch",
        action="store_true",
        help="Regenerate whenever the file changes",
    )

    return parser


def _render_diagram(architecture, format_name: str, livereload: bool = False) -> str:
    if format_name == "html":
        return to_html(architecture, livereload=livereload)
    return to_mermaid(architecture)


def _open_in_browser(path: Path) -> None:
    webbrowser.open(path.resolve().as_uri())


def _start_http_server(directory: Path) -> int:
    """Start a local HTTP server in a background thread. Returns the port."""
    import socket
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()

    class _Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)
        def log_message(self, *args):
            pass  # suppress server logs

    server = HTTPServer(("", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return port


def _run_pipeline(args, livereload: bool = False) -> Path:
    """Run validate + summary + diagram. Returns the diagram path."""
    result = load_validation_result(args.file)
    architecture = result.architecture
    diagram_path = _default_diagram_path(args.file, args.output_dir, args.format)
    diagram = _render_diagram(architecture, args.format, livereload=livereload)
    _write_text_output(diagram, str(diagram_path))
    if result.warnings:
        print("Validation passed with warnings")
    else:
        print("Validation passed")
    _print_warnings(result.warnings)
    print("")
    print(summarize_architecture(architecture))
    print("")
    print(f"Diagram generated: {diagram_path}")
    return diagram_path


def _write_text_output(contents: str, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def _default_diagram_path(source_file: str, output_dir: str, format_name: str) -> Path:
    suffix = ".mmd" if format_name == "mermaid" else f".{format_name}"
    return Path(output_dir) / f"{Path(source_file).stem}{suffix}"


def _export_png(architecture, output_path: Path) -> None:
    import subprocess
    import shutil
    import tempfile

    if not shutil.which("mmdc"):
        print(
            "PNG export requires mermaid-cli (mmdc).\n"
            "Install it with:  npm install -g @mermaid-js/mermaid-cli",
            file=sys.stderr,
        )
        raise SystemExit(1)

    with tempfile.NamedTemporaryFile(suffix=".mmd", mode="w", delete=False) as tmp:
        tmp.write(to_mermaid(architecture))
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["mmdc", "-i", tmp_path, "-o", str(output_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"mmdc error: {result.stderr}", file=sys.stderr)
            raise SystemExit(1)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args(sys.argv[1:])

    if not args.command or args.command == "help":
        print_help()
        raise SystemExit(0)

    try:
        if args.command == "validate":
            try:
                result = load_validation_result(args.file)
            except ValidationError as error:
                if args.json:
                    _print_json_result(
                        _result_envelope(
                            command="validate",
                            source=args.file,
                            status="error",
                            errors=error.errors,
                            data={"valid": False},
                        )
                    )
                    raise SystemExit(1) from error
                raise

            if args.json:
                _print_json_result(
                    _result_envelope(
                        command="validate",
                        source=args.file,
                        status="warning" if result.warnings else "ok",
                        warnings=result.warnings,
                        data=_validation_data(result),
                    )
                )
                return

            if result.warnings:
                print(f"Validation passed with warnings: {result.architecture.name}")
            else:
                print(f"Validation passed: {result.architecture.name}")
            _print_warnings(result.warnings)
            return

        if args.command == "summary":
            architecture = load_architecture(args.file)
            if args.json:
                _print_json_result(
                    _result_envelope(
                        command="summary",
                        source=args.file,
                        status="ok",
                        data=summarize_architecture_data(architecture),
                    )
                )
            else:
                print(summarize_architecture(architecture))
            return

        if args.command == "diagram":
            architecture = load_architecture(args.file)
            if args.format == "png":
                output = args.output or str(
                    _default_diagram_path(args.file, "output", "png")
                )
                _export_png(architecture, Path(output))
                if args.json:
                    _print_json_result(
                        _result_envelope(
                            command="diagram",
                            source=args.file,
                            status="ok",
                            artifacts=[{"type": "diagram", "format": "png", "path": output}],
                        )
                    )
                else:
                    print(f"Diagram generated: {output}")
            else:
                diagram = _render_diagram(architecture, args.format)
                if args.json:
                    if args.output:
                        _write_text_output(diagram, args.output)
                        diagram_artifact: dict = {"type": "diagram", "format": args.format, "path": args.output}
                    else:
                        diagram_artifact = {"type": "diagram", "format": args.format, "content": diagram}
                    _print_json_result(
                        _result_envelope(
                            command="diagram",
                            source=args.file,
                            status="ok",
                            artifacts=[diagram_artifact],
                        )
                    )
                elif args.output:
                    _write_text_output(diagram, args.output)
                    print(f"Diagram generated: {args.output}")
                else:
                    print(diagram)
            return

        if args.command == "run":
            use_livereload = args.watch and args.format == "html"
            diagram_path = _run_pipeline(args, livereload=use_livereload)

            if args.watch:
                port = None
                if use_livereload:
                    port = _start_http_server(Path(args.output_dir))
                    url = f"http://localhost:{port}/{diagram_path.name}"
                    print(f"Serving at {url}")
                    if args.open:
                        webbrowser.open(url)
                elif args.open:
                    _open_in_browser(diagram_path)

                src = Path(args.file)
                last_mtime = src.stat().st_mtime
                print(f"\nWatching {args.file} for changes. Ctrl+C to stop.")
                try:
                    while True:
                        time.sleep(1)
                        try:
                            mtime = src.stat().st_mtime
                        except FileNotFoundError:
                            continue
                        if mtime != last_mtime:
                            last_mtime = mtime
                            print("\nChange detected — regenerating...")
                            try:
                                _run_pipeline(args, livereload=use_livereload)
                            except ValidationError as err:
                                _print_validation_error(err)
                except KeyboardInterrupt:
                    print("\nStopped.")
            elif args.open:
                _open_in_browser(diagram_path)
            return

        if args.command == "import":
            from zephyr.diagram_import import detect_format, parse_diagram
            from zephyr.image_import import is_image_path, parse_image
            import yaml as _yaml

            src = Path(args.file)
            if not src.exists():
                print(f"File not found: {args.file}", file=sys.stderr)
                raise SystemExit(1)

            fmt = args.format if args.format != "auto" else detect_format(args.file)
            if is_image_path(src):
                image_format = None if args.format == "auto" else fmt
                diagram_result = parse_image(src, image_format)
            else:
                diagram_result = parse_diagram(src.read_text(encoding="utf-8"), fmt)
            yaml_str = diagram_result.to_yaml_string()

            val_errors: list[str] = []
            val_warnings: list[str] = []
            if args.validate:
                from zephyr.validation import validate_architecture_data, collect_validation_warnings
                try:
                    data = _yaml.safe_load(yaml_str)
                    validate_architecture_data(data)
                    val_warnings = collect_validation_warnings(data)
                except ValidationError as ve:
                    val_errors = ve.errors

            all_warnings = diagram_result.warnings + val_warnings
            status = "error" if val_errors else ("warning" if all_warnings else "ok")

            if args.json:
                import_artifact: dict = (
                    {"type": "yaml", "format": "zephyr", "path": args.output}
                    if args.output
                    else {"type": "yaml", "format": "zephyr", "content": yaml_str}
                )
                if args.output:
                    _write_text_output(yaml_str, args.output)
                _print_json_result(
                    _result_envelope(
                        command="import",
                        source=args.file,
                        status=status,
                        errors=val_errors,
                        warnings=all_warnings,
                        data={
                            "format": fmt,
                            "name": diagram_result.name,
                            "component_count": len(diagram_result.components),
                            "flow_count": len(diagram_result.flows),
                            "trust_boundary_count": len(diagram_result.trust_boundaries),
                        },
                        artifacts=[import_artifact],
                    )
                )
            else:
                if args.output:
                    _write_text_output(yaml_str, args.output)
                    print(f"Imported: {diagram_result.name} → {args.output}")
                    print(
                        f"  {len(diagram_result.components)} component(s), "
                        f"{len(diagram_result.flows)} flow(s), "
                        f"{len(diagram_result.trust_boundaries)} trust boundary/ies"
                    )
                    if all_warnings:
                        _print_warnings(all_warnings)
                    if val_errors:
                        print("Validation errors:", file=sys.stderr)
                        for e in val_errors:
                            print(f"  - {e}", file=sys.stderr)
                else:
                    print(yaml_str)
            return

        if args.command == "add":
            raise SystemExit(run_add(args.file))

        if args.command == "search":
            architecture = load_architecture(args.file)
            if args.json:
                _print_json_result(
                    _result_envelope(
                        command="search",
                        source=args.file,
                        status="ok",
                        data=search_architecture_data(architecture, args.query),
                    )
                )
            else:
                print(search_architecture(architecture, args.query))
            return

        if args.command == "analyze":
            architecture = load_architecture(args.file)
            analysis = analyze_architecture(architecture)
            if args.json:
                from dataclasses import asdict
                _print_json_result(
                    _result_envelope(
                        command="analyze",
                        source=args.file,
                        status="warning" if analysis.has_blocking() else "ok",
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
                )
            else:
                print(format_analysis(analysis, architecture.name))
            return

        if args.command == "review":
            architecture = load_architecture(args.file)
            if args.template:
                tmpl_result: ReviewTemplateResult = review_with_template(architecture, args.template)
                if args.json:
                    _print_json_result(
                        _result_envelope(
                            command="review",
                            source=args.file,
                            status="warning" if any(
                                f.severity == "risk" for f in tmpl_result.all_findings
                            ) else "ok",
                            data=tmpl_result.to_dict(),
                        )
                    )
                else:
                    print(format_review_template_result(tmpl_result, architecture.name))
                return
            findings = review_architecture(architecture)
            if args.json:
                _print_json_result(
                    _result_envelope(
                        command="review",
                        source=args.file,
                        status="warning" if any(f.severity == "risk" for f in findings) else "ok",
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
                )
            else:
                print(format_review(findings, architecture.name))
            return

        if args.command == "review-templates":
            print(format_template_list())
            return

        if args.command == "score":
            architecture = load_architecture(args.file)
            score: ArchitectureScore = score_architecture(architecture)
            if args.json:
                _print_json_result(
                    _result_envelope(
                        command="score",
                        source=args.file,
                        status="ok",
                        data=score.to_dict(),
                    )
                )
            else:
                bar_width = 10
                print(f"\nArchitecture Score: {architecture.name}")
                print("─" * 40)
                print(f"\n  Overall: {score.overall}/100  (Grade {score.grade})\n")
                for d in score.dimensions:
                    filled = round(d.score / 10)
                    bar = "█" * filled + "░" * (bar_width - filled)
                    print(f"  {d.name:<28} {bar}  {d.score:>3}")
                print(f"\n{score.summary}")
                issues = [(d.name, n) for d in score.dimensions for n in d.notes if d.score < 80]
                if issues:
                    print("\nNotes:")
                    for name, note in issues:
                        print(f"  [{name}] {note}")
                print("")
            return

        if args.command == "lifecycle":
            architecture = load_architecture(args.file)
            lc_report: LifecycleReport = analyze_lifecycle(architecture)
            if args.json:
                _print_json_result(
                    _result_envelope(
                        command="lifecycle",
                        source=args.file,
                        status="warning" if lc_report.health != "healthy" else "ok",
                        data=lc_report.to_dict(),
                    )
                )
            else:
                _HEALTH_ICON = {"healthy": "✓", "warning": "⚠", "critical": "✗"}
                icon = _HEALTH_ICON.get(lc_report.health, "?")
                print(f"\nLifecycle: {architecture.name}  [{icon} {lc_report.health}]")
                print("─" * 40)
                print("\nDistribution:")
                for state, count in lc_report.distribution.items():
                    if count:
                        print(f"  {state:<12} {count}")
                if lc_report.deprecated_in_use:
                    print("\nDeprecated components still in active flows:")
                    for dep in lc_report.deprecated_in_use:
                        print(f"  ✗ {dep.name}  ({dep.flow_count} flow(s))")
                        for f in dep.flows[:4]:
                            print(f"      {f}")
                if lc_report.planned_unconnected:
                    print("\nPlanned components not yet connected:")
                    for p in lc_report.planned_unconnected:
                        desc = f" — {p.description}" if p.description else ""
                        print(f"  ○ {p.name}{desc}")
                if lc_report.no_lifecycle:
                    print("\nComponents missing lifecycle field:")
                    for name in lc_report.no_lifecycle:
                        print(f"  ? {name}")
                print(f"\n{lc_report.summary}\n")
            return

        if args.command == "report":
            architecture = load_architecture(args.file)
            content = generate_report(architecture, format=args.format)
            if args.json:
                report_artifact: dict = (
                    {"type": "report", "format": args.format, "path": args.output}
                    if args.output
                    else {"type": "report", "format": args.format, "content": content}
                )
                if args.output:
                    _write_text_output(content, args.output)
                _print_json_result(
                    _result_envelope(
                        command="report",
                        source=args.file,
                        status="ok",
                        data={"format": args.format, "name": architecture.name},
                        artifacts=[report_artifact],
                    )
                )
            elif args.output:
                _write_text_output(content, args.output)
                print(f"Report generated: {args.output}")
            else:
                print(content)
            return

        if args.command == "explain":
            architecture = load_architecture(args.file)
            ctx = explain_risk(architecture, args.risk_id)
            if ctx is None:
                print(f"Risk '{args.risk_id}' not found in {args.file}", file=sys.stderr)
                raise SystemExit(1)
            if args.json:
                _print_json_result(
                    _result_envelope(
                        command="explain",
                        source=args.file,
                        status="ok",
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
                )
            else:
                print(format_risk_context(ctx))
            return

        if args.command == "reference":
            print(build_reference())
            return

        if args.command == "templates":
            print(list_templates())
            return

        if args.command == "diff":
            a = load_architecture(args.file_a)
            b = load_architecture(args.file_b)
            diff = diff_architectures(a, b, source=args.file_a, target=args.file_b)
            if args.json:
                _print_json_result(
                    _result_envelope(
                        command="diff",
                        source=args.file_a,
                        status="warning" if not diff.is_empty() else "ok",
                        data=_diff_to_dict(diff),
                    )
                )
            else:
                print(format_diff(diff))
            raise SystemExit(1 if not diff.is_empty() else 0)

        if args.command == "impact":
            arch_before = load_architecture(args.before)
            arch_after = load_architecture(args.after)
            diff = diff_architectures(arch_before, arch_after, source=args.before, target=args.after)
            impact_report: ChangeImpactReport = analyze_impact(arch_before, arch_after, diff)
            if args.json:
                _print_json_result(
                    _result_envelope(
                        command="impact",
                        source=args.before,
                        status="warning" if impact_report.severity in ("critical", "high") else "ok",
                        data=impact_report.to_dict(),
                    )
                )
            else:
                print(format_impact(impact_report))
            raise SystemExit(1 if impact_report.severity in ("critical", "high") else 0)

        if args.command == "govern":
            try:
                policy = load_governance_policy(args.policy)
            except GovernancePolicyError as exc:
                print(f"Error loading policy: {exc}", file=sys.stderr)
                raise SystemExit(1) from exc
            architecture = load_architecture(args.file)
            gov_result = check_governance(architecture, policy)
            if args.json:
                _print_json_result(
                    _result_envelope(
                        command="govern",
                        source=args.file,
                        status="warning" if (gov_result.violations and not gov_result.has_errors) else
                               ("error" if gov_result.has_errors else "ok"),
                        data=gov_result.to_dict(),
                    )
                )
            else:
                print(format_governance_result(gov_result, args.policy, architecture.name))
            raise SystemExit(1 if gov_result.has_errors else 0)

        if args.command == "history":
            hist_report = analyze_history(args.file)
            if args.json:
                _print_json_result(
                    _result_envelope(
                        command="history",
                        source=args.file,
                        status="ok",
                        data=hist_report.to_dict(),
                    )
                )
            else:
                print(format_history(hist_report))
            return

        if args.command == "memory":
            if not getattr(args, "mem_action", None):
                memory_parser.print_help()  # type: ignore[name-defined]
                raise SystemExit(1)

            if args.mem_action == "add":
                try:
                    model = add_to_memory(args.file)
                    score_str = f"  score {model.score} ({model.grade})" if model.score else ""
                    print(f"Indexed '{model.name}' — {model.component_count} components{score_str}")
                except ArchMemoryError as exc:
                    print(f"Error: {exc}", file=sys.stderr)
                    raise SystemExit(1) from exc
                return

            if args.mem_action == "remove":
                try:
                    remove_from_memory(args.file)
                    print(f"Removed '{args.file}' from memory index.")
                except ArchMemoryError as exc:
                    print(f"Error: {exc}", file=sys.stderr)
                    raise SystemExit(1) from exc
                return

            if args.mem_action == "list":
                models = list_memory()
                if args.json:
                    _print_json_result(
                        _result_envelope(
                            command="memory-list",
                            source="",
                            status="ok",
                            data={"models": [m.to_dict() for m in models]},
                        )
                    )
                else:
                    print(format_memory_list(models))
                return

            if args.mem_action == "search":
                results = search_memory(args.query)
                if args.json:
                    _print_json_result(
                        _result_envelope(
                            command="memory-search",
                            source="",
                            status="ok",
                            data={"query": args.query,
                                  "results": [r.to_dict() for r in results]},
                        )
                    )
                else:
                    print(format_search_results(results, args.query))
                return

            if args.mem_action == "compare":
                arch_a = load_architecture(args.file_a)
                arch_b = load_architecture(args.file_b)
                cmp_result = compare_architectures(arch_a, arch_b,
                                                   name_a=args.file_a, name_b=args.file_b)
                if args.json:
                    _print_json_result(
                        _result_envelope(
                            command="memory-compare",
                            source=args.file_a,
                            status="ok",
                            data=cmp_result.to_dict(),
                        )
                    )
                else:
                    print(format_comparison(cmp_result))
                return

        if args.command == "snapshot":
            if not getattr(args, "snap_action", None):
                snapshot_parser.print_help()  # type: ignore[name-defined]
                raise SystemExit(1)

            if args.snap_action == "save":
                try:
                    meta = save_snapshot(args.file, args.tag, description=args.description)
                    print(f"Snapshot '{meta.tag}' saved  ({meta.created_at})")
                except SnapshotError as exc:
                    print(f"Error: {exc}", file=sys.stderr)
                    raise SystemExit(1) from exc
                return

            if args.snap_action == "list":
                snaps = list_snapshots(args.file)
                if args.json:
                    _print_json_result(
                        _result_envelope(
                            command="snapshot-list",
                            source=args.file,
                            status="ok",
                            data={"snapshots": [s.to_dict() for s in snaps]},
                        )
                    )
                else:
                    print(format_snapshot_list(args.file, snaps))
                return

            if args.snap_action == "delete":
                try:
                    delete_snapshot(args.file, args.tag)
                    print(f"Snapshot '{args.tag}' deleted.")
                except SnapshotError as exc:
                    print(f"Error: {exc}", file=sys.stderr)
                    raise SystemExit(1) from exc
                return

            if args.snap_action in ("diff", "impact"):
                try:
                    arch_a = load_snapshot_architecture(args.file, args.tag_a)
                    arch_b = load_snapshot_architecture(args.file, args.tag_b)
                except SnapshotError as exc:
                    print(f"Error: {exc}", file=sys.stderr)
                    raise SystemExit(1) from exc

                label_a = f"{args.file}@{args.tag_a}"
                label_b = f"{args.file}@{args.tag_b}"
                diff = diff_architectures(arch_a, arch_b, source=label_a, target=label_b)

                if args.snap_action == "diff":
                    if args.json:
                        _print_json_result(
                            _result_envelope(
                                command="snapshot-diff",
                                source=args.file,
                                status="warning" if not diff.is_empty() else "ok",
                                data=_diff_to_dict(diff),
                            )
                        )
                    else:
                        print(format_diff(diff))
                    raise SystemExit(1 if not diff.is_empty() else 0)

                # snap_action == "impact"
                snap_impact = analyze_impact(arch_a, arch_b, diff)
                if args.json:
                    _print_json_result(
                        _result_envelope(
                            command="snapshot-impact",
                            source=args.file,
                            status="warning" if snap_impact.severity in ("critical", "high") else "ok",
                            data=snap_impact.to_dict(),
                        )
                    )
                else:
                    print(format_impact(snap_impact))
                raise SystemExit(1 if snap_impact.severity in ("critical", "high") else 0)

        if args.command == "init":
            exit_code = run_init_wizard(
                output_path=args.output,
                validate=not args.no_validate,
                minimal=args.minimal,
                template=args.template,
            )
            raise SystemExit(exit_code)
    except ValidationError as error:
        _print_validation_error(error)
        raise SystemExit(1) from error

    parser.print_help()
    raise SystemExit(1)


if __name__ == "__main__":
    main()
