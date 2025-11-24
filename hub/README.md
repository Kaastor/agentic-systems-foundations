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
│       ├── main/              # Main-course steel-thread agent
│       └── cli/               # Typer-based CLI front-end
└── tests/
    └── ...
