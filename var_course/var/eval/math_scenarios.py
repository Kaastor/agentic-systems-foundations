from __future__ import annotations

from typing import Dict, List, Sequence

from ..types import ExerciseSpec
from ..tools.math_generation import arithmetic_problem
from .scenarios import Scenario, _missing_function_stub, _timeout_stub


def math_scenario_matrix(specs: Sequence[ExerciseSpec]) -> List[Scenario]:
    """Scenarios for arithmetic specs.

    These mirror the general scenario families used for coding tasks, but the
    "solutions" are trivial (return the expected integer).

    Useful as:
    - a baseline harness for homeschool mode
    - a cheap sanity check for verification/grading determinism
    """

    op_map = {
        "answer_add": "+",
        "answer_sub": "-",
        "answer_mul": "*",
    }

    scenarios: List[Scenario] = []

    for s in specs:
        fn = s.signature.name
        op = op_map.get(fn)
        if not op:
            continue

        a, b, _, expected = arithmetic_problem(seed=s.seed, difficulty=s.difficulty, op=op)

        sol = f"def {fn}() -> int:\n    return {expected}\n"
        wrong = f"def {fn}() -> int:\n    return {expected + 1}\n"

        # 1) Perfect learner
        scenarios.append(Scenario(name=f"{fn}::{a}{op}{b}::perfect", spec=s, submission_sequence=[sol]))

        # 2) Wrong then fix
        scenarios.append(Scenario(name=f"{fn}::{a}{op}{b}::wrong_then_fix", spec=s, submission_sequence=[wrong, sol]))

        # 3) Syntax error then fix
        scenarios.append(
            Scenario(
                name=f"{fn}::{a}{op}{b}::syntax_then_fix",
                spec=s,
                submission_sequence=[sol.replace(":\n", "\n", 1), sol],
            )
        )

        # 4) Forbidden import then fix
        scenarios.append(
            Scenario(
                name=f"{fn}::{a}{op}{b}::forbidden_import_then_fix",
                spec=s,
                submission_sequence=["import os\n" + sol, sol],
            )
        )

        # 5) Missing function then fix
        scenarios.append(
            Scenario(
                name=f"{fn}::{a}{op}{b}::missing_function_then_fix",
                spec=s,
                submission_sequence=[_missing_function_stub(s), sol],
            )
        )

        # 6) Timeout then fix
        scenarios.append(
            Scenario(
                name=f"{fn}::{a}{op}{b}::timeout_then_fix",
                spec=s,
                submission_sequence=[_timeout_stub(s), sol],
            )
        )

    return scenarios
