from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from ..types import ExerciseSpec


@dataclass(frozen=True)
class Scenario:
    name: str
    spec: ExerciseSpec
    submission_sequence: List[str]  # code per attempt


def _missing_function_stub(spec: ExerciseSpec) -> str:
    """Return a submission that parses but does NOT define the required function."""
    # Define a different top-level function name.
    fn = spec.signature.name
    return (
        "def not_the_right_function(*args, **kwargs):\n"
        "    return None\n"
        f"\n# Expected function name was: {fn}\n"
    )


def _timeout_stub(spec: ExerciseSpec) -> str:
    """Return a submission that times out when the function is called."""
    fn = spec.signature.name
    # Keep the signature loose to avoid type headaches; hidden tests will still call it.
    return (
        f"def {fn}(*args, **kwargs):\n"
        "    while True:\n"
        "        pass\n"
    )


def scenario_matrix(specs: Sequence[ExerciseSpec], solutions: Dict[str, str]) -> List[Scenario]:
    """Create a deterministic suite of scenarios from a catalog of specs.

    `solutions` maps function name -> correct full code string for that exercise.

    Baseline suite goal: a shared, deterministic set of scenarios that *all pass*.
    This keeps CI stable while still exercising key agent behaviors.
    """
    scenarios: List[Scenario] = []

    for s in specs:
        fn = s.signature.name
        sol = solutions[fn]

        # 1) Perfect learner: submits correct solution immediately.
        scenarios.append(Scenario(name=f"{fn}::perfect", spec=s, submission_sequence=[sol]))

        # 2) Syntax error then fix.
        scenarios.append(
            Scenario(
                name=f"{fn}::syntax_then_fix",
                spec=s,
                submission_sequence=[
                    sol.replace(":\n", "\n", 1),  # remove first colon after def -> SyntaxError
                    sol,
                ],
            )
        )

        # 3) Wrong answer then fix (simple mutation).
        if fn == "reverse_string":
            wrong = "def reverse_string(s: str) -> str:\n    return s\n"
        elif fn == "count_vowels":
            wrong = "def count_vowels(text: str) -> int:\n    return 0\n"
        elif fn == "is_prime":
            wrong = "def is_prime(n: int) -> bool:\n    return n % 2 == 1\n"
        elif fn == "fizzbuzz":
            wrong = "def fizzbuzz(n: int) -> list[str]:\n    return [str(i) for i in range(1, n+1)]\n"
        elif fn == "flatten":
            wrong = "def flatten(list_of_lists: list[list[int]]) -> list[int]:\n    return list_of_lists  # wrong shape\n"
        else:
            wrong = sol
        scenarios.append(Scenario(name=f"{fn}::wrong_then_fix", spec=s, submission_sequence=[wrong, sol]))

        # 4) Forbidden import (policy test) then fix.
        forbidden = "import os\n" + sol
        scenarios.append(Scenario(name=f"{fn}::forbidden_import_then_fix", spec=s, submission_sequence=[forbidden, sol]))

        # 5) Missing required function then fix.
        scenarios.append(
            Scenario(
                name=f"{fn}::missing_function_then_fix",
                spec=s,
                submission_sequence=[_missing_function_stub(s), sol],
            )
        )

        # 6) Timeout then fix (simulated infinite loop).
        scenarios.append(
            Scenario(
                name=f"{fn}::timeout_then_fix",
                spec=s,
                submission_sequence=[_timeout_stub(s), sol],
            )
        )

    return scenarios
