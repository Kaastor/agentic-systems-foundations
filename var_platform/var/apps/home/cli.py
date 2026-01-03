from __future__ import annotations

"""Homeschool CLI entrypoint.

This is a *product layer* on top of the same kernel used for the research testbed.

Key idea:
- The kernel still runs "generate → verify → present → grade → hint".
- The homeschool UI just changes *how submissions are collected*.
  Instead of code, it asks for a number and wraps it into code.
"""

import argparse
from pathlib import Path

from ...agent.orchestrator import Toolbox, VAROrchestrator
from ...config import RuntimeConfig
from ...store.exercise_store import ExerciseStore
from ...store.trace_store import FileTraceStore
from ...tools.exercise_generation import CompileDraftTool, GenerateDraftTool, available_specs
from ...tools.grading import GradeSubmissionTool
from ...tools.hinting import MakeHintTool
from ...tools.observability import TraceLogTool
from ...tools.sandbox import SandboxRunner
from ...tools.verification import ExerciseVerifyTool
from ...tools.math_generation import MathGenerateDraftTool, available_math_specs
from ...tools.composite_generation import CompositeGenerateDraftTool

from .io import HomeschoolCLIIO
from .profile import HomeschoolProfile, LocalProfileStore


def build_homeschool_orchestrator(*, root: Path, include_coding: bool, use_math_generator: bool = True) -> VAROrchestrator:
    store = ExerciseStore(root)
    trace_store = FileTraceStore(root)
    sandbox = SandboxRunner()

    if use_math_generator and include_coding:
        gen = CompositeGenerateDraftTool([MathGenerateDraftTool(), GenerateDraftTool()])
    elif use_math_generator:
        gen = MathGenerateDraftTool()
    else:
        gen = GenerateDraftTool()

    tools = Toolbox(
        generate_draft=gen,
        compile_draft=CompileDraftTool(),
        verify=ExerciseVerifyTool(sandbox),
        grade=GradeSubmissionTool(store, sandbox),
        hint=MakeHintTool(store),
        trace_log=TraceLogTool(trace_store),
    )
    return VAROrchestrator(config=RuntimeConfig(), store=store, tools=tools)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="VAR homeschool CLI")
    parser.add_argument("--root", type=Path, default=Path(".var_home"), help="data directory")
    parser.add_argument("--profile", type=str, default="", help="existing profile_id (optional)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--include-coding", action="store_true", help="also include programming exercises")
    args = parser.parse_args(argv)

    args.root.mkdir(parents=True, exist_ok=True)

    profile_store = LocalProfileStore(args.root / "profiles")
    if args.profile:
        profile = profile_store.load(args.profile)
    else:
        name = input("Learner name: ").strip() or "Learner"
        profile = HomeschoolProfile(name=name)
        profile_store.save(profile)
        print(f"Created profile_id={profile.profile_id}")

    orchestrator = build_homeschool_orchestrator(root=args.root, include_coding=args.include_coding)

    # Content pack
    specs = available_math_specs(seed=args.seed)
    if args.include_coding:
        specs = specs + available_specs(seed=args.seed)

    io = HomeschoolCLIIO(profile=profile, profile_store=profile_store)
    final_state = orchestrator.run_session(io=io, specs=specs)
    io.show_message(f"\nRun finished: {final_state.current_state}")


if __name__ == "__main__":
    main()
