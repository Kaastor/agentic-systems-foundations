# StudyCoach Agent Technical Specification v0.1

**Option 1: Personalized Practice Coach with Self‑Verifying Exercise Generation**

**Purpose:** StudyCoach is a production-shaped agentic system that helps a learner master a technical skill (starting with programming) through **diagnostics → personalized practice → deterministic autograding → hint-first feedback → mastery tracking**. It **self-verifies** every generated exercise before showing it to the learner, so it doesn’t ship broken tasks. It is **long-running**, **auditable**, and **evaluated**.

**Steel thread (canonical workflow):**
**Goal intake → diagnostic → personalized plan → generate exercise → verify exercise (solution + tests) → present → learner submits → autograde → hint-first feedback → update mastery → schedule next session → logged + evaluated.**

---

## Specialization Legend

* **[Spec A]** Structured LLM I/O & Tool Schema Engineering
* **[Spec B]** RAG & Tooling for Agentic Systems
* **[Spec C]** Agent State Machines, Planning & Hierarchical Agents
* **[Spec D]** Memory, Long-Term Context & Durable State
* **[Spec E]** Guardrails, Safety, Security & Governance
* **[Spec F]** Evaluation, Testing, Observability & Experimentation
* **[Spec G]** Performance, Scaling & Agent Infrastructure
* **[Spec H]** Model Selection, Customization & Multi-Model Systems
* **[Spec I]** UX, Human-in-the-Loop & Productizing Agents

Throughout this spec, sections include tags like **Touches: [Spec C, Spec F]**.

---

# 1) Scope

## 1.1 In scope (v0.1 MVP → v1)

### MVP focus domain: programming practice (Python-first)

* Deterministic verification is easiest here (unit tests + sandboxed execution).
  Touches: **[Spec B, F, G, E]**

### Core features

1. **Goal intake + constraints**

   * Learner declares a goal (e.g., “learn recursion” / “prep for interviews”).
   * Constraints: difficulty, time budget, language, allowed help level.
     Touches: **[Spec C, I, D]**

2. **Diagnostic assessment**

   * Short quiz or a few micro-exercises to estimate starting mastery.
     Touches: **[Spec C, F, H]**

3. **Personalized learning plan**

   * Structured plan: daily sessions + concept progression + exercise types.
     Touches: **[Spec C, H, D]**

4. **Exercise generation (self-verifying)**

   * Agent generates an exercise artifact and then verifies it by running:

     * reference solution
     * unit tests
     * optional fuzz/property tests
       Touches: **[Spec A, B, F, G]**

5. **Autograding for learner submissions**

   * Execute learner submission in sandbox with hidden tests → grade report.
     Touches: **[Spec B, G, F, E]**

6. **Hint-first feedback**

   * Provide hints progressively; do not reveal full solution by default.
     Touches: **[Spec E, I, C]**

7. **Mastery model + memory**

   * Track concept mastery over time and adapt next exercises.
     Touches: **[Spec D, C, F]**

8. **Long-running sessions**

   * Resume after days; maintain continuity and avoid duplicating “next tasks.”
     Touches: **[Spec D, G, C]**

9. **Logging, tracing, evaluation harness**

   * Full trace per run and offline regression suite.
     Touches: **[Spec F, G]**

---

## 1.2 Explicit non-goals (v0.1)

* No integration with private email/LMS (dataset-free by design).
* No claims of “measuring human learning outcomes” in a scientific/medical sense in v0.1 (you can measure task performance and retention proxies).
* No full autonomous actions affecting external systems (calendar reminders optional later and user-approved).
* No “solve my graded homework” mode (guardrail required).

Touches: **[Spec E, I]**

---

# 2) Personas & Roles

## 2.1 Personas

* **Learner (primary):** practices, submits solutions, requests hints.
  Touches: **[Spec I, E]**
* **Instructor/Author (you):** configures curricula, exercise templates, policies, and reviews analytics.
  Touches: **[Spec I, F, E]**
* **Admin (optional):** deploys, configures infra, views audit exports.
  Touches: **[Spec G, E]**

## 2.2 Access control (RBAC)

* `LEARNER`: can practice; cannot see hidden tests or reference solutions.
* `AUTHOR`: can create/edit exercise generators/templates; can inspect traces.
* `ADMIN`: system config, retention, deployment controls.

Touches: **[Spec E, I]**

---

# 3) System Overview & Architecture

## 3.1 High-level components

1. **Agent Orchestrator (core runtime)**

   * Explicit state machine dispatcher
   * Planning + tool execution
   * Guardrails (hint policy, anti-cheat)
     Touches: **[Spec C, E, G]**

2. **Tool Layer / Sandbox Executor**

   * Deterministic, sandboxed code execution
   * Resource limits (CPU/time/memory)
   * Typed I/O + structured errors
     Touches: **[Spec A, B, G, E]**

3. **Content Store (Course + Exercise Artifacts)**

   * Versioned storage for:

     * concept graph
     * exercise templates
     * generated exercises
     * tests + reference solutions (secured)
       Touches: **[Spec D, G, B]**

4. **Mastery & Memory Store**

   * Learner mastery model, history, session summaries
     Touches: **[Spec D, C]**

5. **Observability + Evaluation Stack**

   * Trace graphs, metrics, offline eval harness
     Touches: **[Spec F, G]**

6. **UI Surface** (minimal in v0.1)

   * Web or CLI:

     * show exercise
     * accept submission
     * show grade + hints
     * show progress
       Touches: **[Spec I]**

7. **Model Gateway**

   * Provider abstraction
   * Node-specific model selection and decoding parameters
     Touches: **[Spec H, G]**

---

# 4) Functional Requirements

## 4.1 Goal intake & session setup

**FR-GOAL-1:** System SHALL accept learner goals and constraints as structured input:

* `target_skills`, `time_budget`, `difficulty_preference`, `language`, `help_policy`
  Touches: **[Spec A, C, I]**

**FR-GOAL-2:** System SHALL create a learner profile and initialize mastery state.
Touches: **[Spec D, C]**

---

## 4.2 Diagnostic assessment

**FR-DIAG-1:** System SHALL run an initial diagnostic (5–15 minutes) producing:

* estimated mastery per concept
* recommended starting difficulty
  Touches: **[Spec C, F, H]**

**FR-DIAG-2:** Diagnostic questions MUST be deterministic to grade (MCQ, short code tasks with tests).
Touches: **[Spec F, G]**

---

## 4.3 Planning

**FR-PLAN-1:** System SHALL create a structured learning plan:

* `sessions: [{date_offset, concepts, exercise_count, target_difficulty, success_criteria}]`
  Touches: **[Spec C, A]**

**FR-PLAN-2:** Plan MUST adapt when learner struggles or excels (re-planning).
Touches: **[Spec C, D]**

---

## 4.4 Exercise generation (self-verifying)

This is the “heart” of the steel thread.

**FR-EX-1:** System SHALL generate exercises as typed artifacts, not free text blobs.
Touches: **[Spec A, C]**

**FR-EX-2:** For every generated exercise, system SHALL run a verification pipeline before presenting it:

* run reference solution against tests
* ensure tests are not flaky (repeatable)
* ensure prompt matches required function signature / I/O contract
  Touches: **[Spec F, B, G]**

**FR-EX-3:** If verification fails, system SHALL repair or regenerate with an explicit loop limit and logging of failure reasons.
Touches: **[Spec E, C, F]**

**FR-EX-4:** Exercises SHALL support difficulty calibration knobs:

* constraints (time complexity, allowed constructs)
* required concepts
* forbidden shortcuts
  Touches: **[Spec H, A, C]**

---

## 4.5 Submission + autograding

**FR-GRADE-1:** System SHALL execute learner submissions in a sandbox and produce:

* pass/fail per test
* error traces (sanitized)
* performance stats (optional)
  Touches: **[Spec B, G, F, E]**

**FR-GRADE-2:** Hidden tests MUST remain inaccessible to learners.
Touches: **[Spec E, G]**

---

## 4.6 Hint-first feedback policy

**FR-HINT-1:** System SHALL default to “hint-first” progression:

* Hint 1: conceptual nudge
* Hint 2: targeted pointer (line-level or function-level)
* Hint 3: partial pseudocode
* Final: full solution only if explicitly allowed by policy/config
  Touches: **[Spec E, I, C]**

**FR-HINT-2:** System SHALL detect “cheating requests” (e.g., “just give me the answer”) and respond according to policy.
Touches: **[Spec E]**

---

## 4.7 Mastery model & long-running progression

**FR-MEM-1:** System SHALL update mastery state after each graded attempt:

* concept updates
* confidence
* error patterns
  Touches: **[Spec D, C, F]**

**FR-LONG-1:** System SHALL persist state after each node (checkpointing) and resume safely.
Touches: **[Spec D, G, C, F]**

---

# 5) Non-Functional Requirements

## 5.1 Reliability & determinism

**NFR-REL-1:** All exercise artifacts MUST be reproducible from stored versions and seeds.
Touches: **[Spec F, G]**

**NFR-REL-2:** Autograding MUST be deterministic given the same submission + tool version + tests.
Touches: **[Spec F, G]**

---

## 5.2 Performance & cost

**NFR-PERF-1:** Define token/cost budgets per workflow stage (plan, generate, verify, hint).
Touches: **[Spec G, H]**

**NFR-PERF-2:** Verification tool calls MUST be bounded (timeouts, max retries).
Touches: **[Spec G, E]**

---

## 5.3 Security & safety

**NFR-SEC-1:** Code execution MUST be sandboxed with strict limits (no network, limited filesystem, CPU/memory/time caps).
Touches: **[Spec E, G]**

**NFR-SEC-2:** Prompt injection defenses apply to any retrieved or user-provided text used in generation (treat as data, not instructions).
Touches: **[Spec E, B]**

---

# 6) Agent Runtime Design

## 6.1 Canonical state machine nodes

Minimum nodes for v0.1:

* `IntakeGoal`
* `RunDiagnostic`
* `BuildPlan`
* `SelectNextConcept`
* `GenerateExercise`
* `VerifyExercise`
* `PresentExercise`
* `AwaitSubmission`
* `GradeSubmission`
* `GenerateHintOrFeedback`
* `UpdateMastery`
* `SummarizeAndLog`
* `AwaitNextSession`
* `TerminalSuccess`
* `TerminalFailure`

Touches: **[Spec C, F, E]**

---

## 6.2 AgentState schema (core fields)

* `run_id: str`
* `learner_id: str`
* `course_id: str | null` (optional; supports authored courses later)
* `actor_role: enum` (`LEARNER|AUTHOR|ADMIN`)
* `goal: GoalSpec`
* `mastery: MasteryState`
* `plan: LearningPlan`
* `current_exercise: ExerciseArtifact | null`
* `exercise_history: [ExerciseAttemptRecord]`
* `tool_calls: [ToolCallRecord]`
* `verification_reports: [VerificationReport]`
* `feedback_artifacts: [HintOrFeedback]`
* `metrics: {tokens, cost, latency_ms, step_count}`
* `errors: [AgentError]`
* `current_node: enum`
* `state_version: str`
* `created_at, updated_at`

Touches: **[Spec C, D, A, F]**

---

## 6.3 Planning contract (structured)

`LearningPlan` MUST include:

* `objective: str`
* `concept_graph_version: str`
* `sessions: [{index, target_concepts, target_difficulty, exercise_mix, success_criteria}]`
* `policies: {hint_level, solution_reveal_allowed, max_attempts_before_review}`

Touches: **[Spec C, A, E]**

---

## 6.4 Loop controls (critical)

* `max_regenerations_per_exercise`
* Detect repeat failures by `(tool_name, args_hash)`
* Force changed plan when verification fails repeatedly (change difficulty, change template, change concept slice)

Touches: **[Spec E, C, F]**

---

# 7) Tool Layer Specification

## 7.1 Tool principles

* Tools are typed functions with JSON schemas (Pydantic/dataclasses).
* Tools validate inputs and return typed outputs/errors.
* “Dangerous” tools are tagged (even in sandbox) for governance and audit.

Touches: **[Spec A, B, E, G]**

---

## 7.2 Minimum tool set (v0.1)

### Content & concept tools

* `concepts.list(course_id) -> [Concept]`
* `concepts.get_graph(course_id, version) -> ConceptGraph`
* `content.store_artifact(artifact, visibility, version_tag) -> ArtifactRef`
* `content.get_artifact(ref) -> Artifact`

Touches: **[Spec D, B, G]**

### Exercise generation tools

* `exercise.generate(spec: ExerciseSpec, seed: int) -> ExerciseDraft`
* `exercise.compile(draft: ExerciseDraft) -> ExerciseArtifact`

  * Produces structured fields: prompt, signature, starter_code, reference_solution, tests, metadata.

Touches: **[Spec A, B]**

### Verification tools (self-verification)

* `sandbox.run_code(code, tests, limits) -> ExecutionReport`
* `exercise.verify(artifact: ExerciseArtifact, repeats: int) -> VerificationReport`

  * Runs reference solution + tests multiple times (flake detection)
  * Ensures signature matches prompt
  * Ensures no forbidden imports/calls (policy)

Touches: **[Spec G, E, F]**

### Grading tools

* `grader.grade(submission, artifact_ref, limits) -> GradeReport`

Touches: **[Spec B, F, G]**

### Memory tools

* `memory.update_mastery(learner_id, deltas) -> MasteryState`
* `memory.get_mastery(learner_id) -> MasteryState`

Touches: **[Spec D]**

### Observability tools

* `trace.log_event(run_id, event) -> Ack`
* `trace.export_run(run_id) -> TraceBundle`

Touches: **[Spec F, G]**

---

## 7.3 Tool error taxonomy (mandatory)

All tools MUST return either `result` or `error` with:

* `error_code: enum` (`ValidationError|AuthError|RateLimitError|TransientError|PermanentError|ConflictError|SandboxViolation`)
* `retryable: bool`
* `safe_user_message: str`
* `debug_context: object` (server-side only)

Touches: **[Spec B, F, G]**

---

# 8) Exercise Artifact Formats (key to publishability + eval)

## 8.1 ExerciseSpec (input to generation)

Fields (example):

* `concepts: [str]`
* `difficulty: 1..5`
* `task_type: enum` (`function_implementation|bugfix|refactor|performance|explain`)
* `constraints: {time_complexity?: str, forbidden?: [str], required?: [str]}`
* `signature: {name, args, returns}`
* `rubric: {criteria}`

Touches: **[Spec A, C]**

## 8.2 ExerciseArtifact (compiled output)

* `artifact_id`
* `prompt_markdown`
* `starter_code`
* `reference_solution` (secured; not shown to learner)
* `public_tests` (optional)
* `hidden_tests` (secured)
* `metadata: {concepts, difficulty, seed, generator_version, created_at}`
* `safety: {forbidden_imports, max_runtime_ms, memory_mb}`

Touches: **[Spec A, E, F, G]**

---

# 9) Human-in-the-Loop (where it belongs here)

Unlike CourseOps (where side effects require approval), StudyCoach approvals are mainly about **content quality and policy boundaries**.

## 9.1 Author review queue (optional but powerful)

* “Quarantine” exercises that pass tests but look suspicious (too hard, ambiguous prompt, solution too long, etc.).
* Author can approve/edit/reject, producing a labeled dataset for future improvements.

Touches: **[Spec I, F, D]**

---

# 10) Evaluation & Observability

## 10.1 Tracing (mandatory)

Record per run:

* node transitions
* model calls (prompt hash, model id/version, tokens, latency)
* tool calls (args, outputs, errors)
* verification reports
* grading reports
* hint steps used

Expose a per-run trace graph UI.

Touches: **[Spec F, G, I]**

---

## 10.2 Offline eval harness (dataset-free strategy)

You don’t need email. You can evaluate with:

1. **Synthetic learner agents** (scripted behaviors)

   * makes common mistakes
   * requests hints
   * retries
2. **Regression suite of goals**

   * “learn recursion”
   * “learn list comprehensions”
   * “practice unit testing”
3. **Deterministic scoring**

   * exercise validity rate (verification pass)
   * grading correctness
   * hint policy compliance
   * loop/non-halting rate
   * cost per completed exercise

Touches: **[Spec F, C, H]**

---

## 10.3 Core metrics

* **Exercise Validity Rate:** % exercises that verify successfully
* **Flake Rate:** % exercises with nondeterministic tests
* **Learner Progress Proxy:** improvement in pass rate over sessions (per concept)
* **Hint Efficiency:** attempts-to-pass and hint-count-to-pass
* **Policy Violations:** solution leaked when not allowed, hidden tests exposed, etc.
* **Cost/Latency:** per session and per exercise

Touches: **[Spec F, G, E]**

---

# 11) Model Strategy

## 11.1 Suggested model roles

* **Planner**: creates learning plan, selects next concept
* **Generator**: creates exercise drafts
* **Verifier/Critic (LLM)**: reviews prompt clarity and checks for ambiguity (in addition to deterministic sandbox verification)
* **Tutor**: generates hints/feedback with policy constraints
* **Safety/Policy**: lightweight classifier or rules + optional small model

Touches: **[Spec H, E, C, F]**

## 11.2 Node-specific decoding policies

* Schema/tool JSON: low temperature, strict structured output
* Hint drafting: moderate temperature but bounded format
* Critic: low temperature, deterministic preference

Touches: **[Spec A, H]**

---

# 12) Deployment & Infrastructure (production-shaped, even in v0.1)

## 12.1 Service boundaries (suggested)

* `studycoach-agent` (orchestrator)
* `sandbox-runner` (isolated execution service)
* `content-store` (Postgres + object store)
* `memory-store` (Postgres; vector store optional later)
* `trace-store` (logs/metrics)

Touches: **[Spec G, D, F]**

## 12.2 APIs (suggested)

* `POST /v1/runs` (start/continue session)
* `GET /v1/runs/{run_id}` (status + trace)
* `POST /v1/submissions` (submit solution)
* `GET /v1/progress` (mastery + plan)

Touches: **[Spec G, I]**

---

# 13) Acceptance Criteria (“Definition of Done” for v0.1)

1. **Self-verification works:** ≥ 95% of generated exercises pass verification without human intervention.
2. **No broken grading:** deterministic grading (same submission → same result).
3. **Hint policy compliance:** default mode never reveals full solution; violations logged as errors.
4. **Durable runs:** user can disappear and resume; no state corruption; consistent next exercise selection.
5. **Traceability:** every session produces a trace graph with tool calls, verification, grading, and costs.
6. **Offline regression suite:** at least 30 scripted scenarios pass in CI.

Touches: **[Spec F, C, D, E, G]**

---

# 14) Implementation Plan (practical “things to do”)

## Phase 0: Minimal skeleton (1 steel thread end-to-end)

* Define **schemas**: `GoalSpec`, `ExerciseSpec`, `ExerciseArtifact`, `GradeReport`, `MasteryState`, `AgentState`.
* Implement orchestrator with the core nodes.
* Implement sandbox runner (local Docker or restricted exec) with strict limits.
* Implement verification step (reference solution + tests).
* Minimal UI: CLI or simple web form.

Touches: **[Spec A, C, G]**

## Phase 1: Make it reliable (where agents become real)

* Add structured errors + retries with loop detection.
* Add trace logging + replay of tool calls (in research-mode with mocks).
* Add deterministic seeds + artifact versioning.

Touches: **[Spec E, F, G, D]**

## Phase 2: Personalization (mastery + adaptive planning)

* Implement concept graph and mastery update rules.
* Add diagnostic and adaptive plan repair.
* Add “hint ladder” and measure hint efficiency.

Touches: **[Spec D, C, F, I]**

## Phase 3: Evaluation harness (publishability engine)

* Build synthetic learners + golden scenarios.
* Create CI gates and dashboards.

Touches: **[Spec F, H]**

---

# 15) Why this is a great steel thread (in agentic terms)

This design forces you to solve the problems that separate toy agents from systems:

* **Structured tool I/O** everywhere (exercises, grading, verification).
* **Explicit state machine** with durable checkpoints.
* **Tools with real failure modes** (sandbox execution, flaky tests, timeouts).
* **Guardrails that matter** (no solution leakage, hint-first).
* **Evaluation that’s objective** (tests pass/fail, verification reports, cost).
* **Long-running personalization** without needing private datasets.

It’s agent engineering with receipts.

---

If you build exactly this v0.1 steel thread, you’ll have a platform that can later grow into “CourseForge” (course creation) simply by adding an authoring workflow that generates concept graphs + modules + exercise banks using the same self-verifying machinery.
