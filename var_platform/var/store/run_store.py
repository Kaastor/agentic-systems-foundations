from __future__ import annotations

import json
from pathlib import Path
from typing import List

from pydantic import TypeAdapter

from ..types import AgentState
from ..research.types import RunBundle, RunManifest, StateSnapshot, ToolCallRecord


class FileRunStore:
    """Per-run storage for research/testbed artifacts.

    Layout under `root_dir`:

        runs/
          run_<run_id>/
            manifest.json
            tool_calls.jsonl
            state_snapshots.jsonl
            latest_state.json

    This is intentionally plain JSON/JSONL so students can analyze it with
    grep/jq/Python/R without extra dependencies.
    """

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.runs_dir = self.root_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        self._manifest_adapter = TypeAdapter(RunManifest)
        self._call_adapter = TypeAdapter(ToolCallRecord)
        self._snapshot_adapter = TypeAdapter(StateSnapshot)
        self._state_adapter = TypeAdapter(AgentState)

    def run_dir(self, run_id: str) -> Path:
        d = self.runs_dir / f"run_{run_id}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_manifest(self, manifest: RunManifest) -> None:
        d = self.run_dir(manifest.run_id)
        path = d / "manifest.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)

    def append_tool_call(self, record: ToolCallRecord) -> None:
        d = self.run_dir(record.run_id)
        path = d / "tool_calls.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False))
            f.write("\n")

    def append_state_snapshot(self, snapshot: StateSnapshot) -> None:
        d = self.run_dir(snapshot.run_id)
        path = d / "state_snapshots.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False))
            f.write("\n")

        # Convenience pointer for "resume from latest" workflows.
        latest = d / "latest_state.json"
        tmp = latest.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(snapshot.state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(latest)

    def load_manifest(self, run_id: str) -> RunManifest:
        d = self.run_dir(run_id)
        raw = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        return self._manifest_adapter.validate_python(raw)

    def load_tool_calls(self, run_id: str) -> List[ToolCallRecord]:
        d = self.run_dir(run_id)
        path = d / "tool_calls.jsonl"
        if not path.exists():
            return []
        out: List[ToolCallRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            out.append(self._call_adapter.validate_python(json.loads(line)))
        return out

    def load_state_snapshots(self, run_id: str) -> List[StateSnapshot]:
        d = self.run_dir(run_id)
        path = d / "state_snapshots.jsonl"
        if not path.exists():
            return []
        out: List[StateSnapshot] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            out.append(self._snapshot_adapter.validate_python(json.loads(line)))
        return out

    def load_latest_state(self, run_id: str) -> AgentState:
        d = self.run_dir(run_id)
        path = d / "latest_state.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        return self._state_adapter.validate_python(raw)

    def export_bundle(self, run_id: str) -> RunBundle:
        return RunBundle(
            manifest=self.load_manifest(run_id),
            tool_calls=self.load_tool_calls(run_id),
            state_snapshots=self.load_state_snapshots(run_id),
        )
