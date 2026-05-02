#!/usr/bin/env python3
"""Regenerate marked sections in docs/zephyr-core.js from Python source.

Sections are delimited by:
    // @@GEN:START <name>
    // @@GEN:END

Run directly or via `make generate-js`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from zephyr.datamodel import (
    AUTH_TYPES,
    COMPONENT_TYPES,
    CONTROL_TYPES,
    CRITICALITIES,
    DOMAINS,
    ENCRYPTION_TYPES,
    ENVIRONMENTS,
    EXPOSURES,
    FLOW_DIRECTIONS,
    IMPACTS,
    LIFECYCLES,
    LIKELIHOODS,
    SEVERITIES,
    STAKEHOLDER_ROLES,
)
from zephyr.diagram import _CLASS_DEFS, _TYPE_TO_CLASS
from zephyr.templates import _TEMPLATES

TARGET = Path(__file__).parent.parent / "docs" / "zephyr-core.js"

_INDENT = "  "
_JS_IDENT = re.compile(r"^[a-zA-Z_$][a-zA-Z0-9_$]*$")
_GEN_RE = re.compile(r"(// @@GEN:START (\w+)\n)(.*?)(  // @@GEN:END)", re.DOTALL)


def _js_key(k: str) -> str:
    return k if _JS_IDENT.match(k) else json.dumps(k)


def _js_val(val: object, indent: int) -> str:
    pad = _INDENT * indent
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, list):
        if not val:
            return "[]"
        if all(isinstance(x, str) for x in val):
            return "[" + ",".join(json.dumps(x) for x in val) + "]"
        parts = [f"{pad}  {_js_val(x, indent + 1)}" for x in val]
        return "[\n" + ",\n".join(parts) + ",\n" + pad + "]"
    if isinstance(val, dict):
        if not val:
            return "{}"
        parts = []
        for k, v in val.items():
            rendered = _js_val(v, indent + 1)
            parts.append(f"{pad}  {_js_key(k)}: {rendered}")
        return "{\n" + ",\n".join(parts) + ",\n" + pad + "}"
    return json.dumps(str(val))


def _generate_enums(indent: int = 1) -> str:
    pad = _INDENT * indent
    lines = []

    def const(name: str, values: list[str]) -> None:
        items = ",".join(json.dumps(v) for v in values)
        single = f"{pad}const {name} = [{items}];"
        if len(single) <= 80:
            lines.append(single)
            return
        # wrap long arrays
        lines.append(f"{pad}const {name} = [")
        row: list[str] = []
        row_len = 0
        for v in values:
            item = json.dumps(v) + ","
            if row and row_len + len(item) + 1 > 72:
                lines.append(f"{pad}  " + " ".join(row))
                row, row_len = [], 0
            row.append(item)
            row_len += len(item) + 1
        if row:
            lines.append(f"{pad}  " + " ".join(row))
        lines.append(f"{pad}];")

    const("DOMAINS", DOMAINS)
    const("COMPONENT_TYPES", COMPONENT_TYPES)
    const("SEVERITIES", SEVERITIES)
    const("LIKELIHOODS", LIKELIHOODS)
    const("IMPACTS", IMPACTS)
    const("CONTROL_TYPES", CONTROL_TYPES)
    const("STAKEHOLDER_ROLES", STAKEHOLDER_ROLES)
    const("ENVIRONMENTS", ENVIRONMENTS)
    const("CRITICALITIES", CRITICALITIES)
    const("EXPOSURES", EXPOSURES)
    const("LIFECYCLES", LIFECYCLES)
    const("FLOW_DIRECTIONS", FLOW_DIRECTIONS)
    const("AUTH_TYPES", AUTH_TYPES)
    const("ENCRYPTION_TYPES", ENCRYPTION_TYPES)

    return "\n".join(lines)


def _generate_diagram(indent: int = 1) -> str:
    pad = _INDENT * indent
    lines = []

    # TYPE_TO_CLASS — two entries per line
    lines.append(f"{pad}const TYPE_TO_CLASS = {{")
    items = list(_TYPE_TO_CLASS.items())
    for i in range(0, len(items), 2):
        chunk = items[i : i + 2]
        pairs = ",".join(f'"{k}":"{v}"' for k, v in chunk)
        lines.append(f"{pad}  {pairs},")
    lines.append(f"{pad}}};")

    # CLASS_DEFS — aligned
    lines.append(f"{pad}const CLASS_DEFS = {{")
    max_len = max(len(k) for k in _CLASS_DEFS)
    for k, v in _CLASS_DEFS.items():
        padding = " " * (max_len - len(k) + 1)
        lines.append(f'{pad}  {k}:{padding}"{v}",')
    lines.append(f"{pad}}};")

    return "\n".join(lines)


def _generate_templates(indent: int = 1) -> str:
    pad = _INDENT * indent
    lines = [f"{pad}const TEMPLATES = {{"]
    for name, template in _TEMPLATES.items():
        rendered = _js_val(template, indent + 1)
        lines.append(f"{pad}  {_js_key(name)}: {rendered},")
    lines.append(f"{pad}}};")
    return "\n".join(lines)


_GENERATORS = {
    "enums": _generate_enums,
    "diagram": _generate_diagram,
    "templates": _generate_templates,
}


def _replace_sections(content: str) -> str:
    def replacer(m: re.Match) -> str:
        name = m.group(2)
        if name not in _GENERATORS:
            return m.group(0)
        new_body = _GENERATORS[name]() + "\n"
        return f"{m.group(1)}{new_body}{m.group(4)}"

    return _GEN_RE.sub(replacer, content)


def main() -> None:
    if not TARGET.exists():
        print(f"error: {TARGET} not found", file=sys.stderr)
        sys.exit(1)

    original = TARGET.read_text(encoding="utf-8")
    updated = _replace_sections(original)

    if updated == original:
        print("docs/zephyr-core.js already in sync.")
    else:
        TARGET.write_text(updated, encoding="utf-8")
        print("docs/zephyr-core.js updated.")


if __name__ == "__main__":
    main()
