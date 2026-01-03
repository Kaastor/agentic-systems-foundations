from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..types import AgentNode, AgentState, VerificationStatus


class RunMetrics(BaseModel):
    """Common metrics used across the VAR research testbed.

    These are intentionally simple. Theses can extend them or add new derived metrics.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    terminal_state: AgentNode
    success: bool

    regen_count: int
    attempts: int
    hints_issued: int

    tool_calls: int
    steps: int

    verified_pass: Optional[bool] = None
    last_score: Optional[float] = None
    policy_flags: List[str] = Field(default_factory=list)

    errors: int = 0


def compute_run_metrics(state: AgentState) -> RunMetrics:
    attempts = len(state.attempts)
    hints = sum(len(a.hints_used) for a in state.attempts)

    last_score = None
    policy_flags: List[str] = []
    if state.attempts and state.attempts[-1].grade is not None:
        last_score = state.attempts[-1].grade.score
        policy_flags = list(state.attempts[-1].grade.policy_flags)

    verified_pass = None
    if state.verification is not None:
        verified_pass = state.verification.status == VerificationStatus.PASS

    return RunMetrics(
        run_id=state.run_id,
        terminal_state=state.current_state,
        success=state.current_state == AgentNode.TerminalSuccess,
        regen_count=state.loop_counters.regen_count,
        attempts=attempts,
        hints_issued=hints,
        tool_calls=state.metrics.tool_calls,
        steps=state.metrics.step_count,
        verified_pass=verified_pass,
        last_score=last_score,
        policy_flags=policy_flags,
        errors=len(state.errors),
    )


def summarize_suite(metrics: List[RunMetrics]) -> Dict[str, Any]:
    if not metrics:
        return {"runs": 0}

    runs = len(metrics)
    success = sum(1 for m in metrics if m.success)
    verified = sum(1 for m in metrics if m.verified_pass)
    hints = sum(m.hints_issued for m in metrics)
    tool_calls = sum(m.tool_calls for m in metrics)
    regens = sum(m.regen_count for m in metrics)

    return {
        "runs": runs,
        "success_rate": success / runs,
        "verified_pass_rate": verified / runs,
        "mean_hints": hints / runs,
        "mean_tool_calls": tool_calls / runs,
        "mean_regens": regens / runs,
    }
