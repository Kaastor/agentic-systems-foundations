from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from agentic.config import settings
from agentic.core.graph import GraphRunner, RunContext
from agentic.core.logging import Tracer
from agentic.core.state import (
    AgentState,
    AgentStatus,
    Memory,
    Message,
    MessageRole,
)
from agentic.core.tools import ToolRegistry
from agentic.llm.groq_backend import GroqLLM
from agentic.llm.stubs import RuleBasedLLM
from agentic.main.nodes import (
    HumanReviewNode,
    NextStepNode,
    PlanningNode,
    SelfCheckNode,
    SummariseNode,
    TerminalNode,
    ToolNode,
)
from agentic.main.policy import PolicyEngine
from agentic.main.tools_calendar import build_calendar_tools
from agentic.main.tools_email import build_email_tools
from agentic.main.tools_rag import build_rag_tool

_LONG_TERM_MEMORY_PATH = settings.runs_dir / "long_term_memory.json"


@dataclass
class HumanDecision:
    approve: bool
    note: str = ""
    edited: bool = False


def _build_llm():
    """Return the configured LLM backend.

    - If settings.llm_backend == "groq", we call Groq's chat completions API.
    - Otherwise we fall back to the deterministic RuleBasedLLM.
    """
    if settings.llm_backend == "groq":
        if not settings.groq_api_key:
            raise RuntimeError(
                "AGENTIC_LLM_BACKEND is 'groq' but GROQ_API_KEY is not set."
            )
        # Very small mode toggle for Module 9: different models per mode.
        model = settings.groq_model
        if settings.mode == "fast":
            model = os.getenv("GROQ_FAST_MODEL", model)
        elif settings.mode == "smart":
            model = os.getenv("GROQ_SMART_MODEL", model)
        return GroqLLM(
            api_key=settings.groq_api_key,
            model=model,
            base_url=settings.groq_base_url,
        )
    return RuleBasedLLM()


def _build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    mailbox_path = settings.data_dir / "inbox.json"
    calendar_path = settings.data_dir / "calendar.json"
    docs_dir = settings.data_dir / "docs"

    enabled_env = os.getenv("AGENTIC_ENABLED_TOOLS")
    disabled_env = os.getenv("AGENTIC_DISABLED_TOOLS")
    enabled: set[str] | None = (
        {t.strip() for t in enabled_env.split(",") if t.strip()}
        if enabled_env
        else None
    )
    disabled: set[str] = (
        {t.strip() for t in disabled_env.split(",") if t.strip()}
        if disabled_env
        else set()
    )

    def _maybe_register(tool) -> None:
        name = tool.metadata.name
        if enabled is not None and name not in enabled:
            return
        if name in disabled:
            return
        registry.register(tool)

    for tool in build_email_tools(mailbox_path):
        _maybe_register(tool)
    for tool in build_calendar_tools(calendar_path):
        _maybe_register(tool)
    _maybe_register(build_rag_tool(docs_dir))
    return registry


def _build_nodes() -> dict[str, object]:
    return {
        "plan": PlanningNode(),
        "next_step": NextStepNode(),
        "run_tool": ToolNode(),
        "human_review": HumanReviewNode(),
        "self_check": SelfCheckNode(),
        "summarize": SummariseNode(),
        "terminal": TerminalNode(),
    }


def _state_path(run_id: str) -> Path:
    return settings.runs_dir / f"{run_id}.json"


def save_state(state: AgentState) -> None:
    path = _state_path(state.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def load_state(run_id: str) -> AgentState:
    path = _state_path(run_id)
    if not path.exists():
        raise FileNotFoundError(f"No saved state for run {run_id!r} at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return AgentState(**data)


def _load_long_term_memory(user_id: str) -> Memory:
    if not _LONG_TERM_MEMORY_PATH.exists():
        return Memory()
    data = json.loads(_LONG_TERM_MEMORY_PATH.read_text(encoding="utf-8"))
    payload = data.get(user_id)
    if not payload:
        return Memory()
    return Memory(**payload)


def _save_long_term_memory(user_id: str, memory: Memory) -> None:
    existing: dict[str, dict] = {}
    if _LONG_TERM_MEMORY_PATH.exists():
        existing = json.loads(_LONG_TERM_MEMORY_PATH.read_text(encoding="utf-8"))
    existing[user_id] = memory.model_dump()
    _LONG_TERM_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LONG_TERM_MEMORY_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def _update_memory_from_state(user_id: str, state: AgentState) -> None:
    """Very small layered memory update (Module 5)."""
    mem = _load_long_term_memory(user_id)
    if state.result_summary:
        mem.summary = state.result_summary
    primary = state.scratchpad.get("primary_email")
    if isinstance(primary, dict):
        mem.key_facts["last_primary_from"] = primary.get("from_address", "")
        mem.key_facts["last_primary_subject"] = primary.get("subject", "")
    if state.status != AgentStatus.SUCCESS:
        mem.todos.append(f"Investigate failed run {state.id}")
    _save_long_term_memory(user_id, mem)


def _is_simple_request(message: str) -> bool:
    """Heuristic router for 'don't be fancy' (Module 4)."""
    text = message.lower()
    return any(
        phrase in text
        for phrase in [
            "just summarize",
            "summary only",
            "quick summary",
        ]
    )


def _simple_summary_state(user_message: str, tools: ToolRegistry) -> AgentState:
    """Direct-answer path that avoids the full agent graph (Module 4)."""
    state = AgentState(user_message=user_message)
    try:
        inbox_tool = tools.get("list_inbox")
        out = inbox_tool({"only_unread": True})
        inbox_count = len(out.emails)
        state.result_summary = (
            f"Quick summary path: there are {inbox_count} unread emails in your inbox. "
            "Run the full agent if you want scheduling or detailed triage."
        )
    except Exception:
        state.result_summary = (
            "Quick summary path: unable to inspect the inbox, "
            "but this is the single-shot route without planning."
        )
    state.status = AgentStatus.SUCCESS
    return state


def run_steel_thread(
    user_message: str,
    run_id: Optional[str] = None,
    human_decision: Optional[HumanDecision] = None,
) -> AgentState:
    """Run (or resume) the steel-thread agent."""

    tools = _build_tool_registry()
    nodes = _build_nodes()
    llm = _build_llm()
    policy = PolicyEngine()

    user_id = "demo_user"

    if run_id is None:
        # New run: maybe take the "simple route" instead of a full agent.
        if _is_simple_request(user_message):
            state = _simple_summary_state(user_message, tools)
            state.metadata["user_id"] = user_id
            save_state(state)
            _update_memory_from_state(user_id, state)
            return state

        long_term_memory = _load_long_term_memory(user_id)
        state = AgentState(user_message=user_message, memory=long_term_memory)
        state.metadata["user_id"] = user_id
        state.conversation.append(
            Message(role=MessageRole.USER, content=user_message)
        )
        if long_term_memory.summary:
            # Very simple recall policy: prepend a summary hint.
            state.user_message = (
                f"{user_message}\n\n"
                f"[Long-term summary for this user: {long_term_memory.summary}]"
            )
    else:
        state = load_state(run_id)
        user_id = state.metadata.get("user_id", "demo_user")
        user_message = state.user_message

    tracer = Tracer(run_id=state.id, runs_dir=settings.runs_dir)

    # If this run is waiting on a timer (wake_at in the future) and there is
    # no explicit human decision, treat this call as a no-op.
    if run_id is not None and state.wake_at and state.wake_at > datetime.utcnow() and human_decision is None:
        save_state(state)
        return state

    if state.status == AgentStatus.AWAITING_USER and human_decision is not None:
        state.status = AgentStatus.RUNNING

    ctx = RunContext(
        tools=tools,
        tracer=tracer,
        llm=llm,
        settings=settings,
        policy=policy,
        human_decision=human_decision,
    )

    runner = GraphRunner(nodes=nodes, max_steps=settings.max_steps)
    final_state = runner.run(state, ctx)

    # Basic per-run metrics for Module 8.
    final_state.metrics.setdefault(
        "successful", 1.0 if final_state.status == AgentStatus.SUCCESS else 0.0
    )

    save_state(final_state)
    _update_memory_from_state(user_id, final_state)
    return final_state
