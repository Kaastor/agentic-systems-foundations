from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Sequence

from ..budgets.manager import BudgetManager
from ..config import RuntimeConfig
from ..io import SessionIO
from ..research.types import RunManifest, StateSnapshot
from ..store.exercise_store import ExerciseStore
from ..store.run_store import FileRunStore
from ..types import (
    AgentError,
    AgentNode,
    AgentState,
    AttemptRecord,
    ExerciseArtifact,
    ExerciseSpec,
    HintArtifact,
    OutcomeKind,
    PresentationKind,
    Submission,
    TraceEvent,
    TraceEventType,
    utc_now,
    stable_hash,
    ToolErrorCode,
)
from ..tools.exercise_generation import CompileDraftTool, GenerateDraftTool
from ..tools.grading import GradeSubmissionTool
from ..tools.hinting import MakeHintTool
from ..tools.observability import TraceLogTool
from ..tools.presentation_gate import GateExerciseViewTool, GateGradeReportTool, GateHintTool
from ..tools.memory import MemoryAppendTool, MemoryQueryTool
from ..tools.verification import ExerciseVerifyTool
from ..memory.store import memory_item_id
from ..memory.types import MemoryItem, MemoryKind

from .tool_executor import ToolExecutor, ToolExecutorConfig


class SimulatedCrash(RuntimeError):
    """Raised when `RuntimeConfig.research.crash_after_step` triggers."""


@dataclass(frozen=True)
class Toolbox:
    generate_draft: GenerateDraftTool
    compile_draft: CompileDraftTool
    verify: ExerciseVerifyTool
    grade: GradeSubmissionTool
    hint: MakeHintTool

    gate_exercise_view: GateExerciseViewTool
    gate_grade_report: GateGradeReportTool
    gate_hint: GateHintTool

    trace_log: TraceLogTool

    # Optional memory tools (used for persistent learner context). Not required
    # for the core verified loop.
    memory_append: MemoryAppendTool | None = None
    memory_query: MemoryQueryTool | None = None


Handler = Callable[[AgentState, SessionIO, Sequence[ExerciseSpec]], AgentState]


class VAROrchestrator:
    """Explicit finite-state machine implementing the Verified Agent Runtime.

    Two non-negotiable design choices:
    1) Orchestration is explicit (FSM): states are named, transitions are testable.
    2) Anything learner-facing goes through PresentationGate.
    """

    # Data-driven transition rules (unit-testable).
    ALLOWED_TRANSITIONS: Dict[AgentNode, set[AgentNode]] = {
        AgentNode.SelectSpec: {AgentNode.GenerateExercise, AgentNode.TerminalFailure},
        AgentNode.GenerateExercise: {AgentNode.VerifyExercise, AgentNode.RepairOrRegenerate, AgentNode.TerminalFailure},
        AgentNode.VerifyExercise: {AgentNode.PresentationGate, AgentNode.RepairOrRegenerate, AgentNode.TerminalFailure},
        AgentNode.RepairOrRegenerate: {AgentNode.GenerateExercise, AgentNode.TerminalFailure},
        AgentNode.PresentationGate: {AgentNode.AwaitSubmission, AgentNode.ProduceHintOrFeedback, AgentNode.TerminalSuccess, AgentNode.TerminalFailure},
        AgentNode.AwaitSubmission: {AgentNode.GradeSubmission, AgentNode.TerminalFailure},
        AgentNode.GradeSubmission: {AgentNode.PresentationGate, AgentNode.TerminalFailure},
        AgentNode.ProduceHintOrFeedback: {AgentNode.PresentationGate, AgentNode.TerminalFailure},
        AgentNode.SummarizeAndLog: {AgentNode.TerminalSuccess, AgentNode.TerminalFailure},
        AgentNode.TerminalSuccess: set(),
        AgentNode.TerminalFailure: set(),
    }

    def __init__(
        self,
        *,
        config: RuntimeConfig,
        store: ExerciseStore,
        tools: Toolbox,
        run_store: FileRunStore | None = None,
        tool_executor: ToolExecutor | None = None,
        budget_manager: BudgetManager | None = None,
    ):
        self._config = config
        self._store = store
        self._tools = tools
        self._run_store = run_store

        budgets = None
        if getattr(config, "budgets", None) is not None and config.budgets.enabled:
            budgets = budget_manager or BudgetManager(limits=config.budgets.limits)

        self._tool_executor = tool_executor or ToolExecutor(
            emit=self._emit,
            run_store=run_store,
            executor_cfg=ToolExecutorConfig(
                max_retries=config.tool_retry.max_retries,
                retry_backoff_ms=config.tool_retry.retry_backoff_ms,
            ),
            budgets=budgets,
            record_tool_io=bool(config.research.enabled and config.research.record_tool_io),
            tool_io_capture=config.research.tool_io_capture,
            redact_tool_io=config.research.redact_tool_io,
        )

        self._handlers: Dict[AgentNode, Handler] = {
            AgentNode.SelectSpec: self._handle_select_spec,
            AgentNode.GenerateExercise: self._handle_generate_exercise,
            AgentNode.VerifyExercise: self._handle_verify_exercise,
            AgentNode.RepairOrRegenerate: self._handle_repair_or_regenerate,
            AgentNode.PresentationGate: self._handle_presentation_gate,
            AgentNode.AwaitSubmission: self._handle_await_submission,
            AgentNode.GradeSubmission: self._handle_grade_submission,
            AgentNode.ProduceHintOrFeedback: self._handle_hint_or_feedback,
            AgentNode.SummarizeAndLog: self._handle_summarize_and_log,
        }

    # ----------------------------
    # Public API
    # ----------------------------

    def run_session(
        self,
        *,
        io: SessionIO,
        specs: Sequence[ExerciseSpec],
        initial_state: AgentState | None = None,
    ) -> AgentState:
        state = initial_state or AgentState(run_id=uuid.uuid4().hex[:12])

        # Capture tool versions for reproducibility (idempotent).
        if not state.versions.tool_versions:
            state.versions.tool_versions = {
                self._tools.generate_draft.name: self._tools.generate_draft.version,
                self._tools.compile_draft.name: self._tools.compile_draft.version,
                self._tools.verify.name: self._tools.verify.version,
                self._tools.grade.name: self._tools.grade.version,
                self._tools.hint.name: self._tools.hint.version,
                self._tools.gate_exercise_view.name: self._tools.gate_exercise_view.version,
                self._tools.gate_grade_report.name: self._tools.gate_grade_report.version,
                self._tools.gate_hint.name: self._tools.gate_hint.version,
                self._tools.trace_log.name: self._tools.trace_log.version,
            }

            if self._tools.memory_append is not None:
                state.versions.tool_versions[self._tools.memory_append.name] = self._tools.memory_append.version
            if self._tools.memory_query is not None:
                state.versions.tool_versions[self._tools.memory_query.name] = self._tools.memory_query.version

        self._maybe_write_manifest(state)

        started = time.time()
        try:
            while True:
                if state.metrics.step_count >= self._config.max_steps:
                    return self._terminal_failure(state, "max_steps exceeded")

                node = state.current_state
                self._emit(state, TraceEventType.state_entered, node, {})

                if node in (AgentNode.TerminalSuccess, AgentNode.TerminalFailure):
                    self._emit(
                        state,
                        TraceEventType.terminal_outcome,
                        node,
                        {"outcome": "success" if node == AgentNode.TerminalSuccess else "failure"},
                    )
                    # Optional: persist a compact summary into memory.
                    self._maybe_append_memory_summary(state)
                    self._maybe_snapshot(state)
                    return state

                handler = self._handlers.get(node)
                if handler is None:
                    return self._terminal_failure(state, f"Unhandled node: {node.value}")

                prev = state.current_state
                state = handler(state, io, specs)
                self._enforce_transition(prev, state.current_state)

                self._maybe_snapshot(state)

                # Crash injection hook (used by the research harness).
                crash_after = self._config.research.crash_after_step
                if self._config.research.enabled and crash_after is not None:
                    if state.metrics.step_count == crash_after:
                        raise SimulatedCrash(f"Simulated crash after step_count={crash_after}")

                state.metrics.step_count += 1
        finally:
            state.metrics.latency_ms = int((time.time() - started) * 1000)

    # ----------------------------
    # Transition enforcement
    # ----------------------------

    def _enforce_transition(self, prev: AgentNode, nxt: AgentNode) -> None:
        allowed = self.ALLOWED_TRANSITIONS.get(prev)
        if allowed is None:
            raise RuntimeError(f"No transition policy for node: {prev}")
        if nxt not in allowed and nxt not in (AgentNode.TerminalSuccess, AgentNode.TerminalFailure) and prev not in (AgentNode.TerminalSuccess, AgentNode.TerminalFailure):
            raise RuntimeError(f"Illegal FSM transition: {prev.value} -> {nxt.value}")

    # ----------------------------
    # Handlers
    # ----------------------------

    def _handle_select_spec(self, state: AgentState, io: SessionIO, specs: Sequence[ExerciseSpec]) -> AgentState:
        chosen = io.choose_spec(specs)
        state.spec = chosen
        state.versions.generator_version = chosen.generator_version
        state.current_state = AgentNode.GenerateExercise
        return state

    def _handle_generate_exercise(self, state: AgentState, io: SessionIO, specs: Sequence[ExerciseSpec]) -> AgentState:
        assert state.spec is not None, "spec must be set before GenerateExercise"

        res_draft = self._tool_executor.call(
            state,
            self._tools.generate_draft,
            args={"spec": state.spec.model_dump(mode="python")},
            call_kwargs={"spec": state.spec},
            state_node=AgentNode.GenerateExercise,
        )
        if not res_draft.ok:
            state.errors.append(res_draft.error)
            # Budget exhaustion is a terminal boundary failure.
            if res_draft.error.code == ToolErrorCode.BudgetExceeded:
                return self._terminal_failure(state, res_draft.error.safe_message)
            state.current_state = AgentNode.RepairOrRegenerate
            return state

        draft = res_draft.result

        res_art = self._tool_executor.call(
            state,
            self._tools.compile_draft,
            args={
                "draft": draft.model_dump(mode="python"),
                "spec": state.spec.model_dump(mode="python"),
            },
            call_kwargs={"draft": draft, "spec": state.spec},
            state_node=AgentNode.GenerateExercise,
        )
        if not res_art.ok:
            state.errors.append(res_art.error)
            if res_art.error.code == ToolErrorCode.BudgetExceeded:
                return self._terminal_failure(state, res_art.error.safe_message)
            state.current_state = AgentNode.RepairOrRegenerate
            return state

        artifact: ExerciseArtifact = res_art.result
        self._store.put(artifact)
        state.artifact_id = artifact.artifact_id
        state.current_state = AgentNode.VerifyExercise
        return state

    def _handle_verify_exercise(self, state: AgentState, io: SessionIO, specs: Sequence[ExerciseSpec]) -> AgentState:
        assert state.spec is not None and state.artifact_id is not None

        artifact = self._store.get(state.artifact_id)

        verify_args = {
            "artifact_id": artifact.artifact_id,
            "constraints": state.spec.constraints.model_dump(mode="python"),
            "repeats": self._config.verification_repeats,
        }
        res = self._tool_executor.call(
            state,
            self._tools.verify,
            args=verify_args,
            call_kwargs={
                "artifact": artifact,
                "constraints": state.spec.constraints,
                "repeats": self._config.verification_repeats,
            },
            state_node=AgentNode.VerifyExercise,
        )

        if not res.ok:
            state.errors.append(res.error)
            if res.error.code == ToolErrorCode.BudgetExceeded:
                return self._terminal_failure(state, res.error.safe_message)
            state.current_state = AgentNode.RepairOrRegenerate
            return state

        state.verification = res.result
        self._emit(
            state,
            TraceEventType.verification_outcome,
            AgentNode.VerifyExercise,
            {
                "outcome_kind": state.verification.kind.value,
                "status": (state.verification.value.status.value if state.verification.value else None),
                "artifact_id": artifact.artifact_id,
                "regen_count": state.loop_counters.regen_count,
                "reason": state.verification.reason,
            },
        )

        if not state.verification.passed:
            args_hash = stable_hash(verify_args)
            state.add_tool_repeat(f"{self._tools.verify.name}:{args_hash}")

        if state.verification.passed:
            # Queue learner-facing presentation through the universal gate.
            state.pending_presentation_kind = PresentationKind.exercise
            state.pending_exercise_view = artifact.view_for_learner()
            state.post_presentation_state = AgentNode.AwaitSubmission
            state.current_state = AgentNode.PresentationGate
        else:
            state.current_state = AgentNode.RepairOrRegenerate
        return state

    def _handle_repair_or_regenerate(self, state: AgentState, io: SessionIO, specs: Sequence[ExerciseSpec]) -> AgentState:
        assert state.spec is not None

        if state.loop_counters.regen_count >= self._config.max_regenerations_per_spec:
            return self._terminal_failure(state, "max_regenerations_per_spec exceeded")

        state.loop_counters.regen_count += 1

        old_spec = state.spec
        new_seed = old_spec.seed + state.loop_counters.regen_count

        # Force-change strategy:
        # - bump seed every time
        # - on repeated failure, rotate to a different spec (next in catalog)
        stuck_key_prefix = f"{self._tools.verify.name}:"
        stuck = any(
            k.startswith(stuck_key_prefix) and v >= self._config.max_repeated_tool_failures
            for k, v in state.loop_counters.tool_repeat_counts.items()
        )

        if stuck:
            idx = 0
            for i, s in enumerate(specs):
                if s.signature.name == old_spec.signature.name:
                    idx = i
                    break
            new_spec = specs[(idx + 1) % len(specs)]
            new_spec = new_spec.model_copy(update={"seed": new_seed})
            io.show_message("Repair: rotating to a different exercise template (loop control).")
        else:
            new_diff = max(1, old_spec.difficulty - 1) if state.loop_counters.regen_count >= 2 else old_spec.difficulty
            new_spec = old_spec.model_copy(update={"seed": new_seed, "difficulty": new_diff})

        state.spec = new_spec
        state.artifact_id = None
        state.verification = None

        # Clear pending presentation.
        state.pending_presentation_kind = None
        state.pending_exercise_view = None
        state.pending_grade = None
        state.pending_hint = None
        state.post_presentation_state = None

        state.current_state = AgentNode.GenerateExercise
        return state

    def _handle_presentation_gate(self, state: AgentState, io: SessionIO, specs: Sequence[ExerciseSpec]) -> AgentState:
        kind = state.pending_presentation_kind
        post = state.post_presentation_state

        if kind is None or post is None:
            return self._terminal_failure(state, "PresentationGate entered without pending payload")

        # --- Steel beam invariant ---
        if kind == PresentationKind.exercise:
            if state.verification is None or not state.verification.passed:
                return self._terminal_failure(state, "Invariant violated: cannot present exercise unless verification OutcomeKind.Pass")
            if state.pending_exercise_view is None:
                return self._terminal_failure(state, "Missing pending_exercise_view")

            gate = self._tool_executor.call(
                state,
                self._tools.gate_exercise_view,
                args={"artifact_id": state.pending_exercise_view.artifact_id},
                call_kwargs={"view": state.pending_exercise_view},
                state_node=AgentNode.PresentationGate,
            )
            if not gate.ok:
                state.errors.append(gate.error)
                return self._terminal_failure(state, "exercise presentation gate tool failed")

            self._emit(
                state,
                TraceEventType.presentation_gate,
                AgentNode.PresentationGate,
                {"kind": kind.value, "outcome_kind": gate.result.kind.value, "reason": gate.result.reason},
            )

            if not gate.result.passed:
                return self._terminal_failure(state, f"Exercise presentation blocked: {gate.result.reason}")

            io.present_exercise(gate.result.value)

        elif kind == PresentationKind.grade:
            if state.pending_grade is None:
                return self._terminal_failure(state, "Missing pending_grade")

            gate = self._tool_executor.call(
                state,
                self._tools.gate_grade_report,
                args={"artifact_id": state.pending_grade.artifact_id},
                call_kwargs={"grade": state.pending_grade},
                state_node=AgentNode.PresentationGate,
            )
            if not gate.ok:
                state.errors.append(gate.error)
                return self._terminal_failure(state, "grade presentation gate tool failed")

            if not gate.result.passed:
                # Fallback: withhold traces, keep pass/fail info.
                scrubbed = state.pending_grade.model_copy(
                    update={
                        "test_results": [
                            tr.model_copy(update={"sanitized_trace": "<withheld by presentation gate>"})
                            for tr in state.pending_grade.test_results
                        ]
                    }
                )
                gate2 = self._tools.gate_grade_report.run(grade=scrubbed).result
                if not gate2.passed:
                    return self._terminal_failure(state, "Grade presentation blocked (even after scrubbing).")
                state.pending_grade = gate2.value

            self._emit(
                state,
                TraceEventType.presentation_gate,
                AgentNode.PresentationGate,
                {"kind": kind.value, "outcome_kind": gate.result.kind.value, "reason": gate.result.reason},
            )

            io.show_grade(state.pending_grade)

        elif kind == PresentationKind.hint:
            if state.pending_hint is None:
                return self._terminal_failure(state, "Missing pending_hint")
            # Derive expected fn name (best-effort).
            expected_fn = None
            if state.artifact_id:
                try:
                    art = self._store.get(state.artifact_id)
                    # Very light: first top-level fn name in reference solution
                    import ast
                    tree = ast.parse(art.reference_solution.get_secret_value())
                    for node in tree.body:
                        if isinstance(node, ast.FunctionDef):
                            expected_fn = node.name
                            break
                except Exception:
                    expected_fn = None

            gate = self._tool_executor.call(
                state,
                self._tools.gate_hint,
                args={"level": state.pending_hint.level, "artifact_id": state.artifact_id or "unknown"},
                call_kwargs={"hint": state.pending_hint, "policy": state.policy, "expected_fn": expected_fn},
                state_node=AgentNode.PresentationGate,
            )
            if not gate.ok:
                state.errors.append(gate.error)
                return self._terminal_failure(state, "hint presentation gate tool failed")

            if not gate.result.passed:
                # Fallback: safe generic hint
                fallback = HintArtifact(
                    level=state.pending_hint.level,
                    hint_md="Hint withheld by safety policy. Focus on the first failing test and inspect your edge-case handling.",
                    reveals_solution=False,
                    based_on={"withheld_reason": gate.result.reason or "policy"},
                )
                gate2 = self._tools.gate_hint.run(hint=fallback, policy=state.policy, expected_fn=expected_fn).result
                if not gate2.passed:
                    return self._terminal_failure(state, "Hint presentation blocked (even after fallback).")
                state.pending_hint = gate2.value
                outcome_kind = gate.result.kind.value
                reason = gate.result.reason
            else:
                state.pending_hint = gate.result.value
                outcome_kind = gate.result.kind.value
                reason = gate.result.reason

            self._emit(
                state,
                TraceEventType.presentation_gate,
                AgentNode.PresentationGate,
                {"kind": kind.value, "outcome_kind": outcome_kind, "reason": reason},
            )

            io.show_hint(state.pending_hint)

        else:
            return self._terminal_failure(state, f"Unknown presentation kind: {kind}")

        # Clear pending presentation fields.
        state.pending_presentation_kind = None
        state.pending_exercise_view = None
        state.pending_grade = None
        state.pending_hint = None
        state.post_presentation_state = None

        state.current_state = post
        return state

    def _handle_await_submission(self, state: AgentState, io: SessionIO, specs: Sequence[ExerciseSpec]) -> AgentState:
        assert state.artifact_id is not None
        artifact = self._store.get(state.artifact_id)

        code = io.get_submission(artifact_id=artifact.artifact_id, starter_code=artifact.starter_code)
        if not code.strip():
            return self._terminal_failure(state, "empty submission")

        submission = Submission(artifact_id=artifact.artifact_id, learner_code=code, submitted_at=utc_now())
        state.attempts.append(AttemptRecord(submission=submission))
        state.current_state = AgentNode.GradeSubmission
        return state

    def _handle_grade_submission(self, state: AgentState, io: SessionIO, specs: Sequence[ExerciseSpec]) -> AgentState:
        assert state.spec is not None
        attempt = state.attempts[-1]

        attempt_index = len(state.attempts) - 1
        submission_code_hash = stable_hash(attempt.submission.learner_code)

        res = self._tool_executor.call(
            state,
            self._tools.grade,
            args={
                "artifact_id": attempt.submission.artifact_id,
                "attempt_index": attempt_index,
                "submission_code_hash": submission_code_hash,
            },
            call_kwargs={"submission": attempt.submission, "constraints": state.spec.constraints},
            state_node=AgentNode.GradeSubmission,
        )
        if not res.ok:
            state.errors.append(res.error)
            return self._terminal_failure(state, "grading tool failed")

        attempt.grade = res.result
        self._emit(
            state,
            TraceEventType.grade_status,
            AgentNode.GradeSubmission,
            {
                "artifact_id": attempt.grade.artifact_id,
                "passed": attempt.grade.passed,
                "score": attempt.grade.score,
                "attempt": attempt_index,
            },
        )

        state.pending_presentation_kind = PresentationKind.grade
        state.pending_grade = attempt.grade
        state.post_presentation_state = AgentNode.TerminalSuccess if attempt.grade.passed else AgentNode.ProduceHintOrFeedback
        state.current_state = AgentNode.PresentationGate
        return state

    def _handle_hint_or_feedback(self, state: AgentState, io: SessionIO, specs: Sequence[ExerciseSpec]) -> AgentState:
        assert state.spec is not None
        attempt_index = len(state.attempts) - 1
        attempt = state.attempts[-1]
        assert attempt.grade is not None

        if len(state.attempts) >= self._config.max_attempts:
            return self._terminal_failure(state, "max_attempts exceeded")

        hint_level = min(len(attempt.hints_used) + 1, state.policy.max_hint_level)

        res = self._tool_executor.call(
            state,
            self._tools.hint,
            args={
                "artifact_id": attempt.grade.artifact_id,
                "hint_level": hint_level,
                "attempt_index": attempt_index,
            },
            call_kwargs={
                "grade": attempt.grade,
                "hint_level": hint_level,
                "policy": state.policy,
                "attempt_index": attempt_index,
            },
            state_node=AgentNode.ProduceHintOrFeedback,
        )
        if not res.ok:
            state.errors.append(res.error)
            return self._terminal_failure(state, "hint tool failed")

        hint = res.result
        attempt.hints_used.append(hint)
        self._emit(
            state,
            TraceEventType.hint_issued,
            AgentNode.ProduceHintOrFeedback,
            {"level": hint.level, "reveals_solution": hint.reveals_solution, "attempt": attempt_index},
        )

        state.pending_presentation_kind = PresentationKind.hint
        state.pending_hint = hint
        state.post_presentation_state = AgentNode.AwaitSubmission
        state.current_state = AgentNode.PresentationGate
        return state

    def _handle_summarize_and_log(self, state: AgentState, io: SessionIO, specs: Sequence[ExerciseSpec]) -> AgentState:
        # Placeholder seam: add summaries, analytics, memory, etc.
        self._maybe_append_memory_summary(state)
        state.current_state = AgentNode.TerminalSuccess
        return state

    def _maybe_append_memory_summary(self, state: AgentState) -> None:
        """Best-effort summary capture.

        This is *not* on the critical path for the verified loop:
        if memory is missing or fails, we ignore it.
        """
        if self._tools.memory_append is None or state.spec is None:
            return

        try:
            last_grade = None
            total_hints = 0
            for a in state.attempts:
                if a.grade is not None:
                    last_grade = a.grade
                total_hints += len(a.hints_used)

            outcome = None if last_grade is None else bool(last_grade.passed)
            concepts = ",".join(state.spec.concepts)
            content = (
                f"session_summary concepts=[{concepts}] difficulty={state.spec.difficulty} "
                f"passed={outcome} attempts={len(state.attempts)} hints={total_hints}"
            )

            item = MemoryItem.make(
                id=memory_item_id(content=content, tags={"concepts": concepts}),
                kind=MemoryKind.outcome,
                content=content,
                tags={"concepts": concepts, "difficulty": str(state.spec.difficulty)},
                metadata={"run_id": state.run_id, "final_state": state.current_state.value},
            )

            _ = self._tools.memory_append.run(item=item)
        except Exception:
            # Never fail the run because memory capture failed.
            return

    # ----------------------------
    # Recording helpers
    # ----------------------------

    def _maybe_write_manifest(self, state: AgentState) -> None:
        if not (self._config.research.enabled and self._run_store is not None):
            return

        manifest = RunManifest(
            run_id=state.run_id,
            created_at=utc_now(),
            runtime_config={
                "max_steps": self._config.max_steps,
                "max_regenerations_per_spec": self._config.max_regenerations_per_spec,
                "max_attempts": self._config.max_attempts,
                "verification_repeats": self._config.verification_repeats,
                "max_repeated_tool_failures": self._config.max_repeated_tool_failures,
                "tool_retry": {
                    "max_retries": self._config.tool_retry.max_retries,
                    "retry_backoff_ms": self._config.tool_retry.retry_backoff_ms,
                },
                "research": {
                    "enabled": self._config.research.enabled,
                    "record_tool_io": self._config.research.record_tool_io,
                    "tool_io_capture": self._config.research.tool_io_capture.value,
                    "redact_tool_io": self._config.research.redact_tool_io,
                    "record_state_snapshots": self._config.research.record_state_snapshots,
                    "snapshot_every_n_steps": self._config.research.snapshot_every_n_steps,
                    "crash_after_step": self._config.research.crash_after_step,
                },
                "budgets": {
                    "enabled": bool(getattr(self._config, "budgets", None) and self._config.budgets.enabled),
                    "limits": {k.value: int(v) for k, v in (self._config.budgets.limits.limits if getattr(self._config, "budgets", None) else {}).items()},
                },
            },
            tool_versions=dict(state.versions.tool_versions),
            generator_version=state.versions.generator_version or "unknown",
            tags=dict(self._config.research.tags),
        )
        self._run_store.write_manifest(manifest)

    def _maybe_snapshot(self, state: AgentState) -> None:
        if not (self._config.research.enabled and self._run_store is not None):
            return
        if not self._config.research.record_state_snapshots:
            return

        n = max(1, int(self._config.research.snapshot_every_n_steps))
        if (state.metrics.step_count % n) != 0:
            return

        snap = StateSnapshot.from_state(run_id=state.run_id, step_index=state.metrics.step_count, state=state)
        self._run_store.append_state_snapshot(snap)

    # ----------------------------
    # Trace helpers
    # ----------------------------

    def _emit(self, state: AgentState, event_type: TraceEventType, node: AgentNode, details: Dict[str, Any]) -> None:
        event = TraceEvent(ts=utc_now(), run_id=state.run_id, event_type=event_type, state=node, details=details)
        _ = self._tools.trace_log.run(event=event)

    def _terminal_failure(self, state: AgentState, message: str) -> AgentState:
        state.errors.append(AgentError(message=message, details={}))
        state.current_state = AgentNode.TerminalFailure
        return state
