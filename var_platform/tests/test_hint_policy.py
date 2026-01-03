import tempfile
import unittest
from pathlib import Path

from var.store.exercise_store import ExerciseStore
from var.tools.exercise_generation import CompileDraftTool, GenerateDraftTool, available_specs
from var.tools.hinting import MakeHintTool
from var.types import GradeReport, HintPolicy, TestCaseResult


class TestHintPolicy(unittest.TestCase):
    def test_hint_does_not_reveal_solution_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = ExerciseStore(root)

            spec = available_specs(seed=0)[0]
            draft = GenerateDraftTool().run(spec=spec).result
            artifact = CompileDraftTool().run(draft=draft, spec=spec).result
            store.put(artifact)

            tutor = MakeHintTool(store)

            grade = GradeReport(
                artifact_id=artifact.artifact_id,
                passed=False,
                test_results=[TestCaseResult(test_name="t", passed=False, error_type="AssertionError", sanitized_trace="x")],
                score=0.0,
                runtime_ms=1,
                policy_flags=[],
            )
            hint = tutor.run(grade=grade, hint_level=1, policy=HintPolicy(), attempt_index=0).result
            self.assertFalse(hint.reveals_solution)
