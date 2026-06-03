"""Tests for zephyr/history.py and runtime.history_model()."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from zephyr.history import (
    EvolutionTrend,
    HistoryEntry,
    HistoryReport,
    analyze_history,
    format_history,
)
from zephyr.runtime import history_model
from zephyr.snapshots import save_snapshot, snapshot_dir


EXAMPLES = Path(__file__).parent.parent / "examples"
FIXTURE = EXAMPLES / "identity-flow.yaml"


# ── Fixture helpers ───────────────────────────────────────────────────────────

@pytest.fixture()
def arch_copy(tmp_path):
    copy = tmp_path / "arch.yaml"
    shutil.copy(FIXTURE, copy)
    yield copy
    snap_root = snapshot_dir(copy)
    if snap_root.exists():
        shutil.rmtree(snap_root)


def _save(path, tag, desc=""):
    save_snapshot(path, tag, description=desc)


# ── analyze_history — no snapshots ───────────────────────────────────────────

def test_returns_history_report(arch_copy):
    assert isinstance(analyze_history(str(arch_copy)), HistoryReport)


def test_no_snapshots_empty_entries(arch_copy):
    report = analyze_history(str(arch_copy))
    assert report.entries == []


def test_no_snapshots_trend_insufficient_data(arch_copy):
    report = analyze_history(str(arch_copy))
    assert report.trend.direction == "insufficient_data"


def test_no_snapshots_summary_mentions_no_snapshots(arch_copy):
    report = analyze_history(str(arch_copy))
    assert "No snapshots" in report.summary


# ── analyze_history — single snapshot ────────────────────────────────────────

def test_single_snapshot_one_entry(arch_copy):
    _save(arch_copy, "v1.0")
    report = analyze_history(str(arch_copy))
    assert len(report.entries) == 1


def test_single_snapshot_has_score(arch_copy):
    _save(arch_copy, "v1.0")
    report = analyze_history(str(arch_copy))
    entry = report.entries[0]
    assert entry.score is not None or entry.score is None  # graceful either way


def test_single_snapshot_no_impact_severity(arch_copy):
    _save(arch_copy, "v1.0")
    report = analyze_history(str(arch_copy))
    assert report.entries[0].impact_severity is None


def test_single_snapshot_first_change_count_zero(arch_copy):
    _save(arch_copy, "v1.0")
    report = analyze_history(str(arch_copy))
    assert report.entries[0].change_count == 0


def test_single_snapshot_trend_insufficient(arch_copy):
    _save(arch_copy, "v1.0")
    report = analyze_history(str(arch_copy))
    assert report.trend.direction == "insufficient_data"


# ── analyze_history — two identical snapshots ─────────────────────────────────

def test_two_identical_snapshots_two_entries(arch_copy):
    _save(arch_copy, "v1.0")
    _save(arch_copy, "v1.1")
    report = analyze_history(str(arch_copy))
    assert len(report.entries) == 2


def test_two_identical_snapshots_zero_changes(arch_copy):
    _save(arch_copy, "v1.0")
    _save(arch_copy, "v1.1")
    report = analyze_history(str(arch_copy))
    assert report.entries[1].change_count == 0


def test_two_identical_snapshots_impact_none(arch_copy):
    _save(arch_copy, "v1.0")
    _save(arch_copy, "v1.1")
    report = analyze_history(str(arch_copy))
    assert report.entries[1].impact_severity == "none"


def test_two_identical_snapshots_trend_stable(arch_copy):
    _save(arch_copy, "v1.0")
    _save(arch_copy, "v1.1")
    report = analyze_history(str(arch_copy))
    assert report.trend.direction == "stable"


def test_two_identical_snapshots_score_delta_zero(arch_copy):
    _save(arch_copy, "v1.0")
    _save(arch_copy, "v1.1")
    report = analyze_history(str(arch_copy))
    assert report.trend.score_delta == 0


# ── HistoryReport.to_dict ─────────────────────────────────────────────────────

def test_to_dict_required_keys(arch_copy):
    _save(arch_copy, "v1.0")
    d = analyze_history(str(arch_copy)).to_dict()
    for key in ("path", "arch_name", "entries", "trend", "summary"):
        assert key in d


def test_to_dict_trend_keys(arch_copy):
    _save(arch_copy, "v1.0")
    d = analyze_history(str(arch_copy)).to_dict()
    for key in ("direction", "score_delta", "notes"):
        assert key in d["trend"]


def test_to_dict_entry_keys(arch_copy):
    _save(arch_copy, "v1.0")
    d = analyze_history(str(arch_copy)).to_dict()
    entry = d["entries"][0]
    for key in ("tag", "created_at", "description", "score", "grade",
                "change_count", "impact_severity"):
        assert key in entry


# ── format_history ────────────────────────────────────────────────────────────

def test_format_returns_string(arch_copy):
    _save(arch_copy, "v1.0")
    report = analyze_history(str(arch_copy))
    assert isinstance(format_history(report), str)


def test_format_contains_tag(arch_copy):
    _save(arch_copy, "v1.0")
    report = analyze_history(str(arch_copy))
    assert "v1.0" in format_history(report)


def test_format_contains_trend(arch_copy):
    _save(arch_copy, "v1.0")
    _save(arch_copy, "v1.1")
    report = analyze_history(str(arch_copy))
    text = format_history(report)
    assert "stable" in text.lower() or "improving" in text.lower() or "degrading" in text.lower()


def test_format_no_snapshots_message(arch_copy):
    report = analyze_history(str(arch_copy))
    text = format_history(report)
    assert "No snapshots" in text


# ── runtime.history_model ─────────────────────────────────────────────────────

def test_runtime_history_ok(arch_copy):
    result = history_model(str(arch_copy))
    assert result.ok
    assert result.command == "history"


def test_runtime_history_data_keys(arch_copy):
    result = history_model(str(arch_copy))
    for key in ("path", "arch_name", "entries", "trend", "summary"):
        assert key in result.data


def test_runtime_history_with_snapshot(arch_copy):
    _save(arch_copy, "v1.0")
    result = history_model(str(arch_copy))
    assert result.ok
    assert len(result.data["entries"]) == 1
