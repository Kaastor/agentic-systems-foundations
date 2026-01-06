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

This guide is method‑agnostic about planning/RAG/model provider. It assumes the foundational premise:

> The model is an *untrusted proposal generator*. The kernel is the **enforcement substrate**.

---

## 1. Operating definitions

### 1.1 Kernel (TCB)
The **kernel** is the **Trusted Computing Base (TCB)**: the smallest set of code + policies that must remain correct for *all side effects, safety properties, and audit claims* to hold.

### 1.2 Strategy modules (userland)
**Strategies** are replaceable modules that propose what to do (planner, prompts, routing, RAG, multi-agent coordination). They are allowed to be wrong. The kernel must remain safe anyway.

### 1.3 A practical rule
If a component can:

- cause side effects,
- grant permissions,
- access secrets,
- decide “allow/deny/approve”,
- write audit logs,

…it’s kernel territory.

If a component can be swapped without changing safety claims, it’s strategy territory.

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

### 4.1 The dependency DAG (conceptual)

```
K1 ABI ─┬─> K9 Audit Ledger (classify+redact at ingestion) ─┬─> K2 Orchestrator ─┬─> K3 Model Boundary
        │                    │                    ├─> K4 Tool Executor
        │                    │                    ├─> K6 Budgets (cross‑cutting; includes rate limits when exposed)
        │                    │                    └─> K7 Verification (baseline)
        │                    │
        │                    ├─> K10 Persistence/Outbox (needs ABI + audit)
        │                    └─> K12 Evals (needs orchestrator + mocks)
        │
        ├─> K18 Sanitizer (ingress + untrusted content)
        └─> K13 Memory Gov (depends on ABI + persistence)
        
K5 Policy/Reference Monitor sits between Orchestrator and Tool Executor (required for **privileged capabilities**: writes **or** sensitive reads)
K14 Identity/Secrets feeds Policy + Tool Executor (principals/scopes)
K8 Sandbox is invoked by Tool Executor / Verifiers for risky execution
K11 Replay builds on Audit + Persistence
K16 Change Mgmt wraps “everything as artifacts”
```

### 4.2 The recommended implementation sequence (phases)

#### Phase A — “A kernel that runs” (day one)
1. **K1 ABI**: typed run state, tool calls/results, errors, trace events
2. **K9 minimal audit**: append-only event stream (even if just JSONL locally)
3. **K2 orchestrator**: explicit FSM with stop conditions
4. **K3 model boundary**: validated structured outputs; bounded repair
5. **K6 budgets**: hard step/time/token caps
5a. **K16‑min (thin slice): bundle manifest + `bundle_id` recording**
   - Start recording a `bundle_id` per run that captures: prompt bundle hash, tool manifest hash, policy bundle hash (if present), and schema version.
   - This is cheap early and prevents “we can’t reproduce it” later.
6. **K4 tool executor**: schema validation + timeouts + typed errors
7. **K7 baseline verification**: schema/type checks for all structured outputs
8. **K18 sanitizer** (if any external content): quarantine + quoting + suspicion flags

Deliverable: a read-only agent that is debuggable and bounded.

#### Phase B — “Safe action” (when you add writes)
9. **K5 policy + reference monitor**: central gate, default deny, 2‑phase execution
10. **K10 outbox + idempotency**: durable intent records; replay-safe
11. **K15 approval UX hook**: approve/deny tokens bound to hashes
12. **K14 identity/secrets**: scoped creds, “secrets never in prompt” enforcement

Deliverable: an action agent that cannot write without the gate.

#### Phase C — “Production hardening” (before you scale)
13. **K12 eval harness + CI gates (+ K12a discipline)**: regression + injection + tool misuse suites; suite cards + immutable suite versions for any gated suite
14. **K11 replay + fault injection**: reproduce incidents deterministically
15. **K16‑full change mgmt + rollback**: versioned bundles, canary/progressive delivery, automated rollback triggers, migrations, rollback drills
16. **K17 portability**: export traces/schemas/bundles (prevents lock‑in)

Deliverable: a system you can safely operate under real failure modes.

---

## 5. Repo architecture (keep the TCB small, prevent leakage)

### 5.1 Design goals
A good repo layout makes the *wrong* code hard to write:

- Strategy modules **cannot** cause side effects directly
- Policies are **versioned artifacts** (not “prompt vibes”)
- Kernel package has **minimal dependencies** and a small public API
- “Action boundary” is unmissable in code review

### 5.2 A reference monorepo layout

```
repo/
  pyproject.toml
  README.md

  packages/
    kernel_tcb/                      # ✅ The Trusted Computing Base (small)
      pyproject.toml
      src/kernel_tcb/
        abi/                         # K1: typed system model
        audit/                       # K9: ledger + event schema + redaction
        orchestrator/                # K2: FSM runtime
        model/                       # K3: model boundary + prompt renderer
        tools/                       # K4: tool protocol + executor wrappers
        policy/                      # K5: reference monitor + policy engine
        budgets/                     # K6: budget enforcement
        verify/                      # K7: verifier framework
        sanitize/                    # K18: untrusted content pipeline
        persistence/                 # K10: checkpoints + outbox
        identity/                    # K14: principals + scopes (no secrets in prompts)
        interop/                     # K17: export formats (optional)
        _internal/                   # internal helpers (not imported by userland)
      tests/                         # kernel invariants tests (must be strong)

    strategies/                      # ❌ NOT TCB (swappable)
      pyproject.toml
      src/strategies/
        planners/                    # prompt-based, heuristic, search-based planners
        prompting/                   # prompt templates, few-shots, routing rules
        rag/                         # retrieval ranking, chunking, rewriters
        critics/                     # optional critics (never enforcement)
        __init__.py

    tool_adapters/                   # tool implementations (not TCB)
      pyproject.toml
      src/tool_adapters/
        jira/
        github/
        email/
        filesystem/
        web/
        ...

    apps/
      agent_service/                 # FastAPI/gRPC app wiring (not TCB)
      cli/                           # local runner

  policies/                          # policy bundles (versioned, tested)
    default/
      policy.yaml
      constraints/
      tests/

  prompts/                           # prompt bundles (versioned, hashed)
    planner_v1/
    summarizer_v2/
    ...

  evals/                             # K12: scenarios, adversarial suites, goldens
    regression/
    injection/
    tool_misuse/
    datasets/

  ops/
    dashboards/
    runbooks/
    terraform/
    k8s/

  contracts/                          # import boundaries + architecture tests
    importlinter.contracts.ini
```

### 5.3 Boundary enforcement mechanisms (do all three)

#### (1) Package boundaries (hard)
- `kernel_tcb` is a separate package with a *small public API*.
- Strategies depend on `kernel_tcb` interfaces only (Protocols, dataclasses).
- **Kernel must never import strategies** (dependency inversion).

#### (2) Import-lint contracts (automated)
Use `import-linter` (or similar) to enforce:
- `kernel_tcb` cannot import `strategies` or `tool_adapters`
- `tool_adapters` cannot import `kernel_tcb._internal`
- `policies/` and `prompts/` are data-only (no Python imports)

Example `contracts/importlinter.contracts.ini`:
```ini
[importlinter]
root_package = repo

[contract:kernel_isolated]
name = Kernel cannot depend on strategies or adapters
type = forbidden
source_modules =
    packages.kernel_tcb.src.kernel_tcb
forbidden_modules =
    packages.strategies.src.strategies
    packages.tool_adapters.src.tool_adapters
```

#### (3) Runtime capabilities (unbypassable)
- Strategies never receive a `ToolExecutor` handle.
- Strategies output only **typed proposals** (e.g., `ProposedAction` objects).
- The orchestrator invokes tools only through the kernel reference monitor.

---

## 6. Concrete Python patterns (production-friendly)

The following snippets show *shape*, not full implementation. The goal is to make enforcement code boring, deterministic, and testable.

### 6.1 K1: ABI + stable hashing (deterministic, auditable)

```python
# packages/kernel_tcb/src/kernel_tcb/abi/base.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
import hashlib
import json
from typing import Any, Literal
from uuid import UUID

class ABIModel(BaseModel):
    # Freeze schema by default: unknown fields are rejected.
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        """Deterministic serialization.

        If you change serialization policy, you are changing the ABI.
        Keep it explicit to avoid accidental hash drift.
        """
        payload = self.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def stable_hash(self, *, domain: str = "abi") -> str:
        """Domain-separated stable hash to prevent cross-protocol reuse."""
        msg = (f"{domain}:v1|" + self.canonical_json()).encode("utf-8")
        h = hashlib.sha256(msg).hexdigest()
        return f"sha256:{h}"


class TraceContext(ABIModel):
    trace_id: UUID
    run_id: UUID
    tenant_id: str | None = None  # Optional until multi-tenant
```

**Kernel rule:** any hash used for approval binding, idempotency, or audit integrity must be computed from **canonicalized** representations.

---

### 6.2 K4: Tool specs and a tool manifest (kernel-owned metadata)

```python
# kernel_tcb/abi/tools.py
from pydantic import BaseModel, Field
from typing import Any, Literal

RiskTier = Literal["low", "medium", "high"]

class ToolSpec(BaseModel):
    name: str
    version: str
    risk_tier: RiskTier
    has_side_effects: bool
    input_schema: dict[str, Any]      # JSON Schema
    output_schema: dict[str, Any]
    supports_preview: bool = False
    supports_idempotency: bool = True
    timeout_ms_default: int = 30_000

class ToolManifest(BaseModel):
    tools: list[ToolSpec]
    manifest_version: str

    def tool_by_name(self, name: str) -> ToolSpec:
        for t in self.tools:
            if t.name == name:
                return t
        raise KeyError(f"Unknown tool: {name}")
```

**Anti-footgun:** ignore model-supplied risk tiers, principals, and idempotency keys. Those are kernel-owned and derived from manifest + identity context.

---

### 6.3 K2: Orchestrator as explicit FSM (no “while model says”)

```python
# kernel_tcb/orchestrator/fsm.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

class State(Enum):
    START = "start"
    PLAN = "plan"
    PROPOSE_ACTIONS = "propose_actions"
    EXECUTE = "execute"
    VERIFY = "verify"
    DONE = "done"
    FAILED = "failed"

ALLOWED_TRANSITIONS: dict[State, set[State]] = {
    State.START: {State.PLAN, State.FAILED},
    State.PLAN: {State.PROPOSE_ACTIONS, State.DONE, State.FAILED},
    State.PROPOSE_ACTIONS: {State.EXECUTE, State.DONE, State.FAILED},
    State.EXECUTE: {State.VERIFY, State.FAILED},
    State.VERIFY: {State.PLAN, State.DONE, State.FAILED},
    State.DONE: set(),
    State.FAILED: set(),
}

@dataclass(frozen=True)
class RunState:
    state: State
    step: int
    # domain-specific fields omitted

class Planner(Protocol):
    def propose_next(self, run_state: RunState) -> "PlanProposal": ...

class CancellationToken:
    """Kernel-owned cancel signal.

    Strategies can *request* cancellation, but only the kernel can decide when to stop.
    """
    def __init__(self):
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def check(self) -> None:
        if self._cancelled:
            raise RuntimeError("run_cancelled")


class Orchestrator:
    def __init__(
        self,
        *,
        planner: Planner,
        budgets: "BudgetEnforcer",
        audit: "AuditLedger",
        cancel: CancellationToken,
    ):
        self._planner = planner
        self._budgets = budgets
        self._audit = audit
        self._cancel = cancel

    def transition(self, run_state: RunState, new_state: State) -> RunState:
        if new_state not in ALLOWED_TRANSITIONS[run_state.state]:
            raise ValueError(f"Illegal transition: {run_state.state} -> {new_state}")
        return RunState(state=new_state, step=run_state.step + 1)

    def run(self, initial: RunState) -> RunState:
        s = initial
        cancel = self._cancel
        while s.state not in (State.DONE, State.FAILED):
            self._budgets.check_step(s.step)
            self._audit.emit("state_enter", {"state": s.state.value, "step": s.step})
            cancel.check()

            if s.state == State.START:
                s = self.transition(s, State.PLAN)
            elif s.state == State.PLAN:
                proposal = self._planner.propose_next(s)
                s = self.transition(s, State.PROPOSE_ACTIONS if proposal.actions else State.DONE)
            # ... execute through reference monitor, then verify ...
            # If cancellation happens mid-tool-call and the tool cannot be cancelled,
            # the kernel must quarantine late results and discard them after abort.
        return s
```

**Kernel invariant:** stop conditions and budget checks are outside the model.

---

### 6.4 K6: Budgets as a cross-cutting gate

```python
# kernel_tcb/budgets/budget.py
from dataclasses import dataclass
import time

@dataclass
class Budget:
    max_steps: int = 50
    max_wall_clock_sec: int = 300

class BudgetExceeded(RuntimeError): pass

class BudgetEnforcer:
    def __init__(self, budget: Budget):
        self._budget = budget
        self._t0 = time.monotonic()

    def check_step(self, step: int) -> None:
        if step > self._budget.max_steps:
            raise BudgetExceeded("max_steps exceeded")
        if (time.monotonic() - self._t0) > self._budget.max_wall_clock_sec:
            raise BudgetExceeded("max_wall_clock_sec exceeded")
```

---

### 6.5 K5: Reference monitor + two-phase execution (Propose → Preview → Commit)

This is the architectural “keystone” for action agents: **no write without a gate**.

```python
# kernel_tcb/policy/decisions.py
from pydantic import BaseModel
from typing import Literal

Decision = Literal["allow", "deny", "needs_approval"]

class PolicyDecision(BaseModel):
    decision: Decision
    reason: str
    binding_hash: str  # sha256(tool + canonical_args + preview_hash)
    expires_at_epoch: int | None = None
```

```python
# kernel_tcb/policy/reference_monitor.py
class ReferenceMonitor:
    def __init__(self, policy: "PolicyEngine", tools: "ToolExecutor", approvals: "ApprovalStore", audit: "AuditLedger"):
        self._policy = policy
        self._tools = tools
        self._approvals = approvals
        self._audit = audit

    def propose(self, intent: "ToolIntent") -> "ToolPreview":
        """Phase 1: compute a preview/diff and decide allow/deny/approval.

        Preview MUST be read-only. If preview cannot be made deterministic, treat the tool as high-risk:
        default to needs_approval (or deny) and bind approval to the canonical args.
        """
        preview = self._tools.preview(intent)
        binding_hash = compute_binding_hash(intent, preview)
        decision = self._policy.evaluate(intent=intent, preview=preview, binding_hash=binding_hash)

        self._audit.emit("policy_decision", {
            "phase": "propose",
            "decision": decision.decision,
            "binding_hash": binding_hash,
        })

        if decision.decision == "deny":
            raise PermissionError(decision.reason)

        # Persist the binding for resumability and to prevent “approval drift” across retries.
        self._approvals.record_proposal(binding_hash=binding_hash, preview_hash=preview.stable_hash())

        if decision.decision == "needs_approval":
            self._approvals.request(binding_hash=binding_hash, expires_at=decision.expires_at_epoch)

        return preview

    def commit(self, intent: "ToolIntent", *, approval_token: str | None) -> "ToolResult":
        """Phase 2: re-evaluate policy and commit exactly what was approved.

        TOCTOU-safe: policy re-check + approval bound to binding_hash.
        """
        preview = self._tools.preview(intent)
        binding_hash = compute_binding_hash(intent, preview)

        self._audit.emit("policy_decision", {
            "phase": "commit",
            "binding_hash": binding_hash,
        })

        decision = self._policy.evaluate(intent=intent, preview=preview, binding_hash=binding_hash)
        if decision.decision == "deny":
            raise PermissionError(decision.reason)

        stored = self._approvals.lookup(binding_hash)
        if stored and stored.preview_hash != preview.stable_hash():
            raise PermissionError("preview_changed_requires_reapproval")

        if decision.decision == "needs_approval":
            self._approvals.assert_valid(approval_token=approval_token, binding_hash=binding_hash)

        return self._tools.execute(intent)
```

**Key properties**
- Approvals bind to a **hash of the exact effect**.
- Policy evaluation happens at **propose** and **commit** time.
- If preview is impossible, policy must default to “needs approval” or deny.

---

### 6.6 K10: Durable outbox (exactly-once side effects at the kernel boundary)

```python
# kernel_tcb/persistence/outbox.py
from pydantic import BaseModel
from typing import Literal

Status = Literal["pending", "committed", "failed"]

class OutboxRecord(BaseModel):
    idempotency_key: str
    tool_name: str
    canonical_args_json: str
    status: Status

class Outbox:
    def __init__(self, store: "KVStore"):
        self._store = store

    def begin(self, record: OutboxRecord) -> None:
        # Must be atomic. If already exists, do not re-execute side effect.
        self._store.put_if_absent(key=record.idempotency_key, value=record.model_dump_json())

    def mark_committed(self, idempotency_key: str) -> None:
        rec = OutboxRecord.model_validate_json(self._store.get(idempotency_key))
        self._store.put(idempotency_key, rec.model_copy(update={"status": "committed"}).model_dump_json())
```

Integrate with tool execution:
1. compute idempotency key from canonical `(tool, args, run_id)`
2. write `pending`
3. execute tool
4. mark `committed` if success

Note: the outbox guarantees **exactly-once at the kernel boundary**. End-to-end “exactly once effects” still depend on tool-side idempotency or compensating semantics.

---

### 6.7 K18: Sanitized content envelope (data ≠ instructions)

```python
# kernel_tcb/sanitize/envelope.py
from pydantic import BaseModel
from typing import Literal

class SanitizedContent(BaseModel):
    provenance: dict
    classification: Literal["L0", "L1", "L2", "L3"]
    suspicion_flags: list[str] = []
    quoted_data: str                 # safe-to-insert "data channel"
    extracted_facts: dict | None = None
    unprocessed: bool = False
```

**Kernel rule:** downstream prompt rendering must insert `quoted_data` only into a **data channel** (quoted/serialized), never into system/developer instruction text.

---

### 6.8 K9: Audit ledger with hash chaining (tamper-evident)

```python
# kernel_tcb/audit/ledger.py
import hmac, hashlib, json, time
from pydantic import BaseModel

class AuditEvent(BaseModel):
    ts: float
    name: str
    payload: dict
    prev_chain_hash: str
    chain_hash: str

class AuditLedger:
    def __init__(self, run_secret: bytes, sink: "AppendOnlySink"):
        self._k = run_secret
        self._sink = sink
        self._prev = "genesis"

    def emit(self, name: str, payload: dict) -> None:
        ts = time.time()
        msg = json.dumps({"ts": ts, "name": name, "payload": payload}, sort_keys=True).encode()
        event_hash = hashlib.sha256(msg).hexdigest().encode()
        chain = hmac.new(self._k, event_hash + self._prev.encode(), hashlib.sha256).hexdigest()
        evt = AuditEvent(ts=ts, name=name, payload=payload, prev_chain_hash=self._prev, chain_hash=chain)
        self._sink.append(evt.model_dump_json())
        self._prev = chain
```

For higher assurance, ship events to an external append-only store not writable by the agent runtime.

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

This section is the “do this, in this order, with these artifacts” playbook so the reliability layer behaves like an OS and the strategy layer stays method/domain agnostic.

**Goal:** if someone follows this playbook, you get:
- enforced kernel invariants (K1–K18),
- a stable kernel public API (strategy/tool/memory/UI ports),
- evals that gate releases,
- debugging and auditing that are operationally usable (not aspirational).

---

### 9.1 The invariant-first build rule

For every kernel subsystem you implement:
1. **Define the typed contract** (K1).
2. **Implement the enforcement code** (fail closed).
3. **Add invariant tests** (unit + integration).
4. **Emit trace events + metrics** (K9).
5. **Add at least one eval case** that would have caught a realistic failure.

If any step is missing, treat the subsystem as “not implemented.”

---

### 9.2 “Reliability layer as OS” — what must be kernel-owned

Kernel-owned (TCB):
- orchestration FSM + stop conditions (K2),
- model boundary + validation + bounded repair (K3),
- tool executor + canonicalization + idempotency metadata (K4),
- policy/reference monitor + two-phase commit (K5),
- budgets/rate limits/circuit breakers (K6),
- verification framework + verifiers (K7),
- audit ledger + redaction at ingestion (K9),
- persistence/outbox/resume semantics (K10),
- sanitizer + untrusted content envelope (K18).

Not kernel-owned (replaceable strategy/userland):
- prompts, planners, routing policies,
- RAG chunking/ranking approaches,
- memory backend implementations,
- UI framework (React/CLI/Slack),
- domain workflows (education tutoring, support triage, code review, etc.).

---

### 9.3 Concrete “from empty repo → Level 2” implementation sequence

This sequence is intentionally specific. It avoids the common failure mode: “we built a cool agent and retrofitted controls.”

#### Step 1 — ABI + hashing (K1)
Deliverables:
- `ABIModel` base with canonical JSON + stable hash.
- `TraceContext`, `RunManifest`, `ToolIntent`, `ToolResult`, error taxonomy.

Required tests:
- `test_canonical_json_stable_ordering`
- `test_stable_hash_domain_separation`
- `test_unknown_fields_rejected`

#### Step 2 — Audit ledger (K9)
Deliverables:
- append-only event sink (JSONL is fine initially),
- classification + redaction at ingestion,
- tamper-evident chaining (hash chain).

Required tests:
- `test_redaction_before_write`
- `test_hash_chain_verifies`
- `test_agent_cannot_write_ledger_via_tools` (architecture boundary test)

#### Step 3 — Deterministic orchestrator FSM (K2)
Deliverables:
- explicit FSM states + allowed transitions table,
- explicit stop conditions,
- cancellation token (abort is kernel-owned).

Required tests:
- `test_illegal_transition_denied`
- `test_max_steps_enforced`
- `test_abort_quarantines_late_results`

#### Step 4 — Model boundary (K3)
Deliverables:
- deterministic prompt renderer + prompt hashing,
- provider-normalized response schema,
- bounded structured-output repair.

Required tests:
- `test_prompt_hash_recorded`
- `test_repair_bounded`
- `test_oversize_output_fails_closed`

#### Step 5 — Tool executor (K4)
Deliverables:
- tool manifest loader (versioned),
- schema validation, timeouts/retries,
- kernel-generated idempotency keys,
- typed error taxonomy.

Required tests:
- `test_tool_args_canonicalized_before_hashing`
- `test_model_cannot_set_principal_or_risk_tier`
- `test_timeout_returns_typed_error`

#### Step 6 — Budgets + thrash controls (K6)
Deliverables:
- per-run budgets (steps/time/tokens/cost),
- tool retry bounds,
- circuit breakers.

Required tests:
- `test_budget_exhaustion_stops_run`
- `test_retry_bounded_and_typed`
- `test_circuit_breaker_trips_on_threshold`

#### Step 7 — Sanitization pipeline (K18)
Deliverables:
- `SanitizedContent` envelope with provenance, classification, suspicion flags,
- “data channel only” enforcement in prompt construction.

Required tests:
- `test_untrusted_content_never_in_instruction_channel`
- `test_suspicion_flags_logged`
- `test_missing_provenance_rejected`

#### Step 8 — Minimal eval harness (K12)
Deliverables:
- test case schema (YAML/JSON),
- runner that executes scenario runs against the kernel,
- a CI gate that fails on constraint violations.

Required tests/evals:
- 10 golden regression cases,
- 10 prompt injection cases (direct + indirect),
- 5 tool misuse cases (even if read-only tools at Level 2).

Exit criteria (Level 2 readiness):
- you can replay a failing eval case deterministically (K11 becomes strongly recommended here).

---

### 9.4 Concrete “from Level 2 → Level 3 action agent” sequence

When you add side effects, you MUST add these *before* the first real write.

#### Step 9 — Policy + reference monitor (K5)
Deliverables:
- default deny policy bundle,
- allowlists + deterministic constraints,
- two-phase execution (propose → preview → approve → commit),
- approval binding hash (tool + canonical args + preview hash),
- policy evaluated at propose-time AND commit-time.

Required tests:
- `test_no_write_without_gate`
- `test_approval_binding_hash_required`
- `test_toctou_hash_mismatch_denied`

#### Step 10 — Outbox + resume safety (K10)
Deliverables:
- durable outbox intent records,
- idempotency semantics documented per tool.

Required tests:
- `test_resume_does_not_duplicate_side_effect`
- `test_outbox_pending_never_committed_on_cancel`

#### Step 11 — Approval UX port (K15)
Deliverables:
- approval request/decision interface (UI-agnostic),
- work-log rendering based on trace events (K9).

Required tests:
- `test_approval_expiry_enforced`
- `test_commit_requires_matching_binding_hash`

#### Step 12 — Identity + secrets governance (K14)
Deliverables:
- agent principals with scoped creds,
- “no secrets in prompt” enforcement,
- secret access audit events.

Required tests:
- `test_secrets_never_enter_model_context`
- `test_scoped_credential_required_for_tool`

---

### 9.5 What evals MUST look like in practice (behavior + artifacts)

Your Constitution and Kernel already specify *what must be true*. This section defines the **operator-facing artifacts** you should standardize so evals are usable.

#### Eval harness behaviors
- Evals run the kernel in a deterministic scenario mode:
  - tools can be mocked OR replayed,
  - model calls can be replayed OR pinned (recorded responses),
  - privileged side effects are disabled unless the test explicitly exercises approval/commit logic.
- Every test case MUST be able to assert:
  - required trace events occurred,
  - no forbidden events occurred,
  - policy outcomes match expected (allow/deny/escalate),
  - constraint violations are zero for gated suites.

#### Standard eval output artifacts (recommended)
For every eval run produce:
- `eval_run_summary.json`
  - suite IDs + versions/hashes,
  - kernel bundle ID,
  - overall pass/fail,
  - aggregate metrics (success rate, violation rate, escalation rate, cost stats),
  - flake/retry counts.
- `eval_cases/<case_id>/`
  - `trace.jsonl` (kernel trace events for the case),
  - `inputs.json` (sanitized case input),
  - `expected.json` (assertions),
  - `artifacts.json` (prompt hashes, policy bundle hash, tool manifest hash).
- `eval_report.md`
  - top regressions,
  - diff vs previous run (what got worse/better),
  - links to the worst failing traces.

This makes evals a first-class evidence artifact for reviews.

---

### 9.6 Debugging playbook (how engineers actually debug a run)

When something goes wrong, the workflow should be mechanical:

1. **Get identifiers**
   - `run_id`, `trace_id`, `bundle_id` (K16), principal, tenant_id.

2. **Inspect the trace**
   - find the first failure event (`policy_denied`, `tool_error`, `verification_failed`, `budget_exceeded`).
   - identify the exact state node and prior observation that triggered it.

3. **Replay deterministically (K11)**
   - run in `mode=replay` with recorded model/tool I/O,
   - confirm the failure reproduces with zero external calls.

4. **Narrow the fault**
   - if policy denied: inspect policy bundle + constraints; add policy unit test.
   - if tool failed: inspect tool adapter error; add fault-injection case.
   - if verifier failed: inspect verifier logs; add regression eval case.

5. **Promote to regression**
   - every incident class becomes a new eval case (scenario or adversarial).

**Rule:** if you cannot replay it, you cannot reliably fix it.

---

### 9.7 Auditing playbook (what auditors/operators must be able to answer)

Minimum audit queries the kernel should support (by trace events + metadata):
- show all privileged commits in a time window,
- for each commit: who approved, what binding hash, what preview/diff, what tool args (redacted), what outcome,
- show policy deny rates by tool and by principal,
- show all runs touching a given tenant_id,
- verify audit chain integrity for a given run_id,
- demonstrate “break-glass logging” enablement events (who/when/why) if used.

If you can’t answer these from your K9 ledger, your “auditability” claim is marketing.

---

## Appendix A — Minimal “MVP to Production” checklist

**MVP (internal demo)**
- K1, K2, K3, K4, K6, K7(min), K9
- **K12 (minimal)**: harness skeleton + a small regression/injection pack
- K18 if any untrusted external content

**Internal pilot (real users, limited blast radius)**
- K12 (full gates) + **K12a** (suite cards + immutable gated suites)
- K13 if memory/RAG
- K11 replay for reproducible incidents
- **K16‑min**: bundle manifest + record `bundle_id` per run
- **Risk register updated each release** (with evidence links)

**External production / scaled production**
- Everything above, plus:
  - **K16‑full** progressive delivery + rollback + migrations + rollback drills
  - multi-tenant isolation if applicable (Level 4)
  - stronger audit posture (tamper evidence + external sink where required)


---

## Appendix B — Traceability matrix (Constitution → Kernel → Evidence)

This appendix exists to make reviews and audits fast: every “SHALL” maps to kernel mechanisms and concrete evidence.

**How to use**
- Add rows whenever you introduce a new safety claim.
- For each row, link to the exact test(s), eval(s), and telemetry that prove the claim.
- Treat this as a living artifact: incidents add rows or strengthen evidence.

| Constitution requirement (Article) | Kernel subsystem(s) | Guide level where REQUIRED | Evidence (tests/evals/telemetry) |
|---|---|---|---|
| Actor outputs are non-authoritative; enforcement is external | K2, K5, K7 | L1+ | `test_no_write_without_gate`, `test_fail_closed_on_invalid_output`, policy decision logs |
| Boundedness + explicit stop conditions | K2, K6 | L1+ | `test_max_steps`, `test_abort_quarantines_late_results`, budget exhaustion metrics |
| Untrusted content discipline (data ≠ instructions) | K18, K13, K3 | L1+ when ingesting external content | injection eval pack, sanitizer suspicion flags, context compiler tests |
| Pre-commit authorization barrier for privileged actions | K5, K15, K10 | L3+ (writes) | approval-binding-hash tests, outbox dedupe tests, approval audit events |
| No deploy without passing gates | K12 (+ K16 for external prod) | L2+ real users; external prod requires K16 | CI gate logs, canary results, rollback drill evidence, risk register update check |
| Eval suite governance: suite cards + immutable gate suites (no silent edits) | K12a, K16 | L2+ real users; any gated suite | suite card files, suite version hashes in CI logs, flake-policy config, changelog entries |
| Risk register updated as part of release gating | (Governance) + K12/K16 | L2+ real users; all production paths | risk register diff in PR, evidence links updated (eval run IDs/tests/dashboards), release checklist artifact |


---

## Appendix C — A small “architecture test” you should actually run

Even without import-linter, add a test that prevents kernel/strategy coupling:

```python
def test_kernel_does_not_import_strategies():
    import pkgutil
    import kernel_tcb

    bad = []
    for m in pkgutil.walk_packages(kernel_tcb.__path__, kernel_tcb.__name__ + "."):
        module = __import__(m.name, fromlist=["*"])
        src = getattr(module, "__file__", "") or ""
        if "strategies" in src or "tool_adapters" in src:
            bad.append(m.name)

    assert not bad, f"Kernel imports userland modules: {bad}"
```

It’s crude, but it catches accidental boundary erosion early.

---


## Appendix D — Kernel invariants test index (template)
Make it impossible to “forget” an invariant by indexing it.

Example `kernel_tcb/tests/invariants/INDEX.md`:
- K1 ABI: `test_canonical_hash_stable`, `test_schema_versioning`
- K2 FSM: `test_illegal_transition_denied`, `test_abort_quarantines_late_results`
- K3 Model boundary: `test_prompt_hash_recorded`, `test_repair_bounded`
- K4 Tool executor: `test_model_cannot_set_principal`, `test_timeout_typed_error`
- K5 Policy: `test_no_write_without_gate`, `test_approval_binding_hash`
- K6 Budgets/Rate limits: `test_max_steps`, `test_tenant_rate_limit_429`
- K9 Audit: `test_redaction_before_write`, `test_hash_chain_verifies`
- K10 Outbox: `test_resume_does_not_duplicate_side_effect`
- K12 Evals: `test_ci_gate_fails_on_injection_case`

If a subsystem exists, it has at least one invariant test. No exceptions.

## Appendix E — Policy bundle skeleton (data-only)
A minimal `policies/default/policy.yaml` shape:

```yaml
policy_version: 1
default: deny
principals:
  - name: agent:default
    allowed_tools:
      - name: search_docs
        mode: read
      - name: create_ticket
        mode: write
        requires_approval: true
        constraints:
          project_allowlist: ["ENG", "OPS"]
          max_description_chars: 4000
rate_limits:
  ingress_per_tenant_rps: 5
  tool_calls_per_minute:
    create_ticket: 10
``` 

Store policy tests next to it (e.g., `policies/default/tests/`).

## Appendix F — Assurance case mini-template (for high-risk agents)
For each hazard, link controls to evidence:

```yaml
system: "agent_service"
scope: "email + ticketing"
hazards:
  - id: H1
    description: "Unauthorized external write"
    unacceptable_loss: "User trust + real-world harm"
    controls:
      - K5: "Reference monitor blocks writes unless policy allows"
      - K15: "High-risk writes require explicit approval"
      - K10: "Outbox prevents duplicate writes on retries"
    evidence:
      - test: "test_no_write_without_gate"
      - eval: "tool_misuse/high_risk_write_without_approval"
      - telemetry: "policy_denies_per_day"
  - id: H2
    description: "Prompt injection causes harmful action"
    controls:
      - K18: "Sanitizer quarantines and flags suspicious content"
      - K5: "Untrusted content cannot authorize actions"
    evidence:
      - eval: "injection/indirect_webpage_instructions"
``` 

Keep this close to the release gates so it can’t rot.

## Appendix G — What to do when you *must* move fast
If you’re under schedule pressure, do not cut the kernel. Cut features.

A “safe read-only agent” beats a “clever action agent” with no gate every time.

---

## Appendix H — Multi-agent message discipline (when you add multi-agent coordination)

Multi-agent systems expand the untrusted surface area: an agent message is just another form of tool output / external content.

**Kernel rules (treat as invariants for any multi-agent setup)**
1. **Inter-agent messages are untrusted input**. They must flow through the same ingestion path as other external content:
   - sanitize + envelope (K18),
   - provenance tags (sender identity, run_id/trace_id),
   - suspicion flags are first-class metadata.

2. **Authenticated sender identity is required**:
   - each agent runs under a distinct principal (K14),
   - the receiver must log sender principal and enforce per-sender policy.

3. **Schema validation is mandatory**:
   - agent messages must be typed (K1),
   - malformed messages fail closed.

4. **Rate limits and circuit breakers apply to agent-to-agent traffic**:
   - per-sender and per-receiver limits (K6),
   - cascading failure prevention: if an upstream agent misbehaves, isolate it.

5. **No cross-agent capability escalation**:
   - an agent cannot “delegate” a privileged capability it doesn’t possess,
   - the receiver’s policy gate (K5) remains authoritative.

**Practical default:** implement multi-agent messaging as a kernel-owned “mailbox tool” whose payload is always wrapped in `SanitizedContent`.

---

e kernel via Ports & Adapters (Hexagonal Architecture)
The kernel defines **stable “ports” (interfaces + ABIs)**. Everything outside the kernel implements “adapters” for those ports.

**Kernel-owned ports (stable contracts)**
- **Actor Port (K3):** call a model provider through a normalized request/response envelope.
- **Strategy Port (userland):** propose next step(s) as typed *proposals* (never direct side effects).
- **Tool Port (K4):** execute tool calls through the kernel executor only.
- **Policy/Approval Port (K5/K15):** authorization + approval workflow (UI-agnostic).
- **Memory Port (K13):** reads/writes with provenance, TTL, classification; backend-agnostic.
- **Retrieval Port (E1 + K18/K13):** search/lookup returning typed chunks with provenance/ACL/classification.
- **Audit/Telemetry Port (K9):** append-only events + traces + metrics.
- **Persistence/Outbox Port (K10):** checkpoint + outbox semantics; storage-agnostic.

**Why this preserves method-agnosticism**
- ReAct vs planner vs multi-agent only changes Strategy behavior (what proposals are emitted), not kernel enforcement.
- RAG and memory can be swapped as long as they return the same typed envelopes and satisfy kernel governance rules.

---

### J.2 Runtime view: Control plane vs Data plane

**Control plane (TCB / kernel-owned)**
1) **Ingress/API**
- AuthN/AuthZ, derives `principal`, `tenant_id`, request classification context.
- Applies ingress rate limits (per tenant/user).

2) **K18 Sanitization pipeline**
- Wraps all external content into `SanitizedContent` (data-channel safe).
- Sets provenance, classification, suspicion flags.

3) **K2 Orchestrator (deterministic FSM / workflow engine)**
- Runs explicit states and transitions.
- Enforces budgets (K6) and stop conditions.
- Owns cancellation/abort; quarantines late results.

4) **K3 Model boundary**
- Provider-normalized, schema-validated outputs, bounded repair.
- Records prompt hash + model params in trace.

5) **K5 Reference monitor + policy engine**
- Complete mediation for privileged reads/writes.
- Two-phase execution for writes (propose/preview/approve/commit).
- Evaluated at propose and commit (TOCTOU safe).

6) **K4 Tool executor**
- Validates args, canonicalizes, generates idempotency keys, timeouts/retries, logs.
- Calls tools only through adapters/transport.

7) **K10 Outbox + checkpoints**
- Durable intent records prevent duplicate side effects on retries/resume.

8) **K9 Audit ledger + telemetry**
- Append-only, tamper-evident chain (or external sink).
- Redaction/classification before any write/ship.

9) **K13 Context compiler + memory governance**
- Deterministic context assembly.
- Memory writes validated, TTL’d, quarantined if suspicious.
- Tenant isolation enforced.

**Data plane (non-TCB, replaceable)**
- tool adapters/connectors (Jira/GitHub/email/etc.)
- retrieval backends (search index/vector DB)
- memory backends (SQL/KV/vector)
- UI clients (React, CLI, Slack)
- model provider SDKs (wrapped by K3 boundary)

---

### J.3 A method-agnostic “Strategy Port” (ReAct / planner / multi-agent all fit)
The kernel never calls “ReAct” directly. It calls a Strategy interface that emits typed proposals.

Example shape (conceptual):
- Strategy receives a **KernelView** (read-only run state + sanitized observations).
- Strategy emits one of:
  - propose tool intent(s),
  - propose retrieval/memory operations,
  - propose a user-facing response,
  - propose escalation/approval request.

**Kernel rule:** proposals are not effects. Effects only happen if the kernel authorizes and executes.

This allows:
- ReAct loops (think-act-tool-observe) as a Strategy implementation,
- plan-and-execute strategies,
- search-based planners,
- multi-agent supervisor/worker strategies (messages treated as untrusted content and sanitized).

---

### J.4 Pluggable RAG with a stable kernel
To stay method-agnostic, the kernel constrains *interfaces and governance*, not ranking algorithms.

**Retrieval Port contract**
- Input: query + filters + principal/tenant context.
- Output: list of `RetrievedChunk` objects with:
  - provenance (`doc_id`, `version`, `span`, `source`),
  - ACL/tenant scope confirmation,
  - classification level,
  - raw text always treated as untrusted and routed through K18 before entering prompts.

**Kernel enforcement**
- Retrieved text cannot enter instruction channels.
- Retrieval adapters must be ACL-aware (or the kernel wraps them with an ACL gate).
- Injection suites specifically target retrieved content paths.

Swap BM25↔vectors↔hybrid freely; the kernel stays stable.

---

### J.5 Pluggable memory with a stable kernel
Memory is governed via a kernel-defined ABI and invariants:
- provenance required,
- TTL required (unless explicitly classed as profile memory with opt-in),
- validation on write,
- quarantine path for suspicious content,
- tenant isolation and deletion hooks.

**Memory Port contract**
- `write_memory(MemoryWriteRequest) -> MemoryWriteResult`
- `read_memory(MemoryQuery) -> MemoryReadResult`
Where request/result types include: `principal`, `tenant_id`, classification, provenance, TTL, and a stable hash.

Backend can be Postgres, Redis, vector DB, or files; governance stays kernel-owned.

---

### J.6 UI/UX method-agnosticism (React vs CLI vs Slack)
Approval and transparency are kernel requirements, but the UI is replaceable.

**Approval Port**
- Kernel emits an `ApprovalRequest` event (with binding hash, preview/diff, expiry).
- Any UI can render it (React app, CLI prompt, Slack bot).
- UI returns an `ApprovalDecision(binding_hash, approve|deny, actor)` through a stable API.
- Kernel verifies binding hash and expiry before commit.

**Work log / transparency**
- UI consumes kernel trace events (K9) to render step-by-step execution, pause/stop controls.
- UI choice does not change safety claims because enforcement is kernel-owned.

---

### J.7 Release plane (how K12/K12a/K16 + Risk Register connect)
A production-grade program needs a release plane that is as method-agnostic as runtime.

**Release artifacts**
- Bundle manifest (`bundle_id`) containing hashes/versions for prompts/policies/tools/verifiers/schemas/workflows and gated eval suites.
- Risk register updated per release (linked to evidence).
- Suite cards + immutable suite versions (K12a).

**Release gates**
- CI runs scenario + adversarial suites; gates are pinned to suite versions/hashes.
- Canary/shadow evals run post-deploy on a fixed scenario set; rollback triggers are defined (K16-full).

This structure lets you change strategy methods (ReAct → plan search) without changing kernel safety claims: you ship a new bundle, run the same gated eval suites, and compare telemetry.

This appendix is the “method-agnosticism by construction” answer the Constitution calls for (observable properties over techniques, equivalent mechanisms).  

---

### Appendix I — Staff-level reference architecture (stable kernel, swappable strategies)

This appendix is a concrete reference architecture that cleanly satisfies:
- the Constitution (external enforcement, least privilege, auditability, eval gates),
- the Kernel Blueprint invariants (K1–K18),
while staying **method-agnostic** (ReAct vs planners vs search; different RAG and memory backends; different UIs).

---

### I.1 Architectural style: “ports & adapters” (hexagonal)

- The **kernel** is the inner hexagon (TCB). It defines:
  - types (ABI),
  - ports (interfaces),
  - enforcement logic.
- Everything else is an adapter or strategy plugin.

**Why this matters:** method-agnosticism becomes an interface guarantee:
- Strategies can change without safety claim changes.
- UIs can change without approval semantics changes.
- RAG/memory backends can change without trust boundary changes.

---

### I.2 Component diagram (runtime)

```

┌──────────────────────────────────────────────────────────────────────────────┐  
│ APPLICATION │  
│ (API server / CLI / Slack bot / React UI — NOT TCB) │  
└───────────────┬───────────────────────────────────────────────┬──────────────┘  
│ │  
│ requests │ approvals + worklog UI  
▼ ▼  
┌──────────────────────────────────────────────────────────────────────────────┐  
│ KERNEL (TCB) │  
│ │  
│ Ingress/AuthN/AuthZ (tenant/principal) │  
│ │ │  
│ ▼ │  
│ K18 Sanitizer ──> K2 Orchestrator (FSM) ──> Strategy Port (swappable) │  
│ │ │ │ │  
│ │ │ proposes intents │ │  
│ │ ▼ ▼ │  
│ │ K3 Model Boundary (no tool handles!) │  
│ │ │ │  
│ │ ▼ │  
│ │ K5 Reference Monitor + Policy Engine │  
│ │ │ │  
│ │ propose/preview│ approve │ commit │  
│ │ ▼ │  
│ │ K4 Tool Executor (schema/timeout/idempotency) │  
│ │ │ │  
│ │ ▼ │  
│ │ K7 Verifiers (veto) │  
│ │ │  
│ ├───────────────┬──────────────────┬───────────────────────────────┐ │  
│ ▼ ▼ ▼ ▼ │  
│ K9 Audit Ledger K10 Persistence K13 Memory Gov K6 Budgets │  
│ (tamper-evident) + Outbox (provenance/TTL) + breakers │  
└──────────────────────────────────────────────────────────────────────────────┘  
│  
▼  
┌──────────────────────────────────────────────────────────────────────────────┐  
│ ADAPTERS (NOT TCB, SWAPPABLE) │  
│ Tool adapters (Jira/GitHub/Email/Web), Memory backends (SQL/Vector/Files), │  
│ Model providers, Trace sinks (OTel), Approval UIs │  
└──────────────────────────────────────────────────────────────────────────────┘

```

---

### I.3 How method-agnosticism works (ReAct, planners, different RAG, different memory)

#### A) ReAct vs planner vs search
All methods compile down to the same kernel interface:
- strategy emits `ModelCallIntent` and `ToolCallIntent`,
- kernel executes with budgets + validation + audit,
- privileged intents go through policy + approvals,
- verifiers can veto outcomes.

So “ReAct” becomes just *one* implementation of `Strategy.propose(ctx)`.

#### B) Different RAG methods
RAG is not a kernel feature; it is:
- either a tool (`search_docs`) backed by BM25/vector/hybrid,
- or a strategy module technique for choosing which retrieval calls to make.

Kernel requirement remains the same:
- retrieved text is untrusted → goes through K18 → becomes `SanitizedContent`.

#### C) Different memory implementations
Memory backend is behind the `MemoryPort`:
- Postgres, Redis, vector DB, files — all acceptable.
Kernel owns:
- write validation, provenance, TTL/deletion, quarantine (K13),
- “data ≠ instructions” discipline when memory is injected into context (K18/K3).

#### D) UI framework (React vs CLI vs Slack)
The UI only implements the Approval Port + Worklog rendering:
- kernel emits `ApprovalRequest(binding_hash, preview, expiry)`,
- UI returns `ApprovalDecision(binding_hash, approve|deny)`,
- kernel verifies binding hash and re-checks policy at commit time.

The UI is not allowed to change semantics.

---

### I.4 The “stable kernel” rule: effects only through the reference monitor

To keep the kernel stable while strategies churn:
- Strategies MUST NOT call tools directly.
- Strategies MUST NOT write audit logs.
- Strategies MUST NOT mint/handle secrets.
- Strategies only propose typed intents.

Everything effectful is routed:
`StrategyProposal → Orchestrator → ReferenceMonitor → ToolExecutor/Memory → Verifiers → Audit`.

That guarantees safety even if the strategy is wrong or compromised.

---

### I.5 Optional “control plane” (recommended once you ship)

For real production you need a thin control plane that is also method-agnostic:
- bundle registry (K16): prompts/policies/tools/schemas/verifiers + hashes,
- eval registry (K12/K12a): suite versions + suite cards + gates,
- risk register + assurance case linking bundles → eval evidence.

This keeps “strategy innovation” decoupled from “safety claims.”