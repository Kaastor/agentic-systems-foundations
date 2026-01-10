A serious research **testbed** is less “a feature” and more “a wind tunnel”: you want to swap brains, environments, tools, and budgets while everything else stays controlled, measurable, and replayable.

So the clean answer is: **it’s cross‑cutting, but it belongs *primarily* in the reliability/kernel layer as first‑class infrastructure**, with **strategy-layer additions only where they enable fair comparison of “brains.”** You *can* do research on top of your existing reliability+strategy stack “as is,” but if you’re aiming for **top-conference-grade** results, you’ll almost certainly want a few explicit testbed extensions—mostly to enforce **reproducibility, controllability, and ground-truth scoring**.

This lines up with your kernel blueprint’s emphasis on replay/fault injection and eval gates (K11/K12), and your hub’s explicit “Simulation / Sandboxes / Synthetic Environments” specialization.  

---

## What makes a testbed “publishable” (the properties reviewers implicitly demand)

A publishable agent testbed usually has these properties (think: reasons papers get accepted/rejected):

1. **Reproducible**

   * Same code + same artifacts + same seeds ⇒ same trajectories (or quantified variance).
   * Record/replay for both **tools and model I/O**.

2. **Controllable**

   * You can dial difficulty, distribution shift, tool reliability, latency, partial failures, prompt injection prevalence, etc.
   * You can isolate causal factors (brain A vs brain B) without confounds.

3. **Measurable with ground truth**

   * Clear success criteria, intermediate signals, and well-defined rewards.
   * Not “LLM-judge vibes only” unless you calibrate it hard.

4. **Realistic enough to matter**

   * Environments reflect the shape of real tool ecosystems (permissions, partial failures, stale data, rate limits, changing UIs).
   * Tasks aren’t toy puzzles unless your claim is explicitly about toy puzzles.

5. **Extensible**

   * New tasks/tools/attack patterns can be added without rewriting the world.
   * You can publish the framework and others can implement adapters.

Those properties map *much more naturally* to the **reliability layer**, because they’re about the **runtime substrate**: determinism, logging, replay, fault injection, scenario definition, governance.

---

## Where testbed capabilities should live

### 1) Reliability layer (kernel): where most testbed additions belong

If you want conference-grade rigor, the kernel should explicitly support a **Research/Testbed Mode** that is:

* **Side-effect safe** (no real external writes)
* **Deterministic where possible**
* **Fully traced + replayable**
* **Fault-injectable**
* **Scoreable**

Conveniently, your kernel blueprint already includes the primitives that *want* to become a testbed:

* **K11 Reproducibility Hooks (Replay + Fault Injection)**: this is basically testbed DNA. 
* **K12 Evaluation Harness + Release Gates** and **K12a Eval Corpus Governance**: in research terms, this is your benchmark framework and dataset discipline. 
* **K2 Orchestrator** (explicit state machine), **K9 Audit/Trace**, **K10 Persistence**, **K6 Budgets**: these become your experiment control plane. 
* Hub Specialization **P (Simulation, Sandboxes & Synthetic Environments)** and **F (Evaluation/Experimentation)** describe exactly the “wind tunnel” idea. 

**Concrete kernel-level additions I’d make (testbed profile):**

* **Environment abstraction**: treat “the world” as a pluggable backend behind your tool interfaces.

  * `LiveToolAdapter` (real APIs)
  * `SimToolAdapter` (deterministic simulator with hidden state + ground truth)
  * `ReplayToolAdapter` (plays back recorded traces)

* **Ground-truth oracle + scorer hooks**

  * The simulator can know truth; your scoring should be deterministic.
  * Scoring should output: `success`, `failure_type`, `partial_credit`, plus structured diagnostics.

* **Fault injection as a first-class policy**

  * Inject: timeouts, malformed tool outputs, latency spikes, rate limits, stale reads, permission denials, adversarial content, UI changes (for browser-like environments).
  * This should be declarative: a per-run “fault schedule” artifact (versioned).

* **Deterministic time + randomness**

  * A “clock” service and seeded RNG used everywhere the world can vary.
  * Seeds and clock state recorded in the run manifest for replay.

* **Experiment manifest**

  * One artifact that pins: strategy ID/version, kernel bundle hash, tool manifest hash, environment version, seeds, budgets, fault profile, task suite version.
  * Without this, you can’t convincingly claim results are reproducible.

* **Strict separation: research vs production**

  * Your kernel already sketches `mode="replay"` semantics; expand this to `mode in {live, sim, replay}` and enforce **no side effects** outside `live`. 

In short: **the reliability layer becomes the scientific instrument**.

---

### 2) Strategy layer: testbed additions that enable fair “brain” research

The strategy layer is where you compare methods (planning/search/memory policies), so testbed-related strategy additions should focus on:

* **Standardized strategy interface** (so swapping brains doesn’t change the world)
* **Baselines library** (so your results aren’t “we beat a strawman”)
* **Compute-control & reporting** (so “method A used 10× inference-time compute” is visible)

**Concrete strategy-layer additions I’d make:**

* **Baseline strategy suite**

  * ReAct
  * Plan-then-execute
  * Plan–act–reflect / critique loops
  * Best-of-N for plan/tool-args with verifier selection
  * Tree search / lookahead in sim (bounded MCTS/BFS)
  * Router–executor (MRKL-style)

  Your hub’s strategy modules explicitly call these out under planning/search and architecture patterns. 

* **Compute budgeting as part of the strategy contract**

  * Strategies must declare (or be constrained by) budgets: number of model calls, “thinking tokens,” branching factor for search, max simulator rollouts.

* **Trajectory annotation**

  * Strategies should emit *structured intent metadata* that helps analysis:

    * “I think this tool call is risky because…”
    * “I’m exploring option #k of N”
    * “Verifier rejected because…”
  * Not for trusting the agent—purely for later scientific analysis.

This keeps strategy-layer testbed hooks *minimal* and prevents the “benchmark is secretly tuned to one architecture” trap.

---

## Can you do research without changes?

You can do *some* research without changes—especially if your kernel already has:

* record/replay,
* a strong eval harness,
* good telemetry,
* safe sandboxing.

But to publish at top venues, the missing pieces are usually:

* **Ground-truth environments** (simulators) rather than only live tools or human judgment
* **Controlled distribution shift + fault injection**
* **Task suite governance** (versioning, stable splits, dataset cards)
* **Statistical rigor** (multiple seeds, confidence intervals, ablations)
* **Baselines that are hard to dismiss**

So: you can start immediately on top of your current layers, but you’ll quickly want the kernel-level “testbed profile” to avoid the classic reviewer critique: *“unclear if results are reproducible / confounded / reliant on proprietary quirks.”*

---

## The clean architecture move: define “Testbed” as a third packaging, not a third layer

Conceptually, don’t create a new layer that competes with reliability vs strategy. Instead:

* **Reliability layer (kernel)**: enforces invariants and provides instrumentation + replay + safety.
* **Strategy layer**: pluggable brains.
* **Testbed package**: a **harness** that binds:

  * task suites + environments (sim/replay/live),
  * scoring + analysis pipelines,
  * experiment manifests,
  * baseline strategies,
  * reporting.

In other words, the testbed is a **consumer** of both layers, but it requires a few kernel capabilities to be truly scientific.

This is exactly the spirit of your hub’s “Simulation…” specialization paired with “Evaluation…”—simulation provides truth; evaluation provides measurement. 

---

## Practical decision rule

If a requirement is about **the world being controlled and observable**, it goes into **reliability/kernel**.

If a requirement is about **how the agent thinks**, it goes into **strategy**.

Examples:

* Record/replay tool I/O → reliability
* Fault injection schedules → reliability
* Ground-truth scoring → reliability
* Baseline planners/search strategies → strategy
* Best-of-N / MCTS / critique loops → strategy
* Standard experiment manifest + artifact pinning → reliability (because it’s enforcement + provenance)

---

## The punchline

Build the testbed as a **first-class profile of the kernel** (reliability layer) plus a **baseline suite of strategies** (strategy layer). That gives you:

* Production-grade engineering discipline (your kernel as TCB),
* Research-grade experimental control (sim/replay/fault injection),
* And a clean way to publish: *“We compare brains under identical kernels/environments.”*

That “identical kernel/environments” phrase is basically catnip to reviewers—because it screams “this isn’t benchmark theater.”

 
