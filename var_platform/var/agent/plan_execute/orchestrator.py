from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Sequence

from ...config import RuntimeConfig
from ...io import SessionIO
from ...store.exercise_store import ExerciseStore
from ...types import (
    AgentError,
    AgentNode,
    AgentState,
    ExerciseArtifact,
    ExerciseSpec,
    OutcomeKind,
    PresentationKind,
    TraceEventType,
    utc_now,
    stable_hash,
)
from ...tools.exercise_generation import CompileDraftTool, GenerateDraftTool
from ...tools.observability import TraceLogTool
from ...tools.presentation_gate import GateExerciseViewTool
from ...tools.verification import ExerciseVerifyTool

from ..tool_executor import ToolExecutor, ToolExecutorConfig
from .planner import DeterministicExerciseBuildPlanner, Planner
from .types import Plan


@dataclass(frozen=True)
class PlanToolbox:
    generate_draft: GenerateDraftTool
    compile_draft: CompileDraftTool
    verify: ExerciseVerifyTool
    gate_exercise_view: GateExerciseViewTool
    trace_log: TraceLogTool


class PlanExecuteOrchestrator:
    """A small plan/execute orchestrator.

    This does **one thing**: build a verified exercise and present it.

    It exists as an alternative to the FSM so students can compare styles.
    """

    def __init__(
        self,
        *,
        config: RuntimeConfig,
        store: ExerciseStore,
        tools: PlanToolbox,
        planner: Planner | None = None,
        tool_executor: ToolExecutor | None = None,
    ):
        self._config = config
        self._store = store
        self._tools = tools
        self._planner = planner or DeterministicExerciseBuildPlanner()
        self._tool_executor = tool_executor or ToolExecutor(
            emit=self._emit,
            run_store=None,
            executor_cfg=ToolExecutorConfig(
                max_retries=config.tool_retry.max_retries,
                retry_backoff_ms=config.tool_retry.retry_backoff_ms,
            ),
            record_tool_io=False,
            tool_io_capture=config.research.tool_io_capture,
            redact_tool_io=config.research.redact_tool_io,
        )

    def run_session(self, *, io: SessionIO, specs: Sequence[ExerciseSpec]) -> AgentState:
        state = AgentState(run_id=uuid.uuid4().hex[:12])

        started = time.time()
        try:
            chosen = io.choose_spec(specs)
            state.spec = chosen

            plan: Plan = self._planner.build_plan(spec=chosen)
            # Emit the plan as a trace detail (small enough to keep inline).
            self._emit(state, TraceEventType.state_entered, AgentNode.GenerateExercise, {"plan": plan.model_dump(mode="python")})

            # Step 1: generate draft
            res_draft = self._tool_executor.call(
                state,
                self._tools.generate_draft,
                args={"spec": chosen.model_dump(mode="python")},
                call_kwargs={"spec": chosen},
                state_node=AgentNode.GenerateExercise,
            )
            if not res_draft.ok:
                state.errors.append(res_draft.error)
                return self._terminal_failure(state, "generate_draft failed")
            draft = res_draft.result

            # Step 2: compile
            res_art = self._tool_executor.call(
                state,
                self._tools.compile_draft,
                args={"draft": draft.model_dump(mode="python"), "spec": chosen.model_dump(mode="python")},
                call_kwargs={"draft": draft, "spec": chosen},
                state_node=AgentNode.GenerateExercise,
            )
            if not res_art.ok:
                state.errors.append(res_art.error)
                return self._terminal_failure(state, "compile_draft failed")

            artifact: ExerciseArtifact = res_art.result
            self._store.put(artifact)
            state.artifact_id = artifact.artifact_id

            # Step 3: verify
            verify_args = {
                "artifact_id": artifact.artifact_id,
                "constraints": chosen.constraints.model_dump(mode="python"),
                "repeats": self._config.verification_repeats,
            }
            res_verify = self._tool_executor.call(
                state,
                self._tools.verify,
                args=verify_args,
                call_kwargs={
                    "artifact_id": artifact.artifact_id,
                    "constraints": chosen.constraints,
                    "repeats": self._config.verification_repeats,
                },
                state_node=AgentNode.VerifyExercise,
            )
            if not res_verify.ok:
                state.errors.append(res_verify.error)
                return self._terminal_failure(state, "verify tool failed")

            state.verification = res_verify.result
            if not state.verification.passed:
                return self._terminal_failure(state, f"verification failed: {state.verification.kind.value}")

            # Step 4: present (through the same universal gate)
            view = artifact.to_view()
            res_gate = self._tool_executor.call(
                state,
                self._tools.gate_exercise_view,
                args={"view_hash": stable_hash(view.model_dump(mode="python"))},
                call_kwargs={"view": view},
                state_node=AgentNode.PresentationGate,
            )
            if not res_gate.ok:
                state.errors.append(res_gate.error)
                return self._terminal_failure(state, "presentation gate tool failed")

            outcome = res_gate.result
            if outcome.kind != OutcomeKind.Pass:
                return self._terminal_failure(state, f"presentation gate failed: {outcome.kind.value}")

            state.pending_presentation_kind = PresentationKind.exercise
            state.pending_exercise_view = outcome.value
            io.show_exercise(outcome.value)
            state.current_state = AgentNode.TerminalSuccess
            return state
        finally:
            state.metrics.latency_ms = int((time.time() - started) * 1000)

    def _emit(self, state: AgentState, event_type: TraceEventType, node: AgentNode, details: Dict[str, Any]) -> None:
        from ...types import TraceEvent

        event = TraceEvent(ts=utc_now(), run_id=state.run_id, event_type=event_type, state=node, details=details)
        _ = self._tools.trace_log.run(event=event)

    def _terminal_failure(self, state: AgentState, message: str) -> AgentState:
        state.errors.append(AgentError(message=message, details={}))
        state.current_state = AgentNode.TerminalFailure
        return state
