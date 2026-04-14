from __future__ import annotations

import sys

from zephyr.analyzer import load_architecture, summarize_architecture
from zephyr.diagram import to_mermaid
from zephyr.validation import ValidationError


def print_help() -> None:
    print("Usage:")
    print("  zephyr validate <file>")
    print("  zephyr summary <file>")
    print("  zephyr diagram <file> --format mermaid")


def _print_validation_error(error: ValidationError) -> None:
    print("Validation failed:", file=sys.stderr)
    for message in error.errors:
        print(f"- {message}", file=sys.stderr)


def main() -> None:
    args = sys.argv[1:]

    if not args:
        print_help()
        raise SystemExit(1)

    command = args[0]

    try:
        if command == "validate" and len(args) >= 2:
            architecture = load_architecture(args[1])
            print(f"Validation passed: {architecture.name}")
            return

        if command == "summary" and len(args) >= 2:
            architecture = load_architecture(args[1])
            print(summarize_architecture(architecture))
            return

        if (
            command == "diagram"
            and len(args) >= 4
            and args[2] == "--format"
            and args[3] == "mermaid"
        ):
            architecture = load_architecture(args[1])
            print(to_mermaid(architecture))
            return
    except ValidationError as error:
        _print_validation_error(error)
        raise SystemExit(1) from error

    print_help()
    raise SystemExit(1)


if __name__ == "__main__":
    main()
