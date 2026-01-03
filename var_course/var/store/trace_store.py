from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from pydantic import TypeAdapter

from ..types import TraceEvent


class FileTraceStore:
    """Append-only JSONL trace store, keyed by `run_id`."""

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.traces_dir = self.root_dir / "traces"
        self.traces_dir.mkdir(parents=True, exist_ok=True)

        self._adapter = TypeAdapter(TraceEvent)

    def _path(self, run_id: str) -> Path:
        return self.traces_dir / f"run_{run_id}.jsonl"

    def log(self, event: TraceEvent) -> None:
        path = self._path(event.run_id)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False))
            f.write("\n")

    def export(self, run_id: str) -> List[TraceEvent]:
        path = self._path(run_id)
        if not path.exists():
            return []
        events: List[TraceEvent] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            events.append(self._adapter.validate_python(raw))
        return events
