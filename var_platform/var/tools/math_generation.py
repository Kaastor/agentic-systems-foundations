from __future__ import annotations

"""Deterministic generator for arithmetic practice.

Design goal: reuse the *same* kernel (sandbox verification, grading, hint policy)
for non-programming homeschool tasks.

How?
- We still compile a Python exercise artifact.
- The learner submits a *number* (via a homeschool UI).
- The UI wraps the number into a tiny function body.

This keeps the invariant (verify before present) and the research harness intact,
while giving you a path to add more homeschool domains later (spelling, logic, etc.).
"""

import random
from dataclasses import dataclass
from typing import List, Optional

from ..types import (
    Constraints,
    ExerciseDraft,
    ExerciseSpec,
    Rubric,
    SignatureSpec,
    TaskType,
    ToolError,
    ToolErrorCode,
)
from .base import Tool, ToolResult


@dataclass(frozen=True)
class _Problem:
    a: int
    b: int
    op: str  # '+', '-', '*'

    @property
    def answer(self) -> int:
        if self.op == '+':
            return self.a + self.b
        if self.op == '-':
            return self.a - self.b
        if self.op == '*':
            return self.a * self.b
        raise ValueError(f"unknown op {self.op}")


def _make_problem(*, seed: int, difficulty: int, op: str) -> _Problem:
    rng = random.Random(seed)
    # Difficulty controls range and presence of negatives.
    if difficulty <= 1:
        lo, hi = 0, 20
    elif difficulty == 2:
        lo, hi = 0, 100
    elif difficulty == 3:
        lo, hi = -50, 200
    elif difficulty == 4:
        lo, hi = -200, 500
    else:
        lo, hi = -500, 2000

    a = rng.randint(lo, hi)
    b = rng.randint(lo, hi)

    # Keep multiplication sane for small kids
    if op == '*':
        a = rng.randint(0, max(5, abs(hi) // 20))
        b = rng.randint(0, max(5, abs(hi) // 20))

    return _Problem(a=a, b=b, op=op)


def arithmetic_problem(*, seed: int, difficulty: int, op: str) -> tuple[int, int, str, int]:
    """Return a deterministic arithmetic problem tuple.

    Exposed for reuse in evaluation harnesses and content tooling.
    """

    p = _make_problem(seed=seed, difficulty=difficulty, op=op)
    return p.a, p.b, p.op, p.answer


def available_math_specs(seed: int = 0, generator_version: str = "math-v1") -> List[ExerciseSpec]:
    """Return a small bank of arithmetic specs.

    This is intentionally tiny in v0.2 — it’s a scaffold for building a larger
    homeschool content pack.
    """

    base_constraints = Constraints(forbidden_imports=["os", "subprocess", "socket"], max_runtime_ms=500, max_memory_mb=128)

    def spec_for(name: str, concepts: List[str], difficulty: int) -> ExerciseSpec:
        sig = SignatureSpec(name=name, args=[], returns="int")
        return ExerciseSpec(
            concepts=concepts,
            difficulty=difficulty,
            task_type=TaskType.function_implementation,
            signature=sig,
            constraints=base_constraints,
            seed=seed,
            generator_version=generator_version,
        )

    return [
        spec_for("answer_add", ["arithmetic", "addition"], 1),
        spec_for("answer_sub", ["arithmetic", "subtraction"], 2),
        spec_for("answer_mul", ["arithmetic", "multiplication"], 2),
    ]


class MathGenerateDraftTool(Tool):
    """Generate arithmetic exercises as Python artifacts."""

    name = "exercise.generate_draft_math"
    version = "math-gen-v1"

    def __init__(self, *, op_map: Optional[dict[str, str]] = None):
        # Map function name -> op symbol.
        self._op_map = op_map or {
            "answer_add": "+",
            "answer_sub": "-",
            "answer_mul": "*",
        }

    def run(self, *, spec: ExerciseSpec) -> ToolResult[ExerciseDraft]:
        fn = spec.signature.name
        op = self._op_map.get(fn)
        if not op:
            from ..types import ToolError, ToolErrorCode

            return ToolResult.failure(
                ToolError(
                    code=ToolErrorCode.ValidationError,
                    retryable=False,
                    safe_message="Unknown math exercise signature.",
                    debug={"fn": fn},
                )
            )

        prob = _make_problem(seed=spec.seed, difficulty=spec.difficulty, op=op)
        expected = prob.answer

        prompt_md = (
            f"## Quick math\n\n"
            f"Compute: **{prob.a} {op} {prob.b}**\n\n"
            f"Write a function `{fn}() -> int` that returns the answer.\n\n"
            f"*(Homeschool mode lets learners type just the number; the system wraps it into code.)*\n"
        )

        starter_code = f"def {fn}() -> int:\n    \"\"\"Return the result of {prob.a} {op} {prob.b}.\"\"\"\n    # TODO: replace with your answer\n    raise NotImplementedError\n"

        reference_solution = f"def {fn}() -> int:\n    return {expected}\n"

        hidden_tests = (
            "import unittest\n"
            "import solution\n\n"
            "class TestMath(unittest.TestCase):\n"
            f"    def test_answer(self):\n        self.assertEqual(solution.{fn}(), {expected})\n"
            f"    def test_type(self):\n        self.assertIsInstance(solution.{fn}(), int)\n\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n"
        )

        rubric = Rubric(criteria=["Returns the correct integer answer."])

        return ToolResult.success(
            ExerciseDraft(
                prompt_md=prompt_md,
                starter_code=starter_code,
                reference_solution=reference_solution,
                public_tests=None,
                hidden_tests=hidden_tests,
                rubric=rubric,
            )
        )
