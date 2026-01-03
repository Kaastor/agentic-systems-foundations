import tempfile
import unittest
from pathlib import Path

from var.agent.orchestrator import Toolbox, VAROrchestrator
from var.config import RuntimeConfig
from var.eval.harness import SyntheticIO
from var.store.exercise_store import FileExerciseStore
from var.store.run_store import FileRunStore
from var.store.trace_store import FileTraceStore
from var.tools.exercise_generation import CompileDraftTool
from var.tools.grading import GradeSubmissionTool
from var.tools.hinting import MakeHintTool
from var.tools.math_generation import MathGenerateDraftTool, available_math_specs, arithmetic_problem
from var.tools.observability import TraceLogTool
from var.tools.sandbox import SandboxRunner
from var.tools.verification import VerifyExerciseTool
from var.types import AgentNode


class TestMathGeneration(unittest.TestCase):
    def test_math_specs_can_run_end_to_end(self):
        specs = available_math_specs(seed=123)
        self.assertTrue(specs)

        with tempfile.TemporaryDirectory() as tmp:
            root = tmp
            exercise_store = FileExerciseStore(Path(root) / "exercises")
            trace_store = FileTraceStore(Path(root) / "traces")
            run_store = FileRunStore(Path(root) / "runs")

            sandbox = SandboxRunner()
            tools = Toolbox(
                generate_draft=MathGenerateDraftTool(),
                compile_draft=CompileDraftTool(),
                verify_exercise=VerifyExerciseTool(sandbox=sandbox),
                grade_submission=GradeSubmissionTool(sandbox=sandbox, store=exercise_store),
                make_hint=MakeHintTool(store=exercise_store),
                trace_log=TraceLogTool(trace_store),
            )

            config = RuntimeConfig(max_steps=50)
            orch = VAROrchestrator(config=config, tools=tools, store=exercise_store, run_store=run_store)

            # Use a synthetic learner that submits the correct answer immediately.
            # We compute the correct answer using the same deterministic helper.
            spec = specs[0]
            fn = spec.signature.name
            op_map = {"answer_add": "+", "answer_sub": "-", "answer_mul": "*"}
            a, b, op, expected = arithmetic_problem(seed=spec.seed, difficulty=spec.difficulty, op=op_map[fn])
            correct_code = f"def {fn}() -> int:\n    return {expected}\n"

            io = SyntheticIO(spec=spec, submission_sequence=[correct_code])
            final_state = orch.run_session(io=io, specs=specs)

            self.assertEqual(final_state.current_state, AgentNode.TerminalSuccess)


if __name__ == "__main__":
    unittest.main()
