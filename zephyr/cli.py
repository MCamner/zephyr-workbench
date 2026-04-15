from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from zephyr.analyzer import load_architecture, summarize_architecture, summarize_architecture_data
from zephyr.diagram import to_mermaid
from zephyr.init_wizard import run_init_wizard
from zephyr.validation import ValidationError, load_validation_result


def print_help() -> None:
    parser = _build_parser()
    parser.print_help()


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

    diagram_parser = subparsers.add_parser("diagram", help="Render a Mermaid diagram from an architecture")
    diagram_parser.add_argument("file")
    diagram_parser.add_argument("--format", choices=["mermaid"], required=True)
    diagram_parser.add_argument("--output", help="Write diagram output to a file instead of stdout")

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
        choices=["mermaid"],
        default="mermaid",
        help="Diagram format to generate",
    )

    return parser


def _write_text_output(contents: str, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def _default_diagram_path(source_file: str, output_dir: str, format_name: str) -> Path:
    suffix = ".mmd" if format_name == "mermaid" else f".{format_name}"
    return Path(output_dir) / f"{Path(source_file).stem}{suffix}"


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args(sys.argv[1:])

    if not args.command:
        parser.print_help()
        raise SystemExit(1)

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
            diagram = to_mermaid(architecture)
            if args.output:
                _write_text_output(diagram, args.output)
                print(f"Diagram generated: {args.output}")
            else:
                print(diagram)
            return

        if args.command == "run":
            result = load_validation_result(args.file)
            architecture = result.architecture
            diagram_path = _default_diagram_path(args.file, args.output_dir, args.format)
            diagram = to_mermaid(architecture)
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
            return

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
