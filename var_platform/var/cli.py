from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .agent.orchestrator import Toolbox, SimulatedCrash, VAROrchestrator
from .config import ResearchConfig, RuntimeConfig, StorageConfig
from .io import SessionIO
from .research.types import ToolIOCapture
from .store.exercise_store import ExerciseStore
from .store.run_store import FileRunStore
from .store.trace_store import FileTraceStore
from .tools.exercise_generation import CompileDraftTool, GenerateDraftTool, available_specs
from .tools.grading import GradeSubmissionTool
from .tools.hinting import MakeHintTool
from .tools.observability import TraceLogTool
from .tools.sandbox import SandboxRunner
from .tools.verification import ExerciseVerifyTool
from .types import ExerciseSpec, ExerciseView, GradeReport, HintArtifact


class CLIIO(SessionIO):
    def choose_spec(self, specs: Sequence[ExerciseSpec]) -> ExerciseSpec:
        print("Choose an exercise:")
        for i, s in enumerate(specs):
            print(f"  [{i}] {s.signature.name} | difficulty={s.difficulty} | concepts={','.join(s.concepts)}")
        raw = input("Enter index (default 0): ").strip()
        idx = int(raw) if raw else 0
        idx = max(0, min(idx, len(specs) - 1))
        return specs[idx]

    def present_exercise(self, view: ExerciseView) -> None:
        print("\n" + "=" * 80)
        print(f"Exercise ID: {view.artifact_id}")
        print("=" * 80)
        print(view.prompt_md.strip())
        print("\n--- Starter code ---\n")
        print(view.starter_code.rstrip())
        if view.public_tests:
            print("\n--- Public tests ---\n")
            print(view.public_tests.rstrip())
        print("=" * 80 + "\n")

    def get_submission(self, *, artifact_id: str, starter_code: str) -> str:
        print("Submit your code. Options:")
        print("  1) Paste code (end with a line containing only EOF)")
        print("  2) Provide a path to a .py file")
        raw = input("Choose [1/2] (default 1): ").strip() or "1"
        if raw == "2":
            path = Path(input("Path to .py file: ").strip())
            return path.read_text(encoding="utf-8")

        print("Paste your full solution code now. End with EOF on its own line.")
        lines = []
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            if line.rstrip("\n") == "EOF":
                break
            lines.append(line)
        return "".join(lines).strip() or starter_code

    def show_grade(self, grade: GradeReport) -> None:
        print("\n--- Grade ---")
        print(f"Passed: {grade.passed} | score={grade.score:.2f} | runtime_ms={grade.runtime_ms}")
        if grade.policy_flags:
            print(f"Policy flags: {', '.join(grade.policy_flags)}")
        for tr in grade.test_results:
            status = "PASS" if tr.passed else "FAIL"
            print(f"  {status} {tr.test_name}")
            if not tr.passed and tr.sanitized_trace:
                print(f"    {tr.sanitized_trace}")
        print("---\n")

    def show_hint(self, hint: HintArtifact) -> None:
        print(f"Hint (level {hint.level}):\n")
        print(hint.hint_md.strip())
        print("\n")

    def show_message(self, message: str) -> None:
        print(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verified Agent Runtime (VAR) interactive CLI")
    p.add_argument("--root", type=str, default=".var_data", help="Workspace directory")
    p.add_argument("--research", action="store_true", help="Enable research-mode recording")
    p.add_argument(
        "--tool-io",
        choices=[c.value for c in ToolIOCapture],
        default=ToolIOCapture.safe.value,
        help="Tool I/O capture level (research mode)",
    )
    p.add_argument(
        "--crash-after-step",
        type=int,
        default=None,
        help="(Research) Simulate a crash after N steps. Use with --research.",
    )
    p.add_argument(
        "--resume-run",
        type=str,
        default=None,
        help="(Research) Resume an existing run_id from the latest snapshot.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv or sys.argv[1:])

    root = Path(args.root)
    store = ExerciseStore(root)
    trace_store = FileTraceStore(root)
    run_store = FileRunStore(root) if args.research else None

    research_cfg = ResearchConfig(
        enabled=args.research,
        tool_io_capture=ToolIOCapture(args.tool_io),
        crash_after_step=args.crash_after_step,
        tags={"entrypoint": "cli"},
    )

    runtime_cfg = RuntimeConfig(research=research_cfg)

    # Tools
    sandbox = SandboxRunner()
    tools = Toolbox(
        generate_draft=GenerateDraftTool(),
        compile_draft=CompileDraftTool(),
        verify=ExerciseVerifyTool(sandbox),
        grade=GradeSubmissionTool(store, sandbox),
        hint=MakeHintTool(store),
        trace_log=TraceLogTool(trace_store),
    )

    orchestrator = VAROrchestrator(config=runtime_cfg, store=store, tools=tools, run_store=run_store)

    io = CLIIO()
    specs = available_specs(seed=0)

    initial_state = None
    if args.resume_run:
        if run_store is None:
            raise SystemExit("--resume-run requires --research so snapshots exist")
        initial_state = run_store.load_latest_state(args.resume_run)

    try:
        final_state = orchestrator.run_session(io=io, specs=specs, initial_state=initial_state)
    except SimulatedCrash as e:
        print(f"\n[SimulatedCrash] {e}")
        print("You can resume with: --research --resume-run <run_id>")
        return

    print("\n=== Run complete ===")
    print(f"run_id={final_state.run_id}")
    print(f"final_state={final_state.current_state.value}")
    if run_store is not None:
        print(f"run_dir={run_store.run_dir(final_state.run_id)}")

    if final_state.errors:
        print("Errors:")
        for e in final_state.errors:
            print(f" - {getattr(e, 'message', getattr(e, 'safe_message', str(e)))}")


if __name__ == "__main__":
    main()
