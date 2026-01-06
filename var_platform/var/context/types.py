from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class ContextKind(str, Enum):
    system = "system"
    memory = "memory"
    retrieval = "retrieval"
    conversation = "conversation"
    rubric = "rubric"


class ContextChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ContextKind
    content: str
    priority: int = 0
    tags: Dict[str, Any] = Field(default_factory=dict)


class ContextPacket(BaseModel):
    """A context packet is a deterministic, ordered set of chunks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunks: List[ContextChunk]

    def render(self) -> str:
        # Simple default rendering (chunk headers help debugging).
        out: List[str] = []
        for c in sorted(self.chunks, key=lambda x: (-x.priority, x.kind.value)):
            out.append(f"## {c.kind.value}\n{c.content.strip()}\n")
        return "\n".join(out).strip() + "\n"
