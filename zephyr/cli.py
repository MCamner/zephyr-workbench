from __future__ import annotations

import argparse
import sys

from zephyr.analyzer import load_architecture, summarize_architecture
from zephyr.diagram import to_mermaid
from zephyr.init_wizard import run_init_wizard
from zephyr.validation import ValidationError


def print_help() -> None:
    parser = _build_parser()
    parser.print_help()


def _print_validation_error(error: ValidationError) -> None:
    print("Validation failed:", file=sys.stderr)
    for message in error.errors:
        print(f"- {message}", file=sys.stderr)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zephyr")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate", help="Validate an architecture YAML file")
    validate_parser.add_argument("file")

    summary_parser = subparsers.add_parser("summary", help="Show a text summary for an architecture")
    summary_parser.add_argument("file")

    diagram_parser = subparsers.add_parser("diagram", help="Render a Mermaid diagram from an architecture")
    diagram_parser.add_argument("file")
    diagram_parser.add_argument("--format", choices=["mermaid"], required=True)

    init_parser = subparsers.add_parser("init", help="Create a new architecture YAML file")
    init_parser.add_argument("--output", help="Output YAML path")
    init_parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip validation after generation",
    )
    init_parser.add_argument("--template", help="Optional starter template name")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args(sys.argv[1:])

    if not args.command:
        parser.print_help()
        raise SystemExit(1)

    try:
        if args.command == "validate":
            architecture = load_architecture(args.file)
            print(f"Validation passed: {architecture.name}")
            return

        if args.command == "summary":
            architecture = load_architecture(args.file)
            print(summarize_architecture(architecture))
            return

        if args.command == "diagram":
            architecture = load_architecture(args.file)
            print(to_mermaid(architecture))
            return

        if args.command == "init":
            exit_code = run_init_wizard(
                output_path=args.output,
                validate=not args.no_validate,
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
