from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .ids import new_run_id


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    role: MessageRole
    content: str


class ToolCallRecord(BaseModel):
    """A single call to a tool and what happened."""

    tool_name: str
    args: Dict[str, Any]
    result: Any | None = None
    error: str | None = None
    success: bool = True
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None


class PlanStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStep(BaseModel):
    id: str
    description: str
    tool_name: str | None = None
    status: PlanStepStatus = PlanStepStatus.PENDING
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    """Very small structured plan: linear list + index."""

    steps: List[PlanStep] = Field(default_factory=list)
    current_index: int = 0

    def current_step(self) -> PlanStep | None:
        if 0 <= self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    def advance(self) -> None:
        self.current_index += 1

    def is_done(self) -> bool:
        return self.current_index >= len(self.steps)


class Memory(BaseModel):
    """Tiny memory sketch: summary + key facts + TODO list."""

    summary: str = ""
    key_facts: Dict[str, str] = Field(default_factory=dict)
    todos: List[str] = Field(default_factory=list)


class AgentStatus(str, Enum):
    RUNNING = "running"
    AWAITING_USER = "awaiting_user"
    SUCCESS = "success"
    FAILED = "failed"


class TraceStep(BaseModel):
    step_index: int
    node: str
    note: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentState(BaseModel):
    """Serializable snapshot of an agent run.

    This is the thing we persist to disk so we can pause/resume, debug, and
    introspect. State machines, not call stacks.
    """

    id: str = Field(default_factory=new_run_id)
    user_message: str

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    status: AgentStatus = AgentStatus.RUNNING
    current_node: str = "plan"
    step_index: int = 0

    conversation: List[Message] = Field(default_factory=list)
    plan: Optional[Plan] = None
    memory: Memory = Field(default_factory=Memory)
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    trace: List[TraceStep] = Field(default_factory=list)
    scratchpad: Dict[str, Any] = Field(default_factory=dict)

    result_summary: str | None = None

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
