from __future__ import annotations

from typing import Optional

from ..base import Tool, ToolResult
from ...types import HintArtifact, HintPolicy, Outcome, OutcomeKind
from ._helpers import contains_disallowed_solution_like_code


class GateHintTool(Tool):
    """Presentation gate for hints (prevents solution leakage by policy)."""

    name = "present.gate_hint"
    version = "present-gate-v1"

    def run(self, *, hint: HintArtifact, policy: HintPolicy, expected_fn: Optional[str] = None) -> ToolResult[Outcome[HintArtifact]]:
        if not policy.allow_solution_reveal and hint.reveals_solution:
            return ToolResult.success(
                Outcome.fail(kind=OutcomeKind.PolicyViolation, value=None, reason="hint_reveals_solution_flag")
            )

        for bad_key in ("reference_solution", "hidden_tests", "learner_code"):
            if bad_key in hint.based_on:
                return ToolResult.success(
                    Outcome.fail(
                        kind=OutcomeKind.PolicyViolation,
                        value=None,
                        reason="hint_metadata_leak",
                        details={"key": bad_key},
                    )
                )

        if (
            not policy.allow_solution_reveal
            and contains_disallowed_solution_like_code(hint.hint_md, fn_name=expected_fn)
        ):
            return ToolResult.success(
                Outcome.fail(
                    kind=OutcomeKind.PolicyViolation,
                    value=None,
                    reason="hint_contains_solution_like_code",
                    details={"expected_fn": expected_fn or "unknown"},
                )
            )

        return ToolResult.success(Outcome.ok(hint))
