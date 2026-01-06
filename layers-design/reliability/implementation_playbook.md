# Kernel Implementation Playbook
**Status:** Staff-level reference implementation guide for the Kernel Blueprint (TCB)  
**Core language:** Python  
**Version:** v1.0  
**Last updated:** 2026-01-06

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

---

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
    apps/                        # ❌ API server / workers / CLI

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
- policy evaluated at propose-time **and** commit-time.

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
    def run(self, req: KernelRequest, *, strategy: Strategy) -> KernelResponse: ...
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

class ModelCallIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["model_call"] = "model_call"
    prompt_ref: str
    input: dict
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
from pydantic import BaseModel, ConfigDict
from typing import Literal

class LLMMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    role: Literal["system","developer","user","assistant","tool"]
    content: str

def build_messages(*, system: str, developer: str, data_blobs: list[str], user: str) -> list[LLMMessage]:
    msgs: list[LLMMessage] = [
        LLMMessage(role="system", content=system),
        LLMMessage(role="developer", content=developer),
    ]
    for blob in data_blobs:
        msgs.append(LLMMessage(role="user", content=f"[UNTRUSTED_DATA]\n{blob}\n[/UNTRUSTED_DATA]"))
    msgs.append(LLMMessage(role="user", content=user))
    return msgs
```

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

---

## 9. K2 + K6 — Deterministic orchestrator with budgets & cancellation

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
    def execute(self, args: dict, meta: ToolMeta) -> ToolResult: ...
```

```python
# kernel_tcb/tools/executor.py
from __future__ import annotations
from kernel_tcb.tools.manifest import ToolManifest
from kernel_tcb.tools.ports import ToolAdapter, ToolMeta, ToolResult

class ToolExecutor:
    def __init__(self, *, manifest: ToolManifest, adapters: dict[str, ToolAdapter]):
        self._manifest = manifest
        self._adapters = adapters

    def spec(self, tool_name: str):
        return self._manifest.get(tool_name)

    def preview(self, *, tool_name: str, args: dict, meta: ToolMeta) -> ToolResult:
        spec = self._manifest.get(tool_name)
        adapter = self._adapters[tool_name]
        if not spec.supports_preview:
            return ToolResult(ok=True, output={"preview": None})
        return adapter.preview(args, meta)

    def execute(self, *, tool_name: str, args: dict, meta: ToolMeta) -> ToolResult:
        spec = self._manifest.get(tool_name)
        if meta.mode == "replay" and spec.has_side_effects:
            return ToolResult(ok=False, error={"code": "replay_forbids_side_effects"})
        return self._adapters[tool_name].execute(args, meta)
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

```python
# kernel_tcb/policy/engine.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal
from kernel_tcb.policy.decisions import PolicyDecision

Decision = Literal["allow","deny","needs_approval"]

@dataclass(frozen=True)
class PolicyRule:
    tool_name: str
    mode: Literal["read","write"]
    requires_approval: bool
    constraints: dict

class PolicyEngine:
    def __init__(self, *, rules: list[PolicyRule], approval_expiry_sec: int = 300):
        self._rules = {r.tool_name: r for r in rules}
        self._approval_expiry_sec = approval_expiry_sec

    def evaluate(self, *, tool_name: str, args: dict, has_side_effects: bool, risk_tier: str, binding_hash: str) -> PolicyDecision:
        rule = self._rules.get(tool_name)
        if rule is None:
            return PolicyDecision(decision="deny", reason="tool_not_allowlisted", binding_hash=binding_hash)

        if has_side_effects and rule.mode != "write":
            return PolicyDecision(decision="deny", reason="write_tool_not_allowed", binding_hash=binding_hash)

        # Example deterministic constraint
        max_chars = int(rule.constraints.get("max_description_chars", 10_000))
        for v in args.values():
            if isinstance(v, str) and len(v) > max_chars:
                return PolicyDecision(decision="deny", reason="arg_too_large", binding_hash=binding_hash)

        if rule.requires_approval or risk_tier == "high":
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

from kernel_tcb.policy.binding import compute_binding_hash
from kernel_tcb.policy.engine import PolicyEngine
from kernel_tcb.policy.approval_ports import ApprovalPort, ApprovalRequest
from kernel_tcb.tools.executor import ToolExecutor
from kernel_tcb.tools.ports import ToolMeta, ToolResult

class ReferenceMonitor:
    def __init__(self, *, policy: PolicyEngine, approvals: ApprovalPort, tools: ToolExecutor, audit: "AuditLedger"):
        self._policy = policy
        self._approvals = approvals
        self._tools = tools
        self._audit = audit

    def propose(self, *, trace_id, run_id, tool_name: str, args: dict, meta: ToolMeta) -> tuple[dict | None, str, int | None]:
        preview_result = self._tools.preview(tool_name=tool_name, args=args, meta=meta)
        preview = preview_result.output
        binding_hash = compute_binding_hash(tool_name=tool_name, args=args, preview=preview)

        spec = self._tools.spec(tool_name)
        decision = self._policy.evaluate(
            tool_name=tool_name,
            args=args,
            has_side_effects=spec.has_side_effects,
            risk_tier=spec.risk_tier,
            binding_hash=binding_hash,
        )

        self._audit.emit(trace_id=trace_id, run_id=run_id, name="policy_decision", payload={
            "phase": "propose",
            "tool": tool_name,
            "decision": decision.decision,
            "reason": decision.reason,
            "binding_hash": binding_hash,
        })

        if decision.decision == "deny":
            raise PermissionError(decision.reason)

        if decision.decision == "needs_approval":
            self._approvals.request(ApprovalRequest(
                binding_hash=binding_hash,
                tool_name=tool_name,
                preview_redacted=preview,  # redaction omitted in snippet
                expires_at_epoch=decision.expires_at_epoch or 0,
                reason=decision.reason,
            ))

        return preview, binding_hash, decision.expires_at_epoch

    def commit(self, *, trace_id, run_id, tool_name: str, args: dict, meta: ToolMeta, timeout_sec: int = 300) -> ToolResult:
        preview_result = self._tools.preview(tool_name=tool_name, args=args, meta=meta)
        binding_hash = compute_binding_hash(tool_name=tool_name, args=args, preview=preview_result.output)

        spec = self._tools.spec(tool_name)
        decision = self._policy.evaluate(
            tool_name=tool_name,
            args=args,
            has_side_effects=spec.has_side_effects,
            risk_tier=spec.risk_tier,
            binding_hash=binding_hash,
        )

        self._audit.emit(trace_id=trace_id, run_id=run_id, name="policy_decision", payload={
            "phase": "commit",
            "tool": tool_name,
            "decision": decision.decision,
            "binding_hash": binding_hash,
        })

        if decision.decision == "deny":
            raise PermissionError(decision.reason)

        if decision.decision == "needs_approval":
            dec = self._approvals.wait_for_decision(binding_hash=binding_hash, timeout_sec=timeout_sec)
            if dec.decision != "approve":
                raise PermissionError("approval_denied")

        return self._tools.execute(tool_name=tool_name, args=args, meta=meta)
```

---

## 13. K10 — Outbox (durable intent log for side effects)

A stronger outbox stores **result/error** as well as status.

```python
# kernel_tcb/persistence/outbox_sqlite.py
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal

Status = Literal["pending","committed","failed"]

@dataclass(frozen=True)
class OutboxRecord:
    idempotency_key: str
    tool_name: str
    canonical_args_json: str
    status: Status
    result_json: str | None = None
    error_json: str | None = None

class Outbox:
    def __init__(self, conn: sqlite3.Connection):
        self._c = conn
        self._c.execute(
            "CREATE TABLE IF NOT EXISTS outbox ("
            " idempotency_key TEXT PRIMARY KEY,"
            " tool_name TEXT NOT NULL,"
            " canonical_args_json TEXT NOT NULL,"
            " status TEXT NOT NULL,"
            " result_json TEXT,"
            " error_json TEXT"
            ")"
        )

    def begin(self, rec: OutboxRecord) -> bool:
        try:
            self._c.execute(
                "INSERT INTO outbox (idempotency_key, tool_name, canonical_args_json, status) VALUES (?,?,?,?)",
                (rec.idempotency_key, rec.tool_name, rec.canonical_args_json, rec.status),
            )
            self._c.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get(self, idempotency_key: str) -> OutboxRecord | None:
        row = self._c.execute(
            "SELECT idempotency_key, tool_name, canonical_args_json, status, result_json, error_json FROM outbox WHERE idempotency_key=?",
            (idempotency_key,),
        ).fetchone()
        if row is None:
            return None
        return OutboxRecord(*row)

    def mark_committed(self, *, idempotency_key: str, result_json: str) -> None:
        self._c.execute(
            "UPDATE outbox SET status='committed', result_json=?, error_json=NULL WHERE idempotency_key=?",
            (result_json, idempotency_key),
        )
        self._c.commit()

    def mark_failed(self, *, idempotency_key: str, error_json: str) -> None:
        self._c.execute(
            "UPDATE outbox SET status='failed', error_json=?, result_json=NULL WHERE idempotency_key=?",
            (error_json, idempotency_key),
        )
        self._c.commit()
```

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

- K1: canonicalization/hash stability
- K2: illegal transition denied; bounded loop; abort semantics
- K3: prompt hash recorded; structured output repair bounded; oversize fails closed
- K4: args validated; idempotency key kernel-generated; timeouts typed
- K5: default deny; two-phase; binding hash; TOCTOU safe
- K6: budgets; retry bounds; circuit breaker
- K7: verifier veto path exercised
- K9: redaction before write; hash chain verifies
- K10: resume does not duplicate side effects
- K18: untrusted content never enters instruction channel

---

**End of playbook.**
