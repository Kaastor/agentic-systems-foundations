# Verified Agent Runtime (VAR) — Research Testbed

> **What this is:** a deterministic, dataset-free **agent systems testbed** for experiments on tool reliability, loop detection/repair, verification gates, durability, observability, and evaluation methodology.

This repo is designed so you can run research like normal software engineering:
- deterministic harness
- fault injection
- reproducible run artifacts
- replayability

---

## Why this is a publishable testbed

The testbed bakes in three “reviewer-proof” properties:

1) **Objective scoring** (verification and grading use sandbox execution + tests)

2) **Reproducibility artifacts**
- run manifest (versions/config)
- tool-call logs (with redaction modes)
- state snapshots (for crash/resume correctness)

3) **Controlled failure**
- deterministic fault injection
- flaky-test detection via repeat execution + fingerprinting

---

## Quick start

### Requirements
- Python **3.10+**
- Linux/macOS recommended (Windows: use WSL)

### Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## Run the deterministic benchmark suite

A smaller, sharper suite that targets failure modes:

```bash
var-golden
```


```bash
var-bench
# or:
python -m var.apps.research.run_bench
```

Include arithmetic task family:

```bash
var-bench --include-math
```

Write JSON results:

```bash
var-bench --include-math --out results.json
```

This benchmark is intentionally dataset-free and CI-friendly.

---

## Run recording (research mode)

For experiments you may publish, record run artifacts:

```bash
var --research --tool-io safe
```

### Tool I/O capture modes
- `hash_only` — store only hashes/metadata (safest)
- `safe` — redacted content (recommended default)
- `full` — full tool inputs/outputs (includes hidden tests / reference solutions; internal use only)

Example:

```bash
var --research --tool-io full
```

Artifacts are stored under **`.var_data/`** (configurable via `--root`).

---

## Crash/resume experiments (durability)

Simulate a crash after N steps:

```bash
var --research --tool-io safe --crash-after-step 3
```

Then resume:

```bash
var --research --resume-run <RUN_ID>
```

This enables “resume correctness” metrics: do we finish in the same terminal outcome after a crash?

---

## Replay (time-travel debugging)

Replay is exposed programmatically (used in tests) and is meant for:
- debugging hard-to-reproduce failures
- ablations: same tool I/O, different orchestration logic

Conceptually:
1) load tool call records from a recorded run
2) create `ReplayToolExecutor(records=...)`
3) run the orchestrator with the replay executor instead of real tools

Key code:
- `var/research/replay.py`
- `tests/test_research_resume_and_replay.py`

---

## Fault injection (controlled failures)

Fault injection is deterministic and composable: wrap any tool with injected failures.

Key code:
- `var/research/fault_injection.py`
- `tests/test_flaky_verification_and_fault_injection.py`

Use cases:
- retry/backoff policy comparisons
- loop detection/repair benchmarking under tool errors
- verifying “no infinite loops” under adversarial failure schedules

---

## What to measure (common metrics)

Suggested baseline metrics (extend as needed):
- Exercise validity rate: verified PASS within budget
- Mean regenerations per successful verified artifact
- Loop rate: runs hitting max retries
- Determinism: identical submission → identical grade (must be 100%)
- Hint policy compliance: solution leakage rate (should be 0 by default)
- Cost proxies: tool calls, sandbox runtime, steps per successful run
- Resume correctness: crash at step N then resume → same terminal outcome

---

## Extending the benchmark

### Add new task families
This repo already demonstrates two families:
- Coding exercises (template-based)
- Arithmetic exercises (`var/tools/math_generation.py`)

To add a new family:
- add a generator that returns `ExerciseDraft`
- route it via `var/tools/composite_generation.py`
- add scenarios in `var/eval/*_scenarios.py`
- version your suite (important for publishability)

---

## Safety & ethics

- The sandbox is lightweight (subprocess + best-effort resource limits), not a hardened security boundary.
- Runs may store sensitive content depending on `tool-io` capture mode.
- If you include real students in experiments, plan for consent/ethics review as appropriate.
