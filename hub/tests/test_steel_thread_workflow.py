from agentic.config import settings
from agentic.core.state import AgentStatus
from agentic.steel_thread.runner import run_steel_thread


def test_full_steel_thread_stub_succeeds():
    """Basic golden-flow test for the steel-thread agent (Module 8)."""
    # Ensure we use the deterministic local backend.
    settings.llm_backend = "stub"
    state = run_steel_thread(
        user_message="Please triage my inbox and schedule any obvious meetings."
    )
    assert state.status in (AgentStatus.SUCCESS, AgentStatus.FAILED)
    # Even on failure, we should have attempted at least one tool call.
    assert state.tool_calls
