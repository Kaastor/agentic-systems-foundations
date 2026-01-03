from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .types import ExerciseSpec, ExerciseView, GradeReport, HintArtifact


class SessionIO(Protocol):
    """Human-in-the-loop boundary.

    The agent runtime never calls `input()` directly; it depends on this interface.
    That keeps the agent testable and supports synthetic learners for evaluation.
    """

    def choose_spec(self, specs: Sequence[ExerciseSpec]) -> ExerciseSpec: ...

    def present_exercise(self, view: ExerciseView) -> None: ...

    def get_submission(self, *, artifact_id: str, starter_code: str) -> str: ...

    def show_grade(self, grade: GradeReport) -> None: ...

    def show_hint(self, hint: HintArtifact) -> None: ...

    def show_message(self, message: str) -> None: ...
