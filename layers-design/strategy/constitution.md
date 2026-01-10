# The Constitution for the Strategy / Brain Layer of Production Agentic Systems
**Also known as:** Cognition Layer Standard (planning, grounding, memory, search)  
**Status:** Engineering constitution for strategy modules (non‑TCB)  
**Version:** v1.0  
**Last updated:** 2026-01-08

---

## Preamble

The **kernel / reliability layer** makes agentic systems *safe, bounded, auditable, and enforceable* even when the model is wrong.

The **strategy / brain layer** makes agentic systems *useful*.

This document specifies the engineering standards for the **strategy layer**: the replaceable “brains” that propose plans, tool calls, retrieval, memory updates, and final answers — all as **typed proposals** evaluated and executed by the kernel.

### What this Constitution optimizes for

A strategy module SHALL be engineered to maximize:

1. **Task success** (correctness, completion, user intent satisfaction)
2. **Groundedness** (decisions traceable to evidence or authoritative tools)
3. **Efficiency** (token/cost/time budgets respected; minimal thrash)
4. **Legibility** (plans, tool intents, and uncertainty are explicit)
5. **Replaceability** (swap strategies without rewriting kernel invariants)
6. **Evolvability** (supports rapid iteration driven by evals + telemetry)

### Non-goals

This is **not** a “prompt style guide” and it is **not** kernel policy enforcement.  
The kernel remains the Trusted Computing Base (TCB) and enforces safety, authorization, budgets, audit, and side-effect gating.

---

## Section 1: Normative language and scope

### 1.1 Requirement keywords

- **SHALL / SHALL NOT**: mandatory.
- **SHOULD / SHOULD NOT**: strongly recommended; deviations require documented rationale and risk acceptance.
- **MAY**: optional.

### 1.2 Scope

Applies to any module that proposes or influences:

- plans, decompositions, or next actions,
- tool selection and tool arguments,
- grounding choices (DB tools vs CAG vs GraphRAG vs RAG vs browsing),
- memory read/write behavior and summarization policies,
- multi-agent coordination or hierarchical execution,
- model routing, test-time compute allocation, or sampling/search,
- critique/verification loops (model-based or deterministic),
- user-facing responses and supporting evidence/citations.

### 1.3 Definitions

- **Strategy**: a replaceable module that transforms **typed observations** into **typed intents** (and optionally a final answer).
- **Kernel**: deterministic runtime that validates, authorizes, executes, verifies, budgets, audits, and persists.
- **Intent**: a typed proposal produced by strategy (e.g., `ToolCallIntent`, `ModelCallIntent`, `MemoryWriteIntent`).
- **Observation**: a typed, sanitized piece of information the kernel provides to strategy (tool results, retrieved docs, user input, system events).
- **Grounding**: using authoritative external information (tools, databases, vetted corpora) to reduce hallucination risk.
- **Verifier**: any mechanism that can veto/score outcomes (deterministic tests/solvers preferred; model-based critique as defense-in-depth).
- **Test-time compute**: spending additional inference compute (more thinking tokens, more samples, more search) to improve accuracy, within budgets [8].

---

## Article 0: Kernel–Strategy Contract (non-negotiable)

### 0.1 Strategies propose; the kernel disposes

1. Strategy outputs SHALL be treated as **untrusted proposals**.
2. Strategies SHALL NOT directly execute tools, perform side effects, mint permissions, or write audit logs.
3. Strategies SHALL NOT assume they can bypass policy, budgets, or verification.

### 0.2 Typed intent boundary (ABI discipline)

1. Strategies SHALL communicate with the kernel exclusively through a **versioned, schema-validated intent ABI**.
2. Intent schemas SHALL be strict (`extra="forbid"` style) and stable; additions SHALL be backward compatible.
3. Strategies SHOULD be runnable as a **separate process/service** so the kernel boundary is a physics constraint, not a convention.

### 0.3 The kernel’s view of strategy output

The kernel SHALL reject or repair (boundedly) any strategy proposal that violates:
- schema constraints,
- budget constraints,
- policy constraints,
- tool manifest constraints,
- invariant constraints (e.g., “no write tools in read-only mode”).

Strategy code MUST be written with the expectation that:
- proposals can be rejected,
- tool calls can fail,
- observations can be incomplete or adversarially crafted,
- “doing nothing” or escalating is a valid outcome.

---

## Article I: Objective and decision discipline

### I.1 Optimize expected task success under constraints

A strategy SHALL behave like a bounded rational optimizer:

- maximize expected utility of outcomes (task success, user value),
- subject to explicit constraints (time, steps, cost, risk tier, allowed tools).

This implies:
- **uncertainty-aware behavior** (don’t commit to brittle plans when evidence is weak),
- **compute-aware behavior** (don’t burn budgets on low-value deliberation),
- **fallback ladders** (cheap → strong → human escalation when appropriate).

### I.2 Prefer authoritative computation over fuzzy text

When a question can be answered by deterministic tools or structured queries, the strategy SHOULD prefer that over parametric recall or free-form generation. This aligns with MRKL-style modular systems and tool-grounded architectures [3].

### I.3 Ask, don’t guess (when ambiguity is real)

If the task is underspecified and a wrong guess would materially reduce success or increase risk, the strategy SHOULD ask for clarification (or propose a safe default + request confirmation) rather than hallucinating requirements.

---

## Article II: Representations beat vibes (IR-first cognition)

### II.1 Plans are data structures, not prose

If the agent is multi-step, the strategy SHOULD represent its plan as a typed **Plan IR** (intermediate representation), not as a paragraph.

Minimum Plan IR fields (recommended):
- `goal` (what “done” means),
- `constraints` (budgets, policy constraints, user constraints),
- `steps[]` (ordered, typed steps),
- `dependencies[]`,
- `expected_observations[]`,
- `success_criteria` (verifiable where possible),
- `risk_tier` per step,
- `fallbacks` and `replan_triggers`.

### II.2 Evidence is a first-class object

For any strategy that makes factual claims:
- Evidence SHALL be tracked as structured objects (`EvidenceItem`) with provenance (source ID, span/quote, timestamp, trust tier).
- Claims SHOULD be linked to evidence (`Claim → Evidence[]`) rather than appended as ad-hoc citations.

### II.3 Explicit uncertainty and confidence signals

Strategies SHOULD emit explicit uncertainty signals in a structured way (e.g., `confidence: low|med|high`, `needs_more_info: true/false`, `blocking_questions[]`).  
Do not bury uncertainty inside prose.

---

## Article III: Grounding strategy (RAG is not a religion)

### III.1 Use a reliability gradient for grounding choices

Strategies SHOULD choose grounding methods using a reliability gradient:

1. **Deterministic tools/DB queries** (highest correctness; easiest verification)
2. **Cache-Augmented Generation (CAG)/long-context on bounded corpora** (eliminates retrieval selection errors when feasible)
3. **GraphRAG / structured retrieval** for interconnected corpora [6][7]
4. **Adaptive retrieval (Self-RAG-style)** when retrieval necessity varies [5]
5. **Vanilla RAG** as the lowest-reliability default (fastest to build; easiest to get subtly wrong)

This gradient is a *design heuristic*; the kernel still enforces untrusted-content discipline.

### III.2 Grounding is a decision, not an implementation detail

The strategy SHOULD make grounding decisions explicit:
- “Do we need retrieval?”
- “What source(s) are authoritative?”
- “Do we need multi-hop context?”
- “Do we have sufficient evidence to answer?”

### III.3 Contradictions and missing evidence are handled explicitly

If sources conflict or evidence is insufficient:
- the strategy SHOULD surface the conflict,
- propose additional retrieval/tool steps,
- or escalate (human review) rather than fabricating.

### III.4 Agentic context construction is a first-class pattern

For complex research/synthesis tasks across large corpora or the open web, strategies MAY implement **agentic context construction**:
- iteratively search/browse/read,
- discard low-value context,
- follow links,
- build a curated working set.

This pattern is powerful but must stay budgeted and injection-aware.

---

## Article IV: Planning and control loop standards

### IV.1 Control loops are chosen deliberately

Strategies SHALL select a control loop pattern appropriate to task/risk:

- **ReAct** for tight tool–observe–reason loops [1]
- **Plan-and-execute** for tasks needing explicit decomposition and progress tracking
- **Plan–act–reflect** when revision is common (coding, complex synthesis)
- **Router–executor (MRKL)** when many specialized skills/tools exist [3]
- **Map–reduce / parallel workers** when processing large sets or avoiding “context fatigue”
- **Search-based deliberation** (best-of-N, tree search) when mistakes are costly and verifiers exist [4]

### IV.2 Plans include stop conditions and replan triggers

Plans SHOULD include:
- explicit stop conditions,
- replan triggers (tool failure, evidence insufficiency, budget pressure),
- maximum retries per step (avoid thrash),
- alternative routes (tool B if tool A fails).

### IV.3 Reflection and critique loops are bounded and rubric-driven

If the strategy uses critique:
- critique MUST be tied to a rubric (correctness, groundedness, policy constraints, clarity),
- revision MUST be bounded (max iterations / budget),
- the strategy MUST avoid “critic rubber-stamping” by requiring concrete reject reasons.

Reflexion-style episodic feedback is a useful pattern, but still needs boundedness and governance [2].

---

## Article V: Search, sampling, and test-time compute (SOTA reasoning)

### V.1 Test-time compute is a controllable knob, not a miracle

Strategies MAY invest additional test-time compute (more thinking, sampling, search) to improve success, but SHALL:

- allocate compute proportional to stakes and uncertainty,
- respect explicit compute budgets,
- record compute choices in trace metadata for analysis.

OpenAI’s reasoning research explicitly frames performance improvements with more “thinking” (test-time compute) and more RL (train-time compute) [8].

### V.2 Best-of-N is for *decisions*, not for prose

If generating multiple candidates:
- sample **plans/tool args/queries**, not just alternative explanations,
- rank with verifiers (deterministic preferred),
- keep N adaptive (uncertainty/risk-driven).

### V.3 Tree/graph search requires verifiable scoring

Tree-of-Thought style search can help on problems requiring exploration, but only when you have:
- a meaningful step scoring function (verifier, heuristic, reward model),
- bounded branching and depth,
- pruning/backtracking rules [4].

---

## Article VI: Memory and context management (brain hygiene)

### VI.1 Layered memory is standard

Strategies SHOULD treat memory as layers:
- **Working memory** (per-run scratch, summaries, plan status)
- **Task memory** (durable, validated: decisions, outputs, open TODOs)
- **Long-term memory** (durable, heavily curated: user preferences, stable facts)

### VI.2 Writes are deliberate and minimal

Memory writes SHOULD:
- store structured summaries rather than raw untrusted text,
- include provenance and confidence,
- include TTL/expiry semantics where appropriate,
- be gated by “worth remembering?” heuristics (avoid junk accumulation).

### VI.3 Retrieval is governed (no memory spam)

Memory retrieval SHOULD:
- be trigger-based (only when needed),
- de-duplicate near-identical items,
- avoid polluting prompts with low-value context,
- surface provenance and suspicion flags.

---

## Article VII: Tool-use cognition (how to act without flailing)

### VII.1 Tool selection is a structured decision

Strategies SHOULD treat tool selection as a classification/planning problem:
- identify required capabilities,
- choose the minimal tool that provides authoritative data,
- generate arguments with explicit assumptions.

### VII.2 Tool calls include expected observations

For each proposed tool call, strategies SHOULD attach:
- expected output shape,
- expected values/ranges (when known),
- how the result will change the plan.

This improves debuggability and reduces “random walk” behavior.

### VII.3 Error-aware action selection

Strategies SHALL use the tool error taxonomy (retryable vs permanent) to choose:
- retry (bounded),
- alternative tool/path,
- replan,
- or escalation.

---

## Article VIII: Hierarchical and multi-agent cognition

### VIII.1 Multi-agent is a scaling tool, not a default

Multi-agent/hierarchical decomposition SHOULD be used when:
- tasks naturally factor into independent subproblems,
- parallelism increases quality (large lists, broad research),
- or isolation prevents error propagation.

Otherwise, it often increases cost and coordination failures.

### VIII.2 Contracts between agents are typed

If using multiple agents:
- every sub-agent MUST have a typed input/output contract,
- workers MUST have narrow tool access (least capability),
- supervisors MUST verify/aggregate outputs deterministically where possible.

### VIII.3 Shared-nothing by default

Workers SHOULD operate in isolated contexts; supervisors merge results using a deterministic aggregation strategy to avoid compounding hallucinations.

---

## Article IX: Model roles, routing, and specialization

### IX.1 Role-based models are normal in production

Strategies SHOULD support multiple model roles:
- router/classifier,
- planner,
- executor (tool args),
- critic/judge,
- summarizer,
- safety/policy assistant (defense-in-depth).

Anthropic guidance emphasizes simple, composable patterns and evaluation-driven improvements for agents [9][10].

### IX.2 Routing policies are explicit and testable

Routing rules SHOULD be:
- encoded as data/config (not hidden in prompts),
- covered by unit tests and eval scenarios,
- measurable (router accuracy, cost savings, failure rates).

---

## Article X: Learning loops (prompt optimization, SFT, RL)

### X.1 Evals drive learning, not intuition

Any improvement method (prompt tuning, compiled prompts, SFT, RL) SHALL be tied to:
- a versioned evaluation suite,
- stable rubrics,
- regression gates.

### X.2 Verifiers are the reward function

For RL or any search-based optimization, verifiers/judges define reward.  
Weak verifiers → reward hacking → broken agents.

GRPO-style RL optimizers are an example of practical post-training methods used for reasoning improvements in open literature [11][12].

### X.3 Training data governance

Training datasets derived from traces SHOULD:
- be sanitized/redacted,
- be versioned and reproducible,
- include negative examples and near-misses,
- be tied to exact schema/tool versions used to generate them.

---

## Article XI: Evaluation and quality gates for strategy changes

### XI.1 Strategy is shipped behind gates

A strategy version SHALL NOT be promoted without:
- passing offline regression suites,
- meeting budget/cost SLOs,
- meeting grounding/citation requirements (when applicable),
- passing adversarial / injection suites appropriate to its tools and data sources.

### XI.2 Telemetry informs next iteration

Strategies SHOULD emit structured telemetry for:
- plan success/failure reasons,
- tool call correctness (wrong tool/args),
- retrieval effectiveness (precision/recall proxies),
- budget exhaustion,
- escalation rate,
- critic agreement/disagreement.

---

## Appendix A: Minimal required artifacts for any serious strategy

A production strategy SHOULD have, at minimum:

1. **Intent ABI schemas** (versioned)
2. **Plan IR** (even if only for debugging)
3. **Evidence objects** (if making factual claims)
4. **Rubrics** for critique/verification (versioned)
5. **Golden eval suite** + adversarial pack (versioned)
6. **Routing policy** (if multiple roles/models) with tests
7. **Memory write policy** (if memory exists) with TTL/provenance rules

---

## Appendix B: Reference links

[1]: https://arxiv.org/abs/2210.03629  "ReAct: Synergizing Reasoning and Acting in Language Models"  
[2]: https://arxiv.org/abs/2303.11366  "Reflexion: Language Agents with Verbal Reinforcement Learning"  
[3]: https://arxiv.org/abs/2205.00445  "MRKL Systems"  
[4]: https://arxiv.org/abs/2305.10601  "Tree of Thoughts"  
[5]: https://arxiv.org/abs/2310.11511  "Self-RAG"  
[6]: https://arxiv.org/abs/2404.16130  "GraphRAG paper"  
[7]: https://www.microsoft.com/en-us/research/project/graphrag/  "Microsoft Research: GraphRAG"  
[8]: https://openai.com/index/learning-to-reason-with-llms/  "OpenAI: Learning to reason with LLMs"  
[9]: https://www.anthropic.com/research/building-effective-agents  "Anthropic: Building Effective AI Agents"  
[10]: https://www.anthropic.com/engineering/writing-tools-for-agents  "Anthropic: Writing tools for agents"  
[11]: https://arxiv.org/abs/2402.03300  "DeepSeekMath (introduces GRPO)"  
[12]: https://arxiv.org/abs/2505.22257  "Revisiting GRPO"  
