from __future__ import annotations

from typing import Any, Dict, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from .enums import OutcomeKind


T = TypeVar("T")


class Outcome(BaseModel, Generic[T]):
    """First-class domain outcome wrapper.

    ToolResult tells you whether the *boundary call* succeeded.
    OutcomeKind tells you whether the *domain goal* succeeded.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: OutcomeKind
    value: Optional[T] = None
    reason: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.kind == OutcomeKind.Pass

    @classmethod
    def ok(cls, value: T, *, details: Optional[Dict[str, Any]] = None) -> "Outcome[T]":
        return cls(kind=OutcomeKind.Pass, value=value, details=details or {})

    @classmethod
    def fail(
        cls,
        *,
        kind: OutcomeKind = OutcomeKind.Fail,
        value: Optional[T] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> "Outcome[T]":
        return cls(kind=kind, value=value, reason=reason, details=details or {})
