from __future__ import annotations

"""Course CLI entrypoint.

This is a thin wrapper that wires the kernel components together.
Students can modify or replace individual parts (tools, policies, configs) without
editing the kernel orchestration logic.
"""

import argparse
from pathlib import Path

from ...agent.orchestrator import Toolbox, VAROrchestrator
from ...config import RuntimeConfig
from ...io import CLISessionIO
from ...store.exercise_store import ExerciseStore
from ...store.trace_store import FileTraceStore
from ...tools.exercise_generation import CompileDraftTool, GenerateDraftTool, available_specs
from ...tools.grading import GradeSubmissionTool
from ...tools.hinting import MakeHintTool
from ...tools.observability import TraceLogTool
from ...tools.sandbox import SandboxRunner
from ...tools.verification import ExerciseVerifyTool


def build_course_orchestrator(*, root: Path) -> VAROrchestrator:
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
    return VAROrchestrator(config=RuntimeConfig(), store=store, tools=tools)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="VAR course CLI")
    parser.add_argument("--root", type=Path, default=Path(".var_course"), help="data directory")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    args.root.mkdir(parents=True, exist_ok=True)

    orchestrator = build_course_orchestrator(root=args.root)
    specs = available_specs(seed=args.seed)
    io = CLISessionIO()
    final_state = orchestrator.run_session(io=io, specs=specs)

    # Minimal summary
    io.show_message(f"\nRun finished: {final_state.current_state}")


if __name__ == "__main__":
    main()
