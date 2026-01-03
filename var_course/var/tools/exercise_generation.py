from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from ..types import (
    ExerciseArtifact,
    ExerciseDraft,
    ExerciseMetadata,
    ExerciseSpec,
    Rubric,
    SignatureSpec,
    ToolError,
    ToolErrorCode,
    utc_now,
    stable_hash,
)
from ..utils import render_signature_stub
from .base import Tool, ToolResult


# ----------------------------
# Template library
# ----------------------------

@dataclass(frozen=True)
class Template:
    key: str
    concepts: List[str]
    difficulty: int
    signature: SignatureSpec

    def prompt(self, spec: ExerciseSpec) -> str:
        raise NotImplementedError

    def starter(self, spec: ExerciseSpec) -> str:
        stub = render_signature_stub(self.signature)
        return f"""{stub}
    \"\"\"TODO: implement.\"\"\"
    raise NotImplementedError
"""

    def solution(self, spec: ExerciseSpec) -> str:
        raise NotImplementedError

    def hidden_tests(self, spec: ExerciseSpec) -> str:
        raise NotImplementedError

    def public_tests(self, spec: ExerciseSpec) -> Optional[str]:
        return None

    def rubric(self) -> Rubric:
        return Rubric(criteria=["Correctness", "Edge cases", "Code clarity"])


def _sig(name: str, args: List[tuple[str, str]], returns: str) -> SignatureSpec:
    from ..types import ArgSpec

    return SignatureSpec(
        name=name,
        args=[ArgSpec(name=a, type=t) for a, t in args],
        returns=returns,
    )


class ReverseStringTemplate(Template):
    def prompt(self, spec: ExerciseSpec) -> str:
        return """# Reverse a string

Implement the function below.

**Task:** Return the reverse of the input string.

Examples:

- `reverse_string("abc") -> "cba"`
- `reverse_string("") -> ""`

Notes:
- You may use slicing or a loop.
- The function must return a **new** string.
"""

    def solution(self, spec: ExerciseSpec) -> str:
        return """def reverse_string(s: str) -> str:
    return s[::-1]
"""

    def hidden_tests(self, spec: ExerciseSpec) -> str:
        return """import unittest
import solution

class TestReverseString(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(solution.reverse_string("abc"), "cba")

    def test_empty(self):
        self.assertEqual(solution.reverse_string(""), "")

    def test_spaces(self):
        self.assertEqual(solution.reverse_string("a b"), "b a")

    def test_unicode(self):
        self.assertEqual(solution.reverse_string("åß∂"), "∂ßå")

if __name__ == "__main__":
    unittest.main()
"""


class CountVowelsTemplate(Template):
    def prompt(self, spec: ExerciseSpec) -> str:
        return """# Count vowels

Implement the function below.

**Task:** Count how many vowels (`a, e, i, o, u`) appear in the input string.
Count is **case-insensitive**.

Examples:
- `count_vowels("Hello") -> 2`  (`e`, `o`)
- `count_vowels("xyz") -> 0`

Notes:
- Treat only `a, e, i, o, u` as vowels (not `y`).
"""

    def solution(self, spec: ExerciseSpec) -> str:
        return """def count_vowels(text: str) -> int:
    vowels = set("aeiou")
    return sum(1 for ch in text.lower() if ch in vowels)
"""

    def hidden_tests(self, spec: ExerciseSpec) -> str:
        # Research/testbed hook: a small probability (by seed) of producing flaky tests.
        # The verifier should detect this and the agent should regenerate away.
        if spec.seed % 13 == 7:
            flag_path = f"/tmp/var_flake_count_vowels_{spec.seed}.flag"
            return f"""import unittest
import solution

FLAG_PATH = {flag_path!r}


def _read_flag() -> int:
    try:
        with open(FLAG_PATH, "r", encoding="utf-8") as f:
            raw = f.read().strip() or "0"
            return int(raw)
    except FileNotFoundError:
        return 0


def _write_flag(v: int) -> None:
    with open(FLAG_PATH, "w", encoding="utf-8") as f:
        f.write(str(v))


class TestCountVowels(unittest.TestCase):
    def test_correctness(self):
        self.assertEqual(solution.count_vowels("Hello"), 2)
        self.assertEqual(solution.count_vowels("xyz"), 0)

    def test_flaky_toggle(self):
        v = _read_flag()
        _write_flag(1 - v)
        self.assertEqual(v, 0, "Intentional flaky test (external state).")


if __name__ == "__main__":
    unittest.main()
"""

        return """import unittest
import solution

class TestCountVowels(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(solution.count_vowels("Hello"), 2)

    def test_none(self):
        self.assertEqual(solution.count_vowels("xyz"), 0)

    def test_all(self):
        self.assertEqual(solution.count_vowels("AEIOUaeiou"), 10)

    def test_punctuation(self):
        self.assertEqual(solution.count_vowels("a! e? i."), 3)

if __name__ == "__main__":
    unittest.main()
"""


class IsPrimeTemplate(Template):
    def prompt(self, spec: ExerciseSpec) -> str:
        return """# Prime checker

Implement the function below.

**Task:** Return `True` if `n` is a prime number, otherwise return `False`.

Definitions:
- A prime number is an integer greater than 1 with no positive divisors other than 1 and itself.
- `0` and `1` are **not** prime.
- Negative numbers are **not** prime.

Examples:
- `is_prime(2) -> True`
- `is_prime(9) -> False`
- `is_prime(1) -> False`
"""

    def solution(self, spec: ExerciseSpec) -> str:
        return """def is_prime(n: int) -> bool:
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True
"""

    def hidden_tests(self, spec: ExerciseSpec) -> str:
        return """import unittest
import solution

class TestIsPrime(unittest.TestCase):
    def test_small(self):
        self.assertTrue(solution.is_prime(2))
        self.assertTrue(solution.is_prime(3))
        self.assertFalse(solution.is_prime(4))
        self.assertFalse(solution.is_prime(1))
        self.assertFalse(solution.is_prime(0))
        self.assertFalse(solution.is_prime(-7))

    def test_known(self):
        self.assertTrue(solution.is_prime(97))
        self.assertFalse(solution.is_prime(99))

    def test_large_composite(self):
        self.assertFalse(solution.is_prime(221))  # 13*17

if __name__ == "__main__":
    unittest.main()
"""


class FizzBuzzListTemplate(Template):
    def prompt(self, spec: ExerciseSpec) -> str:
        return """# FizzBuzz list

Implement the function below.

**Task:** Return a list of strings for the numbers from `1` to `n` (inclusive) following FizzBuzz rules:

- If a number is divisible by 3, use `"Fizz"`.
- If a number is divisible by 5, use `"Buzz"`.
- If a number is divisible by both 3 and 5, use `"FizzBuzz"`.
- Otherwise, use the number itself as a string.

Examples:
- `fizzbuzz(5) -> ["1","2","Fizz","4","Buzz"]`
- `fizzbuzz(15)[-1] -> "FizzBuzz"`

Notes:
- If `n <= 0`, return an empty list.
"""

    def solution(self, spec: ExerciseSpec) -> str:
        return """def fizzbuzz(n: int) -> list[str]:
    out: list[str] = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(i))
    return out
"""

    def hidden_tests(self, spec: ExerciseSpec) -> str:
        return """import unittest
import solution

class TestFizzBuzz(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(solution.fizzbuzz(5), ["1", "2", "Fizz", "4", "Buzz"])

    def test_15(self):
        out = solution.fizzbuzz(15)
        self.assertEqual(out[2], "Fizz")
        self.assertEqual(out[4], "Buzz")
        self.assertEqual(out[14], "FizzBuzz")

    def test_non_positive(self):
        self.assertEqual(solution.fizzbuzz(0), [])
        self.assertEqual(solution.fizzbuzz(-10), [])

if __name__ == "__main__":
    unittest.main()
"""


class FlattenTemplate(Template):
    def prompt(self, spec: ExerciseSpec) -> str:
        return """# Flatten a list of lists

Implement the function below.

**Task:** Given a list of lists of integers, return a single list containing the same integers in the same order.

Examples:
- `flatten([[1,2],[3],[4,5]]) -> [1,2,3,4,5]`
- `flatten([]) -> []`
- `flatten([[]]) -> []`

Notes:
- You should not mutate the input lists.
"""

    def solution(self, spec: ExerciseSpec) -> str:
        return """def flatten(list_of_lists: list[list[int]]) -> list[int]:
    out: list[int] = []
    for inner in list_of_lists:
        for x in inner:
            out.append(x)
    return out
"""

    def hidden_tests(self, spec: ExerciseSpec) -> str:
        return """import unittest
import solution

class TestFlatten(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(solution.flatten([[1,2],[3],[4,5]]), [1,2,3,4,5])

    def test_empty(self):
        self.assertEqual(solution.flatten([]), [])

    def test_nested_empty(self):
        self.assertEqual(solution.flatten([[], [1], []]), [1])

    def test_no_mutation(self):
        data = [[1,2],[3]]
        out = solution.flatten(data)
        self.assertEqual(out, [1,2,3])
        self.assertEqual(data, [[1,2],[3]])

if __name__ == "__main__":
    unittest.main()
"""


TEMPLATES: Dict[str, Template] = {
    "reverse_string": ReverseStringTemplate(
        key="reverse_string",
        concepts=["strings", "slicing"],
        difficulty=1,
        signature=_sig("reverse_string", [("s", "str")], "str"),
    ),
    "count_vowels": CountVowelsTemplate(
        key="count_vowels",
        concepts=["strings", "loops"],
        difficulty=2,
        signature=_sig("count_vowels", [("text", "str")], "int"),
    ),
    "is_prime": IsPrimeTemplate(
        key="is_prime",
        concepts=["loops", "math"],
        difficulty=3,
        signature=_sig("is_prime", [("n", "int")], "bool"),
    ),
    "fizzbuzz": FizzBuzzListTemplate(
        key="fizzbuzz",
        concepts=["loops", "conditionals"],
        difficulty=2,
        signature=_sig("fizzbuzz", [("n", "int")], "list[str]"),
    ),
    "flatten": FlattenTemplate(
        key="flatten",
        concepts=["lists", "loops"],
        difficulty=2,
        signature=_sig("flatten", [("list_of_lists", "list[list[int]]")], "list[int]"),
    ),
}


def available_specs(generator_version: str = "template-v1", seed: int = 0) -> List[ExerciseSpec]:
    """Deterministically list a small catalog of ExerciseSpecs for the CLI / eval harness."""
    from ..types import Constraints, TaskType

    constraints = Constraints(
        forbidden_imports=["os", "sys", "subprocess", "socket", "requests", "urllib", "pathlib"],
        max_runtime_ms=800,
        max_memory_mb=256,
    )

    specs: List[ExerciseSpec] = []
    for t in TEMPLATES.values():
        specs.append(
            ExerciseSpec(
                concepts=t.concepts,
                difficulty=t.difficulty,
                task_type=TaskType.function_implementation,
                signature=t.signature,
                constraints=constraints,
                seed=seed,
                generator_version=generator_version,
            )
        )
    return specs


# ----------------------------
# Tools
# ----------------------------

class GenerateDraftTool(Tool):
    name = "exercise.generate_draft"
    version = "template-v1"

    def run(self, *, spec: ExerciseSpec) -> ToolResult[ExerciseDraft]:
        template = TEMPLATES.get(spec.signature.name)
        if not template:
            return ToolResult.failure(
                ToolError(
                    code=ToolErrorCode.ValidationError,
                    retryable=False,
                    safe_message="Unknown exercise signature.",
                    debug={"signature": spec.signature.model_dump(mode="json")},
                )
            )

        if spec.task_type.value != "function_implementation":
            return ToolResult.failure(
                ToolError(
                    code=ToolErrorCode.ValidationError,
                    retryable=False,
                    safe_message="Only function_implementation is supported in v0.1 templates.",
                    debug={"task_type": spec.task_type.value},
                )
            )

        draft = ExerciseDraft(
            prompt_md=template.prompt(spec),
            starter_code=template.starter(spec),
            reference_solution=template.solution(spec),
            public_tests=template.public_tests(spec),
            hidden_tests=template.hidden_tests(spec),
            rubric=template.rubric(),
        )
        return ToolResult.success(draft)


class CompileDraftTool(Tool):
    name = "exercise.compile"
    version = "compiler-v1"

    def run(self, *, draft: ExerciseDraft, spec: ExerciseSpec) -> ToolResult[ExerciseArtifact]:
        created_at = utc_now()
        identity = stable_hash(
            {
                "prompt_md": draft.prompt_md,
                "starter_code": draft.starter_code,
                "reference_solution": draft.reference_solution,
                "public_tests": draft.public_tests,
                "hidden_tests": draft.hidden_tests,
                "rubric": draft.rubric.model_dump(mode="json"),
                "spec": spec.model_dump(mode="json"),
            }
        )
        artifact_id = f"ex_{identity[:12]}"

        artifact = ExerciseArtifact(
            artifact_id=artifact_id,
            prompt_md=draft.prompt_md,
            starter_code=draft.starter_code,
            reference_solution=draft.reference_solution,
            public_tests=draft.public_tests,
            hidden_tests=draft.hidden_tests,
            rubric=draft.rubric,
            metadata=ExerciseMetadata(
                concepts=spec.concepts,
                difficulty=spec.difficulty,
                seed=spec.seed,
                generator_version=spec.generator_version,
                created_at=created_at,
            ),
        )

        return ToolResult.success(artifact)
