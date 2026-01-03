import unittest

from var.eval.harness import run_eval_suite


class TestEvalHarness(unittest.TestCase):
    def test_eval_suite_passes(self):
        results = run_eval_suite()
        # 5 specs * 6 scenarios per spec = 30
        self.assertEqual(len(results), 30)
        self.assertTrue(all(r["passed"] for r in results), msg=str([r for r in results if not r["passed"]][:3]))


if __name__ == "__main__":
    unittest.main()
