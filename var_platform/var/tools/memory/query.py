from __future__ import annotations

from typing import List

from ..base import Tool, ToolResult
from ...memory.store import MemoryStore
from ...memory.types import MemoryItem, MemoryQuery


class MemoryQueryTool(Tool):
    name = "memory.query"
    version = "memory-query-v1"

    def __init__(self, store: MemoryStore):
        self._store = store

    def run(self, *, query: MemoryQuery) -> ToolResult[List[MemoryItem]]:
        return ToolResult.success(self._store.query(query))
