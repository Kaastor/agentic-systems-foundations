from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from .execution import TestCaseResult


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    learner_code: SecretStr
    submitted_at: datetime


class GradeReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    passed: bool
    test_results: List[TestCaseResult]
    score: float = Field(ge=0.0, le=1.0)
    runtime_ms: int
    policy_flags: List[str] = Field(default_factory=list)
