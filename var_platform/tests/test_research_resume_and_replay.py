import tempfile
import unittest
from pathlib import Path

from var.agent.orchestrator import Toolbox, SimulatedCrash, VAROrchestrator
from var.agent.tool_executor import ToolExecutorConfig
from var.config import ResearchConfig, RuntimeConfig
from var.eval.harness import SyntheticIO
from var.eval.scenarios import Scenario
from var.research.replay import ReplayToolExecutor
from var.research.types import ToolIOCapture, utc_now
from var.store.exercise_store import ExerciseStore
from var.store.run_store import FileRunStore
from var.store.trace_store import FileTraceStore
from var.tools.exercise_generation import CompileDraftTool, GenerateDraftTool, available_specs
from var.tools.grading import GradeSubmissionTool
from var.tools.hinting import MakeHintTool
from var.tools.observability import TraceLogTool
from var.tools.presentation_gate import GateExerciseViewTool, GateGradeReportTool, GateHintTool
from var.tools.sandbox import SandboxRunner
from var.tools.verification import ExerciseVerifyTool
from var.types import AgentState, TraceEvent, TraceEventType


class TestResearchResumeAndReplay(unittest.TestCase):
    def _make_tools(self, store: ExerciseStore, trace_store: FileTraceStore):
        sandbox = SandboxRunner()
        return Toolbox(
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

    def test_crash_and_resume_from_snapshot(self):
        specs = available_specs(seed=0)
        spec = specs[0]

        # One correct submission is enough; the crash happens before grading.
        sol = GenerateDraftTool().run(spec=spec).result.reference_solution.get_secret_value()
        scenario = Scenario(name="crash_resume", spec=spec, submission_sequence=[sol])

        with tempfile.TemporaryDirectory(prefix="var_research_") as tmp:
            root = Path(tmp)
            store = ExerciseStore(root)
            trace_store = FileTraceStore(root)
            run_store = FileRunStore(root)
            tools = self._make_tools(store, trace_store)

            run_id = "crashrun"
            initial = AgentState(run_id=run_id)

            # Crash right after the first step (SelectSpec).
            cfg_crash = RuntimeConfig(
                research=ResearchConfig(
                    enabled=True,
                    crash_after_step=0,
                    record_state_snapshots=True,
                    tool_io_capture=ToolIOCapture.safe,
                    tags={"test": "crash_resume"},
                )
            )
            orch1 = VAROrchestrator(config=cfg_crash, store=store, tools=tools, run_store=run_store)

            io = SyntheticIO(scenario)
            with self.assertRaises(SimulatedCrash):
                orch1.run_session(io=io, specs=specs, initial_state=initial)

            checkpoint = run_store.load_latest_state(run_id)
            self.assertNotEqual(checkpoint.current_state.value, "TerminalSuccess")

            # Resume without crashing.
            cfg_resume = RuntimeConfig(research=ResearchConfig(enabled=True, record_state_snapshots=True))
            orch2 = VAROrchestrator(config=cfg_resume, store=store, tools=tools, run_store=run_store)
            final = orch2.run_session(io=io, specs=specs, initial_state=checkpoint)
            self.assertEqual(final.current_state.value, "TerminalSuccess")

    def test_replay_executor(self):
        specs = available_specs(seed=0)
        spec = specs[0]

        sol = GenerateDraftTool().run(spec=spec).result.reference_solution.get_secret_value()
        scenario = Scenario(name="replay", spec=spec, submission_sequence=[sol])

        with tempfile.TemporaryDirectory(prefix="var_replay_") as tmp:
            root = Path(tmp)
            store = ExerciseStore(root)
            trace_store = FileTraceStore(root)
            run_store = FileRunStore(root)
            tools = self._make_tools(store, trace_store)

            recorded_run_id = "recordedrun"
            initial = AgentState(run_id=recorded_run_id)

            cfg_record = RuntimeConfig(
                research=ResearchConfig(
                    enabled=True,
                    record_tool_io=True,
                    tool_io_capture=ToolIOCapture.full,
                    record_state_snapshots=False,
                    tags={"test": "replay_record"},
                )
            )
            orch = VAROrchestrator(config=cfg_record, store=store, tools=tools, run_store=run_store)
            io = SyntheticIO(scenario)
            final = orch.run_session(io=io, specs=specs, initial_state=initial)
            self.assertEqual(final.current_state.value, "TerminalSuccess")
            recorded_artifact = final.artifact_id

            # Build a replay executor that reuses the recorded tool outputs.
            def emit(state, event_type, node, details):
                tools.trace_log.run(
                    event=TraceEvent(
                        ts=utc_now(),
                        run_id=state.run_id,
                        event_type=event_type,
                        state=node,
                        details=details,
                    )
                )

            replay_exec = ReplayToolExecutor(
                emit=emit,
                run_store=run_store,
                recorded_run_id=recorded_run_id,
                executor_cfg=ToolExecutorConfig(max_retries=0),
            )

            cfg_replay = RuntimeConfig(research=ResearchConfig(enabled=False))
            orch_replay = VAROrchestrator(
                config=cfg_replay,
                store=store,
                tools=tools,
                run_store=None,
                tool_executor=replay_exec,
            )

            replay_state = AgentState(run_id="replayrun")
            io2 = SyntheticIO(scenario)
            final2 = orch_replay.run_session(io=io2, specs=specs, initial_state=replay_state)
            self.assertEqual(final2.current_state.value, "TerminalSuccess")
            self.assertEqual(final2.artifact_id, recorded_artifact)


if __name__ == "__main__":
    unittest.main()
