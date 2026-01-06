from __future__ import annotations

from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class BudgetCategory(str, Enum):
    """Named budget buckets.

    Keep these coarse. Fine-grained accounting can be built in product layers.
    """

    tool_calls = "tool_calls"
    tool_latency_ms = "tool_latency_ms"

    model_total_tokens = "model_total_tokens"
    model_input_tokens = "model_input_tokens"
    model_output_tokens = "model_output_tokens"

    sandbox_calls = "sandbox_calls"
    sandbox_runtime_ms = "sandbox_runtime_ms"

    retrieval_chars = "retrieval_chars"  # for RAG / context assembly, later


class BudgetLimits(BaseModel):
    """Optional limits per category.

    A missing limit means "unlimited".
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    limits: Dict[BudgetCategory, int] = Field(default_factory=dict)

    def limit_for(self, category: BudgetCategory) -> Optional[int]:
        return self.limits.get(category)


class BudgetSnapshot(BaseModel):
    """A serializable snapshot used for traces/state snapshots."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    limits: Dict[BudgetCategory, int] = Field(default_factory=dict)
    used: Dict[BudgetCategory, int] = Field(default_factory=dict)
