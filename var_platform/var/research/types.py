from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..types import AgentNode, AgentState, SCHEMA_VERSION, ToolError, stable_hash


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ToolIOCapture(str, Enum):
    """How much tool input/output to record.

    - hash_only: record only hashes + minimal metadata.
    - safe: record structured, redacted inputs/outputs (default for publishable artifacts).
    - full: record full inputs/outputs (useful for exact replay; contains secrets).
    """

    hash_only = "hash_only"
    safe = "safe"
    full = "full"


class EnvironmentInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    python_version: str
    platform: str
    python_implementation: str

    @classmethod
    def collect(cls) -> "EnvironmentInfo":
        return cls(
            python_version=sys.version.split()[0],
            platform=f"{platform.system()}-{platform.release()} ({platform.machine()})",
            python_implementation=platform.python_implementation(),
        )


class RunManifest(BaseModel):
    """Reproducibility manifest for a single run.

    Stored alongside trace + tool I/O so experiments are replayable.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    schema_version: str = SCHEMA_VERSION
    created_at: datetime

    runtime_config: Dict[str, Any] = Field(default_factory=dict)
    tool_versions: Dict[str, str] = Field(default_factory=dict)
    generator_version: str = "unknown"

    tags: Dict[str, Any] = Field(default_factory=dict)
    environment: EnvironmentInfo = Field(default_factory=EnvironmentInfo.collect)


class ToolCallRecord(BaseModel):
    """A single tool call attempt.

    Note: one logical call may include multiple attempts if the executor retries.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    ts: datetime
    run_id: str
    state: AgentNode

    tool_name: str
    tool_version: str

    call_index: int
    args_hash: str

    attempt_index: int = 0
    latency_ms: int = 0

    ok: bool
    args: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[ToolError] = None

    # A stable fingerprint for result content (useful in hash_only/safe capture)
    result_hash: Optional[str] = None


class StateSnapshot(BaseModel):
    """A time-travel snapshot of AgentState."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ts: datetime
    run_id: str
    step_index: int

    # Stored as plain JSON so it stays stable even if AgentState evolves.
    state: Dict[str, Any]
    state_hash: str

    @classmethod
    def from_state(cls, *, run_id: str, step_index: int, state: AgentState) -> "StateSnapshot":
        payload = state.model_dump(mode="json")
        return cls(
            ts=utc_now(),
            run_id=run_id,
            step_index=step_index,
            state=payload,
            state_hash=stable_hash(payload),
        )


class RunBundle(BaseModel):
    """A fully exportable bundle for offline analysis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest: RunManifest
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    state_snapshots: List[StateSnapshot] = Field(default_factory=list)
