from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from ..research.redaction import redact_jsonable, to_jsonable
from ..research.types import ToolCallRecord, ToolIOCapture, utc_now
from ..store.run_store import FileRunStore
from ..tools.base import Tool, ToolResult
from ..types import AgentNode, AgentState, ToolError, ToolErrorCode, TraceEventType, stable_hash


@dataclass(frozen=True)
class ToolExecutorConfig:
    """Configuration for tool execution behavior.

    Keeping this separate from `RuntimeConfig` makes it easy to compare strategies in papers.
    """

    max_retries: int = 1
    retry_backoff_ms: int = 0


class ToolExecutor:
    """Executes tools with tracing, bounded retries, and optional research recording.

    This is intentionally a small component: it defines where "agent meets the world".
    It is a great thesis seam:

    - swap retry strategies
    - add hedged requests
    - enforce budgets
    - insert remote tool servers
    """

    def __init__(
        self,
        *,
        emit: Callable[[AgentState, TraceEventType, AgentNode, Dict[str, Any]], None],
        run_store: Optional[FileRunStore],
        executor_cfg: ToolExecutorConfig,
        tool_io_capture: ToolIOCapture = ToolIOCapture.safe,
        record_tool_io: bool = False,
        redact_tool_io: bool = True,
    ):
        self._emit = emit
        self._run_store = run_store
        self._cfg = executor_cfg
        self._tool_io_capture = tool_io_capture
        self._record_tool_io = record_tool_io
        self._redact_tool_io = redact_tool_io

        # Monotonic-ish counter for analysis (does not have to match metrics.tool_calls).
        self._call_index = 0

    def call(
        self,
        state: AgentState,
        tool: Tool,
        *,
        args: Dict[str, Any],
        call_kwargs: Dict[str, Any],
        state_node: AgentNode,
    ) -> ToolResult:
        """Call a tool with retry + bookkeeping.

        `args` is a JSON-ish dict used for stable hashing and trace/logging.
        `call_kwargs` are the actual typed objects passed to the tool.
        """
        args_hash = stable_hash(args)
        repeat_key = f"{tool.name}:{args_hash}"

        max_attempts = max(1, int(self._cfg.max_retries) + 1)

        last_res: ToolResult | None = None
        for attempt in range(max_attempts):
            self._emit(
                state,
                TraceEventType.tool_called,
                state_node,
                {
                    "tool": tool.name,
                    "tool_version": getattr(tool, "version", "unknown"),
                    "args_hash": args_hash,
                    "attempt": attempt,
                },
            )

            t0 = time.time()
            res = tool.run(**call_kwargs)
            dt_ms = int((time.time() - t0) * 1000)

            # Count each attempt (useful for cost/latency proxies).
            state.metrics.tool_calls += 1
            self._call_index += 1

            self._emit(
                state,
                TraceEventType.tool_result,
                state_node,
                {
                    "tool": tool.name,
                    "tool_version": getattr(tool, "version", "unknown"),
                    "ok": res.ok,
                    "latency_ms": dt_ms,
                    "attempt": attempt,
                    "error_code": getattr(res.error, "code", None).value if not res.ok else None,
                    "retryable": getattr(res.error, "retryable", False) if not res.ok else False,
                },
            )

            if self._record_tool_io and self._run_store is not None:
                self._record_call(
                    state=state,
                    state_node=state_node,
                    tool=tool,
                    args_hash=args_hash,
                    args=args,
                    res=res,
                    latency_ms=dt_ms,
                    attempt=attempt,
                    call_index=self._call_index,
                )

            if res.ok:
                return res

            last_res = res
            retryable = bool(getattr(res.error, "retryable", False))

            if retryable and (attempt + 1) < max_attempts:
                if self._cfg.retry_backoff_ms > 0:
                    time.sleep(self._cfg.retry_backoff_ms / 1000.0)
                continue

            # Final failure (no retry left or non-retryable).
            state.add_tool_repeat(repeat_key)
            return res

        # Defensive fallback.
        if last_res is not None:
            state.add_tool_repeat(repeat_key)
            return last_res
        return ToolResult.failure(
            ToolError(
                code=ToolErrorCode.PermanentError,
                retryable=False,
                safe_message="ToolExecutor reached an impossible state.",
                debug={"tool": tool.name, "args_hash": args_hash},
            )
        )

    def _record_call(
        self,
        *,
        state: AgentState,
        state_node: AgentNode,
        tool: Tool,
        args_hash: str,
        args: Dict[str, Any],
        res: ToolResult,
        latency_ms: int,
        attempt: int,
        call_index: int,
    ) -> None:
        # Convert to JSON-ish first.
        args_payload = to_jsonable(args)

        result_payload = None
        result_hash = None

        # Capture typed error separately so we can drop debug in safe/hash_only modes.
        error_for_log: ToolError | None = None

        if res.ok:
            result_payload = to_jsonable(res.result)
            try:
                result_hash = stable_hash(result_payload)
            except Exception:
                result_hash = stable_hash(repr(result_payload))
        else:
            error_for_log = res.error
            try:
                result_hash = stable_hash(to_jsonable(res.error))
            except Exception:
                result_hash = stable_hash(repr(res.error))

        capture = self._tool_io_capture

        if capture == ToolIOCapture.hash_only:
            args_payload = None
            result_payload = None
            if error_for_log is not None:
                error_for_log = error_for_log.model_copy(update={"debug": {}})
        elif capture == ToolIOCapture.safe:
            if self._redact_tool_io:
                args_payload = redact_jsonable(args_payload)
                if result_payload is not None:
                    result_payload = redact_jsonable(result_payload)
                if error_for_log is not None:
                    # Keep error code + safe_message, drop debug.
                    error_for_log = error_for_log.model_copy(update={"debug": {}})
        # capture == full -> store everything as-is

        record = ToolCallRecord(
            ts=utc_now(),
            run_id=state.run_id,
            state=state_node,
            tool_name=tool.name,
            tool_version=getattr(tool, "version", "unknown"),
            call_index=call_index,
            args_hash=args_hash,
            attempt_index=attempt,
            latency_ms=latency_ms,
            ok=res.ok,
            args=args_payload,
            result=result_payload,
            error=error_for_log,
            result_hash=result_hash,
        )

        self._run_store.append_tool_call(record)
