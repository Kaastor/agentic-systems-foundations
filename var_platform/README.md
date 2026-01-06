# Verified Agent Runtime (VAR)

VAR is a **production-shaped reference repository** for engineering agentic AI systems as reliable software.

This repo is intentionally small enough to learn end-to-end, while still teaching the disciplines that matter:
**typed interfaces, explicit orchestration, verification gates, observability, budgets, and deterministic evaluation**.

## Start here

- **Course Edition (teaching-first):** see `README_course.md`
- **Platform/Runtime overview:** see `README_platform.md`
- **Research mode (replay, fault injection, redaction):** see `README_research.md`

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Interactive "platform" CLI
var --root .var_data

# Course CLI (minimal surface area)
var-course --root .var_course

# Golden deterministic eval suite
var-golden
```

## The steel beam

> **Verified-before-present:** nothing is shown to the learner unless the artifact passes verification.

That invariant is enforced in code by the orchestrator and the universal `PresentationGate`.
