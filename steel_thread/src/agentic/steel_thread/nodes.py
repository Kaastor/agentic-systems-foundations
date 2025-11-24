from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Dict, Any

from agentic.core.graph import Node, RunContext
from agentic.core.state import (
    AgentState,
    AgentStatus,
    PlanStepStatus,
    ToolCallRecord,
)
from agentic.steel_thread.models import Email
from agentic.steel_thread.policy import PolicyDecisionType
from agentic.steel_thread.tools_email import ListInboxOutput
from agentic.steel_thread.tools_rag import SearchDocsOutput


@dataclass
class PlanningNode(Node):
    """Ask the LLM for a high-level plan."""

    def __init__(self) -> None:
        super().__init__(name="plan")

    def run(self, state: AgentState, ctx: RunContext) -> Tuple[AgentState, str]:
        plan = ctx.llm.make_plan(state.user_message, ctx.tools.list_metadata())
        state.plan = plan
        state.current_node = "next_step"
        return state, f"Created high-level plan with {len(plan.steps)} steps."

@dataclass
class NextStepNode(Node):
    """Move through the plan and decide what to do next."""

    def __init__(self) -> None:
        super().__init__(name="next_step")

    def run(self, state: AgentState, ctx: RunContext) -> Tuple[AgentState, str]:
        if not state.plan:
            state.status = AgentStatus.FAILED
            state.current_node = "terminal"
            return state, "No plan available; cannot continue."

        step = state.plan.current_step()
        if step is None or state.plan.is_done():
            state.current_node = "summarize"
            return state, "Plan is complete; moving to summarisation."

        if step.status == PlanStepStatus.PENDING:
            step.status = PlanStepStatus.RUNNING

        if step.tool_name is None:
            step.status = PlanStepStatus.SKIPPED
            state.plan.advance()
            state.current_node = "next_step"
            return state, f"Skipped non-tool step {step.id!r}."

        state.scratchpad["current_tool_name"] = step.tool_name
        state.current_node = "run_tool"
        return state, f"Next step is {step.id!r} using tool {step.tool_name!r}."


@dataclass
class ToolNode(Node):
    """Execute the selected tool, subject to policy checks and approvals."""

    def __init__(self) -> None:
        super().__init__(name="run_tool")

    def _build_args(self, state: AgentState, tool_name: str) -> Dict[str, Any] | None:
        # If there's a pending tool call for the current step, reuse it.
        pending = state.scratchpad.get("pending_tool_call")
        plan = state.plan
        step = plan.current_step() if plan else None
        if pending and step and pending.get("step_id") == step.id:
            return pending.get("args")

        # Fresh argument construction based on tool name.
        if tool_name == "list_inbox":
            return {"only_unread": True}

        if tool_name == "search_docs":
            return {"query": "email calendar scheduling policies", "k": 3}

        if tool_name == "find_free_slots":
            return {"duration_minutes": 30, "days_ahead": 7, "num_options": 1}

        if tool_name == "send_email":
            # Prefer an explicitly selected primary email.
            raw_primary = state.scratchpad.get("primary_email")
            primary: Email | None
            if isinstance(raw_primary, dict):
                primary = Email(**raw_primary)
            else:
                primary = raw_primary

            if primary is None:
                last_inbox = state.scratchpad.get("last_inbox") or []
                primary = Email(**last_inbox[0]) if last_inbox else None

            if primary is None:
                return None

            slot = state.scratchpad.get("proposed_slot")
            if slot:
                when = slot["start"]
                body = (
                    f"Hi {primary.from_address.split('@')[0].title()},\n\n"
                    f"30 minutes on {when} works well for me. I've sent a calendar invite.\n\n"
                    "Best,\nThe Agent"
                )
            else:
                body = (
                    f"Hi {primary.from_address.split('@')[0].title()},\n\n"
                    "Thanks for your email — I'll get back to you shortly.\n\n"
                    "Best,\nThe Agent"
                )

            subject = f"Re: {primary.subject}"

            return {
                "to_address": primary.from_address,
                "subject": subject,
                "body": body,
                "in_reply_to_id": primary.id,
            }

        if tool_name == "create_event":
            raw_primary = state.scratchpad.get("primary_email")
            primary: Email | None
            if isinstance(raw_primary, dict):
                primary = Email(**raw_primary)
            else:
                primary = raw_primary

            slot = state.scratchpad.get("proposed_slot")
            if primary is None or slot is None:
                return None

            title = f"Meeting about: {primary.subject}"
            participants = ["you@example.com", primary.from_address]
            return {
                "title": title,
                "participants": participants,
                "start": slot["start"],
                "end": slot["end"],
                "location": "Zoom",
            }

        return None

    def run(self, state: AgentState, ctx: RunContext) -> Tuple[AgentState, str]:
        plan = state.plan
        if not plan:
            state.status = AgentStatus.FAILED
            state.current_node = "terminal"
            return state, "Cannot run tools: no plan is attached to the state."

        step = plan.current_step()
        if not step or not step.tool_name:
            state.current_node = "next_step"
            return state, "No current tool step; returning to planner."

        tool_name = state.scratchpad.get("current_tool_name") or step.tool_name
        tool = ctx.tools.get(tool_name)

        raw_args = self._build_args(state, tool_name)
        if raw_args is None:
            step.status = PlanStepStatus.SKIPPED
            plan.advance()
            state.current_node = "next_step"
            return state, f"No arguments available for tool {tool_name!r}; skipping."

        decision = ctx.policy.check_tool_call(tool, raw_args, state)

        # Hard deny.
        if decision.decision == PolicyDecisionType.DENY:
            step.status = PlanStepStatus.FAILED
            plan.advance()
            state.current_node = "next_step"
            return state, f"Policy denied tool {tool_name!r}: {decision.reason}"

        # Human approval flow.
        pending = state.scratchpad.get("pending_tool_call")
        if decision.decision == PolicyDecisionType.REQUIRE_HUMAN and ctx.human_decision is None:
            # Park the tool call and wait for explicit approval.
            state.status = AgentStatus.AWAITING_USER
            state.scratchpad["pending_tool_call"] = {
                "tool_name": tool_name,
                "args": raw_args,
                "step_id": step.id,
                "reason": decision.reason,
            }
            state.current_node = "run_tool"
            return state, f"Waiting for human approval before calling {tool_name!r}."

        if decision.decision == PolicyDecisionType.REQUIRE_HUMAN and ctx.human_decision is not None:
            if not ctx.human_decision.approve:
                step.status = PlanStepStatus.SKIPPED
                plan.advance()
                state.current_node = "next_step"
                state.scratchpad.pop("pending_tool_call", None)
                state.scratchpad.pop("human_approved", None)
                state.status = AgentStatus.RUNNING
                return state, f"Human rejected tool {tool_name!r}; skipping."
            # Approved: mark flag so the policy engine is happy and continue.
            state.scratchpad["human_approved"] = True

        call_record = ToolCallRecord(tool_name=tool_name, args=raw_args)
        try:
            result = tool(raw_args)
            call_record.result = result.model_dump()
            call_record.success = True
            note = f"Called tool {tool_name!r} successfully."
        except Exception as exc:  # pragma: no cover - demo logging
            call_record.error = repr(exc)
            call_record.success = False
            step.status = PlanStepStatus.FAILED
            plan.advance()
            state.tool_calls.append(call_record)
            state.current_node = "next_step"
            state.status = AgentStatus.RUNNING
            return state, f"Tool {tool_name!r} failed with error: {exc!r}"

        state.tool_calls.append(call_record)

        # Feed tool outputs into scratchpad.
        if tool_name == "list_inbox":
            out = ListInboxOutput(**call_record.result)
            state.scratchpad["last_inbox"] = [e.model_dump() for e in out.emails]
            primary = next(
                (e for e in out.emails if "action_required" in e.tags),
                out.emails[0] if out.emails else None,
            )
            if primary:
                state.scratchpad["primary_email"] = primary.model_dump()

        elif tool_name == "search_docs":
            out = SearchDocsOutput(**call_record.result)
            state.scratchpad["policy_snippets"] = [h.snippet for h in out.hits]

        elif tool_name == "find_free_slots":
            slots = call_record.result.get("slots") or []
            if slots:
                state.scratchpad["proposed_slot"] = slots[0]

        # Mark step completion and move on.
        step.status = PlanStepStatus.DONE
        plan.advance()
        state.current_node = "next_step"
        state.status = AgentStatus.RUNNING

        state.scratchpad.pop("pending_tool_call", None)
        state.scratchpad.pop("human_approved", None)

        return state, note


@dataclass
class SummariseNode(Node):
    """Produce a short natural-language summary of the run."""

    def __init__(self) -> None:
        super().__init__(name="summarize")

    def run(self, state: AgentState, ctx: RunContext) -> Tuple[AgentState, str]:
        summary = ctx.llm.summarize_run(state)
        state.result_summary = summary
        state.status = AgentStatus.SUCCESS
        state.current_node = "terminal"
        return state, "Summarised run and marked as SUCCESS."


@dataclass
class TerminalNode(Node):
    """Do nothing; the run is over."""

    def __init__(self) -> None:
        super().__init__(name="terminal")

    def run(self, state: AgentState, ctx: RunContext) -> Tuple[AgentState, str]:
        return state, "Reached terminal node."
