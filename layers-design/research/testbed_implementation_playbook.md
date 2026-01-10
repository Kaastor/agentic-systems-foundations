# Testbed Implementation Playbook
**Building a reproducible, hybrid (real + sim) research platform for agentic systems**

---

## 0. Purpose and scope

This playbook describes how to implement a **publication-grade testbed layer** on top of a kernel/strategy architecture.

It focuses on engineering mechanics that make research results:
- **repeatable** (record/replay + manifests),
- **measurable** (verifiers + metrics),
- **comparable** (controlled budgets + compute reporting),
- **realistic** (real tool failure modes + chaos testing),
- **safe** (no policy bypass).

This playbook assumes you already have the kernel fundamentals (schemas, tool executor, policy engine, audit, persistence). The testbed largely plugs into the kernel via **middleware**.

---

## 1. Reference architecture (a shape you can defend)

### 1.1 High-level components

```
+-------------------+          +---------------------------+
| Research Runner   |          | Benchmark Registry        |
| (sweeps/AB/etc.)  |--------->| (Suites, Scenarios, Splits|
+-------------------+          +---------------------------+
          |
          v
+----------------------------------------------------------+
| KernelRuntime.run(request, strategy)                      |
|  - budgets, policy, verification, audit                   |
|  - deterministic state machine                             |
|                                                          |
|  [Model Boundary] <--> [Tool Executor] <--> [Env/Tools]   |
|      ^                    ^                                |
|      |                    |                                |
|  Testbed middlewares:     |                                |
|   - record/replay         |                                |
|   - fault injection       |                                |
|   - deterministic time/RNG|                                |
|   - manifest emission     |                                |
+----------------------------------------------------------+
          |
          v
+-------------------+          +---------------------------+
| Result Store      |          | Analysis Pipeline         |
| (EpisodeResults)  |--------->| (tables/plots/reports)    |
+-------------------+          +---------------------------+
```

### 1.2 Boundary rules

- **Strategy** never calls tools directly.
- **Testbed harness** never bypasses the kernel to call tools or models.
- **Testbed middlewares** intercept calls *inside* kernel boundaries, to record/replay/fault-inject safely.

### 1.3 The “four tool modes” architecture (per tool)

Every tool adapter is wrapped by a mode controller:

```
ToolCall(args)
  -> ToolModeRouter(mode=Live|Record|Replay|Mirror)
       -> (Live)   RealToolAdapter
       -> (Record) RealToolAdapter + Recorder
       -> (Replay) Replayer (no network)
       -> (Mirror) MirrorToolAdapter (local snapshot)
```

This is the core resolution of: “in research I want real tools, not only sim adapters.”

---

## 2. Core schemas (start here, or everything will rot)

### 2.1 RunManifest

A manifest must be sufficient to recreate the environment *as seen by the agent*.

```json
{
  "@type": "RunManifest",
  "run_id": "uuid",
  "trace_id": "uuid",
  "created_at": "2026-01-09T00:00:00Z",

  "kernel_bundle_hash": "sha256:...",
  "strategy_id": "plan_execute_v3",
  "strategy_bundle_hash": "sha256:...",

  "model": {
    "provider": "openai",
    "model_id": "gpt-4.1",
    "decoding": {"temperature": 0.2, "top_p": 1.0, "max_tokens": 4096}
  },

  "environment": {
    "env_id": "repo_world_mirror:v1",
    "env_hash": "sha256:...",
    "scenario_id": "swe_task_00123",
    "suite_id": "swe_suite_test:v2",
    "split": "test"
  },

  "tool_modes": {
    "git": "mirror",
    "filesystem": "mirror",
    "web_fetch": "replay",
    "email_send": "disabled"
  },

  "budgets": {
    "max_steps": 80,
    "max_wall_clock_sec": 900,
    "max_tokens_total": 60000,
    "max_tool_calls": 200
  },

  "determinism": {
    "seed": 1337,
    "time_mode": "fixed",
    "time_epoch": 1700000000
  },

  "recording_refs": {
    "tool_recording_id": "rec_abc",
    "model_recording_id": "mrec_def"
  }
}
```

**Implementation rule:** the kernel emits this manifest; the research runner stores it.

### 2.2 ScenarioSpec

```json
{
  "@type": "ScenarioSpec",
  "scenario_id": "swe_task_00123",
  "env_id": "repo_world_mirror:v1",
  "initial_state_ref": "artifact://snapshots/repo_00123.tar",
  "objective": {
    "type": "code_fix",
    "description": "Fix failing tests in module X."
  },
  "agent_visible_inputs": {
    "problem_statement": "…",
    "repo_path": "/workspace/repo"
  },
  "hidden_truth": {
    "expected_tests": ["pytest -q"],
    "grading": {"type": "tests_pass"}
  }
}
```

**Leakage rule:** `hidden_truth` is never provided to strategy prompts.

### 2.3 SuiteSpec (“suite card” is mandatory)

A suite definition references scenarios + split strategy:

```json
{
  "@type": "SuiteSpec",
  "suite_id": "swe_suite_test:v2",
  "purpose": "Measure code-fixing success under controlled mirrors.",
  "scenario_ids": ["…"],
  "splits": {"dev": [...], "val": [...], "test": [...]},
  "verifier_ref": "artifact://verifiers/swe_tests_v2",
  "metrics": ["success", "tokens", "time", "tool_calls", "violations"]
}
```

A **Suite Card** is a human-readable doc stored next to SuiteSpec:
- purpose,
- coverage,
- provenance,
- leakage analysis,
- known limitations,
- change log.

---

## 3. Record/replay implementation (do this before “real tools”)

### 3.1 Where to intercept

Intercept at the kernel boundaries:

- **Model Boundary middleware**
  - record: prompt hash + request params + normalized response
  - replay: return the recorded response for the same key

- **Tool Executor middleware**
  - record: canonical tool args + tool version + normalized output/error + timing
  - replay: return recorded output/error for the same key, without executing the tool

### 3.2 Stable replay keys

Keys MUST be stable across runs and machines.

**Tool replay key**
```
tool_key = sha256(
  tool_name
  + tool_version
  + canonical_json(arguments)
  + mode_context   # optional: env_hash or scenario_id to avoid collisions
)
```

**Model replay key**
```
model_key = sha256(
  prompt_hash
  + canonical_json(prompt_inputs)
  + canonical_json(decoding_params)
  + model_id
)
```

### 3.3 Canonicalization rules

- sort JSON keys,
- normalize floats if they appear,
- strip nondeterministic fields (timestamps) *before* hashing,
- include tool/model version fields, always.

### 3.4 Recording storage format

Use an append-only log keyed by `run_id` + `call_index`, plus an indexed KV store by replay key.

Recommended structure:
- `recordings/<recording_id>/events.jsonl` (append-only)
- `recordings/<recording_id>/index.sqlite` (key → offset)

### 3.5 Replay mismatch policy (fail loudly)

If a replay key is missing:
- in **replay mode**: fail the step with a typed `ReplayMiss` error,
- in **hybrid mode**: consult per-tool policy (allowed to fall back to live or not),
- always log as a first-class event.

This prevents “accidental live calls” from contaminating reproducible runs.

---

## 4. Deterministic time and RNG (the underrated stability unlock)

### 4.1 TimeSource port

All time access must go through a `TimeSource` interface:
- `now_epoch()`
- `sleep(ms)` (optional)

Provide implementations:
- `RealTimeSource`
- `FixedTimeSource(epoch)`
- `RecordedTimeSource(recording_id)` (optional)

The kernel’s orchestrator and any sandbox execution must use `TimeSource`, not `time.time()` directly.

### 4.2 RNGSource port

All randomness used by:
- fault injection,
- scenario perturbations,
- sampling in harness (not the LLM provider sampling, but your runner logic),
must go through a seeded RNG.

---

## 5. Fault injection (“chaos”) as a deterministic feature

### 5.1 Fault injection spec

Represent faults as data:

```yaml
faults:
  seed: 1337
  tool_faults:
    - tool: web_fetch
      probability: 0.10
      faults:
        - type: timeout
          timeout_ms: 2000
        - type: malformed_json
    - tool: search_docs
      probability: 0.05
      faults:
        - type: partial_results
          drop_fraction: 0.5
  model_faults:
    - probability: 0.02
      faults:
        - type: provider_timeout
```

### 5.2 Injection points

- before tool execution: inject timeout/malformed output
- after tool execution: corrupt output (to test verifier robustness)
- before model call: inject provider errors
- after model response: truncate output (to test schema repair paths)

### 5.3 Reporting

Every injected fault MUST appear in:
- trace events,
- the run manifest (fault spec hash),
- episode result summary (count by type).

---

## 6. Environment design patterns (how to build “worlds”)

You need both:
- **mirror environments** for reproducibility with realism,
- **sim environments** for full control and ground truth.

### 6.1 The “ToolWorld” environment interface

A pragmatic environment interface for tool-using agents:

- `prepare(scenario_spec) -> EnvContext`
- `get_tool_manifest(env_context) -> ToolManifest`
- `get_initial_observation(env_context) -> Observation`
- verifiers: `score(run_trace, env_context) -> EpisodeScore`

This keeps tools as the “actuator” and the verifier as the “ground truth.”

### 6.2 Mirror environments (recommended for publishable realism)

Mirror design:
- take a snapshot of the external system,
- serve it locally via tools.

Examples:
- **Repo mirror**: tarball of a git repo + local git tool + local filesystem tool
- **DB mirror**: sqlite snapshot + query tool
- **Ticket system mirror**: JSON fixtures + CRUD tool (writes disabled in eval mode)

Mirror advantages:
- reproducible,
- realistic enough to exercise tool schemas and failure modes,
- sharable without credentials.

### 6.3 Simulation environments (recommended for controlled research)

Simulation design:
- explicit state transition model,
- oracle ground truth,
- ability to perturb environment systematically.

Uses:
- studying planning/search algorithms,
- prompt injection and exfiltration experiments,
- multi-agent coordination games.

---

## 7. Integrating real tools safely (yes, use them — but architect it)

### 7.1 Live tools must go through connectors (credential isolation)

Strong recommendation:
- use a connector boundary (e.g., MCP-style tool servers) that:
  - handles OAuth/credentials outside the agent context,
  - enforces per-tool scopes and allowlists,
  - logs independently.

### 7.2 Live runs should be used to *collect recordings*

Adopt a two-stage workflow:
1. **Live/Record stage**: run against real tools, record tool I/O.
2. **Replay/Mirror evaluation stage**: produce publishable numbers.

This gives ecological validity without sacrificing reproducibility.

### 7.3 Safety posture in research mode

- default to read-only tools,
- write tools require explicit policy and approvals (even in research),
- any “destructive” tool must have preview/diff and must be disabled in replay mode.

---

## 8. Benchmark governance and leakage prevention

### 8.1 Suite immutability

Once a suite version is used in a paper:
- suite definition is frozen (hash-verified),
- scenarios are immutable,
- splits are immutable.

If you change anything: bump suite version.

### 8.2 Scenario IDs and stable anchors

- scenario IDs must be stable,
- all artifacts referenced must be content-addressed (hash-based) when possible.

### 8.3 Leakage checks (automated)

Add a “leakage lint” that scans scenario specs for:
- ground truth accidentally exposed in agent-visible fields,
- file paths that point to solution files,
- evaluator code reachable via tools.

---

## 9. Metrics, aggregation, and reporting (standard outputs)

### 9.1 EpisodeResult schema (minimum)

```json
{
  "@type": "EpisodeResult",
  "scenario_id": "…",
  "run_id": "…",
  "strategy_id": "…",
  "success": true,
  "score": 1.0,
  "failure_reason": null,
  "metrics": {
    "wall_time_ms": 123456,
    "tool_calls_total": 42,
    "tool_calls_by_tool": {"git": 5, "pytest": 3},
    "tokens_in": 12000,
    "tokens_out": 4000,
    "policy_denials": 0,
    "replay_misses": 0,
    "faults_injected": 2
  }
}
```

### 9.2 Aggregate reports (what you should publish)

For each suite:
- success rate (with CI),
- cost/latency distribution (P50/P90/P99),
- failure taxonomy,
- Pareto frontier: success vs tokens/time.

---

## 10. Experiment runner (sweeps, ablations, and baselines)

### 10.1 Configuration as data

Use a declarative experiment spec:

```yaml
experiment:
  name: best_of_n_ablation
  suite: swe_suite_test:v2
  repeats: 3
  strategies:
    - id: baseline_plan_execute
      params: {}
    - id: best_of_n
      params: {n: [1, 2, 4, 8]}
  mode: replay
  budgets:
    max_steps: 80
    max_tokens_total: 60000
```

The runner expands the grid and writes one RunManifest per episode.

### 10.2 Baseline library

A credible testbed ships with baselines:
- simple ReAct (bounded),
- plan-and-execute (typed plans),
- best-of-N plan selection (verifier-chosen),
- optionally: a tree-search variant if your environment supports it.

Baselines must share:
- tool manifest constraints,
- budgets,
- verifiers.

---

## 11. CI integration (research needs gates too)

### 11.1 A “gated micro-suite”

Create a small suite (e.g., 20 scenarios) that runs in <10 minutes in replay mode.

CI gates:
- no new policy violations,
- no regression beyond threshold,
- no replay misses,
- stable metrics within tolerance.

### 11.2 Canary suite (nightly)

Nightly runs can include:
- bigger suites,
- robustness (fault injection),
- hybrid live runs (optional) — but do not gate merges on nondeterministic live results.

---

## 12. Reproduction bundles (what you hand to the world)

A minimal reproduction bundle contains:
- suite specs + suite cards,
- scenario specs + artifacts,
- tool/model recordings or mirrors,
- run manifests,
- analysis scripts that regenerate tables/plots.

**Golden rule:** someone without your credentials can still reproduce the headline numbers.

---

## 13. Security and privacy checklist (don’t publish your own secrets)

- redact at ingestion (before writing recordings),
- ban environment variables/secrets from any logged content,
- scrub auth headers and tokens from HTTP tools,
- store recordings encrypted at rest internally; publish only sanitized subsets.

---

## 14. End-to-end “thin slice” implementation plan (do this first)

1. Implement `RunManifest` emission in kernel.
2. Implement tool record/replay middleware for one tool.
3. Implement a mirror environment (local repo snapshot + test verifier).
4. Implement a small suite + suite card.
5. Implement a baseline strategy.
6. Implement `run_suite` CLI that outputs `EpisodeResult.jsonl`.
7. Add CI gating on the micro-suite.

Once this slice is stable, add:
- more tools,
- more environments,
- chaos faults,
- live record collection,
- richer baselines and search methods.

---

## Appendix A: Where this maps to your hub curriculum

- Simulation + sandboxes + synthetic environments → “Simulation, Sandboxes & Synthetic Environments for Agents”
- Evaluation, testing, observability & experimentation → “Evaluation, Testing, Observability & Experimentation”
- Runtime/framework engineering → “Agent Runtime & Framework Engineering”
- Planning/search/test-time compute → “Agent State Machines, Planning & Hierarchical Agents” + “Architecture Patterns & Control Loop Catalog”

The testbed is where those specializations become measurable, reproducible engineering.

