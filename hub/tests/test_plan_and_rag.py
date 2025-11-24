from agentic.core.tools import ToolRegistry
from agentic.llm.stubs import RuleBasedLLM
from agentic.main.tools_rag import build_rag_tool
from agentic.config import settings


def test_stub_llm_makes_non_empty_plan():
    llm = RuleBasedLLM()
    registry = ToolRegistry()
    registry.register(build_rag_tool(settings.data_dir / "docs"))
    plan = llm.make_plan("please triage my inbox and schedule meetings", registry.list_metadata())
    assert plan.steps
    assert any(step.tool_name == "search_docs" for step in plan.steps)


def test_rag_returns_hits():
    tool = build_rag_tool(settings.data_dir / "docs")
    out = tool({"query": "email", "k": 5})
    assert out.hits
