# Strategy / Brain Layer Adoption Guide
**Also known as:** Cognition Maturity Levels + Build Order + Team & Org Patterns  
**Status:** Operationalization guide for strategy modules (non‑TCB)  
**Version:** v1.0  
**Last updated:** 2026-01-08

---

## 0. What this document is (and isn’t)

This guide turns the “strategy layer” into an **engineering adoption plan**:

- a **maturity ladder** for cognition capabilities (planning → grounding → search → multi-agent → learning),
- a **build order** that avoids premature complexity,
- **exit criteria** for each maturity level (tests + telemetry),
- team/organizational patterns to keep iteration fast and evidence-based.

This guide assumes you already have (or are building) the **kernel/reliability layer** that enforces:
budgets, tool mediation, policy gates, verification hooks, audit logging, and state.

Strategy work done without kernel constraints tends to produce brilliant demos and tragic postmortems.

---

## 1. Operating definitions

### 1.1 Strategy layer (a.k.a. “brain”)

The strategy layer is a set of replaceable modules that propose:

- which control loop to use (ReAct vs plan-and-execute vs search, etc.),
- which tools to call and with what arguments,
- how to ground (DB vs CAG vs GraphRAG vs RAG vs browse),
- how to maintain memory/context,
- how to allocate test-time compute,
- how to present final answers with evidence and uncertainty.

### 1.2 Kernel layer (reliability)

The kernel is the enforcement substrate (TCB).  
In adoption terms, strategy maturity is only meaningful when the kernel can safely execute it.

### 1.3 Adoption principle: complexity earns its keep

Add strategy complexity only when:

1. a dominant failure mode in telemetry/evals requires it, **and**
2. you have a verifier / metric that tells you whether it helped.

Otherwise: you are paying token tax for vibes.

---

## 2. Strategy capability ladder (S0–S7)

Each level includes:
- **What you can do**
- **What you must build**
- **Exit criteria** (objective signals)
- **Common failure modes**
- **“Next level” trigger**

### S0 — Single-shot assistant (no tools, no memory)
**Use case:** prototypes, copywriting, brainstorming.  
**Not acceptable** for tasks requiring correctness, grounding, or side effects.

**Capabilities**
- One model call → response

**Must build**
- Prompt versioning + a minimal eval set (even 10 cases)

**Exit criteria**
- Stable tone/format, acceptable hallucination rate for low-stakes content
- Basic cost/latency budget tracking

**Failure modes**
- Hallucinated facts, brittle formatting

**Next trigger**
- You need factuality or external context → S1/S2.

---

### S1 — Structured I/O + tool schemas (foundation)
**Use case:** any serious agent.

**Capabilities**
- Model outputs strict JSON / typed objects
- Tool selection/arguments are structured (even if only “read tools”)

**Must build**
- Typed schemas for:
  - tool call intents,
  - tool arguments,
  - tool results and typed errors,
  - plan skeleton (optional but recommended)
- “Schema adherence” eval pack (malformed JSON, missing fields, wrong enums)

**Exit criteria**
- <1% schema violation rate on a golden suite
- Repair loops bounded and effective

**Common failure modes**
- “Almost valid JSON”, partial outputs, wrong enum values

**Next trigger**
- Multi-step tasks or tool use → S2.

---

### S2 — ReAct loop (tool–observe–act) with basic grounding
**Use case:** search/browse, data lookup, lightweight workflows.

**Relevant method:** ReAct [1].

**Capabilities**
- Iterate: reason → tool → observe → next step
- Basic retrieval (RAG as a tool) or API lookup
- Minimal “ask vs act” behavior under uncertainty

**Must build**
- Observation schema discipline (tool results become typed observations)
- Loop stop conditions (“done”, “need info”, “budget pressure”)
- Tool error handling policy: retry vs alternative vs escalate

**Exit criteria**
- Tool thrash rate below threshold (e.g., <5% runs hit repeated same call)
- Budget exhaustion rate acceptable (e.g., <10% for target tasks)
- Improvement vs S0/S1 on task success, not just “looks smart”

**Common failure modes**
- Infinite loops, repetitive tool calls, hallucinated tool arguments

**Next trigger**
- Tasks need explicit decomposition/progress tracking → S3.

---

### S3 — Plan-and-execute (typed Plan IR + replanning)
**Use case:** longer workflows, coding agents, multi-document synthesis.

**Capabilities**
- Produce a typed plan IR, then execute step-by-step
- Replan when tools fail or evidence is missing
- Track progress against explicit success criteria

**Must build**
- Plan IR schema (goal, steps, dependencies, success criteria, replan triggers)
- Plan validation: “is every step executable with available tools?”
- “Plan quality” eval pack (missing steps, non-executable steps, over-decomposition)

**Exit criteria**
- Plan-execution success improves measurably vs S2 on complex tasks
- Reduced tool thrash (plans reduce random-walk behavior)

**Common failure modes**
- Plans too long (200 microsteps)
- Plans too vague (“research more”)
- Non-actionable steps

**Next trigger**
- Grounding becomes the bottleneck (wrong retrieval, missing evidence) → S4.

---

### S4 — Modern grounding stack (RAG + beyond)
**Use case:** knowledge agents, policy assistants, research agents.

**Relevant methods:** Self-RAG [5], GraphRAG [6][7].

**Capabilities**
- Choose grounding method using a reliability gradient:
  - DB/tool-grounded when possible
  - CAG for bounded corpora
  - GraphRAG for interconnected corpora
  - Self-RAG/adaptive retrieval when retrieval necessity varies
- Evidence objects and claim→evidence linking
- Contradiction handling and insufficiency detection

**Must build**
- Retrieval as a first-class tool contract (`search_docs`, `get_doc`, etc.)
- Evidence model (provenance, spans, trust tier)
- Citation discipline tests (“no uncited factual claims” for configured domains)
- Injection/adversarial doc test pack

**Exit criteria**
- Source attribution accuracy meets threshold
- “Unsupported answer” rate decreases relative to S3
- Retrieval effectiveness metrics improve (precision proxies, human spot checks)

**Common failure modes**
- Over-retrieval (context bloat)
- Under-retrieval (confident hallucinations)
- Evidence ignored even when present

**Next trigger**
- High variance performance due to hard tasks → S5/S6.

---

### S5 — Hierarchical + multi-agent patterns (parallelism for quality)
**Use case:** batch research, large-scale code migrations, “analyze 100 things”.

**Capabilities**
- Supervisor/worker decomposition
- Map–reduce style parallel sub-agents with isolated contexts
- Deterministic aggregation and verification of worker outputs

**Must build**
- Worker contracts (typed input/output)
- Aggregation strategy (merge + dedupe + verify)
- Concurrency budgeting (parallel tool/model calls) and cost controls

**Exit criteria**
- Quality scales with parallelism (reduced “context fatigue”)
- Aggregation reduces hallucinations vs a monolithic agent

**Common failure modes**
- Coordination overhead dominates
- Inconsistent worker outputs; aggregator lacks validation

**Next trigger**
- Mistakes are costly; you need “lookahead” and search → S6.

---

### S6 — Search & test-time compute (best-of-N, ToT-style, verifiers)
**Use case:** high-stakes planning, hard reasoning, complex coding where a wrong step is expensive.

**Relevant methods:** Tree of Thoughts [4], test-time compute scaling [8].

**Capabilities**
- Best-of-N plans/tool args with verifier selection
- Tree/graph search over intermediate “thoughts” when scoring exists
- Adaptive compute allocation based on uncertainty/stakes

**Must build**
- Verifiers/judges (deterministic if possible; model judges calibrated)
- Compute policy: how N scales with uncertainty/risk
- Search pruning/backtracking rules
- Anti-gaming tests (verifier robustness)

**Exit criteria**
- Measurable success improvement on hard tasks for acceptable cost
- Lower catastrophic error rate (tail risk reduced)

**Common failure modes**
- Search burns budget without gains
- Verifier is weak → selects confidently wrong candidate

**Next trigger**
- You need scale/cost efficiency and continuous improvement → S7.

---

### S7 — Multi-model routing + learning loops (industrialization)
**Use case:** production at scale, heterogeneous workloads, continuous improvement.

**Relevant methods:** role-based multi-model patterns (Anthropic guidance) [9][10], and post-training loops such as GRPO-style optimizers [11][12].

**Capabilities**
- Role-based model routing (router/planner/executor/critic/summarizer)
- Prompt optimization / “compiled prompts” loops (DSPy-style)
- Fine-tuning on successful traces (SFT) and RL with verifiers

**Must build**
- Router policy with tests and metrics (cost saved vs quality lost)
- Dataset governance for training data derived from traces
- Training/eval pipeline integrated with release gates (no silent regressions)
- Canary rollouts of new strategy bundles

**Exit criteria**
- Cost per successful task decreases without quality regression
- Continuous improvement is measurable (monthly deltas on pinned suites)
- Incident rate does not increase with iteration velocity

**Common failure modes**
- Over-optimization for a judge (reward hacking)
- Model routing edge cases and weird regressions

---

## 3. Build order (what to implement first)

A practical order that avoids “advanced techniques on a shaky foundation”:

1. **S1: structured I/O discipline**  
   Schemas, validators, repair loops, minimal eval pack.
2. **S2: ReAct loop**  
   Tool–observe–act with strict stop conditions and error taxonomy.
3. **S3: Plan IR**  
   Plan schema, plan validation, replan triggers.
4. **S4: Grounding stack + evidence model**  
   Decide between DB/CAG/GraphRAG/RAG; implement evidence objects and citations.
5. **S5: Hierarchical decomposition**  
   Contracts, parallelism, aggregation verifiers.
6. **S6: Search + verifiers**  
   Best-of-N, ToT-style search, calibrated judges.
7. **S7: Routing + learning**  
   Multi-model roles, prompt optimization, SFT/RL tied to eval gates.

---

## 4. Strategy teams: roles and responsibilities (RACI)

A high-performing agentic team separates concerns while keeping the loop tight.

### 4.1 Suggested roles

- **Agent Architect (Staff/Principal)**: owns end-to-end cognition architecture, selects control loops, owns eval strategy.
- **Tooling Engineer**: owns tool schemas, tool UX (preview/diff), tool correctness, latency/caching.
- **KnowledgeOps Engineer** (if you do RAG): ingestion, indexing, provenance, “needle sets”, doc drift detection.
- **Eval/Experiment Engineer**: owns offline suites, judges, telemetry dashboards, A/B framework.
- **Product/UX**: owns user mental model, approval flows, transparency, fallbacks.
- **Security/Policy**: owns risk tiers, tool permissions, escalation, incident response.

### 4.2 RACI sketch (example)

| Deliverable | Architect | Tool Eng | KnowledgeOps | Eval Eng | Product | Security |
|---|---|---|---|---|---|---|
| Strategy control loop choice | **A/R** | C | C | C | C | C |
| Tool schema + previews | C | **A/R** | C | C | C | C |
| Retrieval quality + provenance | C | C | **A/R** | C | C | C |
| Golden eval suites + gates | C | C | C | **A/R** | C | C |
| Router/routing policy | **A/R** | C | C | **R** | C | C |
| Training data governance | C | C | C | **A/R** | C | C |
| Incident runbooks | C | C | C | C | C | **A/R** |

(A = accountable, R = responsible, C = consulted)

---

## 5. Evidence-based iteration loop (how to improve “brains” safely)

A repeatable strategy iteration loop:

1. **Observe** dominant failures (telemetry + trace review)
2. **Hypothesize** a fix (prompt, plan IR, retrieval, verifier, routing)
3. **Implement** behind a feature flag / new strategy bundle
4. **Evaluate offline** on pinned suites (golden + adversarial)
5. **Canary** (small % of traffic) + shadow evals
6. **Monitor** quality, cost, safety signals
7. **Promote or rollback** based on thresholds
8. **Add regression tests** for any incident or new failure mode

This loop is the core “agent engineering” muscle.

---

## 6. Teaching track (optional, but recommended if you’re training others)

A simplified pedagogy that still teaches transferable skills:

1. S1 schemas + JSON validation
2. S2 ReAct with 2–3 read-only tools
3. S3 typed plan + basic replanning
4. S4 minimal RAG as a tool + evidence objects
5. S6 tiny best-of-N with a deterministic verifier (e.g., unit tests)

Avoid:
- multi-tenant governance,
- complex RL training loops,
- heavy infra,

until students can debug traces and reason about failure modes.

---

## 7. Strategy anti-patterns (how brains die)

1. **Over-decomposition**: 200 subtasks for something that needs 5.
2. **Critic collapse**: the critic rubber-stamps everything.
3. **Retrieval mania**: “more context” as a substitute for thinking.
4. **Tool thrash**: retrying the same failing tool call with tiny variations.
5. **Search without scoring**: ToT/MCTS with no verifier = expensive nonsense.
6. **Hidden routing logic**: decisions only in prompts, impossible to test.
7. **Training without governance**: RL/SFT without pinned evals → regressions.
8. **No “I don’t know” path**: forced answers → hallucinations.

---

## Appendix A: Reference links

[1]: https://arxiv.org/abs/2210.03629  "ReAct"  
[4]: https://arxiv.org/abs/2305.10601  "Tree of Thoughts"  
[5]: https://arxiv.org/abs/2310.11511  "Self-RAG"  
[6]: https://arxiv.org/abs/2404.16130  "GraphRAG paper"  
[7]: https://www.microsoft.com/en-us/research/project/graphrag/  "Microsoft Research: GraphRAG"  
[8]: https://openai.com/index/learning-to-reason-with-llms/  "OpenAI: Learning to reason with LLMs"  
[9]: https://www.anthropic.com/research/building-effective-agents  "Anthropic: Building Effective AI Agents"  
[10]: https://www.anthropic.com/engineering/writing-tools-for-agents  "Anthropic: Writing tools for agents"  
[11]: https://arxiv.org/abs/2402.03300  "DeepSeekMath (introduces GRPO)"  
[12]: https://arxiv.org/abs/2505.22257  "Revisiting GRPO"  
