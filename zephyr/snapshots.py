"""Zephyr Release Architecture Snapshots.

Stores versioned, tagged snapshots of architecture YAML files so that
change impact analysis and diffs can be run between named releases.

Snapshot directory layout (relative to the YAML file):
  .zephyr/snapshots/<model-stem>/
    index.json       — [{tag, created_at, description}] ordered oldest-first
    <tag>.yaml       — exact copy of the YAML at save time

Entry points:
  save_snapshot(path, tag, description="") -> SnapshotMeta
  list_snapshots(path) -> list[SnapshotMeta]
  load_snapshot(path, tag) -> str   (raw YAML text)
  delete_snapshot(path, tag) -> None
  snapshot_dir(path) -> Path
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from zephyr.models import Architecture


_TAG_RE = re.compile(r"^[a-zA-Z0-9._-]{1,64}$")


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class SnapshotMeta:
    tag: str
    created_at: str   # ISO 8601 UTC
    description: str

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "created_at": self.created_at,
            "description": self.description,
        }


class SnapshotError(Exception):
    pass


# ── Directory helpers ─────────────────────────────────────────────────────────

def snapshot_dir(path: str | Path) -> Path:
    """Return the snapshot directory for a given architecture YAML path."""
    p = Path(path).resolve()
    return p.parent / ".zephyr" / "snapshots" / p.stem


def _index_path(path: str | Path) -> Path:
    return snapshot_dir(path) / "index.json"


def _snap_path(path: str | Path, tag: str) -> Path:
    return snapshot_dir(path) / f"{tag}.yaml"


def _load_index(path: str | Path) -> list[SnapshotMeta]:
    idx = _index_path(path)
    if not idx.exists():
        return []
    entries = json.loads(idx.read_text(encoding="utf-8"))
    return [SnapshotMeta(**e) for e in entries]


def _save_index(path: str | Path, snapshots: list[SnapshotMeta]) -> None:
    idx = _index_path(path)
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text(
        json.dumps([s.to_dict() for s in snapshots], indent=2),
        encoding="utf-8",
    )


# ── Public API ────────────────────────────────────────────────────────────────

def save_snapshot(
    path: str | Path,
    tag: str,
    description: str = "",
) -> SnapshotMeta:
    """Save the current state of `path` as a named snapshot.

    Raises SnapshotError if the tag already exists or is invalid.
    """
    if not _TAG_RE.match(tag):
        raise SnapshotError(
            f"Invalid tag '{tag}'. Use only letters, digits, dots, hyphens, or underscores (max 64 chars)."
        )

    src = Path(path)
    if not src.exists():
        raise SnapshotError(f"Architecture file not found: {path}")

    snapshots = _load_index(path)
    if any(s.tag == tag for s in snapshots):
        raise SnapshotError(f"Snapshot '{tag}' already exists. Delete it first or choose a different tag.")

    dest = _snap_path(path, tag)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

    meta = SnapshotMeta(
        tag=tag,
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        description=description,
    )
    snapshots.append(meta)
    _save_index(path, snapshots)
    return meta


def list_snapshots(path: str | Path) -> list[SnapshotMeta]:
    """Return all snapshots for an architecture file, oldest-first."""
    return _load_index(path)


def load_snapshot(path: str | Path, tag: str) -> str:
    """Return the raw YAML text of a snapshot.

    Raises SnapshotError if the snapshot does not exist.
    """
    snap = _snap_path(path, tag)
    if not snap.exists():
        raise SnapshotError(f"Snapshot '{tag}' not found for {path}.")
    return snap.read_text(encoding="utf-8")


def delete_snapshot(path: str | Path, tag: str) -> None:
    """Delete a named snapshot.

    Raises SnapshotError if the snapshot does not exist.
    """
    snap = _snap_path(path, tag)
    if not snap.exists():
        raise SnapshotError(f"Snapshot '{tag}' not found for {path}.")
    snap.unlink()
    snapshots = [s for s in _load_index(path) if s.tag != tag]
    _save_index(path, snapshots)


# ── Human-readable output ────────────────────────────────────────────────────

def load_snapshot_architecture(path: str | Path, tag: str) -> "Architecture":
    """Parse a snapshot into an Architecture object.

    Raises SnapshotError if the snapshot is missing or unparseable.
    """
    from zephyr.loader import architecture_from_data

    text = load_snapshot(path, tag)
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SnapshotError(f"Snapshot '{tag}' contains invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise SnapshotError(f"Snapshot '{tag}' root must be a YAML mapping.")
    return architecture_from_data(data)


def format_snapshot_list(path: str | Path, snapshots: list[SnapshotMeta]) -> str:
    name = Path(path).name
    if not snapshots:
        return f"No snapshots for {name}."
    lines = [f"Snapshots: {name}", ""]
    for s in snapshots:
        desc = f"  {s.description}" if s.description else ""
        lines.append(f"  {s.tag:<24} {s.created_at}{desc}")
    return "\n".join(lines)
