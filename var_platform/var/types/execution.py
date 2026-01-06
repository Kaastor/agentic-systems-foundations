from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


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
