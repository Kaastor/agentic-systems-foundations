from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ._time_hash import SCHEMA_VERSION
from .enums import AgentNode, PresentationKind
from .exercise import ExerciseSpec, ExerciseView
from .grading import GradeReport, Submission
from .hints import HintArtifact, HintPolicy
from .outcome import Outcome
from .verification import VerificationReport


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
    latency_ms: int = 0

    # Best-effort, string-keyed snapshots from BudgetManager.
    # These are optional because budgets may be disabled.
    budget_used: Dict[str, int] = Field(default_factory=dict)
    budget_limits: Dict[str, int] = Field(default_factory=dict)


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

    # Domain outcomes
    verification: Optional[Outcome[VerificationReport]] = None

    attempts: List[AttemptRecord] = Field(default_factory=list)

    # Pending presentation (anything user-facing goes through the gate)
    pending_presentation_kind: Optional[PresentationKind] = None
    pending_exercise_view: Optional[ExerciseView] = None
    pending_grade: Optional[GradeReport] = None
    pending_hint: Optional[HintArtifact] = None
    post_presentation_state: Optional[AgentNode] = None

    loop_counters: LoopCounters = Field(default_factory=LoopCounters)
    policy: HintPolicy = Field(default_factory=HintPolicy)
    metrics: AgentMetrics = Field(default_factory=AgentMetrics)
    errors: List[Any] = Field(default_factory=list)  # ToolError | AgentError

    versions: AgentVersions = Field(default_factory=AgentVersions)

    def add_tool_repeat(self, key: str) -> None:
        self.loop_counters.tool_repeat_counts[key] = self.loop_counters.tool_repeat_counts.get(key, 0) + 1

    def tool_repeat_count(self, key: str) -> int:
        return self.loop_counters.tool_repeat_counts.get(key, 0)
