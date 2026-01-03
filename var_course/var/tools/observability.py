from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from ..store.trace_store import FileTraceStore
from ..types import TraceEvent
from .base import Tool, ToolResult


class Ack(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ok: bool = True


class TraceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    run_id: str
    events: List[TraceEvent] = Field(default_factory=list)


class TraceLogTool(Tool):
    name = "trace.log"
    version = "jsonl-v1"

    def __init__(self, store: FileTraceStore):
        self._store = store

    def run(self, *, event: TraceEvent) -> ToolResult[Ack]:
        self._store.log(event)
        return ToolResult.success(Ack())


class TraceExportTool(Tool):
    name = "trace.export"
    version = "jsonl-v1"

    def __init__(self, store: FileTraceStore):
        self._store = store

    def run(self, *, run_id: str) -> ToolResult[TraceBundle]:
        events = self._store.export(run_id)
        return ToolResult.success(TraceBundle(run_id=run_id, events=events))
