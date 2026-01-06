import tempfile
import unittest
from pathlib import Path

from var.agent.orchestrator import Toolbox, VAROrchestrator
from var.config import RuntimeConfig
from var.eval.harness import SyntheticIO
from var.eval.scenarios import Scenario
from var.store.exercise_store import ExerciseStore
from var.store.trace_store import FileTraceStore
from var.tools.exercise_generation import CompileDraftTool
from var.tools.grading import GradeSubmissionTool
from var.tools.hinting import MakeHintTool
from var.tools.math_generation import MathGenerateDraftTool, available_math_specs, arithmetic_problem
from var.tools.observability import TraceLogTool
from var.tools.presentation_gate import GateExerciseViewTool, GateGradeReportTool, GateHintTool
from var.tools.sandbox import SandboxRunner
from var.tools.verification import ExerciseVerifyTool
from var.types import AgentNode


class TestMathGeneration(unittest.TestCase):
    def test_math_specs_can_run_end_to_end(self):
        specs = available_math_specs(seed=123)
        self.assertTrue(specs)

        with tempfile.TemporaryDirectory(prefix="var_math_") as tmp:
            root = Path(tmp)
            store = ExerciseStore(root)
            trace_store = FileTraceStore(root)

            sandbox = SandboxRunner()
            tools = Toolbox(
                generate_draft=MathGenerateDraftTool(),
                compile_draft=CompileDraftTool(),
                verify=ExerciseVerifyTool(sandbox),
                grade=GradeSubmissionTool(store, sandbox),
                hint=MakeHintTool(store),
                gate_exercise_view=GateExerciseViewTool(),
                gate_grade_report=GateGradeReportTool(),
                gate_hint=GateHintTool(),
                trace_log=TraceLogTool(trace_store),
            )

            config = RuntimeConfig(max_steps=50)
            orch = VAROrchestrator(config=config, tools=tools, store=store)

            # Use a synthetic learner that submits the correct answer immediately.
            spec = specs[0]
            fn = spec.signature.name
            op_map = {"answer_add": "+", "answer_sub": "-", "answer_mul": "*"}
            a, b, op, expected = arithmetic_problem(seed=spec.seed, difficulty=spec.difficulty, op=op_map[fn])
            correct_code = f"def {fn}() -> int:\n    return {expected}\n"

            scenario = Scenario(name=f"{fn}::correct_first_try", spec=spec, submission_sequence=[correct_code])
            io = SyntheticIO(scenario)
            final_state = orch.run_session(io=io, specs=specs)

            self.assertEqual(final_state.current_state, AgentNode.TerminalSuccess)
