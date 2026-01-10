# The Constitution for a Publication-Grade Agentic AI Testbed Layer

---

## Preamble

A production agent is a *product*.  
A research testbed is a *scientific instrument*.

This document defines a **Testbed Layer** for agentic AI systems that lets you do credible research:
- **reproducible** enough that someone else can rerun your experiments,
- **valid** enough that results mean what you claim they mean,
- **ecologically grounded** enough that conclusions transfer to real tools and real failure modes,
- **safe and auditable** enough that “research mode” doesn’t become a policy bypass.

### The three-layer model (how this testbed fits your architecture)

Your overall architecture is assumed to have:

1. **Kernel / Reliability Layer (TCB)**  
   Mechanically enforces correctness and safety properties: budgets, policy gating, verification, audit, idempotency, replay, sandboxing.

2. **Strategy / Brain Layer (Userland Cognition)**  
   Replaceable methods that decide what to do: planners, routers, search, best-of-N, tool selection logic, memory policies, etc.

3. **Testbed Layer (Scientific Instrumentation + Environments)**  
   A *controlled environment + experiment harness* that runs the kernel+strategy under:
   - deterministic conditions when needed (for reproducibility),
   - realistic conditions when needed (for external validity),
   - with ground-truth measurement and experiment governance.

**Key conclusion (from prior design discussion):**
- **Testbed mechanics belong primarily in the Kernel as a separate module (enforced, non-bypassable)**: record/replay, deterministic time, fault injection hooks, experiment manifests, and run packaging.  
- **Testbed “methods” belong in Strategy**: the suite of planners/search/critics/baselines you compare in experiments.  
- The Testbed Layer ties them together, but **must not erode kernel boundaries**.

---

## Section 1: Normative language and scope

### 1.1 Requirement keywords

The keywords **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

### 1.2 Scope

This Constitution applies to any system that claims to support **research-grade evaluation** of agentic behavior, including:
- offline benchmark evaluation,
- online evaluation against live services/tools,
- simulation environments,
- record/replay experiments,
- fault-injection and robustness testing,
- training loops that rely on environment interaction (e.g., verifier-guided search or RL).

### 1.3 Core definitions

- **Testbed Layer**: The collection of components that provide environments, experiment orchestration, measurement, and reproducibility for agentic systems.
- **Environment**: The “world” the agent interacts with. In tool-using agents, the environment is often the **tool ecosystem** plus any hidden state (files, DB rows, tickets, web pages, etc.).
- **Scenario**: A single task instance with a specified initial state, objective, and evaluation rubric.
- **Episode**: One execution of a scenario by an agent (kernel + strategy) under a specific configuration and random seed.
- **Run Manifest**: A machine-readable bundle that fully specifies how an episode was produced (artifact hashes, model configs, tool modes, seeds, budgets, environment version, etc.).
- **Recording**: A captured trace of environment interactions sufficient to reproduce an episode without contacting external services.
- **Replay**: Deterministic substitution of recorded outputs for model/tool calls, producing identical observations for the agent.
- **Hybrid execution**: Some components are live, some replayed (e.g., model live but tools replayed; or only certain tools live).
- **Ground truth**: The authoritative truth about success/failure and other metrics, produced by deterministic verifiers, oracle simulators, or controlled data sources.
- **Verifier**: A deterministic or bounded checker that can accept/reject outputs or trajectories (tests, compilers, solvers, diff checks, rubrics).
- **Ecological validity**: The degree to which an evaluation reflects real conditions: nondeterminism, partial failures, changing web pages, rate limits, etc.
- **Internal validity**: The degree to which experimental conclusions follow from controlled variables, without confounders.

---

## Article 0: Kernel–Strategy–Testbed contract (non-negotiable)

### 0.1 The kernel remains the enforcement substrate

The Testbed Layer **MUST NOT** bypass kernel enforcement. Specifically:
- all tool calls MUST go through the kernel tool executor,
- all side effects MUST go through kernel policy/approval gates,
- all budgets MUST be kernel-enforced,
- all verification gates MUST be kernel-enforced (or stronger).

**Rationale:** A testbed that can bypass safety is not a testbed; it’s an exploit kit for your own system.

### 0.2 Testbed is a kernel module, not a kernel rewrite

Testbed mechanics **SHOULD** be implemented as a **separate module in the kernel** (e.g., `kernel_tcb/testbed/`) that plugs in via:
- model boundary middleware (record/replay, fault injection),
- tool executor middleware (record/replay, fault injection, mirroring),
- time/RNG sources (deterministic control),
- run-manifest emission and artifact packaging.

The testbed module **MUST** be optional and MUST NOT increase the kernel’s trusted surface area more than necessary:
- it should be mostly declarative configuration and middleware,
- it should not add new privileged tool capabilities.

### 0.3 Strategy is swappable; testbed comparisons assume a stable kernel

In research comparisons:
- The kernel version (bundle hash) **MUST** be treated as part of the experimental condition.
- Claims about a strategy **MUST** report kernel/testbed versions, because kernel mechanics (budgets, policies, verifiers) change outcomes.

### 0.4 “Research mode” is never an authorization mechanism

Testbed configuration **MUST NOT** authorize actions.
- “research mode”, “benchmark mode”, “eval run” are not policy signals.
- policy decisions MUST depend on authenticated principal, tool manifests, and policy bundles — never on free-form metadata.

---

## Article I: Reproducibility and provenance (the heart of publishable research)

### I.1 Every episode is reproducible by construction

For any reported metric or claim:
- the episode **MUST** have a run manifest,
- the manifest **MUST** include stable identifiers/hashes for:
  - kernel bundle,
  - strategy bundle,
  - tool manifest(s),
  - policy bundles,
  - verifier versions,
  - environment version (including simulator version or live tool snapshot strategy),
  - model identifiers and decoding parameters,
  - random seeds and deterministic time configuration,
  - budgets and stop conditions.

### I.2 Record/replay is mandatory for “reproducible evaluation mode”

The testbed **MUST** support a “reproducible evaluation mode” where:
- external tool calls are satisfied from recordings (or local mirrors) instead of the live internet/services,
- the run is side-effect free (write tools disabled or forced into preview-only mode),
- results can be reproduced without private credentials.

This mode is the default for:
- regression testing,
- CI gating,
- public release artifacts.

### I.3 Determinism is a controlled dial, not a religion

The testbed **MUST** explicitly support both:
- **Deterministic mode** (high internal validity): fixed seeds, deterministic time, replayed tools, pinned models.
- **Realistic mode** (high ecological validity): live tools, injected latency/outages, changing environment state.

Any paper/result set **SHOULD** report both when feasible:
- deterministic benchmark numbers (repeatable),
- robustness numbers (variance under realistic conditions).

### I.4 Provenance is attached to data, not to prose

All observations fed to the strategy (user input, tool outputs, retrieved docs) **MUST** carry:
- provenance (source, timestamp, tool name/version),
- classification/redaction metadata,
- suspicion flags (if applicable).

This is required for:
- citation discipline,
- debugging,
- dataset governance,
- prompt-injection research.

---

## Article II: Validity discipline (results that mean what you think they mean)

### II.1 Split what you tune on from what you report

The testbed **MUST** support dataset splitting at the scenario level:
- **dev** (for iteration/tuning),
- **validation** (for early stopping / model selection),
- **test** (for final reported numbers).

The test split:
- **MUST** be immutable once a paper’s main results are produced,
- **MUST NOT** be used for prompt/graph/tool tuning.

### II.2 Prevent evaluation leakage

The environment and harness **MUST** prevent (or detect) common leakage channels:
- hiding ground-truth fields from agent-visible observations,
- ensuring evaluation rubrics are not provided verbatim to the agent (unless the task requires it, e.g., “follow this rubric”),
- preventing agents from reading the score function directly (no “oracle tool”).

If leakage is unavoidable (e.g., the task literally is “optimize this rubric”), it **MUST** be explicitly labeled and treated as a different task class.

### II.3 Comparable compute

If you compare strategies:
- budgets (tokens, steps, tool calls, wall time) **MUST** be controlled and reported,
- comparisons **SHOULD** include a Pareto analysis (accuracy vs cost/latency),
- any “test-time compute” (best-of-N, tree search, critics) **MUST** be normalized or reported as a separate axis.

### II.4 Statistical discipline

Reported metrics **SHOULD** include uncertainty:
- confidence intervals across scenarios,
- variance across seeds (where stochasticity exists),
- failure mode breakdowns (taxonomy-based).

---

## Article III: Environments and tools (real tools, simulated tools, and why you need both)

### III.1 The testbed MUST support real tools

A research testbed intended for agentic systems **MUST** support running against **real tool backends** (real APIs, real code execution sandboxes, real repos, real ticket systems, real web browsing), because:
- real tools have the failure modes that agents must learn (timeouts, partial failures, schema drift, auth issues),
- simulation-only results often overestimate competence and robustness.

### III.2 …and it MUST support simulation, too

The testbed **MUST** also support simulation and synthetic environments, because:
- you need ground truth and full observability to train verifiers and measure failure modes precisely,
- you need controllable chaos (fault injection, adversarial docs, UI changes),
- you need reproducibility without private credentials.

### III.3 The correct architecture: live / record / replay / mirror

Tools in the testbed **MUST** be executable under four modes (per-tool configurable):

1. **Live**: call the real tool backend.
2. **Record**: call live and store inputs/outputs as a recording.
3. **Replay**: serve outputs from recordings; live calls are forbidden.
4. **Mirror** (recommended): call a local mirror of a real system (e.g., local git repo mirror, local DB snapshot), producing reproducible realism.

This resolves the “real tools vs sim adapters” tension:
- use **Live/Record** for exploration and collecting datasets,
- publish and gate on **Replay/Mirror** for reproducibility.

### III.4 Faults are first-class environment features

The testbed **MUST** support injecting faults at controlled points:
- tool latency spikes,
- timeouts,
- malformed responses,
- rate limiting,
- partial outages,
- stale caches,
- non-deterministic web changes (in a controlled simulator).

Fault injection **MUST** be:
- deterministic under a seed in deterministic mode,
- auditable (recorded in the run manifest and trace).

---

## Article IV: Measurement and scoring (what the instrument must measure)

### IV.1 Standard metrics are required (you can add more)

Every testbed run **MUST** emit at least:

**Task success**
- scenario-level success/failure,
- reason codes (verifier failures, policy denials, tool errors, budget exhaustion).

**Efficiency**
- total tool calls (by tool),
- model tokens (in/out),
- wall-clock time,
- cost (if applicable).

**Reliability**
- retry counts,
- loop/thrash events,
- non-halting prevention triggers,
- recovery actions taken.

**Safety/governance**
- policy violations attempted,
- prompt-injection detections,
- secret/PII redaction events.

### IV.2 Verifiers define rewards and correctness

Whenever possible, evaluation SHOULD be grounded in deterministic verifiers:
- tests,
- compilers,
- solvers,
- diff checks,
- schema validators.

LLM-as-judge MAY be used, but:
- must be calibrated against human labels or deterministic checks where possible,
- must be treated as a noisy measurement instrument.

---

## Article V: Governance, ethics, and data discipline

### V.1 No proprietary or sensitive leakage in released artifacts

If you publish datasets/recordings:
- all logs and recordings MUST be classified and redacted at ingestion,
- secrets and PII MUST NOT be included,
- provenance MUST be preserved while redacting content.

### V.2 Respect external systems

For live tool runs (especially web):
- rate limiting MUST be enforced,
- robots/ToS constraints SHOULD be respected,
- a caching/mirroring strategy SHOULD be used to reduce load.

### V.3 The testbed cannot weaken safety posture

Research additions MUST NOT:
- expand tool permissions without explicit policy changes,
- bypass approval gates,
- expose secrets to strategies or models,
- allow replay artifacts to trigger live side effects.

---

## Article VI: Publication readiness (the “someone else can run it” bar)

### VI.1 Every published result has a reproduction bundle

A published result set **SHOULD** include a reproduction bundle containing:
- run manifests for all reported runs,
- benchmark suite definition + hashes,
- recordings (or mirrors) required for replay,
- analysis scripts/notebooks,
- exact version pins (container image digest recommended),
- instructions to rerun and to verify outputs match.

### VI.2 Baselines and ablations are mandatory

A testbed intended for top-tier research **MUST** make it easy to:
- run baseline strategies,
- run ablations (toggle one feature at a time),
- sweep parameters,
- produce standardized plots/tables.

### VI.3 Negative results are first-class

The testbed SHOULD treat “what failed and why” as an output artifact:
- failure taxonomy,
- representative traces,
- minimal reproductions (“one scenario that breaks it”),
- regression tests generated from incidents/failures.

---

## Appendix: Testbed layer “non-goals”

The testbed is not:
- a replacement for the kernel (it must not implement policy),
- a single benchmark suite (it must host many),
- a single strategy (it must compare many),
- a collection of ad-hoc scripts (it must be a governed instrument).

