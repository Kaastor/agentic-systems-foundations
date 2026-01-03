from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

from ..agent.orchestrator import Toolbox, VAROrchestrator
from ..config import RuntimeConfig
from ..io import SessionIO
from ..store.exercise_store import ExerciseStore
from ..store.trace_store import FileTraceStore
from ..tools.exercise_generation import CompileDraftTool, GenerateDraftTool, available_specs
from ..tools.composite_generation import CompositeGenerateDraftTool
from ..tools.math_generation import MathGenerateDraftTool, available_math_specs
from ..tools.grading import GradeSubmissionTool
from ..tools.hinting import MakeHintTool
from ..tools.observability import TraceLogTool
from ..tools.sandbox import SandboxRunner
from ..tools.verification import ExerciseVerifyTool
from ..types import ExerciseSpec, ExerciseView, GradeReport, HintArtifact

from .scenarios import Scenario, scenario_matrix
from .math_scenarios import math_scenario_matrix
from .math_scenarios import math_scenario_matrix


class SyntheticIO(SessionIO):
    """A deterministic non-interactive IO for evaluation.

    It returns a scripted sequence of submissions, and collects grades/hints for debugging.
    """

    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self._submission_idx = 0
        self.presented: ExerciseView | None = None
        self.grades: List[GradeReport] = []
        self.hints: List[HintArtifact] = []
        self.messages: List[str] = []

    def choose_spec(self, specs: Sequence[ExerciseSpec]) -> ExerciseSpec:
        return self.scenario.spec

    def present_exercise(self, view: ExerciseView) -> None:
        self.presented = view

    def get_submission(self, *, artifact_id: str, starter_code: str) -> str:
        if self._submission_idx >= len(self.scenario.submission_sequence):
            # If the scenario runs out of scripted submissions, keep returning starter (likely fails).
            return starter_code
        code = self.scenario.submission_sequence[self._submission_idx]
        self._submission_idx += 1
        return code

    def show_grade(self, grade: GradeReport) -> None:
        self.grades.append(grade)

    def show_hint(self, hint: HintArtifact) -> None:
        self.hints.append(hint)

    def show_message(self, message: str) -> None:
        self.messages.append(message)



def _solutions_by_fn() -> Dict[str, str]:
    """Get correct solutions deterministically via the generator tool."""
    gen = GenerateDraftTool()
    out: Dict[str, str] = {}
    for spec in available_specs(seed=0):
        draft = gen.run(spec=spec).result
        out[spec.signature.name] = draft.reference_solution
    return out


def run_eval_suite(*, include_math: bool = False) -> List[dict]:
    with tempfile.TemporaryDirectory(prefix="var_eval_") as tmpdir:
        root = Path(tmpdir)
        store = ExerciseStore(root)
        trace_store = FileTraceStore(root)

        sandbox = SandboxRunner()

        # In "multi-domain" mode we route generation between different generators.
        generator = (
            CompositeGenerateDraftTool([MathGenerateDraftTool(), GenerateDraftTool()])
            if include_math
            else GenerateDraftTool()
        )

        tools = Toolbox(
            generate_draft=generator,
            compile_draft=CompileDraftTool(),
            verify=ExerciseVerifyTool(sandbox),
            grade=GradeSubmissionTool(store, sandbox),
            hint=MakeHintTool(store),
            trace_log=TraceLogTool(trace_store),
        )

        orchestrator = VAROrchestrator(config=RuntimeConfig(), store=store, tools=tools)

        coding_specs = available_specs(seed=0)
        math_specs = available_math_specs(seed=0) if include_math else []
        specs = [*coding_specs, *math_specs]

        solutions = _solutions_by_fn()
        scenarios = scenario_matrix(coding_specs, solutions)
        if include_math:
            scenarios.extend(math_scenario_matrix(math_specs))

        results: List[dict] = []
        for sc in scenarios:
            io = SyntheticIO(sc)
            final_state = orchestrator.run_session(io=io, specs=specs)

            results.append(
                {
                    "scenario": sc.name,
                    "final_state": final_state.current_state.value,
                    "regen_count": final_state.loop_counters.regen_count,
                    "attempts": len(final_state.attempts),
                    "tool_calls": final_state.metrics.tool_calls,
                    "passed": final_state.current_state.value == "TerminalSuccess",
                    "errors": [getattr(e, "message", getattr(e, "safe_message", str(e))) for e in final_state.errors],
                }
            )
        return results


def main() -> None:
    results = run_eval_suite()
    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    print(f"Eval suite: {passed}/{total} scenarios passed")

    # Print a compact failure report (should be empty in CI).
    failures = [r for r in results if not r["passed"]]
    if failures:
        print("\\nFailures:")
        for f in failures[:10]:
            print(f"- {f['scenario']}: final_state={f['final_state']} errors={f['errors']}")

    # Print a small metrics slice (useful for lab discussions).
    avg_tool_calls = sum(r["tool_calls"] for r in results) / max(1, total)
    avg_attempts = sum(r["attempts"] for r in results) / max(1, total)
    print(f"Avg tool calls/run: {avg_tool_calls:.1f}")
    print(f"Avg attempts/run: {avg_attempts:.1f}")


if __name__ == "__main__":
    main()
