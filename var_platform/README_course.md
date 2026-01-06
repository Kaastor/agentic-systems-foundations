# Verified Agent Runtime (VAR) — Course Edition

> **What this is:** a small, production-shaped agent “steel thread” used to teach **agentic systems engineering** as software engineering: typed schemas, typed tools, explicit state machines, verification gates, deterministic grading, traceability, and tests.

This **Course Edition** intentionally focuses on the **core kernel**. It avoids research-only features (replay/fault injection/redaction modes) until you decide to introduce them later in the semester or in an honors/thesis track.

---

## The core idea (the steel beam)

Two big teaching upgrades:
- **Outcomes are first-class** (`OutcomeKind`) so the FSM branches on *domain results*, not just “tool ran”.
- **PresentationGate is universal**: exercise, grade, and hint are all gated before being shown.


**Invariant (must never break):** an exercise is only shown to the learner if it has been **verified PASS** in a sandbox.

The loop:

1. Generate an exercise draft
2. Compile to a runnable artifact (prompt + starter + tests)
3. Verify in sandbox (reference solution passes tests, checks run, flake detection)
4. Present to learner
5. Grade submission (hidden tests remain hidden)
6. Hint-first feedback (no solution by default)
7. Log traces and metrics

---

## Quick start

### Requirements
- Python **3.10+**
- Works best on Linux/macOS (Windows: use WSL for consistent sandbox behavior)
- Minimal dependency set (Pydantic v2)

### Install (recommended)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run the course CLI
```bash
var-course
# or:
python -m var.apps.course.cli
```

Artifacts for the course run are written under **`.var_course/`** by default.

### Run tests
```bash
python -m unittest discover -s tests -q
```

---

## What students should focus on

This codebase is designed so students can “own a slice” without rewriting everything.

### Core skills you can teach directly from this repo
- **Structured, validated data models** (`pydantic`)
- **Typed tool boundaries** with explicit error taxonomy
- **A finite state machine (FSM)** orchestrator (inspectable and testable)
- **Verification as a gate** (hard invariant)
- **Deterministic evaluation** (grading is objective, not subjective)
- **Trace-based debugging** (agent runs emit structured events)
- **Unit tests** for invariants and determinism

---

## Recommended reading order (for teaching)

1. **Data models (schemas)**
   - `var/types.py`

2. **Tool protocol (system boundary)**
   - `var/tools/base.py`

3. **Sandbox execution**
   - `var/tools/sandbox.py`

4. **Exercise generation (templates)**
   - `var/tools/exercise_generation.py`

5. **Verification gate**
   - `var/tools/verification.py`

6. **Grading (hidden tests + sanitization)**
   - `var/tools/grading.py`

7. **Orchestration (explicit FSM + budgets + loop controls)**
   - `var/agent/orchestrator.py`
   - `var/agent/tool_executor.py`

8. **Observability**
   - `var/tools/observability.py`
   - `var/store/trace_store.py`

---

## Where to make changes (safe extension seams)

### Add a new exercise template
- Add a template in `var/tools/exercise_generation.py`
- Ensure it compiles to `ExerciseArtifact` with:
  - starter code
  - reference solution
  - hidden tests

Then verify: reference solution must pass hidden tests under the sandbox.

### Add new verification checks
- Add checks in `var/tools/verification.py` (e.g., stronger signature checks, style constraints, import restrictions)

### Improve loop/repair logic
- Modify `RepairOrRegenerate` logic in `var/agent/orchestrator.py`
- Keep it **bounded** (no infinite regen loops)

### Improve hinting (without leaking)
- Extend the hint ladder in `var/tools/hinting.py`
- Enforce “no solution reveal” unless policy explicitly allows it

---

## Safety note (important for labs)

The sandbox is intentionally lightweight for teaching:
- subprocess isolation + timeouts
- restricted interpreter flags (`-I -S`)
- best-effort resource limits (POSIX systems)

It is **not** a hardened container/VM sandbox. Do not treat it as safe against fully adversarial code.

---

## Suggested lab assignments (easy to grade objectively)

- Add a new exercise family (e.g., list processing, recursion)
- Implement a stronger import/AST-based policy check
- Improve trace output and build a minimal “trace viewer”
- Add new synthetic learner scenarios to the eval harness (if you include it)
- Compare two loop/repair strategies with metrics

---

## Definition of Done (for student work)

- The verification invariant never breaks
- Unit tests pass
- Grading is deterministic in outcome (same submission → same pass/fail, score, and test results)
- Hidden tests and reference solutions never leak to the learner
- Changes are modular and come with tests
