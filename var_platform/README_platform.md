# Verified Agent Runtime (VAR) — Full Platform

> **What this is:** a modular agentic-systems platform built around a single, strict kernel:
>
> **Verified-before-present** learning interactions with deterministic grading, traceability, and replayable runs.

This repo supports three “products” without forking architecture:
- **Research testbed** (reproducibility, replay, fault injection, benchmarks)
- **University course edition** (minimal, teachable core)
- **Homeschool prototype** (profiles + mastery-lite on the same verified loop)

> Note: package/module names may still reference legacy `vpl` naming. “VAR” is the preferred project name going forward.

---

## Repository layout

```
vpl/
  agent/          # FSM orchestrator + tool executor
  tools/          # typed tool boundaries: generate/verify/grade/hint/trace/sandbox
  store/          # exercise store, trace store, run store (research artifacts)
  eval/           # deterministic benchmark harness + scenarios
  research/       # replay, redaction, fault injection, metrics helpers
  apps/
    course/       # student-facing CLI wiring (minimal)
    research/     # benchmark runner entrypoint
    home/         # homeschool CLI + profiles (prototype)
tests/            # unit tests for invariants, determinism, replay, fault injection, etc.
```

---

## Quick start

### Requirements
- Python **3.10+**
- Linux/macOS recommended (Windows: use WSL for consistent sandbox behavior)

### Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run the full platform CLI (interactive)
```bash
vpl
# or:
python -m vpl.cli
```

Default workspace directory: **`.vpl_data/`** (override via `--root`).

---

## The three entrypoints

### 1) Course Edition (minimal surface)
```bash
vpl-course
# or:
python -m vpl.apps.course.cli
```

Writes to **`.vpl_course/`** by default.

### 2) Research bench runner (deterministic)
```bash
vpl-bench
# optional:
vpl-bench --include-math --out results.json
```

### 3) Homeschool prototype (profiles + mastery-lite)
```bash
vpl-home
# optionally mix in coding tasks:
vpl-home --include-coding
```

Writes to **`.vpl_home/`** by default.

---

## Kernel concepts (the “steel thread”)

The system enforces a hard invariant:

> **No exercise is shown unless it has been verified PASS in a sandbox.**

This creates reliable behavior and measurable failure modes:
- broken tests
- flaky tests
- tool failures / timeouts
- loop detection and repair
- policy violations (forbidden imports, hint leakage)

---

## Research mode (recording runs)

The full CLI supports run recording:

```bash
vpl --research --tool-io safe
```

Tool I/O capture:
- `hash_only` (safest)
- `safe` (recommended)
- `full` (internal only; includes hidden tests / reference solutions)

Crash/resume:
```bash
vpl --research --crash-after-step 3
vpl --research --resume-run <RUN_ID>
```

---

## Making a “Course Edition” distribution (recommended)

For teaching, you may want to ship a trimmed repo without research/homeschool extras.

One simple approach is syncing into a separate directory while excluding research-only modules:

```bash
rsync -a --delete ./var_platform/ ./var_course/   --exclude 'vpl/research/'   --exclude 'vpl/apps/research/'   --exclude 'vpl/apps/home/'   --exclude 'tests/test_research_*'   --exclude 'tests/test_flaky_verification_and_fault_injection.py'
```

**Tip:** run with `--dry-run` first to see what would be copied/deleted.

In practice, many teams maintain:
- `main` (full platform)
- `course` branch/tag (trimmed distribution for a semester)

---

## Safety note

The sandbox is designed for teaching and deterministic evaluation:
- subprocess isolation + timeouts
- restricted interpreter flags (`-I -S`)
- best-effort resource limits on POSIX systems

It is **not** a hardened container/VM sandbox for untrusted adversarial code.

---

## Development & quality bar

Run tests:
```bash
python -m unittest discover -s tests -q
```

Quality expectations:
- preserve determinism
- preserve the verified-before-present invariant
- add/extend unit tests for any behavioral change
- treat tool boundaries as stable APIs (schemas + error taxonomy)

