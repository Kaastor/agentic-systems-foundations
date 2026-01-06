# Concrete implementation playbook for a staff-level kernel

This playbook is the “how” companion to:
- `constitution.md` (normative requirements),
- `kernel.md` (K1–K18 invariants),
- `adoption.md` (build order + maturity ladder).

Goal: make it **hard to accidentally violate** kernel invariants in real codebases.

This is written like a staff engineer’s internal playbook: opinionated about boundaries, testing, and operational discipline — but **method-agnostic** about planning/RAG/memory/model providers.

---

## 0. How to use this document

Treat this as a checklist you walk in order:

1. Implement a subsystem.
2. Add its invariant tests.
3. Add its observability hooks.
4. Add its failure-injection tests.
5. Only then let strategy/userland depend on it.

If a section feels “too much for an MVP,” build a smaller product — do not weaken the kernel boundary.

---

## 1. Kernel implementation non-negotiables

These rules prevent most real-world agent failures.

### 1.1 The “no privileged handles in userland” rule

Strategy code MUST NOT receive:
- tool executor objects,
- database connections,
- filesystem/network clients,
- audit log writers,
- policy decision functions.

Strategy code MAY receive:
- a read-only `StrategyView`,
- a kernel-wrapped model boundary client (K3),
- a typed way to propose tool intents and memory writes.

If you violate this, you will eventually ship a bypass.

### 1.2 Typed ABI + canonicalization everywhere (K1)

Pick one canonical serialization format for hashing (JSON with sorted keys is common).
Then:
- any hash used for approvals, idempotency, caching, or audit integrity MUST be derived from canonicalized bytes,
- canonicalization MUST be tested (golden vectors).

### 1.3 “Classify + redact at ingestion” is not optional (K9 + K18)

Before writing:
- logs,
- traces,
- persistence records,
- error messages,

you MUST classify and redact.

This is the difference between “we think we didn’t log secrets” and “we can prove we didn’t log secrets.”

### 1.4 Default deny, fail closed (K5)

If policy evaluation fails (exception, missing rule, unknown tool):
- deny or escalate.
Never allow.

### 1.5 One-run determinism beats cleverness (K2 + K11)

Design the orchestrator so that:
- runs can be replayed,
- state transitions are explicit,
- side effects are mediated and idempotent.

A clever planner is useless if you can’t debug it.

---

## 2. Repo architecture and boundary enforcement

Use all three (defense in depth):

### 2.1 Package boundaries
- `kernel_tcb/` is its own package with a **small** public API.
- strategies are a separate package that depends on kernel interfaces only.

### 2.2 Import-lint / architecture tests
Automate “kernel cannot import strategies/adapters” contracts.

### 2.3 Runtime capability discipline
- tools only execute through kernel reference monitor,
- strategies produce proposals only.

If you can’t enforce (2.3), (2.1) and (2.2) are just paperwork.

---

## 3. Build sequence with definitions of done

This section is the practical “do X, then prove X works” guide.

### Phase A — A bounded, auditable read-only kernel

#### A1) K1: ABI (Typed System Model)
**Implement**
- Pydantic/dataclass models for: run state, tool intent/result, model request/response, policy decision, verifier result, trace event.
- deterministic serialization + stable hashing.

**Definition of done**
- ✅ `test_canonical_json_stable` (golden)
- ✅ `test_schema_rejects_unknown_fields`
- ✅ `test_every_event_has_trace_and_run_id`

#### A2) K9: Audit ledger + trace events (minimal)
**Implement**
- append-only event sink (JSONL is fine initially),
- hash chain integrity (HMAC) if possible,
- redaction at ingestion.

**Definition of done**
- ✅ `test_hash_chain_verifies`
- ✅ `test_redaction_before_write`
- ✅ run emits state transitions + model/tool events with trace IDs

#### A3) K2 + K6: Orchestrator (FSM) + budgets + cancel
**Implement**
- explicit state machine with allowed transitions,
- step/time/cost budgets,
- cancellation semantics (quarantine late results).

**Definition of done**
- ✅ `test_illegal_transition_denied`
- ✅ `test_max_steps_enforced`
- ✅ `test_abort_quarantines_late_results`

#### A4) K3: Model boundary (LLM as tool)
**Implement**
- prompt bundles as versioned artifacts,
- structured outputs with schema validation,
- bounded repair attempts,
- provider normalization and usage accounting.

**Definition of done**
- ✅ `test_prompt_hash_recorded`
- ✅ `test_repair_is_bounded`
- ✅ `test_oversize_output_fails_closed`

#### A5) K4: Tool executor (read-only tools)
**Implement**
- tool manifest (tool name/version/risk/side-effects/preview support),
- input schema validation + canonicalization,
- timeouts/retries, typed errors,
- consistent logging.

**Definition of done**
- ✅ `test_tool_args_canonicalized_before_hash`
- ✅ `test_timeout_returns_typed_error`
- ✅ `test_model_supplied_principal_ignored`

#### A6) K18: Sanitization pipeline
**Implement**
- `SanitizedContent` envelope,
- provenance tagging,
- suspicion flags,
- strict “data channel only” insertion policy.

**Definition of done**
- ✅ injection cases show suspicious flags
- ✅ `test_untrusted_content_never_enters_instruction_channel`
- ✅ sanitizer events appear in trace for user/tool content

At this point, you have a bounded, observable, replay-friendly read-only agent runtime.

---

### Phase B — Safe action (writes)

#### B1) K5: Reference monitor + policy engine (two-phase)
**Implement**
- central policy evaluator (default deny),
- `propose()` + `preview()` + `commit()` flow,
- binding hash: `H(tool, canonical_args, preview_hash)`,
- approvals with expiry and identity.

**Definition of done**
- ✅ `test_no_write_without_gate`
- ✅ `test_approval_binding_hash_required`
- ✅ `test_policy_rechecked_on_commit` (TOCTOU)

#### B2) K10: Durable outbox + idempotency
**Implement**
- outbox record written before side effect,
- mark committed after success,
- resume consults outbox to prevent duplicates.

**Definition of done**
- ✅ `test_resume_does_not_duplicate_side_effect`
- ✅ `test_idempotency_key_kernel_owned`
- ✅ crash-injection test mid-tool-call produces no double-commit

#### B3) K15: Human oversight hooks
**Implement**
- approval UX surface (API + UI),
- pause/stop controls,
- safe mode and kill switch wiring.

**Definition of done**
- ✅ you can disable writes without redeploy (config/flag)
- ✅ approvals are required for high-risk tools in policy bundle
- ✅ audit ledger records approvals/denials

#### B4) K14: Identity + secrets governance
**Implement**
- distinct agent principal(s),
- scoped credentials per tool,
- “secrets never in prompt” enforcement.

**Definition of done**
- ✅ `test_secrets_not_in_model_context`
- ✅ `test_tool_calls_are_attributed_to_principal`
- ✅ secret issuance logged (without logging the secret)

---

### Phase C — Production hardening

#### C1) K12/K12a: Eval harness + release gates
**Implement**
- suite cards + rubrics (versioned),
- deterministic runner (supports replay/stubs),
- CI gates: fail on invariant violations.

**Definition of done**
- ✅ CI fails if any “no-approval commit” case fails
- ✅ eval runs emit `eval_run_id` + `bundle_id`
- ✅ flake policy exists in suite card; no silent retries

#### C2) K11: Record/replay + fault injection
**Implement**
- record tool I/O + model I/O (redacted),
- replay mode is side-effect free,
- fault injection hooks: timeouts, partial responses, crashes.

**Definition of done**
- ✅ incident reproduction can run offline from a recorded bundle
- ✅ `test_replay_mode_never_executes_real_tools`
- ✅ chaos tests exist for at least model timeout + tool timeout + policy exception

#### C3) K16: Artifact bundles + canary + rollback
**Implement**
- bundle manifest includes hashes for prompts/tools/policies/schemas/verifiers/evals,
- canary rollout support,
- rollback procedure is tested.

**Definition of done**
- ✅ every run records exact bundle IDs
- ✅ rollback drill works in staging
- ✅ migrations are versioned + reversible if you store state/memory

#### C4) K17: Export formats (portability)
**Implement**
- export run bundle for replay,
- export traces in a portable structure (OTel-like),
- export tool schemas.

**Definition of done**
- ✅ you can replay a run in a different environment from exported artifacts

---

## 4. Method agnosticity patterns (how to keep strategies swappable)

### 4.1 Strategy interface: proposals only
Strategies should be “proposal generators.” They can be:
- LLM-driven (ReAct),
- heuristic/rule-based,
- symbolic planners,
- multi-agent coordinators.

They all output the same typed proposal objects.

### 4.2 Retrieval as a tool contract
Different RAG stacks should appear as different implementations of the same stable tool contract.

Kernel enforces:
- ACLs/scopes,
- sanitization,
- provenance.

### 4.3 Memory governance wrapper
Backends vary; governance doesn’t.

The kernel owns:
- schema validation,
- TTL/retention,
- provenance,
- quarantine.

---

## 5. What evals should look like (concrete)

A production-grade eval harness is:
- **artifact-based**: suites and rubrics are versioned and immutable once used as gates,
- **trace-backed**: failures link to trace evidence,
- **risk-mapped**: each suite maps to hazards/controls.

Minimal required outputs for gated suites:
- per-case outcome,
- violation tags,
- aggregate metrics,
- bundle IDs,
- runner version,
- randomness controls (seeds, retries).

See `adoption.md` §9.1 for a minimal schema.

---

## 6. Debugging and auditing playbooks (minimum viable operations)

### 6.1 The debugging loop
**Reproduce → Replay → Patch → Add tests → Release**

If you skip the “add tests” step, you will re-live the incident.

### 6.2 The auditing loop
**Claim → Control → Evidence**

Your traceability matrix (Adoption Appendix B) should be kept current:
- every “SHALL” maps to kernel subsystem(s),
- each subsystem has tests/evals/telemetry evidence.

---

## 7. Staff-level code review checklist (copy/paste)

Before approving a change that touches the kernel boundary:

- [ ] Does this expand the TCB? If yes, why is it unavoidable?
- [ ] Can a strategy module bypass the policy gate after this change?
- [ ] Are tool args canonicalized before hashing/logging/outbox keys?
- [ ] Are secrets/PII redacted before any write?
- [ ] Are policy decisions logged (propose + commit)?
- [ ] Are cancellation semantics preserved (no late side effects)?
- [ ] Did we add or update invariant tests and eval cases?
- [ ] Is the change captured in the bundle manifest and versioned?

If you can’t answer these, the kernel isn’t ready to scale.

---

## 8. Where this playbook plugs into the docs

- Normative requirements: `constitution.md`
- Kernel invariants: `kernel.md` (K1–K18)
- Operational adoption plan: `adoption.md`
- Concrete trace shape: `example_run_trace.md`

This set is the reliability “OS.” Strategy layers (education tutor logic, planners, RAG) should sit on top of it.