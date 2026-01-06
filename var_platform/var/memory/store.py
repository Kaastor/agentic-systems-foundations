from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Protocol

from pydantic import TypeAdapter

from ..research.redaction import redact_jsonable, to_jsonable
from ..types import stable_hash
from .types import MemoryItem, MemoryQuery


class MemoryStore(Protocol):
    """A minimal interface for persistent memory."""

    def append(self, item: MemoryItem) -> None: ...

    def query(self, q: MemoryQuery) -> List[MemoryItem]: ...


@dataclass
class FileMemoryStore(MemoryStore):
    """Append-only JSONL memory store.

    Storage format is intentionally simple:
    - each line is one JSON object
    - items are schema-validated on read

    This is good enough for a teaching repo and can be swapped behind the same
    interface for vector DBs or SQL later.
    """

    root: Path
    filename: str = "memory.jsonl"
    redact_on_write: bool = True

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._path = self.root / self.filename
        self._adapter = TypeAdapter(MemoryItem)

    def append(self, item: MemoryItem) -> None:
        payload = to_jsonable(item, reveal_secrets=True)
        if self.redact_on_write:
            payload = redact_jsonable(payload)
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _iter_items(self) -> Iterable[MemoryItem]:
        if not self._path.exists():
            return []
        items: List[MemoryItem] = []
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    items.append(self._adapter.validate_python(raw))
                except Exception:
                    # Skip corrupted line; keep store resilient.
                    continue
        return items

    def query(self, q: MemoryQuery) -> List[MemoryItem]:
        text = (q.text or "").strip().lower()
        required = dict(q.required_tags)
        out: List[MemoryItem] = []

        # Newest first is usually what you want for tutoring.
        for item in reversed(list(self._iter_items())):
            if text and text not in item.content.lower():
                continue
            ok = True
            for k, v in required.items():
                if item.tags.get(k) != v:
                    ok = False
                    break
            if not ok:
                continue
            out.append(item)
            if len(out) >= q.limit:
                break
        return out


def memory_item_id(*, content: str, tags: dict[str, str] | None = None) -> str:
    """Deterministic ID helper for memory items."""

    return stable_hash({"content": content, "tags": tags or {}})[:12]
