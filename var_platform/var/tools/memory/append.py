from __future__ import annotations

from ..base import Tool, ToolResult
from ...memory.store import MemoryStore
from ...memory.types import MemoryItem


class MemoryAppendTool(Tool):
    name = "memory.append"
    version = "memory-append-v1"

    def __init__(self, store: MemoryStore):
        self._store = store

    def run(self, *, item: MemoryItem) -> ToolResult[MemoryItem]:
        self._store.append(item)
        return ToolResult.success(item)
