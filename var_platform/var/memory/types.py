from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..types import utc_now


class MemoryKind(str, Enum):
    """Coarse categories of memory entries."""

    event = "event"
    note = "note"
    outcome = "outcome"
    mastery = "mastery"


class MemoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    ts: Any  # datetime; kept Any to avoid pydantic/date imports in thin stores
    kind: MemoryKind = MemoryKind.event
    content: str
    tags: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def make(
        cls,
        *,
        id: str,
        kind: MemoryKind,
        content: str,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "MemoryItem":
        return cls(
            id=id,
            ts=utc_now(),
            kind=kind,
            content=content,
            tags=tags or {},
            metadata=metadata or {},
        )


class MemoryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = ""
    required_tags: Dict[str, str] = Field(default_factory=dict)
    limit: int = Field(default=20, ge=1, le=200)