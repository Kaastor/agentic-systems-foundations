from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class HintPolicy(BaseModel):
    """Controls what the tutor is allowed to reveal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    allow_solution_reveal: bool = False
    max_hint_level: int = Field(default=4, ge=1, le=10)


class HintArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    level: int
    hint_md: str
    reveals_solution: bool = False
    based_on: Dict[str, Any] = Field(default_factory=dict)
