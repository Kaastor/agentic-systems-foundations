# Kernel Implementation Playbook
**Status:** Staff-level reference implementation guide for the Kernel Blueprint (TCB)  
**Core language:** Python  
**Version:** v1.2  
**Last updated:** 2026-01-08

---

## 0. Purpose and scope

This playbook is the **“how”**: concrete engineering guidance for implementing a production-grade **kernel (TCB)** for reliable, constrained agentic systems.

- The **Constitution** defines the *normative properties* the system must exhibit (enforceability, boundedness, auditability, independent verification).
- The **Kernel Blueprint** defines the *kernel invariants* (K1–K18).
- The **Adoption Guide** defines *when* to adopt which subsystems, by maturity level / blast radius.

This playbook focuses on:

- a reference architecture that keeps the **TCB small** (hexagonal / ports-and-adapters),
- implementation patterns that are **boring, deterministic, testable**,
- code snippets that are **copy‑pasteable** and close to production quality,
- a build sequence that yields a working kernel early, then hardens safely.

---

## 0.1 Agentic system properties crosswalk

Map the common agentic system properties to concrete kernel subsystems you will implement here, grouped by theme:

**Enforcement and authorization**
- **Complete mediation:** K4 tool executor (tools cannot bypass executor), K5 reference monitor + policy gate, and the strategy boundary in §1.1.
- **External enforcement over internal instruction:** strategy outputs are proposals; K5 policy + K4 executor enforce effects.
- **Capability contracts / tool law:** K4 tool specs (purpose, risk tier, IO schemas, scope, reversibility) + K5 authorization barrier.
- **Side effects gated:** K5 two-phase propose -> preview -> approve -> commit, plus K10 outbox/idempotency and K15 approval UX.
- **Least privilege / capability scoping:** K4 tool manifest + K5 policy + K14 identity/secrets.
- **Scope confinement (read vs write, domain/resource allowlists):** K4 tool manifest + K5 parameter constraints.
- **Identity and non-human principals:** K14 scoped credentials + K4 principal metadata.
- **Security hardening / sink-safe tool interfaces:** K4 sink-safe execution + K8 sandboxing + K14 secrets.

**Determinism and bounded execution**
- **Deterministic control (explicit state machine):** K2 orchestrator + K1 state model.
- **Deterministic validation / typed interfaces:** K1 ABI + K3 model boundary + K4 tool executor + K7 schema checks.
- **Fail-closed defaults:** K3 invalid output handling + K5 deny by default + K6 budget stops + K18 sanitization.
- **Bounded autonomy:** K2 stop conditions + K6 budgets/loop controls/circuit breakers (K15 safe mode for degradation).
- **Idempotency + resumability:** K4 idempotency keys + K10 outbox/resume semantics.
- **Breakpoints/watchlist triggers:** K6 budget thresholds + K9 alerts + K15 kill switch.

**Verification, evidence, and release**
- **Independent verification:** K7 verification layer (veto path), with deterministic checks for high-risk actions.
- **Testability / evidence-backed claims:** K12 eval harness + invariant tests for K1 to K7.
- **Audit + replay:** K9 audit ledger + K10 persistence/outbox + K11 replay hooks.
- **Observability + accountability (tamper-evident audit):** K9 traces/metrics/ledger + redaction at ingestion.
- **Reproducibility / fault injection:** K11 record/replay + deterministic fault injection.
- **Eval gates + rollback:** K12 eval harness + K16 change management/rollback.
- **Governance and risk management:** K12 eval gates + K16 change management + risk register in adoption playbook.
- **Operational hardening / continuous response:** K6 circuit breakers + K15 safe mode + K16 rollback + K9 monitoring.

**Data, memory, and threat handling**
- **Untrusted data discipline (data != instructions):** K18 sanitization + K13 context compiler.
- **Threat model / adversarial inputs:** K18 sanitization + K8 sandboxing + K5 policy constraints.
- **Isolation / sandboxing:** K8 isolation boundaries for untrusted execution.
- **Memory governance:** K13 provenance, TTL, and retention controls.

**Architecture and human factors**
- **Method-agnosticism / replaceable strategies:** architecture boundary in §1.2 + K1 ABI + K17 portability.
- **Portability / exportability:** K17 exportable bundles, traces, and schemas.
- **Human oversight + action transparency:** K9 action ledger + K15 preview/approve/deny + pause/stop/takeover.
- **Multi-agent isolation and cross-agent validation:** K5 policy boundaries + K13 tenant isolation + K9 trace correlation.
- **Simplicity / least-agentic pattern:** adoption guidance + replaceable strategies in §1.2.

### Lite coverage (teaching track)

Lite scope follows `adoption.md` §7.2. Coverage codes:
- Full: in Lite scope without simplification
- Lite: included but simplified
- Partial: subset of property covered
- Excluded: not in Lite scope

| Group | Property | Lite coverage | Why (teaching scope) |
| --- | --- | --- | --- |
| Enforcement | Complete mediation | Lite | K4 full + K5 lite gate; no binding hash |
| Enforcement | External enforcement over internal instruction | Lite | Strategy boundary + K5 lite enforcement |
| Enforcement | Capability contracts / tool law | Lite | K4 schemas/specs; K5 lite authorization |
| Enforcement | Side effects gated | Lite | CLI approval + allowlist; no preview/binding hash; K10 lite outbox |
| Enforcement | Least privilege / capability scoping | Partial | Tool allowlist only; no K14 secrets broker |
| Enforcement | Scope confinement (read vs write, domain/resource allowlists) | Partial | Simple allowlist; no rich param constraints |
| Enforcement | Identity and non-human principals | Excluded | K14 excluded in lite |
| Enforcement | Security hardening / sink-safe tool interfaces | Partial | K4 sink-safe patterns; no K8 sandbox/K14 secrets |
| Determinism | Deterministic control (explicit state machine) | Full | K1/K2 full in lite |
| Determinism | Deterministic validation / typed interfaces | Lite | K1 full, K3 basic, K4 full, K7 lite |
| Determinism | Fail-closed defaults | Lite | K3 basic + K5 lite + K6 caps + K18 |
| Determinism | Bounded autonomy | Partial | K2/K6 full; no K15 safe mode |
| Determinism | Idempotency + resumability | Lite | K4 full + K10 lite outbox |
| Determinism | Breakpoints/watchlist triggers | Partial | K6 caps; no K9 alerting or K15 kill switch |
| Verification | Independent verification | Lite | K7 lite schema checks only |
| Verification | Testability / evidence-backed claims | Partial | Unit/invariant tests; no K12 eval gates |
| Verification | Audit + replay | Partial | K9 lite audit + K10 lite; no K11 replay |
| Verification | Observability + accountability (tamper-evident audit) | Partial | JSONL audit, no hash chain |
| Verification | Reproducibility / fault injection | Excluded | K11 excluded |
| Verification | Eval gates + rollback | Excluded | K12/K16 excluded |
| Verification | Governance and risk management | Excluded | Risk register/release governance not in lite |
| Verification | Operational hardening / continuous response | Partial | K6 caps only; no K15 safe mode or K16 rollback |
| Data | Untrusted data discipline (data != instructions) | Partial | K18 full; no K13 context governance |
| Data | Threat model / adversarial inputs | Partial | K18 sanitization; no K8 sandbox |
| Data | Isolation / sandboxing | Excluded | K8 excluded |
| Data | Memory governance | Excluded | K13 excluded |
| Architecture | Method-agnosticism / replaceable strategies | Full | Architecture boundary kept in lite |
| Architecture | Portability / exportability | Excluded | K17 excluded |
| Architecture | Human oversight + action transparency | Partial | CLI approval + JSONL log; no K15 pause/stop UX |
| Architecture | Multi-agent isolation and cross-agent validation | Excluded | Multi-tenant excluded |
| Architecture | Simplicity / least-agentic pattern | Full | Teaching track emphasizes minimal agentic |

---

## 1. Architecture you can defend in a review

### 1.1 The hard rule

> **Strategies propose. The kernel disposes.**

If it can:
- cause side effects,
- read sensitive/scoped data,
- grant permissions,
- decide allow/deny/approve,
- write audit logs,
- access secrets,

…it belongs in the kernel.

### 1.2 Reference architecture: ports & adapters (hexagonal)

**Kernel-owned (TCB)**
- K1 ABI (typed system model)
- K2 Orchestrator (deterministic FSM)
- K3 Model Boundary (LLM as tool)
- K4 Tool Executor (validation/timeouts/idempotency)
- K5 Policy + Reference Monitor (complete mediation; two-phase)
- K6 Budgets / rate limits / circuit breakers
- K7 Verification layer (can veto)
- K9 Audit ledger + redaction at ingestion
- K10 Persistence + outbox + resume semantics
- K18 Sanitization pipeline (untrusted content discipline)
- plus K11/K12/K13/K14/K15/K16/K17 as you scale

**Replaceable (NOT TCB)**
- planners (ReAct, plan-and-execute, search)
- RAG ranking/chunking
- domain prompts
- tool adapters/connectors
- UI clients (React/CLI/Slack)
- model provider SDKs (wrapped behind K3)

**Design goal:** a strategy can be swapped without changing safety claims.


### 1.3 Upgrade: make Strategy *actually untrusted* (process isolation)

Your current boundary enforcement (packaging + import-linter + “no tool handles”) is **good engineering** — but it is still an *in‑process* trust boundary. In real codebases, “in‑process” boundaries slowly erode under pressure (“just this one helper import…”) and you discover you’ve built a security perimeter out of vibes.

A production‑grade elegance upgrade is to make your most important rule:

> **Strategies propose. The kernel disposes.**

…a **physics constraint** via process isolation.

**Recommended shape**
- Run **kernel_tcb** as the only process allowed to:
  - execute tools / touch secrets,
  - write audit/outbox/state,
  - authorize side effects.
- Run **strategy** in a separate process (or container / sandbox) that can only:
  - read sanitized observations,
  - propose typed intents,
  - receive outcomes / next observations.

Start embedded if you must — but **design the API as if strategy is remote** so you can flip the switch later without rewriting your invariants.

#### Strategy RPC ABI (kernel-owned)

Treat strategy outputs as **untrusted input**: the kernel validates them with strict schemas and rejects anything outside the contract.

```python
# kernel_tcb/strategy_rpc/abi.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

from kernel_tcb.abi.strategy import StrategyContext, StrategyProposal

class StrategyProposeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_id: UUID
    run_id: UUID
    strategy_id: str
    # the entire context is already sanitized/typed (K18/K1)
    ctx: StrategyContext

class StrategyProposeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_id: UUID
    run_id: UUID
    strategy_id: str
    proposal: StrategyProposal
    # non-authoritative debug fields (never used for authorization)
    debug: dict = Field(default_factory=dict)
```

**Transport choices (in order):**
1) **Unix domain socket** + HTTP/JSON (simple, local-only, easy ops).
2) **gRPC** over localhost (great schemas, better performance, nicer streaming).
3) Full service-to-service (mTLS, service discovery) once you need horizontal scaling.

#### Strategy “host” sandbox profile (recommended)

A strategy process should run with a **restricted profile** by default:

- **No network** (unless explicitly required for a non-sensitive purpose).
- **No environment secrets** (empty env; no cloud creds; no DB creds).
- **Read-only filesystem** (or a tiny temp dir).
- **Resource caps** (CPU/mem/wall time) independent of kernel budgets (K6).
- **Crash-only** tolerance (kernel treats strategy failure as a typed error; fail closed).

This is distinct from K8 “execute untrusted code”; here you’re isolating *your own* strategy code because humans are fallible and deadlines are undefeated.

#### 1.3.1 Strategy RPC contract hardening (so “in-proc now” doesn’t rot)

When teams start in-process, they often skip all the “service hygiene” and then discover later that their boundary is a suggestion.

Make these constraints part of the **ABI** from day one:

- **Versioning:** include `abi_version` in request/response (semver). Kernel rejects unknown/unsupported versions.
- **Deadlines:** request carries `deadline_ms` (or absolute `deadline_epoch_ms`). Strategy must treat it as authoritative.
- **Payload caps:** enforce max bytes for observations and proposals; return a typed `payload_too_large` error.
- **Cancellation:** kernel can cancel a proposal in flight; strategy should abort work quickly (best effort).
- **Determinism hooks:** pass `rng_seed` and `now_epoch_ms` to strategy for replayable behavior.
- **Tracing:** propagate `traceparent` + `tracestate` through the RPC boundary.

Minimal ABI additions (illustrative):

```python
class StrategyContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    abi_version: str  # e.g. "1.0.0"
    traceparent: str | None = None

    rng_seed: int
    now_epoch_ms: int
    deadline_epoch_ms: int

    # existing fields...
    trace_id: UUID
    run_id: UUID
    sanitized_observations: list[SanitizedContent]
    budgets: Budgets
```

#### 1.3.2 StrategyHost “least privilege” enforcement (Linux notes)

If you can, make your isolation enforceable by the OS:

- **Drop privileges:** run as a non-root user; `no_new_privs` on Linux.
- **Resource limits:** cgroups for CPU/memory; rlimits for file descriptors, process count, core dumps.
- **Filesystem:** read-only root; small writable temp dir; mount namespaces if containerized.
- **Network:** default deny egress (network namespace with no routes; or firewall rules).
- **Syscalls:** seccomp profile (deny dangerous syscalls; allow only what strategy needs).
- **Crash-only contract:** strategy can die; kernel converts it into a typed error and fails closed.

The elegance goal is: even if someone “accidentally” adds an import or tries something clever, the OS shrugs and says “no.”


#### Migration path: in-proc today, service later

Keep the kernel interface stable by using a port adapter.

```python
# kernel_tcb/abi/runtime.py (unchanged public surface)
from typing import Protocol
from kernel_tcb.abi.strategy import StrategyContext, StrategyProposal

class StrategyPort(Protocol):
    strategy_id: str
    def propose(self, ctx: StrategyContext) -> StrategyProposal: ...
```

- **In-process**: `InProcessStrategyAdapter(Strategy)` implements `StrategyPort`.
- **Out-of-process**: `RpcStrategyClient(...)` implements `StrategyPort` using the ABI above.

**Kernel invariant:** regardless of deployment, a strategy never receives tool handles, secrets, policy decisions, or persistence writers.

### 1.4 Upgrade: make the kernel a reducer + effect interpreter (single side-effect pipeline)

Your playbook already wants deterministic control (K2) and explicit typed boundaries (K1). The cleanest way to **prevent orchestration drift** is to formalize the runtime as:

- **KernelCore** (pure-ish):  
  `step(state, observation) -> (new_state, effects[])`
- **EffectRunner** (I/O):  
  executes effects (model/tool/policy/approval/persist/audit), returning new observations
- **EventSink**:  
  every effect produces trace/audit events (K9) *as a contract*

This turns “don’t do side effects ad‑hoc” into “there is only one pipeline where I/O can exist.”

#### Effect ABI (typed, append-only)

```python
# kernel_tcb/effects/abi.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Literal

from kernel_tcb.model.abi import ModelRequest
from kernel_tcb.tools.ports import ToolMeta

class Effect(BaseModel):
    # Effects are inert data; the runner is the only place where I/O happens.
    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_id: str
    run_id: str

class EmitAudit(Effect):
    kind: Literal["emit_audit"] = "emit_audit"
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)

class PersistCheckpoint(Effect):
    kind: Literal["persist_checkpoint"] = "persist_checkpoint"
    state_snapshot: dict[str, Any]  # canonical kernel state (K1)

class CallStrategy(Effect):
    kind: Literal["call_strategy"] = "call_strategy"
    ctx: dict[str, Any]  # StrategyContext canonical JSON (K1)

class CallModel(Effect):
    kind: Literal["call_model"] = "call_model"
    req: ModelRequest

class ToolPreview(Effect):
    kind: Literal["tool_preview"] = "tool_preview"
    tool_name: str
    args: dict[str, Any]
    meta: ToolMeta

class ToolExecute(Effect):
    kind: Literal["tool_execute"] = "tool_execute"
    tool_name: str
    args: dict[str, Any]
    meta: ToolMeta
    capability_token: str | None = None  # K5 capability grant (see §12.6)

# Optional but recommended external-I/O effects (make wiring complete)
class PolicyEval(Effect):
    kind: Literal["policy_eval"] = "policy_eval"
    bundle_id: str
    bundle_version: str
    tool_name: str
    args: dict[str, Any]
    meta: ToolMeta

class ApprovalRequestEffect(Effect):
    kind: Literal["approval_request"] = "approval_request"
    binding_hash: str
    tool_name: str
    preview_redacted: dict | None
    expires_at_epoch: int
    reason: str

class ApprovalWait(Effect):
    kind: Literal["approval_wait"] = "approval_wait"
    binding_hash: str
    timeout_sec: int

class SecretsIssue(Effect):
    kind: Literal["secrets_issue"] = "secrets_issue"
    tool_name: str
    scopes: list[str]
    ttl_sec: int
    meta: ToolMeta


KernelEffect = (
    EmitAudit
    | PersistCheckpoint
    | CallStrategy
    | CallModel
    | ToolPreview
    | ToolExecute
    | PolicyEval
    | ApprovalRequestEffect
    | ApprovalWait
    | SecretsIssue
)
```

Notice what’s *not* here: no raw SDK clients, no database sessions, no “just call tool()”. Effects are inert data.

#### KernelCore signature (testable, replayable)

```python
# kernel_tcb/core/core.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from kernel_tcb.effects.abi import KernelEffect

@dataclass(frozen=True)
class CoreState:
    fsm_state: str
    step: int
    # plus whatever else your K1 state model contains

class Observation(Protocol):
    # typed observations: model responses, tool results, approval decisions, etc.
    kind: str

class KernelCore(Protocol):
    def step(self, state: CoreState, obs: Observation) -> tuple[CoreState, list[KernelEffect]]: ...
```

A “pure” core is optional; a **pure-ish** core is the goal: it should be deterministic given `(state, obs)`.

#### EffectRunner (the only place with I/O)

```python
# kernel_tcb/effects/runner.py
from __future__ import annotations
from typing import Iterable

from kernel_tcb.effects.abi import KernelEffect, EmitAudit, PersistCheckpoint, CallModel, ToolPreview, ToolExecute
from kernel_tcb.model.boundary import ModelBoundary
from kernel_tcb.tools.executor import ToolExecutor

class EffectRunner:
    def __init__(self, *, model: ModelBoundary, tools: ToolExecutor, audit: "AuditLedger", store: "RunStore"):
        self._model = model
        self._tools = tools
        self._audit = audit
        self._store = store

    def run(self, effects: Iterable[KernelEffect]) -> list[object]:
        observations: list[object] = []
        for eff in effects:
            if isinstance(eff, EmitAudit):
                self._audit.emit(trace_id=eff.trace_id, run_id=eff.run_id, name=eff.name, payload=eff.payload)
                observations.append({"kind": "audit_emitted", "name": eff.name})

            elif isinstance(eff, PersistCheckpoint):
                self._store.save_checkpoint(run_id=eff.run_id, state_snapshot=eff.state_snapshot)
                observations.append({"kind": "checkpoint_saved"})

            elif isinstance(eff, CallModel):
                resp = self._model.complete_text(messages=eff.req.messages, config=eff.req.config)
                observations.append({"kind": "model_response", "resp": resp})

            elif isinstance(eff, ToolPreview):
                r = self._tools.preview(tool_name=eff.tool_name, args=eff.args, meta=eff.meta)
                observations.append({"kind": "tool_preview_result", "tool": eff.tool_name, "result": r})

            elif isinstance(eff, ToolExecute):
                r = self._tools.execute(
                    tool_name=eff.tool_name,
                    args=eff.args,
                    meta=eff.meta,
                    capability_token=eff.capability_token,
                )
                observations.append({"kind": "tool_execute_result", "tool": eff.tool_name, "result": r})

            else:
                raise TypeError(f"unknown effect: {type(eff)}")
        return observations
```

> Production note: the interpreter above is intentionally minimal. In production, do **not**
> call adapters directly from this loop. Instead, build a middleware pipeline (breaker/bulkhead/timeout/retry/metrics)
> around dispatch and ensure **every** external interaction is an Effect (§9.5).


**Structural win:** you can now enforce ordering constraints mechanically, e.g. “no `ToolExecute` effect can be emitted unless a `policy_decision` event exists for the same args hash.”



#### 1.4.1 Make the effects boundary *unbreakable* (lint + runtime guards)

The reducer/effects split only pays off if you prevent “one little shortcut” from creeping in.

**Enforce it in three layers:**

1) **Import-linter contract (static)**
   - `kernel_tcb/core/**` may import:
     - `kernel_tcb/abi/**`
     - `kernel_tcb/effects/abi.py`
     - pure utilities (`stable_hash`, schemas)
   - `kernel_tcb/core/**` must **not** import:
     - tool adapters
     - model providers/SDKs
     - persistence implementations
     - policy bundles

   Example `contracts/importlinter.ini` rule (illustrative):

```ini
[importlinter]
root_package = kernel_tcb

[importlinter:contract:core_is_pure]
name = Core cannot import side-effect modules
type = forbidden
source_modules =
    kernel_tcb.core
forbidden_modules =
    kernel_tcb.tool_adapters
    kernel_tcb.providers
    kernel_tcb.persistence
```

2) **API design guard (type-level)**
   - Make the “impure” functions require an `EffectContext` that is only constructible inside `EffectRunner`.
   - Keep constructors internal (module-private) and expose only validated factories.

3) **Runtime guard (fail closed)**
   - `ToolExecutor` should reject calls missing:
     - `effect_id`
     - `capability_token` (for side-effecting tools)
     - `policy_decision_id` / `binding_hash` where applicable
   - This makes unauthorized paths obvious in logs and impossible to “accidentally” wire up.

**Why this matters:** it’s how you stop architecture drift. Your future self will thank you.
### 1.5 Upgrade: event-sourced run state (optional, very elegant)

You already have the ingredients: audit ledger (K9), persistence/outbox (K10), replay hooks (K11). The coherence upgrade is to make a single statement true:

- **State is a fold of events.**

Implementation sketch:
- Every significant transition/effect emits a **RunEvent** into an append-only per-run stream.
- “Current state” is derived by replaying events through a reducer.
- Add **snapshots** every N events for performance.
- The outbox can be derived from events or maintained as a separate table fed by them.

This makes “resume” and “time travel debugging” boring in the best way.

(Concrete storage patterns are in §13.3.)

### 1.6 Upgrade: capability tokens (authorization as an object)

Instead of relying on “tool name + args + policy check happened somewhere earlier”, have the policy layer mint a **capability grant token** that must be presented to execute.

This is capability-based security:
- execution requires possessing the permit object,
- the permit is logged evidence of authorization,
- distributed executors can verify permits without shared in-memory policy state.

(Concrete token design + code is in §12.6.)

### 1.7 Upgrade: treat context as a typed program, not a string

You already enforce “data ≠ instructions” (K18). The elegance move is to make prompt construction **structural**:

- Strategy never passes raw “context strings”.
- Strategy passes references to `SanitizedContent` items + structured facts.
- Kernel compiles a typed `ContextPlan`, then renders provider messages.

(Concrete `ContextPlan`/renderer patterns are in §7.4.)

---


### 1.8 Operational resilience patterns (circuit breaker, bulkhead, saga)

You already have budgets, retries, outbox/idempotency, and deterministic orchestration. The next production step is to add **operational resilience patterns** that prevent *cascading failure* when external dependencies misbehave.

These patterns belong **outside KernelCore** (which stays pure-ish). They live primarily in the **EffectRunner** and the adapters it calls.

#### Circuit breaker (dependency-level “stop hurting yourself”)

**Purpose:** when a dependency starts failing, stop hammering it and quickly surface a typed failure so the kernel can degrade/abort deterministically.

**Where it lives:** `kernel_tcb/resilience/breaker.py` + used by `EffectRunner` around:
- model provider calls,
- tool adapter calls,
- policy/approval service calls,
- persistence/outbox writes (if remote).

**Design rules**
- Breakers are keyed by a **dependency key** (`model:<provider>`, `tool:<tool_name>`, `policy:<bundle_id>`, etc.).
- Breaker state transitions emit audit/trace events (K9) and metrics.
- Fail **closed** for safety: a breaker-open result is treated as a hard stop or safe-mode transition, not “try random alternatives.”

#### Bulkhead (isolate capacity so one fire doesn’t burn the building)

**Purpose:** prevent one slow/flaky dependency from consuming all concurrency and starving unrelated work (including safe shutdown/resume).

**Where it lives:** `kernel_tcb/resilience/bulkhead.py` + used by `EffectRunner` and worker pools.

**Common bulkheads**
- Per-tenant run concurrency (`tenant_id` → semaphore/limiter)
- Per-tool concurrency (`tool:<name>` → limiter)
- Separate pools for **model** vs **tools** vs **persistence** (so a stuck tool can’t block audits/checkpoints)

**Design rules**
- Bulkheads should be **bounded** (max queue / fail-fast); do not build infinite queues.
- Overflow must produce a typed “overloaded” observation to KernelCore (deterministic handling).

#### Saga (multi-step side effects with compensations)

**Purpose:** when a user-visible action spans multiple external side effects, you need a pattern for **partial failure** that is safer than “best effort + shrug”.

**Where it lives:** KernelCore defines saga state machine + emits tool effects; Outbox provides idempotent step commits; the saga runner is effectively “just more deterministic orchestration.”

**Design rules**
- Model “transaction” as a series of **steps** with optional **compensating actions**.
- Every step (and compensation) must be idempotent and outbox-gated.
- Persist saga progress as events (or state + checkpoints) so crash/resume continues deterministically.
- Compensation is not magic: if compensations fail, escalate to manual remediation (ticket, alert, human approval).

---

### 1.9 Extensibility patterns (grow capabilities without widening the TCB)

Extensibility is where agent kernels usually die: teams add “just one more hook” until the trust boundary is mush.

Use these patterns to scale features while keeping the kernel small:

#### Ports & adapters (already your baseline)

KernelCore and the reference monitor remain stable. Everything else is an adapter behind a port.

#### Plugin registry + manifests (safe discovery)

- Tools, verifiers, and policy bundles are discovered through **registries** (not ad-hoc imports).
- Every plugin has a manifest: version, capabilities, schemas, and operational limits.

#### Versioned contracts (evolution without flag days)

- ABI is versioned (`abi_version`) and rejects incompatible clients.
- Effect types and event schemas are **append-only**; include `schema_version` and support forward-compatible decoding.
- Provide adapters for older plugin versions at the boundary (anti-corruption layer).

#### Middleware pipeline for cross-cutting concerns

Cross-cutting concerns (resilience, metrics, redaction, retries) are implemented as **EffectRunner middleware**, not scattered across orchestration code.

#### Feature flags + strangler rollouts

- Roll out new tools/policies/strategies behind feature flags.
- Prefer strangler migrations (route a subset of traffic to the new implementation; compare traces).

#### Contract tests for extensions

Every extension must ship with contract tests:
- tool schema validation + canonicalization,
- idempotency key behavior,
- capability token enforcement,
- determinism in record/replay mode.


## 2. Repo layout and guardrails

### 2.1 Monorepo layout (recommended)

```
repo/
  pyproject.toml
  README.md

  packages/
    kernel_tcb/                  # ✅ THE TCB (small, dependency-light)
    strategies/                  # ❌ swap freely
    tool_adapters/               # ❌ integrations/connectors
    apps/                        # ❌ API server / workers / CLI / strategy host

  policies/                      # versioned policy bundles (+ tests)
  prompts/                       # prompt bundles (hashed/versioned)
  evals/                         # eval suites + suite cards (K12/K12a)
  ops/                           # runbooks, dashboards, IaC
  contracts/                     # import boundaries (import-linter)
```

### 2.2 Boundary enforcement: do all three

1) **Packaging boundary:** `kernel_tcb` is a separate package.  
2) **Import-lint contracts:** prevent dependency erosion.  
3) **Runtime capability design:** strategies never receive tool handles.  
4) **Process boundary (recommended):** run strategy out-of-process (or sandboxed) behind a typed RPC; the kernel remains the only process that can execute tools, access secrets, or write audit/outbox/state.

Example `contracts/importlinter.contracts.ini`:

```ini
[importlinter]
root_package = repo

[contract:kernel_isolated]
name = Kernel cannot import strategies or tool adapters
type = forbidden
source_modules =
    packages.kernel_tcb.src.kernel_tcb
forbidden_modules =
    packages.strategies.src.strategies
    packages.tool_adapters.src.tool_adapters
```

---

## 3. Engineering baseline: “production by default”

### 3.1 Toolchain (recommended)

- Python **3.12**
- `ruff` (format + lint)
- `mypy` (static typing)
- `pytest` (tests)
- `import-linter` (architecture contracts)
- `pydantic` v2 (schemas + validation)
- `jsonschema` (validating tool JSON schemas)
- `structlog` or stdlib logging (structured logs)
- `opentelemetry-sdk` (recommended once you have real users)

### 3.2 Minimal `pyproject.toml` quality gates (snippets)

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E","F","I","B","UP","RUF"]
ignore = ["E501"]  # handled by formatter

[tool.mypy]
python_version = "3.12"
strict = true
warn_unused_ignores = true

[tool.pytest.ini_options]
addopts = "-q"
testpaths = ["packages/kernel_tcb/tests"]
```


### 3.3 Architectural decisions to lock *before* you write “real code”

These are the places teams most often “stay vague” early…and then pay for it later by refactoring the kernel under load.

Lock these down early and treat them as **API-level commitments**.

#### 3.3.1 Strategy execution topology (even if you start in-proc)

**Default recommendation:** design Strategy as **out-of-process** from day one, even if your first deployment runs it in-process.

Decide (and document in `ops/`):
- **Transport:** Unix domain socket + HTTP/JSON (default) or gRPC (preferred once stable).
- **Timeouts:** `propose_timeout_ms` and a hard wall-clock deadline enforced by the kernel host.
- **Payload limits:** max bytes for `observations` and `proposal` (fail closed on overflow).
- **ABI versioning:** a required `abi_version` field in request/response (semver); kernel rejects mismatches.
- **Cancellation:** kernel-issued cancellation token / deadline; strategy must treat it as authoritative.
- **Determinism hooks (recommended):** kernel provides `rng_seed` and `now_epoch_ms` in the request so strategies can be deterministic under replay.

Architectural hardening that solves half your future problems:
- **No network by default** for strategy processes (deny egress; allowlist only if explicitly justified).
- **No secrets in env** (empty env; no cloud credentials; no DB creds; no API keys).
- **CPU/mem/time limits** independent of kernel budgets (cgroups/rlimits).

#### 3.3.2 Effects-only I/O (the “single lane” rule)

**Default recommendation:** *all* model calls + tool calls + persistence + approvals are **effects** produced by `KernelCore` and executed by `EffectRunner`.

Decide (and enforce via tooling):
- Which modules are “pure” (core) vs “impure” (runner/adapters).
- The **exact effect types** you support (preview vs commit; policy eval; approval wait; tool exec; persist; emit audit).
- Your policy on **parallelism**: simplest is “one effect at a time per run_id” (deterministic); scale later.

Architectural hardening:
- Add an **import boundary contract**: core cannot import tool adapters/providers.
- Add a **runtime guard**: tool execution requires an `EffectContext` created only by the runner.

#### 3.3.3 Capability token signing & key management

**Default recommendation:** capability tokens are required for side-effecting tools; tokens are short-lived and tied to canonical args hash + phase + principal/tenant/run.

Decide now:
- **Crypto:** HMAC-SHA256 (internal systems) vs asymmetric (multi-service, zero-trust).
- **Key storage:** KMS/HSM (preferred) vs environment-injected secret (acceptable early).
- **Rotation:** key ring with `kid` (key id) embedded in tokens; verify old keys for a grace window.
- **Clock skew:** allowed skew (e.g., ±30s) and how you handle monotonic time.

Architectural hardening:
- Make `ToolExecutor.execute(...)` **require** a verified token (fail closed).
- Emit `capability_issued` + `capability_verified` events into audit.

#### 3.3.4 Event log mode (state store vs event sourcing)

Pick one early; it changes how you debug and how you resume.

- **Option A (simpler):** persisted state + append-only audit (K9) + outbox (K10).
- **Option B (elegant):** event-sourced run state (fold events → state) + snapshots (see §13.3).

If you choose Option B, decide now:
- **Storage backend:** Postgres (recommended), SQLite (dev), or log systems (Kafka) once you need scale.
- **Event evolution rules:** append-only fields; explicit `schema_version`; never mutate old events.
- **Retention + privacy:** whether events can contain any user text (ideally: only redacted/sanitized).


#### 3.3.5 Persistence abstraction boundaries (repositories + Unit of Work)

This is **recommended for scale** (and for sanity). It turns “we might move from SQLite → Postgres later” into a *swap of adapters* instead of a repo-wide refactor.

**Rule:** one kernel step should be able to write **audit events + state snapshot + outbox rows** in a single atomic boundary.

Adopt:

- **Repository protocols**: `RunRepository`, `OutboxRepository`, `AuditRepository` (and `RunEventRepository` if you event-source).
- A **Unit of Work** (UoW) that binds those repos to a single transaction.
- Kernel code depends only on these ports; SQLite/Postgres become implementations in `packages/kernel_tcb/persistence/*`.

```python
# kernel_tcb/persistence/ports.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Sequence, Optional
from uuid import UUID

@dataclass(frozen=True)
class RunSnapshot:
    run_id: UUID
    seq: int
    state_json: str
    state_hash: str

class RunRepository(Protocol):
    def load_snapshot(self, *, run_id: UUID) -> Optional[RunSnapshot]: ...
    def save_snapshot(self, snap: RunSnapshot) -> None: ...

class OutboxRepository(Protocol):
    def begin(self, rec: "OutboxRecord") -> bool: ...
    def mark_delivered(self, *, idempotency_key: str, result_json: str) -> None: ...
    def mark_failed_retryable(self, *, idempotency_key: str, error_code: str, error_json: str, next_attempt_at: float) -> None: ...
    def dead_letter(self, *, idempotency_key: str, reason: str, error_code: str, error_json: str) -> None: ...

class AuditRepository(Protocol):
    def append(self, event: "AuditEvent") -> None: ...
    def query(self, *, run_id: UUID, after_seq: int = 0, limit: int = 500) -> list["AuditEvent"]: ...
    def get_head(self, *, run_id: UUID) -> tuple[int, str]: ...  # (last_seq, last_chain_hash)

class RunEventRepository(Protocol):
    def append(self, *, run_id: UUID, event_type: str, payload: dict) -> "RunEvent": ...
    def tail(self, *, run_id: UUID, after_seq: int) -> list["RunEvent"]: ...

class UnitOfWork(Protocol):
    runs: RunRepository
    outbox: OutboxRepository
    audit: AuditRepository
    events: Optional[RunEventRepository]  # None if not event-sourcing

    def commit(self) -> None: ...
    def rollback(self) -> None: ...

    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(self, exc_type, exc, tb) -> None: ...
```

**Why a UoW matters:** without it, you will eventually produce “audit says effect was committed, but outbox row didn’t exist” (or the inverse) during partial failures.

**Minimum acceptance tests:**
- A kernel step that writes audit + outbox + snapshot fails mid-way → after restart, either *all* three are present or *none* are (atomicity).
- Repositories can be swapped (SQLite adapter → Postgres adapter) while KernelCore and EffectRunner tests remain unchanged.

---

### 3.4 Production hardening checklist (the “boring but saves you” section)

#### Observability (required)
- **Structured logs** with `trace_id`, `run_id`, `effect_id`, `event_seq`, `tool_name`.
- **Traces:** propagate W3C `traceparent` across strategy RPC, policy service, tool adapters.
- **Metrics (minimum):**
  - runs started/succeeded/failed
  - policy allow/deny/needs_approval counts
  - tool executions by tool_name + outcome
  - outbox pending + retries + dead letters
  - audit verify failures
  - signed run summaries generated + verification failures
  - replay-mode “blocked external call” counter (should be zero in production runs, non-zero only in tests)

#### Resilience defaults (required)

- **Timeouts everywhere** (model/tool/policy/strategy RPC/persistence).
- **Retry policy** with strict bounds + jitter; never retry non-idempotent operations without outbox gating.
- **Backpressure:** cap concurrent runs per tenant; cap effect queue depth; fail fast with typed overload errors.
- **Circuit breakers** per dependency key (model/provider/tool/policy/persistence) with open/half-open/closed states.
- **Bulkheads** (capacity isolation): separate concurrency limits for model vs tools vs persistence, plus per-tool/per-tenant limiters.
- **Load shedding / graceful degradation:** when bulkheads trip or breakers open, return typed observations and enter safe mode (K15) rather than “try harder”.
- **Saga discipline for multi-step writes:** any action that spans multiple side effects must either (a) be designed as a saga with compensations, or (b) be explicitly classified as “non-atomic; manual remediation required” and alerted.


#### Data governance (required)
- Redaction happens **before** any write (audit/state/events).
- Encryption at rest for persistence stores.
- Retention policy for run logs/events + deletion workflow (per tenant/run_id).

#### Release gating (required)
- A must-pass “proof suite” (see §21) that demonstrates:
  - deterministic replay,
  - token-gated tool execution,
  - idempotent resume (no duplicate side effects),
  - prompt injection resilience (data never becomes instructions).

---

## 4. Invariant-first build order (do this, in this order)

For every kernel subsystem you implement:

1) Define the **typed contract** (K1).  
2) Implement the **enforcement code** (fail closed).  
3) Add **invariant tests** (unit + integration).  
4) Emit trace events + metrics (K9).  
5) Add **at least one eval case** that would have caught a realistic failure.

If any step is missing, treat the subsystem as “not implemented.”

### 4.1 From empty repo → Level 2 (read-only kernel)

#### Step 0 — Lock the two “physics constraints” early (recommended)

Before you implement any sophisticated capability, lock in the two design choices that prevent future safety drift:

1) **Strategy is untrusted by construction** (a port you can run out-of-process).  
2) **Kernel I/O is centralized** (reducer + effect interpreter, single side-effect pipeline).

Deliverables:
- `StrategyPort` protocol (kernel ABI) + `strategy_rpc` request/response schemas (even if unused initially).
- `effects` ABI + `EffectRunner` skeleton; make orchestrator depend on effects, not on concrete SDKs.
- A “no tool handles in StrategyContext” check enforced by typing + runtime validation.

Required tests:
- `test_strategy_proposal_schema_rejects_unknown_fields`
- `test_kernel_core_has_no_ports_injected` (core cannot perform I/O)
- `test_effect_runner_is_only_place_tools_are_called` (can be done with spies/mocks)

#### Step 1 — ABI + hashing (K1)
Deliverables:
- `ABIModel` base with canonical JSON + stable hash.
- Error taxonomy.
- Typed `TraceContext`, `RunManifest`, `ToolIntent`, `ToolResult` (minimum set).

Required tests:
- `test_canonical_json_stable_ordering`
- `test_stable_hash_domain_separation`
- `test_unknown_fields_rejected`

#### Step 2 — Audit ledger (K9)
Deliverables:
- append-only event sink (JSONL is fine initially),
- **redaction at ingestion**,
- tamper-evident chaining (hash chain).

Required tests:
- `test_redaction_before_write`
- `test_hash_chain_verifies`
- `test_agent_cannot_write_ledger_via_tools` (architecture boundary test)

#### Step 3 — Deterministic orchestrator FSM (K2)
Deliverables:
- explicit FSM states + allowed transitions,
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
- typed tool error taxonomy.

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

Required suites (minimum):
- 10 golden regression cases,
- 10 prompt injection cases (direct + indirect),
- 5 tool misuse cases (even if only read tools exist at Level 2).

Exit criteria (Level 2 readiness):
- you can replay a failing eval case deterministically (K11 becomes strongly recommended here).

---

### 4.2 From Level 2 → Level 3 action agent (writes)

Before the first real write, add these:

#### Step 9 — Policy + reference monitor (K5)
Deliverables:
- default deny policy bundle,
- allowlists + deterministic constraints,
- two-phase execution (propose → preview → approve → commit),
- approval binding hash (tool + canonical args + preview hash),
- **capability grant tokens** (policy issues a permit object; tool execution requires it),
- policy evaluated at propose-time **and** commit-time (TOCTOU-safe).

Required tests:
- `test_no_write_without_gate`
- `test_approval_binding_hash_required`
- `test_toctou_hash_mismatch_denied`
- `test_commit_requires_capability_token`

#### Step 10 — Outbox + resume safety (K10)
Deliverables:
- durable outbox intent records,
- idempotency semantics documented per tool,
- (optional) append-only **run event stream** + snapshots if adopting event-sourced state (§13.3).

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

## 5. Kernel public API and ports (method-agnosticism made enforceable)

### 5.1 KernelRuntime interface

```python
# kernel_tcb/abi/runtime.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Literal, Protocol
from uuid import UUID

from kernel_tcb.sanitize.envelope import SanitizedContent

class KernelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kernel_api_version: str
    trace_id: UUID
    run_id: UUID
    principal: str
    tenant_id: str | None = None

    input: SanitizedContent
    mode: Literal["live", "replay"] = "live"
    bundle_id: str | None = None  # K16-min, optional in early prototypes

class KernelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_id: UUID
    run_id: UUID
    status: Literal["success", "failed", "cancelled", "timeout"]
    final_output: str | None
    outcome: dict
    bundle_id: str | None
    metrics: dict

class Strategy(Protocol):
    strategy_id: str
    def propose(self, ctx: "StrategyContext") -> "StrategyProposal": ...

class KernelRuntime(Protocol):
    def run(self, req: KernelRequest, *, strategy: StrategyPort) -> KernelResponse: ...
    def resume(self, *, run_id: UUID) -> KernelResponse: ...
    def cancel(self, *, run_id: UUID, reason: str) -> None: ...
```

### 5.2 Strategy port (typed proposals, not side effects)

```python
# kernel_tcb/abi/strategy.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from uuid import UUID

from kernel_tcb.tools.manifest import ToolManifest
from kernel_tcb.sanitize.envelope import SanitizedContent

class RunInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_id: UUID
    run_id: UUID
    principal: str
    tenant_id: str | None
    step: int
    budgets_remaining: dict
    bundle_id: str | None

class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["user_input", "tool_result", "model_output", "memory_read", "system_event"]
    content: SanitizedContent
    meta: dict = Field(default_factory=dict)

class StrategyContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run: RunInfo
    tool_manifest: ToolManifest
    observations: list[Observation]

class ContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # Untrusted text must only arrive as SanitizedContent; the kernel renderer will
    # place it into a data channel (never system/developer).
    data: list[SanitizedContent] = Field(default_factory=list)

    # Structured facts (from extraction, memory, or tools). These are still untrusted
    # unless a verifier asserts otherwise, but they are not treated as instructions.
    facts: dict = Field(default_factory=dict)

class ModelCallIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["model_call"] = "model_call"
    prompt_ref: str
    context: ContextRequest
    output_schema_ref: str | None = None

class ToolCallIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["tool_call"] = "tool_call"
    tool_name: str
    arguments: dict
    requires_commit: bool = False

class MemoryWriteIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["memory_write"] = "memory_write"
    record: dict

KernelIntent = ModelCallIntent | ToolCallIntent | MemoryWriteIntent

class StrategyProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    intents: list[KernelIntent] = Field(default_factory=list)
    final_answer: str | None = None
    stop: bool = False
    notes: dict = Field(default_factory=dict)
```

**Deployment note:** `StrategyPort` is deliberately small so you can run strategies **in-process** during early development and later swap to an **out-of-process** `RpcStrategyClient` (Unix socket / gRPC) without changing kernel invariants. The kernel still treats proposals as untrusted input and validates them strictly before acting.



---


### 5.3 Extension points (tools, verifiers, policies, middleware) — without breaking the boundary

You want teams to add capabilities quickly **without** modifying the kernel’s trusted core.

This section defines the recommended extension points and the patterns that keep them safe.

#### A. Tool packs (new tools without kernel edits)

Pattern: **manifest + adapter + registry**

- Each tool ships:
  - a `ToolManifest` (schemas, risk tier, default limits),
  - an adapter implementing `ToolPort` for that tool,
  - contract tests (see §21.2).
- Kernel loads tools via a **registry** (config or package entry points), not via direct imports in KernelCore.

```python
# kernel_tcb/tools/registry.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class ToolRegistration:
    name: str
    manifest: "ToolManifest"
    adapter_factory: Callable[[], "ToolPort"]  # adapter created in runner layer

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolRegistration] = {}

    def register(self, reg: ToolRegistration) -> None:
        if reg.name in self._tools:
            raise ValueError(f"duplicate tool: {reg.name}")
        self._tools[reg.name] = reg

    def get(self, name: str) -> ToolRegistration:
        return self._tools[name]
```

**Rule:** KernelCore only ever sees the *name + canonical args*; it never holds adapter objects.

#### B. Verifier packs (new safety checks without orchestration drift)

Pattern: **chain-of-responsibility** (ordered verifiers)

- Verifiers are pure-ish functions or small services.
- They run in a deterministic order and may veto execution.

#### C. Policy bundles (data-only, versioned)

Pattern: **data-driven policy** with strict schema/versioning

- Policy is configured by bundles (append-only schema; signed if needed).
- Policy changes are versioned and can be rolled back independently.

#### D. EffectRunner middleware (cross-cutting additions)

Pattern: **middleware pipeline** for effect execution

Use middleware for:
- circuit breakers/bulkheads/retries,
- metrics/tracing,
- redaction enforcement,
- rate limiting / quotas.

```python
# kernel_tcb/effects/middleware.py
from __future__ import annotations
from typing import Protocol, Any

class EffectMiddleware(Protocol):
    def before(self, effect: Any) -> None: ...
    def after(self, effect: Any, outcome: Any) -> None: ...
    def on_error(self, effect: Any, err: Exception) -> None: ...
```

**Rule:** Middleware runs in the runner layer, not in KernelCore.

#### E. Safe evolution rules

- Additive changes only for effect/event schemas (append-only fields).
- ABI version bumps when behavior changes in a way a strategy client must know about.
- New tools/verifiers/policies must not require KernelCore edits unless they change invariants.

---

## 6. K1 — ABI and stable hashing

```python
# kernel_tcb/abi/base.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
import hashlib
import json
from typing import Any

class ABIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)

    def canonical_json(self) -> str:
        return json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def stable_hash(self, *, domain: str, version: str = "v1") -> str:
        msg = f"{domain}:{version}|{self.canonical_json()}".encode("utf-8")
        return "sha256:" + hashlib.sha256(msg).hexdigest()
```

---

## 7. K18 — Sanitization and channel separation (data ≠ instructions)

### 7.1 Sanitized content envelope

```python
# kernel_tcb/sanitize/envelope.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class SanitizedContent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provenance: dict
    classification: Literal["L0","L1","L2","L3"]
    suspicion_flags: list[str] = Field(default_factory=list)

    quoted_data: str
    extracted_facts: dict | None = None
    unprocessed: bool = False
```

### 7.2 A conservative sanitizer (rule-based + pluggable)

```python
# kernel_tcb/sanitize/sanitizer.py
from __future__ import annotations
import re
from kernel_tcb.sanitize.envelope import SanitizedContent

_RE_INSTRUCTION = re.compile(r"(?i)\b(ignore|override|system prompt|developer message|tool)\b")
_RE_SECRET = re.compile(r"(?i)\b(api[_-]?key|token|password|secret)\b")

def sanitize_text(*, text: str, provenance: dict) -> SanitizedContent:
    suspicion: list[str] = []
    if _RE_INSTRUCTION.search(text):
        suspicion.append("instruction_like_text")
    if _RE_SECRET.search(text):
        suspicion.append("secret_like_text")

    classification = "L2"
    if "secret_like_text" in suspicion:
        classification = "L3"

    return SanitizedContent(
        provenance=provenance,
        classification=classification,
        suspicion_flags=suspicion,
        quoted_data=text.replace("\u0000", ""),
    )
```

### 7.3 Prompt renderer guardrail: enforce channels

```python
# kernel_tcb/model/prompting.py
from __future__ import annotations

import json
from pydantic import BaseModel, ConfigDict
from typing import Literal

from kernel_tcb.sanitize.envelope import SanitizedContent

class LLMMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    role: Literal["system","developer","user","assistant","tool"]
    content: str

def _render_untrusted(item: SanitizedContent) -> str:
    meta = {
        "classification": item.classification,
        "suspicion_flags": item.suspicion_flags,
        "provenance": item.provenance,
        "unprocessed": item.unprocessed,
    }
    return (
        "[UNTRUSTED_DATA]\n"
        + json.dumps(meta, ensure_ascii=False, sort_keys=True)
        + "\n---\n"
        + item.quoted_data
        + "\n[/UNTRUSTED_DATA]"
    )

def build_messages(*, system: str, developer: str, data_items: list[SanitizedContent], user: str) -> list[LLMMessage]:
    msgs: list[LLMMessage] = [
        LLMMessage(role="system", content=system),       # kernel-owned instructions
        LLMMessage(role="developer", content=developer), # kernel-owned instructions
    ]
    for item in data_items:
        msgs.append(LLMMessage(role="user", content=_render_untrusted(item)))
    msgs.append(LLMMessage(role="user", content=user))
    return msgs
```


### 7.4 Recommended: ContextPlan + ContextCompiler (typed prompt program)

The “data ≠ instructions” rule becomes much harder to violate if prompt construction is not a pile of strings.

**Pattern**
- Strategy produces *typed* `ContextRequest` (see §5.2): `{data: [SanitizedContent], facts: {...}}`.
- Kernel compiles a **typed** `ContextPlan` (append-only items).
- Renderer turns the plan into provider messages and mechanically enforces:
  - only kernel-owned instructions may appear in `system`/`developer`,
  - untrusted text is only rendered via `SanitizedContent.quoted_data` inside a data channel.

```python
# kernel_tcb/context/plan.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Literal

from kernel_tcb.abi.base import ABIModel
from kernel_tcb.model.prompting import LLMMessage, _render_untrusted
from kernel_tcb.sanitize.envelope import SanitizedContent

class InstructionBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["instruction"] = "instruction"
    role: Literal["system", "developer"]
    text: str

class UntrustedDataBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["untrusted_data"] = "untrusted_data"
    item: SanitizedContent

class FactsBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["facts"] = "facts"
    facts: dict[str, Any] = Field(default_factory=dict)

class UserQueryBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["user_query"] = "user_query"
    text: str

ContextItem = InstructionBlock | UntrustedDataBlock | FactsBlock | UserQueryBlock

class ContextPlan(ABIModel):
    schema_version: str = "v1"
    items: list[ContextItem]
```

```python
# kernel_tcb/context/compiler.py
from __future__ import annotations
from kernel_tcb.abi.strategy import ContextRequest
from kernel_tcb.context.plan import ContextPlan, InstructionBlock, UntrustedDataBlock, FactsBlock, UserQueryBlock

def compile_context(*, system: str, developer: str, req: ContextRequest, user_query: str) -> ContextPlan:
    items = [
        InstructionBlock(role="system", text=system),
        InstructionBlock(role="developer", text=developer),
        *[UntrustedDataBlock(item=i) for i in req.data],
        FactsBlock(facts=req.facts),
        UserQueryBlock(text=user_query),
    ]
    return ContextPlan(items=items)
```

```python
# kernel_tcb/context/renderer.py
from __future__ import annotations

import json
from kernel_tcb.context.plan import ContextPlan, InstructionBlock, UntrustedDataBlock, FactsBlock, UserQueryBlock
from kernel_tcb.model.prompting import LLMMessage, _render_untrusted

def render(plan: ContextPlan) -> list[LLMMessage]:
    msgs: list[LLMMessage] = []

    for it in plan.items:
        if isinstance(it, InstructionBlock):
            msgs.append(LLMMessage(role=it.role, content=it.text))

        elif isinstance(it, UntrustedDataBlock):
            msgs.append(LLMMessage(role="user", content=_render_untrusted(it.item)))

        elif isinstance(it, FactsBlock) and it.facts:
            msgs.append(LLMMessage(role="user", content="[STRUCTURED_FACTS]\n" + json.dumps(it.facts, ensure_ascii=False, sort_keys=True) + "\n[/STRUCTURED_FACTS]"))

        elif isinstance(it, UserQueryBlock):
            msgs.append(LLMMessage(role="user", content=it.text))

        else:
            raise TypeError(f"unknown context item: {type(it)}")

    # Mechanical guardrail: if anything slipped, fail closed
    for m in msgs:
        if m.role in ("system", "developer") and "[UNTRUSTED_DATA]" in m.content:
            raise ValueError("untrusted_data_in_instruction_channel")

    return msgs
```

**Practical benefits**
- You can audit/inspect the `ContextPlan` without dumping full prompts.
- The plan is hashable (`ContextPlan.stable_hash(...)`), which is great for replay and bundle manifests.
- Prompt injection resilience stops being “best effort” and becomes “the compiler won’t let you.”


**Kernel invariant:** sanitizer outputs never enter `system`/`developer`.

---

## 8. K9 — Audit ledger (redaction at ingestion + hash chain)

### 8.1 Audit event ABI

```python
# kernel_tcb/audit/events.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Any
from uuid import UUID

class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ts_epoch: float
    trace_id: UUID
    run_id: UUID

    name: str
    payload: dict[str, Any]

    prev_chain_hash: str
    chain_hash: str
```

### 8.2 Redactor and sink ports

```python
# kernel_tcb/audit/ports.py
from __future__ import annotations
from typing import Any, Protocol
from kernel_tcb.audit.events import AuditEvent

class Redactor(Protocol):
    def redact(self, payload: dict[str, Any]) -> dict[str, Any]: ...

class AppendOnlySink(Protocol):
    def append(self, event: AuditEvent) -> None: ...
```


#### 8.2.1 Production sink composition (fan-out, routing, async backpressure)

A single `AppendOnlySink` is enough for a reference implementation, but production systems almost always need **fan-out**:

- **Primary durable sink (required):** the audit write you *must* succeed with before committing side effects (DB table / WAL-backed log).
- **Secondary sinks (optional):** SIEM, file shipping, Kafka, remote audit service. These can lag or fail without breaking the kernel invariants.
- **Routing:** some events go to all sinks; some go only to compliance storage.

**Invariant:** never make the *primary* durable append “best effort.”  
If you can execute a side-effecting tool, you must be able to append the corresponding audit events first.

Reference sink patterns:

```python
# kernel_tcb/audit/sinks.py
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable

from kernel_tcb.audit.events import AuditEvent
from kernel_tcb.audit.ports import AppendOnlySink

class CompositeSink(AppendOnlySink):
    """Fan-out to multiple sinks in a deterministic order.

    Put the durable sink first. Secondary sinks may be best-effort.
    """
    def __init__(self, sinks: list[AppendOnlySink], *, best_effort_indices: set[int] | None = None):
        self._sinks = sinks
        self._best_effort = best_effort_indices or set()

    def append(self, event: AuditEvent) -> None:
        for i, s in enumerate(self._sinks):
            if i in self._best_effort:
                try:
                    s.append(event)
                except Exception:
                    # Best-effort sinks must never block core durability.
                    continue
            else:
                # Durable sink(s): fail closed.
                s.append(event)

class RoutingSink(AppendOnlySink):
    """Route events to different sinks by predicate (e.g., compliance vs ops)."""
    def __init__(self, routes: list[tuple[Callable[[AuditEvent], bool], AppendOnlySink]], default: AppendOnlySink | None = None):
        self._routes = routes
        self._default = default

    def append(self, event: AuditEvent) -> None:
        routed = False
        for pred, sink in self._routes:
            if pred(event):
                sink.append(event)
                routed = True
        if not routed and self._default is not None:
            self._default.append(event)

@dataclass(frozen=True)
class AsyncSinkConfig:
    queue_max: int = 50_000
    warn_drop_threshold: int = 45_000
    # If "drop" is True, overflow drops events (only safe for secondary sinks).
    drop_on_overflow: bool = True

class AsyncFanoutSink(AppendOnlySink):
    """Async wrapper for secondary sinks.

    Use ONLY for non-primary sinks; otherwise you violate "audit before side effects".
    """
    def __init__(self, downstream: AppendOnlySink, *, cfg: AsyncSinkConfig = AsyncSinkConfig()):
        self._downstream = downstream
        self._cfg = cfg
        self._q: queue.Queue[AuditEvent] = queue.Queue(maxsize=cfg.queue_max)
        self._t = threading.Thread(target=self._worker, name="audit-fanout", daemon=True)
        self._t.start()

    def append(self, event: AuditEvent) -> None:
        try:
            self._q.put_nowait(event)
        except queue.Full:
            if self._cfg.drop_on_overflow:
                # Drop is acceptable ONLY for secondary sinks; emit metrics/alerts.
                return
            self._q.put(event)  # backpressure

    def _worker(self) -> None:
        while True:
            ev = self._q.get()
            try:
                self._downstream.append(ev)
            except Exception:
                # Fanout failures should be visible: log + metrics + optional DLQ.
                pass
            finally:
                self._q.task_done()
                time.sleep(0)  # yield
```

Operational requirements (minimum):
- Metrics: queue depth, drop count (if enabled), fanout latency.
- Alerting: sustained fanout failure, queue saturation.
- Optional: DLQ for fanout events if remote sink outages are common.


### 8.3 Ledger implementation

```python
# kernel_tcb/audit/ledger.py
from __future__ import annotations

import hmac
import hashlib
import json
import time
from uuid import UUID
from typing import Any

from kernel_tcb.audit.events import AuditEvent
from kernel_tcb.audit.ports import AppendOnlySink, Redactor

def _stable_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

class AuditLedger:
    def __init__(self, *, run_secret: bytes, sink: AppendOnlySink, redactor: Redactor):
        self._k = run_secret
        self._sink = sink
        self._redactor = redactor
        self._prev = "genesis"

    def emit(self, *, trace_id: UUID, run_id: UUID, name: str, payload: dict[str, Any]) -> None:
        safe = self._redactor.redact(payload)
        ts = time.time()
        msg = _stable_json({"ts": ts, "trace_id": str(trace_id), "run_id": str(run_id), "name": name, "payload": safe})
        event_hash = hashlib.sha256(msg).digest()
        chain_hash = hmac.new(self._k, event_hash + self._prev.encode("utf-8"), hashlib.sha256).hexdigest()

        self._sink.append(AuditEvent(
            ts_epoch=ts,
            trace_id=trace_id,
            run_id=run_id,
            name=name,
            payload=safe,
            prev_chain_hash=self._prev,
            chain_hash=chain_hash,
        ))
        self._prev = chain_hash
```



### 8.4 Audit read path (query + pagination + authorization)

Writing an audit log is table stakes. In production you also need a **read API** that supports:
- incident response (“what happened after seq N?”),
- compliance export,
- replay/debug (“show me policy decisions + tool commits in order”).

Add a storage-backed read port (the sink can still be append-only, but the *store* must support query).

```python
# kernel_tcb/audit/read.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

@dataclass(frozen=True)
class AuditHead:
    last_seq: int
    last_chain_hash: str

class AuditReader(Protocol):
    def query(self, *, run_id: UUID, after_seq: int = 0, limit: int = 500) -> list["AuditEvent"]: ...
    def get_head(self, *, run_id: UUID) -> AuditHead: ...
```

**Authorization:** Audit reads are a high-value data path.
- Always scope by `tenant_id` (and by principal role).
- Consider separating “operator audit read” from “user run view” endpoints.

### 8.5 Verify chain (tamper detection for a run)

Expose a verifier that recomputes the per-run chain and tells you **where it breaks**.

```python
# kernel_tcb/audit/verify.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

@dataclass(frozen=True)
class ChainVerification:
    ok: bool
    first_bad_seq: Optional[int] = None
    expected_prev: Optional[str] = None
    observed_prev: Optional[str] = None

class AuditVerifier:
    def __init__(self, *, reader: "AuditReader", run_secret_loader: "RunSecretLoader"):
        self._reader = reader
        self._secrets = run_secret_loader

    def verify_chain(self, *, run_id: UUID) -> ChainVerification:
        # Pseudocode: recompute chain hashes exactly as the ledger did (canonical JSON + hash/HMAC).
        # Requires access to the per-run secret/key material used for chaining.
        ...
```

**Implementation note:** if you don’t want verifiers to access per-run secrets, use a *public* hash chain (SHA-256 over canonical JSON + prev hash) and sign the run head instead. Either way: verification must be deterministic.

### 8.6 Global tamper evidence (signed run summaries + global chaining)

Per-run chains detect tampering *within* a run stream. They do not detect:
- entire runs being deleted,
- run streams being replaced wholesale.

Add a **signed run summary** at completion, then chain summaries globally.

**Minimal signed run summary:**
- `run_id`, `tenant_id`, `principal_id`
- start/end timestamps
- final status + failure reason code (if any)
- audit head: `{last_seq, last_chain_hash}`
- counts: tool_exec_count, approvals_count, policy_decisions_count
- `summary_hash`, `signature`, `kid`

**Global chain record:**
- `global_seq`, `ts_epoch`
- `summary_hash`
- `prev_global_hash`
- `global_hash` (hash(summary_hash + prev_global_hash + metadata))

**Critical nuance:** global chaining only adds real security if the chain head is anchored somewhere an attacker with primary-DB access cannot rewrite.

Anchor options (choose one when threat model demands it):
- WORM object storage (object lock / retention)
- separate security account/project with different credentials
- external transparency/notary service
- (last resort) periodic offline export to a restricted system

```python
# kernel_tcb/audit/transparency.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class RunSummary:
    run_id: str
    tenant_id: str
    principal_id: str
    started_ts: float
    ended_ts: float
    status: str
    audit_last_seq: int
    audit_last_chain_hash: str
    counts: dict[str, int]

@dataclass(frozen=True)
class SignedRunSummary:
    summary: RunSummary
    summary_hash: str
    signature: str
    kid: str

class TransparencyAnchor(Protocol):
    def write_head(self, *, ts_epoch: float, global_head_hash: str) -> None: ...
```

### 8.7 Audit export bundles (portable investigations)

Add a deterministic export format so investigators can move evidence across systems.

- `export_run(run_id) -> {events.jsonl, head.json, signature}`
- include:
  - ordered audit events (redacted),
  - audit head hash,
  - optional signed run summary,
  - verification metadata (schema versions, hashing algorithm ids)

This makes “prove what happened” a tooling problem, not a hero problem.


---

## 9. K2 + K6 — Deterministic orchestrator with budgets & cancellation


### 9.0 Recommended: orchestrator wiring as event/effect machine

If you adopt the reducer + effect interpreter pattern (see §1.4), the orchestrator becomes a small, boring loop:

1) Take the next observation/event  
2) Run `KernelCore.step(state, obs)` to get `(state’, effects[])`  
3) Execute `effects[]` via `EffectRunner` (the only I/O path)  
4) Enqueue resulting observations and continue until a terminal state or budget stop

```python
# kernel_tcb/orchestrator/runtime.py
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from kernel_tcb.budgets.engine import BudgetEngine
from kernel_tcb.core.core import CoreState, KernelCore
from kernel_tcb.effects.runner import EffectRunner

@dataclass
class RunResult:
    status: str
    final_output: str | None = None

class Orchestrator:
    def __init__(self, *, core: KernelCore, runner: EffectRunner, budgets: BudgetEngine, audit: "AuditLedger"):
        self._core = core
        self._runner = runner
        self._budgets = budgets
        self._audit = audit

    def run(self, *, initial_state: CoreState, initial_observation: object) -> RunResult:
        state = initial_state
        q = deque([initial_observation])

        while q:
            self._budgets.assert_within_limits(state=state)  # K6: fail closed on exhaustion

            obs = q.popleft()
            state, effects = self._core.step(state, obs)

            # Optional: checkpoint after each state transition (or every N events)
            # effects.append(PersistCheckpoint(state_snapshot=...))

            produced = self._runner.run(effects)
            q.extend(produced)

            if state.fsm_state in ("DONE", "FAILED", "CANCELLED", "TIMEOUT"):
                return RunResult(status=state.fsm_state.lower())

        # Queue drained unexpectedly => treat as deterministic failure.
        return RunResult(status="failed")
```

**Why this matters**
- Orchestration drift becomes harder: every I/O is an explicit `Effect`.
- Deterministic replay becomes natural: record `(obs, effects, produced)` triplets.
- Testing becomes cheap: `KernelCore.step(...)` can be fuzzed without any real tools/models.


### 9.1 Explicit FSM (no “while model says”)

```python
# kernel_tcb/orchestrator/fsm.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class State(Enum):
    START = "start"
    STRATEGY = "strategy"
    EXEC_INTENTS = "exec_intents"
    VERIFY = "verify"
    DONE = "done"
    FAILED = "failed"

ALLOWED: dict[State, set[State]] = {
    State.START: {State.STRATEGY, State.FAILED},
    State.STRATEGY: {State.EXEC_INTENTS, State.DONE, State.FAILED},
    State.EXEC_INTENTS: {State.VERIFY, State.FAILED},
    State.VERIFY: {State.STRATEGY, State.DONE, State.FAILED},
    State.DONE: set(),
    State.FAILED: set(),
}

@dataclass(frozen=True)
class RunState:
    state: State
    step: int
```

### 9.2 Budgets (hard stop)

```python
# kernel_tcb/budgets/budget.py
from __future__ import annotations
from dataclasses import dataclass
import time

class BudgetExceeded(RuntimeError): pass

@dataclass(frozen=True)
class Budget:
    max_steps: int = 50
    max_wall_sec: float = 300.0
    max_tool_calls: int = 100
    max_model_calls: int = 50

class BudgetEnforcer:
    def __init__(self, budget: Budget):
        self._b = budget
        self._t0 = time.monotonic()
        self._tool_calls = 0
        self._model_calls = 0

    def check_step(self, *, step: int) -> None:
        if step > self._b.max_steps:
            raise BudgetExceeded("max_steps_exceeded")
        if (time.monotonic() - self._t0) > self._b.max_wall_sec:
            raise BudgetExceeded("max_wall_clock_exceeded")

    def bump_tool_call(self) -> None:
        self._tool_calls += 1
        if self._tool_calls > self._b.max_tool_calls:
            raise BudgetExceeded("max_tool_calls_exceeded")

    def bump_model_call(self) -> None:
        self._model_calls += 1
        if self._model_calls > self._b.max_model_calls:
            raise BudgetExceeded("max_model_calls_exceeded")
```

### 9.3 Cancellation semantics (quarantine late results)

If you can cancel a tool/model call, do it. If you cannot, quarantine the eventual result and discard it after abort.

Minimal pattern:
- tag every async op with a generation counter,
- abort increments the counter,
- results arriving from older generations are ignored.

---


### 9.4 Operational resilience in the EffectRunner (timeouts + retries + breakers + bulkheads)

Budgets (K6) prevent runaway loops. **Resilience patterns** prevent external dependencies from turning a bounded loop into a cascading outage.

This is the recommended layering for any external call (model/tool/policy/persistence):

1) **Bulkhead acquire** (capacity isolation)  
2) **Circuit breaker allow** (short-circuit if unhealthy)  
3) **Timeout** (never wait forever)  
4) **Retry** (bounded + jitter, only for safe/idempotent operations)  
5) **Record outcome as events** (K9) for audit + debugging  

#### Circuit breaker (reference implementation)

```python
# kernel_tcb/resilience/breaker.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import time

BreakerState = Literal["closed", "open", "half_open"]

class CircuitOpen(RuntimeError):
    pass

@dataclass(frozen=True)
class CircuitBreakerConfig:
    failure_threshold: int = 5          # open after N consecutive failures
    reset_timeout_sec: float = 30.0     # open -> half_open after timeout
    half_open_successes: int = 2        # close after N successes in half-open

class CircuitBreaker:
    def __init__(self, cfg: CircuitBreakerConfig):
        self._cfg = cfg
        self._state: BreakerState = "closed"
        self._failures = 0
        self._half_open_successes = 0
        self._open_until = 0.0

    @property
    def state(self) -> BreakerState:
        if self._state == "open" and time.monotonic() >= self._open_until:
            # time-based transition to half-open
            self._state = "half_open"
            self._half_open_successes = 0
        return self._state

    def allow(self) -> None:
        if self.state == "open":
            raise CircuitOpen("circuit_open")

    def record_success(self) -> None:
        if self.state == "half_open":
            self._half_open_successes += 1
            if self._half_open_successes >= self._cfg.half_open_successes:
                self._state = "closed"
                self._failures = 0
        else:
            self._failures = 0

    def record_failure(self) -> None:
        if self.state == "half_open":
            self._trip_open()
            return

        self._failures += 1
        if self._failures >= self._cfg.failure_threshold:
            self._trip_open()

    def _trip_open(self) -> None:
        self._state = "open"
        self._open_until = time.monotonic() + self._cfg.reset_timeout_sec
        self._half_open_successes = 0
```

#### Bulkhead (capacity limiter + bounded queue)

Use a bulkhead whenever calls may block (network I/O, slow tools). At minimum:
- **per-tenant run limiter**
- **per-tool limiter**
- separate pools/limiters for model vs tools vs persistence

```python
# kernel_tcb/resilience/bulkhead.py
from __future__ import annotations
from dataclasses import dataclass
import threading
import time

class BulkheadBusy(RuntimeError):
    pass

@dataclass(frozen=True)
class BulkheadConfig:
    max_concurrency: int
    acquire_timeout_sec: float = 0.0   # 0 => fail fast

class Bulkhead:
    def __init__(self, cfg: BulkheadConfig):
        self._cfg = cfg
        self._sem = threading.Semaphore(cfg.max_concurrency)

    def acquire(self) -> None:
        if self._cfg.acquire_timeout_sec <= 0:
            ok = self._sem.acquire(blocking=False)
        else:
            ok = self._sem.acquire(timeout=self._cfg.acquire_timeout_sec)
        if not ok:
            raise BulkheadBusy("bulkhead_overloaded")

    def release(self) -> None:
        self._sem.release()

    def __enter__(self) -> "Bulkhead":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
```

#### EffectRunner integration pattern (single place to enforce it)

```python
# kernel_tcb/effects/runner.py (illustrative pattern)
from kernel_tcb.resilience.breaker import CircuitBreaker, CircuitOpen
from kernel_tcb.resilience.bulkhead import Bulkhead, BulkheadBusy

class DependencyUnavailable(Exception):
    pass

class ResilienceManager:
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._bulkheads: dict[str, Bulkhead] = {}

    def breaker(self, key: str) -> CircuitBreaker:
        return self._breakers.setdefault(key, CircuitBreaker(CircuitBreakerConfig()))

    def bulkhead(self, key: str) -> Bulkhead:
        # choose cfg per key (tool/model/persistence)
        return self._bulkheads.setdefault(key, Bulkhead(BulkheadConfig(max_concurrency=8)))

    def call(self, *, dep_key: str, fn, on_event) :
        b = self.breaker(dep_key)
        bh = self.bulkhead(dep_key)
        try:
            b.allow()
            with bh:
                r = fn()
            b.record_success()
            on_event({"kind":"dependency_call_ok","dep":dep_key})
            return r
        except (BulkheadBusy, CircuitOpen) as e:
            on_event({"kind":"dependency_call_short_circuit","dep":dep_key, "reason": type(e).__name__})
            raise DependencyUnavailable(str(e))
        except Exception as e:
            b.record_failure()
            on_event({"kind":"dependency_call_failed","dep":dep_key, "err": type(e).__name__})
            raise
```

**Kernel behavior on `DependencyUnavailable`**
- Prefer deterministic safe mode (K15) or abort with a typed failure.
- Do not “route around” safety controls by swapping tools/providers unless you have explicit, policy-reviewed fallback rules.


### 9.5 Effect middleware pipeline (the wiring that makes patterns real)

A recurring production failure mode is **“patterns described, but not actually applied everywhere.”**  
The fix is architectural: route **all external interactions** through a single interpreter lane, and implement cross-cutting concerns as **middleware** around effect execution.

This is how you make these claims *mechanically true*:

- circuit breakers wrap **every** dependency call,
- bulkheads isolate tenants/tools/models by construction,
- timeouts/retries/metrics/redaction/tracing are not scattered.

#### Rule: every external interaction is an Effect

If it crosses a boundary (network, disk, DB, remote service), model it as an effect kind:

- `call_model`
- `tool_preview`, `tool_execute`
- `policy_eval` (only if policy is remote; pure policy can be in-process)
- `approval_request`, `approval_wait`
- `persist_checkpoint`, `audit_emit`, `outbox_enqueue`
- `secrets_issue` (K14 scoped credentials)

If you keep “approval wait” or “remote policy eval” as direct calls inside helpers, you will eventually bypass breakers/bulkheads and reintroduce nondeterminism.

#### Middleware skeleton (production reference)

```python
# kernel_tcb/effects/middleware.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from kernel_tcb.effects.abi import KernelEffect

Observation = dict[str, Any]
EffectHandler = Callable[["EffectContext", KernelEffect], list[Observation]]

@dataclass(frozen=True)
class EffectContext:
    trace_id: str
    run_id: str
    tenant_id: str | None
    principal: str
    mode: str  # "live" | "record" | "replay"
    now_epoch_ms: int
    deadline_epoch_ms: int

class EffectMiddleware(Protocol):
    middleware_id: str
    def __call__(self, *, ctx: EffectContext, effect: KernelEffect, nxt: EffectHandler) -> list[Observation]: ...

def build_pipeline(*, middlewares: list[EffectMiddleware], terminal: EffectHandler) -> EffectHandler:
    handler = terminal
    for mw in reversed(middlewares):
        prev = handler
        def _wrapped(ctx: EffectContext, effect: KernelEffect, mw=mw, prev=prev) -> list[Observation]:
            return mw(ctx=ctx, effect=effect, nxt=prev)
        handler = _wrapped
    return handler
```

#### Dependency keys: one convention, everywhere

Circuit breakers and bulkheads need consistent keys.

```python
# kernel_tcb/effects/deps.py
from __future__ import annotations
from kernel_tcb.effects.abi import KernelEffect

def dependency_key(effect: KernelEffect) -> str:
    k = getattr(effect, "kind", "unknown")
    if k == "call_model":
        # If you use routing (see §10.3), include provider id post-route in events.
        return f"model_class:{effect.req.model_class}"
    if k == "tool_preview":
        return f"tool:{effect.tool_name}:preview"
    if k == "tool_execute":
        return f"tool:{effect.tool_name}"
    if k in ("approval_request", "approval_wait"):
        return "approval:primary"
    if k in ("audit_emit",):
        return "audit:primary"
    if k in ("persist_checkpoint", "outbox_enqueue"):
        return "db:primary"
    if k in ("secrets_issue",):
        return "secrets:primary"
    if k in ("policy_eval",):
        return "policy:primary"
    return f"internal:{k}"
```

#### Middleware examples (breaker + bulkhead wired once)

```python
# kernel_tcb/effects/mw_resilience.py
from __future__ import annotations

from kernel_tcb.effects.middleware import EffectContext, EffectMiddleware, EffectHandler
from kernel_tcb.effects.deps import dependency_key
from kernel_tcb.resilience.breaker import CircuitBreaker, CircuitOpen
from kernel_tcb.resilience.bulkhead import Bulkhead, BulkheadBusy

class DependencyUnavailable(RuntimeError):
    pass

class BreakerRegistry:
    def __init__(self, breakers: dict[str, CircuitBreaker]):
        self._b = breakers
    def get(self, key: str) -> CircuitBreaker:
        return self._b.setdefault(key, CircuitBreaker())  # configure per key in real impl

class BulkheadRegistry:
    def __init__(self, bulkheads: dict[str, Bulkhead]):
        self._h = bulkheads
    def get(self, key: str) -> Bulkhead:
        return self._h.setdefault(key, Bulkhead(name=key, max_in_flight=50))

class CircuitBreakerMiddleware(EffectMiddleware):
    middleware_id = "circuit_breaker"

    def __init__(self, reg: BreakerRegistry):
        self._reg = reg

    def __call__(self, *, ctx: EffectContext, effect, nxt: EffectHandler):
        dep = dependency_key(effect)
        br = self._reg.get(dep)
        try:
            br.allow()
        except CircuitOpen as e:
            raise DependencyUnavailable(f"{dep}:{e}") from e
        try:
            out = nxt(ctx, effect)
            br.record_success()
            return out
        except Exception:
            br.record_failure()
            raise

class BulkheadMiddleware(EffectMiddleware):
    middleware_id = "bulkhead"

    def __init__(self, reg: BulkheadRegistry):
        self._reg = reg

    def __call__(self, *, ctx: EffectContext, effect, nxt: EffectHandler):
        dep = dependency_key(effect)

        # Typical production pattern: apply multiple bulkheads (tenant + dep class + tool).
        # Keep this minimal here; see §1.8 for recommended key sets.
        bh = self._reg.get(dep)
        try:
            with bh.acquire(timeout_ms=0):  # fail fast; outbox/retry can requeue
                return nxt(ctx, effect)
        except BulkheadBusy as e:
            raise DependencyUnavailable(f"{dep}:bulkhead_busy") from e
```

#### EffectRunner wiring (no “forgotten” call sites)

```python
# kernel_tcb/effects/runner.py (reference skeleton)
from __future__ import annotations

from kernel_tcb.effects.abi import KernelEffect
from kernel_tcb.effects.middleware import EffectContext, build_pipeline, EffectMiddleware

class EffectRunner:
    def __init__(self, *, dispatcher, middlewares: list[EffectMiddleware]):
        self._dispatch = dispatcher
        self._handler = build_pipeline(middlewares=middlewares, terminal=self._dispatch)

    def run(self, *, ctx: EffectContext, effects: list[KernelEffect]) -> list[dict]:
        observations: list[dict] = []
        for eff in effects:
            observations.extend(self._handler(ctx, eff))
        return observations
```

**Hard rule:** adapters/clients/DB sessions must not be callable directly from orchestration code.  
If a team “just calls the tool adapter” somewhere else, CI should fail (import-lint) and runtime should fail closed (missing provenance / missing capability / missing effect context).

#### Acceptance test to catch wiring regressions

Add at least one “tripwire” test that proves all external effects pass through middleware:

- Provide a `TripwireMiddleware` that sets a contextvar on entry.
- Wrap tool/model/approval/persistence adapters with stubs that assert the contextvar is set.
- Run a small scenario that exercises each effect kind.
- If any call bypasses the middleware lane, the test fails.

(Include this under Proof H/I expansions in §21.)


---

## 10. K3 — Model boundary (LLM as tool)

### 10.1 Provider-neutral envelopes

```python
# kernel_tcb/model/abi.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Any

class ModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    prompt_hash: str
    messages: list[dict[str, Any]]
    model_class: str = "default"  # e.g. cheap|reasoning|vision|long_context
    constraints: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)

class ModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: str
    model_id: str
    content: str
    usage: dict[str, int] = Field(default_factory=dict)
    finish_reason: str | None = None
    raw_response_hash: str | None = None
```

### 10.2 Provider port + boundary

```python
# kernel_tcb/model/boundary.py
from __future__ import annotations

import hashlib
import json
from pydantic import BaseModel, ValidationError
from typing import Protocol, TypeVar

from kernel_tcb.model.abi import ModelRequest, ModelResponse

class ModelProvider(Protocol):
    provider_id: str
    def complete(self, req: ModelRequest) -> ModelResponse: ...

T = TypeVar("T", bound=BaseModel)

def _stable_hash(domain: str, obj: object) -> str:
    msg = f"{domain}:v1|{json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)}".encode("utf-8")
    return "sha256:" + hashlib.sha256(msg).hexdigest()

class ModelBoundary:
    def __init__(self, *, provider: ModelProvider, max_repair_attempts: int = 2, max_output_bytes: int = 32_768):
        self._provider = provider
        self._max_repair = max_repair_attempts
        self._max_output_bytes = max_output_bytes

    def complete_text(self, *, messages: list[dict], config: dict) -> ModelResponse:
        prompt_hash = _stable_hash("prompt", {"messages": messages, "config": config})
        resp = self._provider.complete(ModelRequest(prompt_hash=prompt_hash, messages=messages, config=config))
        if len(resp.content.encode("utf-8")) > self._max_output_bytes:
            raise ValueError("model_output_too_large")
        return resp

    def complete_structured(self, *, messages: list[dict], config: dict, schema: type[T]) -> tuple[ModelResponse, T]:
        last_err: str | None = None

        for _attempt in range(self._max_repair + 1):
            if last_err is None:
                resp = self.complete_text(messages=messages, config=config)
            else:
                repair_messages = messages + [{
                    "role": "user",
                    "content": f"Your previous output was invalid JSON for the required schema. Error: {last_err}\nReturn ONLY valid JSON.",
                }]
                resp = self.complete_text(messages=repair_messages, config=config)

            try:
                data = json.loads(resp.content)
                parsed = schema.model_validate(data)
                return resp, parsed
            except (json.JSONDecodeError, ValidationError) as e:
                last_err = str(e)
                continue

        raise ValueError("model_invalid_structured_output")
```

**Kernel invariant:** model outputs are never trusted without validation, and repairs are bounded.

---


### 10.3 Multi-provider model routing (make “multi-LLM” real without policy bypass)

The minimal boundary in §10.2 shows a single injected provider. That’s fine for a reference build, but production systems typically need:

- multiple providers (cost, latency, feature coverage),
- regional/data-residency constraints,
- tenant-specific allowlists,
- graceful fallback (policy-reviewed),
- clean auditing of *which* provider/model was used and *why*.

**Important safety nuance:** Strategy should not choose a provider directly if Strategy is untrusted.  
Instead, Strategy requests a **model class** (capability tier), and the kernel routes the call by **policy**.

#### Extend the request envelope with a model class

```python
# kernel_tcb/model/abi.py (additions)
from pydantic import BaseModel, ConfigDict, Field
from typing import Any

class ModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    prompt_hash: str
    messages: list[dict[str, Any]]
    model_class: str = "default"  # e.g. cheap|reasoning|vision|long_context
    constraints: dict[str, Any] = Field(default_factory=dict)  # e.g. {"data_residency":"EU"}
    config: dict[str, Any] = Field(default_factory=dict)
```

#### Provider registry + router ports

```python
# kernel_tcb/model/routing.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

from kernel_tcb.model.abi import ModelRequest

@dataclass(frozen=True)
class ModelRoute:
    provider_id: str
    model_id: str
    reason: str  # for audit/debug ("tenant_policy", "fallback", "cost_cap")

class ModelProviderRegistry(Protocol):
    def get(self, provider_id: str): ...  # returns ModelProvider
    def list(self) -> list[str]: ...

class ModelRouter(Protocol):
    router_id: str
    def route(self, *, tenant_id: str | None, principal: str, bundle_id: str | None, req: ModelRequest) -> ModelRoute: ...
```

#### Multi-provider boundary (router + per-provider boundary)

```python
# kernel_tcb/model/multiprovider.py
from __future__ import annotations

from kernel_tcb.model.boundary import ModelBoundary, ModelProvider
from kernel_tcb.model.routing import ModelProviderRegistry, ModelRouter
from kernel_tcb.audit.ledger import AuditLedger
from kernel_tcb.effects.middleware import EffectContext  # for trace/run metadata

class MultiProviderModelService:
    def __init__(
        self,
        *,
        registry: ModelProviderRegistry,
        router: ModelRouter,
        audit: AuditLedger,
        max_repair_attempts: int = 2,
        max_output_bytes: int = 32_768,
    ):
        self._registry = registry
        self._router = router
        self._audit = audit
        self._boundaries: dict[str, ModelBoundary] = {}

        # Lazily build per-provider boundaries on demand (keeps startup cheap).
        self._max_repair = max_repair_attempts
        self._max_out = max_output_bytes

    def _boundary(self, provider_id: str) -> ModelBoundary:
        b = self._boundaries.get(provider_id)
        if b is None:
            provider: ModelProvider = self._registry.get(provider_id)
            b = ModelBoundary(provider=provider, max_repair_attempts=self._max_repair, max_output_bytes=self._max_out)
            self._boundaries[provider_id] = b
        return b

    def complete_text(self, *, ctx: EffectContext, req: "ModelRequest") -> "ModelResponse":
        route = self._router.route(
            tenant_id=ctx.tenant_id,
            principal=ctx.principal,
            bundle_id=None,  # set if you pin policy bundles (see §12.4)
            req=req,
        )

        # Audit the route decision (no raw prompt text; use hashes).
        self._audit.emit(
            trace_id=ctx.trace_id,
            run_id=ctx.run_id,
            name="model.routed",
            payload={
                "router_id": getattr(self._router, "router_id", "unknown"),
                "provider_id": route.provider_id,
                "model_id": route.model_id,
                "model_class": req.model_class,
                "prompt_hash": req.prompt_hash,
                "reason": route.reason,
            },
        )

        # Provider-specific config injection (model id)
        config = dict(req.config)
        config["model"] = route.model_id

        return self._boundary(route.provider_id).complete_text(messages=req.messages, config=config)
```

#### Router policy discipline (keep it deterministic)

- Route decisions must be **deterministic** for the same `(tenant_id, bundle_id/version, model_class, constraints)`.
- If you support fallbacks, treat them as **policy-reviewed** (and log `reason="fallback"`).
- Record/replay must pin the chosen provider/model for reproducibility (store in trace events).

**Release gate:** add a test that a run can call two different providers by changing `model_class` while policy controls which are allowed (see §21 additions).


## 11. K4 — Tool executor (schema validation + idempotency metadata)

### 11.1 Tool manifest

```python
# kernel_tcb/tools/manifest.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Any, Literal

RiskTier = Literal["low","medium","high"]

class ToolSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    version: str
    risk_tier: RiskTier
    has_side_effects: bool
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    supports_preview: bool = False
    supports_idempotency: bool = True
    timeout_ms_default: int = 30_000
    required_scopes: list[str] = []  # K14: secrets broker scopes needed for live execution
    credential_ttl_sec_default: int = 900

class ToolManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    manifest_version: str
    tools: list[ToolSpec]

    def get(self, name: str) -> ToolSpec:
        for t in self.tools:
            if t.name == name:
                return t
        raise KeyError(f"unknown tool: {name}")
```

### 11.2 Canonical args + idempotency key (kernel-generated)

```python
# kernel_tcb/tools/canonical.py
from __future__ import annotations
import hashlib, json
from typing import Any

def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def stable_hash(domain: str, obj: Any) -> str:
    msg = f"{domain}:v1|{canonical_json(obj)}".encode("utf-8")
    return "sha256:" + hashlib.sha256(msg).hexdigest()

def idempotency_key(*, tool_name: str, args: dict, run_id: str) -> str:
    return stable_hash("idempotency", {"tool": tool_name, "run_id": run_id, "args": args})
```

### 11.3 Tool port + executor

```python
# kernel_tcb/tools/ports.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Protocol

class ToolMeta(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    trace_id: str
    run_id: str
    principal: str
    tenant_id: str | None
    policy_bundle_id: str | None = None
    policy_bundle_version: str | None = None
    idempotency_key: str
    timeout_ms: int
    mode: str  # "live" | "replay"

class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ok: bool
    output: dict | None = None
    error: dict | None = None

class ToolAdapter(Protocol):
    tool_name: str
    tool_version: str
    def preview(self, args: dict, meta: ToolMeta) -> ToolResult: ...
    def execute(self, args: dict, meta: ToolMeta, *, creds: dict[str, str] | None = None) -> ToolResult: ...
```

```python
# kernel_tcb/tools/executor.py
from __future__ import annotations

from kernel_tcb.security.capabilities import CapabilityGrant, CapabilityTokens, compute_args_hash
from kernel_tcb.security.secrets import SecretsBroker, CredentialRequest
from kernel_tcb.tools.manifest import ToolManifest
from kernel_tcb.tools.ports import ToolAdapter, ToolMeta, ToolResult

class ToolExecutor:
    """K4 tool execution boundary.

    - Validates tool names against the manifest.
    - Enforces capability tokens for commits (and for tools requiring secrets).
    - Keeps Strategy untrusted: tool adapters never leak upward.
    """
    def __init__(
        self,
        *,
        manifest: ToolManifest,
        adapters: dict[str, ToolAdapter],
        capabilities: CapabilityTokens,
        secrets: SecretsBroker | None = None,
    ):
        self._manifest = manifest
        self._adapters = adapters
        self._cap = capabilities
        self._secrets = secrets

    def spec(self, tool_name: str):
        return self._manifest.get(tool_name)

    def preview(self, *, tool_name: str, args: dict, meta: ToolMeta) -> ToolResult:
        return self._adapters[tool_name].preview(args, meta)

    def execute(self, *, tool_name: str, args: dict, meta: ToolMeta, capability_token: str | None = None) -> ToolResult:
        spec = self._manifest.get(tool_name)

        # Replay mode must be side-effect free.
        if meta.mode == "replay" and spec.has_side_effects:
            return ToolResult(ok=False, error={"code": "replay_forbids_side_effects"})

        # Treat "requires secrets" as privileged. A tool that can access credentials is powerful even if read-only.
        requires_privilege = spec.has_side_effects or bool(getattr(spec, "required_scopes", []))
        if requires_privilege:
            if capability_token is None:
                return ToolResult(ok=False, error={"code": "missing_capability"})

            try:
                grant: CapabilityGrant = self._cap.verify(capability_token)
            except Exception as e:  # fail closed
                return ToolResult(ok=False, error={"code": "invalid_capability", "detail": str(e)})

            expected_args_hash = compute_args_hash(tool_name=tool_name, args=args)
            if (
                grant.phase != "commit"
                or grant.tool_name != tool_name
                or grant.args_hash != expected_args_hash
                or grant.run_id != meta.run_id
                or grant.principal != meta.principal
                or grant.tenant_id != meta.tenant_id
            ):
                return ToolResult(ok=False, error={"code": "capability_mismatch"})

        creds: dict[str, str] | None = None
        if getattr(spec, "required_scopes", []) and meta.mode != "replay":
            if self._secrets is None:
                return ToolResult(ok=False, error={"code": "missing_secrets_broker"})
            issued = self._secrets.issue(CredentialRequest(
                tool_name=tool_name,
                scopes=list(spec.required_scopes),
                ttl_sec=int(getattr(spec, "credential_ttl_sec_default", 900)),
                run_id=meta.run_id,
                tenant_id=meta.tenant_id,
                principal=meta.principal,
                capability_token=capability_token,  # broker may re-verify for defense in depth
            ))
            creds = issued.creds

        return self._adapters[tool_name].execute(args, meta, creds=creds)
```

---

## 12. K5 — Policy engine + reference monitor (two-phase)

### 12.1 Policy decisions

```python
# kernel_tcb/policy/decisions.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Literal

Decision = Literal["allow","deny","needs_approval"]

class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    decision: Decision
    reason: str
    binding_hash: str
    expires_at_epoch: int | None = None
```

### 12.2 Approval port

```python
# kernel_tcb/policy/approval_ports.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Literal, Protocol

class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    binding_hash: str
    tool_name: str
    preview_redacted: dict | None
    expires_at_epoch: int
    reason: str

class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    binding_hash: str
    decision: Literal["approve","deny"]
    actor: str
    decided_at_epoch: int

class ApprovalPort(Protocol):
    def request(self, req: ApprovalRequest) -> None: ...
    def wait_for_decision(self, *, binding_hash: str, timeout_sec: int) -> ApprovalDecision: ...
```

### 12.3 Binding hash (tool + args + preview)

```python
# kernel_tcb/policy/binding.py
from __future__ import annotations
from kernel_tcb.tools.canonical import stable_hash

def compute_binding_hash(*, tool_name: str, args: dict, preview: dict | None) -> str:
    return stable_hash("approval_binding", {"tool": tool_name, "args": args, "preview": preview})
```

### 12.4 Policy engine (data-driven, deterministic)

#### 12.4.1 Policy bundles + selection + version pinning (close the “flat rules” gap)

If your design claims “policy bundles are pluggable and context-aware,” you must actually wire:

- **bundle identity** (`bundle_id`)
- **bundle version** (`bundle_version`)
- **selection context** (tenant/run_type/principal/data_class)
- **pinning** (store selection in the run record so replay/debug is coherent)

Otherwise policy inevitably becomes “whatever rules are deployed today,” which breaks auditability and reproducibility.

Minimal ports:

```python
# kernel_tcb/policy/bundles.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

from kernel_tcb.policy.engine import PolicyRule

@dataclass(frozen=True)
class PolicyBundle:
    bundle_id: str
    version: str
    rules: list[PolicyRule]
    metadata: dict

@dataclass(frozen=True)
class PolicySelection:
    bundle_id: str
    version: str
    reason: str  # e.g. "tenant_default", "run_type_override"

class PolicyBundleRegistry(Protocol):
    def get(self, *, bundle_id: str, version: str) -> PolicyBundle: ...
    def latest(self, *, bundle_id: str) -> PolicyBundle: ...
    def list(self) -> list[PolicyBundle]: ...

class PolicySelector(Protocol):
    selector_id: str
    def select(
        self,
        *,
        tenant_id: str | None,
        run_type: str,
        principal: str,
        data_class: str,
    ) -> PolicySelection: ...
```

**Pin at run start** (recommended):
- When creating a run, call `PolicySelector.select(...)`.
- Persist `{bundle_id, version}` in `RunRecord`.
- Emit audit event `policy.bundle_selected` (include selector_id, bundle_id, version, reason).

Then every decision event includes `bundle_id` + `bundle_version`.

---


```python
# kernel_tcb/policy/engine.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from kernel_tcb.policy.bundles import PolicyBundleRegistry
from kernel_tcb.policy.decisions import PolicyDecision

Decision = Literal["allow","deny","needs_approval"]

@dataclass(frozen=True)
class PolicyRule:
    tool_name: str
    mode: Literal["read","write"]
    requires_approval: bool
    constraints: dict  # keep data-only; interpret deterministically

class PolicyEngine:
    """Deterministic policy evaluator.

    - Pure/local evaluation is recommended.
    - If you must call a remote policy service, model it as an effect (`policy_eval`)
      so breakers/bulkheads/timeouts apply via the EffectRunner middleware (§9.5).
    """
    def __init__(self, *, registry: PolicyBundleRegistry, approval_expiry_sec: int = 300):
        self._registry = registry
        self._approval_expiry_sec = approval_expiry_sec

    def evaluate(
        self,
        *,
        bundle_id: str,
        bundle_version: str,
        tool_name: str,
        args: dict,
        has_side_effects: bool,
        risk_tier: str,
        binding_hash: str,
    ) -> PolicyDecision:
        bundle = self._registry.get(bundle_id=bundle_id, version=bundle_version)

        # NOTE: cache this mapping in the registry for performance in production.
        rules = {r.tool_name: r for r in bundle.rules}
        rule = rules.get(tool_name)
        if rule is None:
            return PolicyDecision(decision="deny", reason="tool_not_allowlisted", binding_hash=binding_hash)

        # Example constraint: forbid high-risk side effects without explicit allow.
        if has_side_effects and rule.mode != "write":
            return PolicyDecision(decision="deny", reason="write_not_allowed", binding_hash=binding_hash)

        # Example constraint hook (size limits, denylist, etc.)
        # Keep constraints deterministic: no network calls, no implicit clocks.
        # If constraints require external data, move evaluation behind an effect.
        _ = rule.constraints  # interpreted by your Spec engine (§12.7)

        if rule.requires_approval:
            return PolicyDecision(
                decision="needs_approval",
                reason="requires_approval",
                binding_hash=binding_hash,
                expires_at_epoch=int(time.time()) + self._approval_expiry_sec,
            )

        return PolicyDecision(decision="allow", reason="allowed", binding_hash=binding_hash)
```

### 12.5 Reference monitor (complete mediation)

```python
# kernel_tcb/policy/reference_monitor.py
from __future__ import annotations

import time

from kernel_tcb.audit.ledger import AuditLedger
from kernel_tcb.policy.binding import compute_binding_hash
from kernel_tcb.policy.engine import PolicyEngine
from kernel_tcb.policy.approval_ports import ApprovalPort, ApprovalRequest
from kernel_tcb.security.capabilities import CapabilityGrant, CapabilityTokens, compute_args_hash
from kernel_tcb.tools.executor import ToolExecutor
from kernel_tcb.tools.ports import ToolMeta, ToolResult
from kernel_tcb.verify.chain import VerifierChain, VerifierInput

class ReferenceMonitor:
    """Complete mediation (K5) around tool execution.

    Note on wiring: if ApprovalPort/PolicyEngine are remote services,
    model them as effects (`approval_wait`, `policy_eval`) so breakers/bulkheads apply via middleware (§9.5).
    This snippet shows the *logic*; production implementations typically execute the waits/calls through EffectRunner.
    """

    def __init__(
        self,
        *,
        policy: PolicyEngine,
        approvals: ApprovalPort,
        tools: ToolExecutor,
        capabilities: CapabilityTokens,
        verifiers: VerifierChain,
        audit: AuditLedger,
    ):
        self._policy = policy
        self._approvals = approvals
        self._tools = tools
        self._cap = capabilities
        self._verifiers = verifiers
        self._audit = audit

    def _bundle(self, meta: ToolMeta) -> tuple[str, str]:
        if meta.policy_bundle_id is None or meta.policy_bundle_version is None:
            # Fail closed in live/record; allow None in replay only if tool calls are blocked anyway.
            if meta.mode != "replay":
                raise ValueError("missing_policy_bundle_pin")
            return ("unknown", "unknown")
        return (meta.policy_bundle_id, meta.policy_bundle_version)

    def propose(self, *, trace_id, run_id, tool_name: str, args: dict, meta: ToolMeta) -> tuple[dict | None, str, int | None]:
        preview_result = self._tools.preview(tool_name=tool_name, args=args, meta=meta)
        binding_hash = compute_binding_hash(tool_name=tool_name, args=args, preview=preview_result.output)

        bundle_id, bundle_version = self._bundle(meta)
        spec = self._tools.spec(tool_name)

        decision = self._policy.evaluate(
            bundle_id=bundle_id,
            bundle_version=bundle_version,
            tool_name=tool_name,
            args=args,
            has_side_effects=spec.has_side_effects,
            risk_tier=spec.risk_tier,
            binding_hash=binding_hash,
        )

        self._audit.emit(trace_id=trace_id, run_id=run_id, name="policy_decision", payload={
            "bundle_id": bundle_id,
            "bundle_version": bundle_version,
            "tool": tool_name,
            "decision": decision.decision,
            "reason": decision.reason,
            "binding_hash": binding_hash,
        })

        if decision.decision == "needs_approval":
            self._approvals.request(ApprovalRequest(
                binding_hash=binding_hash,
                tool_name=tool_name,
                preview_redacted=preview_result.output,  # redaction happens in AuditLedger
                expires_at_epoch=decision.expires_at_epoch or 0,
                reason=decision.reason,
            ))

        if decision.decision == "deny":
            raise PermissionError(decision.reason)

        return preview_result.output, binding_hash, decision.expires_at_epoch

    def commit(self, *, trace_id, run_id, tool_name: str, args: dict, meta: ToolMeta, timeout_sec: int = 300) -> ToolResult:
        # Recompute preview + binding at commit time (TOCTOU-safe).
        preview_result = self._tools.preview(tool_name=tool_name, args=args, meta=meta)
        binding_hash = compute_binding_hash(tool_name=tool_name, args=args, preview=preview_result.output)

        # Independent verifier chain (K7): any verifier can veto.
        v = self._verifiers.verify(
            run_id=run_id,
            inp=VerifierInput(
                artifact_type="tool_intent",
                payload={
                    "tool": tool_name,
                    "args_hash": compute_args_hash(tool_name=tool_name, args=args),
                    "binding_hash": binding_hash,
                    "preview_hash": None,  # optionally stable_hash(preview_result.output)
                    "tenant_id": meta.tenant_id,
                    "principal": meta.principal,
                },
            ),
        )
        if not v.ok:
            self._audit.emit(trace_id=trace_id, run_id=run_id, name="verifier_veto", payload={
                "tool": tool_name,
                "binding_hash": binding_hash,
                "verifier_id": v.detail.get("verifier_id"),
                "reason": v.reason,
            })
            return ToolResult(ok=False, error={"code": "verifier_veto", "reason": v.reason})

        bundle_id, bundle_version = self._bundle(meta)
        spec = self._tools.spec(tool_name)

        decision = self._policy.evaluate(
            bundle_id=bundle_id,
            bundle_version=bundle_version,
            tool_name=tool_name,
            args=args,
            has_side_effects=spec.has_side_effects,
            risk_tier=spec.risk_tier,
            binding_hash=binding_hash,
        )

        if decision.decision == "deny":
            return ToolResult(ok=False, error={"code": "policy_denied", "reason": decision.reason})

        if decision.decision == "needs_approval":
            # In production, treat this wait as an effect (`approval_wait`) so middleware applies.
            approval = self._approvals.wait_for_decision(binding_hash=binding_hash, timeout_sec=timeout_sec)
            if approval.decision != "approved":
                return ToolResult(ok=False, error={"code": "approval_denied", "reason": approval.reason})

        # Mint capability token (required for side effects; also recommended for tools that require secrets).
        capability_token: str | None = None
        if spec.has_side_effects or getattr(spec, "required_scopes", []):
            grant = CapabilityGrant(
                tool_name=tool_name,
                args_hash=compute_args_hash(tool_name=tool_name, args=args),
                phase="commit",
                run_id=meta.run_id,
                principal=meta.principal,
                tenant_id=meta.tenant_id,
                expires_at_epoch=int(time.time()) + 300,
                binding_hash=binding_hash,
            )
            capability_token = self._cap.sign(grant)

            self._audit.emit(trace_id=trace_id, run_id=run_id, name="capability_issued", payload={
                "bundle_id": bundle_id,
                "bundle_version": bundle_version,
                "tool": tool_name,
                "args_hash": grant.args_hash,
                "binding_hash": binding_hash,
                "expires_at_epoch": grant.expires_at_epoch,
                "grant_hash": grant.stable_hash(domain="capability_grant"),
            })

        return self._tools.execute(tool_name=tool_name, args=args, meta=meta, capability_token=capability_token)
```


### 12.6 Capability tokens (capability-based authorization)

A **capability token** is a signed permit object. Tool execution requires presenting the permit, so “complete mediation” becomes a mechanical property of the codebase.

**What the grant encodes**
- tool identity (`tool_name`)
- canonical args hash (`args_hash`)
- phase (`preview` vs `commit`; in practice you mostly care about `commit`)
- principal + tenant + run binding
- expiry
- optional approval binding hash (`binding_hash`)

**Where this helps**
- Prevents accidental bypass (“someone called execute() without policy”).
- Makes approvals portable across distributed executors.
- Turns authorization into an auditable artifact (log the grant hash / expiry).

#### Reference implementation (HMAC, internal systems)

```python
# kernel_tcb/security/capabilities.py
from __future__ import annotations

import base64
import hmac
import hashlib
import json
import time
from pydantic import BaseModel, ConfigDict
from typing import Literal

from kernel_tcb.abi.base import ABIModel
from kernel_tcb.tools.canonical import canonical_json, stable_hash

class CapabilityGrant(ABIModel):
    # Append-only schema; rotate via schema_version if needed.
    schema_version: str = "v1"

    phase: Literal["preview", "commit"]
    tool_name: str
    args_hash: str
    binding_hash: str | None = None

    run_id: str
    principal: str
    tenant_id: str | None

    expires_at_epoch: int

def compute_args_hash(*, tool_name: str, args: dict) -> str:
    # Domain-separated stable hash of tool+args (canonicalized).
    return stable_hash("tool_args", {"tool_name": tool_name, "args": args})

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

class CapabilityTokens:
    def __init__(self, *, secret_key: bytes):
        if not secret_key:
            raise ValueError("missing_secret_key")
        self._key = secret_key

    def sign(self, grant: CapabilityGrant) -> str:
        payload_json = canonical_json(grant.model_dump())
        sig = hmac.new(self._key, payload_json.encode("utf-8"), hashlib.sha256).digest()
        return _b64url(payload_json.encode("utf-8")) + "." + _b64url(sig)

    def verify(self, token: str) -> CapabilityGrant:
        try:
            payload_b64, sig_b64 = token.split(".", 1)
        except ValueError as e:
            raise ValueError("invalid_token_format") from e

        payload = _b64url_decode(payload_b64)
        sig = _b64url_decode(sig_b64)

        expected = hmac.new(self._key, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, sig):
            raise ValueError("bad_signature")

        data = json.loads(payload.decode("utf-8"))
        grant = CapabilityGrant.model_validate(data)  # rejects unknown fields (via ABIModel)

        if int(time.time()) > grant.expires_at_epoch:
            raise ValueError("expired")

        return grant
```

**Key management**
- Keep `secret_key` in a KMS / secret store; rotate it like any other auth credential.
- If you need cross-service verification without shared secrets, switch the signer to Ed25519 and publish a verify key.

---


#### 12.6.1 Key management and rotation (don’t wing this later)

Capability tokens become part of your authorization “ground truth,” so treat signing keys like production secrets.

**Minimum viable key management:**
- Tokens include a `kid` (key id).  
- Verifier looks up keys in a **KeyRing**:
  - one active signing key,
  - N previous verification keys (for rotation grace period).
- Keys are never logged; only `kid` is logged.

**Rotation policy (reasonable default):**
- Rotate signing key on a schedule (e.g., weekly/monthly) or on incident.
- Keep old keys valid for verification for **2× the max token TTL** (plus clock skew).
- Immediately revoke on compromise (remove from verifier set).

**Where keys live:**
- Preferred: KMS/HSM (managed key material, audit, rotation).
- Acceptable early: env-injected secret (with strict access controls) + secret manager.
- Avoid: keys baked into images, repos, or “temporary” config files.

**Token claims you should include:**
- `kid`, `iat`, `exp` (issued-at and expiry)
- `tenant_id`, `run_id`, `principal_id`
- `tool_name`, `args_hash`, `phase` (`preview`/`commit` or `read`/`write`)
- optional: `approval_binding_hash`, `policy_decision_id`

**Clock behavior:**
- Allow small skew (±30s) to avoid false negatives.
- Prefer monotonic time for local timeouts; use wall clock only for expiry semantics.

#### 12.6.2 Operational hardening: “permit objects” across distributed executors

If you move tool execution to separate workers:
- Treat the capability token as the *only* permission artifact the executor trusts.
- Do not re-query policy at execution time (prevents “split brain” policy state).
- Require the executor to emit `capability_verified` and `tool_executed` events with the token’s stable grant hash.

This is what makes complete mediation survive distributed systems.


### 12.7 Policy specification pattern (composable predicates + explainability)

As policy grows, procedural `if/else` matching becomes brittle and hard to audit. A **specification pattern** turns policy into composable, testable predicates that produce **structured reasons**.

**Design goals:**
- **Deterministic:** specs are pure; no I/O; no implicit clocks.
- **Composable:** `ToolAllowlisted.and_(ArgSizeLimit).and_(TenantAllowed)`.
- **Explainable:** evaluation returns *reason codes* (machine) + detail (human).
- **Auditable:** the policy decision event logs the failing reason codes.

```python
# kernel_tcb/policy/specs.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class Reason:
    code: str
    detail: str

@dataclass(frozen=True)
class SpecResult:
    ok: bool
    reasons: tuple[Reason, ...] = ()

class Spec(Protocol):
    def evaluate(self, ctx: "PolicyContext") -> SpecResult: ...

@dataclass(frozen=True)
class AndSpec:
    left: Spec
    right: Spec
    def evaluate(self, ctx: "PolicyContext") -> SpecResult:
        a = self.left.evaluate(ctx)
        if not a.ok:
            return a
        b = self.right.evaluate(ctx)
        if not b.ok:
            return b
        return SpecResult(ok=True)

@dataclass(frozen=True)
class OrSpec:
    left: Spec
    right: Spec
    def evaluate(self, ctx: "PolicyContext") -> SpecResult:
        a = self.left.evaluate(ctx)
        b = self.right.evaluate(ctx)
        if a.ok or b.ok:
            return SpecResult(ok=True)
        return SpecResult(ok=False, reasons=a.reasons + b.reasons)
```

**Recommended reason codes (examples):**
- `tool_not_allowlisted`
- `args_too_large`
- `resource_not_allowlisted`
- `risk_tier_too_high`
- `approval_required`
- `capability_invalid`
- `binding_hash_mismatch`

**Integration with capability tokens (§12.6):**
- Policy evaluation can return `allow` only by producing a **CapabilityGrant** (tool + args hash + scope + expiry + principal + tenant).
- Tool execution must require the grant token (enforced by the executor), turning policy into a *permit object*.

**Testing discipline:**
- Each spec has unit tests for pass/fail and reason codes.
- “Golden policy bundle” tests compile a real policy file → spec tree → decisions match expectations.



### 12.8 K14 — Secrets broker (scoped, ephemeral credentials; Strategy never sees secrets)

If you intend to run real tools in production, you need a disciplined pattern for credentials:

- Strategy must **never** access secrets.
- Tools must not carry long-lived keys in args or environment “just because it’s convenient.”
- Credential access must be **scoped**, **audited**, and **rotatable** by design.

The kernel-friendly answer is a **SecretsBroker** port that issues short-lived, tool-scoped credentials.

#### Secrets broker port

```python
# kernel_tcb/security/secrets.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Protocol

class CredentialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: str
    scopes: list[str] = Field(default_factory=list)  # e.g. ["github:read", "s3:write:bucketA"]
    ttl_sec: int = 900

    run_id: str
    tenant_id: str | None
    principal: str

    # Defense in depth: broker may re-verify capability token (K5/K14).
    capability_token: str | None = None

class IssuedCredential(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    credential_id: str
    expires_at_epoch: int
    # Arbitrary opaque credential material. Never log. Never include in audit payload.
    creds: dict[str, str] = Field(default_factory=dict)

class SecretsBroker(Protocol):
    broker_id: str
    def issue(self, req: CredentialRequest) -> IssuedCredential: ...
```

#### How it integrates (minimum viable)

- Add `required_scopes` to `ToolSpec` (see §11.1).
- `ToolExecutor.execute()` requests credentials from `SecretsBroker` when:
  - `ToolSpec.required_scopes` is non-empty, and
  - execution is not replay mode.

**Fail closed:** if a tool requires scopes but no broker is configured, execution must fail.

#### Audit and privacy requirements (don’t skip these)

The broker must emit audit events (via `AuditLedger`) such as:

- `secrets.issued` — include `credential_id`, `tool_name`, `scopes` (or their hash), `expires_at_epoch`, `tenant_id`, `principal`
- `secrets.denied` — include reason code (e.g., `scope_not_allowlisted`, `capability_missing`, `tenant_blocked`)

Do **not** include raw credential material in audit logs.

#### Rotation and “no long-lived keys” stance

Prefer mechanisms that naturally issue ephemeral credentials (examples):
- cloud identity federation (STS-style short-lived tokens),
- mTLS client certs with short validity,
- Vault dynamic secrets.

If you must use static secrets early, keep them behind the broker and set low TTL session tokens on top.

#### Resilience wiring

Treat the broker as an external dependency:
- dependency key: `secrets:primary`
- wrap with bulkhead + breaker + timeout via EffectRunner middleware (§9.5)
- on outage: fail tool exec deterministically (`DependencyUnavailable`) and rely on outbox/DLQ policies where appropriate

#### Release gates (minimum)

Add tests that prove:
- Strategy never receives secrets (no secret fields in StrategyContext / observations).
- Tools that declare `required_scopes` cannot execute without a capability token and broker issuance.
- Secrets are never present in `AuditEvent.payload` (scan for common key names or patterns).


## 13. K10 — Outbox (durable intent log for side effects)

A stronger outbox stores **result/error** as well as status.

```python
# kernel_tcb/persistence/outbox_sqlite.py
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Literal

Status = Literal["pending", "in_flight", "delivered", "failed_retryable", "dead_lettered"]

@dataclass(frozen=True)
class OutboxRecord:
    idempotency_key: str
    run_id: str
    tool_name: str
    canonical_args_json: str
    status: Status

    # retry / quarantine metadata (DLQ-ready)
    retry_count: int = 0
    max_retries: int = 8
    next_attempt_at: float = 0.0

    last_error_code: str | None = None
    last_error_json: str | None = None
    last_error_at: float | None = None

    result_json: str | None = None

    dead_lettered_at: float | None = None
    dead_letter_reason: str | None = None

class Outbox:
    def __init__(self, conn: sqlite3.Connection):
        self._c = conn
        self._c.execute(
            "CREATE TABLE IF NOT EXISTS outbox ("
            " idempotency_key TEXT PRIMARY KEY,"
            " run_id TEXT NOT NULL,"
            " tool_name TEXT NOT NULL,"
            " canonical_args_json TEXT NOT NULL,"
            " status TEXT NOT NULL,"
            " retry_count INTEGER NOT NULL,"
            " max_retries INTEGER NOT NULL,"
            " next_attempt_at REAL NOT NULL,"
            " last_error_code TEXT,"
            " last_error_json TEXT,"
            " last_error_at REAL,"
            " result_json TEXT,"
            " dead_lettered_at REAL,"
            " dead_letter_reason TEXT"
            ")"
        )
        self._c.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status_next ON outbox(status, next_attempt_at)")
        self._c.commit()

    def begin(self, rec: OutboxRecord) -> bool:
        """Insert if absent. Returns True iff inserted."""
        try:
            self._c.execute(
                "INSERT INTO outbox (idempotency_key, run_id, tool_name, canonical_args_json, status, retry_count, max_retries, next_attempt_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    rec.idempotency_key,
                    rec.run_id,
                    rec.tool_name,
                    rec.canonical_args_json,
                    rec.status,
                    rec.retry_count,
                    rec.max_retries,
                    rec.next_attempt_at,
                ),
            )
            self._c.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def mark_delivered(self, *, idempotency_key: str, result_json: str) -> None:
        self._c.execute(
            "UPDATE outbox SET status='delivered', result_json=?, last_error_code=NULL, last_error_json=NULL, last_error_at=NULL WHERE idempotency_key=?",
            (result_json, idempotency_key),
        )
        self._c.commit()

    def mark_failed_retryable(self, *, idempotency_key: str, error_code: str, error_json: str, backoff_sec: float) -> None:
        now = time.time()
        self._c.execute(
            "UPDATE outbox SET status='failed_retryable', retry_count=retry_count+1, last_error_code=?, last_error_json=?, last_error_at=?, next_attempt_at=? "
            "WHERE idempotency_key=?",
            (error_code, error_json, now, now + backoff_sec, idempotency_key),
        )
        self._c.commit()

    def dead_letter(self, *, idempotency_key: str, reason: str, error_code: str, error_json: str) -> None:
        now = time.time()
        self._c.execute(
            "UPDATE outbox SET status='dead_lettered', dead_lettered_at=?, dead_letter_reason=?, last_error_code=?, last_error_json=?, last_error_at=? "
            "WHERE idempotency_key=?",
            (now, reason, error_code, error_json, now, idempotency_key),
        )
        self._c.commit()
```





### 13.1 Dead Letter Queue (DLQ) + retry/backoff discipline

Production outboxes must support **bounded retries** and **quarantine**. Otherwise a single “poison” side effect can thrash workers forever, hide real outages, and (worse) create unsafe repeated side effects.

**Minimum schema contract** (already reflected in the `OutboxRecord` above):

- `retry_count`, `max_retries`
- `next_attempt_at` (for backoff + scheduling)
- `last_error_code`, `last_error_json`, `last_error_at`
- `dead_lettered_at`, `dead_letter_reason`
- `status ∈ {pending, in_flight, delivered, failed_retryable, dead_lettered}`

**Retry classifier (deterministic):**

- **Retryable** (bounded): network timeouts, dependency 429, dependency 5xx, transient DB failures.
- **Non-retryable** (fail fast → DLQ): policy denied, invalid capability token, approval binding mismatch, schema violation, invariant violation, dependency 4xx (except 429) unless explicitly allowlisted.

**Backoff policy (default):**
- exponential with jitter, capped (e.g., 0.5s → 60s), but *jitter generation must be deterministic in tests* (seeded RNG provided by the kernel runtime).

**Quarantine / DLQ behavior:**
- Once `retry_count >= max_retries`, the item is **dead-lettered** and must never be executed again automatically.
- Dead-lettering emits:
  - `outbox.dead_lettered` (audit) with `idempotency_key`, `tool_name`, `error_code`, `reason`.
- Operators can “requeue” only via an explicit admin path that:
  - emits `outbox.requeued` (audit),
  - preserves idempotency semantics (no silent duplication),
  - requires a principal and justification.

**Alerting + SLOs (required):**
- Metrics:
  - `outbox_pending_total{tool_name}`
  - `outbox_retry_total{tool_name,error_code}`
  - `outbox_dead_letter_total{tool_name,reason}`
  - `outbox_oldest_pending_seconds`
- Page on:
  - sustained dead-letter rate,
  - oldest pending over threshold,
  - spikes in a single error code/tool.

**Optional hardening (recommended): poison-message acceleration**
- If the same `error_code` repeats N times (e.g., schema_violation), dead-letter early (don’t waste retries).


### 13.2 Saga pattern (multi-step commits with compensations)

Use a saga when a “single user action” produces **multiple external side effects** that must remain coherent under partial failure.

Classic examples:
- reserve inventory → charge payment → create shipment
- create ticket → update CRM → notify customer

There is no true distributed transaction here. The goal is:
- **idempotent progress**, persisted step-by-step,
- **compensations** when a later step fails,
- deterministic **crash/resume** that continues from the recorded saga state.

#### When you need a saga (rule of thumb)

Use a saga if:
- you have 2+ side-effecting tool commits that must be “all-or-compensate”, and
- the downstream systems do not provide a single atomic API that covers the whole intent.

If you cannot define a meaningful compensation, you can still run a “non-compensatable saga” but you must:
- mark it as such in policy,
- alert on partial failure,
- provide a manual remediation path.

#### Deterministic saga state machine (KernelCore-owned)

Model saga progress inside KernelCore (pure-ish) so it is replayable:

```python
# kernel_tcb/sagas/abi.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

@dataclass(frozen=True)
class SagaStep:
    name: str
    do_tool: str
    do_args: dict[str, Any]
    compensate_tool: Optional[str] = None
    compensate_args: Optional[dict[str, Any]] = None

@dataclass
class SagaState:
    saga_id: str
    step_index: int = 0
    completed: list[str] = None
    status: str = "running"   # running|compensating|done|failed

    def __post_init__(self):
        if self.completed is None:
            self.completed = []
```

KernelCore emits effects for the next step (or compensation) based on `SagaState` and tool results.

#### Outbox integration (idempotent step commits)

Each saga step is a **separate outbox record** with its own idempotency key.

Recommended idempotency key template:

```
saga:{saga_id}:step:{step_name}:phase:{do|compensate}
```

This guarantees:
- crash between “record intent” and “execute tool” does not duplicate side effects,
- retries remain bounded and safe.

#### Compensation flow (reverse order)

On failure at step N:
1) transition saga to `compensating`
2) emit compensation effects for steps `N-1 ... 0` (only for steps recorded as committed)
3) if all compensations succeed → saga ends `failed` (original intent failed, but we cleaned up)
4) if a compensation fails → saga ends `failed` and raises an alert (manual remediation required)

#### Policy + capability tokens (no bypass)

Each `do` and `compensate` tool execution still goes through:
- preview/allow/approve (as configured),
- capability minting,
- token verification at ToolExecutor.

Compensations should typically be pre-authorized by policy for the saga type (otherwise you can’t roll back in emergencies).

#### Minimum saga events (if event-sourcing is enabled)

If you adopt §13.3 event sourcing, include explicit saga events:
- `saga_started {saga_id, steps_hash}`
- `saga_step_committed {saga_id, step_name, outbox_key}`
- `saga_step_failed {saga_id, step_name, error}`
- `saga_compensation_committed {saga_id, step_name, outbox_key}`
- `saga_completed {saga_id, status}`

This makes time-travel debugging and post-incident analysis actually usable.


### 13.3 Optional: event-sourced run state (append-only stream + snapshots)

If you want the “single coherent story” property:

- *What happened?* → events  
- *What is the state?* → fold(events)  
- *Can we reproduce?* → replay(events + recorded I/O)

…implement a per-run event stream in persistence.

**Rule:** the event stream is append-only; state is derived. Snapshots are an optimization.

#### Minimal SQLite event store (reference)

```python
# kernel_tcb/persistence/event_store_sqlite.py
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Iterable

from kernel_tcb.tools.canonical import canonical_json, stable_hash

@dataclass(frozen=True)
class RunEvent:
    run_id: str
    seq: int
    ts_epoch: float
    event_type: str
    payload: dict[str, Any]
    payload_hash: str

class EventStore:
    def __init__(self, conn: sqlite3.Connection):
        self._c = conn
        self._c.execute(
            "CREATE TABLE IF NOT EXISTS run_events ("
            " run_id TEXT NOT NULL,"
            " seq INTEGER NOT NULL,"
            " ts_epoch REAL NOT NULL,"
            " event_type TEXT NOT NULL,"
            " payload_json TEXT NOT NULL,"
            " payload_hash TEXT NOT NULL,"
            " PRIMARY KEY (run_id, seq)"
            ")"
        )
        self._c.execute("CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON run_events(run_id, seq)")
        self._c.execute(
            "CREATE TABLE IF NOT EXISTS run_snapshots ("
            " run_id TEXT PRIMARY KEY,"
            " last_seq INTEGER NOT NULL,"
            " state_json TEXT NOT NULL,"
            " state_hash TEXT NOT NULL"
            ")"
        )

    def append(self, *, run_id: str, event_type: str, payload: dict[str, Any]) -> RunEvent:
        ts = time.time()
        payload_json = canonical_json(payload)
        ph = stable_hash("run_event_payload", {"event_type": event_type, "payload": payload})
        seq = self._next_seq(run_id)

        self._c.execute(
            "INSERT INTO run_events (run_id, seq, ts_epoch, event_type, payload_json, payload_hash) VALUES (?,?,?,?,?,?)",
            (run_id, seq, ts, event_type, payload_json, ph),
        )
        self._c.commit()
        return RunEvent(run_id=run_id, seq=seq, ts_epoch=ts, event_type=event_type, payload=payload, payload_hash=ph)

    def iter_events(self, *, run_id: str, after_seq: int = 0) -> Iterable[RunEvent]:
        rows = self._c.execute(
            "SELECT run_id, seq, ts_epoch, event_type, payload_json, payload_hash "
            "FROM run_events WHERE run_id=? AND seq>? ORDER BY seq ASC",
            (run_id, after_seq),
        )
        for run_id, seq, ts, et, pj, ph in rows:
            yield RunEvent(run_id=run_id, seq=seq, ts_epoch=ts, event_type=et, payload=json.loads(pj), payload_hash=ph)

    def save_snapshot(self, *, run_id: str, last_seq: int, state: dict[str, Any]) -> None:
        sj = canonical_json(state)
        sh = stable_hash("run_state_snapshot", {"last_seq": last_seq, "state": state})
        self._c.execute(
            "INSERT INTO run_snapshots (run_id, last_seq, state_json, state_hash) "
            "VALUES (?,?,?,?) "
            "ON CONFLICT(run_id) DO UPDATE SET last_seq=excluded.last_seq, state_json=excluded.state_json, state_hash=excluded.state_hash",
            (run_id, last_seq, sj, sh),
        )
        self._c.commit()

    def load_snapshot(self, *, run_id: str) -> tuple[int, dict[str, Any]] | None:
        row = self._c.execute(
            "SELECT last_seq, state_json, state_hash FROM run_snapshots WHERE run_id=?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        last_seq, state_json, state_hash = row
        state = json.loads(state_json)
        expected = stable_hash("run_state_snapshot", {"last_seq": last_seq, "state": state})
        if expected != state_hash:
            raise ValueError("snapshot_hash_mismatch")
        return int(last_seq), state

    def _next_seq(self, run_id: str) -> int:
        row = self._c.execute("SELECT COALESCE(MAX(seq), 0) FROM run_events WHERE run_id=?", (run_id,)).fetchone()
        return int(row[0]) + 1
```

#### Reducer: derive state by replaying events

Keep event evolution append-only: add new event types and fields; don’t mutate old ones.

```python
# kernel_tcb/persistence/reducer.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from kernel_tcb.orchestrator.fsm import State

@dataclass(frozen=True)
class DerivedRunState:
    fsm_state: State
    step: int
    # add other derived fields (budgets, last tool result hashes, etc.)

def initial_state() -> DerivedRunState:
    return DerivedRunState(fsm_state=State.START, step=0)

def apply_event(s: DerivedRunState, *, event_type: str, payload: dict[str, Any]) -> DerivedRunState:
    if event_type == "fsm_transition":
        return DerivedRunState(fsm_state=State(payload["to"]), step=int(payload["step"]))
    if event_type == "step_incremented":
        return DerivedRunState(fsm_state=s.fsm_state, step=s.step + 1)
    return s  # unknown events are ignored by older code (forward-compat strategy)
```

**Snapshot cadence:** every 25–100 events per run is typical. Snapshots make resume O(tail) instead of O(history).

**Integration note:** you can implement the outbox as:
- a *derived view* of events (“intent recorded”, “intent committed”), or
- a separate table (as shown in §13 (Outbox)) updated transactionally alongside the event append.

Both are fine; choose based on operational comfort.


#### Production storage patterns (pick one early)

SQLite is a fine reference, but production systems should choose an event store that gives you:
- atomic append,
- predictable ordering,
- concurrency control,
- easy retention/backup.

**Option 1 (recommended): Postgres per-run stream**
- Table `run_events(run_id, seq, event_id, ts, event_type, payload_json, prev_hash, hash, schema_version, producer_version)`
- Primary key `(run_id, seq)` ensures a total order per run.
- Add `run_heads(run_id, next_seq)` to allocate seq safely.

Allocation pattern (transactional, sketch):
1) `SELECT next_seq FROM run_heads WHERE run_id=? FOR UPDATE`
2) `UPDATE run_heads SET next_seq = next_seq + 1 ... RETURNING old_next_seq AS seq`
3) `INSERT INTO run_events(run_id, seq, ...) VALUES (...)`
4) optional: snapshot/outbox updates in the same transaction.

**Option 2: Log system (Kafka) + snapshot store**
- Great for scale, but more moving parts (exactly-once semantics are a lifestyle choice).
- You’ll still want a transactional snapshot store keyed by `run_id`.

**Option 3: Cloud KV (DynamoDB)**
- Works well with `(PK=run_id, SK=seq)`; careful with hot partitions and conditional writes.

#### Event evolution rules (non-negotiable if you want replay)

- Every event carries `schema_version` (integer) and `producer_version` (semver).
- Backwards compatible additions only:
  - **add fields** with defaults,
  - **add new event types**,
  - never delete/rename fields in existing event types.
- Reducers must ignore unknown fields and (optionally) unknown event types (forward-compat).

#### Concurrency and ordering: make it impossible to “double step”

Even if your runtime intends “one worker per run,” enforce correctness at persistence:

- Enforce `(run_id, seq)` uniqueness.
- Use a transactional seq allocator (don’t do `MAX(seq)+1` under concurrency).
- Treat “unexpected seq” as a hard error (`concurrent_step_detected`).

This prevents subtle bugs where two orchestrators race and both think they own the next step.

#### Privacy and retention

Event sourcing is incredibly debuggable…and therefore incredibly good at retaining things you didn’t mean to retain.

- Keep raw user text out of events (store hashes or references to sanitized blobs).
- Apply redaction rules **before** event append.
- Document retention + deletion behavior per tenant/run_id.

---

## 14. K7 — Verifiers (independent veto)

```python
# kernel_tcb/verify/ports.py
from __future__ import annotations
from typing import Protocol
from pydantic import BaseModel, ConfigDict

class VerifyResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ok: bool
    reason: str | None = None
    detail: dict = {}

class Verifier(Protocol):
    verifier_id: str
    def verify(self, *, run_id: str, artifacts: dict) -> VerifyResult: ...
```



### 14.1 VerifierChain composition (independent veto, composable safety checks)

A single `Verifier` interface is a start, but the K7 intent is **multiple independent verifiers**, each able to veto.

Use a chain/composite pattern:

- each verifier is small and owns one concern (PII leak check, prompt injection check, tool-arg constraints, tenant policy invariants),
- the chain aggregates results and fails closed on the first veto (or collects all vetoes, your choice),
- verifier versions are recorded in the bundle manifest (K16-min).

#### Typed verifier input

```python
# kernel_tcb/verify/chain.py
from __future__ import annotations
from typing import Protocol, Literal
from pydantic import BaseModel, ConfigDict, Field

from kernel_tcb.verify.ports import VerifyResult, Verifier

class VerifierInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    artifact_type: Literal["tool_intent","tool_result","run_summary"]
    payload: dict = Field(default_factory=dict)

class VerifierChain:
    def __init__(self, verifiers: list[Verifier]):
        self._verifiers = verifiers

    def verify(self, *, run_id: str, inp: VerifierInput) -> VerifyResult:
        for v in self._verifiers:
            r = v.verify(run_id=run_id, artifacts={
                "artifact_type": inp.artifact_type,
                "payload": inp.payload,
                "verifier_id": v.verifier_id,
            })
            if not r.ok:
                # Attach the vetoing verifier id for observability.
                detail = dict(r.detail or {})
                detail["verifier_id"] = v.verifier_id
                return VerifyResult(ok=False, reason=r.reason, detail=detail)
        return VerifyResult(ok=True, reason=None, detail={})
```

#### Where verifiers run

At minimum:
- **Before capability issuance / tool commit** (most important): veto unsafe actions.
- Optionally after tool result: veto or redact unsafe outputs before Strategy sees them.

**Hard rule:** verifiers must not have privileged access that Strategy lacks.  
If a verifier needs model/tool calls, those calls must be modeled as effects and recorded (K11), and must respect budgets (K6).

#### Wiring recommendation

- `ReferenceMonitor.commit()` calls `VerifierChain.verify(...)` on `artifact_type="tool_intent"` before approval/capability issuance.
- Record veto events (`verifier_veto`) into the audit ledger with structured reason codes.

---


---

## 15. K13 — Memory governance (privileged subsystem)

```python
# kernel_tcb/memory/abi.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class MemoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    record_id: str
    classification: Literal["L0","L1","L2","L3"]
    ttl_seconds: int
    provenance: dict
    payload: dict

class MemoryWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tenant_id: str | None
    principal: str
    record: MemoryRecord

class MemoryWriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ok: bool
    error: dict | None = None

class MemoryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tenant_id: str | None
    principal: str
    query: dict

class MemoryReadResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ok: bool
    records: list[MemoryRecord] = Field(default_factory=list)
    error: dict | None = None
```

---

## 16. K11 — Record/replay (reproducibility)

```python
# kernel_tcb/replay/ports.py
from __future__ import annotations
from typing import Protocol
from kernel_tcb.model.abi import ModelRequest, ModelResponse
from kernel_tcb.tools.ports import ToolResult

class Recorder(Protocol):
    def record_model(self, *, run_id: str, req: ModelRequest, resp: ModelResponse) -> None: ...
    def record_tool(self, *, run_id: str, tool_name: str, args: dict, result: ToolResult) -> None: ...

class Replayer(Protocol):
    def replay_model(self, *, run_id: str, req: ModelRequest) -> ModelResponse: ...
    def replay_tool(self, *, run_id: str, tool_name: str, args: dict) -> ToolResult: ...
```

---

## 17. K12/K12a — Evaluation harness (behavior + artifacts)

### 17.1 Eval harness behaviors (practical)

Evals run the kernel in a deterministic scenario mode:
- tools can be mocked or replayed,
- model calls can be replayed or pinned (recorded responses),
- privileged side effects are disabled unless the test explicitly exercises approval/commit logic.

Every test case should be able to assert:
- required trace events occurred,
- no forbidden events occurred,
- policy outcomes match expected (allow/deny/escalate),
- constraint violations are zero for gated suites.

### 17.2 Standard eval output artifacts (recommended)

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
  - diff vs previous run,
  - links to the worst failing traces.

This makes evals usable as evidence in reviews.

---

## 18. Debugging playbook (mechanical, not mystical)

When something goes wrong, make the workflow boring:

1) Get identifiers  
   `run_id`, `trace_id`, `bundle_id`, principal, tenant_id.

2) Inspect the trace  
   Find the first failure event (`policy_denied`, `tool_error`, `verification_failed`, `budget_exceeded`).  
   Identify the state node and the observation that triggered it.

3) Replay deterministically (K11)  
   Run in `mode=replay` with recorded model/tool I/O.  
   Confirm the failure reproduces with **zero external calls**.

4) Narrow the fault  
   - policy denied → inspect policy bundle + constraints; add a policy unit test
   - tool failed → inspect tool adapter error; add a fault-injection case
   - verifier failed → inspect verifier logs; add a regression eval case

5) Promote to regression  
   Every incident class becomes a new eval case (scenario or adversarial).

---

## 19. K16-min — Bundle manifests (record what is running)

Even early, implement a thin K16-min slice:

- compute `bundle_id` from hashes of:
  - tool manifest
  - policy bundle
  - prompt bundle
  - verifier versions
  - schema/ABI version
  - (if gated) eval suite versions

- write `bundle_id` into every run header and trace.

```python
# kernel_tcb/change_mgmt/bundle.py
from __future__ import annotations
from kernel_tcb.abi.base import ABIModel

class BundleManifest(ABIModel):
    schema_version: str
    tool_manifest_hash: str
    policy_bundle_hash: str
    prompt_bundle_hash: str
    verifier_bundle_hash: str
    eval_bundle_hash: str | None = None

    def bundle_id(self) -> str:
        return self.stable_hash(domain="bundle_manifest")
```

---

## 20. Recommended refactor: what to move out of the Adoption Guide

Move these sections out of the Adoption Guide and into this Implementation Playbook:

- Repo architecture + import-lint patterns (Adoption §5)
- Concrete Python patterns / code snippets (Adoption §6)
- Concrete implementation sequence + eval/debug artifacts (Adoption §9)
- Appendices with code templates (policy bundle skeleton, assurance template, invariant test index)

Keep the Adoption Guide focused on:
- maturity levels, adoption matrix, build order DAG,
- governance minimums and exit criteria per level,
- “when” decisions, not “how” code.

---


## 21. Proof suite and release gates (turn kernel claims into tests)

This section exists because “we built it correctly” is not a property you can deploy.

A production-grade agent kernel should have a small set of **must-pass proofs** that demonstrate the *kernel invariants are mechanically enforced*.

### 21.1 Must-pass end-to-end proofs

#### Proof A — Deterministic replay (no external calls)

Goal: prove that a recorded run can be replayed deterministically and produces the same derived state.

- Run in **record mode** with real model/tool adapters (or deterministic fakes).
- Persist:
  - model requests/responses (hashed + redacted),
  - tool previews/executions (hashed + redacted),
  - run events / audit.
- Replay in **replay mode**:
  - EffectRunner must refuse any “live” adapter calls.
  - State fold at end must match (state hash equality).
  - Outbox must not enqueue new side effects.

Required tests:
- `test_replay_produces_same_state_hash`
- `test_replay_blocks_external_calls`

#### Proof B — Token-gated execution (complete mediation)

Goal: prove that side-effecting tools **cannot execute** without a valid capability token.

- Attempt tool execute without token → must fail closed.
- Attempt tool execute with token but wrong args hash → must fail closed.
- Attempt tool execute with expired token → must fail closed.

Required tests:
- `test_tool_execute_requires_capability_token`
- `test_capability_args_hash_mismatch_denied`
- `test_capability_expired_denied`

#### Proof C — Approval binding (TOCTOU-safe)

Goal: prove “approved preview” cannot be swapped at commit time.

- Preview tool call (canonical args hash A) → policy returns `needs_approval`.
- Approve preview → capability minted bound to hash A.
- Try to commit with args hash B → must fail closed.

Required test:
- `test_approval_binding_hash_enforced`

#### Proof D — Crash/resume idempotency (no duplicate side effects)

Goal: prove a crash between “intent recorded” and “tool executed” does not duplicate side effects.

Scenario (classic):
1) Reserve outbox intent (durable).
2) Crash before tool execution ack is persisted.
3) Resume → kernel should either:
   - detect the intent was already executed (idempotency), or
   - execute exactly once with the same idempotency key.

Required tests:
- `test_resume_does_not_duplicate_side_effect`
- `test_outbox_idempotency_key_stable_across_retries`


#### Proof E — Outbox DLQ (bounded retries + quarantine)

Goal: prove the outbox cannot retry forever and that toxic side effects become **operable** rather than **infinite background pain**.

Scenario:
- Configure a deterministic failing tool adapter that returns:
  - a retryable failure for repeated attempts (e.g., `dependency_timeout`),
  - a non-retryable failure (e.g., `schema_violation` / `capability_invalid`).

Assertions:
- Retryable failures:
  - increment `retry_count`,
  - schedule `next_attempt_at` with backoff,
  - stop after `max_retries` and transition to `dead_lettered`.
- Non-retryable failures:
  - transition to `dead_lettered` immediately (fail closed).
- Dead-lettered records:
  - are never executed automatically again,
  - emit `outbox.dead_lettered` audit events with reason codes.

Required tests:
- `test_outbox_retries_are_bounded_and_dead_lettered`
- `test_non_retryable_errors_dead_letter_immediately`
- `test_dead_lettered_items_are_not_executed`

#### Proof F — Audit read path + verify_chain (usable and verifiable audit)

Goal: prove audit is not just “write-only vibes.”

Scenario:
- Run a normal execution emitting multiple audit events (policy decisions, effects, tool commits).
- Read via `query(run_id, after_seq)` pagination and assert ordering is stable.
- Run `verify_chain(run_id)` and assert `ok=True`.

Tamper test:
- Flip one stored audit payload field (simulated corruption or malicious edit).
- Assert `verify_chain(run_id)` returns `ok=False` and points to the first bad sequence.

Required tests:
- `test_audit_query_paginates_in_order`
- `test_audit_verify_chain_passes`
- `test_audit_verify_chain_detects_tamper`


### 21.2 CI/CD release gates (minimum bar)

A sane default pipeline:

- **Static gates:**
  - ruff + mypy strict
  - import-linter contracts (core purity; strategy boundary)
  - dependency audit (e.g., `pip-audit`) for critical CVEs
- **Unit tests:** fast, deterministic; run on every PR
- **Integration tests:** include at least one live tool adapter in a sandbox environment
- **Proof suite (§21.1):** required before merge to main and before release

### 21.3 Fault injection (chaos, but targeted)

These tests are cheap and catch real incidents early:

- Outbox poison item (non-retryable invariant violation) → immediate DLQ; no worker thrash.
- Audit store corruption simulation → `verify_chain` trips and identifies first bad seq.
- Summary signing key rotation → new `kid` verifies; old runs still verifiable with old keys.

- Kill strategy process mid-propose → kernel fails closed, run is resumable.
- Policy engine timeout/unavailable → default deny; run pauses or fails safe (per config).
- Tool adapter timeout → outbox retry behavior matches policy; no duplicate side effects.
- Persistence transient failure during append → run resumes without state corruption.
- Clock skew simulation → token expiry logic tolerates allowed skew; fails closed beyond it.

### 21.4 Security regression cases (prompt injection and “weird inputs”)

Add regression cases for:
- Untrusted content attempting to add tool calls (“ignore instructions and do X”).
- Oversized observations and truncated content behavior (fail closed, logged).
- Strategy returning unknown fields / malformed proposals (schema reject).
- Tool args canonicalization edge cases (ordering, floats, unicode normalization).

The vibe you’re aiming for: **the system refuses weirdness by construction, not by heroism.**


### 21.5 Operational resilience + extensibility proofs (recommended for production)

These aren’t “nice to have.” They stop the common production incidents: cascading failure, stuck capacity, and unsafe extension drift.

#### Proof G — Global tamper evidence (signed run summaries + global chain)

Goal: detect run deletion/replacement and produce portable evidence.

Scenario:
- Complete two runs and record:
  - signed run summaries (`kid`, signature),
  - appended global chain records.

Assertions:
- Summary signature verifies under the `kid`.
- Global chain verifies end-to-end (`prev_global_hash` links).
- If anchoring is enabled, anchored head matches computed head for the same interval.

Deletion detection:
- Remove one summary or one global chain record (simulated tamper).
- Assert verification fails.

Required tests:
- `test_run_summary_signature_verifies`
- `test_global_chain_verifies`
- `test_global_chain_detects_deletion_or_gap`



#### Proof H — Circuit breaker behavior (trip, short-circuit, recover)

Goal: prove the system *stops calling* a failing dependency and recovers predictably.

Scenario:
- Configure a tool adapter to fail N times.
- Verify:
  - breaker transitions to `open`,
  - subsequent calls are short-circuited (no adapter invocation),
  - after `reset_timeout_sec`, breaker enters `half_open`,
  - after M successes, breaker closes.

Required tests:
- `test_circuit_breaker_opens`
- `test_circuit_breaker_short_circuits_calls`
- `test_circuit_breaker_recovers_half_open_to_closed`

#### Proof I — Bulkhead isolation (no cascading starvation)

Goal: prove one saturated dependency cannot starve unrelated kernel work.

Scenario:
- Saturate `tool:A` bulkhead (max_concurrency reached).
- Verify:
  - `tool:B` calls still execute,
  - audit/checkpoint writes still proceed,
  - overloaded calls fail fast with typed overload errors (no unbounded queue growth).

Required tests:
- `test_bulkhead_isolates_tools`
- `test_bulkhead_overload_fails_fast`
- `test_model_and_tool_pools_are_isolated` (if you have separate pools)

#### Proof J — Saga compensation (partial failure produces compensations)

Goal: prove multi-step actions remain coherent under failure.

Scenario:
- Run a saga with 3 steps; force step 2 to fail after step 1 commits.
- Verify:
  - step 1 outbox record is committed,
  - compensation for step 1 is executed and recorded,
  - saga ends in `failed` with a clear event trail,
  - resume does not duplicate either the original side effect or the compensation.

Required tests:
- `test_saga_compensates_on_failure`
- `test_saga_resume_is_idempotent`

#### Proof K — Extension contract tests (plugins don’t widen the trust boundary)

Goal: prove new tools/verifiers can be added without breaking invariants.

Scenario:
- Load a tool pack via registry.
- Verify:
  - schema validation rejects invalid args,
  - canonicalization is stable,
  - capability tokens are required for commits,
  - record/replay mode blocks live calls.

Required tests:
- `test_tool_pack_contract_suite`
- `test_extension_loading_rejects_duplicate_names`
- `test_extension_does_not_import_tcb_forbidden_modules` (static guard)


#### Proof L — Middleware coverage (no bypass of resilience + governance)

Goal: prove that **all external calls** are executed through the EffectRunner middleware lane (§9.5), so you can’t “forget” breakers/bulkheads/timeouts on a new dependency.

Scenario:
- Install a `TripwireMiddleware` that sets a contextvar (e.g. `in_effect_lane=True`).
- Wrap each external adapter/client with a stub that asserts the contextvar is set:
  - model provider(s),
  - tool adapter(s),
  - approval service,
  - secrets broker,
  - persistence/audit repositories (if remote).
- Execute a scenario run that triggers each effect kind at least once:
  - `call_model`
  - `tool_preview`
  - `tool_execute`
  - `approval_wait`
  - `persist_checkpoint`
  - `audit_emit`
  - `outbox_enqueue`
  - `secrets_issue`
- Verify that no external call can occur without the contextvar being present.

Required tests:
- `test_external_calls_require_effect_middleware_lane`
- `test_dependency_key_convention_is_stable` (guards breaker/bulkhead key drift)
- `test_approval_and_secrets_calls_use_middleware` (targets the most commonly-forgotten paths)

Why this matters:
- It converts “we intended circuit breakers/bulkheads everywhere” into an enforceable property.
- It prevents subtle regressions when a new port is introduced or a helper calls a client directly.


---

## Appendix A — Policy bundle skeleton (data-only)

```yaml
# policies/default/policy.yaml
policy_version: v1
default: deny

approval_expiry_sec: 300

rules:
  - tool_name: send_email
    mode: write
    requires_approval: true
    constraints:
      allowed_recipients: ["*@example.com"]
      max_body_chars: 4000

  - tool_name: search_docs
    mode: read
    requires_approval: false
    constraints:
      max_query_chars: 200
```

---

## Appendix B — Kernel invariants test index (template)


This is the “index card” version. The full must-pass proofs are in §21.

**Recommended minimum test set (by invariant):**

- **K1 (canonicalization/hash stability)**
  - `test_stable_hash_is_stable_across_runs`
  - `test_canonical_json_normalizes_ordering`
- **K2 (deterministic orchestrator)**
  - `test_illegal_transition_denied`
  - `test_max_steps_enforced`
  - `test_abort_quarantines_late_results`
- **K3 (model boundary)**
  - `test_prompt_hash_recorded`
  - `test_structured_output_repair_is_bounded`
  - `test_model_timeout_fails_closed`
- **K4 (tool executor)**
  - `test_tool_args_schema_validation`
  - `test_idempotency_key_kernel_generated`
  - `test_tool_timeout_is_typed_error`
  - `test_tool_pack_contract_suite`
- **K5 (policy/reference monitor)**
  - `test_default_deny`
  - `test_two_phase_preview_then_commit`
  - `test_binding_hash_enforced`
- **K6 (budgets/retries/backpressure)**
  - `test_budget_enforced`
  - `test_retry_bounds_enforced`
  - `test_overload_fails_fast`
  - `test_circuit_breaker_opens`
  - `test_circuit_breaker_recovers_half_open_to_closed`
  - `test_bulkhead_isolates_tools`
  - `test_bulkhead_overload_fails_fast`
- **K7 (verifiers)**
  - `test_verifier_veto_blocks_execution`
- **K9 (audit ledger)**
  - `test_redaction_before_write`
  - `test_hash_chain_verifies`
- **K10 (outbox/idempotency)**
  - `test_resume_does_not_duplicate_side_effect`
  - `test_outbox_deduplication`
  - `test_saga_compensates_on_failure`
  - `test_saga_resume_is_idempotent`
- **K11 (record/replay)**
  - `test_replay_blocks_external_calls`
  - `test_replay_produces_same_state_hash`
- **K18 (sanitization/channel separation)**
  - `test_untrusted_content_never_enters_instruction_channel`
  - `test_context_renderer_wraps_untrusted_data`

---

- K1: canonicalization/hash stability
- K2: illegal transition denied; bounded loop; abort semantics
- K3: prompt hash recorded; structured output repair bounded; oversize fails closed
- K4: args validated; idempotency key kernel-generated; timeouts typed
- K5: default deny; two-phase; binding hash; TOCTOU safe
- K6: budgets; retry bounds; circuit breaker; bulkhead isolation
- K7: verifier veto path exercised
- K9: redaction before write; hash chain verifies
- K10: resume does not duplicate side effects; saga step idempotency/compensation
- K18: untrusted content never enters instruction channel

---

**End of playbook.**
