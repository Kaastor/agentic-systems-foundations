from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agentic.config import settings
from agentic.core.graph import GraphRunner, RunContext
from agentic.core.logging import Tracer
from agentic.core.state import AgentState, AgentStatus
from agentic.core.tools import ToolRegistry
from agentic.llm.stubs import RuleBasedLLM
from agentic.llm.groq_backend import GroqLLM
from agentic.steel_thread.nodes import (
    NextStepNode,
    PlanningNode,
    SummariseNode,
    TerminalNode,
    ToolNode,
)
from agentic.steel_thread.policy import PolicyEngine
from agentic.steel_thread.tools_calendar import build_calendar_tools
from agentic.steel_thread.tools_email import build_email_tools
from agentic.steel_thread.tools_rag import build_rag_tool


@dataclass
class HumanDecision:
    approve: bool
    note: str = ""


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
        return GroqLLM(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            base_url=settings.groq_base_url,
        )
    return RuleBasedLLM()


def _build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    mailbox_path = settings.data_dir / "inbox.json"
    calendar_path = settings.data_dir / "calendar.json"
    docs_dir = settings.data_dir / "docs"

    for tool in build_email_tools(mailbox_path):
        registry.register(tool)
    for tool in build_calendar_tools(calendar_path):
        registry.register(tool)
    registry.register(build_rag_tool(docs_dir))
    return registry


def _build_nodes() -> dict[str, object]:
    return {
        "plan": PlanningNode(),
        "next_step": NextStepNode(),
        "run_tool": ToolNode(),
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

    if run_id is None:
        state = AgentState(user_message=user_message)
    else:
        state = load_state(run_id)
        user_message = state.user_message

    tracer = Tracer(run_id=state.id, runs_dir=settings.runs_dir)

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
    save_state(final_state)
    return final_state
