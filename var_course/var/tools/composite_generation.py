from __future__ import annotations

"""Composite generator tool.

This is a tiny but very "agentic systems" piece of infrastructure:
- multiple generators implement the same schema
- a router chooses one based on the spec

In this baseline we keep it deterministic and simple:
- try generators in order
- treat ValidationError as "not applicable" and fall through

Research extensions:
- learned router (classifier)
- per-generator quality/cost models
- A/B testing in the harness
"""

from typing import List

from ..types import ExerciseDraft, ExerciseSpec, ToolErrorCode
from .base import Tool, ToolResult


class CompositeGenerateDraftTool(Tool):
    """Try multiple generate-draft tools in order."""

    name = "exercise.generate_draft_composite"
    version = "router-v1"

    def __init__(self, generators: List[Tool]):
        if not generators:
            raise ValueError("generators must be non-empty")
        self._generators = generators

    def run(self, *, spec: ExerciseSpec) -> ToolResult[ExerciseDraft]:
        last_error = None
        for gen in self._generators:
            result = gen.run(spec=spec)
            if result.ok:
                return result
            assert result.error is not None
            # ValidationError => this generator doesn't handle that spec.
            if result.error.code == ToolErrorCode.ValidationError:
                last_error = result.error
                continue
            # Anything else => surface it (it is a real failure).
            return result
        # No generator handled it.
        if last_error is None:
            # Defensive; shouldn't happen.
            from ..types import ToolError

            return ToolResult.failure(
                ToolError(
                    code=ToolErrorCode.ValidationError,
                    retryable=False,
                    safe_message="No generator could handle this spec.",
                    debug={"spec": spec.model_dump()},
                )
            )
        return ToolResult.failure(last_error)
