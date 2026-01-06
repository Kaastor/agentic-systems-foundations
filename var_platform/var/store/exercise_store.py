from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from pydantic import TypeAdapter

from ..research.redaction import to_jsonable
from ..types import ExerciseArtifact


class ExerciseStore:
    """A tiny versioned filesystem store for exercise artifacts.

    Files are written as JSON and keyed by `artifact_id`.
    """

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.artifacts_dir = self.root_dir / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self._adapter = TypeAdapter(ExerciseArtifact)

    def put(self, artifact: ExerciseArtifact) -> None:
        path = self.artifacts_dir / f"{artifact.artifact_id}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(to_jsonable(artifact, reveal_secrets=True), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)

    def get(self, artifact_id: str) -> ExerciseArtifact:
        path = self.artifacts_dir / f"{artifact_id}.json"
        if not path.exists():
            raise KeyError(f"Artifact not found: {artifact_id}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        return self._adapter.validate_python(raw)

    def exists(self, artifact_id: str) -> bool:
        return (self.artifacts_dir / f"{artifact_id}.json").exists()

    def list_ids(self) -> Iterable[str]:
        for p in sorted(self.artifacts_dir.glob("*.json")):
            yield p.stem
