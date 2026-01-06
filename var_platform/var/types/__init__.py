"""Typed data model for VAR.

This package is intentionally split into small, teachable modules:
- `exercise` for artifacts/specs
- `verification` / `grading` for outcomes
- `state` for runtime state
- `enums` for shared enums

All names are re-exported here for ergonomic imports (`from var.types import ...`).
"""

from ._time_hash import SCHEMA_VERSION, stable_hash, utc_now
from .enums import (
    AgentNode,
    CheckStatus,
    OutcomeKind,
    PresentationKind,
    TaskType,
    ToolErrorCode,
    TraceEventType,
    VerificationStatus,
)
from .exercise import (
    ArgSpec,
    Constraints,
    ExerciseArtifact,
    ExerciseDraft,
    ExerciseMetadata,
    ExerciseSpec,
    ExerciseView,
    Rubric,
    SignatureSpec,
    artifact_id_for,
    now_metadata,
)
from .execution import ExecutionLimits, ExecutionReport, TestCaseResult
from .grading import GradeReport, Submission
from .hints import HintArtifact, HintPolicy
from .outcome import Outcome
from .tooling import ToolError
from .tracing import TraceEvent
from .verification import VerificationCheck, VerificationReport
from .state import AttemptRecord, AgentError, AgentMetrics, AgentState, AgentVersions, LoopCounters

__all__ = [
    # Core helpers
    "SCHEMA_VERSION",
    "utc_now",
    "stable_hash",

    # Enums
    "TaskType",
    "VerificationStatus",
    "CheckStatus",
    "ToolErrorCode",
    "OutcomeKind",
    "PresentationKind",
    "AgentNode",
    "TraceEventType",

    # Outcomes
    "Outcome",

    # Exercise artifacts
    "ArgSpec",
    "SignatureSpec",
    "Constraints",
    "ExerciseSpec",
    "Rubric",
    "ExerciseDraft",
    "ExerciseMetadata",
    "ExerciseArtifact",
    "ExerciseView",
    "artifact_id_for",
    "now_metadata",

    # Execution
    "ExecutionLimits",
    "TestCaseResult",
    "ExecutionReport",

    # Verification / grading
    "VerificationCheck",
    "VerificationReport",
    "Submission",
    "GradeReport",

    # Hints
    "HintPolicy",
    "HintArtifact",

    # Tool boundary
    "ToolError",

    # Tracing
    "TraceEvent",

    # Agent state
    "AttemptRecord",
    "LoopCounters",
    "AgentMetrics",
    "AgentVersions",
    "AgentError",
    "AgentState",
]
