from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..types import ToolError, ToolErrorCode

T = TypeVar("T")


class ToolResult(BaseModel, Generic[T]):
    """Standard tool boundary result.

    Tools return either:
    - ok=True, result=<typed output>
    - ok=False, error=<ToolError>

    This makes failure modes explicit and testable.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool
    result: Optional[T] = None
    error: Optional[ToolError] = None

    @model_validator(mode="after")
    def _check_consistency(self) -> "ToolResult[T]":
        if self.ok and self.error is not None:
            raise ValueError("ToolResult(ok=True) cannot include error")
        if (not self.ok) and self.error is None:
            raise ValueError("ToolResult(ok=False) must include error")
        return self

    @classmethod
    def success(cls, result: T) -> "ToolResult[T]":
        return cls(ok=True, result=result)

    @classmethod
    def failure(cls, error: ToolError) -> "ToolResult[T]":
        return cls(ok=False, error=error)


class Tool(ABC):
    """Abstract base class for tools.

    In v0.1 tools are local Python classes, but the same interface supports remote calls later.
    """

    name: str
    version: str

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> ToolResult[Any]:
        raise NotImplementedError

    def __call__(self, *args: Any, **kwargs: Any) -> ToolResult[Any]:
        try:
            return self.run(*args, **kwargs)
        except Exception as e:  # pragma: no cover (defensive)
            return ToolResult.failure(
                ToolError(
                    code=ToolErrorCode.PermanentError,
                    retryable=False,
                    safe_message="Internal tool error.",
                    debug={"exception": repr(e), "tool": self.name, "version": self.version},
                )
            )
