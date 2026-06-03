from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = "zephyr-result.v1"


@dataclass
class ZephyrResult:
    """Stable result type for all Zephyr runtime operations.

    Maps 1-to-1 with the zephyr-result.v1 JSON envelope returned by --json CLI flags.
    Consumers (mq-mcp, agents, scripts) should use .to_dict() for serialization
    and .ok / .failed for control flow.
    """

    status: str  # "ok" | "warning" | "error"
    command: str
    source: str | None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    artifacts: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when the operation succeeded (ok or warning)."""
        return self.status in ("ok", "warning")

    @property
    def failed(self) -> bool:
        """True when the operation failed and errors are present."""
        return self.status == "error"

    def to_dict(self) -> dict:
        """Serialize to the zephyr-result.v1 JSON envelope."""
        return {
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "data": self.data,
            "artifacts": self.artifacts,
            "metadata": {
                "command": self.command,
                "source": str(self.source) if self.source is not None else None,
                "schema_version": SCHEMA_VERSION,
            },
        }
