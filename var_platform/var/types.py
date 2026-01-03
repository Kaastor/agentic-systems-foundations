from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


SCHEMA_VERSION = "v0.1"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stable_hash(obj: Any) -> str:
    """Compute a stable SHA-256 hash for JSON-serializable content.

    Used for tool args hashing and artifact identity.
    """
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ----------------------------
# Enums
# ----------------------------

class TaskType(str, Enum):
    function_implementation = "function_implementation"
    bugfix = "bugfix"
    refactor = "refactor"
    complexity = "complexity"


class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class ToolErrorCode(str, Enum):
    ValidationError = "ValidationError"
    TransientError = "TransientError"
    PermanentError = "PermanentError"
    SandboxViolation = "SandboxViolation"
    Timeout = "Timeout"
    Conflict = "Conflict"


class AgentNode(str, Enum):
    SelectSpec = "SelectSpec"
    GenerateExercise = "GenerateExercise"
    VerifyExercise = "VerifyExercise"
    RepairOrRegenerate = "RepairOrRegenerate"
    PresentExercise = "PresentExercise"
    AwaitSubmission = "AwaitSubmission"
    GradeSubmission = "GradeSubmission"
    ProduceHintOrFeedback = "ProduceHintOrFeedback"
    SummarizeAndLog = "SummarizeAndLog"
    TerminalSuccess = "TerminalSuccess"
    TerminalFailure = "TerminalFailure"


# ----------------------------
# Core data model
# ----------------------------

class ArgSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    type: str


class SignatureSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    args: List[ArgSpec]
    returns: str


class Constraints(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    forbidden_imports: List[str] = Field(default_factory=list)
    max_runtime_ms: int = Field(default=800, ge=50, le=10_000)
    max_memory_mb: int = Field(default=256, ge=64, le=2048)


class ExerciseSpec(BaseModel):
    """High-level input intent for an exercise."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    concepts: List[str] = Field(default_factory=list, min_length=1)
    difficulty: int = Field(ge=1, le=5)
    task_type: TaskType
    signature: SignatureSpec
    constraints: Constraints = Field(default_factory=Constraints)
    seed: int = Field(ge=0, le=2**31 - 1)
    generator_version: str = Field(default="template-v1")

    @field_validator("concepts")
    @classmethod
    def _no_empty_concepts(cls, v: List[str]) -> List[str]:
        cleaned = [c.strip() for c in v if c.strip()]
        if not cleaned:
            raise ValueError("concepts must contain at least one non-empty string")
        return cleaned


class Rubric(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    criteria: List[str] = Field(default_factory=list)


class ExerciseDraft(BaseModel):
    """Intermediate artifact produced by generation prior to compilation."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_md: str
    starter_code: str
    reference_solution: str
    public_tests: Optional[str] = None
    hidden_tests: str
    rubric: Rubric = Field(default_factory=Rubric)


class ExerciseMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    concepts: List[str]
    difficulty: int
    seed: int
    generator_version: str
    created_at: datetime


class ExerciseArtifact(BaseModel):
    """Compiled deliverable that can be verified and graded.

    NOTE: `reference_solution` and `hidden_tests` are *secure* fields and must never be shown to learners.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    prompt_md: str
    starter_code: str
    reference_solution: str
    public_tests: Optional[str] = None
    hidden_tests: str
    rubric: Rubric = Field(default_factory=Rubric)
    metadata: ExerciseMetadata

    def view_for_learner(self) -> "ExerciseView":
        return ExerciseView(
            artifact_id=self.artifact_id,
            prompt_md=self.prompt_md,
            starter_code=self.starter_code,
            public_tests=self.public_tests,
            metadata=self.metadata,
        )


class ExerciseView(BaseModel):
    """Redacted artifact view safe to show to learners."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    prompt_md: str
    starter_code: str
    public_tests: Optional[str] = None
    metadata: ExerciseMetadata


class ExecutionLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_runtime_ms: int = Field(default=800, ge=50, le=10_000)
    max_memory_mb: int = Field(default=256, ge=64, le=2048)
    max_output_chars: int = Field(default=20_000, ge=1000, le=200_000)


class TestCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    test_name: str
    passed: bool
    error_type: Optional[str] = None
    sanitized_trace: Optional[str] = None


class ExecutionReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    passed: bool
    runtime_ms: int
    stdout: str
    stderr: str
    test_results: List[TestCaseResult]
    timeout: bool = False
    sandbox_violation: bool = False
    returncode: int = 0


class VerificationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    status: CheckStatus
    details: str = ""


class VerificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    status: VerificationStatus
    checks: List[VerificationCheck] = Field(default_factory=list)
    execution_reports: List[ExecutionReport] = Field(default_factory=list)
    failure_reason: Optional[str] = None
    repair_hint: Optional[str] = None


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    learner_code: str
    submitted_at: datetime


class GradeReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    passed: bool
    test_results: List[TestCaseResult]
    score: float = Field(ge=0.0, le=1.0)
    runtime_ms: int
    policy_flags: List[str] = Field(default_factory=list)


class HintPolicy(BaseModel):
    """Controls what the tutor is allowed to reveal."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    allow_solution_reveal: bool = False
    max_hint_level: int = Field(default=4, ge=1, le=10)


class HintArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    level: int
    hint_md: str
    reveals_solution: bool = False
    based_on: Dict[str, Any] = Field(default_factory=dict)


# ----------------------------
# Tool errors (tool boundary contract)
# ----------------------------

class ToolError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ToolErrorCode
    retryable: bool
    safe_message: str
    debug: Dict[str, Any] = Field(default_factory=dict)


# ----------------------------
# Tracing
# ----------------------------

class TraceEventType(str, Enum):
    state_entered = "state_entered"
    tool_called = "tool_called"
    tool_result = "tool_result"
    verification_status = "verification_status"
    grade_status = "grade_status"
    hint_issued = "hint_issued"
    terminal_outcome = "terminal_outcome"


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ts: datetime
    run_id: str
    event_type: TraceEventType
    state: AgentNode
    details: Dict[str, Any] = Field(default_factory=dict)


# ----------------------------
# Agent state
# ----------------------------

class AttemptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission: Submission
    grade: Optional[GradeReport] = None
    hints_used: List[HintArtifact] = Field(default_factory=list)


class LoopCounters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regen_count: int = 0
    tool_repeat_counts: Dict[str, int] = Field(default_factory=dict)


class AgentMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_count: int = 0
    tool_calls: int = 0
    latency_ms: int = 0  # coarse wall time proxy for the whole run (best-effort)


class AgentVersions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    tool_versions: Dict[str, str] = Field(default_factory=dict)
    generator_version: str = "unknown"


class AgentError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    current_state: AgentNode = AgentNode.SelectSpec

    spec: Optional[ExerciseSpec] = None
    artifact_id: Optional[str] = None
    verification: Optional[VerificationReport] = None

    attempts: List[AttemptRecord] = Field(default_factory=list)

    loop_counters: LoopCounters = Field(default_factory=LoopCounters)
    policy: HintPolicy = Field(default_factory=HintPolicy)
    metrics: AgentMetrics = Field(default_factory=AgentMetrics)
    errors: List[Any] = Field(default_factory=list)  # ToolError | AgentError

    versions: AgentVersions = Field(default_factory=AgentVersions)

    def add_tool_repeat(self, key: str) -> None:
        self.loop_counters.tool_repeat_counts[key] = self.loop_counters.tool_repeat_counts.get(key, 0) + 1

    def tool_repeat_count(self, key: str) -> int:
        return self.loop_counters.tool_repeat_counts.get(key, 0)
