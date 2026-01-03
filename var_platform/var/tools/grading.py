from __future__ import annotations

import ast
from typing import List, Optional

from ..store.exercise_store import ExerciseStore
from ..types import (
    Constraints,
    ExecutionLimits,
    GradeReport,
    Submission,
    TestCaseResult,
)
from ..utils import extract_function_signature, scan_forbidden_imports
from .base import Tool, ToolResult
from .sandbox import SandboxRunner


def _first_top_level_function_name(code: str) -> Optional[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return node.name
    return None


class GradeSubmissionTool(Tool):
    """Grades a learner submission deterministically against hidden tests."""

    name = "grader.grade"
    version = "grader-v1"

    def __init__(self, store: ExerciseStore, sandbox: SandboxRunner):
        self._store = store
        self._sandbox = sandbox

    def run(self, *, submission: Submission, constraints: Constraints) -> ToolResult[GradeReport]:
        artifact = self._store.get(submission.artifact_id)

        policy_flags: List[str] = []

        # Policy: forbidden imports are a hard fail (do not even run).
        forbidden = scan_forbidden_imports(submission.learner_code, constraints.forbidden_imports)
        if forbidden:
            policy_flags.append("forbidden_import_used")
            test_results = [
                TestCaseResult(
                    test_name="__policy__forbidden_imports__",
                    passed=False,
                    error_type="SandboxViolation",
                    sanitized_trace=f"Forbidden imports used: {', '.join(forbidden)}",
                )
            ]
            return ToolResult.success(
                GradeReport(
                    artifact_id=submission.artifact_id,
                    passed=False,
                    test_results=test_results,
                    score=0.0,
                    runtime_ms=0,
                    policy_flags=policy_flags,
                )
            )

        # UX nicety: if function name doesn't match expected, fail early with clear message.
        expected_fn = _first_top_level_function_name(artifact.reference_solution)
        code_parses = True
        try:
            ast.parse(submission.learner_code)
        except SyntaxError:
            code_parses = False

        if expected_fn and code_parses:
            learner_fn = extract_function_signature(submission.learner_code, expected_fn)
            if learner_fn is None:
                policy_flags.append("missing_required_function")
                test_results = [
                    TestCaseResult(
                        test_name="__signature__",
                        passed=False,
                        error_type="SignatureError",
                        sanitized_trace=f"Expected a top-level function named '{expected_fn}'.",
                    )
                ]
                return ToolResult.success(
                    GradeReport(
                        artifact_id=submission.artifact_id,
                        passed=False,
                        test_results=test_results,
                        score=0.0,
                        runtime_ms=0,
                        policy_flags=policy_flags,
                    )
                )
        limits = ExecutionLimits(
            max_runtime_ms=constraints.max_runtime_ms,
            max_memory_mb=constraints.max_memory_mb,
        )

        run_res = self._sandbox.run(code=submission.learner_code, tests=artifact.hidden_tests, limits=limits)
        if not run_res.ok:
            policy_flags.append(run_res.error.code.value)
            test_results = [
                TestCaseResult(
                    test_name="__sandbox__",
                    passed=False,
                    error_type=run_res.error.code.value,
                    sanitized_trace=run_res.error.safe_message,
                )
            ]
            return ToolResult.success(
                GradeReport(
                    artifact_id=submission.artifact_id,
                    passed=False,
                    test_results=test_results,
                    score=0.0,
                    runtime_ms=constraints.max_runtime_ms,
                    policy_flags=policy_flags,
                )
            )

        report = run_res.result
        total = max(1, len(report.test_results))
        passed_count = sum(1 for t in report.test_results if t.passed)
        score = passed_count / total

        # Policy flag for timeouts / runtime spikes (best-effort)
        if report.runtime_ms > constraints.max_runtime_ms:
            policy_flags.append("runtime_exceeded")

        return ToolResult.success(
            GradeReport(
                artifact_id=submission.artifact_id,
                passed=report.passed,
                test_results=report.test_results,
                score=score,
                runtime_ms=report.runtime_ms,
                policy_flags=policy_flags,
            )
        )
