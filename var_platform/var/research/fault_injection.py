from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from ..types import ToolError, ToolErrorCode
from ..tools.base import Tool, ToolResult


@dataclass(frozen=True)
class FaultRule:
    """Deterministic fault injection rule.

    Example: fail the 1st call to `exercise.generate_draft` with a retryable TransientError.
    """

    tool_name: str
    nth_call: int  # 1-indexed
    error_code: ToolErrorCode
    retryable: bool
    safe_message: str
    debug: Dict[str, object] | None = None


class FaultInjectingTool(Tool):
    """Wrap another tool and inject deterministic failures.

    This is a *research harness* utility. It lets you benchmark retry logic, loop controls,
    and robustness deterministically.

    Important: This wrapper preserves the wrapped tool's `name` and `version`.
    """

    def __init__(self, inner: Tool, rules: Sequence[FaultRule]):
        self._inner = inner
        self.name = inner.name
        self.version = inner.version

        self._rules_by_n: Dict[int, List[FaultRule]] = {}
        for r in rules:
            if r.tool_name != inner.name:
                continue
            self._rules_by_n.setdefault(int(r.nth_call), []).append(r)

        self._call_count = 0

    def run(self, *args, **kwargs):
        self._call_count += 1
        rules = self._rules_by_n.get(self._call_count, [])
        if rules:
            r = rules[0]
            return ToolResult.failure(
                ToolError(
                    code=r.error_code,
                    retryable=r.retryable,
                    safe_message=r.safe_message,
                    debug=dict(r.debug or {}),
                )
            )
        return self._inner.run(*args, **kwargs)
