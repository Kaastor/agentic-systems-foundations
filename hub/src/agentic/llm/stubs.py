from __future__ import annotations

from typing import List

from agentic.core.state import AgentState, Plan, PlanStep
from agentic.core.tools import ToolMetadata
from .base import LLM


class RuleBasedLLM(LLM):
    """A tiny, fully deterministic stand-in for a real LLM.

    It behaves like a planner/summariser, but all logic is hand-written.
    This is useful for offline use and for making tests stable.
    """

    def make_plan(self, user_message: str, tools: List[ToolMetadata]) -> Plan:
        lower = user_message.lower()
        steps: List[PlanStep] = []

        steps.append(
            PlanStep(
                id="load_inbox",
                description="List important emails in the inbox.",
                tool_name="list_inbox",
            )
        )
        steps.append(
            PlanStep(
                id="consult_policies",
                description="Consult policy documents relevant to email and scheduling.",
                tool_name="search_docs",
            )
        )

        if "schedule" in lower or "meeting" in lower:
            steps.append(
                PlanStep(
                    id="find_slots",
                    description="Find reasonable free time slots for a 30 minute meeting.",
                    tool_name="find_free_slots",
                )
            )
            steps.append(
                PlanStep(
                    id="create_event",
                    description="Create a calendar event for the proposed meeting slot.",
                    tool_name="create_event",
                )
            )

        if "remind" in lower or "reminder" in lower:
            steps.append(
                PlanStep(
                    id="set_reminder",
                    description="Set a reminder to follow up in a few days.",
                    tool_name="set_reminder",
                )
            )

        steps.append(
            PlanStep(
                id="send_reply",
                description=(
                    "Send a reply email that triages the inbox and, where appropriate, "
                    "proposes a meeting time."
                ),
                tool_name="send_email",
            )
        )

        return Plan(steps=steps, current_index=0)

    def summarize_run(self, state: AgentState) -> str:
        pieces: List[str] = []
        pieces.append(f"User request: {state.user_message!r}.")
        if state.plan:
            done = sum(1 for s in state.plan.steps if s.status.value in {"done", "skipped"})
            total = len(state.plan.steps)
            pieces.append(f"Executed {done}/{total} planned steps.")
        if state.tool_calls:
            tool_names = {c.tool_name for c in state.tool_calls}
            pieces.append("Tools used: " + ", ".join(sorted(tool_names)) + ".")
        pieces.append(f"Final status: {state.status.value}.")
        return " ".join(pieces)
