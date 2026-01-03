import tempfile
import unittest
from pathlib import Path

from var.store.exercise_store import ExerciseStore
from var.tools.exercise_generation import CompileDraftTool, GenerateDraftTool, available_specs
from var.tools.grading import GradeSubmissionTool
from var.tools.sandbox import SandboxRunner
from var.types import Submission, utc_now


class TestGradingDeterminism(unittest.TestCase):
    def test_same_submission_same_grade(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = ExerciseStore(root)
            sandbox = SandboxRunner()

            gen = GenerateDraftTool()
            comp = CompileDraftTool()
            grader = GradeSubmissionTool(store, sandbox)

            spec = available_specs(seed=0)[0]
            draft = gen.run(spec=spec).result
            artifact = comp.run(draft=draft, spec=spec).result
            store.put(artifact)

            # Perfect submission uses the reference solution (for deterministic test).
            sub = Submission(artifact_id=artifact.artifact_id, learner_code=artifact.reference_solution, submitted_at=utc_now())

            g1 = grader.run(submission=sub, constraints=spec.constraints).result
            g2 = grader.run(submission=sub, constraints=spec.constraints).result

            self.assertEqual(g1.model_dump(mode="json"), g2.model_dump(mode="json"))
            self.assertTrue(g1.passed)
