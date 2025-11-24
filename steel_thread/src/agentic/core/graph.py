from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .logging import Tracer
from .state import AgentState, AgentStatus, TraceStep
from .tools import ToolRegistry


@dataclass
class RunContext:
    """Runtime wiring for a single agent run."""

    tools: ToolRegistry
    tracer: Tracer
    llm: Any  # We keep this untyped to avoid import tangles.
    settings: Any
    policy: Any
    human_decision: Any | None = None


class Node:
    """Base class for graph nodes."""

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, state: AgentState, ctx: RunContext) -> Tuple[AgentState, str]:
        raise NotImplementedError


class GraphRunner:
    """Executes nodes until the agent halts or hits a step limit."""

    def __init__(self, nodes: Dict[str, Node], max_steps: int) -> None:
        self.nodes = nodes
        self.max_steps = max_steps

    def run(self, state: AgentState, ctx: RunContext) -> AgentState:
        while (
            state.status == AgentStatus.RUNNING
            and state.step_index < self.max_steps
        ):
            node_name = state.current_node
            if node_name not in self.nodes:
                state.status = AgentStatus.FAILED
                state.result_summary = f"Unknown node: {node_name}"
                break

            node = self.nodes[node_name]
            state.touch()

            new_state, note = node.run(state, ctx)

            ctx.tracer.log(state.step_index, node.name, note)
            new_state.trace.append(
                TraceStep(step_index=state.step_index, node=node.name, note=note)
            )

            state = new_state
            state.step_index += 1

            if state.status in (
                AgentStatus.AWAITING_USER,
                AgentStatus.SUCCESS,
                AgentStatus.FAILED,
            ):
                break

        if (
            state.status == AgentStatus.RUNNING
            and state.step_index >= self.max_steps
        ):
            state.status = AgentStatus.FAILED
            state.result_summary = (
                state.result_summary
                or f"Aborted: exceeded max_steps={self.max_steps}"
            )
        return state
