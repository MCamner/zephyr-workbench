"""Zephyr tool safety contracts.

Defines which operations are read-only versus write-creating, and what
safety guarantees each carries. Consumed by mq-mcp and other callers
that need to classify tools before exposing them to agents.

Read-only tools:  safe to call freely, no side effects
Write-creating:   write only the files documented for each operation
Forbidden:        must not be called autonomously (interactive or destructive)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Safety = Literal["read-only", "write-creating", "forbidden"]


@dataclass(frozen=True)
class ToolContract:
    name: str
    safety: Safety
    description: str
    idempotent: bool
    json_supported: bool


TOOLS: dict[str, ToolContract] = {
    "validate": ToolContract(
        name="validate",
        safety="read-only",
        description="Validate an architecture YAML model. No file writes.",
        idempotent=True,
        json_supported=True,
    ),
    "summary": ToolContract(
        name="summary",
        safety="read-only",
        description="Return a structured summary of a model. No file writes.",
        idempotent=True,
        json_supported=True,
    ),
    "diagram_stdout": ToolContract(
        name="diagram_stdout",
        safety="read-only",
        description="Render a diagram to stdout or artifact content. No file writes.",
        idempotent=True,
        json_supported=True,
    ),
    "diagram_file": ToolContract(
        name="diagram_file",
        safety="write-creating",
        description="Render a diagram and write to an explicit output path.",
        idempotent=True,
        json_supported=True,
    ),
    "diff": ToolContract(
        name="diff",
        safety="read-only",
        description="Compare two architecture models. No file writes.",
        idempotent=True,
        json_supported=True,
    ),
    "search": ToolContract(
        name="search",
        safety="read-only",
        description="Filter model elements by field value. No file writes.",
        idempotent=True,
        json_supported=True,
    ),
    "lifecycle": ToolContract(
        name="lifecycle",
        safety="read-only",
        description="Analyse component lifecycle states. No file writes.",
        idempotent=True,
        json_supported=True,
    ),
    "report_stdout": ToolContract(
        name="report_stdout",
        safety="read-only",
        description="Generate review report to artifact content. No file writes.",
        idempotent=True,
        json_supported=True,
    ),
    "report_file": ToolContract(
        name="report_file",
        safety="write-creating",
        description="Generate review report and write to an explicit output path.",
        idempotent=True,
        json_supported=True,
    ),
    "score": ToolContract(
        name="score",
        safety="read-only",
        description="Compute multi-dimensional quality score. No file writes.",
        idempotent=True,
        json_supported=True,
    ),
    "run": ToolContract(
        name="run",
        safety="write-creating",
        description="Validate + summarize + write diagram to output dir.",
        idempotent=True,
        json_supported=False,
    ),
    "init": ToolContract(
        name="init",
        safety="forbidden",
        description="Interactive wizard to create a new model. Not safe for autonomous calls.",
        idempotent=False,
        json_supported=False,
    ),
    "add": ToolContract(
        name="add",
        safety="forbidden",
        description="Interactive wizard to add items to a model. Not safe for autonomous calls.",
        idempotent=False,
        json_supported=False,
    ),
}

# Keep every runtime surface classified; destructive operations stay forbidden.
for _name in (
    "analyze",
    "review",
    "explain",
    "govern",
    "impact",
    "history",
    "snapshot_list",
    "snapshot_diff",
    "snapshot_impact",
    "memory_list",
    "memory_search",
    "memory_compare",
    "review_templates",
    "import_stdout",
):
    TOOLS[_name] = ToolContract(
        _name, "read-only", "Return structured results without writes.", True, True
    )
for _name, _description in {
    "import_file": "Write an imported YAML model to an explicit output path.",
    "snapshot_save": "Copy a model and update its snapshot index (two files).",
    "memory_add": "Create or update the local memory index.",
    "memory_refresh": "Reindex changed sources in the local memory index.",
    "memory_remove": "Remove an entry from the local memory index.",
}.items():
    TOOLS[_name] = ToolContract(
        _name,
        "write-creating",
        _description,
        _name not in {"snapshot_save", "memory_add", "memory_remove"},
        True,
    )
TOOLS["snapshot_delete"] = ToolContract(
    "snapshot_delete",
    "forbidden",
    "Delete a snapshot and update its index; requires explicit destructive intent.",
    False,
    True,
)

READ_ONLY = {k: v for k, v in TOOLS.items() if v.safety == "read-only"}
WRITE_CREATING = {k: v for k, v in TOOLS.items() if v.safety == "write-creating"}
FORBIDDEN = {k: v for k, v in TOOLS.items() if v.safety == "forbidden"}


def is_safe_for_agents(tool_name: str) -> bool:
    """Return True if a tool may be called autonomously by an agent."""
    contract = TOOLS.get(tool_name)
    return contract is not None and contract.safety in ("read-only", "write-creating")


def requires_write_intent(tool_name: str) -> bool:
    """Return True if the tool writes files and needs explicit caller authorization."""
    contract = TOOLS.get(tool_name)
    return contract is not None and contract.safety == "write-creating"
