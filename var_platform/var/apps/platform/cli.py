from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ...agent.orchestrator import Toolbox, SimulatedCrash, VAROrchestrator
from ...budgets.manager import BudgetManager
from ...config import BudgetConfig, ResearchConfig, RuntimeConfig
from ...research.types import ToolIOCapture
from ...store.exercise_store import ExerciseStore
from ...store.run_store import FileRunStore
from ...store.trace_store import FileTraceStore
from ...memory.store import FileMemoryStore
from ...tools.exercise_generation import CompileDraftTool, GenerateDraftTool, available_specs
from ...tools.grading import GradeSubmissionTool
from ...tools.hinting import MakeHintTool
from ...tools.observability import TraceLogTool
from ...tools.presentation_gate import GateExerciseViewTool, GateGradeReportTool, GateHintTool
from ...tools.memory import MemoryAppendTool, MemoryQueryTool
from ...tools.sandbox import SandboxRunner
from ...tools.verification import ExerciseVerifyTool
from ..common.cli_io import CLIIO
from ...agent.plan_execute.orchestrator import PlanExecuteOrchestrator, PlanToolbox


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verified Agent Runtime (VAR) interactive CLI")
    p.add_argument("--root", type=str, default=".var_data", help="Workspace directory")
    p.add_argument(
        "--orchestrator",
        choices=["fsm", "plan-build"],
        default="fsm",
        help="Orchestration style (fsm = full tutor loop, plan-build = build+verify+present only)",
    )
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
    p.add_argument("--budget-tool-calls", type=int, default=None, help="Max tool call attempts (optional)")
    p.add_argument("--budget-tool-latency-ms", type=int, default=None, help="Max total tool latency in ms (optional)")
    p.add_argument("--budget-model-tokens", type=int, default=None, help="Max total model tokens (optional)")
    p.add_argument("--budget-sandbox-ms", type=int, default=None, help="Max total sandbox runtime in ms (optional)")
    p.add_argument(
        "--orchestrator",
        choices=["fsm", "plan-build"],
        default="fsm",
        help="Orchestration strategy: FSM (default) or a simple Plan/Execute build pipeline",
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

    budgets_cfg = BudgetConfig.from_simple(
        enabled=any(
            v is not None
            for v in [args.budget_tool_calls, args.budget_tool_latency_ms, args.budget_model_tokens, args.budget_sandbox_ms]
        ),
        max_tool_calls=args.budget_tool_calls,
        max_tool_latency_ms=args.budget_tool_latency_ms,
        max_model_total_tokens=args.budget_model_tokens,
        max_sandbox_runtime_ms=args.budget_sandbox_ms,
    )

    runtime_cfg = RuntimeConfig(research=research_cfg, budgets=budgets_cfg)

    budget_manager = BudgetManager(limits=budgets_cfg.limits) if budgets_cfg.enabled else None

    sandbox = SandboxRunner(budgets=budget_manager)
    memory_store = FileMemoryStore(root / "memory")
    tools = Toolbox(
        generate_draft=GenerateDraftTool(),
        compile_draft=CompileDraftTool(),
        verify=ExerciseVerifyTool(sandbox),
        grade=GradeSubmissionTool(store, sandbox),
        hint=MakeHintTool(store),
        gate_exercise_view=GateExerciseViewTool(),
        gate_grade_report=GateGradeReportTool(),
        gate_hint=GateHintTool(),
        trace_log=TraceLogTool(trace_store),
        memory_append=MemoryAppendTool(memory_store),
        memory_query=MemoryQueryTool(memory_store),
    )

    if args.orchestrator == "plan-build":
        # A small alternative orchestration style: build a verified exercise and exit.
        plan_tools = PlanToolbox(
            generate_draft=tools.generate_draft,
            compile_draft=tools.compile_draft,
            verify=tools.verify,
            gate_exercise_view=tools.gate_exercise_view,
            trace_log=tools.trace_log,
        )
        orchestrator = PlanExecuteOrchestrator(config=runtime_cfg, store=store, tools=plan_tools)
    else:
        orchestrator = VAROrchestrator(
            config=runtime_cfg,
            store=store,
            tools=tools,
            run_store=run_store,
            budget_manager=budget_manager,
        )

    io = CLIIO()
    specs = available_specs(seed=0)

    initial_state = None
    if args.resume_run:
        if args.orchestrator != "fsm":
            raise SystemExit("--resume-run is only supported for --orchestrator fsm")
        if run_store is None:
            raise SystemExit("--resume-run requires --research so snapshots exist")
        initial_state = run_store.load_latest_state(args.resume_run)

    try:
        if args.orchestrator == "fsm":
            final_state = orchestrator.run_session(io=io, specs=specs, initial_state=initial_state)  # type: ignore[attr-defined]
        else:
            final_state = orchestrator.run_session(io=io, specs=specs)  # type: ignore[arg-type]
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
