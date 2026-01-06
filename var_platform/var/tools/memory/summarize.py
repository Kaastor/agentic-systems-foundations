from __future__ import annotations

from typing import List

from ..base import Tool, ToolResult
from ...memory.types import MemoryItem


class MemorySummarizeTool(Tool):
    """Deterministic summarizer for memory items.

    This exists so the kernel can remain verified/deterministic even when you
    add "summaries" to UX.

    You can later swap this implementation to a ModelTool-backed one, but the
    Tool boundary stays the same.
    """

    name = "memory.summarize"
    version = "memory-summarize-v1"

    def run(self, *, items: List[MemoryItem], max_chars: int = 800) -> ToolResult[str]:
        # Newest first, short bullet lines.
        lines: List[str] = []
        for it in items[:50]:
            lines.append(f"- [{it.kind.value}] {it.content}")
        out = "\n".join(lines)
        if len(out) > max_chars:
            out = out[: max_chars - 3] + "..."
        return ToolResult.success(out)
