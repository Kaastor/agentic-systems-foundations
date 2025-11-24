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
    """Very small policy engine for tool calls (Module 6).

    For the main course, this demonstrates:

    - Looking at tool metadata (name, dangerous, permissions).
    - Looking at arguments (e.g. destination email).
    - Looking at simple user identity from AgentState.metadata.
    - Returning: allow / require human / deny.
    """

    def check_tool_call(self, tool: Tool, args: dict, state: AgentState) -> PolicyDecision:
        user_id = state.metadata.get("user_id", "demo_user")

        # Baseline risk from tool metadata.
        risk_score = 0
        if tool.metadata.dangerous:
            risk_score += 1

        # Very small example of argument-based risk: emailing non-example.com
        to_address = args.get("to_address")
        if isinstance(to_address, str) and not to_address.endswith("@example.com"):
            risk_score += 1

        # Treat "guest" as a slightly higher-risk identity.
        if user_id == "guest":
            risk_score += 1

        if risk_score >= 2 and not state.scratchpad.get("human_approved", False):
            return PolicyDecision(
                decision=PolicyDecisionType.DENY,
                reason=f"High-risk write for user {user_id!r}; refusing tool {tool.metadata.name!r}.",
            )

        if tool.metadata.dangerous and not state.scratchpad.get("human_approved", False):
            return PolicyDecision(
                decision=PolicyDecisionType.REQUIRE_HUMAN,
                reason=f"Tool {tool.metadata.name!r} is dangerous and needs human approval.",
            )

        return PolicyDecision(
            decision=PolicyDecisionType.ALLOW,
            reason="No policy issues detected.",
        )
