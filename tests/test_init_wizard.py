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
            "workplace-architecture",
            "prod",
            "high",
            "y",
            "user",
            "actor",
            "y",
            "End user",
            "high",
            "internal",
            "active",
            "y",
            "macbook",
            "endpoint",
            "y",
            "Managed corporate device",
            "high",
            "internal",
            "active",
            "n",
            "y",
            "user",
            "macbook",
            "signs in",
            "https",
            "mfa",
            "tls",
            "outbound",
            "n",
            "y",
            "R1",
            "VPN is single point of failure",
            "high",
            "medium",
            "high",
            "Remote access depends on one gateway",
            "Add redundant gateway",
            "n",
            "y",
            "MFA policy",
            "policy",
            "macbook",
            "Require MFA for sign-in",
            "n",
            "y",
            "Workplace Architecture",
            "owner",
            "n",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    exit_code = run_init_wizard(output_path=str(output_path), validate=False)

    assert exit_code == 0
    data = yaml.safe_load(output_path.read_text(encoding="utf-8"))

    assert data["name"] == "macos-intune-secure-access"
    assert "meta" in data
    assert "domains" in data
    assert "components" in data
    assert "flows" in data
    assert "risks" in data
    assert "controls" in data
    assert "stakeholders" in data


def test_generated_yaml_validates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "validated.yaml"
    answers = iter(
        [
            "identity-edge",
            "",
            "platform-team",
            "dev",
            "medium",
            "y",
            "idp",
            "identity-provider",
            "y",
            "",
            "medium",
            "internal",
            "active",
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
