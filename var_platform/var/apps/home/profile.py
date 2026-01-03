from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field

from ...types import utc_now


class HomeschoolProfile(BaseModel):
    """Minimal learner profile.

    This is deliberately lightweight in v0.2. The long-run vision is a real mastery model,
    but we start with something students can reason about and extend.
    """

    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    created_at: datetime = Field(default_factory=utc_now)

    # Concept mastery in [0,1].
    concept_mastery: Dict[str, float] = Field(default_factory=dict)

    def update_mastery(self, *, concepts: List[str], passed: bool) -> None:
        """Update mastery for the given concepts in-place."""
        for c in concepts:
            cur = float(self.concept_mastery.get(c, 0.0))
            if passed:
                cur = min(1.0, cur + 0.10)
            else:
                cur = max(0.0, cur - 0.02)
            self.concept_mastery[c] = cur


class LocalProfileStore:
    """File-backed storage for homeschool profiles."""

    def __init__(self, root: Path):
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def path_for(self, profile_id: str) -> Path:
        return self._root / f"profile_{profile_id}.json"

    def save(self, profile: HomeschoolProfile) -> None:
        p = self.path_for(profile.profile_id)
        p.write_text(json.dumps(profile.model_dump(mode="json"), indent=2), encoding="utf-8")

    def load(self, profile_id: str) -> HomeschoolProfile:
        p = self.path_for(profile_id)
        data = json.loads(p.read_text(encoding="utf-8"))
        return HomeschoolProfile.model_validate(data)
