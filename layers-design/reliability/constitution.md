# The Constitution for Reliable, Constrained, Verified Agentic AI Systems

---

## Preamble

Agentic AI systems extend beyond passive generation into planning, capability use, memory/state, and multi-step execution. This increases utility and expands the risk surface: untrusted inputs can manipulate behavior, and privileged actions can cause real-world harm. Industry security guidance emphasizes least privilege, explicit authorization, segregation of untrusted content, layered defenses, and strong identity governance for agents. ([OWASP Cheat Sheet Series][1])

This Constitution defines a formal standard for building agentic systems that are constrained by design, independently verified, and auditable in operation. Trustworthiness is treated as a **system property** across the AI lifecycle. ([NIST Publications][7])

---

## Section 1: Normative Language and Scope

### 1.1 Requirement Keywords

* **SHALL / SHALL NOT**: mandatory.
* **SHOULD / SHOULD NOT**: strongly recommended; deviations require documented rationale and risk acceptance.
* **MAY**: optional.

### 1.2 Scope

Applies to any system in which an AI-driven component can:

* plan across multiple steps,
* invoke external capabilities (tools/APIs/connectors/code),
* maintain or retrieve memory/state,
* or take actions that read sensitive data or change external state.

### 1.3 Core Definitions

* **Agentic System**: A system that uses an AI component to propose, select, or sequence actions to accomplish goals.
* **Actor**: The decision-making component that proposes actions (LLM or otherwise).
* **Capability**: Any operation that reads data, changes state, or consumes resources.
* **Tool**: A capability exposed via a structured interface.
* **Orchestrator**: Deterministic runtime managing context, invoking the actor, routing capability calls, enforcing budgets, logging.
* **Reference Monitor**: Authoritative enforcement mechanism with complete mediation, tamper resistance, and testability.
* **Policy Engine**: Component that evaluates proposed actions against rules and returns allow/deny/escalate.
* **Trusted Data**: Operator-controlled, integrity-protected.
* **Untrusted Data**: Any external content (user text, retrieval/web, uploads, tool outputs).
* **High-Risk Action**: Irreversible harm, value transfer, secrets/PII disclosure, production mutation, permission changes, external comms, arbitrary code execution.

---

## Article 0: Implementation Independence and Method-Agnosticism

### 0.1 Observable Properties over Techniques

All SHALL requirements are requirements on observable system properties (enforceability, verifiability, auditability, boundedness), not on model technique (prompting, fine-tuning, RL, symbolic planning, etc.).

### 0.2 Equivalent Mechanisms Clause

Named mechanisms (e.g., “orchestrator,” “schema validation”) may be replaced by any alternative that provides equivalent:

* complete mediation for privileged actions,
* least privilege capability access,
* deterministic validation where required,
* independent verification for high-risk outcomes,
* auditability and accountability.

### 0.3 Safety Under Actor Confusion

The system SHALL remain safe even when the actor proposes unsafe actions due to error, adversarial inputs, or distribution shift.

---

## Article I: The Prime Directive of Constrained Agency

### I.1 External Enforcement Over Internal Instruction

1. Actor outputs SHALL be treated as non-authoritative proposals.
2. Prompt text SHALL NOT be considered enforcement.
3. Enforcement SHALL be implemented by the Reference Monitor and Policy Engine external to the actor.

### I.2 Least Privilege by Default

1. The system SHALL grant minimum capabilities required.
2. Permissions SHALL be scoped per capability (read/write separation; resource allowlists).
3. Separate capability sets SHALL exist for different trust levels (user-facing vs internal), and sensitive operations SHALL require explicit authorization. ([OWASP Cheat Sheet Series][1])

### I.3 Boundedness and Budget Discipline

The system SHALL enforce explicit bounds on time, steps, cost, rate limits, concurrency, and recursion.

### I.4 Explicit Stop Conditions

Every workflow SHALL define completion and stop conditions, including safe abort/fallback paths.

---

## Article II: Trust Model and Threat Model

### II.1 Trust Boundaries Are First-Class

Architecture SHALL explicitly define trust boundaries between: user/system, untrusted content/policy, actor/tools, memory/tenant, tool servers/internal network.

### II.2 Minimum Threat Enumeration

System SHALL model and mitigate, at minimum:

* prompt injection (direct/indirect), untrusted-content instruction hazards, ([OWASP Gen AI Security Project][2])
* excessive agency, ([AWS Documentation][10])
* secrets/PII disclosure,
* insecure output handling,
* memory poisoning,
* DoS/denial-of-wallet,
* supply chain vulnerabilities (models/tools/connectors), ([OWASP Cheat Sheet Series][8])
* protocol/connector delegation hazards (e.g., confused deputy patterns). ([Model Context Protocol][9])

### II.3 Treat the Actor as an Untrusted Principal for Privileged Effects

No single actor output SHALL be sufficient to authorize a high-risk action. Untrusted content SHALL NOT directly trigger state change without independent checks. OWASP explicitly recommends privilege control, HITL for privileged operations, segregation of external content, and explicit trust boundaries. ([OWASP Gen AI Security Project][2])

---

## Article III: Governance and Risk Management

### III.1 Risk Lifecycle

Operator SHALL implement a risk lifecycle aligned to lifecycle-based AI risk management (govern/map/measure/manage) and maintain role accountability. ([NIST Publications][7])

### III.2 Trustworthiness Targets

System SHALL define measurable targets for valid/reliable, safe, secure/resilient, accountable/transparent, and (where applicable) explainable/interpretable, privacy-enhanced, and fair with harmful bias managed. ([NIST Publications][7])

### III.3 Change Control

Operator SHALL version and gate changes to models, prompts, policies, capability sets, connectors, eval suites, and deployment configs.

### III.4 Separation of Duties

Where feasible, separate builders from validators, policy authors from tool implementers, operations from security review.

### III.5 Assurance Case Requirement

For any production agent with high-risk actions, the operator SHALL maintain an **Assurance Case** that:

* enumerates hazards and unacceptable losses,
* maps hazards → controls → tests/telemetry,
* documents residual risk and acceptance,
* defines monitoring signals and incident playbooks.

### III.5.1 Assurance Case Format and Maintenance (Normative)

1. The Assurance Case SHALL be maintained as a **versioned artifact** (e.g., in the same repository and release process as prompts/tools/policies), with a stable identifier (e.g., `AC-<system>-<env>-<date>`).
2. The Assurance Case SHALL explicitly reference:
   * the deployed artifact bundle identifier(s) (hash/version),
   * the set of enabled capabilities/tools and their risk tiers,
   * the policy bundle identifier (hash/version),
   * the evaluation suite bundle identifier(s) (hash/version),
   * monitoring dashboards/alerts and incident runbooks used for detection/response.
3. The Assurance Case SHALL be updated on any of the following triggers:
   * adding or modifying a high-risk action/capability,
   * changing policy logic for privileged actions,
   * changing model/provider or decoding parameters for a production path,
   * changing tool connectors/permissions/scopes,
   * any P0/P1 incident, or a sustained SLO regression,
   * any major evaluation suite revision that changes pass/fail outcomes.
4. The Assurance Case SHALL conform to the minimum structure in **Appendix E** (or a documented equivalent with the same fields).

---

### III.6 Risk Register Requirement (Normative)

1. Operator SHALL maintain a **Risk Register** as a living artifact that tracks identified risks, their controls, evidence, and explicit acceptance.
2. The Risk Register SHALL be **updated for every release** that changes any of:
   * models/providers/decoding parameters used in production paths,
   * prompts/policies/tool manifests/capability scopes,
   * memory behavior (write rules, retrieval sources, retention/TTL),
   * evaluation gates or thresholds,
   * any new workflow that introduces or expands high-risk actions.
3. Each entry SHALL include, at minimum:
   * a unique Risk ID,
   * description and category (security, privacy, safety, reliability, cost/DoS, compliance),
   * affected capabilities and user impact,
   * severity and likelihood (with defined scales),
   * control references (policy/tool wrapper/verifier/HITL/monitoring),
   * evidence references (eval run IDs, tests, dashboards),
   * residual risk and explicit acceptance (owner + expiry), or mitigation plan.
4. Release Gates (Article XII) SHALL treat “updated risk register” as:
   * entries created/updated for all relevant changes,
   * evidence links refreshed (new eval runs),
   * residual risk acceptances re-confirmed (or expired acceptances renewed).
5. The Risk Register SHALL conform to the minimum structure in **Appendix F** (or a documented equivalent with the same fields).

---

## Article IV: Reference Architecture for Verified Agency

### IV.1 Required System Functions

A compliant system SHALL implement these functions (as services/modules/kernel controls/etc.):

1. Orchestrator (deterministic control)
2. Reference Monitor (authoritative gate)
3. Policy Engine (authorization/escalation)
4. Capability Wrappers (validation, scoping, idempotency, budgets)
5. Isolation/Sandboxing (for risky execution)
6. Observability (audit logs, metrics, traces)
7. Memory Governance (validation, provenance, TTL, deletion, tenant isolation)

### IV.2 State-Changing Actions Are Privileged

Privileged actions SHALL require policy authorization, precondition checks, postcondition verification, and (when high-risk) explicit approval.

### IV.3 Pre-Commit Authorization Barrier

For any privileged action, the system SHALL enforce an authorization barrier **before** effects occur.

**Recommended implementation:** Two-phase Plan → Commit with dry-run support.

### IV.4 Scope Confinement for Content-Interactive Agents

For agents operating across broad untrusted content spaces (e.g., the web), the system SHOULD implement scope confinement (domain/origin/resource sets) and separate read-only vs read-write scopes; Google’s “Agent Origin Sets” demonstrate this pattern as a guardrail against cross-site exfiltration and unwanted actions. ([Google Online Security Blog][3])

### IV.5 Action Transparency Ledger

The system SHALL maintain an action ledger/work log sufficient for audit and (for user-facing agents) user observation and interruption; Chrome’s design highlights step-by-step work logs and user ability to pause/stop during execution. ([Google Online Security Blog][3])

---

## Article V: Capability Control and Tool Contract Law

### V.1 Capabilities Are the Unit of Control

All external effects SHALL occur only through explicitly defined capabilities with declared contracts and side effects.

### V.2 Capability Specification

Each capability SHALL have a machine-readable spec: purpose, risk tier, input schema, output schema, permission scope, side effects, reversibility, idempotency, timeouts/retries/limits, cost model, audit fields.

### V.3 Authorization Middleware (Complete Mediation)

Every capability invocation SHALL pass through authorization middleware that authenticates the agent identity, authorizes via policy, validates parameters, enforces budgets/scope, and logs decisions.

### V.4 Deterministic Validation

Inputs and outputs SHALL be deterministically validated; on failure the system SHALL fail closed (deny/escalate).

### V.5 Poka‑Yoke Tooling

Capability interfaces SHOULD be designed to make unsafe or ambiguous usage difficult (“poka‑yoke”), and tool definitions SHOULD include clear boundaries, examples, edge cases, and testing of model tool usage; Anthropic explicitly recommends this approach for reliable agents. ([Anthropic][5])

---

## Article VI: Untrusted Input Discipline and Prompt Injection Resilience

### VI.1 Default-Untrusted Rule

All external content SHALL be treated as untrusted. ([OWASP Gen AI Security Project][2])

### VI.2 Instruction/Data Separation

System SHALL segregate authoritative instructions from untrusted content and label boundaries.

### VI.3 Untrusted Content Cannot Authorize Actions

Untrusted content SHALL NOT directly trigger privileged actions; authorization must be independent.

### VI.4 Injection-Aware Processing Pipeline (Recommended)

When using untrusted content, system SHOULD normalize, summarize/extract structured facts under constrained transforms, prefer facts over raw text, and escalate on suspicious signals.

### VI.5 Human-in-the-Loop for Privileged Operations

High-risk actions SHALL require explicit approval; OWASP prompt injection guidance explicitly recommends HITL for privileged operations like sending/deleting emails. ([OWASP Gen AI Security Project][2])

### VI.6 Visual Trust Signaling

User-facing systems SHOULD visually distinguish untrusted-derived content and highlight potentially untrustworthy responses; OWASP notes LLMs can act as intermediaries and may hide/manipulate information. ([OWASP Gen AI Security Project][2])

---

## Article VII: Verification and Independent Checking

### VII.1 Layered Verification

System SHALL implement layered verification: schema/type, policy, preconditions, postconditions, security scans, and budget/loop controls.

### VII.2 Independent Action Review (Optional but Strong)

The system MAY employ an independent reviewer/critic for action proposals, but SHALL NOT replace deterministic enforcement for privileged actions. Google describes a separate “User Alignment Critic” isolated from untrusted content that can veto misaligned actions. ([Google Online Security Blog][3])

### VII.3 Evidence-Backed Claims

When stating external facts, system SHOULD track provenance, mark uncertainty, and avoid fabricated sources.

---

## Article VIII: Memory, Context, and Data Governance

### VIII.1 Memory Is Privileged

Memory SHALL be governed as a privileged subsystem (risk of leakage and poisoning).

### VIII.2 Memory Classes

Define: ephemeral working memory (TTL), task memory (validated, provenance-tagged), optional user profile memory (explicit opt-in, low sensitivity).

### VIII.3 Memory Write Controls

Persistent writes SHALL be validated, minimized, store structured summaries over raw untrusted text, and record provenance and approval context.

### VIII.4 Secret Hygiene

Secrets SHALL NOT be exposed to the actor except through controlled execution contexts designed to prevent exfiltration.

---

## Article IX: Identity, Access, and Non-Human Principals

### IX.1 Agents Have Distinct Identities

Agents SHALL run under distinct non-human identities with scoped credentials, rotation, deprovisioning, and accountable ownership.

Microsoft Entra’s agent identity governance explicitly frames governing agent identities like human identities, with sponsors accountable and access expiring when no longer needed. ([Microsoft Learn][4])

### IX.2 Zero Standing Privilege (Preferred)

System SHOULD use just-in-time credentials and avoid long-lived static secrets.

### IX.3 Delegation and Consent Are Explicit

Delegation SHALL be explicit: who granted access, what scope, and for how long.

---

## Article X: Security Engineering Requirements

### X.1 Map Controls to Recognized Risk Taxonomies

System SHOULD map threats and mitigations to recognized taxonomies (prompt injection, excessive agency, insecure output handling, supply chain, DoS).

### X.2 Tool/Connector Growth is an Attack Surface

Authentication, authorization, schema validation, provenance, and scope enforcement SHALL be applied to all connectors.

### X.3 Connector/Protocol Security (Method-Neutral)

For any tool protocol, the system SHALL support:

* modern delegated authorization where appropriate,
* scope upgrades (step-up authorization),
* token rotation/expiration,
* auditable actions,
* protection against proxy/delegation hazards (e.g., confused deputy).
  MCP’s specifications and security best practices illustrate concrete risks (including confused deputy vulnerabilities) and modern authorization requirements such as OAuth 2.1 with security requirements. ([Model Context Protocol][9])

---

## Article XI: Observability, Auditability, and Accountability

### XI.1 Traceability

System SHALL log sufficient detail to reconstruct: request context, policy decisions, capability calls (redacted), tool outputs used, approvals/denials, and outcomes.

### XI.2 Tamper Evidence

High-risk systems SHOULD use tamper-evident logging.

### XI.3 SLOs

Operator SHALL define SLOs: success rate, constraint violation rate, escalation rate, tool depth, cost per completion, incident response times.

### XI.4 User-Facing Transparency Controls

User-facing agents SHALL provide a work log and controls to pause/stop/take over for sensitive workflows. ([Google Online Security Blog][3])

---

## Article XII: Evaluation, Testing, and Release Discipline

### XII.1 Testing Pyramid

Unit → integration → scenario → adversarial → regression suites SHALL exist.

### XII.2 Real Failure Modes Covered

Evals SHALL include indirect injection, tool misuse, runaway loops, scope confusion, partial failures/rollback behavior.

### XII.3 Release Gates

No deployment without passing regression, meeting constraint thresholds, configured monitoring, and updated risk register.

### XII.4 Canary + Rollback (Staff-Level Requirement)

Production deployments SHOULD use staged rollout (canary), automatic rollback triggers, and explicit rollback procedures.

---

### XII.5 Evaluation Data Governance (Normative)

Evals are only as trustworthy as the data and labeling behind them. Therefore:

1. **Eval Suite Cards (Required).**
   Every evaluation suite SHALL have a suite “card” that documents:
   * suite purpose and risk coverage (which hazards/capabilities it targets),
   * dataset provenance (how cases were sourced or generated),
   * labeling rubric version and pass/fail criteria,
   * privacy/sensitivity classification and retention rules,
   * update cadence and change log,
   * known gaps and non-goals.
   The suite card SHALL be stored and versioned alongside the suite itself.

2. **Versioned, Immutable Suites (No Silent Edits).**
   Eval suites and datasets SHALL be versioned artifacts. Changes SHALL produce a new version (hash) and a changelog entry.
   “Hot edits” to keep a gate passing are prohibited; changes require documented rationale and review.

3. **Coverage Mapping to Risk.**
   Eval design SHALL map to hazards and controls:
   * each high-risk capability SHALL have scenario evals and adversarial/injection evals,
   * each policy rule SHALL have at least one positive and one negative test,
   * each incident class SHALL be represented by at least one regression test.

4. **Labeling Quality Controls.**
   For any suite used as a release gate:
   * labeling rubrics SHALL be explicit and unambiguous,
   * ambiguous cases SHALL be flagged and either clarified or removed,
   * sampling-based re-label audits SHALL be performed when suites change materially or when drift is suspected.

5. **Statistical Discipline for Gates.**
   Release gates SHALL specify:
   * minimum sample sizes for stochastic behaviors,
   * decision thresholds (with rationale),
   * handling of flakes (retries, triage, quarantine),
   * confidence/variance expectations and acceptable error rates.
   Gates SHALL avoid “metric shopping”; thresholds and metrics SHALL be fixed per version and changed only via change control.

6. **Privacy and Access Control.**
   Eval datasets derived from production traces SHALL:
   * be minimized, redacted/anonymized where applicable,
   * have explicit consent/legal basis where required,
   * be access-controlled (least privilege),
   * never include secrets.
   Sensitive eval data SHALL have defined retention and deletion procedures.

7. **Training/Eval Separation (Strongly Recommended).**
   Operator SHOULD enforce separation between training data pipelines and evaluation datasets to reduce leakage and overfitting to gates.

---

## Article XIII: Human Oversight and UX as Safety Controls

### XIII.1 User Visibility for Consequential Steps

Before consequential actions, show intended action, justification, data disclosure, capability invoked, and approve/deny path.

### XIII.2 Escalation Paths

Human approval, takeover, refusal, and read-only fallback SHALL be supported.

### XIII.3 Refusal is Designed

Refusal SHALL be a testable, consistent behavior (fail closed).

---

## Article XIV: Multi-Agent and Distributed Systems

### XIV.1 Prevent Cascading Failures

Isolate agents by permissions, validate inter-agent messages, restrict cross-agent capability invocation, implement circuit breakers.

### XIV.2 Inter-Agent Protocol Discipline

Authenticated sender identity, schema validation, trust tags, and rate limits SHALL exist.

---

## Article XV: Operational Hardening and Continuous Response

### XV.1 Evolving Threat Posture

Assume attacks evolve; defenses SHALL be continuously maintained.

### XV.2 Rapid Response Loop

Detect → reproduce → add to adversarial suite → deploy mitigations → monitor.

Google describes continuous auditing/red-teaming and rapid iteration for agentic security; OpenAI describes prompt injection as an open challenge requiring continued hardening. ([Google Online Security Blog][3])

### XV.3 Kill Switch and Safe Mode

System SHALL support disabling privileged capabilities, read-only mode, and emergency shutdown with preserved logs.

---

## Article XVI: Simplicity, Modularity, and Effective Agents Discipline

### XVI.1 Augmented-Component Principle

Treat agentic systems as AI components augmented by tools/memory, surrounded by deterministic controls.

### XVI.2 Prefer the Simplest Adequate Pattern

Use the least agentic pattern that works; add complexity only when it demonstrably improves outcomes—Anthropic explicitly recommends starting simple and iterating with evaluation. ([Anthropic][5])

### XVI.3 Modular Skills over Monolith Prompts

Decompose behavior into small testable skills/capability pipelines, validators, and explicit state machines for critical workflows.

### XVI.4 Deliberate Context Management

Minimize irrelevant context, label sources, segregate untrusted content, and avoid context sprawl.

---

## Article XVII: Breakpoints and Watchlist

The system SHALL monitor for paradigm shifts that require constitutional amendments:

1. Loss of interceptable enforcement gate (no complete mediation)
2. Enforcement becomes purely probabilistic (no deterministic backstop)
3. Uncontrolled self-modification becomes intrinsic
4. Irreversible actions required at machine speed without pre-commit checks
5. Proof-carrying/formally verified actors become practical (positive breakpoint)
6. Closed-world trusted inputs reduce untrusted-content risk (contextual shift)

OpenAI explicitly characterizes prompt injection as an open challenge for agent security in the browser context due to the broad untrusted surface area and consequential actions. ([OpenAI][6])

---

## Appendix A: Capability Specification Template

```yaml
capability:
  name: "send_email"
  description: "Send an email on behalf of the user"
  risk_level: "high"
  permissions:
    mode: "write"
    allowed_recipients: "allowlist_only"
  input_schema:
    type: object
    required: ["to", "subject", "body"]
  output_schema:
    type: object
    required: ["status", "message_id"]
  controls:
    requires_human_approval: true
    idempotency_key_required: true
    timeout_ms: 5000
  audit:
    correlation_id_required: true
    justification_required: true
```

---

## Appendix B: Minimal Policy Ruleset

1. Default deny for non-allowlisted capabilities
2. Read-only by default
3. High-risk actions require approval
4. Untrusted content cannot directly trigger state changes ([OWASP Gen AI Security Project][2])
5. Budget enforcement (steps/time/cost)
6. Sensitive data minimization
7. Scope confinement for content-interactive agents (read vs write scopes) ([Google Online Security Blog][3])
8. Identity-based authorization for agent principals with expiring access ([Microsoft Learn][4])

---

## Appendix C: Builder’s Training Path (Staff Track)

1. Distributed systems reliability + SRE
2. Security engineering + threat modeling
3. Evaluation science (adversarial + regression)
4. Agent systems engineering (tools, memory, modular skills) ([Anthropic][5])
5. Governance and risk (trustworthiness targets, audits, change control) ([NIST Publications][7])

---

## Appendix D: ModelOps and Supply Chain Minimums (Non-Normative but Strongly Recommended)

OWASP Secure AI Model Ops highlights threats like data poisoning, model extraction, unsecured APIs, unvalidated third-party models, drift detection gaps, and orphaned deployments, and recommends versioned pipelines, secret managers, model registry access control, signing artifacts, inference API auth/rate limiting, monitoring, and rollback mechanisms. ([OWASP Cheat Sheet Series][8])

---

## Appendix E: Assurance Case Template (Normative)

> This template is intentionally concrete. Replace “TBD” fields; do not delete sections without documented rationale.

# Assurance Case: <System Name> (<Environment>)
- Assurance Case ID: AC-<system>-<env>-<yyyymmdd>
- Status: draft | approved | retired
- Owner: <name/team>
- Security Reviewer: <name/team>
- Ops/SRE Reviewer: <name/team>
- Approval Authority (Risk Acceptance): <name/title>
- Last Updated: <date>
- Next Review Due: <date>

## E.1 Scope and Assumptions
- Intended use / user population:
- Out-of-scope use:
- Operating environments (dev/stage/prod):
- Assumptions (dependencies, trust assumptions, user constraints):
- Data classes touched (e.g., public/internal/confidential/PII/secrets):

## E.2 High-Risk Actions and Capability Inventory
List every enabled capability (including read-only ones) and mark which are high-risk.

| Capability | Risk Tier | Side Effects | Reversible | Preview/Diff Supported | Human Approval Required | Scope Constraints | Notes |
|-----------:|:---------:|:------------:|:----------:|:----------------------:|:----------------------:|:----------------|:------|
| <tool>     | low/med/high | yes/no | yes/no/partial | yes/no | yes/no | <domains/paths/etc> | |

## E.3 Unacceptable Losses (Top-Level Harm Statements)
Enumerate outcomes you consider unacceptable (these anchor hazard analysis).

| Loss ID | Unacceptable Loss Statement |
|--------:|-----------------------------|
| L-1     | <e.g., unauthorized disclosure of customer PII> |
| L-2     | <e.g., unintended external communications on behalf of user> |
| L-3     | <e.g., unauthorized production mutation or permission escalation> |
| L-4     | <e.g., value transfer or financial loss above threshold> |

## E.4 Hazards (What Could Cause an Unacceptable Loss)
A hazard is a scenario that could produce one of the losses above.

Severity and likelihood scales SHALL be defined (e.g., 1–5) and applied consistently.

| Hazard ID | Scenario | Triggers / Preconditions | Loss IDs | Severity | Likelihood | Risk Level | Notes |
|----------:|----------|--------------------------|---------:|:--------:|:----------:|:----------:|------|
| H-1       | <prompt injection causes tool misuse> | <untrusted content in context> | L-2,L-3 | 5 | 3 | High | |
| H-2       | <memory poisoning leads to secrets disclosure> | <persistent write allowed> | L-1 | 4 | 2 | Med | |

## E.5 Controls (Prevention / Detection / Response)
Every hazard SHALL map to one or more controls. Controls SHOULD be diverse (policy, technical, UX/HITL, monitoring).

| Control ID | Type (Prevent/Detect/Respond) | Description | Enforced Where | Hazards Covered | Failure Mode | Owner |
|-----------:|:------------------------------:|-------------|----------------|-----------------|-------------|------|
| C-1        | Prevent | <two-phase approve/commit bound to diff hash> | <ref monitor/policy> | H-1 | <TOCTOU, bypass> | |
| C-2        | Prevent | <tool scope allowlists + parameter validation> | <tool wrapper> | H-1 | <overbroad scopes> | |
| C-3        | Detect | <shadow eval + alerts on violation rate> | <monitoring> | H-1,H-2 | <alert fatigue> | |
| C-4        | Respond | <automatic rollback + safe mode> | <ops> | H-1,H-2 | <rollback too slow> | |

## E.6 Evidence (Tests, Evals, Telemetry, Reviews)
Every control SHALL have evidence. Evidence MUST be specific and retrievable.

| Control ID | Evidence Type | Evidence ID / Link | Pass Criteria | Last Run | Result |
|-----------:|--------------|--------------------|--------------|----------|--------|
| C-1        | Eval (scenario) | <eval_suite@hash / run_id> | <0 high-risk commits without approval> | <date> | pass/fail |
| C-2        | Unit/Integration | <CI job link> | <validation rejects disallowed args> | <date> | pass/fail |
| C-3        | Dashboard/Alert | <dashboard link> | <violation rate < threshold> | <date> | ok/alert |
| C-4        | Game day / Drill | <report link> | <rollback < X minutes> | <date> | pass/fail |

## E.7 Residual Risk and Explicit Acceptance
List what remains after controls, why it’s acceptable, and under what conditions.

| Residual Risk ID | Description | Related Hazards | Remaining Risk Level | Mitigation Plan | Acceptance Owner | Expiry / Review Date |
|-----------------:|-------------|-----------------|----------------------|-----------------|------------------|----------------------|
| RR-1             | <provider drift causes rare false approvals> | H-1 | Med | <increase canary + add drift eval> | <name> | <date> |

## E.8 Monitoring, Alerts, and Incident Response
- SLOs (success, constraint violations, escalation rate, cost per completion, etc.):
- Alert thresholds (what triggers page vs ticket):
- On-call ownership:
- Incident runbooks (links):
- Safe mode / kill switch procedure:
- Rollback procedure and maximum time-to-rollback target:
- Post-incident rule: P0/P1 incidents SHALL add regression tests and update this Assurance Case.

## E.9 Change Triggers and Review Cadence
- Changes requiring re-review:
- Scheduled review cadence:
- Required approvers for high-risk changes:

---

## Appendix F: Risk Register Template (Normative)

> This register is intended to be machine-readable (CSV/JSON/YAML) or a structured table in a repo.

### F.1 Scales (Required)
Define and keep stable (example):

- Severity (1–5): 1=negligible, 3=material user harm/incident, 5=catastrophic (major breach/financial loss/safety harm)
- Likelihood (1–5): 1=rare, 3=occasional, 5=frequent
- Risk Level: derived (e.g., Severity × Likelihood) with defined bands

### F.2 Risk Register Entries
| Risk ID | Title | Category | Description | Affected Capabilities | Severity | Likelihood | Risk Level | Controls (IDs) | Evidence (links/IDs) | Residual Risk | Mitigation Plan | Owner | Status | Acceptance Owner | Acceptance Expiry | Last Reviewed |
|-------:|-------|----------|-------------|------------------------|:--------:|:----------:|:----------:|----------------|----------------------|--------------|-----------------|-------|--------|------------------|-------------------|--------------|
| R-001  | <…>   | security | <…>         | <tool1, tool2>        | 4 | 3 | 12 | C-1,C-2 | <eval_run_id,…> | <…> | <…> | <team> | open/mitigated/accepted | <name> | <date> | <date> |

### F.3 Required Linkage Rules (Normative)
- Every Risk Register entry SHALL map to at least one control and at least one piece of evidence.
- “Accepted” risks SHALL include an explicit acceptance owner and an expiry/review date.
- Any P0/P1 incident SHALL result in:
  1) a Risk Register update (new risk or updated likelihood/severity),
  2) at least one new regression/adversarial eval,
  3) updated controls/evidence references.

---

## Appendix G: Evaluation Suite Cards, Rubrics, and Coverage Templates (Normative)

### G.1 Eval Suite Card (Required)
```yaml
eval_suite:
  name: "<suite_name>"
  suite_id: "EVAL-<name>-<yyyymmdd>"
  version: "<hash or semver>"
  purpose: "<what this suite is meant to detect>"
  risk_coverage:
    hazards: ["H-1", "H-2"]
    capabilities: ["<tool_1>", "<tool_2>"]
    controls: ["C-1", "C-3"]
  composition:
    types: ["golden_regression", "adversarial_injection", "scenario_simulation"]
    num_cases: 0
    min_cases_for_gate: 0
  provenance:
    sources: ["synthetic", "incident_regressions", "prod_trace_sanitized"]
    generator: "<script/tooling + version>"
    inclusion_criteria: "<rules>"
    exclusion_criteria: "<rules>"
  labeling:
    rubric_id: "RUBRIC-<name>-<yyyymmdd>"
    rubric_version: "<hash>"
    labelers: "<human/auto/mixed>"
    audit_plan: "<spot-check %, cadence>"
  privacy:
    classification: "public|internal|confidential|PII|secrets_prohibited"
    retention_days: 90
    access_policy: "<who can access>"
  gate:
    metrics: ["success_rate", "constraint_violation_rate", "escalation_rate"]
    thresholds:
      success_rate_min: 0.0
      violation_rate_max: 0.0
    flake_policy: "<retry/quarantine rules>"
  changelog:
    - date: "<date>"
      change: "<what changed and why>"
      approved_by: "<reviewer>"
```

### G.2 Test Case Schema (Recommended)

```yaml
test_case:
  id: "TC-0001"
  title: "<short title>"
  type: "golden|adversarial|scenario"
  target_capabilities: ["<tool>"]
  hazard_refs: ["H-1"]
  control_refs: ["C-1", "C-2"]
  input:
    user_prompt: "<string>"
    context_docs: ["<doc refs>"]
    system_state: "<optional typed state>"
  expected:
    outcome: "allow|deny|escalate|safe_mode"
    constraints:
      - "no_high_risk_commit_without_approval"
      - "no_secrets_in_output"
    required_trace_events:
      - "policy_eval"
      - "tool_call_proposed"
  notes:
    - "<edge cases>"
```

### G.3 Labeling Rubric Skeleton (Required for Gated Suites)

```md
# Rubric: <name> (RUBRIC-<yyyymmdd>)
## Pass/Fail definitions
- PASS means: <precise, testable criteria>
- FAIL means: <precise, testable criteria>
- ESCALATE means: <precise, testable criteria>

## Common failure categories (use as labels/tags)
- Policy bypass / unauthorized action
- Prompt injection following untrusted instructions
- Scope violation (domain/path/recipient)
- Missing approval for high-risk
- Unsafe output (secrets/PII)
- Loop/thrash / budget violation
- Incorrect rollback / non-idempotent replay

## Ambiguity handling
- If labelers disagree or criteria unclear: mark as AMBIGUOUS and route to rubric update.
```

### G.4 Coverage Matrix (Recommended)

| Hazard | Capability | Control | Eval Suite(s) | Test Case IDs | Gate? | Notes |
| -----: | ---------- | ------- | ------------- | ------------- | :---: | ----- |
|    H-1 | send_email | C-1,C-2 | EVAL-email-…  | TC-0001,…     |  yes  |       |

---

## Alignment Anchors (Non-Normative)

* OWASP AI Agent Security: least privilege, per-tool scoping, explicit authorization ([OWASP Cheat Sheet Series][1])
* AWS Well-Architected GenAI Lens: permission boundaries for agentic workflows ([AWS Documentation][10])
* OWASP Prompt Injection: segregate external content, HITL for privileged ops, trust boundaries ([OWASP Gen AI Security Project][2])
* Google Chrome agentic security: critic isolation, origin sets, work log, confirmations, red-teaming ([Google Online Security Blog][3])
* Microsoft Entra agent identity governance: lifecycle + sponsor accountability + expiring access ([Microsoft Learn][4])
* Anthropic: simplicity, transparency, careful tool interface (ACI), poka‑yoke tools ([Anthropic][5])
* OpenAI: prompt injection as an open challenge; continuous hardening required ([OpenAI][6])

---

## Closing Clause

This Constitution defines trust as **provable restraint**: explicit capabilities, enforced boundaries, independent verification, and auditable execution. The system SHALL evolve via evidence: incidents, eval failures, and new attack classes SHALL result in amendments, expanded tests, and updated operational practice.

[1]: https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html "AI Agent Security - OWASP Cheat Sheet Series"
[2]: https://genai.owasp.org/llmrisk2023-24/llm01-24-prompt-injection/ "LLM01: Prompt Injection - OWASP Gen AI Security Project"
[3]: https://security.googleblog.com/2025/12/architecting-security-for-agentic.html "
Google Online Security Blog: Architecting Security for Agentic Capabilities in Chrome 
"
[4]: https://learn.microsoft.com/en-us/entra/id-governance/agent-id-governance-overview "Governing Agent Identities (Preview) - Microsoft Entra ID Governance | Microsoft Learn"
[5]: https://www.anthropic.com/research/building-effective-agents "Building Effective AI Agents \ Anthropic"
[6]: https://openai.com/index/hardening-atlas-against-prompt-injection/ "Continuously hardening ChatGPT Atlas against prompt injection attacks | OpenAI"
[7]: https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf "Artificial Intelligence Risk Management Framework (AI RMF 1.0)"
[8]: https://cheatsheetseries.owasp.org/cheatsheets/Secure_AI_Model_Ops_Cheat_Sheet.html "Secure AI Model Ops - OWASP Cheat Sheet Series"
[9]: https://modelcontextprotocol.io/specification/draft/basic/security_best_practices "Security Best Practices - Model Context Protocol"
[10]: https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec05-bp01.html "GENSEC05-BP01 Implement least privilege access and permissions boundaries for agentic workflows - Generative AI Lens"
