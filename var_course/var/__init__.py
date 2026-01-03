"""Verified Agent Runtime (VAR) package.

This package intentionally resembles production code, but stays small enough for lab work.
"""

from .types import (
    AgentState,
    ExerciseArtifact,
    ExerciseSpec,
    GradeReport,
    HintArtifact,
    HintPolicy,
    Submission,
    VerificationReport,
)

__all__ = [
    "AgentState",
    "ExerciseArtifact",
    "ExerciseSpec",
    "GradeReport",
    "HintArtifact",
    "HintPolicy",
    "Submission",
    "VerificationReport",
]
