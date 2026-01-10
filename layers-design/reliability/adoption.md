# Kernel Adoption Guide
**Also known as:** Maturity Levels + Build Order + Repo Architecture + Teaching Track  
**Core language:** Python  
**Status:** Operationalization layer for the Kernel Blueprint (TCB)  
**Version:** v1.1  
**Last updated:** 2026-01-05

---

## 0. What this document is (and isn’t)

This guide turns the **kernel blueprint** into an *implementation plan*:

- **Day‑one mandatory vs conditional vs later hardening**
- **Dependency / build order** (what must exist before what)
- **Repository architecture** that keeps the **TCB small**
- **Teaching track** so undergrads learn the transferable ideas without drowning in enterprise plumbing

This guide is method‑agnostic about planning/RAG/model provider. It assumes the kernel/strategy boundary and enforcement rule defined in `layers-design/reliability/implementation_playbook.md` (see "Architecture you can defend in a review").

---

## 1. Operating definitions

### 1.1 Kernel (TCB)
The **kernel** is the **Trusted Computing Base (TCB)**: the smallest set of code + policies that must remain correct for *all side effects, safety properties, and audit claims* to hold.

### 1.2 Strategy modules (userland)
**Strategies** are replaceable modules that propose what to do (planner, prompts, routing, RAG, multi-agent coordination). They are allowed to be wrong. The kernel must remain safe anyway.

### 1.2.1 Testbed modules (research harness)

The **testbed** is the “wind tunnel” for agentic systems research: scenario packs + environment adapters + statistical harness that let you compare strategies *fairly* and *reproducibly*.

**Where it lives (architecturally):**
- The testbed is **kernel-adjacent but NOT TCB**. It should be a separate package/module that depends on kernel ports (K1/K2/K11/K12/K16), never the reverse.
- The testbed MUST NOT weaken kernel invariants; it only selects **run modes** and **adapters**.

**Mechanics vs methods:**
- **Mechanics in kernel:** record/replay, eval harness, policy gating, deterministic orchestration.
- **Methods in strategy:** planners/search/critique/RAG/etc.
- Research iteration is: *swap strategies; keep kernel + testbed mechanics constant*.

**Real tools in research (recommended, not forbidden):**
- Use real tools when it increases external validity, but do it via:
  - sandbox/staging endpoints or ephemeral tenants/accounts for write tools,
  - `record` mode for reproducibility,
  - `shadow` mode for preview-only “would-have” evaluation,
  - `replay`/`sim` for deterministic regression + ablations.

**Publishable baseline (rule of thumb):**
If you want results you can defend in peer review, treat “research runs” as **Level 2 governance minimum** even if you have no end users: K11 + K12/K12a + K16-min are non-negotiable for credibility.


### 1.3 A practical rule
Use the kernel/strategy boundary rule from `layers-design/reliability/implementation_playbook.md` ("Architecture you can defend in a review"). This guide assumes that split.

### 1.4 Privileged capabilities (not just “writes”)

A **privileged capability** is any tool or access path that can:

- change external state (**writes**),
- read **sensitive or scoped data** (secrets, PII/customer content, internal tickets/docs with ACLs, cross‑tenant data),
- mint/upgrade permissions or credentials.

**Implication:** a “read‑only agent” can still require a policy gate if it can read sensitive or ACL’d data. In those cases adopt **K5‑lite**: allowlist read tools by principal, enforce query/scope/ACL constraints, and log allow/deny decisions.

### 1.5 “Production” in this guide (internal pilot vs external production)

This guide uses two practical thresholds:

- **Internal pilot production:** real users, limited blast radius (single team, limited data sensitivity, low stakes).  
  **Minimum required** for internal pilot:
  - **K12 (full gates)** appropriate to your risks (regression + injection + tool-misuse packs).
  - **K12a (eval corpus governance)** for any suite used as a gate: suite cards, immutable versions, flake policy, and pinned suite hashes.
  - **K16-min (bundle manifest + provenance)**: every run records a `bundle_id` referencing the exact prompts/policies/tool manifest/verifiers/schemas (and gated eval suite versions, if applicable). Rollback = redeploy a previous bundle.
  - **Risk Register** updated for each release that changes a production path (prompts/policies/tools/memory/evals/config).
  - Operational ownership (on-call or named operator) and incident intake.

- **External production:** customer-facing, multi-user, high-stakes, or sensitive data at scale.  
  **Requires**:
  - Everything from internal pilot, plus **K16-full** (progressive delivery + rollback + migrations) and deeper operational readiness (runbooks, incident playbooks, rollback drills, monitoring).

#### K16-min vs K16-full (practical split)
**K16-min (“record what is running”)** is the minimum change control you need once real users exist:
- A **versioned artifact bundle** (or “bundle manifest”) that includes *at minimum*:
  - schema/ABI version,
  - policy bundle ID/hash,
  - tool manifest ID/hash,
  - prompt bundle ID/hash,
  - verifier versions/hashes,
  - workflow/strategy version (optional but strongly recommended),
  - gated eval suite versions/hashes (when used for release gates).
- Every run records `bundle_id` (and component hashes) in its trace header.
- Rollback is “deploy the previous bundle” (no bespoke hotfixes).

**K16-full (“operate safely at scale”)** adds:
- canary / staged rollout, automated rollback triggers,
- compatibility/migrations for stored state and memories,
- rollback drills as routine operations,
- CI enforcement that prevents “silent edits” to gated eval suites, prompts, or policies.

**Rule of thumb:** If you have **high-risk actions** (writes, privileged reads, secrets, external comms), treat even an “internal pilot” as requiring K16-full-level rigor.


---

## 2. Adoption matrix: what’s mandatory, when

### 2.1 Three lanes of adoption
Pick the lane that matches your product’s “blast radius”:

1. **Read‑only agent** (no writes, no external irreversible actions)  
2. **Action agent** (can change external state via tools)  
3. **Multi‑tenant enterprise** (isolation, compliance, governance)

The kernel grows by *constraints required*, not by ambition.

### 2.2 Day‑one vs conditional vs later hardening

**Interpretation used here**
- **Day‑one mandatory:** you cannot get reliable constrained behavior without it, even in a small demo.
- **Conditional:** required once a capability exists (side effects, memory, code execution, multi‑tenant, etc.).
- **Later hardening:** required before “real production” at scale or high stakes; can be staged after a working MVP.

#### Kernel subsystems categorization (K1–K18)

| Subsystem | Category | Trigger | Minimal scope for adoption |
|---|---|---|---|
| **K1 Typed System Model (ABI)** | **Day‑one** | Always | Pydantic models, deterministic serialization, versioning |
| **K2 Deterministic Orchestrator (FSM)** | **Day‑one** | Always | Explicit states + transitions + stop conditions; **cancel/abort is first‑class (quarantine late results)** |
| **K3 Model Boundary (LLM as tool)** | **Day‑one** | Always | Prompt hashing, output validation, bounded repair |
| **K4 Tool Interface + Executor** | **Day‑one** | Any tools | Schema validation, timeouts, typed errors, logging |
| **K5 Reference Monitor + Policy Engine** | **Conditional** | Any privileged capability (writes **or** sensitive reads) | Central allow/deny/approve; **2‑phase commit for writes**; **K5‑lite for sensitive reads** (ACL/query constraints + decision logging) |
| **K6 Budgets + Loop Controls** | **Day‑one** | Always | Hard caps: steps/time/cost/tool retries; **rate limits + concurrency caps when exposed/multi‑tenant** |
| **K7 Verification Layer** | **Day‑one (minimal)** | Always | Schema/type checks at minimum; add domain verifiers over time |
| **K8 Isolation / Sandboxing** | **Conditional** | Code execution/untrusted artifacts | “No network by default”, CPU/mem caps |
| **K9 Observability + Audit Ledger** | **Day‑one** | Always | Structured events + trace IDs; append-only ledger; **classify+redact at ingestion before any write/ship** |
| **K10 Persistence + Resume + Outbox** | **Conditional** | Side effects OR long runs | Durable outbox, idempotency, checkpoints |
| **K11 Replay + Fault Injection** | **Conditional** | Production operations / serious debugging (Level 2+) | Record/replay for model + tool I/O; deterministic clocks/seeds where relevant; replay mode is **side‑effect free**; fault injection/chaos tests |
| **K12 Evaluation Harness + Release Gates** | **Day‑one (minimal) → Later hardening** | Always (full gates required before external production) | MVP: harness skeleton + smoke/regression + injection starter pack; Later: CI gates + canary/shadow eval + auto rollback triggers |
| **K12a Eval Corpus Governance (Suite Cards + immutable suites)** | **Conditional** | Any eval suite used as a release gate (CI/prod) | Suite cards + immutable versioning (no silent edits) + provenance + privacy class + flake policy + min sample sizes; gated releases reference exact suite versions (hash) |
| **K13 Context + Memory Governance** | **Conditional** | Any memory/RAG | Provenance, TTL, validation, “data ≠ instructions” |
| **K14 Identity + Secrets Governance** | **Conditional** | Integrations/secrets | Agent principals, scoped creds, “no secrets in prompt” |
| **K15 Human Oversight UX** | **Conditional** | High-risk actions | Preview/approve/deny, pause/stop, autonomy levels |
| **K16 Change Management + Rollback** | **Later hardening (with a required K16-min slice for real users)** | Real users (K16‑min) / External production (K16‑full) | **K16‑min:** bundle manifest + record `bundle_id` per run + rollback by redeploying a prior bundle. **K16‑full:** canary + automated rollback triggers + migrations + rollback drills |
| **K17 Interop + Portability** | **Later hardening** | Avoid lock‑in | Export schemas/traces/bundles; OTel-like traces |
| **K18 Input Sanitization Pipeline** | **Day‑one** if any untrusted external content | Web/RAG/tool outputs | Quarantine + typed envelopes + suspicion flags; **classify at ingestion** |

**Important nuance:** If you do **RAG** or ingest external text, treat **K18 as Day‑one** even for read-only agents. Prompt injection is not a “later” problem.

---

### 2.3 Release-gated governance artifacts (non-kernel, but mandatory once you have real users)

These artifacts are not “kernel subsystems,” but they are required to keep production operation evidence-based instead of vibe-based.

**Required artifacts**
1. **Risk Register (release-gated)**
   - A living artifact tracking risks, controls, evidence, and explicit acceptance/expiry.
   - Updated for every release that changes: prompts, policies, tool manifests/scopes, connectors, memory behavior, eval gates/thresholds, or deployment config.
   - Stored in-repo (machine-readable preferred) so CI can enforce update rules.

2. **Eval Suite Cards + immutable suite versions (K12a)**
   - Every gated suite has a suite card documenting purpose, risk coverage, provenance, rubric, privacy class, thresholds, and flake policy.
   - Suites used as gates are versioned and **immutable**. Changes produce a new version/hash and changelog entry.

3. **Assurance Case (required for production high-risk actions)**
   - For any production path enabling high-risk capabilities, maintain an assurance case mapping hazards → controls → evidence.
   - The assurance case references the deployed `bundle_id`, enabled capabilities, policy bundle ID, eval suite versions, dashboards, and runbooks.

**Recommended repo placement**
- `ops/governance/risk_register.yaml`
- `ops/governance/assurance_case.yaml` (or per-env files)
- `evals/<suite_name>/SUITE_CARD.yaml` stored alongside suite cases
- `ops/releases/<date>_<bundle_id>.md` (human-readable release note that links to the above)

**CI rule of thumb**
- If a PR changes `prompts/`, `policies/`, `tool_adapters/`, `kernel_tcb/`, `evals/`, or memory rules/config: CI should require:
  - updated risk register (or an explicit “no risk impact” justification),
  - updated suite card/changelog if a gated eval suite changes,
  - a new `bundle_id` (K16-min).
- If PR changes `testbed/`, `benchmarks/`, or eval suite definitions → run the benchmark gate(s), update suite cards/changelog, and require deterministic replay on any new “golden” cases.


---

## 3. Maturity levels (a practical ladder)

Each level is defined by:
- **Permissions surface** (what the agent can do)
- **Minimum kernel invariants** that must hold
- **Exit criteria** (tests + telemetry thresholds)

### Level 0 — Prototype (allowed only on a laptop)
**Purpose:** validate product value, not safety.  
**Risks accepted:** basically all of them.

**Allowed characteristics**
- No real users
- No secrets
- No side effects
- No persistence

**Goal:** get to Level 1 quickly; do not ship Level 0.

---

### Level 1 — Constrained read-only kernel (single user, local)
**Capabilities**
- Deterministic orchestrator
- Read‑only tools (retrieval, parsing, search) allowed
- No external writes

**Minimum kernel**
- K1, K2, K3, K4, K6, K7(min), K9, K18(if external content)
- **K5‑lite** *(only if any privileged reads)*: allowlist + scope/ACL constraints + decision logging
- **K12 (minimal)**: harness skeleton + smoke regression + injection starter pack


**Exit criteria**
- End-to-end trace exists for every run (`trace_id`, `run_id`)
- Hard stop conditions work (no infinite “continue”)
- **Cancel/abort works**: abort stops the run; late tool/model results are quarantined/discarded
- Malformed model/tool output fails closed and produces typed errors
- Minimal eval harness runs in CI (even if tiny)

---

### Level 2 — Production read-only assistant (with RAG/memory)

**Note:** Level 2 can be used for an *internal pilot*. For **external production**, treat **K16** as mandatory (see §1.5).

**Capabilities**
- Retrieval + memory
- Document-grounded answers with provenance
- Still **no** external writes

**Minimum kernel (incremental)**
- Level 1 plus **K13** (memory governance)
- **K5‑lite** (policy gate for privileged reads): ACL/scope constraints, default deny, decision logging
- **K12 (full gates)** required for real users (regression + injection + tool-misuse packs)
- **K12a** required for any suite used as a gate: suite cards + immutable versions + flake policy + pinned suite hashes
- **K11 (record/replay)** required for production operations: record/replay model + tool I/O; replay mode is side‑effect free
- **K16‑min required before any real users**: bundle manifest + record `bundle_id` per run + rollback by redeploying a prior bundle
- **K16‑full required before external production**
- **Risk Register required for any production path** (internal pilot or external): updated each release and linked to evidence (tests/eval run IDs/dashboards)


**Exit criteria**
- Retrieval injection suite passes (direct + indirect injection cases)
- Memory writes are validated, provenance-tagged, TTL’d (suspicious writes are quarantined)
- You can reproduce a representative incident end-to-end using replay (no live model/tool calls)
- **Every run records `bundle_id`** (K16‑min) and you can reload that bundle to reproduce behavior
- **Gated eval suites have suite cards** and pinned suite versions/hashes (no silent edits)
- **Risk register updated for the release** (or explicit “no risk impact” justification) and evidence links refreshed
- Constraint violation rate and budget exhaustion are within targets


---

### Level 3 — Action agent (state changes via tools)
**Capabilities**
- Sends emails, creates tickets, opens PRs, modifies config, etc.

**Minimum kernel (incremental)**
- Level 2 plus **K5, K10, K14, K15**
- K8 if executing code or handling untrusted artifacts
- **K12 full gates + K12a** are required before any action agent is exposed to real users
- **K16‑min required before any real users** (bundle manifest + record `bundle_id` per run)
- **K16‑full required before external production**
- **Assurance case required for any production high-risk capability** (hazards → controls → evidence; references `bundle_id`)
- **Risk register updated for each release** affecting action capabilities/tools/policies/memory/evals/config


**Exit criteria**
- **Two‑phase execution** (Propose → Preview → Approve → Commit) is enforced
- Approvals are bound to exact tool+args+preview hash and expire
- Durable outbox prevents duplicate side effects on retries/resume
- Safe mode / kill switch works (disable writes quickly)
- **Assurance case exists and references** enabled capabilities + policy bundle + eval suite versions + `bundle_id`
- **Risk register updated** with current evidence links (tests/eval runs/telemetry) for the release


---

### Level 4 — Multi-tenant enterprise (governed, scalable)
**Capabilities**
- Multiple tenants/users, strict isolation, audit/reporting, retention controls

**Minimum kernel (incremental)**
- Level 3 plus multi-tenant invariants (tenant_id propagation, partitioning)
- **K16 change management** required
- Stronger K9 (tamper evidence + external log sink) recommended

**Exit criteria**
- Cross-tenant access attempts are blocked and alert
- `tenant_id` is immutable per run and present as a first-class dimension in logs/metrics/traces
- Tenant-scoped storage partitions are enforced for runs/memory/audit/persistence
- Tenant-scoped policy bundles + tool allowlists are enforced (no “global policy” footguns)
- **Per‑tenant ingress rate limits + per‑tool executor rate limits** are enforced and observable
- Noisy-neighbor protection exists: per-tenant quotas on concurrent runs and resource usage; circuit breakers behave as expected
- Tenant offboarding exists: soft-delete (no new runs) → retention window → hard-delete; deletion events are recorded in the audit ledger
- Artifact bundles are versioned and reproducible
- Rollback is a normal operation (tested in CI)


---

### Level 5 — High-assurance / regulated / high-risk autonomy
**Capabilities**
- High-stakes actions, machine-speed effects, regulated data

**Minimum kernel (incremental)**
- Level 4 plus:
  - hardened audit (WORM or external append-only log),
  - continuous red-teaming + adversarial eval expansion,
  - formal assurance case maintained (hazards → controls → tests/telemetry).

**Exit criteria**
- You can prove restraint with evidence (tests, telemetry, audit trails)
- Incidents lead to test additions and policy hardening within defined SLA

---

### Governance minimums by level (don’t skip these)

These are the minimum non-code controls needed so the kernel stays operable under real failures.

- **Level 1:** owner named; minimal threat model written; CI runs the minimal K12 harness; data classification/redaction rules documented (even if coarse).
- **Level 2:** on-call ownership; incident intake + triage; replay available for reproduction (K11); **risk register exists and is updated each release**; **gated eval suites have suite cards and immutable versions (K12a)**; change control baseline (K16‑min) in place.
- **Level 3:** approval UX and kill switch are documented and drilled; separation of duties where feasible (policy authors vs tool implementers); **assurance case maintained for any high-risk capability**; risk acceptance owner named for residual risks.
- **Level 4:** tenant isolation is tested; tenant-scoped policies/capabilities; retention/access controls for audit data are defined; tenant offboarding/deletion procedure exists; rollback is a routine operation.
- **Level 5:** assurance case is continuously maintained (hazards → controls → evidence); continuous adversarial testing + red-teaming cadence; stronger audit integrity and compliance posture.


---

## 4. Build order (dependency order that keeps you honest)
See `layers-design/reliability/implementation_playbook.md` §4 for the dependency DAG and phased build sequence.

---

## 5. Repo architecture (keep the TCB small, prevent leakage)
See `layers-design/reliability/implementation_playbook.md` §2 for the monorepo layout and boundary enforcement mechanisms.

---

## 6. Concrete Python patterns (production-friendly)
See `layers-design/reliability/implementation_playbook.md` §5–§7 for the kernel API definitions and code patterns.

---

## 7. Teaching track (undergrad-friendly, enterprise-free)

### 7.1 Teaching goal
Teach the *transferable* ideas:
- reference monitors
- least privilege
- explicit state machines
- typed interfaces and validation
- idempotency + outbox
- adversarial thinking (prompt injection)
- verification loops and eval gates
- observability and replay

Avoid enterprise plumbing:
- OAuth, KMS, distributed queues, Kubernetes, SOC2, etc. (introduce as optional “extensions”)

### 7.2 “Kernel Lite” (course version) scope
Implement a minimal kernel that runs locally:
- Tools are local Python functions (no network)
- Audit ledger is JSONL on disk
- Approval UX is a CLI prompt
- Persistence is SQLite (single file)

But the architecture is identical to production:
- strategies propose
- kernel enforces
- all effects go through the gate

**Terminology note:** "K5-lite" appears twice in this document with different meanings:
- **§2 (production):** "K5-lite for sensitive reads" = production pattern for read-only agents accessing ACL'd data (allowlist + scope constraints + decision logging).
- **§7 (teaching):** "K5 Policy: Lite" = simplified policy for the teaching kernel (allowlist + CLI approval, no two-phase preview).

Both share the core principle: *effects are gated by policy*. The teaching version is simpler; the production version handles more edge cases.

**Included subsystems (teaching scope):**

| Subsystem | Lite Scope | Implementation |
|-----------|------------|----------------|
| **K1** ABI | Full | Pydantic models, `stable_hash()`, error taxonomy |
| **K2** Orchestrator | Full | FSM with transitions, stop conditions, cancel/abort |
| **K3** Model Boundary | Basic | One provider wrapper, schema validation, bounded repair |
| **K4** Tool Executor | Full | Schema validation, timeouts, idempotency keys, typed errors |
| **K5** Policy | Lite | Simple allowlist + CLI approval (no full two-phase preview) |
| **K6** Budgets | Full | Step + time + token caps |
| **K7** Verification | Lite | Schema/type checks; verifier registry pattern |
| **K9** Audit | Lite | JSONL append-only (no hash chain) |
| **K10** Persistence | Lite | SQLite outbox for idempotency; basic checkpoints |
| **K18** Sanitizer | Full | `SanitizedContent` envelope, provenance, suspicion flags |

**Excluded (production-only complexity):**

| Subsystem | Why Excluded |
|-----------|--------------|
| **K5-full** | Two-phase preview/commit with binding hashes requires approval UX |
| **K8** Sandbox | nsjail/gVisor requires system-level setup |
| **K9-full** | Tamper-evident hash chains, external sinks |
| **K11** Replay | Recording infrastructure, deterministic time |
| **K12** Eval Gates | CI integration, suite governance |
| **K14** Secrets | KMS, credential broker, short-lived tokens |
| **K16** Bundles | Artifact registry, canary, migrations |
| **Multi-tenant** | Isolation, per-tenant policies, offboarding |

**Critical invariants still enforced in Lite:**
1. Strategies cannot call tools directly (capability discipline)
2. Untrusted content is enveloped (K18)
3. Budgets are hard caps (K6)
4. Effects are gated by policy (K5-lite)
5. Audit trail exists (K9)

### 7.3 6-module curriculum (with labs)

#### Module 1 — Kernel mindset: trust boundaries and TCB
- Concepts: untrusted inputs, complete mediation, fail closed
- Lab: break a naive agent with prompt injection; document threat model

#### Module 2 — ABI + deterministic orchestration
- Concepts: typed state, explicit FSM, stop conditions
- Lab: implement K1 + K2; add budget caps; write transition tests

#### Module 3 — Tools as contracts (tool executor)
- Concepts: schemas, typed errors, retries/timeouts, canonicalization
- Lab: implement a tool executor for read-only tools; add logging

#### Module 4 — Policy + reference monitor + two-phase commit
- Concepts: allowlists, risk tiers, approval binding hashes, TOCTOU
- Lab: add a “write” tool (e.g., modify a TODO list file) and enforce propose/preview/commit

#### Module 5 — Idempotency + outbox + replay safety
- Concepts: dedupe keys, durable intent logs, crash recovery
- Lab: simulate crash mid-tool-call; show no duplicate side effects after resume

#### Module 6 — Evaluation harness + adversarial suites
- Concepts: regression tests, injection suites, constraint violation metrics
- Lab: build a small eval pack; require CI pass to “release”

### 7.4 Grading rubric (simple and honest)
- **Correctness:** passes deterministic invariants tests
- **Safety:** no policy bypass; no write without approval
- **Reliability:** bounded retries, graceful failure, resumability
- **Evidence:** traces + replay demonstrate “what happened”

---

## 8. Practical adoption tips (what experienced teams do)
### 8.5 Classify and redact before you log

**Recommended minimum classification taxonomy (L0–L3)**
| Level | Label | Examples | Logging rule |
|---:|---|---|---|
| L0 | Public | published docs, public outputs | ok to log |
| L1 | Internal | trace IDs, run metadata, aggregated metrics | ok to log |
| L2 | Confidential | user inputs, tool arguments, model outputs | redacted by default |
| L3 | Restricted | secrets, credentials, auth tokens, PII (as defined) | **never logged** |

**Invariants**
- All inbound blobs are classified at ingestion time (user text, retrieved text, tool outputs, uploads).
- Classification is immutable once assigned (no silent downgrades).
- L3 must not appear in logs, traces, or error messages; block or over-redact if uncertain.
- Classify every inbound blob (user text, retrieved text, tool output) at **ingestion time**.
- Redact based on that classification **before** writing audit events, persistence records, or error messages.
- Treat “log everything” as break-glass, time-bounded, and separately audited.

### 8.6 Rate limiting is not the same as budgets
- Budgets stop a *run* from spiraling. Rate limits protect your *system* and your *wallet*.
- If you’re exposed to users or multi-tenant: enforce **per-tenant ingress** limits and **per-tool executor** limits.

### 8.7 Make abort semantics boring and testable
- Cancellation must be a kernel control.
- If you cannot cancel an in-flight tool call, quarantine its eventual result and discard it after abort.
- Write a test that proves: “cancel → no further state transitions → no side effects after cancellation.”

### 8.8 Treat evals as a day-one artifact, not a day-100 project
- Start with a tiny harness + 10 regression cases + 10 injection cases.
- Grow it from incidents and near-misses.


### 8.1 Keep the kernel dependency-light
Prefer:
- `pydantic` (schemas), `jsonschema` (optional), `structlog` (logs), `opentelemetry` (traces)

Avoid dragging your whole product stack into the TCB.

### 8.2 “No direct tool handles” is the golden rule
If a strategy can call a tool directly, you’ve dissolved your enforcement boundary.

### 8.3 Make policy boring
- Default deny
- Explicit allowlists
- Deterministic constraints (domains/paths/diff size)
- Approvals bound to hashes
- Versioned policy bundles with tests

### 8.4 Build evals from incidents
Every production failure should become:
- a regression test
- an adversarial case
- a policy or verifier improvement

That’s how you evolve from Level 3 → Level 5 without superstition.

---

## 9. Concrete implementation playbook (make the invariants real)
This playbook lives in `layers-design/reliability/implementation_playbook.md`. Use that file as the canonical step-by-step reference for build order, API definitions, and code patterns.
