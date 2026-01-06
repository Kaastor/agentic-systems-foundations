from __future__ import annotations

from enum import Enum


class TaskType(str, Enum):
    function_implementation = "function_implementation"
    bugfix = "bugfix"
    refactor = "refactor"
    complexity = "complexity"


class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class ToolErrorCode(str, Enum):
    # Boundary / contract
    ValidationError = "ValidationError"
    SchemaMismatch = "SchemaMismatch"

    # Runtime budgets
    BudgetExceeded = "BudgetExceeded"

    # Transient infra
    TransientError = "TransientError"
    Timeout = "Timeout"
    RateLimit = "RateLimit"
    Conflict = "Conflict"

    # Safety / policy / sandbox
    SandboxViolation = "SandboxViolation"
    PolicyViolation = "PolicyViolation"

    # Non-determinism
    NonDeterministicFlake = "NonDeterministicFlake"

    # Permanent / unknown
    PermanentError = "PermanentError"
    Unauthorized = "Unauthorized"


class OutcomeKind(str, Enum):
    """Domain outcome category."""

    Pass = "Pass"
    Fail = "Fail"
    Flaky = "Flaky"
    Timeout = "Timeout"
    PolicyViolation = "PolicyViolation"
    Invalid = "Invalid"


class PresentationKind(str, Enum):
    exercise = "exercise"
    grade = "grade"
    hint = "hint"


class AgentNode(str, Enum):
    SelectSpec = "SelectSpec"
    GenerateExercise = "GenerateExercise"
    VerifyExercise = "VerifyExercise"
    RepairOrRegenerate = "RepairOrRegenerate"

    # Universal gate for *anything* shown to a learner.
    PresentationGate = "PresentationGate"

    AwaitSubmission = "AwaitSubmission"
    GradeSubmission = "GradeSubmission"
    ProduceHintOrFeedback = "ProduceHintOrFeedback"
    SummarizeAndLog = "SummarizeAndLog"
    TerminalSuccess = "TerminalSuccess"
    TerminalFailure = "TerminalFailure"


class TraceEventType(str, Enum):
    state_entered = "state_entered"
    tool_called = "tool_called"
    tool_result = "tool_result"
    verification_outcome = "verification_outcome"
    grade_status = "grade_status"
    hint_issued = "hint_issued"
    presentation_gate = "presentation_gate"
    terminal_outcome = "terminal_outcome"
