from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from agentic.core.state import AgentState, Plan
from agentic.core.tools import ToolMetadata


class LLM(ABC):
    """Very small abstraction over whatever LLM backend you use."""

    @abstractmethod
    def make_plan(self, user_message: str, tools: List[ToolMetadata]) -> Plan:
        ...

    @abstractmethod
    def summarize_run(self, state: AgentState) -> str:
        ...
