from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional

from pydantic import TypeAdapter

from ..agent.tool_executor import ToolExecutorConfig
from ..store.run_store import FileRunStore
from ..tools.base import Tool, ToolResult
from ..types import (
    AgentNode,
    AgentState,
    ExerciseArtifact,
    ExerciseDraft,
    GradeReport,
    HintArtifact,
    TraceEventType,
    ToolError,
    ToolErrorCode,
    VerificationReport,
    stable_hash,
)


@dataclass
class ReplayCursor:
    idx: int = 0


class ReplayToolExecutor:
    """A tool executor that replays recorded tool outputs.

    Replay is the backbone of "research mode": it lets you compare orchestration strategies
    on identical tool I/O, and enables time-travel debugging without running the sandbox.

    Replay requires that the recorded run captured tool outputs in a form sufficient to
    reconstruct typed objects (typically ToolIOCapture.full).
    """

    def __init__(
        self,
        *,
        emit: Callable[[AgentState, TraceEventType, AgentNode, Dict[str, Any]], None],
        run_store: FileRunStore,
        recorded_run_id: str,
        executor_cfg: ToolExecutorConfig,
        adapters: Optional[Mapping[str, TypeAdapter]] = None,
    ):
        self._emit = emit
        self._cfg = executor_cfg

        self._records = sorted(run_store.load_tool_calls(recorded_run_id), key=lambda r: r.call_index)
        self._cursor = ReplayCursor(0)

        self._adapters: Dict[str, TypeAdapter] = dict(adapters or {})
        if not self._adapters:
            # Default adapters for the baseline VAR tool set.
            self._adapters = {
                "exercise.generate_draft": TypeAdapter(ExerciseDraft),
                "exercise.compile": TypeAdapter(ExerciseArtifact),
                "exercise.verify": TypeAdapter(VerificationReport),
                "grader.grade": TypeAdapter(GradeReport),
                "tutor.make_hint": TypeAdapter(HintArtifact),
            }

    def call(
        self,
        state: AgentState,
        tool: Tool,
        *,
        args: Dict[str, Any],
        call_kwargs: Dict[str, Any],
        state_node: AgentNode,
    ) -> ToolResult:
        """Replay the next matching tool call sequence.

        `call_kwargs` is accepted for interface compatibility but not used.
        """
        _ = call_kwargs

        args_hash = stable_hash(args)

        start = self._find_next(tool.name, args_hash)
        if start is None:
            return ToolResult.failure(
                ToolError(
                    code=ToolErrorCode.Conflict,
                    retryable=False,
                    safe_message=f"No recorded call for tool={tool.name} args_hash={args_hash}",
                    debug={"tool": tool.name, "args_hash": args_hash, "cursor": self._cursor.idx},
                )
            )

        max_attempts = max(1, int(self._cfg.max_retries) + 1)
        last_res: ToolResult | None = None

        for attempt in range(max_attempts):
            idx = start + attempt
            if idx >= len(self._records):
                break
            rec = self._records[idx]
            if rec.tool_name != tool.name or rec.args_hash != args_hash:
                break

            self._emit(
                state,
                TraceEventType.tool_called,
                state_node,
                {
                    "tool": tool.name,
                    "tool_version": rec.tool_version,
                    "args_hash": args_hash,
                    "attempt": attempt,
                    "replay": True,
                },
            )
            self._emit(
                state,
                TraceEventType.tool_result,
                state_node,
                {
                    "tool": tool.name,
                    "tool_version": rec.tool_version,
                    "ok": rec.ok,
                    "latency_ms": rec.latency_ms,
                    "attempt": attempt,
                    "error_code": rec.error.code.value if rec.error else None,
                    "retryable": rec.error.retryable if rec.error else False,
                    "replay": True,
                },
            )

            state.metrics.tool_calls += 1
            self._cursor.idx = max(self._cursor.idx, idx + 1)

            if rec.ok:
                adapter = self._adapters.get(tool.name)
                if adapter is None:
                    return ToolResult.failure(
                        ToolError(
                            code=ToolErrorCode.ValidationError,
                            retryable=False,
                            safe_message=f"No output adapter registered for tool name {tool.name!r}",
                            debug={"tool": tool.name},
                        )
                    )
                if rec.result is None:
                    return ToolResult.failure(
                        ToolError(
                            code=ToolErrorCode.PermanentError,
                            retryable=False,
                            safe_message=(
                                "Recorded result is missing. "
                                "The recorded run probably did not use ToolIOCapture.full."
                            ),
                            debug={"tool": tool.name, "call_index": rec.call_index},
                        )
                    )
                obj = adapter.validate_python(rec.result)
                return ToolResult.success(obj)

            # Failure
            if rec.error is None:
                return ToolResult.failure(
                    ToolError(
                        code=ToolErrorCode.PermanentError,
                        retryable=False,
                        safe_message="Recorded failure is missing ToolError payload.",
                        debug={"tool": tool.name, "call_index": rec.call_index},
                    )
                )

            last_res = ToolResult.failure(rec.error)
            if not rec.error.retryable:
                return last_res

        return last_res or ToolResult.failure(
            ToolError(
                code=ToolErrorCode.PermanentError,
                retryable=False,
                safe_message="Replay could not find a completed call sequence.",
                debug={"tool": tool.name, "args_hash": args_hash},
            )
        )

    def _find_next(self, tool_name: str, args_hash: str) -> Optional[int]:
        for i in range(self._cursor.idx, len(self._records)):
            r = self._records[i]
            if r.tool_name == tool_name and r.args_hash == args_hash and r.attempt_index == 0:
                return i
        return None
