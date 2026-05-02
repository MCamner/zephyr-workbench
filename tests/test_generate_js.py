from __future__ import annotations

from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_js_core import _generate_enums, _generate_diagram, _generate_templates, _replace_sections

from zephyr.datamodel import COMPONENT_TYPES, CRITICALITIES, SEVERITIES
from zephyr.diagram import _CLASS_DEFS, _TYPE_TO_CLASS
from zephyr.templates import template_names


def test_enums_contains_all_component_types() -> None:
    out = _generate_enums()
    for t in COMPONENT_TYPES:
        assert t in out


def test_enums_contains_all_criticalities() -> None:
    out = _generate_enums()
    for c in CRITICALITIES:
        assert c in out


def test_diagram_contains_all_type_to_class_keys() -> None:
    out = _generate_diagram()
    for k in _TYPE_TO_CLASS:
        assert k in out


def test_diagram_contains_all_class_def_styles() -> None:
    out = _generate_diagram()
    for k, style in _CLASS_DEFS.items():
        assert k in out
        assert style in out


def test_templates_contains_all_template_names() -> None:
    out = _generate_templates()
    for name in template_names():
        assert name in out


def test_generator_is_idempotent() -> None:
    target = Path(__file__).parent.parent / "docs" / "zephyr-core.js"
    original = target.read_text(encoding="utf-8")
    regenerated = _replace_sections(original)
    assert regenerated == original, "docs/zephyr-core.js is out of sync — run: make generate-js"
