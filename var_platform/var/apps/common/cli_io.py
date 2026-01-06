from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from ...io import SessionIO
from ...types import ExerciseSpec, ExerciseView, GradeReport, HintArtifact


class CLIIO(SessionIO):
    """A tiny interactive IO implementation for local CLIs.

    This stays *outside* the kernel so the engine can remain UI-agnostic.
    """

    def choose_spec(self, specs: Sequence[ExerciseSpec]) -> ExerciseSpec:
        print("Choose an exercise:")
        for i, s in enumerate(specs):
            print(f"  [{i}] {s.signature.name} | difficulty={s.difficulty} | concepts={','.join(s.concepts)}")
        raw = input("Enter index (default 0): ").strip()
        idx = int(raw) if raw else 0
        idx = max(0, min(idx, len(specs) - 1))
        return specs[idx]

    def present_exercise(self, view: ExerciseView) -> None:
        print("\n" + "=" * 80)
        print(f"Exercise ID: {view.artifact_id}")
        print("=" * 80)
        print(view.prompt_md.strip())
        print("\n--- Starter code ---\n")
        print(view.starter_code.rstrip())
        if view.public_tests:
            print("\n--- Public tests ---\n")
            print(view.public_tests.rstrip())
        print("=" * 80 + "\n")

    def get_submission(self, *, artifact_id: str, starter_code: str) -> str:
        print("Submit your code. Options:")
        print("  1) Paste code (end with a line containing only EOF)")
        print("  2) Provide a path to a .py file")
        raw = input("Choose [1/2] (default 1): ").strip() or "1"
        if raw == "2":
            path = Path(input("Path to .py file: ").strip())
            return path.read_text(encoding="utf-8")

        print("Paste your full solution code now. End with EOF on its own line.")
        lines: list[str] = []
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            if line.rstrip("\n") == "EOF":
                break
            lines.append(line)
        return "".join(lines).strip() or starter_code

    def show_grade(self, grade: GradeReport) -> None:
        print("\n--- Grade ---")
        print(f"Passed: {grade.passed} | score={grade.score:.2f} | runtime_ms={grade.runtime_ms}")
        if grade.policy_flags:
            print(f"Policy flags: {', '.join(grade.policy_flags)}")
        for tr in grade.test_results:
            status = "PASS" if tr.passed else "FAIL"
            print(f"  {status} {tr.test_name}")
            if not tr.passed and tr.sanitized_trace:
                print(f"    {tr.sanitized_trace}")
        print("---\n")

    def show_hint(self, hint: HintArtifact) -> None:
        print(f"Hint (level {hint.level}):\n")
        print(hint.hint_md.strip())
        print("\n")

    def show_message(self, message: str) -> None:
        print(message)
