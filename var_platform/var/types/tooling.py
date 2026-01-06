from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from .enums import ToolErrorCode


class ToolError(BaseModel):
    """Typed tool boundary error.

    This is the contract between the orchestrator (caller) and tools/external systems.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ToolErrorCode
    retryable: bool
    safe_message: str
    debug: Dict[str, Any] = Field(default_factory=dict)
