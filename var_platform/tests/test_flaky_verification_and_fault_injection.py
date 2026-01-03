import tempfile
import unittest
from pathlib import Path

from var.agent.orchestrator import Toolbox, VAROrchestrator
from var.config import RuntimeConfig
from var.eval.harness import SyntheticIO
from var.eval.scenarios import Scenario
from var.research.fault_injection import FaultInjectingTool, FaultRule
from var.store.exercise_store import ExerciseStore
from var.store.trace_store import FileTraceStore
from var.tools.exercise_generation import CompileDraftTool, GenerateDraftTool, available_specs
from var.tools.grading import GradeSubmissionTool
from var.tools.hinting import MakeHintTool
from var.tools.observability import TraceLogTool
from var.tools.sandbox import SandboxRunner
from var.tools.verification import ExerciseVerifyTool
from var.types import AgentNode, ToolErrorCode


class TestFlakyVerificationAndFaultInjection(unittest.TestCase):
    def test_flaky_hidden_tests_triggers_regen_then_succeeds(self):
        """Seed=7 triggers an intentional flaky hidden-test variant for count_vowels.

        The verifier should detect flakiness (repeat fingerprints differ), forcing the
        agent to regenerate (seed bump) until it finds a non-flaky variant.
        """
        with tempfile.TemporaryDirectory(prefix="var_flake_") as td:
            root = Path(td)
            store = ExerciseStore(root)
            traces = FileTraceStore(root)

            # Seed=7 triggers the flaky hidden-tests variant inside CountVowelsTemplate.
            specs = available_specs(seed=7)
            spec = next(s for s in specs if s.signature.name == "count_vowels")

            correct = GenerateDraftTool().run(spec=spec).result.reference_solution
            scenario = Scenario(
                name="count_vowels::flaky_verification_regen",
                spec=spec,
                submission_sequence=[correct],
            )

            sandbox = SandboxRunner()
            tools = Toolbox(
                generate_draft=GenerateDraftTool(),
                compile_draft=CompileDraftTool(),
                verify=ExerciseVerifyTool(sandbox),
                grade=GradeSubmissionTool(store, sandbox),
                hint=MakeHintTool(store),
                trace_log=TraceLogTool(traces),
            )

            cfg = RuntimeConfig(max_steps=80, verification_repeats=2)
            orch = VAROrchestrator(config=cfg, store=store, tools=tools)

            io = SyntheticIO(scenario)
            final_state = orch.run_session(io=io, specs=specs)

            self.assertEqual(final_state.current_state, AgentNode.TerminalSuccess)
            # Must have regenerated at least once to escape the flaky variant.
            self.assertGreaterEqual(final_state.loop_counters.regen_count, 1)

    def test_fault_injection_transient_error_is_retried(self):
        """A retryable injected tool error should be handled by ToolExecutor retries."""
        with tempfile.TemporaryDirectory(prefix="var_fault_") as td:
            root = Path(td)
            store = ExerciseStore(root)
            traces = FileTraceStore(root)

            spec = available_specs(seed=0)[0]
            correct = GenerateDraftTool().run(spec=spec).result.reference_solution
            scenario = Scenario(
                name=f"{spec.signature.name}::transient_tool_error",
                spec=spec,
                submission_sequence=[correct],
            )

            # Fail the first call to generate_draft with a retryable transient error.
            gen = FaultInjectingTool(
                inner=GenerateDraftTool(),
                rules=[
                    FaultRule(
                        tool_name="exercise.generate_draft",
                        nth_call=1,
                        error_code=ToolErrorCode.TransientError,
                        retryable=True,
                        safe_message="Injected transient failure (test).",
                    )
                ],
            )

            sandbox = SandboxRunner()
            tools = Toolbox(
                generate_draft=gen,  # wrapper preserves tool name + version
                compile_draft=CompileDraftTool(),
                verify=ExerciseVerifyTool(sandbox),
                grade=GradeSubmissionTool(store, sandbox),
                hint=MakeHintTool(store),
                trace_log=TraceLogTool(traces),
            )

            cfg = RuntimeConfig(max_steps=80)
            orch = VAROrchestrator(config=cfg, store=store, tools=tools)

            io = SyntheticIO(scenario)
            final_state = orch.run_session(io=io, specs=[spec])

            self.assertEqual(final_state.current_state, AgentNode.TerminalSuccess)
            # The retry should avoid a full regeneration.
            self.assertEqual(final_state.loop_counters.regen_count, 0)


if __name__ == "__main__":
    unittest.main()
