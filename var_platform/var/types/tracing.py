from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from .enums import AgentNode, TraceEventType


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ts: datetime
    run_id: str
    event_type: TraceEventType
    state: AgentNode
    details: Dict[str, Any] = Field(default_factory=dict)
