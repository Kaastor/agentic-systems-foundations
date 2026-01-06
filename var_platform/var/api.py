"""Public API surface for VAR.

The goal is pedagogical clarity: students can start with these imports without
needing to learn the whole folder tree on day 1.

Everything else in the repo is still importable, but this module is the
**supported** surface you should treat as stable.
"""

from .agent.orchestrator import Toolbox, VAROrchestrator
from .agent.plan_execute.orchestrator import PlanExecuteOrchestrator, PlanToolbox
from .budgets import BudgetCategory, BudgetLimits, BudgetManager
from .context import ContextBuilder, ContextPacket
from .memory import FileMemoryStore, MemoryStore, MemoryItem, MemoryQuery
from .config import RuntimeConfig, ResearchConfig, BudgetConfig
from .io import SessionIO
from .store.exercise_store import ExerciseStore
from .store.trace_store import FileTraceStore
from .types import (
    AgentState,
    ExerciseSpec,
    ExerciseArtifact,
    ExerciseView,
    Submission,
    GradeReport,
    HintPolicy,
    HintArtifact,
    VerificationReport,
)

__all__ = [
    # Orchestration
    "Toolbox",
    "VAROrchestrator",
    "PlanExecuteOrchestrator",
    "PlanToolbox",

    # Config
    "RuntimeConfig",
    "ResearchConfig",
    "BudgetConfig",
    "BudgetCategory",
    "BudgetLimits",
    "BudgetManager",

    # Context engineering
    "ContextBuilder",
    "ContextPacket",

    # Memory
    "MemoryStore",
    "FileMemoryStore",
    "MemoryItem",
    "MemoryQuery",

    # IO boundary
    "SessionIO",

    # Stores
    "ExerciseStore",
    "FileTraceStore",

    # Types
    "AgentState",
    "ExerciseSpec",
    "ExerciseArtifact",
    "ExerciseView",
    "Submission",
    "GradeReport",
    "HintPolicy",
    "HintArtifact",
    "VerificationReport",
]
