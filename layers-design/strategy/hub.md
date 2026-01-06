# “Agentic Systems Foundations” Hub 

---

# Program Overview

**Courses**

1. **Specialization A:** Structured LLM I/O & Tool Schema Engineering
2. **Specialization B:** RAG & Tooling for Agentic Systems
3. **Specialization C:** Agent State Machines, Planning & Hierarchical Agents
4. **Specialization D:** Memory, Long-Term Context & Durable State
5. **Specialization E:** Guardrails, Safety, Security & Governance
6. **Specialization F:** Evaluation, Testing, Observability & Experimentation
7. **Specialization G:** Performance, Scaling & Agent Infrastructure
8. **Specialization H:** Model Selection, Customization & Multi‑Model Systems
9. **Specialization I:** UX, Human-in-the-Loop & Productizing Agents
10. **Specialization J:** Agent Architecture Patterns & Control Loop Catalog
11. **Specialization K:** Neurosymbolic Reasoning, Solvers & Formal Guarantees
12. **Specialization L:** KnowledgeOps: Corpus Engineering, Provenance & Data Lifecycle
13. **Specialization M:** Agent Runtime & Framework Engineering (Build Your Own "LangGraph-ish")
14. **Specialization N:** Standards, Interoperability & Packaging (So You're Not Trapped in One Stack)
15. **Specialization O:** Domain Blueprints & Reference Implementations
16. **Specialization P:** Simulation, Sandboxes & Synthetic Environments for Agents

---

# Specializations

---

## Specialization A – Structured LLM I/O & Tool Schema Engineering

**Goal:** Master schemas, JSON mode, sampling, streaming, and all the gnarly details of “LLM behaves like a structured function caller.”

**Modules**

1. **Schema Design & Tool Semantics**

   * Typed tools with Pydantic/dataclasses.
   * Required vs optional, enums, nested types.
   * Clear side-effect semantics (idempotent vs not).
   * Dangerous tools tagging & metadata for policies.

2. **Robust Structured Generation**

   * JSON mode / function calling / `response_format`.
   * Prompt patterns: explicit schemas, examples, “if unsure then …”.
   * Validation + auto-retry loops; capturing raw outputs for debugging.
   * Handling malformed JSON / half-output scenarios.

3. **Sampling, Streaming & Token Economics**

   * Tokenization basics; programmatic token counting.
   * Temperature, top_p, frequency/repetition penalties and how they impact:

     * Schema adherence
     * Creativity
   * Streaming responses vs full responses; handling partials.
   * Designing `max_tokens` and stop sequences for structured outputs.

4. **Multimodal Structured I/O (Optional)**

   * Treating vision/audio models as tools.
   * Schemas for image analysis, file classification, etc.

5. **Constrained Decoding & Grammars**

  * JSON grammar / regex / EBNF constraints; when they help and when they hide bugs.
  * Partial parsing and incremental validation during streaming.

6. **Schema Evolution & Compatibility**

  * Versioned tool schemas, migrations, deprecation, and “accept old + new” patterns.
  * Canonical serialization (sorted keys, stable formatting) to improve caching and determinism.

7. **Tool Output Normalization**

  * Normalize tool responses into typed domain objects.
  * Distinguish “tool returned error” vs “agent mis-called tool” vs “environment failed”.

8. **Provider Divergence**

  * Designing one schema intent across different function-calling implementations.
  * Feature detection and graceful degradation strategies.

> Covers & deepens: everything in **Module 1** of the main course, and sets up the model-configuration work expanded in **Specialization H**.


---

## Specialization B – RAG & Tooling for Agentic Systems

**Goal:** Make RAG and tools feel like clean, reliable system boundaries.

**Modules**

1. **RAG Fundamentals & Structural Failure Modes**

   * Traditional pipeline: chunking strategies, embeddings, BM25 vs vector retrieval.
   * Index design, metadata filtering, retrieval hyperparameters (k, similarity thresholds).
   * **Structural limitations of vanilla RAG:**
     * Approximate retrieval: semantic similarity ≠ entailment; embeddings are lossy.
     * Chunk boundary pathology: facts split across chunks, decontextualized snippets.
     * Model misuse of evidence: ignoring, distorting, or hallucinating despite correct chunks.
     * Security: retrieved text as untrusted input (indirect prompt injection risk).
   * **When RAG is the wrong choice**: decision framework for structured vs unstructured knowledge.

2. **Beyond Vanilla RAG: Modern Grounding Strategies**

   * **Cache-Augmented Generation (CAG)**: when corpus is bounded (course materials, APIs, policy docs).
     * Preload entire corpus into context once, reuse KV cache across queries.
     * Eliminates retrieval selection errors entirely; corpus as versioned, compiled artifact.
     * Tradeoffs: corpus size limits, cache regeneration on updates, model errors remain.
     * Killer use cases: syllabi, rubrics, certification handbooks, API documentation.
   
   * **DB/Tool-Grounded Systems**: replacing fuzzy text retrieval with authoritative structured queries.
     * SQL databases (grades, deadlines, rosters), knowledge graphs, rule engines, symbolic tools.
     * LLM as translator/controller: question → structured query → execute → present.
     * Provable correctness through schemas, constraints, deterministic computation.
     * Educational gold: "What's my grade?", "What's due?", "Why did tests fail?" → structured, not retrieved.
   
   * **GraphRAG**: graph-structured summaries for interconnected, narrative corpora.
     * Entity extraction, relationship graphs, community detection, multi-hop reasoning.
     * Retrieves connected context, not just top-k similar chunks.
     * Use cases: institutional policies, procedural knowledge, messy interconnected documents.
     * Limitations: still text-based, inherits injection risks and extraction errors.
   
   * **Self-RAG & Adaptive Retrieval**: retrieve-generate-critique loops.
     * Agent decides when to retrieve vs rely on internal knowledge.
     * Self-verification of retrieved evidence relevance and sufficiency.
     * Reducing unsupported answers through explicit critique nodes.
   
   * **Reliability gradient & decision framework:**
     * Tier 1: Deterministic tools/DB queries (highest correctness guarantees).
     * Tier 2: CAG for static, bounded text corpora (eliminates retrieval errors).
     * Tier 3: GraphRAG/structured retrieval for complex unstructured corpora.
     * Tier 4: Vanilla RAG (fastest to build, easiest to get wrong).
     * Orthogonal: verification (tests, solvers, cross-checks) tolerates upstream fuzz.
   
   * **Agentic Context Construction**: dynamic, tool-driven grounding (the Manus approach).
     * Beyond static retrieval (RAG) and full-corpus loading (CAG): agent as active researcher.
     * Process: small initial context → tool-based search/browse → read & evaluate → discard useless / keep relevant → follow links → iterate.
     * The agent builds its own context intelligently based on what it learns, not blind math or bulk loading.
     * Ties together: filesystem-as-memory (Spec D), tool orchestration, CodeAct (Spec B), state machines (Spec C).
     * Use cases: complex research tasks, interconnected knowledge bases requiring synthesis, exploratory analysis.
     * Tradeoffs: requires full agentic capabilities (tools, planning, state), multiple LLM calls, but scales better than CAG and achieves higher accuracy than RAG for complex queries.
   
   * **The Three-Way Decision Framework:**
     * **Use CAG** when: corpus is bounded, mostly static, fits in context window (syllabi, rubrics, API docs, certification handbooks).
     * **Use RAG** when: corpus is massive (TB+), individual queries are simple/isolated (FAQ lookup, basic keyword search).
     * **Use Agentic Context** when: corpus is large but interconnected, task requires synthesis across distant sources, or highest accuracy is required and agent infrastructure is available.

3. **RAG as a First-Class Tool (Implementation Patterns)**

   * API design: `search_docs(query, k) -> [DocumentHit]`.
   * DocumentHit schema: `id`, `snippet`, `score`, `source`, `metadata`.
   * Structured integration into AgentState (not just appending text).
   * Adaptive retrieval: agent decides when/whether to call search_docs.
   * Evidence tracking and citation: linking generated text back to source documents.

4. **Tool Layer Design**

   * Wrappers with input validation and idempotency.
   * Structured errors (`TransientError`, `PermanentError`, `ValidationError`).
   * Read vs write tools, logging & observability hooks.

5. **CodeAct: Code as the Universal Action Interface**

   * Beyond JSON function calling: using Python/Bash as the primary action language.
   * Expressiveness advantages: loops, conditionals, exception handling in single execution.
   * Self-correction through traceback feedback: agent sees and fixes errors directly.
   * Consolidating tool libraries: using pandas/numpy/requests instead of hundreds of tiny specialized tools.
   * Complex workflows without round-trip latency: multi-step scripts executed atomically.
   * Tradeoffs: security considerations (code injection), sandboxing requirements, debugging complexity.
   * When to use CodeAct vs structured function calls: task complexity, environment capabilities, safety requirements.

6. **Tool Orchestration, Concurrency & Caching**

   * Tool registry/manifest with latency, permissions, categories.
   * Running tools in parallel vs serial order; when to choose which.
   * Timeouts, retries, backoff, rate-limiting.
   * Tool result caching and invalidation strategies.

7. **Model Context Protocol (MCP) & Tool Standardization**

   * MCP as an emerging standard for agent-tool integration (client-server architecture).
   * Resources, Tools, and Prompts as first-class MCP primitives.
   * Security benefits: credential isolation (OAuth flows handled by MCP server, not agent context).
   * Practical MCP server implementation: exposing Google Drive, Slack, GitHub, etc.
   * Connector patterns and lifecycle management for external integrations.

8. **Security for Tools & RAG**

   * Avoiding injection into shell/SQL/HTTP.
   * Treating retrieved content as untrusted: no instruction-following.
   * Guardrails around URL fetchers, internal resources.

9. **Hybrid Retrieval & Reranking**

  * BM25 + vectors + reranker as the *default* reliability baseline.
  * Query rewriting and multi-query retrieval (diversity retrieval).

10. **Evidence Discipline**

  * Claim–evidence linking as structured objects (not just “append citations”).
  * Quote extraction + span-level provenance.

11. **Corpus Engineering Hooks**

  * Crosslink to Spec M: ingestion quality, doc linting, drift detection.

12. **Context Assembly as a First-Class Program**

  * “Context compiler”: build context from tool outputs + memory + retrieved evidence with explicit rules.


> Deepens: main course Modules 2, 10, and the RAG & tool security bits from the safety modules.

---

## Specialization C – Agent State Machines, Planning & Hierarchical Agents

**Goal:** Turn “agent” into a well-typed, testable program with explicit plans and hierarchies.

**Modules**

1. **Typed Agent State Machines**

   * AgentState schema and persistence constraints.
   * Enumerating states and node types.
   * Dispatcher patterns and deterministic routing.

2. **Graph Design & State Invariants**

   * Graph representations (adjacency maps, DSLs, etc.).
   * Explicit transitions, allowed-next-state tables.
   * State invariants and property-based tests for transitions.

3. **Plan-Then-Act Patterns**

   * Structured plan schemas (steps, tools, dependencies).
   * Turning plans into graph fragments.
   * Plan repair nodes + re-planning strategies.

4. **Agent Pattern Families**

   * Chain-of-thought vs plan-and-execute vs plan–act–reflect.
   * When hierarchical decomposition makes sense.

5. **Hierarchical & Multi-Agent Systems**

   * Supervisor/worker patterns.
   * Contracts between agents (schemas + success criteria).
   * Narrow toolsets for workers; verifying worker outputs.

6. **Parallel Agent Orchestration (Map-Reduce Patterns)**

   * The "Fabrication Threshold" problem: quality degradation in sequential processing of large lists.
   * Map-Reduce architecture for agents: decompose task → spawn isolated sub-agents → aggregate results.
   * Shared-nothing execution: each sub-agent gets fresh context, preventing error propagation and "context fatigue".
   * Use cases: research tasks (analyze 100 companies), batch processing, competitive analysis.
   * Tradeoffs: increased token cost vs linear quality scaling and true parallelism.

7. **Reflection & Critique**

   * Worker → critic → revised output loops.
   * Critic prompts and rubrics (quality, correctness, policy).

8. **Inference-Time Reasoning & Search Strategies**

   * **The "Thinking" Paradigm (Test-Time Compute)**
     * Moving beyond immediate tool calls: forcing "latent reasoning" steps before action.
     * Structuring the `<think>` block: implementing explicit reflection patterns before emitting JSON.
     * Compute Budgeting: Trading latency for accuracy by scaling the number of reasoning tokens generated.
     * Reasoning tokens: internal monologue not shown to user, enabling explicit "thinking" traces (o1/R1-style).
   
   * **Search-Based Policy Improvement**
     * **Best-of-N (Rejection Sampling)**: Generate $N$ plans/tool-calls, use a lightweight verifier or reward model to pick the best one.
     * **Tree Search (MCTS/BFS)**: Implementing "lookahead" where the agent simulates tool execution steps (in a sandbox) to value a path before committing.
     * Monte Carlo Tree Search (MCTS) for agent decision-making: simulation, backpropagation, policy refinement.
     * **Self-Correction Loops**: Detecting "stuck" states and pruning that branch of the reasoning tree.
     * Self-verification and backtracking: detecting errors in reasoning and rewinding to earlier decision points.
   
   * **Practical Implementation Patterns**
     * Pseudocode as intermediate representation: structured thinking before final code generation.
     * Sandbox execution for safe tool simulation during lookahead.
     * Balancing compute budget vs task complexity: when to invest in search vs direct execution.
     * Applications: complex coding tasks, mathematical reasoning, multi-step planning, strategy optimization.

8. **Reactive / Event-Driven Agents**

  * Event bus patterns: tool completion events, user interrupts, external triggers.
  * Interruptible plans and resumable nodes.

9. **Formal Planning Interfaces**

  * PDDL/HTN planner as a tool; feasibility checks before execution.

10. **Scheduling & Resource-Aware Planning**

  * Plans that incorporate budgets (tokens, time, money, tool quotas).
  * Multi-objective planning: accuracy vs cost vs latency.

> Deepens: main course Modules 3 & 4 + related planning content from the full curriculum.

---

## Specialization D – Memory, Long-Term Context & Durable State

**Goal:** Teach the agent to remember what matters, forget what doesn’t, and not blow the context window.

**Modules**

1. **Context Window Management**

   * Rolling windows; sliding-window strategies.
   * Running summaries structured as objects.

2. **Layered Memory Architectures**

   * Conversation summary, key facts/entities table, open tasks/TODO list, world state.
   * Designing schemas and update rules.

3. **Long-Term Memory Systems**

   * Vector stores vs key-value vs relational stores.
   * Recall policies: triggers, k selection, scoring, and merging into prompts.

4. **User Identity & Persona**

   * Modelling user preferences, constraints, and long-term contracts.
   * Permissions logic (“auto-approve X under conditions Y”).

5. **Forgetting & Privacy**

   * Deletion/forgetting flows.
   * Tombstoning and de-indexing RAG content.
   * Interaction with regulatory/compliance concerns.

6. **Advanced Context Engineering & Cache Optimization**

   * KV-Cache mechanics in Transformers: why prefix stability matters for cost and latency.
   * Static prefix patterns: placing variable data (timestamps, user location) at the end to maximize cache hits.
   * Deterministic serialization: ensuring identical state produces identical token sequences (sorted JSON keys).
   * Logits masking: dynamically constraining model outputs (e.g., available tools) without modifying context.
   * Recitation mechanisms: forcing the model to regenerate summaries/plans to "refresh" attention and prevent drift.
   * Filesystem-as-memory: offloading large data to files, feeding only paths/metadata to context.
   * Economic implications: cache-aware design can reduce costs by 10-100x in long-running sessions.

7. **Durable State & Long-Running Workflows**

   * Persisting AgentState with versioning.
   * Combining memory with durable workflows (ties into long-running agents).

8. **Memory Consolidation**

  * Episodic vs semantic memory and consolidation policies.
  * “Promote to long-term memory” triggers and confidence thresholds.

9. **Memory Poisoning & Safety**

  * Detect adversarial/incorrect memories; quarantine + review.
  * Provenance tags on memories: who/what created them and when.

10. **Preference Learning**

  * Bandit-style preference adaptation (with guardrails) vs static user profiles.

> Deepens: main course Modules 5 & 7 plus memory/compliance aspects from the safety modules.

---

## Specialization E – Guardrails, Safety, Security & Governance

**Goal:** Make agents safe to hook up to real systems and real users.

**Modules**

1. **Guardrails as Graph Edges**

   * Policy check nodes: inspect tool, args, identity, risk.
   * Returning: continue / human approval / refuse.

2. **Tool Loops & Failure Recovery**

   * Loop detection via `(tool_name, args_hash)` history.
   * Strategies to avoid infinite “retry the same broken call”.
   * Forcing plan changes or alternative tools.

3. **Self-Checks & Safety Models**

   * Self-check prompts for restating goals and evidence.
   * `confident` / `need_more_info` / `refuse` decisions.
   * Separate safety/policy models and classifiers.

4. **Prompt Injection & Data Exfiltration**

   * Direct vs indirect prompt injection.
   * RAG-specific risks: untrusted instructions embedded in docs.
   * Defences: content filters, strict separation of “data vs instructions”.

5. **Threat Modeling**

   * Malicious users, compromised tools, adversarial model outputs.
   * Concrete attacks like SSRF with URL tools, cross-tenant leaks.

6. **Refusal, Escalation & Governance**

   * Refusal patterns: clarity without oversharing.
   * Human review queues and escalation paths.
   * Least privilege, role-based access, approvals for adding write tools.

7. **Privacy & Compliance**

   * PII handling, redaction/masking, prompt-scoping.
   * Logging and retention; “right to be forgotten”.

8. **Secrets & Credential Hygiene**

  * Secret zero, token scoping, never putting credentials in model context.
  * Capability-based tool access: least privilege as code.

9. **Sandboxing & Dry Runs**

  * Safe simulation modes for side-effecting tools.
  * “Propose → preview diff → approve → execute” as a standard pattern.

10. **Red Teaming as Curriculum**

  * Build an internal library of adversarial prompts/docs and test continuously (ties to Spec F + P).


> Deepens: main course Module 6 + 9 and the safety-related bits from tooling & RAG.

---

## Specialization F – Evaluation, Testing, Observability & Experimentation

**Goal:** Build the measurement machinery around agents – offline, online, human, automatic.

**Modules**

1. **Logging & Tracing**

   * Structured logs, trace IDs, node-level telemetry.
   * Building trace graphs from node transitions.

2. **Workflow-Level Test Harnesses**

   * Fixtures with mock tools and initial states.
   * Expected terminal states / side-effects.
   * Monte Carlo / fuzz tests with noisy LLM outputs and tool failures.

3. **Comparative Grounding Strategy Evaluation ("Needle in Haystack" Lab)**

   * **Goal**: Empirically compare RAG vs CAG vs Agentic Context Construction on real-world tasks.
   * **Dataset**: Medium-to-large corpus (codebase, course materials, policy documents).
   * **Test design**: Questions requiring synthesis across distant sections (cross-module understanding, multi-hop reasoning).
   * **Three approaches:**
     * **Task A (Vanilla RAG)**: Use vector retrieval (LangChain + embeddings) to answer cross-document questions.
       * Expected result: Often fails or gives generic answers when relevant chunks don't share keywords.
     * **Task B (CAG/Long Context)**: Load entire corpus into long-context model (Gemini 1.5, Claude 3.5).
       * Expected result: Usually succeeds due to global understanding, finds "needles" consistently.
     * **Task C (Agentic Context)**: Use autonomous agent (Manus, custom agentic system) to dynamically construct context.
       * Expected result: Most grounded answer, may run verification scripts or follow dependency chains.
   * **Metrics**: Accuracy, cost (tokens), latency, citation quality, handling of edge cases.
   * **Learning outcomes**: Students understand cost-accuracy-scale tradeoffs, learn when each approach is appropriate.

4. **Failure Taxonomies & Metrics**

   * Taxonomy of agent failures (wrong tool, wrong args, non-halting, safety, loops).
   * Quantitative metrics and dashboards.

4. **Time-Travel Debugging**

   * Checkpoints after each node.
   * Replay from step N with original or modified configs.

5. **Offline Evaluation**

   * Golden datasets for key workflows.
   * LLM-as-judge and scoring strategies.

6. **Online Evaluation & AB Testing**

   * User signals and task-completion metrics.
   * AB testing prompts, graphs, and tools.
   * Basic statistics and experiment interpretation.

7. **Human-in-the-Loop Evaluation**

   * Designing rubrics.
   * Labeling tools and workflows for raters.

8. **Prompt Optimization & DSPy-Style “Compiled” Prompts**

**Goal:** Show how to move from hand-crafted prompts to *programmatically optimized* prompt/agent configurations, using something like DSPy.

* **Conceptual model: compiled prompts**

  * Prompts and system instructions as “parameters” learned from data/evals.
  * Contrast:

    * “Write the prompt by hand.”
    * vs “Define an objective and let a framework search for prompts/weights.”

* **DSPy / prompt optimization frameworks (practical intro)**

  * High-level DSPy ideas:

    * Declarative pipelines: you specify *what* the pipeline should do, not *exactly how to prompt* each step.
    * Objective functions: accuracy, helpfulness, tool-calling correctness.
    * Optimizers: gradient-free search, bandits, etc. (explained at engineer level, not math-paper level).
  * Mapping your agent:

    * Identify key modules (e.g., planner prompt, summarizer prompt, tool-selection prompt).
    * Wrap them as components in a DSPy-style program.

* **Integrating with your eval harness**

  * Use the golden tasks from earlier modules as the optimization objective.
  * Run:

    * Compile/optimize cycle over your eval set.
    * Compare pre- and post-optimization metrics.
  * Keep:

    * Snapshots of prompt/graph versions so you can roll back.

* **Safeguards when optimizing prompts**

  * Ensure:

    * Safety constraints aren’t violated during optimization.
    * You keep human-readable artifacts (no “magic binary prompt” no one understands).
  * Treat optimized prompts as versioned artifacts in CI/CD.

9. **Reward Modeling & Verifiers**

**Goal:** Build the reward infrastructure required for RL-based agent alignment. Without robust verifiers, you cannot do RL for general agent tasks.

* **Outcome-Based Rewards (ORM)**

  * Binary success metrics: "Did the unit tests pass?" "Did the file exist?" "Did the API return 200?"
  * Hard-coding verifiable outcomes for coding/data agents.
  * Advantages: objective, deterministic, no model needed.
  * Limitations: only works for tasks with executable validation.

* **Process-Based Rewards (PRM)**

  * Scoring the reasoning steps, not just the final answer.
  * Using a stronger model (e.g., GPT-4o) to grade the traces of a smaller model (e.g., Llama-8B) to create a dataset.
  * Annotating intermediate steps: which reasoning chains lead to correct vs incorrect outcomes.
  * Advantages: catches errors in reasoning early, provides richer training signal.
  * Challenges: requires step-level labels, expensive to generate at scale.

* **Training a Verifier**

  * Distilling the "Judge" into a small, fast classifier.
  * Dataset construction: collect (trajectory, outcome) pairs from agent executions.
  * Architecture choices: sequence classifiers, reward towers, fine-tuned embedding models.
  * Using the Verifier to guide search (Module 8 of Spec C) rather than just for final eval.

* **Verifiers in the Agent Loop**

  * Integration patterns: post-tool verification, pre-commit approval, best-of-N selection.
  * Failure handling: what to do when the verifier rejects all candidates.
  * Human escalation: when automated verification is insufficient.

* **Cross-Reference to Specialization H**

  * Verifiers are the reward function for RL (see Spec H Module 7).
  * The quality of your RL agent is bottlenecked by the quality of your verifier.

7. **Benchmark Suites & Scenario Sims**

  * Task suites by domain blueprint (Spec R).
  * Tool-failure chaos tests: latency spikes, partial outages, malformed responses.

8. **Eval Data Management**

  * Versioned eval datasets aligned to schema/tool versions.
  * Regression gates in CI/CD: “no deploy without passing golden tasks.”

9. **Judge Calibration**

  * LLM-as-judge reliability: inter-rater agreement, spot-checking, and adversarial judge tests.

> Deepens: main course **Module 8** and connects directly to model/experiment choices in **Specialization H**.


---

## Specialization G – Performance, Scaling & Agent Infrastructure

**Goal:** Get agents off your laptop and onto infra that doesn’t catch fire.

**Modules**

1. **Token, Latency & Cost Budgets**

   * Per-step and per-workflow budgets.
   * Understanding cost drivers.

2. **Throughput & Concurrency**

   * Handling multiple users/agents in parallel.
   * Fan-out/fan-in patterns for tools and models.
   * Avoiding bottlenecks and contention.

3. **Job Orchestration & Long-Running Work**

   * Queues, workers, schedulers.
   * At-least-once vs exactly-once semantics.
   * Handling retries and backpressure.

4. **Caching Strategies**

   * Response caching, semantic caching, tool result caching.
   * Cache invalidation, TTLs, and consistency.

5. **Rate Limiting & Quotas**

   * Handling LLM and API provider limits.
   * Degrading gracefully under pressure.

6. **Deployment & Runtime Concerns**

   * Containerization, scaling up/down.
   * Integrating traces and logs with existing observability stacks.

7. **Multi-Tenancy & Isolation**

  * Per-tenant quotas, isolation boundaries, noisy-neighbor mitigation.
  * Data-plane vs control-plane separation for tool execution.

8. **Load Shedding & Degradation**

  * “Good-enough mode”: fewer steps, cheaper model, less retrieval under load.

9. **Artifact Stores**

  * Store large intermediate artifacts (files, tables, traces) as first-class outputs.


> Deepens: main course Modules 7, 8, 9 + performance parts of the full curriculum.

---

## Specialization H – Model Selection, Fine-Tuning & Agent Alignment

**Goal:** Choose and tune the models powering your agent system. Master supervised fine-tuning (SFT) and reinforcement learning (RL) for agent-specific alignment.

**Modules**

1. **Roles & Model Capabilities**

   * Assigning models to roles: router, planner, critic, generator, safety.
   * Capability, latency, and cost tradeoffs.

2. **Provider & Version Abstractions**

   * Designing a pluggable LLM interface.
   * Handling versions across providers.

3. **Per-Node Model Configuration**

   * Node-specific hyperparameters (temp, top_p, max_tokens).
   * Consistency vs diversity tradeoffs.

4. **Fine-Tuning Fundamentals & LoRA**

   * When prompts are not enough: limits of in-context learning.
   * Dataset design for schema adherence, domain style, and tool-calling behavior.
   * LoRA (Low-Rank Adaptation): efficient fine-tuning without full parameter updates.
   * Training infrastructure: compute requirements, dataset size considerations.
   * Evaluation: measuring improvement on held-out agent tasks vs general capability degradation.

5. **Supervised Fine-Tuning (SFT) for Agents**

**Goal:** Move beyond generic LLM fine-tuning to agent-specific training patterns.

   * **Format Formatting**

     * Tuning models specifically to output your strict JSON schema or tool tokens.
     * Skipping the "chat" fluff: training for direct, structured responses.
     * Eliminating preambles, apologies, and verbose explanations in tool-calling contexts.
     * Dataset creation: filtering successful agent traces for strict format adherence.

   * **Cold Start Problem: Expert Iteration**

     * Bootstrapping agent capability when you don't have training data yet.
     * Process: Prompt a smart model (GPT-4o, Claude) to solve tasks → filter for success → SFT a smaller model on those traces.
     * Iterative improvement: use the fine-tuned model to generate more data, repeat.
     * Advantages: creates a task-specific model without manual labeling.
     * Challenges: quality filtering, avoiding distribution collapse.

   * **Thought Distillation**

     * Distilling the "hidden thoughts" (CoT) of reasoning models (o1/R1) into smaller, faster agent models.
     * Training on reasoning traces: model learns to generate internal monologue before tool calls.
     * Preserving reasoning quality while reducing latency and cost.
     * Techniques: curriculum learning (short to long chains), filtering for high-quality reasoning.

   * **Agent-Specific Dataset Construction**

     * Trajectory collection: logging successful agent executions in production.
     * Negative examples: near-misses and failures with corrected versions.
     * Balancing exploration vs exploitation in data collection.
     * Version control for training datasets tied to schema/tool updates.

6. **Reinforcement Learning for Agents**

**Goal:** Train agents to optimize for task success using RL, going beyond supervised learning to handle complex, multi-step reasoning.

   * **The RL Pipeline for Agents**

     * **Environment**: The agent's execution context (tools, APIs, filesystem, databases).
     * **Action Space**: Tool calls + text generation (reasoning tokens, user-facing responses).
     * **Reward**: The output of the verifier (see Spec F Module 9).
       * Sparse rewards: final task success/failure.
       * Dense rewards: intermediate checkpoints, step-level verification.
     * **Policy**: The agent model itself, trained to maximize expected reward.

   * **GRPO (Group Relative Policy Optimization)**

     * Why PPO is often too heavy for agent RL: requires a separate critic/value model, complex implementation.
     * **DeepSeek's GRPO approach**: Sampling a group of outputs, ranking them by reward, optimizing the policy without a value network.
     * Process:
       1. Sample N trajectories from the current policy for each task.
       2. Execute and score each trajectory with the verifier.
       3. Rank trajectories by reward within each group.
       4. Update policy to increase probability of higher-ranked trajectories.
     * Advantages: simpler than PPO, no critic training, works well for discrete rewards.
     * Hyperparameters: group size, temperature, KL penalty to prevent policy collapse.

   * **Reasoning Alignment**

     * Training models how to use the `<think>` block effectively (inference-time reasoning).
     * Rewarding accurate reasoning chains, penalizing hallucinated or circular reasoning.
     * Detecting and penalizing "looping thoughts": repetitive reasoning that doesn't progress.
     * Teaching when to reason vs when to act: balancing compute budget with task complexity.
     * Self-correction training: rewarding trajectories that detect and fix their own errors.

   * **Online vs Offline RL**

     * **Offline RL**: Learning from "gold" trajectories collected beforehand.
       * Advantages: safer, no exploration risk in production.
       * Dataset: expert demonstrations, filtered successful executions.
       * Challenges: distribution mismatch, limited coverage of edge cases.

     * **Online RL**: Learning by interacting with tools and getting feedback in real-time.
       * Exploration in production: agent tries new strategies, learns from failures.
       * Feedback sources: compiler errors, API errors, unit test results, user corrections.
       * Advantages: discovers novel solutions, adapts to changing environments.
       * Risks: potential for failures in production, requires safety guardrails.

     * **Hybrid Approaches**: Start with offline RL on expert data, gradually introduce online learning with safety constraints.

   * **Practical Considerations**

     * Compute requirements: RL is expensive, budget accordingly.
     * Safety during training: sandbox environments, human oversight for critical tasks.
     * Evaluation: measuring generalization to truly novel tasks, avoiding overfitting to training distribution.
     * When RL is worth it vs when SFT + prompt engineering suffices.

7. **Experimentation with Models**

   * Comparing model variants on eval suites.
   * Deciding whether the fix is: model, prompt, graph, or tools.

8. **Mixture-of-Models Routing**

  * Router model chooses: planner vs coder vs critic vs safety model.
  * Learnable routing policies using eval feedback.

9. **Distillation & Compression**

  * Distill expensive agent traces into cheaper operational models.
  * Distill verifiers/judges into small classifiers.

10. **Tool-Use Training Beyond SFT**

  * Train for tool reliability: “choose not to call tool” when uncertain.
  * Reward “ask for clarification” when tool calls would be unsafe.

> Deepens: the model-selection and experimentation themes introduced in **Main Course Modules 1 and 9**, and ties closely to the eval stack in **Specialization F**.


---

## Specialization I – UX, Human-in-the-Loop & Productizing Agents

**Goal:** Make your agent feel like a coherent product instead of a log file with a UI.

**Modules**

1. **User Mental Models**

   * Showing plan/state.
   * Setting expectations: what the agent can/can’t do.

2. **Legibility & Trust**

   * Surfacing sources, evidence, and tool actions.
   * Showing confidence/uncertainty.

3. **Consent & Control**

   * Designing approval flows for side-effecting actions.
   * Undo/rollback where possible.

4. **Human-in-the-Loop Interactions**

   * Review queues, draft edits, human overrides.
   * Integrating human feedback into learning/evals.

5. **Interaction Surfaces**

   * Chat UX vs forms vs dashboards.
   * Notifications, progressive disclosure of complexity.

6. **Closing the Loop with Evals**

   * Using UX telemetry and edits as eval signals.
   * Connecting UX with the evaluation stack (Specialization F).

7. **Legible Action Previews**

  * Show “what I’m about to do” + expected side effects + undo plan.

8. **Conversation Repair**

  * “I got interrupted; here’s where we were” resumability UX.
  * Structured clarification UX: forms instead of back-and-forth chat.

9. **Autonomy Controls**

  * User-tunable autonomy levels: read-only, suggest-only, auto-execute.
  * Trust calibration: show uncertainty and evidence quality, not vibes.

> Deepens: the UX-related content from **Main Course Modules 8–10**, especially the shipping and feedback loops.

## Specialization J – Agent Architecture Patterns & Control Loop Catalog

**Goal:** Build a shared vocabulary of “agent recipes” and know when each one is the right hammer (or the wrong one).

**Modules**

1. **Core Control Loops (The Classics)**

   * **ReAct** (reason → act → observe → repeat) and why observation design matters.
   * **Plan-and-Execute** vs **Plan–Act–Reflect** vs **Act-first** (reactive) loops.
   * **Sense–Model–Plan–Act** style loops (especially for embodied/UI agents).

2. **Router–Executor Architectures**

   * **MRKL-style** routing: classifier/router → specialized executor/toolchain.
   * Mixture-of-prompts / mixture-of-tools: “small router, big specialist” design.
   * Fallback ladders: cheap model → expensive model → human escalation.

3. **Deliberation Patterns**

   * **Best-of-N / Self-consistency** for plans, tool args, and final answers.
   * **Tree/Graph-of-Thought** as *search*, not as “longer text”.
   * Compute budgeting: adaptive N based on uncertainty / stakes.

4. **Critique & Revision Families**

   * **Reflexion-style** memory of mistakes and correction policies.
   * Critic-as-a-service: separate critic model + rubric library.
   * Double-loop learning: “change the plan” vs “change the system prompt”.

5. **Decomposition Patterns**

   * “Outline → fill → verify” for long-form synthesis.
   * Map–reduce and staged aggregation (ties to Spec C).
   * Progressive deepening: quick draft → targeted research → final.

6. **Tool-Use Strategy Patterns**

   * “Tool-first” vs “LLM-first” policies by task type.
   * Tool selection under uncertainty: probe tools, then commit.
   * Multi-tool choreography templates (fetch → parse → compute → present).

7. **Anti-Patterns (How Agents Die)**

   * Infinite loops, “tool thrashing”, premature optimization, over-retrieval.
   * Over-decomposition: 200 subtasks that should’ve been 5.
   * Critic collapse: critic rubber-stamps everything.

8. **Pattern Selection Guides**

   * A decision table: task complexity × tool reliability × time budget × risk.
   * “Minimum viable agent loop” vs “full orchestration” criteria.

> Deepens: Spec C (planning), Spec F (eval), Spec I (UX legibility), Spec E (guardrails).

---


## Specialization K – Neurosymbolic Reasoning, Solvers & Formal Guarantees

**Goal:** Stop pretending everything is best done with fuzzy text generation. Learn when to hand the baton to math, logic, and deterministic checkers.

**Modules**

1. **When to Go Symbolic**

   * “Text is a terrible database.”
   * Identify tasks needing guarantees: scheduling, constraints, compliance rules, proofs, exact arithmetic.

2. **External Solvers as Tools**

   * SAT/SMT (satisfiability / satisfiable modulo theories) patterns for constraints.
   * Constraint programming (CP-SAT style) for scheduling and assignment.
   * Theorem proving (where appropriate) and proof sketch workflows.

3. **Program-of-Thought / Code-as-Reasoning**

   * Generate executable logic (Python) as the reasoning substrate.
   * Intermediate representations: pseudocode → code → tests.
   * Guarded execution: sandbox + timeouts + resource caps.

4. **Formal Planning & Classical Planners**

   * PDDL-like planning (domain + problem) as a tool call.
   * HTN (hierarchical task networks): structured decomposition with guarantees.
   * Using planners for “plan existence” and feasibility checks.

5. **Specification & Invariants**

   * Formal-ish specs: pre/post-conditions, contracts, state invariants.
   * Runtime monitors: assert invariants after each tool call/state transition.
   * Type systems and schema constraints as “lightweight formality.”

6. **Verifier Design Patterns**

   * “Generate → verify → repair” loops with deterministic verifiers.
   * Multi-verifier ensembles: style checker + factual checker + safety checker.
   * Avoiding verifier gaming: adversarial tests and randomized spot checks.

7. **Hybrid Knowledge: Rules + Retrieval**

   * Rule retrieval: fetch rules, then execute deterministically.
   * Knowledge graphs + query languages as authoritative tools.
   * Provenance-preserving reasoning traces.

> Deepens: Spec F (verifiers), Spec B (DB/tool grounding), Spec C (search), Spec E (safety via checks).

---

## Specialization L – KnowledgeOps: Corpus Engineering, Provenance & Data Lifecycle

**Goal:** Treat “knowledge” like production software: versioned, testable, observable, and governed—so agents don’t learn from a garbage swamp.

**Modules**

1. **Ingestion Pipelines**

   * Connectors (docs, wikis, code, PDFs, tickets), parsing, normalization.
   * Table/code preservation: don’t shred structure into text confetti.
   * Deduplication and canonical IDs.

2. **Metadata, Provenance & Lineage**

   * Source-of-truth tracking: doc ID, version, timestamp, author/system.
   * “Citation-ready chunks”: stable anchors, span IDs, quote extraction.
   * Trust tiers: official policy docs vs random notes.

3. **Corpus Quality & Maintenance**

   * Drift detection: what changed, what broke, what is stale.
   * Content linting: forbidden patterns, PII scans, injection signatures.
   * Consistency checks across docs (duplicate policies, contradictory rules).

4. **Indexing & Retrieval Engineering (Beyond “embed it”)**

   * Hybrid search defaults (BM25 + vectors) and reranking.
   * Entity-aware chunking, structural chunking (headings/sections).
   * Multi-index strategies: per-domain indexes + global index.

5. **Knowledge Graph Construction Pipelines**

   * Entity extraction + relation extraction + human review loops.
   * Graph versioning: schema migrations and backward compatibility.
   * Graph evaluation: coverage, correctness, usefulness for multi-hop.

6. **Access Control & Governance for Knowledge**

   * Document-level ACLs and role-based retrieval.
   * Redaction policies and tiered visibility.
   * Auditability: who retrieved what and why.

7. **Knowledge Testing**

   * “Needle sets”: facts that must always be retrievable and cited.
   * Regression tests for ingestion/index changes.
   * Retrieval poisoning tests (indirect prompt injection resilience).

> Deepens: Spec B (grounding), Spec E (injection defense), Spec F (eval datasets).

---

## Specialization M – Agent Runtime & Framework Engineering (Build Your Own “LangGraph-ish”)

**Goal:** Understand the execution substrate so agents are not vibes glued to API calls.

**Modules**

1. **Execution Models**

   * Step function design: `state -> (action | tool_call) -> new_state`.
   * Determinism controls: seeds, snapshotting, replayability.
   * Event-driven vs tick-driven runtimes.

2. **Graph DSLs & Compilation**

   * Declarative graphs → compiled runtime plans.
   * Typed nodes, typed edges, and schema-validated transitions.
   * Static analysis: unreachable states, cycles, missing guards.

3. **Persistence & Event Sourcing**

   * State snapshots + append-only event logs.
   * Exactly-once-ish semantics: idempotency keys and tool call deduping.
   * Time-travel debugging as a first-class runtime feature.

4. **Scheduling & Concurrency**

   * Cooperative vs preemptive tool scheduling.
   * Priority queues and SLA-aware scheduling (interactive UX vs batch).
   * Safe parallelism: shared-nothing subagents + merge strategies.

5. **Plugin & Capability Systems**

   * Capability tokens: tools granted per node/role.
   * Dependency injection for tools (prod vs mock vs sandbox).
   * Tool registry design: discovery, versioning, deprecation.

6. **Built-In Observability**

   * Traces as a product artifact (not an afterthought).
   * Standard event schemas for: tool calls, model calls, decisions, guardrails.
   * Debug UIs: “why did it do that?” answered by design.

7. **Config & Rollback**

   * Version prompts, graphs, tools, and policies as deployable artifacts.
   * Feature flags for new tools and new planning behaviors.
   * Rollback triggers (quality regressions, cost spikes, safety alerts).

> Deepens: Spec F (debugging), Spec G (infra), Spec E (policy nodes), Spec C (graphs).

---

## Specialization N – Standards, Interoperability & Packaging (So You’re Not Trapped in One Stack)

**Goal:** Make components swappable: models, tool servers, runtimes, and eval pipelines.

**Modules**

1. **Tool Schema Standards**

   * JSON Schema discipline, OpenAPI-inspired specs, versioned contracts.
   * Stable tool semantics across providers (function calling differences).
   * Tool response formats: deterministic serialization and typed errors.

2. **Agent ↔ Tool Protocols**

   * MCP-style client/server boundaries (already in Spec B, expanded here).
   * Credential isolation and token scoping patterns.
   * Tool capability negotiation and discovery.

3. **Trace & Eval Interop**

   * Common trace event formats and “portable traces.”
   * Reproducible replays across runtimes.
   * Dataset formats for agent trajectories and verifier outputs.

4. **Prompt & Policy Packaging**

   * Prompt bundles: templates + rubrics + constraints + test cases.
   * Policy bundles: guardrails and compliance logic deployed like code.
   * Compatibility matrices: which bundle versions work with which tool versions.

5. **Model Abstraction Layers**

   * “Least common denominator” interfaces vs provider-specific superpowers.
   * Feature detection: JSON mode present? tool calling present? vision present?
   * Migration playbooks when providers change behavior.

> Deepens: Spec B (MCP), Spec O (frameworks), Spec F (reproducibility), Spec H (provider abstractions).

---

## Specialization O – Domain Blueprints & Reference Implementations

**Goal:** Turn theory into reusable templates: “here’s what a good research agent / coding agent / ops agent actually looks like.”

**Modules**

1. **Research & Intelligence Agent Blueprint**

   * Agentic context construction, citation discipline, claim tracking.
   * Source quality scoring, contradictory source resolution.

2. **Software Engineering Agent Blueprint**

   * Repo map + code search + plan + implement + test + patch application.
   * CI integration, linting, unit test gating, safe refactors.

3. **Data Analysis Agent Blueprint**

   * Dataset ingestion, profiling, EDA, hypothesis testing, plotting, reporting.
   * Reproducible notebooks/scripts; artifact storage.

4. **Customer Support / CRM Agent Blueprint**

   * Intent routing, policy-grounded responses, safe account actions.
   * Conversation summaries into tickets; “no hallucinated policy” constraints.

5. **Operations / SRE Agent Blueprint**

   * Runbook retrieval, monitoring queries, safe remediation proposals.
   * Approval gates for side-effecting actions.

6. **Education / Tutor Agent Blueprint**

   * Student model (knowledge state), spaced repetition, rubric-based grading.
   * Tooling: quizzes, feedback loops, progress dashboards.

7. **Compliance / Legal / Policy Agent Blueprint**

   * Strict citations, refusal behavior, escalation workflows.
   * Provenance-first answers with “show me the clause” capability.

8. **Creative & Design Agent Blueprint**

   * Constraint-driven ideation, style guides, critique loops, versioning.

> Deepens: all specs — these are the “capstone templates.”

---

## Specialization P – Simulation, Sandboxes & Synthetic Environments for Agents

**Goal:** Train and test agents in worlds you control before they do interpretive dance in production.

**Modules**

1. **Tool Sandboxes**

   * Stubbed tools, fake APIs, fake file systems, deterministic time.
   * “Record/replay” tool traces for reproducible debugging.

2. **World Simulators**

   * Simulated web pages/UI states for browser agents (including deliberate UI changes).
   * Simulated ticketing systems, CRMs, schedulers, etc.

3. **Scenario Generation**

   * Synthetic users: cooperative, confused, adversarial, inconsistent.
   * Injection corpora: documents with traps embedded (prompt injection, exfil attempts).

4. **Stress & Chaos Testing**

   * Tool latency spikes, partial failures, corrupted outputs, rate limiting.
   * Randomized “fault injection” at each node.

5. **Self-Play and Curriculum**

   * Generate increasingly hard tasks based on failure modes (curriculum learning).
   * Self-play for negotiation / coordination (ties to multi-agent spec).

6. **Ground-Truth Instrumentation**

   * In sim, you can know the truth → perfect scoring and rich training signals.
   * Use sim data to build verifiers and judge calibrators (Spec F + H).

> This is the missing “wind tunnel” for agent systems.

---