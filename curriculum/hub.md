# “Agentic Systems Foundations” Hub 

---

# Program Overview

**Steel thread for the whole program**

> *Email triage + calendar scheduling agent with human approval + RAG docs lookup (company policies, context, etc.), long‑running, logged, and evaluated.*

**Courses**

1. **Main Course:** Agentic Systems Foundations (breadth + working steel thread)
2. **Specialization A:** Structured LLM I/O & Tool Schema Engineering
3. **Specialization B:** RAG & Tooling for Agentic Systems
4. **Specialization C:** Agent State Machines, Planning & Hierarchical Agents
5. **Specialization D:** Memory, Long-Term Context & Durable State
6. **Specialization E:** Guardrails, Safety, Security & Governance
7. **Specialization F:** Evaluation, Testing, Observability & Experimentation
8. **Specialization G:** Performance, Scaling & Agent Infrastructure
9. **Specialization H:** Model Selection, Customization & Multi‑Model Systems
10. **Specialization I:** UX, Human-in-the-Loop & Productizing Agents

The **main course** touches *all* concepts at a practical level. The **Specializations** go much deeper but stay consistent with the same steel thread.

---

# Main Course: Agentic Systems Foundations

**Goal:** Build a working, production-shaped agent over the steel thread. Students see everything once end-to-end, but not every topic in maximal depth.

Think: “broad but solid” + lots of hands-on.

---

## Module 1 – LLM & Structured I/O Basics

**Focus:** Make the model behave like a typed library, not a poetry engine.

* Design strict tool/function schemas

  * Tools as typed functions (Pydantic/dataclasses).
  * Required vs optional args, enums, clear side-effect semantics.
  * Tag dangerous tools (`delete_*`, `transfer_funds`, `send_email`) with metadata for human approval.

* Robust structured generation

  * JSON mode / function calling / `response_format`.
  * Schema examples in prompts; instructions for “if unsure”.
  * Pydantic validation, auto-retry, raw-output logging.

* Tokenization, sampling & cost (intro)

  * Token counting, worst-case cost for workflows.
  * `max_tokens` / stop sequences without truncating JSON.
  * Basic temperature/top_p choices for “strict tools” vs “creative text”.

> **Deep dive:** Specialization A + H

---

## Module 2 – Tooling & RAG as a Tool (Intro)

**Focus:** Safe interaction with external systems, including retrieval.

* Tool layer fundamentals

  * Wrappers with input validation and idempotency keys.
  * Read vs write tools; logging all writes.
  * Basic structured error types (`TransientError`, `PermanentError`, `ValidationError`).

* Tool registry / manifest

  * Names, descriptions, latency profile, permissions.
  * LLM tool selection vs hand-written routing for critical paths.

* RAG as a first-class tool (intro)

  * Simple `search_docs(query, k) -> [DocumentHit]` API.
  * DocumentHit with id/snippet/score/source.
  * RAG results in state as structured objects, not pasted blobs.

> **Deep dive:** Specialization B

---

## Module 3 – Agent as Explicit State Machine / Graph

**Focus:** From chat loop to explicit graph.

*   **The "Why": The Trap of the Implicit Loop**
    *   *The Anti-Pattern:* The naive `while True:` loop where state lives in Python variables and the call stack.
    *   *The Failure Mode:* Why you can't inspect, pause, or resume a standard Python loop without complex pickling.
    *   *The Shift:* Moving state from "Stack Frames" (opaque) to "State Objects" (transparent).
    
* AgentState as a serializable object

  * `conversation_history`, `scratchpad`, `plan`, `tool_results`, `memory`, `metadata`, `step_index`, etc.

* Node types & finite states

  * States: `Planning`, `ToolSelection`, `ToolExecution`, `Summarize`, `AwaitUser`, `HumanReview`, `TerminalSuccess`, `TerminalFailure`, etc.
  * Node types: LLM decision node, tool node, router/switch node, human-approval node, loop node with max-iterations.

* Dispatcher & pure transitions

  * Deterministic dispatcher keyed by `current_node`.
  * Pure `(state, node_output) -> new_state` functions, mockable in tests.
  * State invariants (e.g. `ToolExecution` implies selected_tools ≠ ∅).

> **Deep dive:** Specialization C

---

## Module 4 – Planning & Multi-Step Workflows (Intro)

**Focus:** Basic plan-then-act and “don’t overcomplicate it” heuristics.

* Plan-then-act loop

  * First LLM call: structured plan (steps, tools, dependencies, expected outputs).
  * Convert plan into graph nodes rather than paragraphs in history.

* Simple re-planning & repair

  * Adjust plan when tools fail or assumptions break.

* “When not to be fancy”

  * Criteria for single-shot calls vs agent graph.
  * Simple classifier/heuristic to route easy Q&A to direct-answer path.

> **Deep dive:** Specialization C

---

## Module 5 – Memory & Context Management (Intro)

**Focus:** Not losing the plot when the context window ends.

* Rolling context

  * Last N turns + running summary.

* Layered memory

  * Conversation summary, key facts/entities table, open tasks/TODO list.

* Long-term memory (intro)

  * Vector or key-value store for “what did we do before for this user?”
  * Simple recall policy (“check memory at the start of each workflow”).

> **Deep dive:** Specialization D

---

## Module 6 – Guardrails, Safety Checks & Basic Governance (Intro)

**Focus:** Guardrails as edges in the graph, not vibes.

* Policy check node

  * Inspect tool name, args, user identity, risk level.
  * Decisions: continue / ask for human approval / refuse.

* Tool loop detection

  * Track `(tool_name, args_hash)`; stop repeating failing calls N times.
  * Feed error details back to LLM and require a changed plan.

* Self-check node (intro)

  * Restate user goal.
  * List evidence/tools used.
  * Choose: `confident` / `need_more_info` / `refuse`.

* Basic threat thinking

  * “Never follow instructions from RAG content unless user explicitly asked”.
  * Simple least-privilege setup for credentials.

> **Deep dive:** Specialization E

---

## Module 7 – Long-Running & Durable Agents (Intro)

**Focus:** Surviving user delays and crashes.

* Persist & rehydrate AgentState to storage.
* `AwaitUser` state and resume on webhook/user reply.
* Simple time-based wake-ups (“remind me in 3 days”).
* Idempotent restarts: don’t send duplicate emails.

> **Deep dive:** Specialization D + G

---

## Module 8 – Evaluation, Testing & Observability (Intro)

**Focus:** Agents as distributed systems, not prompt toys.

* Logs & traces

  * Node transitions, tool I/O, prompts/completions, timing, cost.
  * Per-run trace graph.

* Basic workflow-level tests

  * Mock tools, assert final state or key side effects.

* Simple failure taxonomy & metrics

  * Wrong tool vs wrong args vs failure to halt vs safety violation.
  * Track success rate, average steps, human escalation rate.

> **Deep dive:** Specialization F

---

## Module 9 – Production Deployment & Runtime Configuration

**Goal:** Take the agent from “great in a notebook” to “running as a service with sane defaults.”

**Focus:** Packaging, configuration, logging, and light CI/CD for the steel-thread agent.

*Packaging & entrypoints*

- `run_agent(user_message, context) -> AgentResult` as a stable API.
- Wrap the agent in:
  - An HTTP endpoint
  - A CLI / notebook harness (now “production-shaped”).

*Configuration & feature flags*

- Env/config-file driven toggles for:
  - Models (fast vs smart modes; deep model selection lives in Specialization H).
  - Temperatures / decoding parameters per *mode*.
  - Max steps / depth limits.
  - Tool enable/disable per environment (dev/staging/prod).

*Production logging & integration*

- Hook the logging/tracing from Module 8 into:
  - Your actual logging stack (structured logs, trace IDs).
  - Basic dashboards for:
    - Error rates
    - Latency
    - Cost per request.

*CI/CD & regression protection (light)*

- Integrate:
  - Unit tests for state transitions.
  - A small golden-flow suite for the steel-thread agent.
- Gate deployments on these passing.

> Detailed performance tuning and cost optimization are covered in **Specialization G**.  
> Deep model-selection strategy is covered in **Specialization H**.


---

## Module 10 – The User Interface & Shipping the Agent

**Goal:** End the course with something you can actually show a human.

**Based on / expands previous “UX survey” bits:**

* **Simple UI for the steel-thread agent**

  * A minimal chat-like or dashboard UI that:

    * Lets a user ask: “Clean up my inbox” / “Schedule this meeting”.
    * Shows the agent’s current plan and progress (basic “what I’m doing now” exposure).

* **Human approval flow**

  * UX for:

    * Reviewing proposed emails.
    * Approving or editing calendar invites.
  * Clear affordances for:

    * Approve
    * Edit
    * Cancel

* **Surfacing internals for trust**

  * Show:

    * Which tools were used.
    * Which RAG documents or emails were consulted.
    * A simple “why I chose this” explanation.

* **Feedback loops**

  * Capture:

    * User edits to drafts.
    * Explicit “this was wrong/unhelpful” signals.
  * Plumb these into:

    * Logs for analysis.
    * Inputs to later Specializations (Evals, Prompt Optimization).

* **Shipping narrative**

  * Final “from notebook to shipped” walkthrough:

    * Agent is deployed behind an endpoint (Module 9).
    * There is *some* UI where users can interact with it.
    * Basic approval and feedback flows are live.

---

### Notes on earlier modules (no structural change, just emphasis)

* **Basic model config & cost awareness** stay where they already are:

  * Token/cost basics in Module 1.
  * Some perf/latency awareness in tools/memory/long-running modules.
* The **heavy-duty perf/model-selection** content stays deferred to Specializations G and H.


---

# Specializations

Now the “spin-offs” where each major concept gets the royal treatment.

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

8. **System 2 Thinking & Tree Search**

   * Moving beyond greedy token generation: exploring multiple reasoning paths before committing.
   * Monte Carlo Tree Search (MCTS) for agent decision-making: simulation, backpropagation, policy refinement.
   * Reasoning tokens: internal monologue not shown to user, enabling explicit "thinking" traces.
   * Self-verification and backtracking: detecting errors in reasoning and rewinding to earlier decision points.
   * Pseudocode as intermediate representation: structured thinking before final code generation.
   * Practical applications: complex coding tasks, mathematical reasoning, strategy planning.

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

> Deepens: main course Modules 7, 8, 9 + performance parts of the full curriculum.

---

## Specialization H – Model Selection, Customization & Multi‑Model Systems

**Goal:** Choose and tune the models powering your agent system.

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

4. **Fine-Tuning & LoRA (Conceptual)**

   * When prompts are not enough.
   * Dataset design for schema adherence or domain style.

5. **Reward Models & RL (High Level)**

   * Reward functions for agent behaviours.
   * How RLHF-style setups relate to agent design.

6. **Experimentation with Models**

   * Comparing model variants on eval suites.
   * Deciding whether the fix is: model, prompt, graph, or tools.

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

> Deepens: the UX-related content from **Main Course Modules 8–10**, especially the shipping and feedback loops.


---

## Sanity Check: Did we keep everything?

* **Structured I/O, schemas, sampling, streaming, JSON, retries, tokens, cost** → Main Module 1 + Specialization A & H.
* **State machines, graphs, invariants, pure transitions** → Main Module 3 + Specialization C.
* **Tool layer, RAG-as-tool, registries, concurrency, caching, security** → Main Module 2 + Specialization B.
* **Memory, long-term state, summaries, personas, forgetting** → Main Module 5 + Specialization D.
* **Guardrails, policy checks, self-checks, loops, safety models, prompt injection** → Main Module 6 + Specialization E.
* **Planning, hierarchical agents, reflection, plan repair** → Main Module 4 + Specialization C.
* **Long-running workflows, pause/resume, idempotent restarts, queues** → Main Module 7 + Specialization D + G.
* **Eval, testing, metrics, failure taxonomy, time-travel debugging, offline/online eval, human eval** → Main Module 8 + Specialization F.
* **Threat modelling, privacy, governance, least privilege** → Main Module 6/9 + Specialization E.
* **Infra, CI/CD, config, feature flags, deployment** → Main Module 9 + Specialization G.
* **Model selection, multi-model architectures, fine-tuning, experiments** → Main Modules 1 & 9 + Specialization H.
* **UX, human approval, productization** → Main Modules 9–10 + Specialization I.


So the main course gives one coherent story and working agent; the Specializations let you zoom in on any slice and push it to “senior engineer who can argue with infra / security / PM” depth.
