from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from agentic.core.state import AgentState
from agentic.core.tools import Tool


class PolicyDecisionType(str, Enum):
    ALLOW = "allow"
    REQUIRE_HUMAN = "require_human"
    DENY = "deny"


@dataclass
class PolicyDecision:
    decision: PolicyDecisionType
    reason: str


class PolicyEngine:
    """Very small policy engine for tool calls.

    For the main course, we only implement one idea: some tools are marked
    as ``dangerous`` and should not be executed without explicit human
    approval.
    """

    def check_tool_call(self, tool: Tool, args: dict, state: AgentState) -> PolicyDecision:
        if tool.metadata.dangerous and not state.scratchpad.get("human_approved", False):
            return PolicyDecision(
                decision=PolicyDecisionType.REQUIRE_HUMAN,
                reason=f"Tool {tool.metadata.name!r} is dangerous and needs human approval.",
            )

        return PolicyDecision(
            decision=PolicyDecisionType.ALLOW,
            reason="No policy issues detected.",
        )
