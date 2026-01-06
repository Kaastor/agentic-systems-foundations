from __future__ import annotations

from ..base import Tool, ToolResult
from ...types import ExerciseView, Outcome, OutcomeKind


class GateExerciseViewTool(Tool):
    """Universal presentation gate for ExerciseView.

    ExerciseView is already redacted, but we still scan for common leakage markers to
    prevent accidental mistakes.
    """

    name = "present.gate_exercise_view"
    version = "present-gate-v1"

    def run(self, *, view: ExerciseView) -> ToolResult[Outcome[ExerciseView]]:
        combined = f"{view.prompt_md}\n\n{view.starter_code}\n\n{view.public_tests or ''}"
        forbidden_markers = ["hidden_tests", "reference_solution", "__HIDDEN__", "__SOLUTION__"]
        if any(m in combined for m in forbidden_markers):
            return ToolResult.success(
                Outcome.fail(
                    kind=OutcomeKind.PolicyViolation,
                    value=None,
                    reason="exercise_view_contains_forbidden_markers",
                    details={"markers": [m for m in forbidden_markers if m in combined]},
                )
            )
        return ToolResult.success(Outcome.ok(view))
