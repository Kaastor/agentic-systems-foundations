from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from agentic.core.graph import Node, RunContext
from agentic.core.state import (
    AgentState,
    AgentStatus,
    FailureType,
    PlanStepStatus,
    ToolCallRecord,
    ToolErrorType,
)
from agentic.steel_thread.models import Email
from agentic.steel_thread.policy import PolicyDecisionType
from agentic.steel_thread.tools_email import ListInboxOutput
from agentic.steel_thread.tools_rag import SearchDocsOutput


def _make_idempotency_key(tool_name: str, args: Dict[str, Any]) -> str:
    try:
        serialized = json.dumps(args, sort_keys=True, default=str)
    except TypeError:
        serialized = repr(sorted(args.items()))
    return f"{tool_name}:{serialized}"


def _classify_error(exc: Exception) -> ToolErrorType:
    """Very small heuristic error classifier (Module 2 / 8)."""
    try:
        from pydantic import ValidationError
    except Exception:  # pragma: no cover - import guard
        ValidationError = Exception  # type: ignore

    transient_types: tuple[type[BaseException], ...]
    try:
        import requests

        transient_types = (requests.RequestException,)
    except Exception:  # pragma: no cover - requests import guard
        transient_types = ()

    if isinstance(exc, ValidationError):
        return ToolErrorType.VALIDATION
    if transient_types and isinstance(exc, transient_types):
        return ToolErrorType.TRANSIENT
    return ToolErrorType.PERMANENT


@dataclass
class PlanningNode(Node):
    """Ask the LLM for a high-level plan."""

    def __init__(self) -> None:
        super().__init__(name="plan")

    def run(self, state: AgentState, ctx: RunContext) -> Tuple[AgentState, str]:
        # Feed previous errors back into the planner for simple plan repair.
        augmented_message = state.user_message
        last_error = state.scratchpad.get("last_error")
        if last_error:
            augmented_message += (
                "\n\n[Note: a previous attempt failed with this error; "
                "please adjust your plan to avoid repeating it: "
                f"{last_error}]"
            )

        plan = ctx.llm.make_plan(augmented_message, ctx.tools.list_metadata())
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
            state.failure_type = state.failure_type or FailureType.UNCLASSIFIED
            state.current_node = "terminal"
            return state, "No plan available; cannot continue."

        step = state.plan.current_step()
        if step is None or state.plan.is_done():
            state.current_node = "self_check"
            return state, "Plan is complete; moving to self-check."

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
class HumanReviewNode(Node):
    """Explicit node that waits for and consumes human approval (Module 6)."""

    def __init__(self) -> None:
        super().__init__(name="human_review")

    def run(self, state: AgentState, ctx: RunContext) -> Tuple[AgentState, str]:
        pending = state.scratchpad.get("pending_tool_call")
        if not pending:
            state.current_node = "next_step"
            state.status = AgentStatus.RUNNING
            return state, "No pending tool call; returning to next_step."

        if ctx.human_decision is None:
            state.status = AgentStatus.AWAITING_USER
            return state, "Still waiting for human decision."

        plan = state.plan
        step = plan.current_step() if plan else None
        tool_name = pending.get("tool_name", "<unknown>")

        if not ctx.human_decision.approve:
            if step:
                step.status = PlanStepStatus.SKIPPED
                plan.advance()
            state.scratchpad.pop("pending_tool_call", None)
            state.scratchpad.pop("human_approved", None)
            state.status = AgentStatus.RUNNING
            state.current_node = "next_step"
            return state, f"Human rejected tool {tool_name!r}; skipping."

        # Approved – optionally with edits.
        state.scratchpad["human_approved"] = True
        if ctx.human_decision.note:
            state.scratchpad["human_edit_note"] = ctx.human_decision.note
        state.status = AgentStatus.RUNNING
        state.current_node = "run_tool"
        return state, f"Human approved tool {tool_name!r}; proceeding."


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

        if tool_name == "set_reminder":
            return {
                "remind_in_days": 3,
                "note": "Remind me to follow up on this project in a few days.",
            }

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
            edit_note = state.scratchpad.get("human_edit_note") or ""

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

            if edit_note:
                body += f"\n\n(Edits from human reviewer: {edit_note})"

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
            state.failure_type = state.failure_type or FailureType.UNCLASSIFIED
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

        # Idempotency key for this call.
        idempotency_key = _make_idempotency_key(tool_name, raw_args)

        # Simple loop detection: if we've already failed this key twice, bail.
        error_history: Dict[str, int] = state.scratchpad.setdefault(
            "tool_error_history", {}
        )
        failure_count = int(error_history.get(idempotency_key, 0))
        if failure_count >= 2:
            step.status = PlanStepStatus.FAILED
            state.failure_type = state.failure_type or FailureType.NON_HALTING
            state.scratchpad["tool_loop_detected"] = True
            plan.advance()
            state.current_node = "self_check"
            state.status = AgentStatus.RUNNING
            return state, f"Detected failing loop for {tool_name!r}; handing off to self-check."

        decision = ctx.policy.check_tool_call(tool, raw_args, state)

        # Hard deny / refuse.
        if decision.decision == PolicyDecisionType.DENY:
            step.status = PlanStepStatus.FAILED
            plan.advance()
            state.failure_type = state.failure_type or FailureType.SAFETY_VIOLATION
            state.current_node = "summarize"
            return state, f"Policy denied tool {tool_name!r}: {decision.reason}"

        # Human approval flow.
        if decision.decision == PolicyDecisionType.REQUIRE_HUMAN:
            # Park the tool call and go to the explicit HumanReviewNode.
            state.status = AgentStatus.AWAITING_USER
            state.metrics["human_approvals_requested"] = state.metrics.get(
                "human_approvals_requested", 0
            ) + 1
            state.scratchpad["pending_tool_call"] = {
                "tool_name": tool_name,
                "args": raw_args,
                "step_id": step.id,
                "reason": decision.reason,
            }
            state.current_node = "human_review"
            return state, f"Waiting for human approval before calling {tool_name!r}."

        # At this point the policy engine allows the call.
        call_record = ToolCallRecord(
            tool_name=tool_name,
            args=raw_args,
            idempotency_key=idempotency_key,
        )

        # Re-use previous successful result if present (idempotent writes).
        previous = next(
            (
                c
                for c in state.tool_calls
                if c.idempotency_key == idempotency_key and c.success
            ),
            None,
        )
        if previous is not None:
            call_record.result = previous.result
            call_record.success = True
            note = f"Re-used cached result for tool {tool_name!r}."
        else:
            try:
                result = tool(raw_args)
                call_record.result = result.model_dump()
                call_record.success = True
                note = f"Called tool {tool_name!r} successfully."
            except Exception as exc:  # pragma: no cover - demo logging
                error_type = _classify_error(exc)
                call_record.error = repr(exc)
                call_record.error_type = error_type
                call_record.success = False
                error_history[idempotency_key] = failure_count + 1
                if error_type == ToolErrorType.VALIDATION:
                    state.failure_type = state.failure_type or FailureType.WRONG_ARGS
                else:
                    state.failure_type = state.failure_type or FailureType.UNCLASSIFIED
                state.scratchpad["last_error"] = str(exc)
                step.status = PlanStepStatus.FAILED
                plan.advance()
                state.tool_calls.append(call_record)
                state.current_node = "next_step"
                state.status = AgentStatus.RUNNING
                return state, f"Tool {tool_name!r} failed with error: {exc!r}"

        state.tool_calls.append(call_record)
        state.metrics["tool_calls"] = float(len(state.tool_calls))

        # Feed tool outputs into scratchpad.
        if tool_name == "list_inbox":
            out = ListInboxOutput(**call_record.result)
            state.scratchpad["last_inbox"] = [e.model_dump() for e in out.emails]
            primary = next(
                (
                    e
                    for e in out.emails
                    if "action_required" in [t.value for t in e.tags]
                ),
                out.emails[0] if out.emails else None,
            )
            if primary:
                state.scratchpad["primary_email"] = primary.model_dump()

        elif tool_name == "search_docs":
            out = SearchDocsOutput(**call_record.result)
            state.scratchpad["policy_snippets"] = [h.snippet for h in out.hits]
            # Keep structured DocumentHit objects around, not just pasted blobs.
            state.scratchpad["policy_hits"] = [h.model_dump() for h in out.hits]

        elif tool_name == "find_free_slots":
            slots = call_record.result.get("slots") or []
            if slots:
                state.scratchpad["proposed_slot"] = slots[0]

        elif tool_name == "set_reminder":
            wake_at = call_record.result.get("wake_at")
            state.wake_at = wake_at

        # Mark step completion and move on.
        step.status = PlanStepStatus.DONE
        plan.advance()
        state.current_node = "next_step"
        state.status = AgentStatus.RUNNING

        state.scratchpad.pop("pending_tool_call", None)
        state.scratchpad.pop("human_approved", None)
        state.scratchpad.pop("human_edit_note", None)

        return state, note


@dataclass
class SelfCheckNode(Node):
    """Simple self-check over the run before returning to the user (Module 6)."""

    def __init__(self) -> None:
        super().__init__(name="self_check")

    def run(self, state: AgentState, ctx: RunContext) -> Tuple[AgentState, str]:
        plan = state.plan
        classification = "confident"
        reasons = []

        if not plan:
            classification = "need_more_info"
            reasons.append("no_plan")

        if plan and any(s.status == PlanStepStatus.FAILED for s in plan.steps):
            classification = "need_more_info"
            reasons.append("plan_has_failed_steps")

        if state.failure_type in (
            FailureType.SAFETY_VIOLATION,
            FailureType.NON_HALTING,
        ):
            classification = "refuse"
            reasons.append(f"failure_type={state.failure_type.value}")

        tools_used = sorted({c.tool_name for c in state.tool_calls})
        state.scratchpad["self_check"] = {
            "classification": classification,
            "reasons": reasons,
            "tools_used": tools_used,
        }

        if classification == "refuse":
            state.status = AgentStatus.FAILED
            state.current_node = "terminal"
            return state, "Self-check refused to return a result."
        else:
            state.current_node = "summarize"
            return state, f"Self-check classification: {classification}."


@dataclass
class SummariseNode(Node):
    """Produce a short natural-language summary of the run."""

    def __init__(self) -> None:
        super().__init__(name="summarize")

    def run(self, state: AgentState, ctx: RunContext) -> Tuple[AgentState, str]:
        summary = ctx.llm.summarize_run(state)

        self_check = state.scratchpad.get("self_check") or {}
        classification = self_check.get("classification")
        reasons = self_check.get("reasons") or []
        if classification:
            summary += (
                f"\n\n(Internal self-check: {classification}"
                + (f" — reasons: {', '.join(reasons)}" if reasons else "")
                + ")"
            )

        hits = state.scratchpad.get("policy_hits") or []
        if hits:
            titles = sorted({h.get("title", "") for h in hits if isinstance(h, dict)})
            if titles:
                summary += (
                    "\n\nI consulted these policy documents: "
                    + ", ".join(titles)
                    + "."
                )

        state.result_summary = summary
        if state.status != AgentStatus.FAILED:
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
