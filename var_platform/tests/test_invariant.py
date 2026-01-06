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
from var.tools.verification import ExerciseVerifyTool
from var.types import (
    AgentNode,
    AgentState,
    CheckStatus,
    Outcome,
    OutcomeKind,
    PresentationKind,
    VerificationCheck,
    VerificationReport,
    VerificationStatus,
)


class NoOpIO:
    def __init__(self, spec):
        self.spec = spec
        self.present_calls = 0

    def choose_spec(self, specs):
        return self.spec

    def present_exercise(self, view):
        self.present_calls += 1

    def get_submission(self, *, artifact_id: str, starter_code: str) -> str:
        # Always return starter code; will likely fail grading and drive the loop.
        return starter_code

    def show_grade(self, grade):
        pass

    def show_hint(self, hint):
        pass

    def show_message(self, message: str) -> None:
        pass


class TestInvariant(unittest.TestCase):
    def _make_orchestrator(self, root: Path) -> tuple[VAROrchestrator, ExerciseStore]:
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
        orchestrator = VAROrchestrator(config=RuntimeConfig(max_steps=50), store=store, tools=tools)
        return orchestrator, store

    def test_present_exercise_requires_verified_pass(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator, _store = self._make_orchestrator(Path(tmpdir))
            spec = available_specs(seed=0)[0]
            io = NoOpIO(spec)

            final_state = orchestrator.run_session(io=io, specs=[spec])

            self.assertGreater(io.present_calls, 0, "Exercise should have been presented via PresentationGate.")
            self.assertIsNotNone(final_state.verification)
            self.assertTrue(final_state.verification.passed, "Template exercises should verify PASS.")
            self.assertIn(final_state.current_state, [AgentNode.TerminalSuccess, AgentNode.TerminalFailure])

    def test_invariant_guard_trips_if_forced(self):
        # Force: PresentationGate with pending exercise but a FAIL verification.
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orchestrator, store = self._make_orchestrator(root)

            spec = available_specs(seed=0)[0]
            io = NoOpIO(spec)

            draft = orchestrator._tools.generate_draft.run(spec=spec).result  # type: ignore[attr-defined]
            artifact = orchestrator._tools.compile_draft.run(draft=draft, spec=spec).result  # type: ignore[attr-defined]
            store.put(artifact)

            report = VerificationReport(
                artifact_id=artifact.artifact_id,
                status=VerificationStatus.FAIL,
                checks=[VerificationCheck(name="x", status=CheckStatus.FAIL, details="forced")],
                execution_reports=[],
                failure_reason="forced",
            )

            state = AgentState(run_id="test")
            state.spec = spec
            state.artifact_id = artifact.artifact_id
            state.verification = Outcome.fail(kind=OutcomeKind.Fail, value=report, reason="forced")
            state.pending_presentation_kind = PresentationKind.exercise
            state.pending_exercise_view = artifact.view_for_learner()
            state.post_presentation_state = AgentNode.AwaitSubmission
            state.current_state = AgentNode.PresentationGate

            new_state = orchestrator._handle_presentation_gate(state, io, [spec])  # type: ignore[attr-defined]
            self.assertEqual(new_state.current_state, AgentNode.TerminalFailure)
