# Verified Agent Runtime (VAR)

This repo is a **research-grade steel thread** built around one core invariant:

> **No exercise is shown to the learner unless it has been verified in a sandbox.**

It is deliberately shaped as a *platform* that can serve three distinct goals without forking the code:

1) **Research testbed** (deterministic runs, replay, fault injection, metrics)
2) **University course codebase slice** (clean seams, typed tools, state machines)
3) **Homeschooling tool** (kid-friendly UX + lightweight mastery tracking)

The kernel is still the same: a verified agent with typed tool boundaries and a serializable explicit state machine.

---

## Quick start

### 1) University course CLI (baseline)

```bash
python -m var.apps.course.cli
```

### 2) Homeschool CLI (arithmetic practice)

```bash
python -m var.apps.home.cli
```

Optional: mix in coding exercises too:

```bash
python -m var.apps.home.cli --include-coding
```

### 3) Research harness (deterministic benchmark)

```bash
python -m var.apps.research.run_bench
python -m var.apps.research.run_bench --include-math
```

### 4) Unit tests

```bash
python -m unittest discover -s tests -q
```

---

## What changed from v0.1

- Added **product layers** under `var/apps/`:
  - `course` (university labs)
  - `home` (homeschool UX + mastery stub)
  - `research` (bench runner)

- Added a second *topic domain* (still compiled into Python for determinism):
  - `var.tools.math_generation` + `available_math_specs()`

- Added a small but useful “platform seam”:
  - `var.tools.composite_generation.CompositeGenerateDraftTool` routes specs to the right generator.

This keeps everything measurable and replayable while allowing multiple “products” to share the same kernel.

---

## Research mode (publishability engine)

Research mode turns var into a thesis/paper platform:

- **Run manifests**: config snapshot + tool versions + environment info.
- **Tool I/O recording**: optional capture of tool inputs/outputs (with redaction).
- **State snapshots**: time-travel debugging and crash/resume experiments.
- **Replay**: rerun the agent using recorded tool outputs (no sandbox required).
- **Fault injection**: deterministic tool failures for robustness benchmarking.

Enable research recording from the classic CLI (still available):

```bash
python -m var.cli --research --tool-io safe
```

Record full tool I/O (needed for replay):

```bash
python -m var.cli --research --tool-io full
```

Simulate a crash and resume (tests crash recovery):

```bash
python -m var.cli --research --crash-after-step 3
python -m var.cli --research --resume-run <run_id>
```

Recorded artifacts live under:

- `.var_data/runs/run_<run_id>/` (manifest, tool_calls, state_snapshots)
- `.var_data/artifacts/` (exercise artifacts)
- `.var_data/traces/` (trace events)

---

## Architecture (high-level)

### Kernel

- `var/types.py` — Pydantic schemas (artifact, reports, errors, trace events, agent state)
- `var/tools/` — typed tool layer with structured failures
- `var/agent/` — explicit state machine orchestrator
- `var/store/` — filesystem stores (artifacts, traces, runs)
- `var/research/` — recording, replay, fault injection, metrics
- `var/eval/` — dataset-free deterministic evaluation harness + synthetic learners

### Product layers

- `var/apps/course/` — course entrypoints (student-friendly)
- `var/apps/home/` — homeschool UX + mastery stub
- `var/apps/research/` — research bench entrypoints

---

## Safety / sandbox note

This is a **teaching sandbox**, not a hardened production container.
We enforce:

- time limits (subprocess timeout + CPU limit)
- memory limits (best-effort via `resource`)
- forbidden imports (AST scan)
- temp working directory per run
- output truncation

For real-world untrusted execution, swap `SandboxRunner` with a container/VM backend.
