from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("agentic.tracer")


@dataclass
class Tracer:
    """Extremely small structured logger.

    It writes one JSON object per line into ``runs/<run_id>.trace.jsonl`` and
    also lets us feed structured logs into a normal logging stack.
    """

    run_id: str
    runs_dir: Path

    def __post_init__(self) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.runs_dir / f"{self.run_id}.trace.jsonl"

    def log(self, step_index: int, node: str, message: str, **extra: Any) -> None:
        record = {
            "ts": datetime.utcnow().isoformat(),
            "run_id": self.run_id,
            "step_index": step_index,
            "node": node,
            "message": message,
            "extra": extra,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        logger.info("trace: %s", json.dumps(record, default=str))
