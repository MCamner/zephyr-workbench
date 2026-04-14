from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from zephyr.init_wizard import run_init_wizard
from zephyr.validation import load_validated_architecture


def test_run_init_wizard_creates_expected_output_shape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "generated.yaml"
    answers = iter(
        [
            "macos-intune-secure-access",
            "Secure enterprise access for macOS devices",
            "y",
            "user",
            "actor",
            "",
            "y",
            "macbook",
            "endpoint",
            "",
            "n",
            "y",
            "user",
            "macbook",
            "signs in",
            "n",
            "y",
            "R1",
            "VPN is single point of failure",
            "high",
            "n",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    exit_code = run_init_wizard(output_path=str(output_path), validate=False, minimal=True)

    assert exit_code == 0
    data = yaml.safe_load(output_path.read_text(encoding="utf-8"))

    assert data["name"] == "macos-intune-secure-access"
    assert "meta" in data
    assert "domains" in data
    assert "components" in data
    assert "flows" in data
    assert "risks" in data
    assert "controls" not in data
    assert "stakeholders" not in data
    assert data["components"][0]["criticality"] == "medium"
    assert data["flows"][0]["direction"] == "outbound"
    assert data["risks"][0]["likelihood"] == "medium"


def test_generated_yaml_validates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "validated.yaml"
    answers = iter(
        [
            "identity-edge",
            "",
            "",
            "",
            "",
            "y",
            "idp",
            "identity-provider",
            "",
            "",
            "",
            "",
            "",
            "n",
            "n",
            "n",
            "n",
            "y",
            "Platform Team",
            "owner",
            "n",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    exit_code = run_init_wizard(output_path=str(output_path), validate=True)

    assert exit_code == 0
    architecture = load_validated_architecture(output_path)
    assert architecture.name == "identity-edge"
    assert len(architecture.components) == 1


def test_guided_mode_only_adds_optional_sections_when_selected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "guided.yaml"
    answers = iter(
        [
            "secure-workplace",
            "",
            "platform-team",
            "",
            "",
            "y",
            "user",
            "actor",
            "",
            "",
            "",
            "",
            "",
            "n",
            "n",
            "n",
            "n",
            "n",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    exit_code = run_init_wizard(output_path=str(output_path), validate=False)

    assert exit_code == 0
    data = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert data["meta"]["owner"] == "platform-team"
    assert data["meta"]["environment"] == ["prod"]
    assert data["meta"]["criticality"] == "medium"
    assert data["controls"] == []
    assert data["stakeholders"] == []


def test_invalid_selection_is_blocked_until_valid(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["bad", "actor"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    from zephyr.init_wizard import _prompt_choice

    result = _prompt_choice("Type", ["actor", "endpoint"])

    assert result == "actor"
    captured = capsys.readouterr()
    assert "Invalid selection. Choose one of: actor/endpoint" in captured.out
