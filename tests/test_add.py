from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from zephyr.add import run_add


def _write_model(path: Path, **overrides) -> None:
    model = {
        "name": "test-arch",
        "components": [
            {"name": "api", "type": "application", "domain": "application",
             "criticality": "medium", "exposure": "internal", "lifecycle": "active"},
        ],
        "flows": [],
        "risks": [],
        **overrides,
    }
    path.write_text(yaml.safe_dump(model, sort_keys=False), encoding="utf-8")


def test_add_component_appends_and_saves(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    model_path = tmp_path / "arch.yaml"
    _write_model(model_path)

    # _prompt_choice_list for "What to add" (5 items > threshold 4): number or name
    # prompt_components(minimal=False) with no existing items (default=True for first "Add component?")
    # Type has 14 items → list → "application" accepted by _resolve_option as exact name
    # Domain has 4 items → inline → "" accepts default derived from type
    answers = iter([
        "1",           # what to add → "component" (index 1)
        "",            # add component? default=True
        "db",          # name
        "application", # type (exact name accepted by list resolver)
        "",            # domain (accept suggested default)
        "",            # description (skip)
        "",            # criticality (accept default "medium")
        "",            # exposure (accept default "internal")
        "",            # lifecycle (accept default "active")
        "n",           # add another?
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    exit_code = run_add(str(model_path))

    assert exit_code == 0
    data = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    names = [c["name"] for c in data["components"]]
    assert "api" in names
    assert "db" in names


def test_add_flow_appends_and_saves(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    model_path = tmp_path / "arch.yaml"
    _write_model(model_path, components=[
        {"name": "idp", "type": "identity-provider", "domain": "application",
         "criticality": "high", "exposure": "internal", "lifecycle": "active"},
        {"name": "client", "type": "endpoint", "domain": "technology",
         "criticality": "medium", "exposure": "internal", "lifecycle": "active"},
    ])

    # component_names has 2 items → inline choice → exact name
    # prompt_flows(minimal=False): protocol, auth, encryption, direction after label
    answers = iter([
        "2",      # what to add → "flow" (index 2)
        "",       # add flow? default=True (bool(component_names) and not flows)
        "idp",    # from
        "client", # to
        "auth",   # label
        "",       # protocol (skip, empty ok)
        "",       # authentication (accept default "none")
        "",       # encryption (accept default "none")
        "",       # direction (accept default "outbound")
        "n",      # add another?
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    exit_code = run_add(str(model_path))

    assert exit_code == 0
    data = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    assert len(data["flows"]) == 1
    assert data["flows"][0]["label"] == "auth"
    assert data["flows"][0]["from"] == "idp"
    assert data["flows"][0]["to"] == "client"


def test_add_risk_appends_and_saves(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    model_path = tmp_path / "arch.yaml"
    _write_model(model_path)

    # prompt_risks(minimal=False): severity(inline 4), likelihood(inline 3),
    # impact(inline 3), description(text), mitigation(text)
    answers = iter([
        "3",    # what to add → "risk" (index 3)
        "y",    # add risk? default=False so must say "y"
        "R1",   # risk id
        "SPOF", # title
        "high", # severity (inline: low/medium/high/critical)
        "",     # likelihood (accept default "medium")
        "",     # impact (accept default "medium")
        "",     # description (skip)
        "",     # mitigation (skip)
        "n",    # add another?
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    exit_code = run_add(str(model_path))

    assert exit_code == 0
    data = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    assert len(data["risks"]) == 1
    assert data["risks"][0]["id"] == "R1"
    assert data["risks"][0]["severity"] == "high"


def test_add_flow_fails_when_no_components(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    model_path = tmp_path / "arch.yaml"
    model_path.write_text(
        yaml.safe_dump({"name": "empty", "components": [], "flows": []}, sort_keys=False),
        encoding="utf-8",
    )

    monkeypatch.setattr("builtins.input", lambda _: "flow")

    exit_code = run_add(str(model_path))

    assert exit_code == 1


def test_add_returns_error_for_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "component")

    exit_code = run_add("nonexistent.yaml")

    assert exit_code == 1


def test_add_control_fails_when_no_components(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    model_path = tmp_path / "arch.yaml"
    model_path.write_text(
        yaml.safe_dump({"name": "empty", "components": [], "flows": []}, sort_keys=False),
        encoding="utf-8",
    )

    monkeypatch.setattr("builtins.input", lambda _: "control")

    exit_code = run_add(str(model_path))

    assert exit_code == 1
