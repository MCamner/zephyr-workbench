from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from zephyr.init_wizard import run_init_wizard
from zephyr.templates import get_template, list_templates, template_names
from zephyr.validation import load_validated_architecture


def test_all_templates_are_valid() -> None:
    for name in template_names():
        model = get_template(name)
        assert model is not None, f"Template '{name}' returned None"
        assert "name" in model
        assert "components" in model
        assert "flows" in model


def test_all_templates_pass_validation(tmp_path: Path) -> None:
    for name in template_names():
        model = get_template(name)
        assert model is not None
        path = tmp_path / f"{name}.yaml"
        path.write_text(yaml.safe_dump(model, sort_keys=False), encoding="utf-8")
        arch = load_validated_architecture(path)
        assert arch.name == model["name"]


def test_get_template_returns_none_for_unknown() -> None:
    assert get_template("does-not-exist") is None


def test_get_template_excludes_internal_keys() -> None:
    for name in template_names():
        model = get_template(name)
        assert model is not None
        for key in model:
            assert not key.startswith("_"), f"Internal key '{key}' leaked into template '{name}'"


def test_list_templates_contains_all_names() -> None:
    output = list_templates()
    for name in template_names():
        assert name in output


def test_init_with_template_writes_valid_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "out.yaml"
    answers = iter(["my-hybrid", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    exit_code = run_init_wizard(
        template="hybrid-identity",
        output_path=str(output_path),
        validate=True,
    )

    assert exit_code == 0
    data = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert data["name"] == "my-hybrid"
    assert len(data["components"]) > 1
    assert len(data["controls"]) > 0
    assert len(data["stakeholders"]) > 0


def test_init_with_unknown_template_returns_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "")
    exit_code = run_init_wizard(template="nonexistent", output_path=str(tmp_path / "out.yaml"))
    assert exit_code == 1
