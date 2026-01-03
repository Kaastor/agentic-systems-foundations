from __future__ import annotations

import re
from typing import List, Optional

from ...types import ExerciseSpec, ExerciseView, GradeReport, HintArtifact
from .planner import HomeschoolPlanner
from .profile import HomeschoolProfile, LocalProfileStore


class HomeschoolCLIIO:
    """Kid-friendly CLI.

    Differences from CLISessionIO:
    - chooses specs automatically via a planner
    - accepts a numeric answer instead of Python code
    - wraps the answer into a Python function matching the exercise signature
    - updates & persists a tiny mastery state
    """

    def __init__(self, *, profile: HomeschoolProfile, profile_store: LocalProfileStore, planner: Optional[HomeschoolPlanner] = None):
        self.profile = profile
        self._profile_store = profile_store
        self._planner = planner or HomeschoolPlanner()
        self._current_spec: Optional[ExerciseSpec] = None

    def choose_spec(self, specs: List[ExerciseSpec]) -> ExerciseSpec:
        spec = self._planner.choose(profile=self.profile, specs=specs)
        self._current_spec = spec
        return spec

    def present_exercise(self, view: ExerciseView) -> None:
        print("\n" + "=" * 72)
        print(f"{self.profile.name}, here's your next challenge!")
        print("=" * 72)
        print(view.prompt_md)

    def get_submission(self, *, artifact_id: str, starter_code: str) -> str:
        fn = self._infer_function_name(starter_code) or "answer"
        while True:
            raw = input("Your answer (just a number): ").strip()
            if re.fullmatch(r"-?\d+", raw):
                break
            print("Please type an integer (example: 42 or -7).")
        return f"def {fn}() -> int:\n    return {raw}\n"

    def show_grade(self, grade: GradeReport) -> None:
        if grade.passed:
            print("✅ Correct!")
        else:
            print("❌ Not quite yet.")
            first_fail = next((t for t in grade.test_results if not t.passed), None)
            if first_fail:
                print(f"(Debug info) error_type: {first_fail.error_type}")

        # Update mastery using the last chosen spec.
        if self._current_spec is not None:
            self.profile.update_mastery(concepts=list(self._current_spec.concepts), passed=grade.passed)
            self._profile_store.save(self.profile)

    def show_hint(self, hint: HintArtifact) -> None:
        print("\nHint:")
        print(hint.hint_md)

    def show_message(self, message: str) -> None:
        print(message)

    @staticmethod
    def _infer_function_name(starter_code: str) -> Optional[str]:
        m = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", starter_code)
        return m.group(1) if m else None
