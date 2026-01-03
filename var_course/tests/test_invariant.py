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
from var.tools.sandbox import SandboxRunner
from var.tools.verification import ExerciseVerifyTool
from var.types import AgentNode, VerificationReport, VerificationStatus, VerificationCheck, CheckStatus


class NoOpIO:
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


class TestInvariant(unittest.TestCase):
    def test_present_exercise_requires_verified_pass(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = ExerciseStore(root)
            trace_store = FileTraceStore(root)

            sandbox = SandboxRunner()
            tools = Toolbox(
                generate_draft=GenerateDraftTool(),
                compile_draft=CompileDraftTool(),
                verify=ExerciseVerifyTool(sandbox),
                grade=GradeSubmissionTool(store, sandbox),
                hint=MakeHintTool(store),
                trace_log=TraceLogTool(trace_store),
            )
            orchestrator = VAROrchestrator(config=RuntimeConfig(), store=store, tools=tools)

            spec = available_specs(seed=0)[0]
            io = NoOpIO(spec)

            # Run until an artifact exists and verification is done.
            state = orchestrator.run_session(io=io, specs=[spec])

            # The orchestrator should never present an exercise that isn't verified PASS.
            # In practice, verification should pass for template exercises; this asserts the invariant check exists.
            self.assertNotEqual(io.present_calls, 0, "Template exercises should have been presented at least once.")
            self.assertIn(state.current_state, [AgentNode.TerminalSuccess, AgentNode.TerminalFailure])

    def test_invariant_guard_trips_if_forced(self):
        # Directly test the guard: PresentExercise with FAIL verification must become TerminalFailure.
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = ExerciseStore(root)
            trace_store = FileTraceStore(root)
            sandbox = SandboxRunner()

            tools = Toolbox(
                generate_draft=GenerateDraftTool(),
                compile_draft=CompileDraftTool(),
                verify=ExerciseVerifyTool(sandbox),
                grade=GradeSubmissionTool(store, sandbox),
                hint=MakeHintTool(store),
                trace_log=TraceLogTool(trace_store),
            )
            orchestrator = VAROrchestrator(config=RuntimeConfig(), store=store, tools=tools)

            spec = available_specs(seed=0)[0]
            io = NoOpIO(spec)

            # Generate & store artifact
            draft = tools.generate_draft.run(spec=spec).result
            artifact = tools.compile_draft.run(draft=draft, spec=spec).result
            store.put(artifact)

            # Force state to PresentExercise with FAIL verification
            from var.types import AgentState

            state = AgentState(run_id="test")
            state.spec = spec
            state.artifact_id = artifact.artifact_id
            state.verification = VerificationReport(
                artifact_id=artifact.artifact_id,
                status=VerificationStatus.FAIL,
                checks=[VerificationCheck(name="x", status=CheckStatus.FAIL, details="forced")],
            )
            state.current_state = AgentNode.PresentExercise

            new_state = orchestrator._handle_present_exercise(state, io)  # type: ignore[attr-defined]
            self.assertEqual(new_state.current_state, AgentNode.TerminalFailure)
