from __future__ import annotations

import ast
from typing import List, Optional, Tuple

from ..types import (
    CheckStatus,
    Constraints,
    ExecutionLimits,
    ExerciseArtifact,
    VerificationCheck,
    VerificationReport,
    VerificationStatus,
)
from ..utils import extract_function_signature, scan_forbidden_imports
from .base import Tool, ToolResult
from .sandbox import SandboxRunner


def _first_top_level_function_name(code: str) -> Optional[str]:
    """Return the first top-level function name defined in `code`, if any."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return node.name
    return None


def _execution_fingerprint(report) -> Tuple:
    """A stable fingerprint for flake detection (ignores runtime/stdout noise)."""
    return tuple((t.test_name, t.passed, t.error_type) for t in report.test_results)


class ExerciseVerifyTool(Tool):
    """Verify an exercise artifact is valid and solvable under constraints.

    Output is a VerificationReport with granular checks, suitable for debugging and eval metrics.
    """

    name = "exercise.verify"
    version = "verifier-v1"

    def __init__(self, sandbox: SandboxRunner):
        self._sandbox = sandbox

    def run(
        self,
        *,
        artifact: ExerciseArtifact,
        constraints: Constraints,
        repeats: int = 2,
    ) -> ToolResult[VerificationReport]:
        checks: List[VerificationCheck] = []
        execution_reports = []

        target_fn = _first_top_level_function_name(artifact.reference_solution)
        if not target_fn:
            checks.append(
                VerificationCheck(
                    name="reference_solution_has_function",
                    status=CheckStatus.FAIL,
                    details="Could not find a top-level function in reference_solution.",
                )
            )
            return ToolResult.success(
                VerificationReport(
                    artifact_id=artifact.artifact_id,
                    status=VerificationStatus.FAIL,
                    checks=checks,
                    execution_reports=[],
                    failure_reason="Missing reference solution function definition.",
                    repair_hint="Ensure reference_solution defines the target function at top level.",
                )
            )

        # 1) Signature consistency (starter + reference)
        ref_sig = extract_function_signature(artifact.reference_solution, target_fn)
        starter_sig = extract_function_signature(artifact.starter_code, target_fn)

        if ref_sig is None:
            checks.append(
                VerificationCheck(
                    name="reference_solution_signature",
                    status=CheckStatus.FAIL,
                    details=f"Could not parse signature for '{target_fn}' in reference_solution.",
                )
            )
        else:
            checks.append(
                VerificationCheck(
                    name="reference_solution_signature",
                    status=CheckStatus.PASS,
                    details=f"Found '{target_fn}' args={list(ref_sig.arg_names)}",
                )
            )

        if starter_sig is None:
            checks.append(
                VerificationCheck(
                    name="starter_code_signature",
                    status=CheckStatus.FAIL,
                    details=f"Could not parse signature for '{target_fn}' in starter_code.",
                )
            )
        elif ref_sig is not None and list(starter_sig.arg_names) == list(ref_sig.arg_names):
            checks.append(
                VerificationCheck(
                    name="starter_code_signature",
                    status=CheckStatus.PASS,
                    details=f"Starter signature matches reference for '{target_fn}'.",
                )
            )
        else:
            checks.append(
                VerificationCheck(
                    name="starter_code_signature",
                    status=CheckStatus.FAIL,
                    details=f"Starter args {list(starter_sig.arg_names)} do not match reference args "
                    f"{list(ref_sig.arg_names) if ref_sig else '<?> '}.",
                )
            )

        # 2) Prompt mentions function name (simple, but catches many generator mistakes)
        if target_fn in artifact.prompt_md:
            checks.append(
                VerificationCheck(
                    name="prompt_mentions_function",
                    status=CheckStatus.PASS,
                    details=f"Prompt includes '{target_fn}'.",
                )
            )
        else:
            checks.append(
                VerificationCheck(
                    name="prompt_mentions_function",
                    status=CheckStatus.FAIL,
                    details=f"Prompt does not mention '{target_fn}'.",
                )
            )

        # 3) Forbidden imports (starter, reference, tests)
        forbidden_hits = {
            "starter_code": scan_forbidden_imports(artifact.starter_code, constraints.forbidden_imports),
            "reference_solution": scan_forbidden_imports(artifact.reference_solution, constraints.forbidden_imports),
            "hidden_tests": scan_forbidden_imports(artifact.hidden_tests, constraints.forbidden_imports),
            "public_tests": scan_forbidden_imports(artifact.public_tests or "", constraints.forbidden_imports),
        }
        any_forbidden = any(v for v in forbidden_hits.values())
        if any_forbidden:
            checks.append(
                VerificationCheck(
                    name="forbidden_imports",
                    status=CheckStatus.FAIL,
                    details=f"Forbidden imports found: {forbidden_hits}",
                )
            )
        else:
            checks.append(
                VerificationCheck(
                    name="forbidden_imports",
                    status=CheckStatus.PASS,
                    details="No forbidden imports detected.",
                )
            )

        # 4) Run reference solution against hidden tests (repeats)
        limits = ExecutionLimits(
            max_runtime_ms=constraints.max_runtime_ms,
            max_memory_mb=constraints.max_memory_mb,
        )

        fingerprints = []
        for i in range(max(1, repeats)):
            run_res = self._sandbox.run(code=artifact.reference_solution, tests=artifact.hidden_tests, limits=limits)
            if not run_res.ok:
                checks.append(
                    VerificationCheck(
                        name=f"sandbox_run_{i}",
                        status=CheckStatus.FAIL,
                        details=f"Sandbox error: {run_res.error.safe_message}",
                    )
                )
                return ToolResult.success(
                    VerificationReport(
                        artifact_id=artifact.artifact_id,
                        status=VerificationStatus.FAIL,
                        checks=checks,
                        execution_reports=[],
                        failure_reason="Sandbox failed during verification.",
                        repair_hint="Check sandbox limits or reference_solution for infinite loops / heavy computation.",
                    )
                )

            report = run_res.result
            execution_reports.append(report)
            fingerprints.append(_execution_fingerprint(report))

            if report.timeout or report.runtime_ms > constraints.max_runtime_ms:
                checks.append(
                    VerificationCheck(
                        name=f"runtime_bounds_{i}",
                        status=CheckStatus.FAIL,
                        details=f"Runtime exceeded: {report.runtime_ms}ms > {constraints.max_runtime_ms}ms",
                    )
                )
            else:
                checks.append(
                    VerificationCheck(
                        name=f"runtime_bounds_{i}",
                        status=CheckStatus.PASS,
                        details=f"Runtime ok: {report.runtime_ms}ms",
                    )
                )

            if not report.passed:
                checks.append(
                    VerificationCheck(
                        name=f"reference_solution_tests_{i}",
                        status=CheckStatus.FAIL,
                        details="Reference solution failed hidden tests.",
                    )
                )
            else:
                checks.append(
                    VerificationCheck(
                        name=f"reference_solution_tests_{i}",
                        status=CheckStatus.PASS,
                        details="Reference solution passed hidden tests.",
                    )
                )

        # 5) Flake detection: fingerprints must match across runs
        flaky = len(set(fingerprints)) > 1
        if flaky:
            checks.append(
                VerificationCheck(
                    name="flake_detection",
                    status=CheckStatus.FAIL,
                    details="Hidden test results differed between repeats (potential flakiness).",
                )
            )
        else:
            checks.append(
                VerificationCheck(
                    name="flake_detection",
                    status=CheckStatus.PASS,
                    details="Repeated runs consistent.",
                )
            )

        passed = all(c.status == CheckStatus.PASS for c in checks)
        status = VerificationStatus.PASS if passed else VerificationStatus.FAIL

        failure_reason: Optional[str] = None
        repair_hint: Optional[str] = None
        if status == VerificationStatus.FAIL:
            # Prefer global failures (like flaky tests) over per-run failures.
            preferred = next(
                (c for c in checks if c.name == "flake_detection" and c.status == CheckStatus.FAIL),
                None,
            )
            first_fail = preferred or next((c for c in checks if c.status == CheckStatus.FAIL), None)
            failure_reason = first_fail.details if first_fail else "Verification failed."

            if preferred is not None:
                repair_hint = "Hidden tests appear flaky. Remove time/random/external-state dependence."
            else:
                repair_hint = f"Fix failing check: {first_fail.name}" if first_fail else "Inspect checks."

        return ToolResult.success(
            VerificationReport(
                artifact_id=artifact.artifact_id,
                status=status,
                checks=checks,
                execution_reports=execution_reports,
                failure_reason=failure_reason,
                repair_hint=repair_hint,
            )
        )
