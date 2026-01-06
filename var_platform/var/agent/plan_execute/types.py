from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanStep(BaseModel):
    """A single step in a plan.

    In a model-driven planner, this can be produced by the ModelTool using a
    structured schema.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    tool: str
    description: str = ""
    args: Dict[str, Any] = Field(default_factory=dict)
    expects: Optional[str] = None


class Plan(BaseModel):
    """A plan is a serializable artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    planner: str
    version: str
    steps: List[PlanStep]