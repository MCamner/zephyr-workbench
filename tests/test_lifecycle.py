"""Tests for zephyr/lifecycle.py and runtime.lifecycle_model()."""

from __future__ import annotations

from pathlib import Path

from zephyr.models import Architecture, Component, Flow
from zephyr.lifecycle import LifecycleReport, analyze_lifecycle
from zephyr.runtime import lifecycle_model


EXAMPLES = Path(__file__).parent.parent / "examples"


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _empty() -> Architecture:
    return Architecture(name="empty")


def _healthy() -> Architecture:
    return Architecture(
        name="healthy",
        components=[
            Component(name="api", type="service", lifecycle="active"),
            Component(name="db", type="data-store", lifecycle="active"),
        ],
        flows=[Flow(source="api", target="db")],
    )


def _deprecated_in_use() -> Architecture:
    return Architecture(
        name="deprecated-in-use",
        components=[
            Component(name="api", type="service", lifecycle="active"),
            Component(name="legacy", type="service", lifecycle="deprecated"),
        ],
        flows=[
            Flow(source="api", target="legacy", label="old-path"),
        ],
    )


def _planned_unconnected() -> Architecture:
    return Architecture(
        name="planned-unconnected",
        components=[
            Component(name="api", type="service", lifecycle="active"),
            Component(name="future", type="service", lifecycle="planned",
                      description="Upcoming replacement"),
        ],
        flows=[Flow(source="api", target="api")],
    )


def _no_lifecycle() -> Architecture:
    return Architecture(
        name="no-lifecycle",
        components=[
            Component(name="svc", type="service"),
            Component(name="db", type="data-store", lifecycle="active"),
        ],
    )


def _mixed() -> Architecture:
    return Architecture(
        name="mixed",
        components=[
            Component(name="a", type="service", lifecycle="active"),
            Component(name="b", type="service", lifecycle="active"),
            Component(name="old", type="service", lifecycle="deprecated"),
            Component(name="future", type="service", lifecycle="planned"),
            Component(name="unknown", type="service"),
        ],
        flows=[
            Flow(source="a", target="b"),
            Flow(source="a", target="old"),
        ],
    )


# ── Return type ───────────────────────────────────────────────────────────────

def test_returns_lifecycle_report() -> None:
    assert isinstance(analyze_lifecycle(_empty()), LifecycleReport)


def test_distribution_keys_always_present() -> None:
    report = analyze_lifecycle(_empty())
    assert set(report.distribution.keys()) == {"active", "deprecated", "planned", "unset"}


# ── Distribution counts ───────────────────────────────────────────────────────

def test_distribution_empty_arch() -> None:
    report = analyze_lifecycle(_empty())
    assert report.distribution == {"active": 0, "deprecated": 0, "planned": 0, "unset": 0}


def test_distribution_healthy_arch() -> None:
    report = analyze_lifecycle(_healthy())
    assert report.distribution["active"] == 2
    assert report.distribution["deprecated"] == 0


def test_distribution_mixed_arch() -> None:
    report = analyze_lifecycle(_mixed())
    assert report.distribution["active"] == 2
    assert report.distribution["deprecated"] == 1
    assert report.distribution["planned"] == 1
    assert report.distribution["unset"] == 1


# ── Deprecated in use ─────────────────────────────────────────────────────────

def test_deprecated_in_use_detected() -> None:
    report = analyze_lifecycle(_deprecated_in_use())
    assert len(report.deprecated_in_use) == 1
    assert report.deprecated_in_use[0].name == "legacy"


def test_deprecated_in_use_includes_flows() -> None:
    report = analyze_lifecycle(_deprecated_in_use())
    d = report.deprecated_in_use[0]
    assert d.flow_count >= 1
    assert any("legacy" in f for f in d.flows)


def test_deprecated_not_in_use_not_flagged() -> None:
    arch = Architecture(
        name="safe",
        components=[
            Component(name="active", type="service", lifecycle="active"),
            Component(name="old", type="service", lifecycle="deprecated"),
        ],
        flows=[Flow(source="active", target="active")],
    )
    report = analyze_lifecycle(arch)
    assert len(report.deprecated_in_use) == 0


def test_no_deprecated_in_use_when_healthy() -> None:
    report = analyze_lifecycle(_healthy())
    assert report.deprecated_in_use == []


# ── Planned unconnected ───────────────────────────────────────────────────────

def test_planned_unconnected_detected() -> None:
    report = analyze_lifecycle(_planned_unconnected())
    assert len(report.planned_unconnected) == 1
    assert report.planned_unconnected[0].name == "future"


def test_planned_unconnected_includes_description() -> None:
    report = analyze_lifecycle(_planned_unconnected())
    assert report.planned_unconnected[0].description == "Upcoming replacement"


def test_planned_with_flows_not_flagged() -> None:
    arch = Architecture(
        name="planned-connected",
        components=[
            Component(name="src", type="service", lifecycle="active"),
            Component(name="new", type="service", lifecycle="planned"),
        ],
        flows=[Flow(source="src", target="new")],
    )
    report = analyze_lifecycle(arch)
    assert len(report.planned_unconnected) == 0


# ── No lifecycle ──────────────────────────────────────────────────────────────

def test_no_lifecycle_detected() -> None:
    report = analyze_lifecycle(_no_lifecycle())
    assert "svc" in report.no_lifecycle


def test_no_lifecycle_excludes_set_fields() -> None:
    report = analyze_lifecycle(_no_lifecycle())
    assert "db" not in report.no_lifecycle


def test_no_lifecycle_empty_when_all_set() -> None:
    report = analyze_lifecycle(_healthy())
    assert report.no_lifecycle == []


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_critical_when_deprecated_in_use() -> None:
    report = analyze_lifecycle(_deprecated_in_use())
    assert report.health == "critical"


def test_health_warning_when_planned_unconnected() -> None:
    report = analyze_lifecycle(_planned_unconnected())
    assert report.health == "warning"


def test_health_warning_when_no_lifecycle() -> None:
    report = analyze_lifecycle(_no_lifecycle())
    assert report.health == "warning"


def test_health_healthy_when_all_clean() -> None:
    report = analyze_lifecycle(_healthy())
    assert report.health == "healthy"


def test_health_healthy_on_empty_arch() -> None:
    report = analyze_lifecycle(_empty())
    assert report.health == "healthy"


# ── Summary ───────────────────────────────────────────────────────────────────

def test_summary_is_non_empty_string() -> None:
    for arch in [_empty(), _healthy(), _deprecated_in_use(), _mixed()]:
        assert isinstance(analyze_lifecycle(arch).summary, str)
        assert len(analyze_lifecycle(arch).summary) > 0


# ── to_dict serialization ─────────────────────────────────────────────────────

def test_to_dict_has_required_keys() -> None:
    d = analyze_lifecycle(_mixed()).to_dict()
    for key in ("distribution", "deprecated_in_use", "planned_unconnected",
                "no_lifecycle", "health", "summary"):
        assert key in d


def test_to_dict_deprecated_in_use_shape() -> None:
    d = analyze_lifecycle(_deprecated_in_use()).to_dict()
    item = d["deprecated_in_use"][0]
    assert "name" in item
    assert "flow_count" in item
    assert "flows" in item


# ── runtime.lifecycle_model ───────────────────────────────────────────────────

def test_lifecycle_model_ok_on_healthy_example() -> None:
    result = lifecycle_model(EXAMPLES / "identity-flow.yaml")
    assert result.ok


def test_lifecycle_model_command_field() -> None:
    result = lifecycle_model(EXAMPLES / "identity-flow.yaml")
    assert result.command == "lifecycle"


def test_lifecycle_model_data_has_health() -> None:
    result = lifecycle_model(EXAMPLES / "identity-flow.yaml")
    assert "health" in result.data
    assert result.data["health"] in ("healthy", "warning", "critical")


def test_lifecycle_model_data_has_distribution() -> None:
    result = lifecycle_model(EXAMPLES / "identity-flow.yaml")
    assert "distribution" in result.data


def test_lifecycle_model_error_on_missing_file() -> None:
    result = lifecycle_model("nonexistent.yaml")
    assert result.failed


def test_lifecycle_model_zero_trust_example() -> None:
    result = lifecycle_model(EXAMPLES / "zero-trust-access.yaml")
    assert result.ok or result.status == "warning"
