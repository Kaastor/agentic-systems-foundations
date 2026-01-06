# Verified Agent Runtime (VAR): Vision & Principles

This repository is a reference implementation for **engineering agentic AI systems** as reliable software.

It is intentionally **production-shaped** (typed interfaces, explicit orchestration, verification gates, observability, evaluation) while remaining **small enough to learn end-to-end**.

The same core supports three long-term uses:

- **Research testbed** (reproducible experiments and benchmarks)
- **University course substrate** (a teachable kernel with progressive disclosure)
- **Homeschool tool** (long-run product layer built on verified learning loops)

> **Core belief:** agentic AI should be built like systems engineering, not prompt improvisation.

---

## Vision

Build an agent runtime where:

1. **Actions and content are verified before use**
2. **State is explicit and serializable**
3. **Tools are typed, testable boundaries**
4. **Failures are expected and measurable**
5. **Experiments are reproducible by default**

The goal is not to build a “chatbot demo.”  
The goal is to build a **reference repository** that teaches state-of-the-art agent engineering by forcing the real disciplines: contracts, budgets, safety, traces, and tests.

---

## The Steel Beam (Non-negotiable invariant)

> **Verified-before-present:** nothing is shown to the learner unless the artifact has passed verification.

Verification is performed by deterministic tools (e.g., sandbox execution), not by model self-confidence.

This invariant creates reliable behavior and meaningful failure modes:
- broken tests / unsatisfied specs
- flaky tests
- timeouts and resource limits
- tool failures
- loop thrashing
- policy violations (e.g., forbidden imports, leakage)

---

## Scope

### In scope
- A minimal but realistic **agent workflow** (generate → verify → present → grade → hint → log)
- Typed schemas for core artifacts and trace events
- Explicit orchestration via FSM/graph with budgets and loop controls
- Deterministic grading and evaluation harnesses
- Research-mode reproducibility: manifests, snapshots, replay, fault injection
- Multiple thin “apps” over one kernel (course / research / home)

### Out of scope (for the kernel)
- UI frameworks beyond minimal CLIs
- Domain-specific personalization strategies (these belong in product layers)
- Private datasets as a dependency
- “Magic” abstractions that hide state, tool boundaries, or failure modes

---

## Design principles

### 1) Verification over vibes
If correctness matters, verify with tools:
- execute code in a sandbox
- run tests/checkers
- re-run for flake detection when needed

### 2) Typed everything at boundaries
All system boundaries are explicit and typed:
- schemas for artifacts (specs, exercises, reports)
- schemas for tool inputs/outputs
- structured error taxonomy (retryable vs permanent)

### 3) Explicit orchestration
The agent is an explicit FSM/graph:
- deterministic dispatcher
- named states/nodes
- transition rules you can unit-test
- invariants enforced in code (not in prompts)

### 4) Budgets and bounded loops
No infinite “regen until it works” behavior.
The runtime enforces:
- max steps
- max retries per tool call (based on error retryability)
- max regenerations per spec
- forced-change strategies when repeating failures

### 5) Observability is a first-class feature
Every run emits structured events:
- state transitions
- tool calls and outcomes
- verification status
- grading status
- hint issuance
- terminal outcomes

The system should be debuggable like production software.

### 6) Deterministic evaluation is mandatory
A testbed is only useful if it can regress:
- scripted scenarios (synthetic learners)
- deterministic seeds
- stable outputs (same inputs → same grade)

### 7) Modular growth through stable seams
New capabilities should be introduced by adding:
- a new tool implementation
- a new verifier/grader plugin
- a new app layer
- new eval scenarios/metrics

Avoid rewriting the orchestrator for every feature.

---

## Architecture at a glance

### Kernel (stable engine)
The kernel contains:
- **Types & schemas** for all artifacts and trace events
- **Tool protocol**: `ToolResult` + `ToolError`
- **Sandbox runner** interface (backend-swappable)
- **Verification + grading** tools
- **Orchestrator** (FSM/graph) enforcing invariants and budgets
- **Trace/run storage**, replay hooks, evaluation harness primitives

The kernel is optimized for:
- clarity
- determinism
- testability
- extension seams

### Product layers (thin wiring)
Apps configure and present the kernel:

- **Course Edition**: minimal surface area, teaching-first defaults  
- **Research runner**: recording, replay, fault injection, benchmarks  
- **Homeschool app**: profiles, mastery-lite, kid-friendly interaction  

Product layers should not mutate kernel invariants.

---

## Research mode: what “reproducible by default” means

Research is treated as software engineering, not storytelling.

A publishable run should have:
- deterministic seeds and generator versions
- tool versions/config captured in a **run manifest**
- tool I/O capture with **redaction modes**
- state snapshots for crash/resume experiments
- ability to **replay** tool outputs deterministically
- fault injection to stress recovery logic under controlled failures

Research goals supported well:
- robustness benchmarking (retries, loop policies, repair strategies)
- durability and resume correctness
- verification and flake handling
- evaluation methodology and trace-based debugging

---

## Course Edition: teaching strategy (progressive disclosure)

The course edition is intentionally smaller than the full platform.

**Teaching principle:** students learn core concepts first; advanced infrastructure is introduced later.

Suggested progression:
1. typed schemas and validation
2. tool protocol and structured errors
3. sandbox execution
4. verification gate (the invariant)
5. FSM orchestration
6. loop detection and repair
7. trace debugging
8. evaluation harness
9. (advanced track) replay, fault injection, durability

This keeps cognitive load manageable while remaining “real enough” to teach professional habits.

---

## Homeschool mode: long-run product strategy

The homeschool goal is practical: deliver verified practice and feedback safely.

Early domains should be verifiable and deterministic (coding, arithmetic).  
Over time, expand via **verifier plugins** rather than weakening verification.

Guiding rule:
- do not show tasks that cannot be verified fairly
- do not grade submissions you cannot check deterministically
- where deterministic checking is impossible, require explicit human/parent approval gates

Privacy and safety defaults should be conservative when minors are involved.

---

## Safety & governance

The platform treats safety as a system property, not a disclaimer.

Minimum expectations:
- sandbox limits (timeouts; resource bounds where possible)
- forbidden imports / policy constraints enforced in code
- no hidden test leakage; sanitized traces
- hint-first default (no full solution reveal unless policy allows)

**Note:** the current sandbox backend is designed for teaching and determinism, not hardened multi-tenant security. For adversarial settings, swap to container/VM/microVM isolation behind the same `sandbox.run` tool boundary.

---

## Contribution rules (quality bar)

Changes should preserve:
- the verified-before-present invariant
- determinism where required (grading and eval harness)
- typed boundaries and error taxonomy
- bounded loop behavior
- trace completeness
- unit test coverage for new behavior

Before merging a change, ask:
1. Does this preserve invariants?
2. Can we reproduce failures from logs/records?
3. Is the change isolated behind stable seams (tools/apps)?
4. Are errors typed and actionable?
5. Are there tests?

If not, refactor until “yes.”

---

## Roadmap (high-level)

Near-term (platform maturity):
- benchmark suite expansion (task breadth and scenario breadth)
- standardized metrics reporting and aggregation
- stronger sandbox backend option (container/VM)
- clearer plugin interfaces for non-code verifiers

Mid-term (research and product growth):
- LLM-backed generator/tutor tools behind the same schemas
- RAG as a tool with injection-resistance evaluation
- mastery model and curriculum planning as optional layers
- trace visualization / replay UX
