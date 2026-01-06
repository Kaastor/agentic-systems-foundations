from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class PromptTemplate:
    prompt_id: str
    version: str
    template: str

    @property
    def template_hash(self) -> str:
        return hashlib.sha256(self.template.encode("utf-8")).hexdigest()


class PromptRegistry:
    """File-backed prompt registry.

    Prompts live under a directory and are named:
        <prompt_id>__<version>.txt

    Example:
        tutor_hint__v1.txt

    This avoids "random strings in code" and makes prompts versioned artifacts.
    """

    def __init__(self, root: Path):
        self._root = Path(root)
        self._cache: Dict[tuple[str, str], PromptTemplate] = {}

    def get(self, prompt_id: str, version: str) -> PromptTemplate:
        key = (prompt_id, version)
        if key in self._cache:
            return self._cache[key]

        path = self._root / f"{prompt_id}__{version}.txt"
        if not path.exists():
            raise KeyError(f"Prompt not found: {prompt_id}::{version} at {path}")
        tpl = PromptTemplate(prompt_id=prompt_id, version=version, template=path.read_text(encoding="utf-8"))
        self._cache[key] = tpl
        return tpl

    def maybe_get(self, prompt_id: str, version: str) -> Optional[PromptTemplate]:
        try:
            return self.get(prompt_id, version)
        except KeyError:
            return None
