from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from ._time_hash import stable_hash, utc_now
from .enums import TaskType


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

    # Security-sensitive fields: never show to learners; redact in logs by default.
    reference_solution: SecretStr
    hidden_tests: SecretStr

    public_tests: Optional[str] = None
    rubric: Rubric = Field(default_factory=Rubric)


class ExerciseMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    concepts: List[str]
    difficulty: int
    seed: int
    generator_version: str
    created_at: datetime


class ExerciseArtifact(BaseModel):
    """Compiled deliverable that can be verified and graded."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    prompt_md: str
    starter_code: str

    # Security-sensitive fields: never show to learners; redact in logs by default.
    reference_solution: SecretStr
    hidden_tests: SecretStr

    public_tests: Optional[str] = None
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


def artifact_id_for(draft: ExerciseDraft, spec: ExerciseSpec) -> str:
    """Compute a stable artifact_id for a compiled artifact."""

    identity = stable_hash(
        {
            "prompt_md": draft.prompt_md,
            "starter_code": draft.starter_code,
            "reference_solution": draft.reference_solution.get_secret_value(),
            "public_tests": draft.public_tests,
            "hidden_tests": draft.hidden_tests.get_secret_value(),
            "rubric": draft.rubric.model_dump(mode="json"),
            "spec": spec.model_dump(mode="json"),
        }
    )
    return f"ex_{identity[:12]}"


def now_metadata(spec: ExerciseSpec) -> ExerciseMetadata:
    return ExerciseMetadata(
        concepts=spec.concepts,
        difficulty=spec.difficulty,
        seed=spec.seed,
        generator_version=spec.generator_version,
        created_at=utc_now(),
    )
