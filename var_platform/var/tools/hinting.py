from __future__ import annotations

import ast
from typing import Dict, Optional

from ..store.exercise_store import ExerciseStore
from ..types import GradeReport, HintArtifact, HintPolicy
from .base import Tool, ToolResult


def _first_top_level_function_name(code: str) -> Optional[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return node.name
    return None


_HINTS: Dict[str, Dict[int, str]] = {
    "reverse_string": {
        1: "Think of the string as a sequence of characters. Your job is to return them in reverse order.",
        2: "In Python, slicing can reverse sequences. Alternatively, loop from the end to the start.",
        3: "Pseudocode: initialize empty output; iterate characters from last index down to 0; append each; return output.",
        4: "Skeleton:\n\n```python\ndef reverse_string(s: str) -> str:\n    # Option A: build manually\n    out = []\n    for i in range(len(s) - 1, -1, -1):\n        out.append(s[i])\n    return \"\".join(out)\n```",
    },
    "count_vowels": {
        1: "You need to count letters that are in the set {a,e,i,o,u}. Case shouldn't matter.",
        2: "Try lowercasing the string once, then counting characters that are vowels.",
        3: "Pseudocode: vowels = {'a','e','i','o','u'}; count=0; for ch in lower(text): if ch in vowels: count++ ; return count.",
        4: "Skeleton:\n\n```python\ndef count_vowels(text: str) -> int:\n    vowels = set(\"aeiou\")\n    count = 0\n    for ch in text.lower():\n        if ch in vowels:\n            count += 1\n    return count\n```",
    },
    "is_prime": {
        1: "A prime is > 1 and divisible only by 1 and itself. Start by handling small/negative inputs cleanly.",
        2: "You only need to check divisors up to sqrt(n). If any divisor divides evenly, it's not prime.",
        3: "Pseudocode: if n<=1 return False; for d from 2 to floor(sqrt(n)): if n%d==0 return False; return True.",
        4: "Skeleton:\n\n```python\ndef is_prime(n: int) -> bool:\n    if n <= 1:\n        return False\n    d = 2\n    while d * d <= n:\n        if n % d == 0:\n            return False\n        d += 1\n    return True\n```",
    },
    "fizzbuzz": {
        1: "You’re mapping each integer i in 1..n to a string based on divisibility rules.",
        2: "Check the 'both 3 and 5' case first (divisible by 15), then 3, then 5.",
        3: "Pseudocode: out=[]; for i=1..n: if i%15==0: append FizzBuzz; elif i%3==0: append Fizz; elif i%5==0: append Buzz; else append str(i).",
        4: "Skeleton:\n\n```python\ndef fizzbuzz(n: int) -> list[str]:\n    out = []\n    for i in range(1, n + 1):\n        # TODO: choose label based on divisibility\n        out.append(str(i))\n    return out\n```",
    },
    "flatten": {
        1: "You’re taking a list of lists and producing one list with all inner elements, in order.",
        2: "Use a nested loop: for each inner list, append its elements into an output list.",
        3: "Pseudocode: out=[]; for inner in list_of_lists: for x in inner: out.append(x); return out.",
        4: "Skeleton:\n\n```python\ndef flatten(list_of_lists: list[list[int]]) -> list[int]:\n    out: list[int] = []\n    for inner in list_of_lists:\n        for x in inner:\n            out.append(x)\n    return out\n```",
    },
    # Homeschool arithmetic tasks (still compiled into Python under the hood).
    "answer_add": {
        1: "This is plain addition: add the two numbers in the question.",
        2: "Try doing it column-style if it's large. Watch carries.",
        3: "Double-check the sign (+/-) and that you didn't swap digits.",
    },
    "answer_sub": {
        1: "This is subtraction: take the second number away from the first.",
        2: "If the result is negative, that's okay. Watch borrows.",
        3: "Re-check by adding your answer to the second number; you should get the first.",
    },
    "answer_mul": {
        1: "This is multiplication: repeated addition. Multiply the two numbers.",
        2: "Break it up: (a×b) = a×(tens) + a×(ones).",
        3: "Sanity check: multiplication should get bigger when both numbers are > 1.",
    },
}


class MakeHintTool(Tool):
    """Policy-controlled hint generation (rule-based baseline)."""

    name = "tutor.make_hint"
    version = "rule-based-v1"

    def __init__(self, store: ExerciseStore):
        self._store = store

    def run(
        self,
        *,
        grade: GradeReport,
        hint_level: int,
        policy: HintPolicy,
        attempt_index: int,
    ) -> ToolResult[HintArtifact]:
        artifact = self._store.get(grade.artifact_id)
        fn = _first_top_level_function_name(artifact.reference_solution.get_secret_value()) or "unknown"

        safe_level = max(1, min(int(hint_level), policy.max_hint_level))

        # Special policy/guardrail cases first.
        if "forbidden_import_used" in grade.policy_flags:
            hint_md = (
                "Your submission uses a forbidden import. Remove it and re-submit.\n\n"
                "Tip: in this lab, we restrict imports to keep execution safe and deterministic."
            )
            return ToolResult.success(
                HintArtifact(
                    level=safe_level,
                    hint_md=hint_md,
                    reveals_solution=False,
                    based_on={"attempt_index": attempt_index, "policy_flags": grade.policy_flags},
                )
            )

        if grade.passed:
            return ToolResult.success(
                HintArtifact(
                    level=safe_level,
                    hint_md="All tests passed — no hint needed.",
                    reveals_solution=False,
                    based_on={"attempt_index": attempt_index},
                )
            )

        # Use rule-based hint ladder per function, falling back to generic hints.
        hint_bank = _HINTS.get(fn, {})
        hint_md = hint_bank.get(
            safe_level,
            "Hint: Re-read the prompt carefully and handle edge cases. Use the failing test output to guide debugging.",
        )

        # Add a tiny nudge derived from first failing test (but avoid leaking hidden tests).
        first_fail = next((t for t in grade.test_results if not t.passed), None)
        if first_fail:
            hint_md += f"\n\n**Debug nudge:** At least one test is failing with `{first_fail.error_type}`."

        reveals_solution = False
        if policy.allow_solution_reveal and safe_level >= policy.max_hint_level and fn != "unknown":
            # Still keep it conservative; in v0.1 we do not dump full solutions by default.
            hint_md += "\n\n(Policy note: solution reveal is enabled, but this tutor baseline still avoids full code dumps.)"

        return ToolResult.success(
            HintArtifact(
                level=safe_level,
                hint_md=hint_md,
                reveals_solution=reveals_solution,
                based_on={"attempt_index": attempt_index, "function": fn},
            )
        )
