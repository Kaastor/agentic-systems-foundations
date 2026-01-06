from __future__ import annotations

"""A tiny, deterministic suite that proves VAR fails cleanly.

The goal is not breadth. The goal is *sharp failure modes*:

1) Budget exhaustion (boundary failure) -> TerminalFailure with BudgetExceeded.
2) Sandbox timeout (domain failure) -> bounded attempts -> TerminalFailure.
3) Model schema mismatch (domain failure) -> OutcomeKind.Invalid with reason schema_mismatch.

These are the kinds of things that make agents "production-shaped":
they don't just succeed — they fail predictably.
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from ..agent.orchestrator import Toolbox, VAROrchestrator
from ..config import BudgetConfig, RuntimeConfig
from ..eval.harness import SyntheticIO
from ..eval.scenarios import Scenario
from ..model.prompt_registry import PromptRegistry
from ..model.schema_registry import ModelSchemaRegistry
from ..model.tool import ModelCompleteTool, ModelProviderClient
from ..model.types import ModelRequest, ModelResponse
from ..store.exercise_store import ExerciseStore
from ..store.trace_store import FileTraceStore
from ..tools.exercise_generation import CompileDraftTool, GenerateDraftTool, available_specs
from ..tools.grading import GradeSubmissionTool
from ..tools.hinting import MakeHintTool
from ..tools.observability import TraceLogTool
from ..tools.presentation_gate import GateExerciseViewTool, GateGradeReportTool, GateHintTool
from ..tools.sandbox import SandboxRunner
from ..tools.verification import ExerciseVerifyTool
from ..types import AgentNode, OutcomeKind, ToolErrorCode


_TIMEOUT_SUBMISSION = """def reverse_string(*args, **kwargs):\n    while True:\n        pass\n"""


class _TinySchema(BaseModel):
    ok: bool = Field(...)


class _BadJSONProvider(ModelProviderClient):
    def complete(self, *, rendered_prompt: str, request: ModelRequest) -> ModelResponse:  # noqa: ARG002
        # Intentionally NOT JSON.
        return ModelResponse(text="not-json", parsed=None, provider="mock", model="bad-json", usage={})


def _make_orchestrator(
    root: Path,
    *,
    config: RuntimeConfig,
) -> tuple[VAROrchestrator, ExerciseStore]:
    store = ExerciseStore(root)
    trace_store = FileTraceStore(root)
    sandbox = SandboxRunner()

    tools = Toolbox(
        generate_draft=GenerateDraftTool(),
        compile_draft=CompileDraftTool(),
        verify=ExerciseVerifyTool(sandbox),
        grade=GradeSubmissionTool(store, sandbox),
        hint=MakeHintTool(store),
        gate_exercise_view=GateExerciseViewTool(),
        gate_grade_report=GateGradeReportTool(),
        gate_hint=GateHintTool(),
        trace_log=TraceLogTool(trace_store),
    )
    orch = VAROrchestrator(config=config, store=store, tools=tools)
    return orch, store


def run_brutal_suite() -> List[Dict[str, Any]]:
    """Return a list of result dicts (friendly to CI + teaching labs)."""
    results: List[Dict[str, Any]] = []

    # ----------------------------
    # 1) Budget exhaustion (tool_calls)
    # ----------------------------
    with tempfile.TemporaryDirectory(prefix="var_brutal_budget_") as td:
        root = Path(td)

        spec = available_specs(seed=0)[0]
        # Budget small enough that verification cannot happen.
        cfg = RuntimeConfig(
            max_steps=20,
            max_regenerations_per_spec=1,
            budgets=BudgetConfig.from_simple(enabled=True, max_tool_calls=2),
        )
        orch, _store = _make_orchestrator(root, config=cfg)
        io = SyntheticIO(Scenario(name="budget_exhaustion", spec=spec, submission_sequence=[]))
        final = orch.run_session(io=io, specs=[spec])

        err_codes = [
            getattr(e, "code", None).value
            for e in final.errors
            if getattr(e, "code", None) is not None
        ]
        results.append(
            {
                "case": "budget_exhaustion_tool_calls",
                "terminal_state": final.current_state.value,
                "has_budget_error": ToolErrorCode.BudgetExceeded.value in err_codes,
                "errors": [getattr(e, "safe_message", getattr(e, "message", str(e))) for e in final.errors],
                "budget_used": getattr(final.metrics, "budget_used", {}),
                "budget_limits": getattr(final.metrics, "budget_limits", {}),
            }
        )

    # ----------------------------
    # 2) Sandbox timeouts -> bounded attempts
    # ----------------------------
    with tempfile.TemporaryDirectory(prefix="var_brutal_timeout_") as td:
        root = Path(td)
        base = next(s for s in available_specs(seed=0) if s.signature.name == "reverse_string")
        # Keep the spec constraints intact so the *reference* solution verifies.
        # We'll trigger timeouts via the learner submission itself.
        spec = base

        cfg = RuntimeConfig(max_steps=200, max_attempts=2)
        orch, _store = _make_orchestrator(root, config=cfg)

        io = SyntheticIO(
            Scenario(
                name="timeout_exhaust_attempts",
                spec=spec,
                submission_sequence=[_TIMEOUT_SUBMISSION] * cfg.max_attempts,
            )
        )
        final = orch.run_session(io=io, specs=[spec])
        timeout_seen = any(
            getattr(t, "error_type", "") == ToolErrorCode.Timeout.value
            for a in final.attempts
            if a.grade is not None
            for t in a.grade.test_results
        )
        results.append(
            {
                "case": "sandbox_timeout_exhaust_attempts",
                "terminal_state": final.current_state.value,
                "attempts": len(final.attempts),
                "timeout_seen": bool(timeout_seen),
                "ended_at_max_attempts": final.current_state == AgentNode.TerminalFailure
                and any(getattr(e, "message", "") == "max_attempts exceeded" for e in final.errors),
            }
        )

    # ----------------------------
    # 3) Model schema mismatch -> OutcomeKind.Invalid
    # ----------------------------
    with tempfile.TemporaryDirectory(prefix="var_brutal_model_") as td:
        root = Path(td)
        prompts_dir = root / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        # NOTE: Prompt templates are rendered via str.format; braces must be escaped.
        (prompts_dir / "demo__v1.txt").write_text(
            "Return a JSON object like this exactly: {{\"ok\": true}}",
            encoding="utf-8",
        )

        pr = PromptRegistry(prompts_dir)
        sr = ModelSchemaRegistry()
        sr.register_model("tiny", _TinySchema)

        tool = ModelCompleteTool(prompt_registry=pr, schema_registry=sr, provider_client=_BadJSONProvider())
        req = ModelRequest(
            prompt_id="demo",
            prompt_version="v1",
            variables={},
            output_schema_ref="tiny",
        )
        res = tool.run(request=req)
        ok = bool(res.ok and res.result.kind == OutcomeKind.Invalid and res.result.reason == "schema_mismatch")
        results.append(
            {
                "case": "model_schema_mismatch",
                "tool_ok": res.ok,
                "outcome_kind": (res.result.kind.value if res.ok else None),
                "outcome_reason": (res.result.reason if res.ok else None),
                "detected": ok,
            }
        )

    return results


def main() -> None:
    results = run_brutal_suite()
    passed = sum(1 for r in results if (
        (r["case"] == "budget_exhaustion_tool_calls" and r["terminal_state"] == AgentNode.TerminalFailure.value and r["has_budget_error"]) or
        (r["case"] == "sandbox_timeout_exhaust_attempts" and r["timeout_seen"] and r["ended_at_max_attempts"]) or
        (r["case"] == "model_schema_mismatch" and r["detected"])
    ))
    total = len(results)
    print(f"Brutal suite: {passed}/{total} checks passed")
    for r in results:
        print(f"- {r['case']}: {r}")


if __name__ == "__main__":
    main()
