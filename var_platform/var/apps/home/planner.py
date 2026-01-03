from __future__ import annotations

from typing import Iterable, List

from ...types import ExerciseSpec
from .profile import HomeschoolProfile


class HomeschoolPlanner:
    """Choose the next exercise spec for a homeschool learner.

    This is a deliberately simple heuristic planner:
    - compute each spec's mastery as the average mastery of its concepts
    - pick the spec with lowest mastery

    Research extensions:
    - spaced repetition
    - prerequisite graphs
    - bandit algorithms
    - multi-objective tradeoffs (confidence vs novelty vs time)
    """

    def choose(self, *, profile: HomeschoolProfile, specs: List[ExerciseSpec]) -> ExerciseSpec:
        if not specs:
            raise ValueError("no specs")

        def mastery_for(spec: ExerciseSpec) -> float:
            vals = [float(profile.concept_mastery.get(c, 0.0)) for c in spec.concepts]
            if not vals:
                return 0.0
            return sum(vals) / len(vals)

        return min(specs, key=mastery_for)
