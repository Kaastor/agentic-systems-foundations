from __future__ import annotations

from ..base import Tool, ToolResult
from ...types import GradeReport, Outcome, OutcomeKind


class GateGradeReportTool(Tool):
    """Presentation gate for grades (prevents accidental trace leakage)."""

    name = "present.gate_grade_report"
    version = "present-gate-v1"

    def run(self, *, grade: GradeReport) -> ToolResult[Outcome[GradeReport]]:
        for tr in grade.test_results:
            if tr.sanitized_trace and ("hidden_tests" in tr.sanitized_trace or "__HIDDEN__" in tr.sanitized_trace):
                return ToolResult.success(
                    Outcome.fail(kind=OutcomeKind.PolicyViolation, value=None, reason="grade_trace_leakage")
                )
        return ToolResult.success(Outcome.ok(grade))
