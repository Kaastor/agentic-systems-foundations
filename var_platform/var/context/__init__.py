"""Context engineering utilities.

In modern agent systems, *context* is an engineered artifact:

- what information is included
- what is excluded
- ordering / priority
- size budgets
- redaction

This package is deliberately deterministic so it can be unit-tested.
"""

from .types import ContextChunk, ContextKind, ContextPacket
from .builder import ContextBuilder

__all__ = [
    "ContextKind",
    "ContextChunk",
    "ContextPacket",
    "ContextBuilder",
]
