# Agentic Systems Foundations — Steel Thread (Groq-backed)

This repo contains a **minimal but production-shaped steel-thread** implementation
for the *Agentic Systems Foundations* main course.

The steel thread is an agent that can:

- Triage a tiny demo inbox.
- Propose a meeting time using a calendar tool.
- Consult RAG over company-style policy docs.
- Draft and (with human approval) send a reply email + create a calendar event.
- Run as an explicit state machine with persistent `AgentState` and traces.
- Use **Groq** as a real LLM backend (or a local stub for offline work).

The code is intentionally small and explicit:

- Plain Python + Typer CLI.
- Pydantic models for typed schemas.
- `requests` for a tiny Groq integration — no SDKs, no frameworks.
- No real email/calendar APIs; everything is local JSON files.

## Layout

```text
.
├── pyproject.toml       # Poetry config + `agentic` CLI entrypoint
├── README.md
├── src/
│   └── agentic/
│       ├── __init__.py
│       ├── config.py          # Paths, knobs, feature flags (including Groq)
│       ├── core/              # Reusable building blocks for all courses
│       ├── llm/               # LLM abstraction + stub + Groq backend
│       ├── steel_thread/      # Main-course steel-thread agent
│       └── cli/               # Typer-based CLI front-end
└── tests/
    └── ...
```

The idea is that **Specializations** can add their own packages next to
`steel_thread` (e.g. `specialization_rag`, `specialization_guardrails`) while
reusing `agentic.core` and `agentic.llm` without constant code-copying.

## Quickstart (stub LLM, no Groq)

```bash
# In this repo
poetry install

# Run the demo steel-thread agent end-to-end
poetry run agentic demo

# If the run pauses for human approval, you'll see a run id, e.g. `run-...`
# Approve or reject the pending action:
poetry run agentic runs
poetry run agentic show RUN_ID
poetry run agentic resume RUN_ID approve   # or 'reject'
```

All runs are stored under `./runs/` as JSON state and JSONL traces.

## Using a real LLM via Groq

By default the agent uses a tiny deterministic `RuleBasedLLM` so the repo
runs anywhere with no network calls. To turn it into a *real* agentic system
backed by Groq, set a couple of environment variables:

```bash
export GROQ_API_KEY=sk_your_key_here
export AGENTIC_LLM_BACKEND=groq
# Optional overrides (these have sensible defaults):
# export GROQ_MODEL="llama-3.1-70b-versatile"
# export GROQ_BASE_URL="https://api.groq.com/openai/v1"
```

Then run the agent as usual:

```bash
poetry install
poetry run agentic demo
```

Under the hood, `GroqLLM` calls the OpenAI-compatible

```text
POST https://api.groq.com/openai/v1/chat/completions
```

endpoint, asks the model to emit a small JSON plan, and parses that into the
`Plan` / `PlanStep` structures used by the rest of the system. If something
goes wrong (network error, bad JSON), it gracefully falls back to the local
`RuleBasedLLM` so you can still demonstrate the rest of the stack.

## Where the main-course modules show up

Rough mapping:

- **Module 1 – Structured I/O**  
  Pydantic models in `agentic.core.state`, `agentic.core.tools`, and
  `agentic.steel_thread.tools_*`.

- **Module 2 – Tooling & RAG**  
  Tool registry in `agentic.core.tools`, demo tools in
  `agentic.steel_thread.tools_email/calendar/rag`.

- **Module 3 – Agent as State Machine**  
  `agentic.core.graph` + `agentic.steel_thread.nodes`.

- **Module 4 – Planning**  
  `LLM.make_plan` implemented by `GroqLLM` (real inference) or
  `RuleBasedLLM` (offline) + `PlanningNode`.

- **Module 5 – Memory & Context**  
  `Memory` model on `AgentState` and light-touch usage in nodes.

- **Module 6 – Guardrails**  
  `agentic.steel_thread.policy.PolicyEngine` enforcing human approval for
  dangerous tools.

- **Module 7 – Long-Running**  
  `AgentState` persistence in `agentic.steel_thread.runner` +
  `AgentStatus.AWAITING_USER` + `resume` CLI.

- **Module 8 – Evaluation & Observability**  
  `Tracer` in `agentic.core.logging`, `TraceStep` in `AgentState`, and the
  `show` / `runs` CLI.

- **Modules 9–10 – Deployment & UX**  
  `run_steel_thread()` API in `agentic.steel_thread.runner` and the simple
  Typer CLI.

The code is written to be **read** as much as **run** — it deliberately leaves
space for you to plug in real email/calendar systems, richer RAG, beefier
guardrails, and proper evaluation machinery.
