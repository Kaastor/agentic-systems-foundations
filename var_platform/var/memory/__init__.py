"""Memory: persistent learner/session context.

This repo keeps memory deliberately *boring* and deterministic:

- append-only JSONL storage
- simple substring queries

Why? Because it's a teaching repo. You can later swap in:
- vector DB retrieval
- summaries via ModelTool
- per-learner mastery models

...without changing the agent kernel contracts.
"""

from .types import MemoryItem, MemoryKind, MemoryQuery
from .store import FileMemoryStore, MemoryStore

__all__ = [
    "MemoryItem",
    "MemoryKind",
    "MemoryQuery",
    "MemoryStore",
    "FileMemoryStore",
]
