## The Compass

**Industry patterns for building reliable, constrained, verified agentic AI systems**
*(Your Constitution = non‑negotiable invariants. This Compass = practical ways teams actually build toward those invariants.)*

The Constitution tells you what **must** be true. This Compass tells you what tends to **work in practice**—and (crucially) what tends to fail—based on public guidance and design choices from teams that are shipping real agents: **Anthropic, OpenAI, Google (Chrome/Gemini), Microsoft (Entra/Agent ID), AWS (Well‑Architected GenAI Lens), and OWASP**. ([Anthropic][1])

### How to use this Compass

* Use it during **design** (pick the lowest‑agency pattern that solves the problem), during **implementation** (tool contracts, gates, identity), and during **release/ops** (evals, monitoring, incident loops).
* Every pattern includes a paired **anti‑pattern** so the “why” burns into your brain.
* Every pattern implicitly supports one or more Constitution articles (least privilege, pre‑commit barrier, untrusted input discipline, auditability, etc.). I’ll call out alignment when it’s especially important.

---

# North Star heuristics (the “you should hear this in your sleep” set)

1. **Start simple, earn complexity**
   Anthropic’s consistent observation: successful teams use *simple, composable patterns*, not maximal frameworks. They recommend finding the simplest solution and increasing complexity only when needed. ([Anthropic][1])

2. **Increase agency only when the task requires it**
   AWS frames agentic systems as having degrees of agency, and recommends only increasing it as task complexity demands. ([AWS Documentation][2])

3. **Assume prompt injection exists forever; design for containment**
   OWASP explains the root problem: instructions and data are processed together without a native “trust boundary,” enabling prompt injection. ([OWASP Cheat Sheet Series][3])
   OpenAI explicitly treats it as a long‑term challenge, using layered defenses, monitoring, sandboxing, and user control mechanisms. ([OpenAI][4])

4. **Only code can enforce. Models can suggest.**
   The industry trend is clear: keep the model as a proposing component; enforce through permissions, gates, sandboxes, confirmations, and monitoring. ([OWASP Cheat Sheet Series][5])

---

# Pattern Library (with anti‑patterns)

## A) Autonomy and orchestration patterns

### 1) **Workflow-first architecture (deterministic spine + LLM “joints”)**

**Pattern**: Implement the system as a deterministic workflow where only certain steps are delegated to the model (classification, extraction, drafting, planning), and all effects happen through explicit gates.
Anthropic draws a key distinction: **workflows** are predefined code paths; **agents** are model-directed tool use. Start with workflows for predictability. ([Anthropic][1])
AWS similarly describes “LLM‑augmented workflows” as low‑agency systems with largely deterministic code paths. ([AWS Documentation][2])

**Practical moves**

* Start with *one* LLM call + retrieval/examples; only then add multi-step loops. ([Anthropic][1])
* Make the workflow observable: every step logged; every tool call mediated.

**Anti-pattern**: “Agent-first for everything”
You build a looping autonomous agent as the default, then try to bolt on safety later. Result: unpredictable behavior, hard-to-debug failures, and runaway scope.

---

### 2) **Prompt chaining (decompose into fixed subtasks + gates)**

**Pattern**: Break the task into a sequence of steps; add programmatic “gates” between steps to verify correctness before proceeding. Anthropic calls this **prompt chaining** and explicitly shows adding checks mid-chain. ([Anthropic][1])

**Practical moves**

* Put strict validators between steps (schema checks, constraints, policy checks).
* Store intermediate artifacts so failures are recoverable.

**Anti-pattern**: “One giant prompt to rule them all”
Big monolithic prompt + massive context → brittle, non-debuggable, and impossible to attribute errors.

---

### 3) **Routing (classify → specialized handler)**

**Pattern**: Classify input and route to specialized prompts/tools/models. Anthropic recommends routing for separation of concerns and cost/perf optimization. ([Anthropic][1])

**Practical moves**

* Use deterministic routing where possible; use model routing when categories are fuzzy.
* Keep per-route tool permissions distinct (least privilege).

**Anti-pattern**: “Single universal agent prompt”
You try to handle refunds, onboarding, security, and billing with one prompt and one toolset. You get tool misuse and misalignment because nothing is truly bounded.

---

### 4) **Parallelization (sectioning or voting)**

**Pattern**: Run multiple independent model calls and aggregate:

* **Sectioning**: split the task into independent parts
* **Voting**: multiple attempts to increase confidence
  Anthropic highlights both and notes it can outperform “do everything in one call,” including for guardrails/evals. ([Anthropic][1])

**Practical moves**

* Use parallel “checker” calls (policy, safety, compliance) independent of the main generator.
* Aggregate deterministically (thresholds, scoring, structured adjudication).

**Anti-pattern**: “Single model does response + safety + policy in one breath”
You get entangled objectives and higher chance of missing violations.

---

### 5) **Orchestrator–workers (manager delegates; workers are scoped specialists)**

**Pattern**: A central planner decomposes a task and delegates to worker calls, then synthesizes results. Anthropic describes this as useful when subtasks can’t be predicted ahead of time (e.g., coding). ([Anthropic][1])

**Practical moves**

* Each worker has a *narrow* toolset and strict budget.
* Worker outputs are treated as untrusted until validated.
* Synthesis step must cite/trace sources.

**Anti-pattern**: “Swarm of peers with shared superuser privileges”
Collaboration without constraints becomes amplified chaos: message poisoning, privilege bleed, and impossible auditing.

---

### 6) **Evaluator–optimizer loop (iterative refinement with explicit criteria)**

**Pattern**: One call generates; another evaluates against explicit criteria and provides feedback, iterating. Anthropic recommends it when criteria are clear and iterative refinement measurably helps. ([Anthropic][1])

**Practical moves**

* Cap iterations.
* Require the evaluator to output structured critiques tied to rubric items.
* Log deltas across iterations.

**Anti-pattern**: “Infinite self-critique / reflection spiral”
Costs explode; the agent becomes performative instead of productive; and it can rationalize unsafe actions if the evaluator is not enforced by deterministic guards.

---

## B) Tooling and “capability contract” patterns

### 7) **Typed tool contracts (schema-first tools)**

**Pattern**: Every tool has a strict input/output schema, declared side effects, idempotency, timeouts, and audit fields.
This matches the general “tool interface discipline” that serious agent builders emphasize; Anthropic explicitly stresses careful agent–computer interface design (ACI) and tool documentation/testing. ([Anthropic][1])

**Practical moves**

* Reject tool calls that don’t validate.
* Design tools so “unsafe ambiguity” is impossible (poka‑yoke).
* Version tool schemas; maintain backward compatibility.

**Anti-pattern**: “Free-form tool calls via natural language”
The model emits vague actions (“update the record”) that you interpret ad hoc. That’s how you get silent corruption.

---

### 8) **Read/write split tools + step-up authorization**

**Pattern**: Provide separate read-only and write tools; require step-up authorization (user approval, higher privilege token) before writes.
OWASP and AWS both emphasize least privilege and explicit authorization boundaries to reduce excessive agency. ([OWASP Cheat Sheet Series][5])

**Practical moves**

* Reads can be broader; writes must be narrow, allowlisted, and logged.
* “Upgrade” from read → write is explicit and visible.

**Anti-pattern**: “Single tool that both reads and mutates everything”
This is excessive agency by construction. OWASP names excessive agency as enabling damaging actions from unexpected/ambiguous/manipulated outputs; the root cause is often excessive permissions/autonomy. ([OWASP Gen AI Security Project][6])

---

### 9) **Tool approvals (human approval node for sensitive ops)**

**Pattern**: Keep approvals on for operations (including reads and writes when warranted). OpenAI’s agent-builder safety guidance explicitly recommends enabling tool approvals so end users can review/confirm every operation. ([OpenAI Platform][7])

**Practical moves**

* Approval UX shows: what tool, what data scope, what will change, what is irreversible.
* Add “deny + alternative suggestion” path to keep flow useful.

**Anti-pattern**: “Invisible background actions”
The agent quietly reads email, touches files, or changes settings “because it thought it was helpful.” That’s how trust dies.

---

### 10) **Preview / dry-run / diff tools**

**Pattern**: For any state-changing action, provide a “preview” tool that returns what would change (diff), then require a commit.
This is the practical version of your Constitution’s pre-commit barrier.

**Practical moves**

* “Compute diff” is deterministic.
* Approvals happen on the diff, not on vague intent.

**Anti-pattern**: “Direct writes with no explainable preview”
Humans can’t safely approve what they can’t see, and you can’t audit intent vs effect.

---

### 11) **Sandboxed execution for risky tools (code, shell, browser automation)**

**Pattern**: Run risky tools in sandboxed environments with restricted permissions and observable output. OpenAI explicitly uses sandboxing when AI tools run programs/code to reduce harm from prompt injection. ([OpenAI][4])

**Practical moves**

* No network by default; allowlist egress.
* Mount read-only data; isolate secrets.
* Log every command + artifact.

**Anti-pattern**: “Model has prod shell access”
That’s not an agent; it’s an incident.

---

## C) Untrusted input and prompt-injection containment patterns

### 12) **Treat all external content as untrusted + label boundaries**

**Pattern**: Treat user inputs, retrieved docs, webpages, tool outputs, emails as untrusted; separate instructions from data with explicit boundaries. OWASP’s prompt injection guidance centers on the lack of separation between instructions and data and recommends structured prompts and clear separation. ([OWASP Cheat Sheet Series][3])

**Practical moves**

* Put untrusted content in clearly delimited blocks.
* Never let untrusted content become “system/developer instruction.”
* Keep a provenance tag per chunk.

**Anti-pattern**: “Paste webpage/email directly into the ‘instructions’ area”
That’s basically inviting indirect prompt injection.

---

### 13) **Quarantine → extract → reason (two-pass untrusted content handling)**

**Pattern**: Use a separate extraction/summarization step on untrusted content, producing structured facts with provenance, then reason on that structured representation.
OWASP suggests separate calls to validate/summarize untrusted content. ([OWASP Cheat Sheet Series][8])

**Practical moves**

* Extract into schema: entities, dates, obligations, actionable items.
* Include “suspicion flags” (e.g., contains instructions, credentials requests, obfuscation).

**Anti-pattern**: “Let the planner read raw untrusted content and decide actions directly”
That couples the most dangerous input to the most privileged decision.

---

### 14) **Least-privilege tool tokens + “model never sees the secret”**

**Pattern**: The application holds API tokens and performs privileged operations in code, not by handing secrets to the model. OWASP explicitly recommends privilege control and handling extensible functions in code rather than giving them to the model. ([OWASP Gen AI Security Project][9])

**Practical moves**

* Use scoped, short-lived tokens fetched by the orchestrator.
* Redact secrets from model-visible logs.

**Anti-pattern**: “Put API keys in context so the agent can call the API”
That’s credential exfiltration waiting to happen.

---

### 15) **Continuous adversarial testing + “rapid response loop”**

**Pattern**: Treat prompt injection as an evolving adversary; continuously test and patch.
OpenAI describes continuous discovery of new prompt injection attacks and a rapid response cycle for hardening Atlas, including automated attacker work. ([OpenAI][10])
OWASP recommends adversarial testing and breach simulations, treating the model as an untrusted user. ([OWASP Gen AI Security Project][9])

**Practical moves**

* Build an attack suite: indirect injection, tool misuse, memory poisoning, goal hijack.
* Add every incident as a regression test.
* Canary defenses before broad rollout.

**Anti-pattern**: “Security review once before launch”
Agents don’t stay secure by nostalgia.

---

## D) Browser / “computer use” agent patterns (high-risk surface area)

### 16) **Action vetting by an isolated checker + metadata-only review**

**Pattern**: Separate the planner from a high-trust checker that only sees action metadata (not raw web content) and can veto misaligned actions.
Google’s Chrome design introduces a **User Alignment Critic** that is isolated from untrusted content and vets each proposed action for alignment. ([Google Online Security Blog][11])

**Practical moves**

* Checker sees: proposed action type, target origin, risk tier, user goal, justification.
* Checker does **not** see raw page text, emails, or ads.

**Anti-pattern**: “Planner and guard in the same context”
If your guard reads the poison, it can be poisoned too.

---

### 17) **Origin / domain scoping (read-only vs read-write origins)**

**Pattern**: Constrain which origins the agent can interact with based on the task; separate read-only from read-write. Google extends origin isolation via **Agent Origin Sets** to constrain what sites the agent can access and act on. ([Google Online Security Blog][11])

**Practical moves**

* Default: read-only everywhere.
* Escalate to write only on task-relevant domains explicitly approved.

**Anti-pattern**: “Agent can browse + act anywhere on the open web”
That’s a permissionless attack surface.

---

### 18) **User confirmations + “watch mode” for sensitive sites**

**Pattern**: Require explicit confirmations before sensitive steps (purchases, banking/medical navigation, password usage). OpenAI describes pausing for confirmation for sensitive steps and a “Watch Mode” concept for sensitive sites; it also offers logged-out mode to reduce risk exposure. ([OpenAI][4])

**Practical moves**

* Confirmation required for: purchases, password autofill, financial transfers, account settings.
* Logged-out mode as default when possible.

**Anti-pattern**: “Full-speed autonomy on sensitive flows”
Even if the model is “usually right,” the blast radius is unacceptable.

---

## E) Memory and state patterns (where agents become haunted by their own past)

### 19) **Memory as a governed subsystem (classes, TTL, provenance, validation)**

**Pattern**: Separate ephemeral working memory from persistent memory; validate writes; store structured summaries with provenance tags; apply TTL; allow deletion.
This matches OWASP’s emphasis on agent security including memory poisoning risk and untrusted data handling. ([OWASP Cheat Sheet Series][5])

**Practical moves**

* “Write to memory” is a privileged action with a validator.
* Never store raw untrusted content as long-term memory.
* Store “why we stored this” metadata (task, date, approval status).

**Anti-pattern**: “Vector store as a diary (dump everything forever)”
That’s how you get persistent manipulation across sessions—explicitly called out as a prompt injection impact. ([OWASP Cheat Sheet Series][3])

---

### 20) **Long-running harness with artifacts + incremental progress discipline**

**Pattern**: For tasks spanning hours/days, design a harness that enables progress across context windows using durable artifacts and explicit “handoff” state.
Anthropic describes a two-part approach: an initializer session that sets up environment + a progress log, followed by sessions that make incremental progress and leave clear artifacts for the next run. ([Anthropic][12])

**Practical moves**

* Maintain a progress ledger (what was done, what remains, next steps).
* Require each session to end in a clean state (tests pass, docs updated).
* Use version control as “truth.”

**Anti-pattern**: “One mega-session until context explodes”
You get half-implemented work and the next session guesses, thrashes, and regresses—exact failure modes Anthropic observed. ([Anthropic][12])

---

## F) Identity, access, governance patterns (agents as non-human principals)

### 21) **Agent identities with lifecycle governance (sponsor/owner, access reviews)**

**Pattern**: Treat each agent as a first-class identity with lifecycle and access governance (like a service principal with human accountability).
Microsoft Entra’s agent identity governance introduces agent identities that can be governed with lifecycle/access features; sponsors are human users accountable for lifecycle and access decisions. ([Microsoft Learn][13])

**Practical moves**

* Every agent has an owner + sponsor.
* Access is time-bound; reviewed; logged.
* “Who is accountable?” is always answerable.

**Anti-pattern**: “Shared credentials / shadow agents”
Nobody owns it, nobody can rotate it safely, and deprovisioning becomes a ghost story.

---

### 22) **Permissions boundaries + least privilege for agent workflows**

**Pattern**: Apply explicit permission boundaries to limit what agent workflows can do. AWS explicitly recommends least privilege and permissions boundaries for agentic workflows to reduce excessive agency. ([AWS Documentation][14])
OWASP’s AI Agent Security cheat sheet echoes per-tool scoping and explicit authorization for sensitive operations. ([OWASP Cheat Sheet Series][5])

**Practical moves**

* Define “maximum possible” permissions via boundary policy; grant less per task.
* Separate builder vs operator roles (separation of duties).

**Anti-pattern**: “Agent runs as admin because it’s convenient”
Convenience is not a security argument.

---

## G) Guardrails, monitoring, and operating patterns (reliability is a verb)

### 23) **Layered defenses: monitors + approvals + sandboxes + red teaming**

**Pattern**: Use overlapping defenses, not single magic filters. OpenAI describes layered security protections: automated monitors, sandboxing, user controls, red-teaming, bug bounty. ([OpenAI][4])
Google describes layered defenses including critic, origin constraints, confirmations, real-time threat detection, and red-teaming/response. ([Google Online Security Blog][11])

**Practical moves**

* Separate *prevention* (scopes, gates) from *detection* (monitors) from *response* (kill switch).
* Instrument everything: tool calls, scopes, approvals, failures.

**Anti-pattern**: “One jailbreak filter, ship it”
Filters drift; attackers adapt; and your runtime still lacks enforceable control.

---

### 24) **Operational budgets + circuit breakers + safe mode**

**Pattern**: Enforce budgets (steps, time, cost), detect runaway behavior, and degrade to read-only / safe mode.
This is implied everywhere serious teams talk about “predictable” and “guardrailed” agents; it’s also foundational in agent security best practices (limit blast radius, detect abuse). ([OWASP Cheat Sheet Series][5])

**Practical moves**

* Circuit breaker triggers: repeated tool failures, anomalous tool sequences, cost spikes.
* Safe mode: disable writes and sensitive tools instantly.

**Anti-pattern**: “No budgets; no kill switch”
That’s how you get denial-of-wallet and infinite loops that call real systems.

---

### 25) **Secure ModelOps (supply chain hygiene for models + endpoints)**

**Pattern**: Treat model artifacts and inference endpoints like production-critical dependencies: signing, access control, rate limiting, drift monitoring, rollback. OWASP’s Secure AI Model Ops cheat sheet highlights risks like unsecured APIs, hardcoded secrets, unvalidated third-party models, lack of drift detection, orphaned deployments—and recommends controls including signed artifacts, access-controlled registries, endpoint auth/rate limiting, monitoring, and rollback. ([OWASP Cheat Sheet Series][15])

**Practical moves**

* Model registry with signed artifacts.
* Endpoint auth + abuse detection.
* Drift alarms + rollback runbooks.

**Anti-pattern**: “Random model blob from the internet + public endpoint”
That’s an attacker’s dream: either supply chain compromise or extraction/abuse.

---

# A compact “pattern selection” mental model (your compass rose)

When deciding how agentic to go, evaluate:

* **Task ambiguity** (low → workflow, high → agent loop)
* **Cost of error** (low → automation OK, high → approvals + previews + narrow scopes)
* **Reversibility** (reversible → more autonomy; irreversible → strict gates)
* **Untrusted exposure** (lots of web/email/docs → origin scoping + quarantine + isolated checker)
* **Verification availability** (tests, constraints, invariants → more autonomy is safer)

This matches the direction from Anthropic (“simplest adequate system”) and AWS (“increase agency only when complexity requires”). ([Anthropic][1])

---

# Why this is “industry aligned” (in one paragraph)

The dominant trend in serious agent deployments is **bounded autonomy**:

* **least privilege + explicit tool authorization** (OWASP, AWS), ([OWASP Cheat Sheet Series][5])
* **human approvals for sensitive actions** (OpenAI guidance), ([OpenAI Platform][7])
* **isolation and scoping for browser agents** (Google’s critic + origin sets), ([Google Online Security Blog][11])
* **agents as governable identities** (Microsoft Entra), ([Microsoft Learn][13])
* **continuous adversarial testing and hardening loops** (OpenAI’s Atlas hardening + OWASP adversarial testing guidance). ([OpenAI][10])

That’s the “compass direction” the whole industry is converging on: **don’t trust the model; trust the system you built around it**.

---

## Next step (to turn this into something you can “live by” as an architect)

Take 2–3 real agent use-cases you care about (e.g., “email triage,” “internal DevOps change assistant,” “customer support refund agent”) and, for each one, write a one-page design that explicitly states:

* chosen autonomy level (workflow vs agent loop),
* tool list + scopes (read vs write),
* approval points,
* untrusted content handling strategy,
* eval suite outline,
* rollback + safe mode plan,
* identity/credential lifecycle.

Doing that a few times is how you go from “I have principles” to “I ship trustworthy systems.”

[1]: https://www.anthropic.com/research/building-effective-agents "Building Effective AI Agents \ Anthropic"
[2]: https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/agentic-ai.html "Agentic AI - Generative AI Lens"
[3]: https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html "LLM Prompt Injection Prevention - OWASP Cheat Sheet Series"
[4]: https://openai.com/index/prompt-injections/ "Understanding prompt injections: a frontier security challenge | OpenAI"
[5]: https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html "AI Agent Security - OWASP Cheat Sheet Series"
[6]: https://genai.owasp.org/llmrisk2023-24/llm08-excessive-agency/?utm_source=chatgpt.com "LLM08: Excessive Agency - OWASP Gen AI Security Project"
[7]: https://platform.openai.com/docs/guides/agent-builder-safety "Safety in building agents | OpenAI API"
[8]: https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html?utm_source=chatgpt.com "AI Agent Security - OWASP Cheat Sheet Series"
[9]: https://genai.owasp.org/llmrisk/llm01-prompt-injection/ "LLM01:2025 Prompt Injection - OWASP Gen AI Security Project"
[10]: https://openai.com/index/hardening-atlas-against-prompt-injection/ "Continuously hardening ChatGPT Atlas against prompt injection attacks | OpenAI"
[11]: https://security.googleblog.com/2025/12/architecting-security-for-agentic.html "
Google Online Security Blog: Architecting Security for Agentic Capabilities in Chrome 
"
[12]: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents "Effective harnesses for long-running agents \ Anthropic"
[13]: https://learn.microsoft.com/en-us/entra/id-governance/agent-id-governance-overview "Governing Agent Identities (Preview) - Microsoft Entra ID Governance | Microsoft Learn"
[14]: https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec05-bp01.html "GENSEC05-BP01 Implement least privilege access and permissions boundaries for agentic workflows - Generative AI Lens"
[15]: https://cheatsheetseries.owasp.org/cheatsheets/Secure_AI_Model_Ops_Cheat_Sheet.html "Secure AI Model Ops - OWASP Cheat Sheet Series"
