from __future__ import annotations

from typing import Optional

import typer

from agentic.config import settings
from agentic.core.state import AgentStatus
from agentic.steel_thread.runner import HumanDecision, load_state, run_steel_thread

app = typer.Typer(help="Agentic Systems Foundations — steel-thread CLI")


@app.command()
def demo(
    message: str = typer.Option(
        "Triage my inbox and schedule any obvious meetings using company policies.",
        "--message",
        "-m",
        help="User request to give to the steel-thread agent.",
    )
) -> None:
    """Run the steel-thread agent end-to-end on the demo inbox."""
    state = run_steel_thread(user_message=message)
    _print_run_summary(state)


class Decision(str, typer.ParamType):
    name = "decision"

    def convert(self, value, param, ctx):  # type: ignore[override]
        v = str(value).lower()
        if v in {"approve", "a"}:
            return "approve"
        if v in {"reject", "r"}:
            return "reject"
        self.fail("Decision must be 'approve' or 'reject'.", param, ctx)


@app.command()
def resume(run_id: str, decision: Decision = typer.Argument(..., help="approve|reject")) -> None:
    """Resume a paused run that is waiting for human approval."""
    approve = decision == "approve"
    state = run_steel_thread(
        user_message="",
        run_id=run_id,
        human_decision=HumanDecision(approve=approve),
    )
    _print_run_summary(state)


@app.command()
def runs() -> None:
    """List known runs and their status."""
    if not settings.runs_dir.exists():
        typer.echo("No runs directory yet.")
        raise typer.Exit(code=0)

    rows = []
    for path in sorted(settings.runs_dir.glob("run-*.json")):
        try:
            state = load_state(path.stem)
        except Exception:
            continue
        rows.append(
            (
                state.id,
                state.status.value,
                state.created_at.isoformat(timespec="seconds"),
                state.updated_at.isoformat(timespec="seconds"),
            )
        )

    if not rows:
        typer.echo("No runs found.")
        raise typer.Exit(code=0)

    typer.echo(f"{'RUN ID':36}  {'STATUS':14}  {'CREATED'}")
    for rid, status, created, updated in rows:
        typer.echo(f"{rid:36}  {status:14}  {created}")


@app.command()
def show(run_id: str) -> None:
    """Inspect a single run in slightly more detail."""
    state = load_state(run_id)
    _print_run_summary(state, verbose=True)


def _print_run_summary(state, verbose: bool = False) -> None:
    typer.echo("")
    typer.echo(f"Run id:       {state.id}")
    typer.echo(f"Status:       {state.status.value}")
    typer.echo(f"Created at:   {state.created_at.isoformat(timespec='seconds')}")
    typer.echo(f"Updated at:   {state.updated_at.isoformat(timespec='seconds')}")
    typer.echo(f"User message: {state.user_message!r}")
    typer.echo("")

    if state.result_summary:
        typer.echo("Result summary:")
        typer.echo(state.result_summary)
        typer.echo("")

    if state.status == AgentStatus.AWAITING_USER:
        pending = state.scratchpad.get("pending_tool_call") or {}
        tool_name = pending.get("tool_name", "<unknown>")
        reason = pending.get("reason", "No reason stored.")
        typer.echo("This run is waiting for human approval:")
        typer.echo(f"  Tool:   {tool_name}")
        typer.echo(f"  Reason: {reason}")
        typer.echo("")
        typer.echo("To continue, run:")
        typer.echo(f"  agentic resume {state.id} approve")
        typer.echo(f"  agentic resume {state.id} reject")
        typer.echo("")

    if verbose:
        typer.echo("Plan:")
        if not state.plan:
            typer.echo("  <no plan>")
        else:
            for idx, step in enumerate(state.plan.steps):
                marker = "->" if idx == state.plan.current_index else "  "
                typer.echo(
                    f"  {marker} [{step.status.value:8}] {step.id}: {step.description} "
                    f"(tool={step.tool_name})"
                )
        typer.echo("")

        typer.echo("Recent tool calls:")
        if not state.tool_calls:
            typer.echo("  <none>")
        else:
            for call in state.tool_calls[-5:]:
                ts = call.started_at.isoformat(timespec="seconds")
                status = "ok" if call.success else "error"
                typer.echo(f"  [{ts}] {call.tool_name} ({status})")
        typer.echo("")


if __name__ == "__main__":  # pragma: no cover
    app()
