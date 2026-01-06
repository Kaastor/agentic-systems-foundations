from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import CheckStatus, VerificationStatus
from .execution import ExecutionReport


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
