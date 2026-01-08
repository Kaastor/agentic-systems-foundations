# Design Patterns Taxonomy for Agentic System Kernels

**Status:** Reference guide mapping design pattern families to kernel implementation  
**Companion to:** `implementation_playbook.md`  
**Last updated:** 2026-01-08

> All section references (§) link to `implementation_playbook.md` unless otherwise noted.

---

## Overview

This document catalogs the design patterns used in the kernel implementation, organized by their canonical taxonomies. Each pattern family addresses a different concern:

| Family | Concern | Key Question |
|--------|---------|--------------|
| GoF Behavioral | Object interaction | How do components communicate and delegate? |
| GoF Structural | Object composition | How do we compose objects into larger structures? |
| Enterprise/Integration | Persistence & messaging | How do we handle data, transactions, and integration? |
| Resilience (Stability) | Failure handling | How do we survive dependency failures? |
| Extensibility | Growth without risk | How do we add capabilities without widening the TCB? |
| Security | Authorization & isolation | How do we enforce safety properties mechanically? |

---

## 1. Gang of Four (GoF) Patterns

The classic 1994 classification from Gamma, Helm, Johnson, Vlissides.

### 1.1 Behavioral Patterns

Patterns for object interaction, responsibility distribution, and algorithms.

| Pattern | Purpose | Implementation Reference |
|---------|---------|-------------------------|
| **State (FSM)** | Explicit state machine with allowed transitions | [§9.1](implementation_playbook.md#91-explicit-fsm-no-while-model-says) — `State` enum + `ALLOWED` transition map |
| **Command / Effect** | Encapsulate requests as objects | [§1.4](implementation_playbook.md#14-upgrade-make-the-kernel-a-reducer--effect-interpreter-single-side-effect-pipeline) — `KernelEffect` union type |
| **Interpreter** | Execute effects through a single pipeline | [§1.4](implementation_playbook.md#14-upgrade-make-the-kernel-a-reducer--effect-interpreter-single-side-effect-pipeline) — `EffectRunner.run()` |
| **Strategy** | Interchangeable algorithms/policies | [§5.2](implementation_playbook.md#52-strategy-port-typed-proposals-not-side-effects) — `StrategyPort` protocol |
| **Template Method** | Define skeleton with extension points | [§9.0](implementation_playbook.md#90-recommended-orchestrator-wiring-as-eventeffect-machine) — Orchestrator loop |
| **Observer** | Event notification | [§8](implementation_playbook.md#8-k9--audit-ledger-redaction-at-ingestion--hash-chain) — Audit ledger as event sink |
| **Chain of Responsibility** | Pass requests along a chain | [§14](implementation_playbook.md#14-k7--verifiers-independent-veto) — Verifier chain |

### 1.2 Structural Patterns

Patterns for composing objects into larger structures.

| Pattern | Purpose | Implementation Reference |
|---------|---------|-------------------------|
| **Adapter** | Convert interface to expected form | [§1.2](implementation_playbook.md#12-reference-architecture-ports--adapters-hexagonal) — Tool adapters, model provider adapters |
| **Facade** | Simplified interface to subsystem | [§5.1](implementation_playbook.md#51-kernelruntime-interface) — `KernelRuntime` as public facade |
| **Proxy** | Control access to an object | [§12.5](implementation_playbook.md#125-reference-monitor-complete-mediation) — Reference monitor proxies tool execution |
| **Decorator** | Add behavior dynamically | [§5.3](implementation_playbook.md#53-extension-points-tools-verifiers-policies-middleware--without-breaking-the-boundary) — Effect middleware |
| **Composite** | Tree structures | [§7.4](implementation_playbook.md#74-recommended-contextplan--contextcompiler-typed-prompt-program) — `ContextPlan` with nested items |

### 1.3 Creational Patterns

Patterns for object creation (less prominent in this architecture).

| Pattern | Purpose | Implementation Reference |
|---------|---------|-------------------------|
| **Factory Method** | Delegate instantiation | [§5.3](implementation_playbook.md#53-extension-points-tools-verifiers-policies-middleware--without-breaking-the-boundary) — `ToolRegistration.adapter_factory` |
| **Builder** | Construct complex objects step-by-step | [§7.4](implementation_playbook.md#74-recommended-contextplan--contextcompiler-typed-prompt-program) — `compile_context()` builds `ContextPlan` |

---

## 2. Enterprise / Integration Patterns

From Fowler's *Patterns of Enterprise Application Architecture* (2002) and Hohpe's *Enterprise Integration Patterns* (2003).

### 2.1 Data Source Patterns

| Pattern | Purpose | Implementation Reference |
|---------|---------|-------------------------|
| **Repository** | Abstract data access | *Recommended but not yet implemented* — Extract `RunRepository`, `OutboxRepository` protocols |
| **Unit of Work** | Track changes for atomic commit | [§13](implementation_playbook.md#13-k10--outbox-durable-intent-log-for-side-effects) — Outbox + event store transactions |

### 2.2 Offline Concurrency Patterns

| Pattern | Purpose | Implementation Reference |
|---------|---------|-------------------------|
| **Optimistic Offline Lock** | Detect conflicts at commit | [§12.3](implementation_playbook.md#123-binding-hash-tool--args--preview) — Binding hash detects TOCTOU |
| **Idempotent Receiver** | Handle duplicate messages safely | [§11.2](implementation_playbook.md#112-canonical-args--idempotency-key-kernel-generated) — Kernel-generated idempotency keys |

### 2.3 Distribution Patterns

| Pattern | Purpose | Implementation Reference |
|---------|---------|-------------------------|
| **Remote Facade** | Coarse-grained interface for remote calls | [§1.3](implementation_playbook.md#13-upgrade-make-strategy-actually-untrusted-process-isolation) — Strategy RPC ABI |
| **Data Transfer Object (DTO)** | Serialize data for transfer | [§6](implementation_playbook.md#6-k1--abi-and-stable-hashing) — `ABIModel` with `canonical_json()` |

### 2.4 Session State Patterns

| Pattern | Purpose | Implementation Reference |
|---------|---------|-------------------------|
| **Event Sourcing** | State as fold of events | [§13.2](implementation_playbook.md#132-optional-event-sourced-run-state-append-only-stream--snapshots) — `EventStore` + `apply_event()` reducer |
| **Snapshot** | Optimize event replay | [§13.2](implementation_playbook.md#132-optional-event-sourced-run-state-append-only-stream--snapshots) — `save_snapshot()` / `load_snapshot()` |

### 2.5 Integration Patterns

| Pattern | Purpose | Implementation Reference |
|---------|---------|-------------------------|
| **Transactional Outbox** | Reliable message publishing | [§13](implementation_playbook.md#13-k10--outbox-durable-intent-log-for-side-effects) — `Outbox` with `pending → committed` lifecycle |
| **Saga** | Distributed transaction with compensations | [§13.2](implementation_playbook.md#132-saga-pattern-multi-step-commits-with-compensations) — `SagaState` + compensation flow |
| **Dead Letter Channel** | Quarantine failed messages | [§13.1](implementation_playbook.md#131-dead-letter-queue-dlq--retrybackoff-discipline) — `OutboxRecord` with retry tracking + DLQ |
| **Correlation Identifier** | Track related messages | Throughout — `trace_id`, `run_id`, `effect_id` |

---

## 3. Resilience / Stability Patterns

From Nygard's *Release It!* (2007, 2nd ed. 2018). These prevent cascading failures.

| Pattern | Purpose | Implementation Reference |
|---------|---------|-------------------------|
| **Circuit Breaker** | Stop calling failing dependencies | [§9.4](implementation_playbook.md#94-operational-resilience-in-the-effectrunner-timeouts--retries--breakers--bulkheads) — `CircuitBreaker` with open/half-open/closed states |
| **Bulkhead** | Isolate failure domains | [§9.4](implementation_playbook.md#94-operational-resilience-in-the-effectrunner-timeouts--retries--breakers--bulkheads) — `Bulkhead` with semaphore + fail-fast |
| **Timeout** | Bound wait time | [§11.1](implementation_playbook.md#111-tool-manifest) — `timeout_ms_default` per tool |
| **Retry** | Recover from transient failures | [§3.4](implementation_playbook.md#34-production-hardening-checklist-the-boring-but-saves-you-section) — Bounded retries with jitter |
| **Fail Fast** | Reject early under overload | [§9.4](implementation_playbook.md#94-operational-resilience-in-the-effectrunner-timeouts--retries--breakers--bulkheads) — `BulkheadBusy` exception |
| **Steady State** | Prevent resource exhaustion | [§9.2](implementation_playbook.md#92-budgets-hard-stop) — Budget enforcement |
| **Test Harness** | Fault injection for testing | [§21.3](implementation_playbook.md#213-fault-injection-chaos-but-targeted) — Targeted chaos tests |
| **Shed Load** | Drop work under pressure | [§3.4](implementation_playbook.md#34-production-hardening-checklist-the-boring-but-saves-you-section) — Backpressure + overload errors |
| **Dead Letter Queue** | Quarantine failed messages | [§13.1](implementation_playbook.md#131-dead-letter-queue-dlq--retrybackoff-discipline) — `OutboxRecord` with `dead_lettered_at` + retry tracking |
| **Resilience Façade** | Unified resilience coordination | [§9.4](implementation_playbook.md#94-operational-resilience-in-the-effectrunner-timeouts--retries--breakers--bulkheads) — `ResilienceManager` wrapping breakers + bulkheads |

### Resilience Pattern Interactions

```
Request
   │
   ▼
┌──────────────┐
│   Bulkhead   │──── capacity full ────► BulkheadBusy (fail fast)
└──────────────┘
   │ acquired
   ▼
┌──────────────┐
│Circuit Breaker│──── open ────► CircuitOpen (short-circuit)
└──────────────┘
   │ closed/half-open
   ▼
┌──────────────┐
│   Timeout    │──── exceeded ────► TimeoutError
└──────────────┘
   │ success
   ▼
┌──────────────┐
│    Retry     │──── transient failure ────► retry (bounded)
└──────────────┘
   │ success/permanent failure
   ▼
 Result
```

---

## 4. Extensibility Patterns

Patterns for growing system capabilities without widening the trusted computing base.

| Pattern | Purpose | Implementation Reference |
|---------|---------|-------------------------|
| **Ports & Adapters (Hexagonal)** | Swap implementations freely | [§1.2](implementation_playbook.md#12-reference-architecture-ports--adapters-hexagonal) — Core architecture |
| **Plugin Registry** | Discover and load extensions | [§5.3](implementation_playbook.md#53-extension-points-tools-verifiers-policies-middleware--without-breaking-the-boundary) — `ToolRegistry` |
| **Middleware Pipeline** | Compose cross-cutting concerns | [§5.3](implementation_playbook.md#53-extension-points-tools-verifiers-policies-middleware--without-breaking-the-boundary) — `EffectMiddleware` protocol |
| **Anti-Corruption Layer** | Translate external APIs | [§1.9](implementation_playbook.md#19-extensibility-patterns-grow-capabilities-without-widening-the-tcb) — Adapters for older plugin versions |
| **Strangler Fig** | Incremental migration | [§1.9](implementation_playbook.md#19-extensibility-patterns-grow-capabilities-without-widening-the-tcb) — Route subset to new implementation |
| **Feature Toggle** | Runtime capability switching | [§1.9](implementation_playbook.md#19-extensibility-patterns-grow-capabilities-without-widening-the-tcb) — Feature flags for rollouts |
| **Contract Testing** | Verify extension compatibility | [§5.3](implementation_playbook.md#53-extension-points-tools-verifiers-policies-middleware--without-breaking-the-boundary) + [§21](implementation_playbook.md#21-proof-suite-and-release-gates-turn-kernel-claims-into-tests) — Extension contract tests |

### Extension Point Architecture

```
                    ┌─────────────────────────────────────────┐
                    │              KernelCore (TCB)           │
                    │  • Pure-ish reducer                     │
                    │  • Effect emission only                 │
                    │  • No direct I/O                        │
                    └─────────────────────────────────────────┘
                                       │
                                       │ effects
                                       ▼
┌─────────────┐    ┌─────────────────────────────────────────┐    ┌─────────────┐
│  Middleware │◄───│            EffectRunner                 │───►│  Middleware │
│  (before)   │    │  • Resilience (breakers, bulkheads)     │    │  (after)    │
└─────────────┘    │  • Metrics, tracing                     │    └─────────────┘
                   │  • Calls adapters via ports             │
                   └─────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
            ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
            │ToolRegistry │    │PolicyBundle │    │VerifierPack│
            │  (plugins)  │    │   (data)    │    │  (plugins)  │
            └─────────────┘    └─────────────┘    └─────────────┘
```

---

## 5. Security Patterns

From capability-security literature and OWASP secure design principles.

| Pattern | Purpose | Implementation Reference |
|---------|---------|-------------------------|
| **Capability Token** | Authorization as a possessable object | [§12.6](implementation_playbook.md#126-capability-tokens-capability-based-authorization) — `CapabilityGrant` + `CapabilityTokens` |
| **Reference Monitor** | Complete mediation of all access | [§12.5](implementation_playbook.md#125-reference-monitor-complete-mediation) — `ReferenceMonitor.propose()` / `.commit()` |
| **Taint Tracking** | Track data provenance | [§7.1](implementation_playbook.md#71-sanitized-content-envelope) — `SanitizedContent` with provenance + classification |
| **Least Privilege** | Minimal required permissions | [§1.3.2](implementation_playbook.md#132-strategyhost-least-privilege-enforcement-linux-notes) — Seccomp, cgroups, network deny |
| **Fail Closed** | Deny on error | Throughout — Unknown fields rejected, default deny policy |
| **Defense in Depth** | Multiple enforcement layers | [§1.4.1](implementation_playbook.md#141-make-the-effects-boundary-unbreakable-lint--runtime-guards) — Import-linter + type-level + runtime |
| **Separation of Privilege** | Require multiple conditions | [§12](implementation_playbook.md#12-k5--policy-engine--reference-monitor-two-phase) — Two-phase propose/commit |
| **Complete Mediation** | Check every access | [§12.5](implementation_playbook.md#125-reference-monitor-complete-mediation) — All tool calls through monitor |

### Security Pattern Layering

```
Layer 1: Static Analysis
├── import-linter contracts (core cannot import adapters)
└── mypy strict mode

Layer 2: Type-Level Enforcement
├── ABIModel with extra="forbid"
├── EffectContext only constructible in runner
└── Frozen dataclasses

Layer 3: Runtime Enforcement
├── Capability token verification
├── Binding hash validation (TOCTOU)
├── Policy evaluation at propose AND commit
└── Schema validation on all inputs

Layer 4: Process Isolation
├── Strategy in separate process
├── Seccomp profile
├── Network namespace (no egress)
└── Read-only filesystem
```

---

## 6. Pattern Coverage Matrix

Summary of pattern coverage by kernel subsystem:

| Subsystem | Primary Patterns | Status |
|-----------|------------------|--------|
| **K1 ABI** | DTO, Canonical Form | ✓ Complete |
| **K2 Orchestrator** | State (FSM), Template Method | ✓ Complete |
| **K3 Model Boundary** | Adapter, Facade | ✓ Complete |
| **K4 Tool Executor** | Adapter, Idempotent Receiver | ✓ Complete |
| **K5 Policy/Monitor** | Reference Monitor, Capability, Proxy | ✓ Complete |
| **K6 Budgets** | Steady State, Circuit Breaker, Bulkhead | ✓ Complete |
| **K7 Verifiers** | Chain of Responsibility | ✓ Complete |
| **K9 Audit** | Observer, Event Sourcing | ✓ Complete |
| **K10 Outbox** | Transactional Outbox, Saga, Idempotent Receiver, Dead Letter Queue | ✓ Complete |
| **K11 Replay** | Event Sourcing, Snapshot | ✓ Complete |
| **K18 Sanitization** | Taint Tracking | ✓ Complete |
| **Extensions** | Plugin Registry, Middleware, Contract Testing | ✓ Complete |
| **Resilience** | Circuit Breaker, Bulkhead, Timeout, Retry, Dead Letter Queue | ✓ Complete |

---

## 7. Canonical References

| Book | Year | Focus | Relevant Patterns |
|------|------|-------|-------------------|
| *Design Patterns* (Gamma et al.) | 1994 | GoF patterns | State, Command, Strategy, Adapter, Observer |
| *Patterns of Enterprise Application Architecture* (Fowler) | 2002 | Enterprise patterns | Repository, Unit of Work, Event Sourcing |
| *Enterprise Integration Patterns* (Hohpe, Woolf) | 2003 | Messaging patterns | Saga, Correlation ID, Transactional Outbox, Dead Letter Channel |
| *Release It!* (Nygard) | 2007/2018 | Stability patterns | Circuit Breaker, Bulkhead, Timeout, Fail Fast |
| *Building Microservices* (Newman) | 2015/2021 | Service patterns | Strangler Fig, Anti-Corruption Layer |
| *Designing Data-Intensive Applications* (Kleppmann) | 2017 | Data patterns | Event Sourcing, Idempotency, Exactly-Once |
| *Capability Myths Demolished* (Miller et al.) | 2003 | Security patterns | Capability Token, Reference Monitor |

---

## 8. Patterns Not Yet Implemented

These patterns are recommended for future iterations:

| Pattern | Source | Purpose | Priority |
|---------|--------|---------|----------|
| **Specification** | Evans (DDD) | Composable policy predicates | Medium |
| **Repository** | Fowler | Abstract persistence | Medium |
| **Competing Consumers** | Hohpe | Parallel processing | Low (single-node) |
| **Leader Election** | Distributed systems | Multi-node coordination | Future |
| **Service Mesh** | Cloud Native | Cross-service observability | Future |

---

**End of taxonomy.**
