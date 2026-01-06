from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from .budgets.types import BudgetCategory, BudgetLimits
from .research.types import ToolIOCapture


@dataclass(frozen=True)
class ToolRetryConfig:
    """Executor-level retry policy for *retryable* ToolErrors.

    This is intentionally small and explicit so students can swap strategies and compare them
    in the evaluation harness.
    """

    max_retries: int = 1
    retry_backoff_ms: int = 0


@dataclass(frozen=True)
class ResearchConfig:
    """Optional 'research mode' knobs.

    When enabled, the runtime records enough metadata for reproducible experiments:

    - a RunManifest (versions + environment + config)
    - tool call records (optionally redacted)
    - AgentState snapshots (time-travel + resume)
    """

    enabled: bool = False

    # Tool I/O capture (for replay/debugging). Defaults to 'safe' for publishability.
    record_tool_io: bool = True
    tool_io_capture: ToolIOCapture = ToolIOCapture.safe
    redact_tool_io: bool = True

    # State snapshots (for crash/restart experiments).
    record_state_snapshots: bool = True
    snapshot_every_n_steps: int = 1

    # Synthetic crash injection hook (used only by eval harness / experiments).
    crash_after_step: Optional[int] = None

    # Free-form labels useful for experiments (scenario name, cohort, etc.).
    tags: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeConfig:
    max_steps: int = 50
    max_regenerations_per_spec: int = 3
    max_attempts: int = 5
    verification_repeats: int = 2

    # Loop detection: if the same tool call fails this many times, force a change.
    max_repeated_tool_failures: int = 2

    # Retry policy for retryable tool errors (transient failures, timeouts, conflicts).
    tool_retry: ToolRetryConfig = field(default_factory=ToolRetryConfig)

    # Research-mode recording and fault injection hooks.
    research: ResearchConfig = field(default_factory=ResearchConfig)

    # Optional spend budgets (tokens, tool calls, sandbox time, etc.).
    budgets: "BudgetConfig" = field(default_factory=lambda: BudgetConfig())


@dataclass(frozen=True)
class BudgetConfig:
    """Optional runtime budgets.

    Budgets are a separate concept from loop bounds. They allow you to cap resources
    (tool calls, latency, model tokens, sandbox time) regardless of how many steps
    you allow.
    """

    enabled: bool = False
    limits: BudgetLimits = field(default_factory=BudgetLimits)

    @staticmethod
    def from_simple(
        *,
        enabled: bool,
        max_tool_calls: Optional[int] = None,
        max_tool_latency_ms: Optional[int] = None,
        max_model_total_tokens: Optional[int] = None,
        max_sandbox_runtime_ms: Optional[int] = None,
    ) -> "BudgetConfig":
        limits: Dict[BudgetCategory, int] = {}
        if max_tool_calls is not None:
            limits[BudgetCategory.tool_calls] = int(max_tool_calls)
        if max_tool_latency_ms is not None:
            limits[BudgetCategory.tool_latency_ms] = int(max_tool_latency_ms)
        if max_model_total_tokens is not None:
            limits[BudgetCategory.model_total_tokens] = int(max_model_total_tokens)
        if max_sandbox_runtime_ms is not None:
            limits[BudgetCategory.sandbox_runtime_ms] = int(max_sandbox_runtime_ms)
        return BudgetConfig(enabled=enabled, limits=BudgetLimits(limits=limits))


@dataclass(frozen=True)
class StorageConfig:
    root_dir: Path
