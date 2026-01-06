"""Plan/Execute orchestration (alternative to the explicit FSM).

The FSM is the default in VAR because it's easiest to reason about and test.

Plan/Execute is useful for:
- showing decomposition explicitly as an artifact
- swapping different planners (deterministic vs model-driven)
- experimenting with execution policies without rewriting tools

This package is intentionally small so students can compare it to the FSM.
"""

from .types import Plan, PlanStep
from .planner import Planner, DeterministicExerciseBuildPlanner
from .orchestrator import PlanExecuteOrchestrator

__all__ = [
    "Plan",
    "PlanStep",
    "Planner",
    "DeterministicExerciseBuildPlanner",
    "PlanExecuteOrchestrator",
]
