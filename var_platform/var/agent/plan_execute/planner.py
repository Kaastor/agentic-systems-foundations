from __future__ import annotations

from typing import Protocol

from ...types import ExerciseSpec
from .types import Plan, PlanStep


class Planner(Protocol):
    def build_plan(self, *, spec: ExerciseSpec) -> Plan: ...


class DeterministicExerciseBuildPlanner:
    """A deterministic plan builder for the exercise-build pipeline.

    This planner is intentionally simple: it's a readable baseline.
    """

    name = "deterministic-exercise-build"
    version = "v1"

    def build_plan(self, *, spec: ExerciseSpec) -> Plan:
        return Plan(
            planner=self.name,
            version=self.version,
            steps=[
                PlanStep(
                    name="generate_draft",
                    tool="generate_draft",
                    description="Generate an exercise draft from a spec.",
                    args={"spec": spec.model_dump(mode="python")},
                    expects="ExerciseDraft",
                ),
                PlanStep(
                    name="compile_draft",
                    tool="compile_draft",
                    description="Compile the draft into a full ExerciseArtifact.",
                    args={"spec": spec.model_dump(mode="python")},
                    expects="ExerciseArtifact",
                ),
                PlanStep(
                    name="verify",
                    tool="verify",
                    description="Verify the artifact in the sandbox.",
                    args={"constraints": spec.constraints.model_dump(mode="python")},
                    expects="Outcome[VerificationReport]",
                ),
                PlanStep(
                    name="present",
                    tool="gate_exercise_view",
                    description="Present verified exercise view to the learner.",
                    args={},
                    expects="ExerciseView",
                ),
            ],
        )
