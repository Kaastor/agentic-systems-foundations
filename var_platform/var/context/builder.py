from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..budgets.manager import BudgetExceeded, BudgetManager
from ..budgets.types import BudgetCategory
from ..memory.types import MemoryItem, MemoryQuery
from ..tools.memory.query import MemoryQueryTool
from ..types import ExerciseSpec
from .types import ContextChunk, ContextKind, ContextPacket


@dataclass(frozen=True)
class ContextBuilder:
    """Builds deterministic context packets.

    This is the "context engineering" seam:
    - you can unit-test it
    - you can swap in vector retrieval later
    - you can apply size budgets
    """

    max_chars: int = 6_000
    memory_limit: int = 8

    def build(
        self,
        *,
        spec: ExerciseSpec,
        memory_query: Optional[MemoryQueryTool] = None,
        budgets: Optional[BudgetManager] = None,
    ) -> ContextPacket:
        chunks: List[ContextChunk] = []

        # System / task framing.
        chunks.append(
            ContextChunk(
                kind=ContextKind.system,
                priority=100,
                content=(
                    "You are a careful tutor. Do not guess. Prefer deterministic checking. "
                    "Do not reveal hidden tests or reference solutions."
                ),
                tags={"policy": "default"},
            )
        )

        # Spec (acts like a lightweight rubric).
        chunks.append(
            ContextChunk(
                kind=ContextKind.rubric,
                priority=90,
                content=f"concepts={spec.concepts} difficulty={spec.difficulty} task_type={spec.task_type.value}",
                tags={"spec": True},
            )
        )

        # Memory retrieval (optional).
        if memory_query is not None:
            q = MemoryQuery(text=" ".join(spec.concepts), limit=self.memory_limit)
            items: List[MemoryItem] = []
            try:
                res = memory_query.run(query=q)
                if res.ok:
                    items = list(res.result)
            except Exception:
                items = []

            if items:
                mem_lines = [f"- {it.content}" for it in items]
                chunks.append(
                    ContextChunk(
                        kind=ContextKind.memory,
                        priority=50,
                        content="\n".join(mem_lines),
                        tags={"count": len(items)},
                    )
                )

        packet = ContextPacket(chunks=chunks)
        rendered = packet.render()

        # Enforce size budget deterministically.
        if len(rendered) > self.max_chars:
            rendered = rendered[: self.max_chars - 3] + "..."
            packet = ContextPacket(chunks=[ContextChunk(kind=ContextKind.system, content=rendered, priority=0)])

        # Optional budget accounting.
        if budgets is not None:
            try:
                budgets.spend(BudgetCategory.retrieval_chars, len(rendered), reason="context_chars")
            except BudgetExceeded:
                # If you exceed context budget, return the minimal system chunk.
                packet = ContextPacket(
                    chunks=[
                        ContextChunk(
                            kind=ContextKind.system,
                            priority=100,
                            content="Context budget exceeded. Proceed with minimal instructions.",
                        )
                    ]
                )

        return packet
