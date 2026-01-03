from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

from pydantic import TypeAdapter

from ..types import ExecutionLimits, ExecutionReport, TestCaseResult, ToolError, ToolErrorCode
from ..utils import truncate
from .base import Tool, ToolResult


_RUNNER_FILENAME = "run_tests.py"
_SOLUTION_FILENAME = "solution.py"
_TESTS_FILENAME = "tests.py"


def _quantize_ms(ms: int, quantum: int = 10) -> int:
    """Reduce wall-time jitter for deterministic reports.

    This project cares about *correctness determinism* more than micro-benchmark precision.
    We bucket runtime to make unit tests stable across machines and loads.
    """
    if ms < 0:
        return 0
    return int(ms // quantum) * quantum


def _runner_source() -> str:
    # The runner avoids leaking hidden tests by never printing source lines from tracebacks.
    # It prints exactly one JSON object to stdout (sys.__stdout__) at the end.
    return r'''
import io
import json
import os
import random
import sys
import time
import traceback
import unittest
from types import TracebackType
from typing import Any, Dict, List, Optional, Tuple

# Determinism knobs
random.seed(0)
os.environ.setdefault("PYTHONHASHSEED", "0")

# In isolated mode (-I), Python does not include the script directory on sys.path.
# Add the working directory explicitly so `import solution` and `import tests` work.
sys.path.insert(0, os.getcwd())

_ORIG_STDOUT = sys.__stdout__
_ORIG_STDERR = sys.__stderr__

_capture_out = io.StringIO()
_capture_err = io.StringIO()

# Capture everything the submission might print, including at import-time.
sys.stdout = _capture_out
sys.stderr = _capture_err


def _sanitize_exc(exc_info: Tuple[type, BaseException, TracebackType]) -> Dict[str, Any]:
    exc_type, exc, tb = exc_info
    frames = []
    for f in traceback.extract_tb(tb):
        frames.append({
            "file": os.path.basename(f.filename),
            "line": int(f.lineno),
            "function": str(f.name),
        })
    return {
        "error_type": getattr(exc_type, "__name__", str(exc_type)),
        "message": str(exc),
        "frames": frames,
    }


class CapturingResult(unittest.TestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases: List[Dict[str, Any]] = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.cases.append({"test_name": test.id(), "passed": True})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.cases.append({"test_name": test.id(), "passed": False, "exception": _sanitize_exc(err)})

    def addError(self, test, err):
        super().addError(test, err)
        self.cases.append({"test_name": test.id(), "passed": False, "exception": _sanitize_exc(err)})


def main() -> None:
    started = time.time()
    payload: Dict[str, Any] = {
        "passed": False,
        "runtime_ms": 0,
        "stdout": "",
        "stderr": "",
        "tests": [],
    }

    try:
        try:
            import solution  # noqa: F401
        except Exception:
            payload["tests"] = [{
                "test_name": "__import_solution__",
                "passed": False,
                "exception": _sanitize_exc(sys.exc_info()),
            }]
            return
        try:
            import tests as tests_module
        except Exception:
            payload["tests"] = [{
                "test_name": "__import_tests__",
                "passed": False,
                "exception": _sanitize_exc(sys.exc_info()),
            }]
            return

        suite = unittest.defaultTestLoader.loadTestsFromModule(tests_module)
        runner = unittest.TextTestRunner(
            stream=io.StringIO(),  # never print unittest output to stdout/stderr
            verbosity=0,
            resultclass=CapturingResult,
        )
        result: CapturingResult = runner.run(suite)  # type: ignore[assignment]
        payload["tests"] = result.cases
        payload["passed"] = result.wasSuccessful()
    finally:
        payload["runtime_ms"] = int((time.time() - started) * 1000)
        payload["stdout"] = _capture_out.getvalue()
        payload["stderr"] = _capture_err.getvalue()

        # Restore (not strictly necessary, but keeps things tidy)
        sys.stdout = _ORIG_STDOUT
        sys.stderr = _ORIG_STDERR

        print(json.dumps(payload, ensure_ascii=False), file=_ORIG_STDOUT)


if __name__ == "__main__":
    main()
'''


def _limit_preexec(max_runtime_s: float, max_memory_mb: int) -> None:
    """Best-effort resource limits (POSIX only)."""
    try:
        import resource  # POSIX-only

        # CPU time limit: give a tiny cushion over wall-time to tolerate scheduling jitter.
        cpu_s = max(1, int(math.ceil(max_runtime_s)) + 1)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))

        # Virtual memory limit (address space). Not perfect, but useful in teaching labs.
        bytes_limit = int(max_memory_mb) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))

        # Limit file descriptors.
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))

        # Limit file size output (in bytes).
        resource.setrlimit(resource.RLIMIT_FSIZE, (5 * 1024 * 1024, 5 * 1024 * 1024))
    except Exception:
        # If resource limits are unavailable, continue without them.
        return


class SandboxRunner(Tool):
    """Runs code+tests in a constrained subprocess and returns a structured ExecutionReport.

    This is intentionally *not* a hardened sandbox. It's a clean interface you can later swap with:
    - containers,
    - microVMs,
    - remote sandboxes,
    - secure interpreters.

    The key goal is deterministic, structured evaluation + failure modes.
    """

    name = "sandbox.run"
    version = "local-subprocess-v1"

    def __init__(self) -> None:
        self._adapter = TypeAdapter(dict)

    def run(self, *, code: str, tests: str, limits: ExecutionLimits) -> ToolResult[ExecutionReport]:
        # Basic validation at the boundary
        if not isinstance(code, str) or not isinstance(tests, str):
            return ToolResult.failure(
                ToolError(
                    code=ToolErrorCode.ValidationError,
                    retryable=False,
                    safe_message="Invalid sandbox inputs.",
                    debug={"type_code": str(type(code)), "type_tests": str(type(tests))},
                )
            )

        max_runtime_s = max(0.05, limits.max_runtime_ms / 1000.0)

        with tempfile.TemporaryDirectory(prefix="var_sandbox_") as tmpdir:
            td = Path(tmpdir)
            (td / _SOLUTION_FILENAME).write_text(code, encoding="utf-8")
            (td / _TESTS_FILENAME).write_text(tests, encoding="utf-8")
            (td / _RUNNER_FILENAME).write_text(_runner_source(), encoding="utf-8")

            env = os.environ.copy()
            env["PYTHONHASHSEED"] = "0"
            # Make execution more deterministic by ignoring user/site packages.
            cmd = [sys.executable, "-I", "-S", _RUNNER_FILENAME]

            started = time.time()
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(td),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=max_runtime_s,
                    preexec_fn=(lambda: _limit_preexec(max_runtime_s, limits.max_memory_mb))
                    if os.name == "posix"
                    else None,
                )
            except subprocess.TimeoutExpired:
                return ToolResult.failure(
                    ToolError(
                        code=ToolErrorCode.Timeout,
                        retryable=True,
                        safe_message="Sandbox timed out.",
                        debug={"max_runtime_ms": limits.max_runtime_ms},
                    )
                )
            except Exception as e:
                return ToolResult.failure(
                    ToolError(
                        code=ToolErrorCode.TransientError,
                        retryable=True,
                        safe_message="Sandbox execution failed.",
                        debug={"exception": repr(e)},
                    )
                )

            wall_ms = int((time.time() - started) * 1000)

            # Runner prints JSON to stdout. If parsing fails, treat as a tool error.
            try:
                raw = json.loads(proc.stdout.strip() or "{}")
            except Exception:
                return ToolResult.failure(
                    ToolError(
                        code=ToolErrorCode.PermanentError,
                        retryable=False,
                        safe_message="Sandbox produced invalid output.",
                        debug={"stdout": truncate(proc.stdout, 2000), "stderr": truncate(proc.stderr, 2000)},
                    )
                )

            # Validate runner payload shape loosely.
            passed = bool(raw.get("passed", False))
            runtime_ms = _quantize_ms(int(raw.get("runtime_ms", wall_ms)))
            stdout = truncate(str(raw.get("stdout", "")), limits.max_output_chars)
            stderr = truncate(str(raw.get("stderr", "")), limits.max_output_chars)

            test_results: List[TestCaseResult] = []
            def _redact_file(name: str) -> str:
                if name == "tests.py":
                    return "<hidden_tests>"
                if name == "solution.py":
                    return "<submission>"
                if name == "run_tests.py":
                    return "<runner>"
                return name

            for t in raw.get("tests", []) or []:
                test_name = str(t.get("test_name", "unknown"))
                if t.get("passed", False):
                    test_results.append(TestCaseResult(test_name=test_name, passed=True))
                else:
                    exc = t.get("exception") or {}
                    err_type = str(exc.get("error_type") or "Exception")
                    # Build a line-free, non-leaky trace representation.
                    frames = exc.get("frames") or []
                    frame_str = " -> ".join(
                        [f'{_redact_file(str(f.get("file")))}:{f.get("line")}:{f.get("function")}' for f in frames][:10]
                    )
                    message = str(exc.get("message") or "")
                    sanitized = f"{err_type}: {message}"
                    if frame_str:
                        sanitized += f"\nframes: {frame_str}"
                    test_results.append(
                        TestCaseResult(
                            test_name=test_name,
                            passed=False,
                            error_type=err_type,
                            sanitized_trace=truncate(sanitized, 2000),
                        )
                    )

            report = ExecutionReport(
                passed=passed,
                runtime_ms=runtime_ms,
                stdout=stdout,
                stderr=stderr,
                test_results=test_results,
                timeout=False,
                sandbox_violation=False,
                returncode=int(proc.returncode),
            )

            return ToolResult.success(report)
