# Design Decisions Questionnaire

This document is a **pre-implementation decision checklist** for the Kernel/Strategy agent system described in the Implementation Playbook.  
The goal is to eliminate ambiguity, make tradeoffs explicit, and prevent “we’ll decide later” decisions from quietly becoming production incidents.

## How to use this document

1. **Answer every question that applies.** If a question is “TBD,” assign an owner and a date.
2. Record the final choice as an **Architecture Decision Record (ADR)** (template below).
3. Treat “defaults” as **provisional**; they exist to keep you moving, not to replace product/security requirements.
4. Revisit decisions when:
   - you add a new tool/provider,
   - you onboard a new tenant/customer,
   - you change the deployment topology,
   - you change your threat model/compliance posture.

---

## ADR template

Copy/paste this template per decision (or use your ADR system):

- **ADR-ID:** ADR-###
- **Title:** (short descriptive title)
- **Status:** Proposed | Accepted | Superseded | Deprecated
- **Date:** YYYY-MM-DD
- **Owners:** (names/roles)
- **Decision:** (what we chose)
- **Options considered:** (brief list)
- **Rationale:** (why this choice)
- **Consequences:** (what gets easier/harder)
- **Security/Privacy impact:** (data exposure, blast radius)
- **Operational impact:** (SLOs, costs, failure modes)
- **Testing/Proof impact:** (new tests required)
- **Migration plan (if any):** (how to move from current state)

---

# 1. Product scope and non-goals

1. What is the **primary use case** (assistant, workflow automation, data retrieval, code execution, customer support, internal ops)?
2. What are the **explicit non-goals** (e.g., no autonomous network scanning, no financial trading, no high-risk medical)?
3. What is the **definition of “run success”** vs “run failure”?
4. What is the expected **interaction style**:
   - synchronous (user waits),
   - asynchronous (run continues in background),
   - mixed (approve gates + async effects)?
5. What are the **hard constraints**:
   - latency target (p50/p95),
   - cost per run,
   - maximum tokens per run,
   - maximum tool calls per run,
   - maximum run duration?
6. What are the **user roles** (viewer/operator/admin) and what can each do?

---

# 2. Deployment topology and environments

1. Where will the system run (cloud provider, region(s), on-prem)?
2. Is the system **single-tenant or multi-tenant**? If multi-tenant, what is the isolation boundary?
3. Do you require **data residency** (EU-only, US-only, etc.)?
4. What environments exist (dev/stage/prod) and how are they isolated?
5. What is the deployment unit:
   - monolith,
   - kernel service + strategy service,
   - kernel + multiple executors,
   - fully distributed (policy/approval separate services)?
6. Is Strategy executed:
   - in-process (MVP),
   - separate process,
   - container sandbox (recommended),
   - remote service?
7. What are the **resource limits** for Strategy execution (CPU/memory/timeouts)?
8. Is outbound network access from Strategy allowed? If yes, for what domains? (Default: **deny**.)

---

# 3. Identity, tenancy, and authorization

1. What is the **principal model** (user, service account, delegated principal, organization)?
2. How is principal identity **authenticated** (OIDC, API keys, mTLS)?
3. How are **tenant_id**, **principal_id**, and **run_id** generated and validated?
4. What is the authorization model for:
   - creating runs,
   - viewing run state,
   - viewing audit logs,
   - approving tool commits,
   - exporting audit bundles?
5. What is the access control policy for **audit read path** (tenant scoping, RBAC)?
6. Do you need “break-glass” admin access? How is it audited?

---

# 4. Threat model and compliance posture

1. What is the threat model? Check all that apply:
   - malicious prompt injection,
   - malicious tool output,
   - compromised Strategy code,
   - compromised worker,
   - insider with DB access,
   - external attacker with API access.
2. What data classifications exist (public/internal/confidential/regulated)?
3. What compliance regimes apply (SOC2, ISO27001, HIPAA, PCI, GDPR)?
4. Are there requirements for:
   - encryption at rest,
   - encryption in transit,
   - key management via KMS/HSM,
   - WORM retention / legal hold?
5. Do you require **global tamper evidence** (detect run deletion)? If yes, what is the external anchor (WORM bucket, separate security account, transparency log)?
6. What is the incident response expectation:
   - detection time,
   - notification process,
   - forensic export requirements?

---

# 5. Kernel/Strategy boundary and ABI

1. What is the Strategy ABI versioning plan (semantic versioning, compatibility rules)?
2. What is the maximum size for:
   - observations,
   - intents,
   - context plans,
   - tool previews,
   - tool results?
3. What is the RPC mechanism:
   - in-proc interface,
   - HTTP/JSON,
   - gRPC/Protobuf,
   - message bus?
4. What is the timeout policy for Strategy calls (per step, per run)?
5. What is the cancellation model (kernel cancels, strategy must cooperate)?
6. What is the determinism contract:
   - kernel provides time + rng_seed,
   - strategy must not call clock/random directly?
7. What data can cross the boundary (strictly sanitized observations only)?
8. What *must never* cross the boundary:
   - tool handles,
   - secrets,
   - raw untrusted content without wrappers?
9. What is the strategy sandboxing plan:
   - filesystem access,
   - network egress,
   - environment variables,
   - syscalls (seccomp),
   - container runtime?

---

# 6. Kernel core, effects pipeline, and determinism

1. Confirm the control model:
   - KernelCore is pure-ish reducer: `step(state, observation) -> (state, effects[])`.
   - EffectRunner is the only I/O interpreter.
2. What is the effect type taxonomy? List all effect kinds you will implement now vs later:
   - model_call,
   - tool_preview,
   - policy_eval,
   - approval_wait,
   - tool_execute,
   - persistence_write,
   - audit_append,
   - secrets_fetch,
   - outbox_enqueue,
   - saga_compensate, etc.
3. What is the canonical encoding / hashing scheme for:
   - tool args canonicalization,
   - context plan hash,
   - approval binding hash,
   - audit event hash?
4. What is the replay strategy:
   - record/replay all external I/O,
   - block external I/O in replay mode,
   - deterministic state hash comparisons?
5. Concurrency rules:
   - Is a run single-threaded by design?
   - Can effects execute concurrently? If yes, what ordering guarantees exist?
6. Failure handling:
   - What errors are fatal to the run?
   - What errors are retryable/deferred via outbox?

---

# 7. Model routing and provider strategy

1. Do you require multiple model providers at launch? If yes, which providers and in which regions?
2. Does Strategy choose:
   - the provider/model directly (not recommended),
   - a model class + constraints (recommended)?
3. What is the set of model classes (e.g., `cheap`, `reasoning`, `vision`, `high_context`, `offline_allowed=false`)?
4. What constraints must routing enforce:
   - data residency,
   - PII restrictions,
   - budget,
   - latency,
   - maximum context size?
5. How is provider selection audited (provider_id, model_id, policy bundle version)?
6. What is the fallback behavior when a provider is down:
   - fail closed,
   - fallback to another provider,
   - degrade to smaller model,
   - request user approval?
7. What is the provider-specific prompt formatting/roles policy?
8. What telemetry is required per model call (tokens, cost, latency, error codes)?

---

# 8. Tooling model and tool safety

1. What tools exist at launch? Categorize them:
   - read-only,
   - write/side-effecting,
   - high-risk (payments, deletion, user impersonation).
2. What is the tool contract shape:
   - typed args schema versioning,
   - deterministic serialization,
   - result schema?
3. Which tools require:
   - preview + explicit approval,
   - policy-only gating,
   - always-on (no approval) allowed?
4. What is the tool execution environment:
   - in-process,
   - separate executor service,
   - containerized job?
5. What is the idempotency strategy per tool:
   - caller-provided idempotency key,
   - tool-specific natural keys,
   - outbox idempotency enforcement?
6. What are tool timeouts and max payload sizes?
7. What is the tool error taxonomy (retryable vs non-retryable)?
8. Are tool outputs treated as untrusted content by default? (Default: **yes**.)

---

# 9. Policy engine, approvals, and capability tokens

1. Is policy evaluation:
   - fully local (specs/rules),
   - remote policy service,
   - hybrid?
2. Do you need **policy bundles** per tenant/run_type? If yes:
   - how are bundles discovered (registry),
   - how is version pinned per run?
3. What is the policy decision output contract:
   - allow,
   - deny (with reason codes),
   - needs_approval (with binding hash)?
4. Approval workflow:
   - who can approve,
   - where approvals live (UI, Slack, ticketing),
   - timeouts/expiry,
   - cancellation behavior?
5. Capability tokens:
   - HMAC or asymmetric signing?
   - where are keys stored (KMS/HSM/env)?
   - rotation cadence,
   - token TTL,
   - clock-skew policy?
6. What fields are bound into the token:
   - tool name,
   - canonical args hash,
   - phase (preview/commit),
   - principal_id,
   - tenant_id,
   - expiry,
   - approval binding hash?
7. What is the executor behavior if:
   - token missing,
   - token invalid,
   - token expired,
   - approval binding mismatch? (Default: **fail closed** + audit.)

---

# 10. Context safety: typed ContextPlan and prompt injection discipline

1. Do you require strict separation of:
   - instructions (system/developer),
   - untrusted data (data channel),
   - tool outputs (untrusted)?
2. What is the ContextPlan schema and versioning policy?
3. What is the maximum size of untrusted content injected into a prompt? What truncation rules apply?
4. What is the redaction policy for:
   - logs,
   - audit events,
   - model inputs,
   - model outputs?
5. Do you require structured citations/grounding? If yes, what is the format?
6. What is the policy for storing:
   - full prompts,
   - model outputs,
   - tool outputs? (Retention + privacy.)

---

# 11. Persistence, outbox, DLQ, and sagas

1. What persistence backend is used at launch (SQLite/Postgres/etc.)?
2. Do you require event sourcing immediately, or is it optional later?
3. What is the atomic write boundary (Unit of Work) for a kernel step:
   - audit append(s),
   - state snapshot,
   - outbox enqueue?
4. Outbox schema decisions:
   - statuses used,
   - retry_count/max_retries/next_attempt_at,
   - last_error_code/message storage format,
   - idempotency keys.
5. DLQ decisions:
   - where dead-lettered records live,
   - alerting thresholds,
   - operator remediation flow.
6. Retry/backoff policy:
   - exponential backoff parameters,
   - jitter,
   - max age for retries,
   - poison-message acceleration rules.
7. Saga usage:
   - which multi-step operations are sagas,
   - what compensating actions exist,
   - when to mark saga as failed vs compensating,
   - how saga state is stored/replayed.
8. Resume behavior:
   - what happens after crash mid-step,
   - how to guarantee no duplicated side effects.

---

# 12. Audit ledger, read path, and tamper evidence

1. What is the durable audit store (DB table, log, append-only file)?
2. What audit events are mandatory for compliance:
   - policy decisions,
   - approvals,
   - tool previews,
   - tool executions,
   - capability token issuance,
   - secrets access?
3. Audit read APIs:
   - `query(run_id, after_seq, limit)` supported?
   - `get_head(run_id)` supported?
   - time-based queries required?
4. Chain verification:
   - do you verify per-run chain routinely (background job) or on demand?
   - what triggers an alert (broken chain, missing seq)?
5. Multi-sink fan-out:
   - do you need remote SIEM export?
   - which sinks are primary vs secondary?
   - backpressure/drop policy for secondary sinks?
6. Global tamper evidence:
   - do you need it?
   - what anchor mechanism is used?
   - signing keys and rotation?
7. Audit export bundle:
   - required format (JSONL + head hash + signature),
   - who can export,
   - retention of exports.

---

# 13. Operational resilience (timeouts, retries, circuit breakers, bulkheads)

1. What are the default timeouts for:
   - model calls,
   - tool calls,
   - policy eval,
   - approval wait,
   - persistence operations?
2. Circuit breaker configuration:
   - failure thresholds,
   - window sizes,
   - half-open probe rate,
   - per-dependency keys.
3. Bulkhead configuration:
   - per-tenant concurrency,
   - per-tool concurrency,
   - separate pools for model/tool/persistence.
4. Load shedding:
   - behavior when bulkhead saturated (fail fast vs queue),
   - user-facing error semantics.
5. Retry policy decisions:
   - which effects are retryable,
   - max retries,
   - backoff parameters.
6. Which dependencies should fail closed vs fail open?
7. How are resilience events audited/observed (breaker_open, bulkhead_reject, retry_exhausted)?

---

# 14. Observability and operations

1. What metrics are required (minimum set):
   - run success/failure,
   - step latency,
   - tool latency,
   - model tokens/cost,
   - outbox backlog age,
   - DLQ count,
   - breaker state,
   - bulkhead saturation.
2. What tracing is required (OpenTelemetry, trace IDs across services)?
3. What logs are required and what redaction is mandatory?
4. What are the SLOs (availability, latency, correctness/replay)?
5. On-call expectations and alert routing?
6. Run debugging workflow:
   - how to replay a run,
   - how to export evidence,
   - how to inspect ContextPlan without leaking secrets.

---

# 15. Extensibility and versioning

1. Which extension points are supported at launch:
   - tool packs,
   - verifier packs,
   - policy bundles,
   - effect middleware?
2. How are extensions discovered:
   - static config,
   - dynamic registry,
   - feature flags?
3. What is the compatibility policy:
   - how long old versions must remain supported,
   - how migrations occur?
4. How are extension changes tested:
   - contract tests,
   - golden traces,
   - replay compatibility tests?
5. What is the rollout strategy for new tools/policies (canary, staged rollout)?

---

# 16. Data management: retention, deletion, and privacy

1. Retention policies for:
   - audit events,
   - run state snapshots,
   - model inputs/outputs,
   - tool outputs,
   - outbox records,
   - DLQ records.
2. Data deletion requirements:
   - per-user delete,
   - per-tenant delete,
   - selective redaction vs full deletion.
3. How is PII identified and handled:
   - redaction at ingestion,
   - redaction at render time,
   - encrypted fields?
4. Are you allowed to store raw prompts/responses? If yes, for how long and who can view them?
5. What is the policy for storing external content fetched by tools?

---

# 17. Testing and proof suite gates

1. Which “proof tests” are required as CI gates:
   - deterministic replay test,
   - no I/O outside EffectRunner test,
   - capability token required for side effects test,
   - approval binding mismatch test,
   - crash/resume idempotency test,
   - DLQ bounded retries test,
   - audit chain verify test,
   - breaker/bulkhead coverage tests.
2. What is the replay dataset strategy:
   - synthetic traces,
   - production sampling (with redaction),
   - golden runs per tool/provider.
3. What fuzz/property tests exist:
   - args canonicalization,
   - event hashing,
   - policy spec evaluation?
4. What performance tests exist (load tests, chaos tests)?

---

# 18. Performance and scaling

1. Expected throughput (runs/sec, tool calls/sec, model calls/sec)?
2. Scaling approach:
   - scale Strategy horizontally,
   - scale executors,
   - shard by tenant/run_id.
3. Storage scaling:
   - event stream growth rate,
   - snapshot frequency,
   - indexing strategy.
4. Cost controls:
   - budgets per tenant,
   - rate limiting,
   - model class throttles.

---

# 19. Release, migrations, and change management

1. Schema migration strategy (online migrations, backward compatibility)?
2. Key rotation playbook (capability token keys, signing keys)?
3. Policy bundle rollout strategy and rollback?
4. Tool version rollout strategy and rollback?
5. Incident rollback:
   - can you disable a tool globally?
   - can you force a run type into “approval required” mode?
6. Change audit:
   - how are policy/tool changes themselves audited?

---

# 20. Sign-off checklist

Before implementation begins, confirm:
- [ ] Threat model defined and agreed.
- [ ] Tenant/principal model defined.
- [ ] Strategy boundary + ABI constraints defined.
- [ ] Effect taxonomy + middleware pipeline plan agreed.
- [ ] Model routing policy agreed.
- [ ] Tool approval + capability token contract agreed.
- [ ] Persistence/outbox/DLQ design agreed.
- [ ] Audit read/verify + retention agreed.
- [ ] Secrets broker approach agreed.
- [ ] Proof suite CI gates defined.
- [ ] SLOs + alerting defined.

---

## Appendix: Minimal recommended defaults (if you must pick something today)

- Strategy provider selection: **Strategy requests model_class; kernel routes by policy.**
- External I/O: **only via EffectRunner**; enforce with lint + runtime tripwire test.
- Capability tokens: **HMAC** for internal MVP; move to asymmetric when executors are truly external.
- Audit: **durable DB ledger as primary**, async fan-out to SIEM.
- DLQ: **enabled**, bounded retries with exponential backoff + jitter.
- Secrets: **brokered ephemeral credentials**, Strategy never sees secrets.
