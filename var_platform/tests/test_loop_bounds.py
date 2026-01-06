import tempfile
import unittest
from pathlib import Path

from var.agent.orchestrator import Toolbox, VAROrchestrator
from var.config import RuntimeConfig
from var.store.exercise_store import ExerciseStore
from var.store.trace_store import FileTraceStore
from var.tools.exercise_generation import CompileDraftTool, GenerateDraftTool, available_specs
from var.tools.grading import GradeSubmissionTool
from var.tools.hinting import MakeHintTool
from var.tools.observability import TraceLogTool
from var.tools.presentation_gate import GateExerciseViewTool, GateGradeReportTool, GateHintTool
from var.tools.sandbox import SandboxRunner
from var.types import Outcome, OutcomeKind, VerificationReport, VerificationStatus
from var.tools.base import Tool, ToolResult


class AlwaysFailVerifyTool(Tool):
    name = "exercise.verify"
    version = "test-always-fail"

    def run(self, *, artifact, constraints, repeats: int = 2):
        return ToolResult.success(
            Outcome.fail(kind=OutcomeKind.Fail, value=VerificationReport(
                artifact_id=artifact.artifact_id,
                status=VerificationStatus.FAIL,
                checks=[],
                execution_reports=[],
                failure_reason="forced",
                repair_hint="forced",
            ), reason="forced")
        )


class NoPresentIO:
    def __init__(self, spec):
        self.spec = spec
        self.present_calls = 0

    def choose_spec(self, specs):
        return self.spec

    def present_exercise(self, view):
        self.present_calls += 1

    def get_submission(self, *, artifact_id: str, starter_code: str) -> str:
        return starter_code

    def show_grade(self, grade):
        pass

    def show_hint(self, hint):
        pass

    def show_message(self, message: str) -> None:
        pass


class TestLoopBounds(unittest.TestCase):
    def test_regeneration_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = ExerciseStore(root)
            trace_store = FileTraceStore(root)
            sandbox = SandboxRunner()

            spec = available_specs(seed=0)[0]

            tools = Toolbox(
                generate_draft=GenerateDraftTool(),
                compile_draft=CompileDraftTool(),
                verify=AlwaysFailVerifyTool(),  # force failure
                grade=GradeSubmissionTool(store, sandbox),
                hint=MakeHintTool(store),
                gate_exercise_view=GateExerciseViewTool(),
                gate_grade_report=GateGradeReportTool(),
                gate_hint=GateHintTool(),
                trace_log=TraceLogTool(trace_store),
            )

            cfg = RuntimeConfig(max_regenerations_per_spec=2, max_steps=30)
            orchestrator = VAROrchestrator(config=cfg, store=store, tools=tools)
            io = NoPresentIO(spec)

            final_state = orchestrator.run_session(io=io, specs=[spec])

            self.assertEqual(final_state.current_state.value, "TerminalFailure")
            self.assertLessEqual(final_state.loop_counters.regen_count, cfg.max_regenerations_per_spec)
            # Never present anything because verification never PASS.
            self.assertEqual(io.present_calls, 0)
