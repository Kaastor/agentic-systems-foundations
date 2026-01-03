from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Sequence

from ..config import RuntimeConfig
from ..io import SessionIO
from ..research.types import RunManifest
from ..store.exercise_store import ExerciseStore
from ..store.run_store import FileRunStore
from ..types import (
    AgentError,
    AgentNode,
    AgentState,
    AttemptRecord,
    ExerciseArtifact,
    ExerciseSpec,
    Submission,
    TraceEvent,
    TraceEventType,
    VerificationStatus,
    utc_now,
    stable_hash,
)
from ..tools.base import Tool
from ..tools.exercise_generation import CompileDraftTool, GenerateDraftTool
from ..tools.grading import GradeSubmissionTool
from ..tools.hinting import MakeHintTool
from ..tools.observability import TraceLogTool
from ..tools.verification import ExerciseVerifyTool

from .tool_executor import ToolExecutor, ToolExecutorConfig
from ..research.types import StateSnapshot


class SimulatedCrash(RuntimeError):
    """Raised when `RuntimeConfig.research.crash_after_step` triggers."""


@dataclass(frozen=True)
class Toolbox:
    generate_draft: GenerateDraftTool
    compile_draft: CompileDraftTool
    verify: ExerciseVerifyTool
    grade: GradeSubmissionTool
    hint: MakeHintTool
    trace_log: TraceLogTool


class VAROrchestrator:
    """Explicit finite-state machine implementing the Verified Agent Runtime."""

    def __init__(
        self,
        *,
        config: RuntimeConfig,
        store: ExerciseStore,
        tools: Toolbox,
        run_store: FileRunStore | None = None,
        tool_executor: ToolExecutor | None = None,
    ):
        self._config = config
        self._store = store
        self._tools = tools
        self._run_store = run_store

        # Default executor is local + deterministic.
        self._tool_executor = tool_executor or ToolExecutor(
            emit=self._emit,
            run_store=run_store,
            executor_cfg=ToolExecutorConfig(
                max_retries=config.tool_retry.max_retries,
                retry_backoff_ms=config.tool_retry.retry_backoff_ms,
            ),
            record_tool_io=bool(config.research.enabled and config.research.record_tool_io),
            tool_io_capture=config.research.tool_io_capture,
            redact_tool_io=config.research.redact_tool_io,
        )

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
        """Run a single VAR session.

        If `initial_state` is provided, the run continues from that checkpoint.
        This supports crash/resume experiments and long-running agents.
        """
        state = initial_state or AgentState(run_id=uuid.uuid4().hex[:12])

        # Capture tool versions for reproducibility (idempotent).
        if not state.versions.tool_versions:
            state.versions.tool_versions = {
                self._tools.generate_draft.name: self._tools.generate_draft.version,
                self._tools.compile_draft.name: self._tools.compile_draft.version,
                self._tools.verify.name: self._tools.verify.version,
                self._tools.grade.name: self._tools.grade.version,
                self._tools.hint.name: self._tools.hint.version,
                self._tools.trace_log.name: self._tools.trace_log.version,
            }

        # Research manifest (written early; can be re-written later with extra tags).
        self._maybe_write_manifest(state)

        started = time.time()
        try:
            while True:
                if state.metrics.step_count >= self._config.max_steps:
                    return self._terminal_failure(state, "max_steps exceeded")

                node = state.current_state
                self._emit(state, TraceEventType.state_entered, node, {})

                if node == AgentNode.SelectSpec:
                    state = self._handle_select_spec(state, io, specs)
                    self._maybe_write_manifest(state)
                elif node == AgentNode.GenerateExercise:
                    state = self._handle_generate_exercise(state)
                elif node == AgentNode.VerifyExercise:
                    state = self._handle_verify_exercise(state)
                elif node == AgentNode.RepairOrRegenerate:
                    state = self._handle_repair_or_regenerate(state, io, specs)
                elif node == AgentNode.PresentExercise:
                    state = self._handle_present_exercise(state, io)
                elif node == AgentNode.AwaitSubmission:
                    state = self._handle_await_submission(state, io)
                elif node == AgentNode.GradeSubmission:
                    state = self._handle_grade_submission(state, io)
                elif node == AgentNode.ProduceHintOrFeedback:
                    state = self._handle_hint_or_feedback(state, io)
                elif node == AgentNode.TerminalSuccess:
                    self._emit(state, TraceEventType.terminal_outcome, node, {"outcome": "success"})
                    self._maybe_snapshot(state)
                    return state
                elif node == AgentNode.TerminalFailure:
                    self._emit(state, TraceEventType.terminal_outcome, node, {"outcome": "failure"})
                    self._maybe_snapshot(state)
                    return state
                else:
                    return self._terminal_failure(state, f"Unhandled node: {node}")

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
    # Handlers
    # ----------------------------

    def _handle_select_spec(self, state: AgentState, io: SessionIO, specs: Sequence[ExerciseSpec]) -> AgentState:
        chosen = io.choose_spec(specs)
        state.spec = chosen
        state.versions.generator_version = chosen.generator_version
        state.current_state = AgentNode.GenerateExercise
        return state

    def _handle_generate_exercise(self, state: AgentState) -> AgentState:
        assert state.spec is not None, "spec must be set before GenerateExercise"

        res_draft = self._tool_executor.call(
            state,
            self._tools.generate_draft,
            args={"spec": state.spec.model_dump(mode="json")},
            call_kwargs={"spec": state.spec},
            state_node=AgentNode.GenerateExercise,
        )
        if not res_draft.ok:
            state.errors.append(res_draft.error)
            state.current_state = AgentNode.RepairOrRegenerate
            return state

        draft = res_draft.result

        res_art = self._tool_executor.call(
            state,
            self._tools.compile_draft,
            args={
                "draft": draft.model_dump(mode="json"),
                "spec": state.spec.model_dump(mode="json"),
            },
            call_kwargs={"draft": draft, "spec": state.spec},
            state_node=AgentNode.GenerateExercise,
        )
        if not res_art.ok:
            state.errors.append(res_art.error)
            state.current_state = AgentNode.RepairOrRegenerate
            return state

        artifact: ExerciseArtifact = res_art.result
        self._store.put(artifact)
        state.artifact_id = artifact.artifact_id
        state.current_state = AgentNode.VerifyExercise
        return state

    def _handle_verify_exercise(self, state: AgentState) -> AgentState:
        assert state.spec is not None and state.artifact_id is not None

        artifact = self._store.get(state.artifact_id)

        res = self._tool_executor.call(
            state,
            self._tools.verify,
            args={
                "artifact_id": artifact.artifact_id,
                "constraints": state.spec.constraints.model_dump(mode="json"),
                "repeats": self._config.verification_repeats,
            },
            call_kwargs={
                "artifact": artifact,
                "constraints": state.spec.constraints,
                "repeats": self._config.verification_repeats,
            },
            state_node=AgentNode.VerifyExercise,
        )

        if not res.ok:
            state.errors.append(res.error)
            state.current_state = AgentNode.RepairOrRegenerate
            return state

        state.verification = res.result
        self._emit(
            state,
            TraceEventType.verification_status,
            AgentNode.VerifyExercise,
            {
                "status": state.verification.status.value,
                "artifact_id": artifact.artifact_id,
                "regen_count": state.loop_counters.regen_count,
            },
        )

        if state.verification.status == VerificationStatus.FAIL:
            # Treat verification FAIL (a *successful tool call* with a FAIL report) as
            # a repeated failing call for loop controls.
            verify_args = {
                "artifact_id": artifact.artifact_id,
                "constraints": state.spec.constraints.model_dump(mode="json"),
                "repeats": self._config.verification_repeats,
            }
            args_hash = stable_hash(verify_args)
            state.add_tool_repeat(f"{self._tools.verify.name}:{args_hash}")

        state.current_state = (
            AgentNode.PresentExercise
            if state.verification.status == VerificationStatus.PASS
            else AgentNode.RepairOrRegenerate
        )
        return state

    def _handle_repair_or_regenerate(
        self, state: AgentState, io: SessionIO, specs: Sequence[ExerciseSpec]
    ) -> AgentState:
        assert state.spec is not None

        if state.loop_counters.regen_count >= self._config.max_regenerations_per_spec:
            return self._terminal_failure(state, "max_regenerations_per_spec exceeded")

        state.loop_counters.regen_count += 1

        # Force-change strategy:
        # - bump seed every time
        # - on repeated failure, rotate to a different spec (next in catalog)
        old_spec = state.spec
        new_seed = old_spec.seed + state.loop_counters.regen_count

        rotate = False
        stuck_key_prefix = f"{self._tools.verify.name}:"
        stuck = any(
            k.startswith(stuck_key_prefix) and v >= self._config.max_repeated_tool_failures
            for k, v in state.loop_counters.tool_repeat_counts.items()
        )
        if stuck:
            rotate = True

        if rotate:
            idx = 0
            for i, s in enumerate(specs):
                if s.signature.name == old_spec.signature.name:
                    idx = i
                    break
            new_spec = specs[(idx + 1) % len(specs)]
            new_spec = new_spec.model_copy(update={"seed": new_seed})
            io.show_message("Repair: rotating to a different exercise template (loop control).")
        else:
            # keep same spec, just change seed + optionally lower difficulty if already high
            new_diff = max(1, old_spec.difficulty - 1) if state.loop_counters.regen_count >= 2 else old_spec.difficulty
            new_spec = old_spec.model_copy(update={"seed": new_seed, "difficulty": new_diff})

        state.spec = new_spec
        state.artifact_id = None
        state.verification = None
        state.current_state = AgentNode.GenerateExercise
        return state

    def _handle_present_exercise(self, state: AgentState, io: SessionIO) -> AgentState:
        assert state.artifact_id is not None and state.verification is not None

        # --- Invariant VAR-INV-1 ---
        if state.verification.status != VerificationStatus.PASS:
            return self._terminal_failure(
                state,
                "Invariant violated: PresentExercise is not allowed unless verification.status == PASS",
            )

        artifact = self._store.get(state.artifact_id)
        io.present_exercise(artifact.view_for_learner())
        state.current_state = AgentNode.AwaitSubmission
        return state

    def _handle_await_submission(self, state: AgentState, io: SessionIO) -> AgentState:
        assert state.artifact_id is not None
        artifact = self._store.get(state.artifact_id)

        code = io.get_submission(artifact_id=artifact.artifact_id, starter_code=artifact.starter_code)
        if not code.strip():
            return self._terminal_failure(state, "empty submission")

        submission = Submission(artifact_id=artifact.artifact_id, learner_code=code, submitted_at=utc_now())
        state.attempts.append(AttemptRecord(submission=submission))
        state.current_state = AgentNode.GradeSubmission
        return state

    def _handle_grade_submission(self, state: AgentState, io: SessionIO) -> AgentState:
        assert state.spec is not None
        attempt = state.attempts[-1]

        # NOTE (research determinism): tool args used for hashing/replay must be stable.
        # `submitted_at` is intentionally excluded because it is time-dependent.
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
                "attempt": len(state.attempts) - 1,
            },
        )
        io.show_grade(attempt.grade)

        state.current_state = AgentNode.TerminalSuccess if attempt.grade.passed else AgentNode.ProduceHintOrFeedback
        return state

    def _handle_hint_or_feedback(self, state: AgentState, io: SessionIO) -> AgentState:
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

        io.show_hint(hint)
        state.current_state = AgentNode.AwaitSubmission
        return state

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
