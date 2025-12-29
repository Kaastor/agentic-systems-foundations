# CourseOps Agent Technical Specification v0.1

**Purpose:** CourseOps Agent is a production-shaped agentic system that reduces instructor/TA operational load by triaging course communications, scheduling meetings/office hours, and answering course-policy questions **with citations**, while requiring **human approval** for side‑effecting actions. It is **long‑running**, **auditable**, and **evaluated**.

**Steel thread (canonical workflow):**
**Inbox triage → policy-grounded draft response (citations) → optional scheduling action → human approval → execution → logged + evaluated.**

---

## Specialization Legend

* **[Spec A]** Structured LLM I/O & Tool Schema Engineering
* **[Spec B]** RAG & Tooling for Agentic Systems
* **[Spec C]** Agent State Machines, Planning & Hierarchical Agents
* **[Spec D]** Memory, Long-Term Context & Durable State
* **[Spec E]** Guardrails, Safety, Security & Governance
* **[Spec F]** Evaluation, Testing, Observability & Experimentation
* **[Spec G]** Performance, Scaling & Agent Infrastructure
* **[Spec H]** Model Selection, Customization & Multi‑Model Systems
* **[Spec I]** UX, Human‑in‑the‑Loop & Productizing Agents

Throughout this spec, sections and requirements are annotated with tags like **Touches: [Spec B, Spec F]**.

---

## 1) Scope

### 1.1 In scope (MVP → v1)

* **Communication triage** for course-related messages (email + optionally LMS/Slack/Teams).
  Touches: **[Spec B, C, F, I]**
* **Policy Q&A with citations** over course materials (syllabus, rubric, deadlines, policies).
  Touches: **[Spec B, A, E, F]**
* **Drafting responses** (never auto-send by default).
  Touches: **[Spec A, I, E]**
* **Scheduling workflows** (office hours appointments, meeting coordination) with human approval.
  Touches: **[Spec B, C, E, I]**
* **Long-running tasks** (follow-ups, awaiting user response, reminders, resumable state).
  Touches: **[Spec D, G, C, F]**
* **Logging/tracing + evaluation harness** (offline regression tests + production metrics).
  Touches: **[Spec F, G]**

### 1.2 Explicit non-goals (for v0.1)

* Full “solve the homework” tutoring. (Allowed: hint-first help *if configured*.)
  Touches: **[Spec E, I]**
* Automated grading decisions or grade changes. (Can draft rubric-based feedback with approvals.)
  Touches: **[Spec E, I]**
* Fully autonomous outbound communication (auto-send) without approval.
  Touches: **[Spec E, I]**
* Self-modifying tool permissions (agent cannot grant itself new privileges).
  Touches: **[Spec E]**

---

## 2) Personas and Roles

### 2.1 User personas

* **Instructor**: approves sends/invites, configures policies, views analytics.
  Touches: **[Spec I, E]**
* **TA**: can approve some actions (configurable), triages, drafts replies.
  Touches: **[Spec I, E]**
* **Student**: receives responses, may request scheduling.
  Touches: **[Spec I, E]**
* **Admin/Teaching center (optional)**: governance, compliance, deployment.
  Touches: **[Spec E, G]**

### 2.2 Access control (RBAC)

Define roles and capabilities:

* `INSTRUCTOR_ADMIN`: full course config + approvals
* `TA_EDITOR`: can draft, can approve limited actions (configurable)
* `STUDENT`: can initiate requests, cannot view internal logs
* `AUDITOR`: read-only audit export

Touches: **[Spec E, I]**

---

## 3) System Overview and Architecture

### 3.1 High-level components

1. **Agent Orchestrator Service** (core runtime)

   * state machine dispatcher
   * planning + tool execution
   * policy checks + approvals
     Touches: **[Spec C, E, G]**

2. **Tool Layer / Connectors** (Email, Calendar, LMS, Docs)

   * typed schemas + validation
   * idempotency + retries
   * permissions + audit hooks
     Touches: **[Spec A, B, E, G]**

3. **Knowledge / RAG Service** (course corpus, citations)

   * indexing + metadata filtering
   * injection defenses
   * evidence objects (DocumentHit)
     Touches: **[Spec B, E]**

4. **State + Memory Store**

   * durable AgentState snapshots
   * conversation summaries + per-course memory
     Touches: **[Spec D, G]**

5. **Observability + Evaluation Stack**

   * traces, logs, metrics, dashboards
   * offline eval harness and golden test suite
     Touches: **[Spec F, G]**

6. **Web UI (CourseOps Console)**

   * inbox view + triage suggestions
   * approval queue + diff editor
   * evidence/citations view
     Touches: **[Spec I]**

7. **Model Gateway**

   * provider abstraction
   * per-node model selection
   * rate limiting and caching
     Touches: **[Spec H, G]**

---

## 4) Functional Requirements

### 4.1 Inbox ingestion & triage

**FR-INBOX-1:** System SHALL ingest course-relevant messages from configured channels (email required; LMS/Slack optional).
Touches: **[Spec B, G]**

**FR-INBOX-2:** System SHALL classify each message into a triage category:
`PolicyQuestion | Scheduling | GradingDispute | ExtensionRequest | ContentHelp | Admin | Other`
Touches: **[Spec A, C, H]**

**FR-INBOX-3:** System SHALL extract structured fields when possible:
`course_id, student_id (if known), topic, deadline, urgency, requested_action`
Touches: **[Spec A, C]**

**FR-INBOX-4:** System SHALL propose a response plan with an explicit next step and required tools.
Touches: **[Spec C]**

**FR-INBOX-5:** System SHALL route messages to an approval queue when a side-effecting action is proposed (send email, create invite, post announcement).
Touches: **[Spec E, I, C]**

### 4.2 Policy-grounded Q&A (“RAG with receipts”)

**FR-RAG-1:** System SHALL answer policy questions using only course-approved corpora (syllabus, rubric, announcements, policy docs), and SHALL attach citations.
Touches: **[Spec B, E, A]**

**FR-RAG-2:** System SHALL represent evidence as structured objects, not pasted text blobs, in AgentState (see DocumentHit schema).
Touches: **[Spec B, C, D]**

**FR-RAG-3:** System SHALL refuse or ask for clarification when evidence is insufficient.
Touches: **[Spec E, A]**

**FR-RAG-4:** System SHALL defend against indirect prompt injection from retrieved documents by treating retrieved content as untrusted data.
Touches: **[Spec E, B]**

### 4.3 Drafting and sending communications

**FR-COMMS-1:** System SHALL generate **draft** replies with tone controls (professional, concise), and SHALL label factual claims vs policy citations.
Touches: **[Spec A, I, B]**

**FR-COMMS-2:** System SHALL never send messages without explicit approval unless course config enables auto-send for narrow safe cases.
Touches: **[Spec E, I]**

**FR-COMMS-3:** Approval UI SHALL allow “edit before send” with diff view and “why this draft” explanation (non-CoT).
Touches: **[Spec I, E]**

**FR-COMMS-4:** All outbound actions SHALL be idempotent (no duplicate sends/invites on retries).
Touches: **[Spec B, G, E]**

### 4.4 Scheduling workflows

**FR-SCHED-1:** System SHALL propose meeting times based on instructor/TA availability windows and constraints (office hours rules, time zones).
Touches: **[Spec B, C, H]**

**FR-SCHED-2:** System SHALL draft calendar invites and email confirmations, and SHALL require approval before creating calendar events (default).
Touches: **[Spec E, I, A]**

**FR-SCHED-3:** System SHALL support “AwaitUser” state for scheduling back-and-forth and resume reliably.
Touches: **[Spec D, C, G]**

### 4.5 Long-running tasks & reminders

**FR-LONG-1:** System SHALL persist AgentState after each node execution (checkpointing).
Touches: **[Spec D, F, C]**

**FR-LONG-2:** System SHALL resume workflows via webhook triggers (new reply received, approval decision, scheduled timer).
Touches: **[Spec D, G, C]**

**FR-LONG-3:** System SHALL support time-based reminders (e.g., “follow up in 48 hours if no response”).
Touches: **[Spec D, G]**

### 4.6 Administration & configuration

**FR-CONFIG-1:** System SHALL support per-course configuration including: corpora selection, tool permissions, auto-send policy, integrity rules, escalation rules.
Touches: **[Spec E, I, G]**

**FR-CONFIG-2:** System SHALL support role-based approval policies (TA can approve invites but not send grades-related emails, etc.).
Touches: **[Spec E, I]**

---

## 5) Non-Functional Requirements

### 5.1 Reliability

**NFR-REL-1:** For any side-effecting action, system MUST provide an audit trail: who approved, what changed, and what was executed.
Touches: **[Spec E, F]**

**NFR-REL-2:** System MUST be able to replay a run deterministically given stored prompts, tool I/O, and config snapshot (within stochastic tolerance).
Touches: **[Spec F, C, G]**

### 5.2 Performance and cost

**NFR-PERF-1:** Provide token/cost budgets per workflow (triage, RAG answer, scheduling) and enforce max steps.
Touches: **[Spec G, C, H]**

**NFR-PERF-2:** Implement caching where safe (RAG results, stable prompt prefixes, availability lookups).
Touches: **[Spec G, D, B]**

### 5.3 Security, privacy, compliance

**NFR-SEC-1:** PII and student records MUST be handled per institutional policy; include configurable retention, redaction, and access controls.
Touches: **[Spec E, D, G]**

**NFR-SEC-2:** Secrets MUST remain outside model context; tools must use server-side auth tokens and least privilege.
Touches: **[Spec E, B]**

### 5.4 Maintainability

**NFR-MAINT-1:** Prompts, schemas, and state machine versions MUST be versioned and tied to eval results in CI.
Touches: **[Spec F, A, C, G]**

---

## 6) Agent Runtime Design

### 6.1 State machine (canonical)

**Node states (minimum):**

* `Intake`
* `Classify`
* `RetrieveEvidence`
* `Plan`
* `DraftResponse`
* `PolicyCheck`
* `HumanReview` (optional)
* `ExecuteTools` (optional)
* `SummarizeAndLog`
* `AwaitUser`
* `TerminalSuccess`
* `TerminalFailure`

Touches: **[Spec C, E, F]**

### 6.2 AgentState schema (core fields)

* `run_id: str`
* `course_id: str`
* `user_context: {actor_role, actor_id}`
* `channel_context: {email_thread_id, message_ids, calendar_thread_id}`
* `conversation_history: [Message]` (bounded)
* `task_type: enum`
* `plan: Plan` (structured)
* `evidence: [DocumentHit]`
* `tool_calls: [ToolCallRecord]`
* `drafts: [DraftArtifact]`
* `approvals: [ApprovalRequest]`
* `memory_refs: [MemoryRef]`
* `metrics: {tokens, cost, latency_ms, step_count}`
* `errors: [AgentError]`
* `state_version: str`
* `current_node: enum`
* `created_at, updated_at`

Touches: **[Spec C, D, F, A]**

### 6.3 Planning contract

* Plans MUST be structured:

  * `steps: [{goal, required_tools, dependencies, success_criteria}]`
  * `risk_level: Low|Medium|High`
  * `requires_approval: bool`
* Plan-to-graph conversion MUST produce explicit nodes with step index.

Touches: **[Spec C, A, E]**

### 6.4 Loop controls

* Max steps per run (configurable)
* Loop detection on `(tool_name, args_hash)` with backoff + forced replan
* “Stuck” detection triggers escalation to human

Touches: **[Spec E, C, F]**

---

## 7) Tool Layer Specification

### 7.1 Tool interface principles

* Tools are typed functions with JSON schemas (Pydantic/dataclasses).
* Tools MUST validate inputs and return typed outputs or typed errors.
* Write tools MUST support idempotency keys and produce audit events.

Touches: **[Spec A, B, E, G]**

### 7.2 Minimum tool set (v0.1)

#### Email tools

* `email.search_threads(query, course_id) -> [EmailThreadSummary]`
* `email.get_thread(thread_id) -> EmailThread`
* `email.create_draft_reply(thread_id, body, metadata) -> DraftId`
* `email.send_draft(draft_id, idempotency_key) -> SendReceipt` **(DANGEROUS)**
* `email.label_thread(thread_id, label) -> LabelReceipt` *(can be safe or dangerous depending on policy)*

Touches: **[Spec A, B, E]**

#### Calendar tools

* `calendar.find_availability(participants, window, constraints) -> [TimeSlot]`
* `calendar.create_invite(details, idempotency_key) -> InviteReceipt` **(DANGEROUS)**
* `calendar.update_invite(invite_id, patch, idempotency_key) -> InviteReceipt` **(DANGEROUS)**

Touches: **[Spec A, B, E, G]**

#### Knowledge tools (RAG as tool)

* `kb.search_course_docs(query, course_id, k, filters) -> [DocumentHit]`
* `kb.get_doc(doc_id) -> Document`
* `kb.list_sources(course_id) -> [SourceMetadata]`

Touches: **[Spec B, A, E]**

#### Admin/config tools

* `course.get_config(course_id) -> CourseConfig`
* `course.update_config(course_id, patch) -> ConfigReceipt` **(DANGEROUS; admin only)**

Touches: **[Spec E, A]**

### 7.3 Tool error taxonomy (mandatory)

* `ValidationError` (bad args)
* `AuthError`
* `RateLimitError`
* `TransientError`
* `PermanentError`
* `ConflictError` (idempotency / state mismatch)

Tools MUST return `error_code`, `retryable`, and `safe_user_message`.

Touches: **[Spec B, G, F]**

---

## 8) Knowledge Base and Grounding

### 8.1 Corpora

* Syllabus, schedule, rubric, assignment specs
* Staff policies (extensions, late work, regrades)
* Course announcements and pinned messages
* Optional: institutional teaching policies

Each document MUST have:

* `source_id`, `version`, `effective_date`, `visibility` (students/staff), `tags`

Touches: **[Spec B, E, D]**

### 8.2 Citation requirement

All policy answers MUST include citations to `source_id` + section anchors when available.

Touches: **[Spec B, F, I]**

### 8.3 Injection defenses

* Retrieved text is **data-only**; never treated as system instructions.
* RAG tool returns structured snippets with provenance.
* Policy check rejects drafts that contain “tool directives” derived from docs.

Touches: **[Spec E, B]**

---

## 9) Human-in-the-Loop (Approvals)

### 9.1 Approval policy

Actions requiring approval by default:

* send email
* create/update calendar invite
* post announcement
* access sensitive student records (if ever enabled)
* any message categorized as `GradingDispute` or involving exceptions

Touches: **[Spec E, I]**

### 9.2 Approval artifact

Approval request MUST contain:

* proposed action(s) + structured parameters
* draft message/invite content
* evidence used (citations)
* risk level + policy reason
* “what changed since last attempt” (if retry)

Touches: **[Spec I, F, C, E]**

### 9.3 Editor and provenance

Approver can:

* approve as-is
* edit + approve
* reject with feedback (stored as training/eval signal)

Edits are stored as diffs tied to run_id.

Touches: **[Spec I, F, D]**

---

## 10) Evaluation and Observability

### 10.1 Tracing and logs (mandatory)

For every run, record:

* node transitions with timestamps
* model calls: model id/version, prompt hash, output, tokens, latency
* tool calls: args, outputs, errors
* approvals: who/when/edits
* final outcome category

Expose per-run “trace graph” UI.

Touches: **[Spec F, G, I]**

### 10.2 Offline eval harness

Maintain golden scenarios:

* 50–200 message threads across categories
* expected: correct triage, correct citations, correct refusal, correct escalation
* deterministic tool mocks

Metrics:

* classification accuracy
* citation precision/recall (or heuristic)
* “answer leakage” rate (did it reveal forbidden solution?)
* escalation rate for high-risk tasks

Touches: **[Spec F, C, E, B]**

### 10.3 Online monitoring

Dashboards:

* success rate by workflow
* average steps/run
* human approval rate + edit rate
* cost per resolved item
* latency p50/p95
* top failure modes taxonomy

Alerts:

* spikes in refusal, hallucination, or tool errors
* cost anomalies
* repeated loop detections

Touches: **[Spec F, G]**

---

## 11) Model Strategy

### 11.1 Model roles (recommended)

* **Router/Classifer** (fast, cheap)
* **RAG Answerer** (grounded, citation-aware)
* **Planner** (strong reasoning)
* **Draft Writer** (tone + clarity)
* **Policy/Safety Checker** (can be separate small classifier + rules)
* Optional **Critic** (best-of-N selection)

Touches: **[Spec H, C, E, F]**

### 11.2 Per-node decoding policies

* Tool selection + schema generation: low temperature, strict JSON mode
* Drafting text: moderate temperature, still bounded
* Critic: deterministic or low temperature

Touches: **[Spec A, H]**

### 11.3 Future: customization

* SFT for schema adherence and consistent drafting style
* Verifier training from approval outcomes + edits
* RL only after verifiers/evals are strong

Touches: **[Spec H, F, A]**

---

## 12) Deployment, Configuration, and Infrastructure

### 12.1 Service boundaries

* `courseops-agent` (orchestrator)
* `courseops-kb` (index + retrieval)
* `courseops-ui` (console)
* `model-gateway`
* `worker` (async jobs)
* `db` (Postgres) + `object_store` + optional `vector_store`

Touches: **[Spec G, B, D]**

### 12.2 API surfaces (suggested)

* `POST /v1/runs` (create run from event or user action)
* `GET /v1/runs/{run_id}` (status + trace)
* `POST /v1/runs/{run_id}/approve` (approve/reject/edit)
* `POST /v1/webhooks/email`
* `POST /v1/webhooks/calendar`
* `POST /v1/webhooks/timer`

Touches: **[Spec G, C, I]**

### 12.3 Configuration and feature flags

Configurable per course:

* allowed tools
* approval thresholds
* “hint-only” vs “direct answer” policy
* model assignments
* budgets (steps/tokens/cost)

Touches: **[Spec G, E, H]**

---

## 13) UX Requirements (CourseOps Console)

### 13.1 Core UI views

* **Inbox view**: triage categories, suggested next action
* **Run trace view**: plan, tool usage, evidence, costs
* **Approval queue**: approve/edit/reject with diff
* **Knowledge sources**: upload/version course docs; see index status
* **Analytics**: trends, stuck points, workload stats

Touches: **[Spec I, F, B]**

### 13.2 Trust and legibility

UI MUST show:

* which docs were cited
* which tools were used and why (short explanation)
* what is pending approval
* uncertainty/need-more-info flags

Touches: **[Spec I, F, E]**

---

## 14) Data Storage and Retention

### 14.1 Storage classes

* **Durable state** (Postgres): AgentState snapshots, tool calls metadata, approvals, configs
  Touches: **[Spec D, G, F]**
* **Artifacts** (object store): draft bodies, attachments, trace exports
  Touches: **[Spec G, D]**
* **Vectors/Index** (vector DB or Postgres extension): doc chunks + metadata
  Touches: **[Spec B, G]**

### 14.2 Retention policy (configurable)

* Default retention windows for logs and drafts
* “forget student” / de-index content capability
* audit export for compliance

Touches: **[Spec E, D]**

---

## 15) Acceptance Criteria (“Definition of Done” for v0.1)

1. **Inbox triage** works on real course email with >80% correct category accuracy on a labeled eval set.
   Touches: **[Spec F, H]**

2. **Policy answers** include citations and refuse when evidence is missing; hallucination rate below defined threshold on eval set.
   Touches: **[Spec B, E, F]**

3. **No side-effecting action** occurs without approval (unless explicitly enabled in config and tested).
   Touches: **[Spec E, I, F]**

4. **Every run is traceable**: you can reconstruct what happened from logs and view it in the console.
   Touches: **[Spec F, I]**

5. **Long-running flows** resume correctly and do not duplicate sends/invites.
   Touches: **[Spec D, G, E]**

6. **CI gates**: a golden-flow suite passes for the steel-thread workflows.
   Touches: **[Spec F, G, C]**

---

## 16) Implementation Notes (recommended engineering constraints)

* Treat prompts + schemas as **versioned artifacts**; link each deployment to an eval report.
  Touches: **[Spec F, A, G]**
* Keep the agent **explicitly graph-shaped**, not an implicit chat loop.
  Touches: **[Spec C]**
* Prefer deterministic tools/DB queries over fuzzy retrieval when possible (deadlines, rosters).
  Touches: **[Spec B]**
* Make approvals first-class objects, not UI sugar.
  Touches: **[Spec I, E]**
* Build eval harness early; use it as the learning and shipping throttle.
  Touches: **[Spec F]**

---

If you treat this as your reference spec, you can now “compile” each specialization into concrete work items: **Spec A writes the tool schemas**, **Spec B builds the KB/RAG**, **Spec C implements the graph**, **Spec F creates the eval harness**, and **Spec I ships the approval console**—all orbiting the same CourseOps steel thread.
