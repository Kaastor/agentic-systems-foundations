from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import typer

from agentic.config import settings
from agentic.core.state import AgentStatus
from agentic.main.runner import HumanDecision, load_state, run_steel_thread

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
        if v in {"edit", "e"}:
            return "edit"
        self.fail("Decision must be 'approve', 'reject', or 'edit'.", param, ctx)


@app.command()
def resume(
    run_id: str,
    decision: Decision = typer.Argument(..., help="approve|reject|edit"),
    note: Optional[str] = typer.Option(
        None,
        "--note",
        "-n",
        help="Optional note or edit instruction when approving/editing.",
    ),
) -> None:
    """Resume a paused run that is waiting for human approval."""
    approve = decision in {"approve", "edit"}
    edited = decision == "edit"
    state = run_steel_thread(
        user_message="",
        run_id=run_id,
        human_decision=HumanDecision(approve=approve, note=note or "", edited=edited),
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


@app.command()
def chat() -> None:
    """Tiny chat-like UI around the steel-thread agent (Module 10)."""
    typer.echo("Chatting with the steel-thread agent. Type 'exit' to quit.\n")
    while True:
        msg = typer.prompt("You")
        if msg.strip().lower() in {"exit", "quit"}:
            break
        state = run_steel_thread(user_message=msg)
        typer.echo(f"[run {state.id[:8]}] status={state.status.value}")
        if state.result_summary:
            typer.echo("Agent:")
            typer.echo(state.result_summary)
            typer.echo("")


@app.command()
def feedback(
    run_id: str,
    rating: str = typer.Argument(..., help="e.g. good|bad|meh"),
    note: str = typer.Option("", "--note", "-n", help="Free-form feedback text."),
) -> None:
    """Attach simple feedback to a run for eval purposes (Module 8 / 10)."""
    state = load_state(run_id)
    path = settings.runs_dir / f"{run_id}.feedback.json"
    payload = {
        "run_id": run_id,
        "status": state.status.value,
        "rating": rating,
        "note": note,
        "created_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    typer.echo(f"Feedback saved to {path}")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run a minimal HTTP endpoint exposing the steel-thread agent (Module 9/10)."""
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # type: ignore[override]
            if self.path != "/run":
                self.send_response(404)
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw or "{}")
            except json.JSONDecodeError:
                data = {}
            message = data.get("message") or "Triage my inbox and schedule any obvious meetings."
            state = run_steel_thread(user_message=message)
            body = json.dumps(
                {
                    "run_id": state.id,
                    "status": state.status.value,
                    "result_summary": state.result_summary,
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # type: ignore[override]
            # Keep HTTP server logs quiet; real systems would integrate with logging.
            return

    server = HTTPServer((host, port), Handler)
    typer.echo(f"Serving steel-thread agent on http://{host}:{port}/run")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        typer.echo("Shutting down server.")
        server.server_close()


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
        typer.echo(f"  agentic resume {state.id} edit --note 'tweak the email like this...'")
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
            estimated_tokens = len(state.plan.steps) * 256
            typer.echo(f"\n  Estimated worst-case LLM tokens for this plan: ~{estimated_tokens}")
        typer.echo("")

        typer.echo("Recent tool calls:")
        if not state.tool_calls:
            typer.echo("  <none>")
        else:
            for call in state.tool_calls[-5:]:
                ts = call.started_at.isoformat(timespec="seconds")
                status = "ok" if call.success else f"error ({call.error_type or 'unknown'})"
                typer.echo(f"  [{ts}] {call.tool_name} ({status})")

        if state.metrics:
            typer.echo("")
            typer.echo(f"Metrics: {state.metrics}")

        if getattr(state, "failure_type", None):
            typer.echo(f"Failure type: {state.failure_type.value}")

        snippets = state.scratchpad.get("policy_snippets") or []
        if snippets:
            typer.echo("")
            typer.echo("Policy snippets consulted:")
            for s in snippets:
                trimmed = (s[:77] + "...") if len(s) > 80 else s
                typer.echo(f"  - {trimmed}")

        self_check = state.scratchpad.get("self_check")
        if self_check:
            typer.echo("")
            typer.echo(
                f"Self-check: {self_check.get('classification')} "
                f"(reasons: {', '.join(self_check.get('reasons', []))})"
            )


if __name__ == "__main__":  # pragma: no cover
    app()
