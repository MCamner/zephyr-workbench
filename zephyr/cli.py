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
from zephyr.search import search_architecture
from zephyr.analyzer import load_architecture, summarize_architecture, summarize_architecture_data
from zephyr.diagram import to_html, to_mermaid
from zephyr.diff import diff_architectures, format_diff
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

  init
    Create a new model interactively (guided wizard).
    • --template <name>     start from a template, skip the wizard
    • --minimal             skip optional fields for a faster flow
    • --no-validate         skip validation after writing

  templates
    List available starter templates with descriptions.

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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zephyr")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate", help="Validate an architecture YAML file")
    validate_parser.add_argument("file")

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

    add_parser = subparsers.add_parser("add", help="Add items to an existing architecture model")
    add_parser.add_argument("file")

    search_parser = subparsers.add_parser("search", help="Filter components, flows, risks by field value")
    search_parser.add_argument("file")
    search_parser.add_argument(
        "query",
        help="Filter expression: type=endpoint, severity=high, encryption=none, missing=mitigation",
    )

    subparsers.add_parser("reference", help="Show all valid field values")
    subparsers.add_parser("templates", help="List available starter templates")
    subparsers.add_parser("help", help="Show detailed usage guide")

    diff_parser = subparsers.add_parser("diff", help="Compare two architecture YAML files")
    diff_parser.add_argument("file_a", metavar="FILE_A")
    diff_parser.add_argument("file_b", metavar="FILE_B")

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
    _print_warnings(result.warnings)
    if result.warnings:
        print("Validation passed with warnings")
    else:
        print("Validation passed")
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
            result = load_validation_result(args.file)
            _print_warnings(result.warnings)
            if result.warnings:
                print(f"Validation passed with warnings: {result.architecture.name}")
            else:
                print(f"Validation passed: {result.architecture.name}")
            return

        if args.command == "summary":
            architecture = load_architecture(args.file)
            if args.json:
                print(json.dumps(summarize_architecture_data(architecture), indent=2))
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
                print(f"Diagram generated: {output}")
            else:
                diagram = _render_diagram(architecture, args.format)
                if args.output:
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

        if args.command == "add":
            raise SystemExit(run_add(args.file))

        if args.command == "search":
            architecture = load_architecture(args.file)
            print(search_architecture(architecture, args.query))
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
            print(format_diff(diff))
            raise SystemExit(1 if not diff.is_empty() else 0)

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
