# Kernel Checklist for Production Agentic Systems (Kernel Blueprint)

This document defines the **kernel** required for an agentic system that a company can confidently ship, debug, and audit — *even when the model is wrong*.

It’s intentionally **method‑agnostic**: you can swap prompting/planning/RAG/model providers without rewriting the kernel.

**Definition:** The kernel is the system’s **Trusted Computing Base (TCB)**: the smallest set of code + policies that must remain correct for all side effects, safety properties, and audit claims to hold.


**Requirements language:** The keywords **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative. Anything labeled "example" or "reference" is non-normative.
---

## 0) Threat Model + Scope (read this first)

The kernel is designed to survive these realities:

- **The model is fallible**: it will hallucinate, produce malformed outputs, and confidently choose the wrong actions.
- **Inputs are adversarial**: users, retrieved documents, web pages, tickets, and tool outputs may contain prompt injection or malicious payloads.
- **Tools are unreliable**: timeouts, partial failures, retries, and inconsistent results are normal.
- **The environment is hostile** (eventually): secrets exist, credentials exist, and anything reachable can be targeted for exfiltration.

**Protected assets (typical):**
- external state (money, emails, prod config, tickets, code merges),
- credentials/secrets,
- user data / PII / customer content,
- tenant isolation boundaries,
- system integrity (preventing arbitrary code execution or SSRF via tools),
- audit integrity (tamper-evident history).

**Non-goals (not kernel):**
- “best prompting style”
- “best RAG method”
- “best planner”
- “best model”

Those are strategy modules. The kernel is the enforcement substrate they run inside.

**Trust boundary rules (kernel‑enforced):**
- Treat **user input**, **retrieved text**, **tool outputs**, and **model outputs** as **untrusted data**.
- Only the **Policy Engine** can authorize side effects; only the **Verification Layer** can assert correctness/safety for gated outputs.
- Untrusted data is inserted into prompts via a **data channel** (quoted/serialized), never into instruction channels (system/developer prompts).

**Scope note:** Sections **K1–K18** define **kernel invariants** (the TCB requirements). Later sections (budgets/SLOs, wire formats, crypto profile, sandbox tech, incident response) are **reference operational profiles** that MAY be delegated to platform controls, but MUST still satisfy the kernel invariants.

---

## 1) Kernel = the stuff that must stay true even if the model goes feral

A kernel is the smallest set of components that collectively enforce:

- **boundedness** (it can’t run forever or bankrupt you),
- **complete mediation** (no privileged effect without a gate),
- **deterministic validation** (schemas/contracts are enforced in code),
- **independent verification** (high-stakes outputs/actions get checked),
- **auditability & replay** (you can reconstruct what happened and why),
- **least privilege** (the agent can only do what it is explicitly granted),
- **fail-closed defaults** (ambiguous or risky ⇒ block/escalate),
- **testability** (every stated invariant is enforced by code and covered by an automated test or runtime monitor).

**Kernel rule:** If you can't *mechanically* enforce or test it, it's guidance — not a kernel invariant.

---

## 2) Non‑negotiable kernel subsystems (the checklist)

Legend:
- **Always** = you need it even for “toy” agents if you want them reliable.
- **If side effects** = required once tools can change external state (emails, PRs, prod config, money).
- **If multi-user** = required once you have tenants/users and access control matters.

### K1. Typed System Model (“ABI”)
**Always.** A stable schema for:
- agent state,
- tool calls/results,
- error taxonomy,
- outcomes (domain-level success/failure categories),
- trace events,
- configs & versions (prompts/tools/policies/verifiers).

**Kernel invariants**
- serialization is deterministic (stable hashes possible),
- schema versioning exists (forward/backward strategy documented),
- partial/invalid states are detectable and rejected at boundaries,
- all events and actions carry `trace_id` and `run_id`.

---

### K2. Deterministic Orchestrator / Control Loop
**Always.** A runtime that:
- executes an explicit state machine (FSM/graph/workflow),
- enforces allowed transitions,
- has explicit stop conditions,
- supports safe abort paths and resumability.

**Kernel invariants**
- no hidden recursion; no “while model says keep going” without hard bounds,
- every step is traceable to a state node + reason,
- state transitions are validated (invariants checked at each step),
- dependency injection is supported (swap real tools for mocks/sim/replay).
- abort/cancel is a first-class control: in-flight tool/model calls are cancelled when possible; otherwise their results are quarantined and discarded if the run is aborted.

---

### K3. Model Boundary (LLM as a Tool)
**Always.** A single boundary that:
- renders prompts deterministically from typed inputs,
- normalizes provider responses into a stable schema,
- validates structured outputs (and captures raw output for debugging),
- accounts for token/cost budgets,
- supports provider feature detection and graceful degradation.

**Kernel invariants**
- model output is never “trusted” without validation,
- malformed/partial outputs are handled deterministically (repair/retry/escalate),
- prompts are versioned artifacts (hashable, deployable, rollbackable),
- the rest of the system doesn’t care which provider/model you use,
- model calls enforce hard caps: `max_tokens`, `max_output_bytes`, and stop conditions; oversize outputs are treated as invalid and handled deterministically,
- every model response is tagged with: provider, `model_id`/version (if available), decoding params, and a prompt hash (for replay/audit),
- structured-output repair is bounded (e.g., ≤2 attempts) and uses the same schema validator (no "best effort" acceptance).

---

### K4. Capability / Tool Interface + Execution Wrapper
**Always.** A tool protocol + executor that provides:
- input validation + parameter sanitization,
- output normalization (typed results + typed errors),
- timeouts, retries, backoff, rate limits,
- idempotency hooks and deduplication keys,
- structured error taxonomy (retryable vs permanent),
- logging/tracing around every call.

**Kernel invariants**
- tools cannot bypass the executor,
- tool calls include required metadata: `principal`, `purpose`, `risk_tier`, `idempotency_key`, `trace_id`,
- `principal`, `risk_tier`, and `purpose` are kernel-owned metadata (derived from session identity + tool manifest + calling node); model-supplied values are ignored,
- a versioned tool manifest exists (tool name/version, side-effect flag, risk tier, required capabilities/scopes, preview support, idempotency support, allowed network/FS); its hash is recorded per run,
- untrusted content cannot become tool arguments without passing validation/sanitization,
- “read vs write” tools are explicitly labeled (side effects are never implicit),
- idempotency keys are generated by the kernel (from canonical tool name + canonical args + run_id), not supplied by the model,
- tool arguments are canonicalized (stable serialization) before hashing, caching, dedupe, or auditing,
- tools that accept code/queries/URLs must use sink-safe interfaces (e.g., parameterized SQL, argv-style execution, URL allowlists); never "stringly-typed" concatenation.

---

### K5. Reference Monitor + Policy Engine (Authorization + Risk)
**If side effects (strongly recommended even earlier).** A centralized gate that:
- allowlists tools by identity + scope (capability tokens, not prompt text),
- enforces parameter constraints (domains, paths, SQL patterns, diff limits, etc.),
- applies risk-tier rules (low/medium/high; high-risk requires approval),
- enforces **two-phase execution**: Propose → Preview → Approve → Commit,
- binds approvals to the exact proposed effect (tool + args + preview/diff hash), not to free-form text,
- every side-effecting tool supports either (a) a deterministic preview/diff, or (b) is always human-approved (no blind commit),
- fails closed.

**Kernel invariants**
- no privileged effect is possible without passing policy,
- policies are code/config artifacts (versioned, tested, auditable),
- retrieved/tool content is treated as untrusted data, never as authorization,
- policy evaluation is logged as a first-class event,
- approvals are bound to a deterministic hash of (tool, args, preview/diff) and expire; commit must match exactly or require re-approval,
- policy is evaluated at both propose-time and commit-time (TOCTOU-safe).

---

### K6. Budgets + Loop/Thrash Controls
**Always.** Hard limits on:
- steps, wall-clock time,
- model tokens/cost,
- tool calls and tool latency,
- sandbox/runtime resources,
- repeated failures (tool thrash) and repeated near-identical attempts.

**Kernel invariants**
- budget exceeded ⇒ deterministic stop/degrade/escalate,
- repeated identical failures trigger plan change or abort (no infinite retries),
- circuit breakers exist (e.g., disable a flaky tool or switch to safe mode).

**Rate limiting invariants (if multi-user or exposed API)**
- per-tenant request rate limits enforced at ingress (requests/sec, requests/min),
- per-tool rate limits enforced at executor (calls/min per tool),
- rate limit violations return a standardized "rate_limited" error with a retry-after duration (HTTP 429 + `Retry-After` when applicable),
- sustained rate limit violations (>N in window) trigger circuit breaker,
- rate limit state is shared across distributed executors (e.g., via Redis or similar),
- rate limit configs are per-tenant tunable; defaults defined in §3.

---

### K7. Verification Layer (Independent Checking)
**Always (strong).** Independent checks outside the model:
- schema/type checks,
- preconditions/postconditions,
- output safety checks,
- domain verifiers (tests, solvers, diff checks, compilation),
- flake detection / repeatability checks where applicable.

**Kernel invariants**
- verification runs outside the model and can veto,
- “generate → verify → repair” is first-class,
- verifiers are versioned artifacts and included in audit trails,
- verification failure is a typed outcome (not “just try again”).
- for high-risk actions, the final gate MUST include a deterministic verifier or human approval; model-based "verifiers" MAY be used as defense-in-depth but not as the sole guarantee.

---

### K8. Isolation / Sandboxing
**Always once you execute code or run untrusted artifacts.** Isolation for:
- code execution,
- risky tool actions,
- network/FS boundaries,
- resource caps (CPU/mem/time), deterministic time where needed.

**Kernel invariants**
- untrusted code runs in a constrained context,
- secrets are not available in the sandbox by default,
- network is off by default (explicit allowlist if required),
- sandbox outputs are treated as untrusted unless verified.

---

### K9. Observability + Audit Ledger
**Always.** Structured:
- traces (state transitions, tool calls, model calls, policy decisions),
- logs (with redaction),
- metrics (success, violations, cost, latency, retries),
- an append-only action ledger.

**Kernel invariants**
- you can reconstruct “what happened” without guessing,
- sensitive data is redacted by default,
- ledger is tamper-evident (hash-chained events or equivalent),
- the audit ledger is append-only and not writable via agent-accessible tools (the agent cannot alter its own history),
- retention and access controls are defined (who can read what, and for how long),
- redaction/classification happens at ingestion time (before anything is written to disk or shipped to log aggregation),
- "full prompt/tool payload logging" is a break-glass mode with explicit enablement, scoped duration, and its own audit trail.

---

### K10. Persistence + Resume Semantics
**Always for long-running or crashable agents.** Persistence for:
- run manifests,
- state snapshots/checkpoints,
- tool call logs,
- resume-from-latest-state.

**Kernel invariants**
- replay and time-travel debugging are possible,
- resuming does not duplicate side effects (idempotency keys + dedupe),
- semantics are explicit: at-least-once vs exactly-once for each tool/action,
- side-effecting actions use a durable outbox: intent record written before execution, marked committed only after success; resume/replay consults this ledger to prevent duplicates.

---

### K11. Reproducibility Hooks (Replay + Fault Injection)
**Always for serious debugging and hardening.** Facilities for:
- record/replay tool I/O,
- deterministic seeds and deterministic time sources (where relevant),
- fault injection (simulate outages, timeouts, partial responses),
- crash injection.

**Kernel invariants**
- experiments are replayable end-to-end,
- model calls are replayable: requests/responses (redacted) can be recorded, and replay mode substitutes recorded model outputs instead of calling a live provider,
- robustness can be benchmarked deterministically,
- “replay mode” cannot accidentally trigger real side effects.

---

### K12. Evaluation Harness + Release Gates
**Always.** A harness that runs:
- golden regression suites,
- adversarial/injection suites,
- scenario simulations (multi-step, multi-turn),
- CI gates on constraint violations and SLO thresholds.

**Kernel invariants**
- “no deploy without passing” is enforceable,
- evals are versioned with tools/policies/schemas,
- post-deploy canary/shadow evaluation runs continuously on a fixed scenario set; sustained SLO violations trigger automatic rollback or forced safe mode (per K16/K6).

---

### K12a. Eval Corpus Governance (Data Discipline)
**Always for gated systems.** The eval harness is only reliable if eval data is curated like code.

**Kernel invariants**
- every eval suite is a versioned artifact with a stable ID and hash (immutable once released),
- suites include an “Eval Suite Card” (purpose, risk coverage, provenance, rubric version, privacy class, thresholds, changelog),
- eval datasets derived from production traces are sanitized/redacted and access-controlled; secrets are prohibited,
- gates specify minimum sample sizes, fixed thresholds, and a flake policy (retry/quarantine) to prevent metric gaming,
- every P0/P1 incident results in at least one new regression/adversarial test case added to a gated suite (per the Rapid Response Loop),
- the artifact bundle manifest references the exact eval suite versions used for release gating.

---

### K13. Context + Memory Governance
**Always once you store/retrieve context.** A deterministic context builder + memory interface with:
- provenance tags (who/what wrote this, when, from what source),
- validation on write (schemas, safety classification),
- TTL/deletion hooks + retention policies,
- poisoning/quarantine path (suspect memories require review),
- tenant isolation (if multi-user),
- strict “data ≠ instructions” handling for retrieved content.

**Kernel invariants**
- memory cannot silently accumulate unsafe junk,
- retrieval results are treated as untrusted input,
- context assembly is a first-class program (“context compiler”), not string concatenation.

---

### K14. Identity + Secrets Governance
**If side effects / integrations.** You need:
- non-human principals (agent identities),
- scoped credentials (least privilege, short-lived tokens),
- rotation/expiry and revocation,
- “secrets never in model context” enforcement,
- separate control-plane vs data-plane credentials (when applicable).

**Kernel invariants**
- credentials are not exfiltratable via model output,
- every action is attributable to a principal,
- secret access is logged and minimized.

---

### K15. Human Oversight + Safety Controls
**If side effects.** UX/IO hooks for:
- preview/approve/deny,
- pause/stop/takeover,
- safe mode / kill switch,
- autonomy levels (read-only, suggest-only, auto-execute with limits).

**Kernel invariants**
- operator can intervene and halt safely,
- high-risk actions can be blocked or gated,
- the system can degrade gracefully (safe mode) under uncertainty or incident.

---

### K16. Change Management + Rollback (Kernel Operations)
**Always (production).** Treat the agent as a deployable system of artifacts:
- versioned bundles: prompts, tools, policies, schemas, verifiers, routing rules,
- compatibility matrix (which versions work together),
- feature flags and progressive delivery (canary/gradual rollout),
- fast rollback paths on regressions (quality, cost spikes, safety alerts),
- migration strategy for state and stored memories when schemas change.

**Kernel invariants**
- every run records the exact artifact versions/hashes used,
- you can reproduce a run by reloading the same bundle,
- rollback is a normal operation, not a crisis ritual,
- bundles are integrity-protected (hash-verified; optionally signed) and loaded from a trusted artifact store.

---

### K17. Interoperability + Portability (Avoid Stack Lock-In)
**Always recommended.** Ability to export:
- tool schemas (JSON Schema / OpenAPI-inspired contracts),
- trace events in a portable format (e.g., OpenTelemetry-compatible structure),
- run bundles (manifest + artifacts + replay inputs),
- policy bundles (policy-as-code) and eval bundles.

**Kernel invariants**
- core artifacts are not trapped in one framework,
- a run can be replayed in a different runtime with minimal adaptation.

---

### K18. Input Sanitization Pipeline (Untrusted Content Handling)
**Always for agents processing external content.** A preprocessing gate that:
- quarantines untrusted content (user input, retrieved docs, web pages, tool outputs),
- extracts structured facts via constrained transforms,
- applies injection detection heuristics,
- tags content with provenance and suspicion flags.

**Kernel invariants**
- untrusted content never enters instruction channels without sanitization,
- sanitizer outputs a typed `SanitizedContent` envelope: `{quoted_data, provenance, classification, suspicion_flags, optional_extracted_facts}`; raw content is only ever used via `quoted_data` (data channel),
- suspicion flags (contains instructions, credential requests, obfuscation) are first-class metadata,
- sanitization is a logged, auditable step in the trace.

---

## 3) Kernel Configuration (Quantified Thresholds)

All kernel subsystems operate within **explicit, tunable bounds**. The following are reference defaults; operators MUST review and adjust for their risk profile.

### 3.1 Budget Defaults

| Parameter | Default | Range | Subsystem |
|-----------|---------|-------|-----------|
| `max_steps_per_run` | 50 | 10–500 | K6 |
| `max_wall_clock_sec` | 300 | 30–3600 | K6 |
| `max_cost_usd` | 1.00 | 0.10–100.00 | K6 |
| `max_tool_failures_before_abort` | 3 | 1–10 | K6 |
| `max_repair_attempts` | 2 | 1–5 | K3, K7 |
| `max_tokens_per_call` | 8192 | 1024–128000 | K3 |
| `max_output_bytes` | 32768 | 4096–1048576 | K3 |
| `max_context_tokens` | 32000 | 4096–200000 | K13 |
| `tool_timeout_ms` | 30000 | 1000–300000 | K4 |
| `approval_expiry_sec` | 300 | 60–3600 | K5 |

### 3.2 Circuit Breaker Settings

| Parameter | Default | Range | Notes |
|-----------|---------|-------|-------|
| `tool_failure_window_sec` | 60 | 30–300 | Rolling window for failure counting |
| `tool_failure_threshold` | 5 | 2–20 | Failures in window to trip breaker |
| `cooldown_sec` | 300 | 60–1800 | Time before retry after trip |
| `global_error_rate_threshold` | 0.20 | 0.05–0.50 | Error rate to trigger safe mode |

### 3.3 SLO Targets

| Metric | Target | Alert Threshold | Critical Threshold |
|--------|--------|-----------------|-------------------|
| Run success rate | ≥95% | <90% | <80% |
| P50 latency | ≤5s | >10s | >30s |
| P99 latency | ≤30s | >60s | >120s |
| Constraint violation rate | ≤1% | >2% | >5% |
| Budget exhaustion rate | ≤5% | >10% | >20% |
| Escalation rate (to human) | ≤10% | >20% | >40% |

---

## 4) Failure Modes and Recovery

Each kernel subsystem has explicit failure modes, detection mechanisms, and recovery paths.

### 4.1 K3 Model Boundary Failures

| Failure | Detection | Recovery | Escalation |
|---------|-----------|----------|------------|
| Provider timeout | HTTP timeout | Retry (max 2) with backoff | Fail run with `TransientError` |
| Malformed response | Schema validation | Structured repair attempt | Fail step, log raw response |
| Token limit exceeded | Token counter | Truncate context, retry | Degrade to summary mode |
| Rate limit (429) | HTTP status | Exponential backoff | Queue or fail run |
| Provider outage | Consecutive failures | Switch to fallback provider | Alert, enter safe mode |

### 4.2 K4 Tool Executor Failures

| Failure | Detection | Recovery | Escalation |
|---------|-----------|----------|------------|
| Tool timeout | Executor timer | Retry (if retryable) | Return `ToolError.Timeout` |
| Validation failure | Schema check | Return `ToolError.ValidationError` | No retry |
| Sandbox violation | Seccomp/runtime monitor | Immediate abort | Quarantine tool, alert |
| Idempotency conflict | Dedupe lookup | Return cached result | Log warning |
| Resource exhaustion | OOM/CPU limits | Kill, return error | Circuit breaker check |

### 4.3 K5 Policy Engine Failures

| Failure | Detection | Recovery | Escalation |
|---------|-----------|----------|------------|
| Policy evaluation error | Exception in evaluator | Fail closed (deny) | Alert, log full context |
| Approval expired | Timestamp check | Re-request approval | Inform user |
| TOCTOU mismatch | Hash mismatch at commit | Reject, re-propose | Log as potential attack |
| Policy config invalid | Startup validation | Refuse to start | Require fix before boot |

### 4.4 K9 Audit Ledger Failures

| Failure | Detection | Recovery | Escalation |
|---------|-----------|----------|------------|
| Write failure | I/O error | Buffer in memory, retry | Alert if buffer grows |
| Hash chain break | Verification check | Mark chain as broken | Alert security team |
| Storage full | Disk check | Rotate old logs | Alert, pause if critical |
| Redaction failure | Classifier error | Over-redact (safe default) | Log for review |

### 4.5 K18 Input Sanitization Failures

| Failure | Detection | Recovery | Escalation |
|---------|-----------|----------|------------|
| Extraction timeout | Timer exceeded | Return `SanitizedContent` with `quoted_data` + `unprocessed=true` (no extracted facts) | Log warning; require stricter policy gate if risk-tier is high |
| Injection heuristic false positive | — | Over-quarantine (safe default) | Queue for manual review |
| Classifier model failure | Health check / exception | Fail closed (reject content) | Alert, use rule-based fallback |
| Provenance tag missing | Validation check | Reject untraceable content | Log as policy violation |
| Malformed input | Schema validation | Return `ValidationError` | No retry; inform caller |
| Suspicion threshold exceeded | Heuristic score | Quarantine entire input | Escalate to human review |

### 4.6 Degraded Operation Modes

| Mode | Trigger | Capabilities | Exit Condition |
|------|---------|--------------|----------------|
| **Safe Mode** | Error rate >20%, circuit breaker trip | Read-only tools only, no side effects | Manual operator clear |
| **Fallback Mode** | Primary provider down | Secondary model, reduced capabilities | Primary health restored |
| **Maintenance Mode** | Operator command | No new runs, complete in-flight | Operator clear |
| **Emergency Stop** | Kill switch activation | Immediately halt all runs | Manual restart |

---

## 5) Concurrency and Ordering Guarantees

### 5.1 Within a Single Run

- **Sequential by default**: State transitions are single-threaded per run.
- **Parallel tool calls**: The orchestrator MAY execute independent tool calls in parallel if explicitly marked as parallelizable in tool metadata.
- **Ordering guarantee**: All tool calls within a step MUST complete before state transition.
- **At-most-once execution**: Each `(tool_name, idempotency_key)` pair executes at most once per run.

### 5.2 Across Concurrent Runs

- **Run isolation**: Runs are fully isolated; no shared mutable state except through tenant-scoped persistence.
- **Persistence locking**: K10 (Persistence) uses optimistic locking with version vectors; concurrent writes to the same run fail with `Conflict`.
- **Memory isolation**: K13 provides a documented consistency model for reads during a run (e.g., snapshot or monotonic reads); the chosen model is enforced and tested.

### 5.3 Distributed Execution (if applicable)

- **Coordinator election**: If runs span multiple nodes, a single coordinator owns the run until completion or timeout.
- **Lease-based ownership**: Run ownership expires after `run_lease_timeout_sec` (default: 600) if coordinator fails.
- **Handoff protocol**: Resumption requires re-acquiring lease and replaying from last checkpoint.

---

## 6) Interoperability Specification (Wire Protocols)

### 6.1 Model Boundary Protocol (K3)

**Request envelope:**
```json
{
  "@type": "ModelRequest",
  "trace_id": "uuid",
  "run_id": "uuid",
  "prompt_hash": "sha256:...",
  "messages": [...],
  "config": {
    "max_tokens": 8192,
    "temperature": 0.7,
    "stop_sequences": [...]
  }
}
```

**Response normalization:**
All provider responses are normalized to:
```json
{
  "@type": "ModelResponse",
  "trace_id": "uuid",
  "provider": "openai|anthropic|google|...",
  "model_id": "gpt-4o-2024-...",
  "content": "...",
  "usage": {"input_tokens": N, "output_tokens": M},
  "finish_reason": "stop|length|tool_use",
  "raw_response_hash": "sha256:..."
}
```

### 6.2 Tool Protocol (K4)

**Primary protocol: MCP-compatible JSON-RPC**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "send_email",
    "arguments": {...},
    "meta": {
      "trace_id": "uuid",
      "run_id": "uuid",
      "principal": "agent:abc123",
      "risk_tier": "high",
      "idempotency_key": "sha256:...",
      "timeout_ms": 30000
    }
  },
  "id": "request-uuid"
}
```

**Fallback: Direct function call** for in-process tools with identical metadata requirements.

### 6.3 Trace Event Format (K9)

**OpenTelemetry-compatible with kernel extensions:**
```json
{
  "timestamp": "2026-01-05T16:30:00.000Z",
  "trace_id": "uuid",
  "span_id": "uuid",
  "parent_span_id": "uuid|null",
  "name": "tool_call",
  "kind": "INTERNAL",
  "attributes": {
    "kernel.run_id": "uuid",
    "kernel.state": "ExecuteTool",
    "kernel.tool_name": "send_email",
    "kernel.risk_tier": "high",
    "kernel.principal": "agent:abc123",
    "kernel.outcome": "success|failure",
    "kernel.schema_version": "v0.1"
  },
  "events": [...],
  "status": {"code": "OK|ERROR"}
}
```

---

## 7) Cryptographic Profile

### 7.1 Algorithm Selection

| Purpose | Algorithm | Key Size | Notes |
|---------|-----------|----------|-------|
| Content hashing | SHA-256 | 256-bit | For `stable_hash()`, event chaining, deduplication |
| Fast hashing (non-security) | BLAKE3 | 256-bit | Optional for large content |
| Bundle signing | Ed25519 | 256-bit | Optional; requires key management |
| Secret encryption (at-rest) | AES-256-GCM | 256-bit | Via platform KMS |
| Secret encryption (in-transit) | TLS 1.3 | — | Required for all external communication |
| Event chain integrity | HMAC-SHA-256 | 256-bit | Keyed by per-run secret |
| Password/token derivation | Argon2id | — | If storing any credentials |

### 7.2 Key Management Requirements

- **Signing keys**: Stored in HSM or platform KMS; never in application memory.
- **Encryption keys**: Envelope encryption with data keys encrypted by master key in KMS.
- **Per-run secrets**: Derived from master key + run_id; used for event chain HMAC.
- **Rotation**: Signing keys rotated annually; encryption keys rotated on compromise.

### 7.3 Tamper-Evident Ledger (K9)

Each trace event includes:
```
event_n.chain_hash = HMAC-SHA-256(
  key = run_secret,
  message = event_n.hash || event_{n-1}.chain_hash
)
```

This creates a hash chain; tampering with any event invalidates all subsequent hashes.

**Security note:** A hash chain (including HMAC-chained events) detects post-hoc tampering in storage, but does **not** prevent a fully compromised writer from emitting forged events with valid hashes. For stronger guarantees, ship events to an external append-only/WORM log or perform signing in an HSM/KMS service not directly writable by the agent runtime.

---

## 8) Sandbox Implementation Reference (K8)

### 8.1 Technology Options

| Technology | Use Case | Isolation Level | Performance |
|------------|----------|-----------------|-------------|
| **nsjail** | Code execution (Python, JS) | Process + namespace | High |
| **gVisor (runsc)** | General container isolation | Syscall interception | Medium |
| **Firecracker** | High-security workloads | Full microVM | Lower |
| **WASM (Wasmtime)** | Lightweight plugins | Memory-safe sandbox | Highest |

**Default recommendation:** nsjail for code execution with seccomp-bpf filtering.

### 8.2 Default Sandbox Configuration

```yaml
sandbox:
  filesystem:
    root: read-only
    workdir: tmpfs (size: 100MB)
    no_mounts: ["/etc/passwd", "/etc/shadow", "/root", "/home"]
  
  network:
    enabled: false  # default
    allowlist: []   # explicit allowlist if enabled
  
  resources:
    max_memory_mb: 256
    max_cpu_time_sec: 30
    max_file_descriptors: 64
    max_processes: 10
  
  syscalls:
    policy: seccomp-bpf
    default: KILL
    allowlist: [read, write, open, close, mmap, ...]  # minimal set
  
  environment:
    scrub_all: true
    inject: ["PATH=/usr/bin", "LANG=C.UTF-8"]
    # NEVER inject secrets; use token broker
```

### 8.3 Secret Isolation

1. **Scrubbing**: All environment variables cleared before sandbox exec.
2. **Token broker**: Short-lived credentials fetched via secure channel (Unix socket or localhost HTTPS with mTLS).
3. **Credential lifetime**: Tokens expire after single use or 60 seconds, whichever is first.
4. **Audit**: All credential issuance logged with purpose, principal, and expiry.

---

## 9) Schema Evolution Policy

### 9.1 Versioning Scheme

**SemVer**: `MAJOR.MINOR.PATCH`
- **MAJOR**: Breaking changes requiring migration
- **MINOR**: Additive changes (new optional fields)
- **PATCH**: Bug fixes, documentation

Current version: **v0.1** (pre-release)

### 9.2 Compatibility Rules

| Artifact Type | Compatibility Requirement |
|---------------|---------------------------|
| Agent state | Read: N-1 → N supported; Write: current version only |
| Tool schemas | Must support N-1 (one major version back) |
| Policy bundles | Exact version match required |
| Trace events | Append-only; new fields optional |
| API contracts | N-1 supported for 6 months after deprecation |

### 9.3 Migration Requirements

1. **Migration scripts**: All schema changes require migration script in `/migrations/NNNN_description.py`.
2. **Bidirectional**: Every migration MUST have a rollback script.
3. **Testing**: Migrations tested against production-scale data samples before deploy.
4. **Atomicity**: Migrations are all-or-nothing; partial migration leaves system in prior state.

### 9.4 State Snapshot Compatibility

```json
{
  "schema_version": "v0.1",
  "state": {...},
  "checksum": "sha256:..."
}
```

Loader validates:
1. `schema_version` is supported
2. `checksum` matches computed hash
3. Required fields present per schema

Unsupported version → migration required → operator intervention.

---

## 10) Multi-Tenancy Invariants

### 10.1 Tenant Context Propagation

- Every request MUST carry `tenant_id` in authenticated envelope.
- `tenant_id` is immutable for the duration of a run.
- All kernel components propagate tenant context via explicit parameter or context object.
- Logs, metrics, and traces MUST include `tenant_id` as a first-class dimension.

### 10.2 Isolation Requirements

| Subsystem | Isolation Mechanism | Enforcement |
|-----------|---------------------|-------------|
| K13 Memory | Tenant-prefixed keys; query-layer rejection | Storage layer + validation |
| K9 Audit | Tenant-partitioned storage; access control | Query layer |
| K10 Persistence | Tenant-prefixed keys; optional per-tenant encryption | Storage layer |
| K6 Budgets | Per-tenant quota tables | Budget engine |
| K5 Policy | Tenant-scoped policy bundles | Policy loader |

### 10.3 Noisy Neighbor Protection

- **Rate limiting**: Per-tenant rate limits at ingress.
- **Resource quotas**: Per-tenant caps on concurrent runs, storage, compute.
- **Priority queues**: High-priority tenants (by tier) get preferential scheduling.
- **Isolation failures**: Cross-tenant data access attempts trigger immediate alert and run termination.

### 10.4 Tenant Offboarding

1. **Soft delete**: Tenant data marked for deletion; no new runs accepted.
2. **Retention period**: Data retained for 30 days (configurable) for recovery.
3. **Hard delete**: All tenant data purged; cryptographic keys destroyed.
4. **Audit trail**: Deletion events logged immutably.

---

## 11) Alerting and Incident Response

### 11.1 Alert Categories

| Category | Examples | Severity | Response Time |
|----------|----------|----------|---------------|
| **Security** | Sandbox escape attempt, policy bypass, credential leak | P0 | 15 min |
| **Reliability** | Error rate spike, circuit breaker trip, provider outage | P1 | 1 hour |
| **Compliance** | Audit chain break, redaction failure, retention violation | P1 | 1 hour |
| **Capacity** | Budget exhaustion, quota exceeded, storage full | P2 | 4 hours |
| **Performance** | Latency degradation, throughput drop | P3 | 24 hours |

### 11.2 Escalation Matrix

| Severity | Primary | Secondary | Executive |
|----------|---------|-----------|-----------|
| P0 | On-call engineer (page) | Security team (5 min) | CTO (15 min) |
| P1 | On-call engineer (page) | Team lead (30 min) | — |
| P2 | On-call engineer (ticket) | — | — |
| P3 | Team queue (async) | — | — |

### 11.3 Incident Playbooks (Required)

Every production deployment MUST have documented playbooks for:
1. **Safe mode activation**: When, how, and who can activate.
2. **Provider failover**: Steps to switch model providers.
3. **Circuit breaker management**: Manually resetting or adjusting thresholds.
4. **Credential rotation**: Emergency rotation on suspected compromise.
5. **Data breach response**: Containment, notification, forensics.
6. **Rollback procedure**: How to revert to previous artifact bundle.

### 11.4 Post-Incident Requirements

- **Blameless postmortem** within 72 hours of P0/P1 incidents.
- **Action items** tracked to completion.
- **Regression tests** added for failure mode.
- **Adversarial suite** updated if security incident.

---

## 12) Data Classification and Sensitivity Levels

### 12.1 Classification Taxonomy

| Level | Label | Examples | Retention |
|-------|-------|----------|----------|
| **L0** | Public | Published outputs, documentation | Indefinite |
| **L1** | Internal | Trace metadata, run IDs, aggregated metrics | 90 days default |
| **L2** | Confidential | User inputs, tool arguments, model responses | 30 days default |
| **L3** | Restricted | Secrets, PII, credentials, auth tokens | Never logged; encrypted at rest |

### 12.2 Handling Requirements by Level

| Level | Logging | Storage | Transmission | Access Control |
|-------|---------|---------|--------------|----------------|
| L0 | Full | Any | Any | None required |
| L1 | Full | Encrypted preferred | TLS required | Team-level |
| L2 | Redacted by default | Encrypted required | TLS required | Role-based |
| L3 | Never logged | Encrypted + KMS | mTLS required | Need-to-know + audit |

### 12.3 Classification Rules

**Automatic classification:**
- Content matching PII patterns (email, SSN, credit card) → L3
- Content containing `secret`, `password`, `token`, `key` in structured fields → L3
- User-provided free text → L2 (default)
- System-generated IDs and metadata → L1
- Explicitly published artifacts → L0

**Manual override:**
- Operators can upgrade (never downgrade) classification via policy.
- Downgrade requires security review and audit trail.

### 12.4 Kernel Invariants (Data Classification)

- All data entering the kernel MUST be classified at ingestion.
- Classification is immutable once assigned (no silent downgrades).
- L3 data MUST NOT appear in logs, traces, or error messages.
- Redaction applies classification rules before any write to persistent storage.
- Cross-level data mixing (e.g., L3 in L1 context) triggers alert and blocks operation.

---

## 13) Operational Lifecycle

### 13.1 Startup Sequence

1. **Load configuration** → validate schema, check required secrets present
2. **Initialize subsystems** → in dependency order (storage → audit → policy → tools → orchestrator)
3. **Run self-tests** → critical path verification (can write audit, can reach model, policy loads)
4. **Health check passes** → mark ready
5. **Accept traffic** → begin processing runs

**Startup invariants:**
- System MUST NOT accept traffic until all subsystems report healthy.
- Invalid configuration → refuse to start (fail-fast).
- Missing required secrets → refuse to start.

### 13.2 Health Check Contract

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `/health/live` | Process is running | `200 OK` if process alive |
| `/health/ready` | Can accept new runs | `200 OK` if all subsystems healthy |
| `/health/deep` | Detailed subsystem status | JSON with per-subsystem health |

**Health check invariants:**
- `ready` implies `live` (but not vice versa).
- Readiness probe failure → orchestrator stops routing traffic.
- Deep health includes: model reachability, storage write test, policy load status.

### 13.3 Graceful Shutdown

1. **Stop accepting new runs** → return `503 Service Unavailable` for new requests
2. **Drain in-flight runs** → wait up to `shutdown_grace_period_sec` (default: 30)
3. **Checkpoint incomplete runs** → K10 persistence with `interrupted` status
4. **Flush audit buffers** → K9 ensures all events written
5. **Close connections** → model providers, tool endpoints, storage
6. **Exit** → return appropriate exit code

**Shutdown invariants:**
- In-flight runs are checkpointed, not abandoned.
- Audit trail is complete up to shutdown (no lost events).
- If grace period exceeded → force stop, mark runs as `force_terminated`.

### 13.4 Cancellation Protocol

| Cancel Type | Trigger | Behavior | Outcome |
|-------------|---------|----------|---------|
| **Soft cancel** | User request, timeout approaching | Complete current step, checkpoint, stop | `status: cancelled`, partial result if applicable |
| **Hard cancel** | Kill switch, security alert | Immediate stop, no cleanup | `status: force_terminated`, no result |
| **Timeout cancel** | Budget exhausted (K6) | Stop after current tool completes | `status: timeout`, partial result |

**Cancellation invariants:**
- Side effects already committed (K10 outbox marked complete) are NOT rolled back.
- Pending side effects (outbox uncommitted) are NOT executed.
- Cancellation is logged as a first-class trace event with reason.
- Resources (sandbox, connections) are released on any cancel type.

### 13.5 Streaming Response Handling (K3 Extension)

For models that stream responses:

**Buffered mode (default, recommended):**
- Stream is buffered until complete.
- Validation runs on complete response.
- Downstream receives validated result only.
- Token counting on complete response.

**Incremental mode (optional, advanced):**
- Partial outputs validated incrementally where schema allows.
- Final validation on complete response.
- Validation failure → rollback partial outputs, return error.
- Requires explicit opt-in per use case.

**Streaming invariants:**
- Unvalidated streaming content MUST NOT reach downstream consumers.
- Streaming timeout applies to total stream time, not per-chunk.
- Partial stream failure is treated as complete failure (no partial results).

---

## 14) Common Expansion Modules (pick based on your product)

The kernel (§0-§13) is the **TCB (Trusted Computing Base)**. Everything below is **"userland"**: add only what your product needs, and keep modules swappable.

### E1. Knowledge & Grounding (RAG / KnowledgeOps)
**Add if:** your product promises *"answer from our docs/policies/tickets with citations"*.

**Minimum additions:**
- Retrieval tool boundary: `search_docs(query, filters) -> hits[]` with provenance (`doc_id`, `version`, `span_id`, `source`, `score`).
- Deterministic context compiler (explicit rules; strict "data ≠ instructions").
- Retrieval regression tests ("needle set": facts that must always be retrievable + cited).
- Injection hardening for retrieved text (treat as untrusted; apply K18).
- If multi-user: ACL-aware retrieval (access enforced at retrieval time).

**Skip risk:** Confident hallucinations that are hard to debug.

---

### E2. Distributed Runtime (Queues / Workers / Long-Running Jobs)
**Add if:** tasks take minutes+, you need concurrency, or request/response timeouts are unacceptable.

**Minimum additions:**
- Job queue + worker runner (same FSM, different execution substrate).
- Event-driven resume: "continue `run_id` from checkpoint N".
- Clear semantics: at-least-once at job level; side effects protected by K10 outbox + K4 idempotency.

**Skip risk:** Stuck runs, retries that duplicate work, operational pain.

---

### E3. Multi-Tenancy + Enterprise Governance
**Add if:** multiple customers/teams, regulated data, or strict audit/compliance requirements.

**Minimum additions:**
- Tenant-scoped storage (runs/memory/traces/artifacts) with hard isolation.
- Tenant-scoped tool capabilities + policy bundles.
- "Who can read what" for audit data.
- Retention + deletion workflows per tenant (ties into K9/K13/K16).

**Skip risk:** Cross-tenant exposure becomes existential risk.

---

### E4. Cost / Latency Engineering (Routing + Caching)
**Add if:** strict budgets, high volume, or heterogeneous tasks (planner vs coder vs summarizer).

**Minimum additions:**
- Node-level model routing policy (rules first; learned routing later).
- Fallback ladder: cheap → strong → human escalation.
- Caching where safe:
  - Prompt/prefix stability (KV-cache aware),
  - Tool result caching (with TTL/invalidation),
  - Semantic caching only with tight constraints and audit visibility.

**Skip risk:** Economic failure even when technically correct.

---

### E5. Advanced Deliberation (Best-of-N / Search) + Multi-Agent
**Add if:** system is safe but frequently "dumb" (bad plans) even with verifiers.

**Minimum additions:**
- Best-of-N **plans/tool-args** with verifier selection (not best-of-N prose).
- Bounded critic loop with explicit reject reasons and hard stop limits.
- For batch problems: supervisor/worker with isolated contexts + deterministic aggregation.

**Skip risk:** Reliable but underperforming on complex tasks.

---

### 14.1 Product Case Mapping

| Product Type | Usually Requires | Often Optional | Critical Kernel |
|--------------|------------------|----------------|-----------------|
| **Action Agent** (tickets → tools → changes) | E2, E4, sometimes E3 | E1 (unless policy-driven) | K5/K10/K15 |
| **Knowledge Agent** (doc Q&A with citations) | E1 | E3 if multi-team | K18/K13 |
| **Hybrid Agent** (answers + executes) | E1 + K5/K10/K15 | E2/E3/E4 by scale | Full kernel |
| **Coding Agent** (PRs, CI, refactors) | E2, E4, sometimes E5 | E1 for docs | K7/K8 + K5 two-phase |

**Rule of thumb:** Expand scope only when:
1. Required by product promise, OR
2. Resolves a dominant failure mode observed in production telemetry.

---

## Appendix A: Kernel vs Strategy Modules (what you can swap)

**Kernel (enforcement substrate):**
schemas, control loop, tool executor, policy gate, verifiers, sandbox, audit/replay, budgets, rate limiting, persistence, eval gates, input sanitization, data classification, alerting.

**Strategy modules (replaceable):**
prompting style, planner type, RAG method, ranking approach, model provider, agent persona, UI layer.

---

## Appendix B: Implementation Checklist

For each kernel subsystem, implementers MUST verify:

- [ ] Schema/types defined (Pydantic models or equivalent)
- [ ] Invariants have automated tests (unit + integration)
- [ ] Failure modes documented and tested (chaos/fault injection)
- [ ] Metrics/observability hooks present and dashboarded
- [ ] Configuration externalized (not hardcoded)
- [ ] Documentation includes usage examples
- [ ] Integration test with adjacent subsystems
- [ ] Security review completed (for K5, K8, K14, K18)
- [ ] Performance baseline established

---

## Appendix C: Reference Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              KERNEL BOUNDARY                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────────────────┐  │
│  │  Ingress    │───▶│  K18 Sanitizer  │───▶│  K2 Orchestrator            │  │
│  │  (authn)    │    │  (quarantine)   │    │  (FSM/state machine)        │  │
│  └─────────────┘    └─────────────────┘    └─────────────┬───────────────┘  │
│                                                          │                  │
│        ┌─────────────────────────────────────────────────┼──────────┐       │
│        │                                                 ▼          │       │
│        │  ┌───────────────┐    ┌───────────────┐    ┌───────────┐   │       │
│        │  │ K3 Model      │◀──▶│ K5 Policy     │◀──▶│ K4 Tool   │   │       │
│        │  │ Boundary      │    │ Engine        │    │ Executor  │   │       │
│        │  └───────────────┘    └───────────────┘    └─────┬─────┘   │       │
│        │         │                    │                   │         │       │
│        │         ▼                    ▼                   ▼         │       │
│        │  ┌───────────────┐    ┌───────────────┐    ┌───────────┐   │       │
│        │  │ K7 Verifier   │    │ K15 Human     │    │ K8 Sandbox│   │       │
│        │  │ Layer         │    │ Oversight     │    │           │   │       │
│        │  └───────────────┘    └───────────────┘    └───────────┘   │       │
│        │                                                            │       │
│        └────────────────────────────┬───────────────────────────────┘       │
│                                     │                                       │
│        ┌────────────────────────────┼────────────────────────────────┐      │
│        │                            ▼                                │      │
│        │  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐│      │
│        │  │ K9 Audit      │    │ K10 Persist   │    │ K13 Memory    ││      │
│        │  │ Ledger        │    │ + Resume      │    │ Governance    ││      │
│        │  └───────────────┘    └───────────────┘    └───────────────┘│      │
│        │                        DATA PLANE                           │      │
│        └─────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  K6 Budgets │ K11 Replay │ K12 Eval Gates │ K14 Identity │ K16 Ops   │   │
│  │                         CROSS-CUTTING CONCERNS                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix D: Kernel Public API Surface (Reference)

This appendix defines a *recommended* kernel **public API surface**: the stable “ABI” that strategy modules, tool adapters, memory implementations, and UIs integrate against.

The point is to make **method‑agnosticism enforceable** by interface:
- You can swap ReAct / planner / RAG / memory backend / UI without changing kernel safety claims.
- The kernel remains the Trusted Computing Base (TCB): it enforces budgets, policy gates, verification, and audit trails.

**Rule:** Everything not listed here is internal and MAY change without notice.

---

### D.1 Versioning and stability rules

- The kernel public API SHALL have a `kernel_api_version` (SemVer).
- Backwards‑compatible changes:
  - adding optional fields,
  - adding new event types (append‑only),
  - adding new ports with defaults.
- Breaking changes:
  - removing fields,
  - changing semantics of policy/approval binding,
  - changing canonicalization/hashing rules.

**Compatibility policy (recommended):**
- Support `N-1` API versions for 6 months after deprecation.
- Reject unsupported versions at startup (fail fast).

---

### D.2 Top-level runtime API

A minimal runtime API that keeps enforcement inside the kernel:

```python
from typing import Protocol, Literal, Optional
from pydantic import BaseModel
from uuid import UUID

class KernelRequest(BaseModel):
    kernel_api_version: str
    trace_id: UUID
    run_id: UUID
    tenant_id: str | None
    principal: str              # authenticated caller identity
    input: "SanitizedContent"   # K18 envelope
    mode: Literal["live", "replay"] = "live"
    bundle_id: str | None = None  # K16 bundle (optional in early levels)

class KernelResponse(BaseModel):
    trace_id: UUID
    run_id: UUID
    status: Literal["success", "failed", "cancelled", "timeout"]
    final_output: str | None
    outcome: dict               # typed domain outcome (K1)
    bundle_id: str | None
    metrics: dict               # cost/latency/violations summary (K9/K6)

class KernelRuntime(Protocol):
    def run(self, req: KernelRequest, *, strategy: "Strategy") -> KernelResponse: ...
    def resume(self, *, run_id: UUID) -> KernelResponse: ...
    def cancel(self, *, run_id: UUID, reason: str) -> None: ...
```

**Kernel invariants enforced by this API:**

- Strategy is injected, but cannot bypass enforcement (no tool handles are exposed to strategy).
    
- `mode="replay"` MUST be side‑effect free (no write tools; no live external calls).
    

---

### D.3 Strategy port (method-agnostic cognition)

The strategy is “userland”: replaceable logic that proposes what to do next.

Kernel requirement: strategies output **typed proposals**, not side effects.

```python
from typing import Protocol, Literal, Any
from pydantic import BaseModel
from uuid import UUID

class RunInfo(BaseModel):
    trace_id: UUID
    run_id: UUID
    tenant_id: str | None
    principal: str
    step: int
    budgets: dict              # remaining budgets summary (K6)
    bundle_id: str | None

class Observation(BaseModel):
    kind: Literal["user_input", "tool_result", "memory_read", "system_event"]
    content: "SanitizedContent"  # always the K18 envelope
    meta: dict

class StrategyContext(BaseModel):
    run: RunInfo
    tool_manifest: "ToolManifest"      # read-only tool specs (K4)
    observations: list[Observation]    # sanitized
    memory_snapshot: dict | None       # sanitized/validated (K13)

class ModelCallIntent(BaseModel):
    kind: Literal["model_call"] = "model_call"
    prompt_ref: str                   # artifact ref (K16) or prompt hash
    input: dict                       # typed prompt inputs
    output_schema_ref: str | None     # schema for structured output validation

class ToolCallIntent(BaseModel):
    kind: Literal["tool_call"] = "tool_call"
    tool_name: str
    arguments: dict                   # will be canonicalized + validated (K4)
    requires_commit: bool = False     # true for side effects (K5 two-phase)

class MemoryWriteIntent(BaseModel):
    kind: Literal["memory_write"] = "memory_write"
    record: dict                      # typed; includes provenance, TTL, classification

KernelIntent = ModelCallIntent | ToolCallIntent | MemoryWriteIntent

class StrategyProposal(BaseModel):
    intents: list[KernelIntent] = []
    final_answer: str | None = None
    stop: bool = False
    notes: dict = {}                  # non-authoritative debug hints

class Strategy(Protocol):
    strategy_id: str
    def propose(self, ctx: StrategyContext) -> StrategyProposal: ...
```

**Interpretation:**

- ReAct strategies produce a sequence of `ModelCallIntent` + `ToolCallIntent`.
    
- Planner/search strategies do the same.
    
- Multi-agent strategies can be expressed via a “mailbox tool” (messages are still untrusted input).
    

---

### D.4 Tool adapter port (implementation behind the kernel tool executor)

Tool adapters are NOT TCB, but they must obey the kernel tool protocol.  
The kernel tool executor owns:

- schema validation,
    
- canonicalization,
    
- timeouts/retries,
    
- idempotency keys,
    
- audit events,
    
- policy gating.
    

```python
from typing import Protocol, Any

class ToolMeta(BaseModel):
    trace_id: str
    run_id: str
    principal: str
    tenant_id: str | None
    idempotency_key: str
    timeout_ms: int

class ToolResult(BaseModel):
    ok: bool
    output: dict | None = None
    error: dict | None = None          # typed error taxonomy (K1/K4)

class ToolAdapter(Protocol):
    tool_name: str
    tool_version: str
    def preview(self, args: dict, meta: ToolMeta) -> ToolResult: ...
    def execute(self, args: dict, meta: ToolMeta) -> ToolResult: ...
```

**Kernel rule:** Strategies never receive a `ToolAdapter` or executor handle.

---

### D.5 Memory port (swappable backend, kernel-owned governance)

Memory is privileged. The backend is swappable; governance is kernel-owned.

```python
from typing import Protocol

class MemoryWriteRequest(BaseModel):
    tenant_id: str | None
    principal: str
    record: dict                      # typed record, includes provenance + TTL + class

class MemoryWriteResult(BaseModel):
    ok: bool
    record_id: str | None
    error: dict | None

class MemoryQuery(BaseModel):
    tenant_id: str | None
    principal: str
    query: dict                       # typed query language (vector/keyword/etc)

class MemoryReadResult(BaseModel):
    ok: bool
    records: list[dict] = []          # kernel wraps as SanitizedContent observations
    error: dict | None

class MemoryPort(Protocol):
    def write_memory(self, req: MemoryWriteRequest) -> MemoryWriteResult: ...
    def read_memory(self, q: MemoryQuery) -> MemoryReadResult: ...
```

---

### D.6 Approval + work-log ports (UI framework agnosticism)

Approval is kernel-required; UI is replaceable (React / CLI / Slack).

```python
from typing import Protocol, Literal

class ApprovalRequest(BaseModel):
    binding_hash: str
    tool_name: str
    preview: dict
    expires_at_epoch: int
    reason: str

class ApprovalDecision(BaseModel):
    binding_hash: str
    decision: Literal["approve", "deny"]
    actor: str                 # who approved/denied
    decided_at_epoch: int

class ApprovalPort(Protocol):
    def request_approval(self, req: ApprovalRequest) -> None: ...
    def wait_for_decision(self, *, binding_hash: str, timeout_sec: int) -> ApprovalDecision: ...
```

**Kernel rule:** commit MUST re-check policy + verify approval binding hash (TOCTOU safe).

---

### D.7 Trace + audit export ports (debugging/auditing depend on this)

The kernel MUST expose trace events in a portable format (OTel-like JSON is fine).

```python
from typing import Protocol

class TraceEvent(BaseModel):
    ts: str
    trace_id: str
    run_id: str
    name: str
    attributes: dict
    redacted: bool = True

class TraceSink(Protocol):
    def emit(self, evt: TraceEvent) -> None: ...
```

---

### D.8 Forbidden / non-public APIs

The following SHALL NOT be part of the public surface:

- any handle that lets strategy call tools directly,
    
- any API that allows writing audit logs from userland,
    
- any API that exposes secrets into model context,
    
- any “unsafe escape hatch” without a break-glass control plane gate.
    