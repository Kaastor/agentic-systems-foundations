# Strategy / Brain Layer Implementation Playbook
**Also known as:** Cognition Architecture + Control Loop Catalog + SOTA Methods  
**Core language:** Python (but architecture is language-agnostic)  
**Status:** Production playbook for building replaceable strategy modules atop a reliability kernel  
**Version:** v1.2  
**Last updated:** 2026-01-08

---

## 0. Purpose and scope

This playbook is a **staff/principal-level** guide to implementing the **strategy/brain layer** of an agentic system — the part that decides:

- what the user is asking,
- what the system should do next,
- which tools to call (and how),
- how to ground and verify,
- when to search/think more,
- when to stop / ask / escalate,
- how to produce a final answer with evidence.

It assumes you already have (or are building) a **kernel** that enforces:
tool mediation, policy, budgets, verification hooks, audit logging, and state.

> Core principle: **the brain proposes; the kernel enforces.**  
> Translation: strategy is optimized for *quality*; the kernel is optimized for *safety and invariants*.

---

## 0.1 Crosswalk: strategy capabilities ↔ hub specializations ↔ SOTA methods

This playbook maps to your hub:

- **Structured I/O & tool schemas** → Spec A  
  (function calling / JSON mode / constrained decoding; schema evolution)
- **Grounding / RAG / tool use** → Spec B  
  (CAG, GraphRAG, Self-RAG, DB-grounding)
- **Planning / hierarchies / state machines** → Spec C + J  
  (ReAct, plan-execute, router-executor, map-reduce, ToT search)
- **Memory & durable state** → Spec D  
  (episodic memory, long-term memory policies, TTL/provenance)
- **Evaluation & experimentation** → Spec F  
  (judge calibration, pinned suites, release gates)
- **Performance / scaling** → Spec G  
  (caching, batching, model routing, cost policies)
- **Model selection / customization** → Spec H  
  (multi-model roles, SFT, RL, distillation)
- **Neurosymbolic / verifiers** → Spec K  
  (deterministic solvers, parsers, unit tests)
- **Interop & standards** → Spec N  
  (MCP tool servers, packaging)

Key external references for the SOTA methods included here:
ReAct [1], Tree of Thoughts [4], Self-RAG [5], GraphRAG [6][7], OpenAI test-time compute framing [8], Anthropic agent/tool guidance [9][10], GRPO-style post-training [11][12], and MCP security guidance [13][14].

---

## 1. Architecture you can defend in a design review

### 1.1 Strategy as a compiler (recommended mental model)

> **Strategy = compiler from (observations, goal, constraints) → (typed intents + final response)**

- Input: typed `StrategyContext` (sanitized observations + tool manifest + budgets)
- Output: typed `StrategyProposal` (next intent(s) and optional response)

The kernel remains the runtime:
- validates and executes intents,
- enforces budgets and policy,
- persists state and logs traces.

This model makes “reasoning” **inspectable** and makes “intelligence” **testable**.

### 1.2 Reference architecture (modules inside “brain”)

A production brain is rarely one prompt. It’s a **pipeline** (often a graph):

1. **TaskSpec extraction**  
   What is asked? constraints? success criteria? ambiguity?
2. **Routing**  
   Which controller? which tool set? which model roles?
3. **Planning (optional but strongly recommended for multi-step)**  
   Plan IR with steps, dependencies, stop conditions.
4. **Grounding & context construction**  
   DB queries / retrieval / browse / tool calls to gather evidence.
5. **Action selection**  
   Tool selection + argument generation as typed intents.
6. **Verification / critique**  
   Pre-commit checks; best-of-N; rubric-driven judges.
7. **Response synthesis**  
   Final answer with claim→evidence mapping.
8. **Memory update**  
   Store only what is worth remembering; attach provenance; TTL.

### 1.3 Hard boundaries you should enforce (even in non‑TCB code)

Even though the kernel enforces invariants, strategy code SHOULD still enforce:

- **No hidden I/O**: strategy never calls tools directly (only proposes intents).
- **Normalize observations early**: convert tool outputs into typed objects ASAP.
- **Bounded deliberation**: max critique iterations; max search depth; max “thinking tokens”.
- **Instruction/data separation**: retrieved/browsed text is data, never policy.

### 1.4 Strategy topology: in-proc today, service tomorrow (design for it now)

Even if you start with strategy code in the same process, design it as if it were remote:

- strict input/output schemas,
- timeouts (kernel-side),
- idempotent request IDs,
- statelessness where possible (state lives in kernel snapshots),
- deterministic behavior under replay when inputs are identical.

**Why:** strategy evolution is frequent; kernel evolution should be rare.

---

## 2. Repo layout and artifact hygiene (prompts are code)

A production strategy layer lives or dies on artifact hygiene.

### 2.1 Recommended repo layout (strategy side)

```
strategy/
  controllers/         # ReAct, PlanExec, MapReduce, Search controllers
  skills/              # domain skills: SQL, web research, code repair, etc.
  prompts/
    router/
    planner/
    tool_args/
    critic/
    summarizer/
  rubrics/             # critic/judge rubrics, written as data
  schemas/             # Plan IR, Evidence IR, StrategyProposal ABI
  configs/
    models.yaml        # role-based models + routing rules
    compute.yaml       # test-time compute policy
  bundles/             # versioned bundle manifests
  tests/
    unit/
    integration/
    golden/
  evals/
    suites/
    judges/
```

### 2.2 Bundle manifests (strategy ships as a bundle)

Treat a “strategy version” as a **bundle**:

- strategy code version (git sha)
- prompt bundle ID/hash
- rubric versions/hashes
- schema/ABI version
- routing config hash
- compute policy hash
- eval suite versions used as gates

This makes A/B tests, canary, and rollback real.

### 2.3 Prompt design rules (so prompts scale)

- Prompts SHALL be parameterized templates (Jinja/YAML/whatever) with versioning.
- Prompts SHALL be covered by evals and regression tests.
- Prompts SHOULD be designed for *structured outputs first*:
  - JSON schema embedded,
  - explicit “if unsure, set `needs_more_info=true`” constraints,
  - examples include edge cases.

Anthropic’s agent guidance emphasizes simple, composable patterns and eval-driven iteration [9].

---

## 3. Core schemas: cognition IR (your brain’s internal API)

Typed IR is the biggest force multiplier you have.

### 3.1 TaskSpec (what problem are we solving?)

```python
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, List, Optional, Dict

class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_goal: str
    task_type: Literal[
        "qa", "research", "coding", "data_analysis", "workflow", "ops", "creative", "other"
    ]
    constraints: Dict[str, str] = Field(default_factory=dict)  # budgets, style, compliance
    acceptance_criteria: List[str] = Field(default_factory=list)
    blocking_questions: List[str] = Field(default_factory=list)
    risk_tier: Literal["low", "med", "high"] = "low"
```

**Engineering notes**
- `task_type` drives routing and loop choice.
- `acceptance_criteria` becomes verifier seeds.
- `blocking_questions` makes “ask vs act” explicit and testable.

### 3.2 Plan IR (plans are data, not prose)

```python
from typing import Any

class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    step_id: str
    intent: Literal[
        "tool_call", "retrieve", "reason", "write", "ask_user", "finalize"
    ]
    description: str
    depends_on: List[str] = Field(default_factory=list)
    expected_observation: Optional[str] = None
    success_check: Optional[str] = None  # should map to a verifier when possible
    risk_tier: Literal["low", "med", "high"] = "low"

class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    goal: str
    steps: List[PlanStep]
    stop_conditions: List[str] = Field(default_factory=list)
    replan_triggers: List[str] = Field(default_factory=list)
    fallback_strategies: List[str] = Field(default_factory=list)
```

### 3.3 Evidence IR (claim → evidence)

```python
class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str            # doc/tool run id
    source_type: Literal["tool", "doc", "web", "memory", "user"]
    quote: Optional[str] = None
    span: Optional[str] = None  # e.g., "L120-L145" or byte offsets
    url: Optional[str] = None
    collected_at: str          # ISO timestamp
    trust_tier: Literal["high", "med", "low"] = "med"

class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    evidence: List[EvidenceItem] = Field(default_factory=list)
    confidence: Literal["low", "med", "high"] = "med"
```

### 3.4 StrategyProposal (what the kernel actually needs)

At minimum, the kernel needs:
- `next_intents[]`
- `response` (optional)
- `debug` (optional: plan IR, rationale, scores — but remember: not TCB)

If you already have a kernel ABI, don’t fork it — extend it compatibly.

---

## 4. Control loop catalog (choose the right brain for the job)

### 4.1 ReAct (tool–observe–reason) — the default workhorse
**When to use**
- interactive agents
- search/browse tasks
- workflows where each observation changes next step

**Reference:** ReAct paper [1].

**Implementation sketch**
- Strategy proposes one tool call intent at a time
- Kernel executes tool call
- Strategy receives typed observation
- Repeat until done or budget exhausted

**Common failure**: tool thrash  
Fix with:
- loop detectors,
- “expected_observation” fields,
- bounded retries,
- escalating to plan-execute when thrash detected.

### 4.2 Plan-and-execute — the “project manager” loop
**When to use**
- long tasks with dependencies
- coding/refactoring with checkpoints
- workflows that require progress visibility

**Implementation sketch**
1. Generate `TaskSpec`
2. Generate `Plan`
3. Validate plan is executable with available tools
4. Execute steps (with replanning)

**Plan validation rules (practical)**
- Every step must map to a known intent/tool or a user question.
- No step is allowed to be purely “research more” without a retrieval/tool spec.
- Risk tier is assigned per step.

### 4.3 Plan–act–reflect — bounded revision loops
**When to use**
- first drafts often fail (coding, complex synthesis)
- you need iterative improvement with a rubric

Related pattern: Reflexion (episodic feedback) [2].

**Bounded reflect recipe**
- `draft → critique(rubric) → revise` up to K times
- stop early when rubric passes

### 4.4 Router–executor (MRKL-style) — specialization at scale
**When to use**
- many tools/skills exist
- you can cheaply classify tasks
- specialized executors outperform generalists

Reference: MRKL systems [3].

**Pattern**
- Router outputs `task_type`, `executor_id`, and recommended compute budget
- Executor runs its own controller (ReAct/plan/verify)
- Kernel remains enforcement runtime

### 4.5 Map–reduce / parallel workers — quality via isolation
**When to use**
- processing large lists
- broad research
- summarizing many docs where “context fatigue” is real

**Pattern**
- Supervisor decomposes into N tasks
- Spawn N workers (isolated contexts; narrow tool access)
- Aggregate with deterministic checks (dedupe, contradictions, coverage)

### 4.6 Search-based deliberation — test-time compute as an algorithm
**When to use**
- mistakes are expensive
- you have scoring (verifier/judge)
- the problem needs exploration

Tree-of-Thoughts introduces deliberate search over intermediate “thoughts” [4].

**Rule:** search without scoring is expensive fanfiction.

---

## 5. Grounding: from “RAG” to a modern grounding stack

A strategy engineer treats grounding as a **decision system**.

### 5.1 Grounding decision tree (practical)

1. **Is there a deterministic tool/DB?**  
   Use it. Treat output as authoritative.
2. **Is the corpus bounded and mostly static?**  
   Consider CAG / long-context with caching.
3. **Is the corpus interconnected with multi-hop queries?**  
   Consider GraphRAG [6][7].
4. **Does retrieval necessity vary by question?**  
   Use adaptive retrieval (Self-RAG-style) [5].
5. **Otherwise**: use hybrid RAG (BM25 + vectors + reranker) with strong evidence discipline.

### 5.2 Retrieval as a tool (do not “append text”)

Define retrieval as an explicit tool contract:

```python
class SearchDocsArgs(BaseModel):
    query: str
    k: int = 8
    filters: dict = Field(default_factory=dict)

class DocHit(BaseModel):
    doc_id: str
    title: str
    snippet: str
    score: float
    metadata: dict = Field(default_factory=dict)

class SearchDocsResult(BaseModel):
    hits: list[DocHit]
```

**Strategy discipline**
- retrieval outputs become `EvidenceItem`s, not prompt soup,
- retrieval is conditional (don’t always retrieve),
- run “evidence sufficiency” checks (“do hits actually support claims?”),
- tie factual claims to evidence objects.

### 5.3 Self-RAG / adaptive retrieval (retrieve only when needed)

Self-RAG explicitly models retrieve → generate → critique with reflection tokens [5].

A practical production approximation:
- do a cheap “retrieve_needed?” step first,
- retrieve only if needed,
- after retrieval, do “evidence sufficiency” scoring,
- escalate if sufficiency fails (retrieve more, ask user, or abstain).

### 5.4 GraphRAG (multi-hop over narrative corpora)

GraphRAG builds graph-structured summaries and uses them for better global retrieval [6][7].

**Where it helps**
- policy corpora, wikis, narrative private data
- “explain system X” / “what caused incident Y” style questions

**Where it hurts**
- ingestion complexity
- extraction errors become new failure modes
- requires solid KnowledgeOps (provenance, drift detection)

### 5.5 CAG / long-context caching (bounded corpora)

CAG is straightforward:
- compile a bounded corpus into a canonical context artifact,
- cache KV states where supported,
- reference a versioned corpus build ID in your bundle manifest.

This reduces retrieval selection errors, but does not eliminate:
- model misinterpretation,
- outdated corpus versions,
- injection risks from the corpus itself.

---

## 6. Verification and critique (make quality a mechanism)

### 6.1 Verifiers hierarchy

Use verifiers in this order:

1. **Deterministic** (unit tests, schema validation, solvers)
2. **Tool-grounded** (re-run query, check constraints)
3. **Model-judge** (rubric-based critique as defense-in-depth)

### 6.2 Best-of-N with verifiers (high leverage)

Instead of sampling N final answers, sample N *decisions*:

- N plans → pick best plan
- N tool args → pick args that satisfy constraints
- N SQL queries → pick query that parses and returns plausible results

This is practical test-time compute: spend compute where it changes outcomes [8].

### 6.3 Judge calibration (if you use model judges)

Model judges can drift or be biased. Calibrate them.

**Minimal calibration protocol**
- Create a judge calibration set with:
  - obvious passes,
  - obvious fails,
  - tricky near-misses.
- Compare judge vs human labels.
- Track judge precision/recall over time.
- Never use a judge as the only safety mechanism for privileged actions.

### 6.4 Critic design rules (avoid critic collapse)

- Critic MUST use a rubric and output structured scores.
- Critic MUST provide concrete reject reasons (“Step 3 is non-executable because …”).
- Critic MUST be bounded (max K revisions).
- Critic MUST not treat untrusted content as policy.

Anthropic’s tool-writing guidance is strongly aligned with this: improve tools + evals systematically [10].

---

## 7. Tool-use cognition (how to act without flailing)

### 7.1 Tool selection is classification + planning

Treat “which tool?” as an explicit step:
- identify required capability,
- pick minimal authority tool,
- generate args with constraints.

### 7.2 Tool description contracts (poka‑yoke for the model)

Tool manifests SHOULD include:
- purpose,
- input schema,
- output schema,
- example calls (good and bad),
- common failure modes,
- cost/latency hints,
- idempotency semantics (if relevant),
- risk tier labels (kernel-enforced; strategy uses for compute allocation).

Anthropic recommends poka-yoke tool design for agent reliability [10].

### 7.3 Argument generation patterns (robustness)

Patterns that work in practice:
- “Draft args → validate → repair” (bounded)
- “Explain assumptions as structured fields” (not prose)
- “If required fields unknown → ask user” (don’t hallucinate)

### 7.4 Standards and interoperability: MCP tool servers (recommended)

If your ecosystem spans multiple apps and tool providers, standardize tool integration.
The **Model Context Protocol (MCP)** is one emerging open standard for exposing tools/resources to LLM applications.

Practical strategy-layer implications:
- Treat MCP tools like any other tool in the manifest: **typed inputs/outputs** and clear side-effect semantics.
- Assume tool outputs can be adversarial or malformed; always parse and validate.
- Align your strategy policies (risk tiers, compute) with tool metadata (read vs write, dangerous ops).

Security note:
- Authorization and security best practices are non-optional in production MCP deployments [13][14].
- Strategy code must not “roll its own auth”; the kernel/tooling layer should.

---

## 8. Model roles, routing, and test-time compute

### 8.1 Role-based model assignment (multi-model is normal)

Common roles:
- Router (cheap)
- Planner (strong)
- Executor/tool args (schema-adherent)
- Critic/judge (strong)
- Summarizer (cheap, stable)

Routing should be explicit and testable, not hidden in prompts.

### 8.2 Test-time compute policy

Test-time compute scaling is now a standard lever [8].

Knobs:
- planner “thinking tokens” budget
- N for best-of-N sampling
- search depth/branching
- critique iterations

**Policy template**
- Low risk + high confidence → low compute
- High risk or low confidence → higher compute + verifiers

Record compute choices in trace metadata.

---

## 9. Memory and context (brain hygiene)

### 9.1 Layered memory recap

- Working memory: run summary, plan status, open questions
- Task memory: durable artifacts, decisions, TODOs
- Long-term: curated user preferences/stable facts

### 9.2 Memory write policy (what gets stored)

Store only:
- validated outputs,
- stable preferences (with explicit user opt-in where relevant),
- lessons learned (bounded, non-sensitive),
- pointers to artifacts (files/IDs), not large blobs.

Never store:
- raw untrusted web text,
- secrets,
- ambiguous facts without provenance.

### 9.3 Memory retrieval policy (when to recall)

Retrieve memory only when it improves decision-making:
- user preference needed,
- prior work exists (avoid duplication),
- long-running workflow resumption.

A “memory spam” strategy will degrade over time by drowning itself in its own output.

---

## 10. Learning and optimization loops (SFT / RL / compiled prompts)

### 10.1 Prompt optimization (“compiled prompts”)

Treat prompts like code:
- versioned
- tested
- optimized against eval suites

DSPy-style approaches formalize this as “compile prompt parameters against data.”

### 10.2 SFT on traces (cold start → distill → iterate)

Workflow:
1. Collect successful trajectories (intent → tool → observation → … → success)
2. Filter for correctness and schema adherence
3. Fine-tune a smaller/faster model for executor/router roles
4. Re-evaluate on pinned suites

### 10.3 RL with verifiable rewards (where it’s worth it)

When you have objective verifiers (tests, parsers, solvers), RLVR-style training can work.

GRPO is a practical optimizer used in open literature for post-training reasoning with verifiable rewards [11][12].

**Staff-level warning:** RL amplifies what your verifier measures — including bugs.

---

## 11. Testing and evaluation for strategy (make progress measurable)

### 11.1 Minimum eval packs per capability

- **Schema adherence**: malformed JSON, missing fields, wrong enums
- **Tool selection**: correct tool chosen, wrong tool avoided
- **Tool args correctness**: args within constraints; idempotency keys present
- **Grounding**: “unsupported claim” detection; citation accuracy
- **Loop behavior**: no infinite loops; bounded retries; replanning works
- **Adversarial**: prompt injection docs; contradictory sources; tool error storms
- **Budget**: stays within token/cost limits

### 11.2 Trace review as a first-class debugging tool

Require every run to produce:
- plan IR (even if internal),
- tool intents with expected observations,
- evidence objects,
- verifier results,
- final response + claim/evidence map (when applicable).

This turns debugging from “read chat logs” into “inspect structured traces”.

---

## 12. Packaging and shipping strategies (iteration without production chaos)

### 12.1 Strategy bundles

Ship strategy as a bundle:
- strategy code version
- prompt templates version
- rubrics version
- routing config
- model role configs
- compute policy config
- eval suite versions used as gates

### 12.2 Feature flags and progressive rollout

- enable new bundles for a small % of traffic (canary)
- shadow-evaluate on live tasks (no user impact)
- auto-rollback on quality or cost regressions

---

## Appendix A: Reference links

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
[13]: https://modelcontextprotocol.io/specification/draft/basic/security_best_practices  "MCP Security Best Practices"  
[14]: https://modelcontextprotocol.io/docs/tutorials/security/authorization  "MCP Authorization (OAuth 2.1) tutorial"  
