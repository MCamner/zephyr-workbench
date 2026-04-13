from __future__ import annotations

import sys

from zephyr.analyzer import load_architecture, summarize_architecture
from zephyr.diagram import to_mermaid


def print_help() -> None:
    print("Usage:")
    print("  zephyr summary <file>")
    print("  zephyr diagram <file> --format mermaid")


def main() -> None:
    args = sys.argv[1:]

    if not args:
        print_help()
        raise SystemExit(1)

    command = args[0]

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

    print_help()
    raise SystemExit(1)
