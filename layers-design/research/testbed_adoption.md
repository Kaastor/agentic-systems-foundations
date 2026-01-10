# Testbed Adoption Guide
**Also known as:** Maturity Levels + Build Order + Repo Architecture + “Paper-Ready” Checklist

---

## 0. What this document is (and isn’t)

This guide tells you how to add a **research testbed layer** to an existing agentic system architecture that already has:

- a **Kernel / Reliability Layer** (TCB that enforces budgets, policy gating, verification, audit, replay hooks),
- a **Strategy / Brain Layer** (replaceable cognition: planning, search, routing, tool-use reasoning).

It is **not**:
- a tutorial on any single benchmark,
- a set of “magic prompts,”
- a substitute for experimental rigor.

The point is to build a testbed that can sustain:
- daily experimentation without becoming a pile of scripts,
- credible claims with reproducible evidence,
- a path to open release without leaking secrets.

---

## 1. Operating definitions

### 1.1 Testbed “layer” in a kernel/strategy architecture

The testbed layer is *not* a third brain. It is a **controlled harness** that runs kernel+strategy in environments with measurable ground truth.

It contributes in two places:

**(A) Kernel module (mechanics / enforcement)**
- record/replay middleware for model and tool boundaries,
- deterministic time/RNG sources,
- fault injection (deterministic + auditable),
- run manifests and artifact packaging,
- side-effect-free “reproducible eval mode.”

**(B) Userland research harness (orchestration)**
- benchmark registry and scenario loaders,
- experiment runner (sweeps, AB comparisons, baselines),
- analysis pipelines and reports.

**(C) Strategy library (methods)**
- baseline strategies (ReAct, plan-execute, best-of-N, search, critics),
- your new proposed strategy variants.

### 1.2 Why you should *not* “just use production as-is”

You can absolutely run research on top of a production agent — but top-quality research requires properties production systems often lack by default:

- stable, replayable environments (web pages change; APIs drift),
- clean experimental control (seeds, budgets, comparable compute),
- dataset governance (splits, immutability, leakage prevention),
- standardized metrics and scoring,
- artifact packaging for others to reproduce.

Those are testbed responsibilities.

---

## 2. What belongs where (the boundary table)

| Concern | Kernel (mechanics) | Strategy (methods) | Testbed harness (orchestration) |
| --- | --- | --- | --- |
| Record/replay tool outputs | **MUST** | Never | **MUST** consume |
| Record/replay model outputs | **MUST** | Never | **MUST** consume |
| Deterministic time/RNG | **MUST** provide ports | **MAY** consume | **MUST** configure |
| Fault injection | **MUST** enforce | **MAY** react | **MUST** configure scenarios |
| Live vs replay vs mirror mode | **MUST** enforce safety | **MUST NOT** decide | **MUST** select per run |
| Policy gating / approvals | **MUST** | Never | **MAY** set principals/roles |
| Baseline planning/search methods | Never | **MUST** | **SHOULD** ship baseline set |
| Metrics + trace emission | **MUST** | **MAY** add annotations | **MUST** aggregate/analyze |
| Benchmark suite definitions | Never | Never | **MUST** own + govern |
| Splits / leakage prevention | Partial (enforcement hooks) | Never | **MUST** own |
| Paper reproduction bundle | **MUST** emit manifests | **MAY** be included | **MUST** package |

**Rule:** Anything that prevents cheating, leakage, or side effects belongs in kernel enforcement, not in strategy or scripts.

---

## 3. Maturity levels (a practical ladder)

### Level 0 — “Notebook wind tunnel” (local only)

**Goal:** Fast iteration on ideas with simulated tools.

**Requirements**
- Minimal environment interface (scenario → episode run)
- One or two toy environments (file system, simple DB)
- Baseline strategy (simple ReAct or plan-execute)
- Metrics: success/failure + token counts

**Allowed sins**
- no record/replay,
- no strict splits,
- ad-hoc configs.

**Not publishable.** This is for learning and prototyping.

---

### Level 1 — Replayable harness (minimum credible research)

**Goal:** You can reproduce results on your machine tomorrow.

**Minimum adds**
- Run manifest for every episode
- Deterministic seed control (RNG + time)
- Record/replay for tool outputs (at least)
- Scenario registry + stable IDs
- A tiny “golden” scenario set for regression

**Publishability**
- Internal reports and early drafts, but still weak for external reproduction.

---

### Level 2 — Benchmark suite governance (conference-grade baseline)

**Goal:** You can defend your evaluation design.

**Minimum adds**
- Versioned benchmark suites (immutable IDs + hashes)
- dev/val/test splits (scenario-level)
- Leakage prevention rules (ground truth hidden; no score tool)
- Deterministic verifiers wherever possible
- Standard metrics (success, cost, latency, safety events)
- Baseline library (at least 2–3 strong baselines)

**Publishability**
- Strong enough for many venues if environment is realistic and results are reproducible.

---

### Level 3 — Hybrid real-tools testbed (ecological validity)

**Goal:** The agent faces real tool failure modes.

**Minimum adds**
- Live / record / replay / mirror modes per tool
- Credential isolation (MCP-style connector boundaries recommended)
- Rate limiting, ToS/robots compliance (especially web tools)
- Chaos suite: latency, timeouts, partial failures
- Robustness reporting (variance across seeds and tool nondeterminism)

**Publishability**
- This is where results start to generalize.

---

### Level 4 — Publication-grade platform (open release ready)

**Goal:** Others can run it without your infra.

**Minimum adds**
- Reproduction bundles: manifests + suites + recordings/mirrors + analysis
- Containerized execution (pinned dependencies)
- Public-friendly environments (no proprietary APIs required to reproduce)
- Artifact evaluation checklist + scripts to verify outputs
- A red-team/injection benchmark pack (if you claim safety/robustness)

**Publishability**
- This is the “top conference artifact” posture.

---

## 4. Build order (the shortest path to “paper-ready”)

1. **Define the schemas first**
   - `ScenarioSpec`, `SuiteSpec`, `RunManifest`, `EpisodeResult`.

2. **Make every run produce a manifest**
   - hashes, seeds, budgets, tool modes.

3. **Add tool record/replay**
   - start with one tool; generalize via middleware.

4. **Add deterministic time**
   - tests will immediately become more stable.

5. **Add a benchmark registry + suite cards**
   - immutability is the unlock.

6. **Add baseline strategies**
   - your new method must earn its keep against them.

7. **Add analysis pipeline**
   - CI can run a small suite; research runs can scale.

8. **Only then add real tools**
   - because without record/replay, “real tools” destroy reproducibility.

---

## 5. Repo architecture (fits your kernel_tcb layout)

A practical structure that keeps boundaries honest:

```
repo/
  kernel_tcb/
    ...                       # your existing kernel
    testbed/                  # kernel module: record/replay, faults, manifests
      recording/
      replay/
      faults/
      manifests/
  strategy/                   # your strategy layer implementation(s)
    baselines/
    variants/
  environments/               # sims and mirrors (NOT in kernel)
    filesystem_world/
    web_world_sim/
    repo_world_mirror/
  benchmarks/
    suites/
      suite_cards/
      suite_defs/
    scenarios/
      <domain>/
  research/
    runners/
    analysis/
    reports/
  evals/
    testbed_regression/       # small gated set
```

**Kernel rule:** `kernel_tcb/testbed/` can wrap kernel boundaries, but cannot add privileged capabilities.

---

## 6. Research workflow (repeatable scientific loop)

1. **State the hypothesis**
   - what failure mode are you fixing?
   - what tradeoff do you expect (cost vs success vs latency)?

2. **Choose the environment and suite**
   - deterministic suite for regression,
   - robustness suite for variance,
   - real-tools suite (live/mirror/record) for validity.

3. **Run baselines first**
   - if your method can’t beat them, don’t paper it yet.

4. **Run ablations**
   - turn one knob at a time.

5. **Do failure analysis**
   - taxonomy counts,
   - trace exemplars,
   - minimal reproduction scenarios.

6. **Promote incidents to regression**
   - any new failure you discover becomes a test case.

7. **Package reproduction bundle**
   - manifests + suite defs + recordings + analysis scripts.

---

## 7. “Paper-ready” checklist (brutally practical)

**Reproducibility**
- [ ] All reported runs have manifests with hashes and seeds
- [ ] Suites are immutable and versioned
- [ ] Reproduction bundle reruns end-to-end offline (replay/mirror)

**Validity**
- [ ] dev/val/test splits exist and test is frozen
- [ ] budgets are controlled and reported
- [ ] compute comparisons include cost/latency axes

**Measurement**
- [ ] deterministic verifiers used where possible
- [ ] LLM judges are calibrated or clearly labeled as noisy
- [ ] metrics include safety/governance events, not just success

**Baselines + ablations**
- [ ] at least 2 strong baselines
- [ ] ablation table exists (remove each feature)

**Ethics**
- [ ] recordings redacted; no PII/secrets
- [ ] live tool usage respects rate limits and ToS

---

## 8. Common failure modes (how testbeds die)

- **Script sprawl**: 20 half-working runners with slightly different configs.
- **Unpinned everything**: model version drift invalidates results.
- **No splits**: you accidentally tune on test.
- **Real tools too early**: unreproducible results and debugging hell.
- **Only sim**: beautiful numbers that don’t survive contact with reality.
- **No baselines**: you can’t tell if your idea matters.

---

## 9. Minimal “starter pack” (if you want momentum)

If you build only one thin slice first, build:

- tool record/replay middleware,
- run manifests with hashes + seeds,
- a 50–200 scenario deterministic suite with strong verifiers,
- 2–3 baseline strategies,
- a single command: `run_suite --suite <id> --strategy <id> --mode replay`.

Everything else can evolve around that stable core.

