"""Tests for zephyr/snapshots.py and runtime snapshot functions."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from zephyr.snapshots import (
    SnapshotError,
    SnapshotMeta,
    delete_snapshot,
    format_snapshot_list,
    list_snapshots,
    load_snapshot,
    load_snapshot_architecture,
    save_snapshot,
    snapshot_dir,
)
from zephyr.runtime import (
    snapshot_delete,
    snapshot_diff,
    snapshot_impact,
    snapshot_list,
    snapshot_save,
)


EXAMPLES = Path(__file__).parent.parent / "examples"
FIXTURE = EXAMPLES / "identity-flow.yaml"


# ── Helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_snapshots(tmp_path, monkeypatch):
    """Run each test with a temp copy of the fixture so snapshots are isolated."""
    copy = tmp_path / "arch.yaml"
    shutil.copy(FIXTURE, copy)
    yield copy
    snap_root = snapshot_dir(copy)
    if snap_root.exists():
        shutil.rmtree(snap_root)


# ── snapshot_dir ──────────────────────────────────────────────────────────────

def test_snapshot_dir_structure(clean_snapshots):
    path = clean_snapshots
    d = snapshot_dir(path)
    assert d.name == path.stem
    assert ".zephyr" in str(d)


# ── save_snapshot ─────────────────────────────────────────────────────────────

def test_save_returns_snapshot_meta(clean_snapshots):
    meta = save_snapshot(clean_snapshots, "v1.0")
    assert isinstance(meta, SnapshotMeta)


def test_save_creates_yaml_file(clean_snapshots):
    save_snapshot(clean_snapshots, "v1.0")
    snap = snapshot_dir(clean_snapshots) / "v1.0.yaml"
    assert snap.exists()


def test_save_creates_index(clean_snapshots):
    save_snapshot(clean_snapshots, "v1.0")
    idx = snapshot_dir(clean_snapshots) / "index.json"
    assert idx.exists()


def test_save_meta_tag(clean_snapshots):
    meta = save_snapshot(clean_snapshots, "release-1")
    assert meta.tag == "release-1"


def test_save_meta_created_at_format(clean_snapshots):
    meta = save_snapshot(clean_snapshots, "v1.0")
    assert "T" in meta.created_at and meta.created_at.endswith("Z")


def test_save_with_description(clean_snapshots):
    meta = save_snapshot(clean_snapshots, "v1.0", description="Initial release")
    assert meta.description == "Initial release"


def test_save_duplicate_tag_raises(clean_snapshots):
    save_snapshot(clean_snapshots, "v1.0")
    with pytest.raises(SnapshotError, match="already exists"):
        save_snapshot(clean_snapshots, "v1.0")


def test_save_invalid_tag_raises(clean_snapshots):
    with pytest.raises(SnapshotError, match="Invalid tag"):
        save_snapshot(clean_snapshots, "bad tag!")


def test_save_missing_file_raises(tmp_path):
    with pytest.raises(SnapshotError, match="not found"):
        save_snapshot(tmp_path / "nonexistent.yaml", "v1.0")


# ── list_snapshots ────────────────────────────────────────────────────────────

def test_list_empty_when_none_saved(clean_snapshots):
    assert list_snapshots(clean_snapshots) == []


def test_list_returns_saved_snapshots(clean_snapshots):
    save_snapshot(clean_snapshots, "v1.0")
    save_snapshot(clean_snapshots, "v2.0")
    snaps = list_snapshots(clean_snapshots)
    assert len(snaps) == 2


def test_list_preserves_order(clean_snapshots):
    save_snapshot(clean_snapshots, "v1.0")
    save_snapshot(clean_snapshots, "v2.0")
    snaps = list_snapshots(clean_snapshots)
    assert snaps[0].tag == "v1.0"
    assert snaps[1].tag == "v2.0"


# ── load_snapshot ─────────────────────────────────────────────────────────────

def test_load_returns_yaml_text(clean_snapshots):
    save_snapshot(clean_snapshots, "v1.0")
    text = load_snapshot(clean_snapshots, "v1.0")
    assert isinstance(text, str)
    assert "name:" in text


def test_load_missing_raises(clean_snapshots):
    with pytest.raises(SnapshotError, match="not found"):
        load_snapshot(clean_snapshots, "nonexistent")


# ── load_snapshot_architecture ────────────────────────────────────────────────

def test_load_snapshot_architecture_ok(clean_snapshots):
    from zephyr.models import Architecture
    save_snapshot(clean_snapshots, "v1.0")
    arch = load_snapshot_architecture(clean_snapshots, "v1.0")
    assert isinstance(arch, Architecture)


def test_load_snapshot_architecture_has_name(clean_snapshots):
    save_snapshot(clean_snapshots, "v1.0")
    arch = load_snapshot_architecture(clean_snapshots, "v1.0")
    assert arch.name  # non-empty


def test_load_snapshot_architecture_missing_raises(clean_snapshots):
    with pytest.raises(SnapshotError, match="not found"):
        load_snapshot_architecture(clean_snapshots, "ghost")


# ── delete_snapshot ───────────────────────────────────────────────────────────

def test_delete_removes_file(clean_snapshots):
    save_snapshot(clean_snapshots, "v1.0")
    delete_snapshot(clean_snapshots, "v1.0")
    snap = snapshot_dir(clean_snapshots) / "v1.0.yaml"
    assert not snap.exists()


def test_delete_removes_from_index(clean_snapshots):
    save_snapshot(clean_snapshots, "v1.0")
    save_snapshot(clean_snapshots, "v2.0")
    delete_snapshot(clean_snapshots, "v1.0")
    snaps = list_snapshots(clean_snapshots)
    assert all(s.tag != "v1.0" for s in snaps)
    assert any(s.tag == "v2.0" for s in snaps)


def test_delete_missing_raises(clean_snapshots):
    with pytest.raises(SnapshotError, match="not found"):
        delete_snapshot(clean_snapshots, "ghost")


# ── format_snapshot_list ──────────────────────────────────────────────────────

def test_format_empty(clean_snapshots):
    text = format_snapshot_list(clean_snapshots, [])
    assert "No snapshots" in text


def test_format_lists_tags(clean_snapshots):
    save_snapshot(clean_snapshots, "v1.0", description="first")
    snaps = list_snapshots(clean_snapshots)
    text = format_snapshot_list(clean_snapshots, snaps)
    assert "v1.0" in text


# ── runtime.snapshot_save ─────────────────────────────────────────────────────

def test_runtime_save_ok(clean_snapshots):
    result = snapshot_save(clean_snapshots, "v1.0")
    assert result.ok


def test_runtime_save_command(clean_snapshots):
    result = snapshot_save(clean_snapshots, "v1.0")
    assert result.command == "snapshot-save"


def test_runtime_save_data_has_tag(clean_snapshots):
    result = snapshot_save(clean_snapshots, "v1.0")
    assert result.data["tag"] == "v1.0"


def test_runtime_save_duplicate_error(clean_snapshots):
    snapshot_save(clean_snapshots, "v1.0")
    result = snapshot_save(clean_snapshots, "v1.0")
    assert result.failed


# ── runtime.snapshot_list ─────────────────────────────────────────────────────

def test_runtime_list_ok(clean_snapshots):
    result = snapshot_list(clean_snapshots)
    assert result.ok


def test_runtime_list_empty(clean_snapshots):
    result = snapshot_list(clean_snapshots)
    assert result.data["snapshots"] == []


def test_runtime_list_populated(clean_snapshots):
    snapshot_save(clean_snapshots, "v1.0")
    result = snapshot_list(clean_snapshots)
    assert len(result.data["snapshots"]) == 1


# ── runtime.snapshot_delete ───────────────────────────────────────────────────

def test_runtime_delete_ok(clean_snapshots):
    snapshot_save(clean_snapshots, "v1.0")
    result = snapshot_delete(clean_snapshots, "v1.0")
    assert result.ok


def test_runtime_delete_missing_error(clean_snapshots):
    result = snapshot_delete(clean_snapshots, "ghost")
    assert result.failed


# ── runtime.snapshot_diff ─────────────────────────────────────────────────────

def test_runtime_diff_identical_ok(clean_snapshots):
    snapshot_save(clean_snapshots, "v1.0")
    snapshot_save(clean_snapshots, "v1.1")
    result = snapshot_diff(clean_snapshots, "v1.0", "v1.1")
    assert result.ok
    assert result.data["changed"] is False


def test_runtime_diff_missing_snapshot_error(clean_snapshots):
    snapshot_save(clean_snapshots, "v1.0")
    result = snapshot_diff(clean_snapshots, "v1.0", "ghost")
    assert result.failed


def test_runtime_diff_data_has_components(clean_snapshots):
    snapshot_save(clean_snapshots, "v1.0")
    snapshot_save(clean_snapshots, "v1.1")
    result = snapshot_diff(clean_snapshots, "v1.0", "v1.1")
    assert "components" in result.data


# ── runtime.snapshot_impact ───────────────────────────────────────────────────

def test_runtime_impact_identical_ok(clean_snapshots):
    snapshot_save(clean_snapshots, "v1.0")
    snapshot_save(clean_snapshots, "v1.1")
    result = snapshot_impact(clean_snapshots, "v1.0", "v1.1")
    assert result.ok


def test_runtime_impact_data_has_severity(clean_snapshots):
    snapshot_save(clean_snapshots, "v1.0")
    snapshot_save(clean_snapshots, "v1.1")
    result = snapshot_impact(clean_snapshots, "v1.0", "v1.1")
    assert result.data["severity"] == "none"


def test_runtime_impact_missing_snapshot_error(clean_snapshots):
    snapshot_save(clean_snapshots, "v1.0")
    result = snapshot_impact(clean_snapshots, "v1.0", "ghost")
    assert result.failed
