from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Dict, Any

from ..agent.orchestrator import Toolbox, VAROrchestrator
from ..config import RuntimeConfig
from ..store.exercise_store import ExerciseStore
from ..store.trace_store import FileTraceStore
from ..tools.exercise_generation import CompileDraftTool, GenerateDraftTool, available_specs
from ..tools.grading import GradeSubmissionTool
from ..tools.hinting import MakeHintTool
from ..tools.math_generation import MathGenerateDraftTool, available_math_specs
from ..tools.observability import TraceLogTool
from ..tools.presentation_gate import GateExerciseViewTool, GateGradeReportTool, GateHintTool
from ..tools.sandbox import SandboxRunner
from ..tools.verification import ExerciseVerifyTool
from ..types import AgentNode
from .harness import SyntheticIO
from .scenarios import Scenario


def _make_orchestrator(root: Path) -> tuple[VAROrchestrator, ExerciseStore]:
    store = ExerciseStore(root)
    trace_store = FileTraceStore(root)
    sandbox = SandboxRunner()

    # Golden suite focuses on runtime correctness, not breadth of generation.
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
    orch = VAROrchestrator(config=RuntimeConfig(max_steps=120, verification_repeats=2), store=store, tools=tools)
    return orch, store


def golden_scenarios() -> List[Scenario]:
    """A small, sharp suite that intentionally exercises failure modes.

    This is meant to be 'brutal but deterministic':
    - wrong answer -> hint loop -> fix
    - forbidden import -> policy flag -> fix
    - timeout -> fix
    - missing function -> fix
    - flaky verification -> regen escape
    """
    # Base catalog
    base_specs = available_specs(seed=0)
    gen = GenerateDraftTool()
    solutions = {s.signature.name: gen.run(spec=s).result.reference_solution.get_secret_value() for s in base_specs}

    scenarios: List[Scenario] = []
    # Pick one representative spec for each pattern.
    for fn in ("reverse_string", "count_vowels", "is_prime"):
        spec = next(s for s in base_specs if s.signature.name == fn)
        sol = solutions[fn]

        # wrong -> fix
        wrong = sol.replace("return", "return  # WRONG\n    return", 1)
        scenarios.append(Scenario(name=f"{fn}::wrong_then_fix_golden", spec=spec, submission_sequence=[wrong, sol]))

        # forbidden import -> fix
        scenarios.append(Scenario(name=f"{fn}::forbidden_import_then_fix_golden", spec=spec, submission_sequence=["import os\n"+sol, sol]))

        # timeout -> fix
        scenarios.append(Scenario(name=f"{fn}::timeout_then_fix_golden", spec=spec, submission_sequence=[
            f"def {fn}(*args, **kwargs):\n    while True:\n        pass\n",
            sol,
        ]))

        # missing fn -> fix
        scenarios.append(Scenario(name=f"{fn}::missing_function_then_fix_golden", spec=spec, submission_sequence=[
            "def not_the_right_function(*args, **kwargs):\n    return None\n",
            sol,
        ]))

    # Flaky verification escape: seed=7 makes count_vowels hidden tests flaky (by design in templates).
    flake_specs = available_specs(seed=7)
    flake_spec = next(s for s in flake_specs if s.signature.name == "count_vowels")
    flake_sol = GenerateDraftTool().run(spec=flake_spec).result.reference_solution.get_secret_value()
    scenarios.append(Scenario(name="count_vowels::flaky_verification_regen_golden", spec=flake_spec, submission_sequence=[flake_sol]))

    return scenarios


def run_golden_suite() -> List[Dict[str, Any]]:
    scenarios = golden_scenarios()

    results: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="var_golden_") as td:
        root = Path(td)
        orch, _store = _make_orchestrator(root)

        for sc in scenarios:
            io = SyntheticIO(sc)
            final = orch.run_session(io=io, specs=[sc.spec])
            results.append(
                {
                    "scenario": sc.name,
                    "terminal_state": final.current_state.value,
                    "passed": final.current_state == AgentNode.TerminalSuccess,
                    "regen_count": final.loop_counters.regen_count,
                    "attempts": len(final.attempts),
                    "hints": sum(len(a.hints_used) for a in final.attempts),
                }
            )

    return results


def main() -> None:
    results = run_golden_suite()
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"Golden suite: {passed}/{total} passed")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"- {status} {r['scenario']} :: {r['terminal_state']} (regen={r['regen_count']}, attempts={r['attempts']}, hints={r['hints']})")
