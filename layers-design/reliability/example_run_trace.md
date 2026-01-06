# One concrete end-to-end example run trace

This document is a **single, concrete** “example run” that demonstrates what a **Constitution + Kernel-compliant** system looks like *in the logs*.

It is intentionally **method-agnostic**:
- the strategy could be ReAct, plan-and-execute, tree search, or something else,
- the model provider could be OpenAI/Anthropic/…,
- the retrieval and memory backends could vary.

The important part is that the **kernel invariants** are visible and auditable.

---

## Scenario

A student asks an AI tutor:

> “I’m preparing for my calculus exam. Using my past performance, create a 2-week study plan.  
> Save the plan to my profile and email it to me.”

This run includes:
- **privileged reads** (student profile memory),
- **memory write** (saving the plan),
- **high-risk side effect** (sending an email),
- **two-phase execution** with approval binding hash (Propose → Preview → Approve → Commit),
- **audit + trace** events that make debugging and compliance possible.

---

## Preconditions (what is configured before the run)

### Tool manifest (excerpt)

```yaml
tool_manifest_version: "1"
tools:
  - name: "memory.query_profile"
    version: "1.0"
    risk_tier: "medium"
    has_side_effects: false
    supports_preview: false

  - name: "memory.write_profile"
    version: "1.0"
    risk_tier: "medium"
    has_side_effects: true
    supports_preview: true     # preview shows a diff to the profile record

  - name: "send_email"
    version: "2.1"
    risk_tier: "high"
    has_side_effects: true
    supports_preview: true     # preview shows recipient + subject + body hash
```

### Policy bundle (excerpt)

```yaml
policy_version: 1
default: deny

principals:
  - name: "agent:tutor_v1"
    allowed_tools:
      - name: "memory.query_profile"
        mode: read
        constraints:
          tenant_scoped: true

      - name: "memory.write_profile"
        mode: write
        constraints:
          allowed_fields: ["study_plan", "progress_summary"]
          max_chars: 8000
        requires_approval: false   # medium risk; allowed under constraints

      - name: "send_email"
        mode: write
        requires_approval: true    # high risk always needs explicit approval
```

### Budget defaults (excerpt)

```yaml
max_steps_per_run: 25
max_wall_clock_sec: 120
max_repair_attempts: 2
tool_timeout_ms: 15000
approval_expiry_sec: 300
```

---

## Trace overview (human-readable)

At a high level, the state machine does:

1. Ingress authenticates identity → creates `run_id` + `trace_id`.
2. Kernel sanitizes and classifies the user prompt (K18 + classification).
3. Strategy requests a model call to decide next steps.
4. Strategy proposes a privileged read: `memory.query_profile`.
5. Kernel authorizes + executes the read via tool executor; result is sanitized.
6. Strategy requests a model call to draft the 2-week plan and propose actions:
   - write plan to memory,
   - send email.
7. Kernel verifies output + runs policy:
   - memory write allowed (no approval required),
   - email send requires approval.
8. Kernel performs two-phase execution for `send_email`:
   - preview → binding hash → approval request → commit on approval.
9. Kernel completes run, emits final outcome, and stores run bundle for replay.

---

## Concrete event trace (JSONL-style)

Notes:
- This is a **representative** event stream. Exact field names may vary, but the *information content* must be equivalent.
- Events are shown in approximate chronological order.
- `payload` contents are redacted/summarized where they might contain confidential data.

### 0) Run started

```json
{"ts":"2026-01-06T10:00:00.012Z","name":"run_started","trace_id":"2bb0...","run_id":"a9d1...","tenant_id":"school:acme_high","principal":"user:stu_123","bundle_id":"bundle:sha256:8c4b...","tool_manifest_hash":"sha256:5d2a...","policy_bundle_hash":"sha256:0aa1...","schema_version":"v0.1"}
```

### 1) K18 sanitize + classify user prompt (untrusted input discipline)

```json
{"ts":"2026-01-06T10:00:00.020Z","name":"sanitize_ingress","trace_id":"2bb0...","run_id":"a9d1...","payload":{"classification":"L2","suspicion_flags":[],"quoted_data_hash":"sha256:91f6...","provenance":{"source":"user","user_id":"stu_123"}}}
```

### 2) FSM enters planning

```json
{"ts":"2026-01-06T10:00:00.030Z","name":"state_enter","trace_id":"2bb0...","run_id":"a9d1...","payload":{"state":"PLAN","step":1,"budgets_remaining":{"steps":24,"wall_clock_sec":120}}}
```

### 3) Strategy asks for a model call (through K3)

```json
{"ts":"2026-01-06T10:00:00.035Z","name":"model_call_requested","trace_id":"2bb0...","run_id":"a9d1...","payload":{"prompt_bundle":"planner_v3","prompt_hash":"sha256:0f1a...","expected_schema":"PlanProposal@v2"}}
```

### 4) K3 model boundary executes and normalizes output

```json
{"ts":"2026-01-06T10:00:01.100Z","name":"model_call_completed","trace_id":"2bb0...","run_id":"a9d1...","payload":{"provider":"openai","model_id":"gpt-4.1","usage":{"input_tokens":1820,"output_tokens":310},"finish_reason":"stop","raw_response_hash":"sha256:9d0c...","parsed_schema":"PlanProposal@v2","repair_attempts":0}}
```

### 5) Strategy proposes privileged read: memory.query_profile

```json
{"ts":"2026-01-06T10:00:01.120Z","name":"tool_intent_proposed","trace_id":"2bb0...","run_id":"a9d1...","payload":{"tool":"memory.query_profile","risk_tier":"medium","principal":"agent:tutor_v1","purpose":"personalize_study_plan","idempotency_key":"sha256:3a7b...","args_hash":"sha256:6c21..."}} 
```

### 6) K5-lite policy decision for privileged read (allow under constraints)

```json
{"ts":"2026-01-06T10:00:01.125Z","name":"policy_decision","trace_id":"2bb0...","run_id":"a9d1...","payload":{"phase":"read","tool":"memory.query_profile","decision":"allow","reason":"tenant_scoped_ok","constraints_applied":{"tenant_id":"school:acme_high"}}}
```

### 7) K4 tool executor executes read; output normalized (still untrusted)

```json
{"ts":"2026-01-06T10:00:01.400Z","name":"tool_call_completed","trace_id":"2bb0...","run_id":"a9d1...","payload":{"tool":"memory.query_profile","outcome":"success","latency_ms":270,"result_hash":"sha256:aa81..."}}
```

### 8) K18 sanitizes tool output before any prompt use

```json
{"ts":"2026-01-06T10:00:01.410Z","name":"sanitize_tool_output","trace_id":"2bb0...","run_id":"a9d1...","payload":{"tool":"memory.query_profile","classification":"L2","suspicion_flags":["contains_instructions:false"],"quoted_data_hash":"sha256:bb10...","provenance":{"source":"tool","tool":"memory.query_profile","result_hash":"sha256:aa81..."}}}
```

### 9) Strategy asks for another model call to draft the plan + propose actions

```json
{"ts":"2026-01-06T10:00:01.420Z","name":"model_call_requested","trace_id":"2bb0...","run_id":"a9d1...","payload":{"prompt_bundle":"tutor_plan_writer_v5","prompt_hash":"sha256:77b3...","expected_schema":"TutorPlanAndActions@v1"}}
```

### 10) K3 model boundary returns structured plan + two proposed actions

```json
{"ts":"2026-01-06T10:00:02.600Z","name":"model_call_completed","trace_id":"2bb0...","run_id":"a9d1...","payload":{"provider":"openai","model_id":"gpt-4.1","usage":{"input_tokens":2650,"output_tokens":820},"finish_reason":"stop","raw_response_hash":"sha256:19c4...","parsed_schema":"TutorPlanAndActions@v1","repair_attempts":0}}
```

### 11) K7 verification: schema + safety checks

```json
{"ts":"2026-01-06T10:00:02.620Z","name":"verification_result","trace_id":"2bb0...","run_id":"a9d1...","payload":{"verifier":"schema_and_safety_v2","status":"pass","notes":["no_L3_in_output","plan_length_ok"]}}
```

### 12) Tool intent proposed: memory.write_profile (medium risk)

```json
{"ts":"2026-01-06T10:00:02.630Z","name":"tool_intent_proposed","trace_id":"2bb0...","run_id":"a9d1...","payload":{"tool":"memory.write_profile","risk_tier":"medium","principal":"agent:tutor_v1","idempotency_key":"sha256:81b0...","args_hash":"sha256:ed90..."}} 
```

### 13) K5 policy decision: allow memory write under constraints

```json
{"ts":"2026-01-06T10:00:02.635Z","name":"policy_decision","trace_id":"2bb0...","run_id":"a9d1...","payload":{"phase":"propose","tool":"memory.write_profile","decision":"allow","reason":"allowed_fields_ok+size_ok"}}
```

### 14) K4 tool preview (diff) + binding hash computed (even if approval not needed)

```json
{"ts":"2026-01-06T10:00:02.650Z","name":"tool_preview_created","trace_id":"2bb0...","run_id":"a9d1...","payload":{"tool":"memory.write_profile","preview_hash":"sha256:5f90...","binding_hash":"sha256:0c11..."}} 
```

### 15) Outbox begin + execute memory write

```json
{"ts":"2026-01-06T10:00:02.660Z","name":"outbox_record_created","trace_id":"2bb0...","run_id":"a9d1...","payload":{"tool":"memory.write_profile","idempotency_key":"sha256:81b0...","status":"pending"}} 
{"ts":"2026-01-06T10:00:02.900Z","name":"tool_call_completed","trace_id":"2bb0...","run_id":"a9d1...","payload":{"tool":"memory.write_profile","outcome":"success","result_hash":"sha256:3d12..."}} 
{"ts":"2026-01-06T10:00:02.905Z","name":"outbox_record_committed","trace_id":"2bb0...","run_id":"a9d1...","payload":{"idempotency_key":"sha256:81b0...","status":"committed"}} 
```

### 16) Tool intent proposed: send_email (high risk)

```json
{"ts":"2026-01-06T10:00:02.920Z","name":"tool_intent_proposed","trace_id":"2bb0...","run_id":"a9d1...","payload":{"tool":"send_email","risk_tier":"high","principal":"agent:tutor_v1","idempotency_key":"sha256:55a8...","args_hash":"sha256:f003..."}} 
```

### 17) K5 policy decision (propose): needs approval

```json
{"ts":"2026-01-06T10:00:02.925Z","name":"policy_decision","trace_id":"2bb0...","run_id":"a9d1...","payload":{"phase":"propose","tool":"send_email","decision":"needs_approval","reason":"high_risk_external_comm","expires_in_sec":300}}
```

### 18) Preview + approval request bound to binding hash

```json
{"ts":"2026-01-06T10:00:02.940Z","name":"tool_preview_created","trace_id":"2bb0...","run_id":"a9d1...","payload":{"tool":"send_email","preview_hash":"sha256:7c12...","binding_hash":"sha256:9a71...","preview":{"to":"stu_123@example.com","subject":"Your 2-week calculus plan","body_hash":"sha256:44af..."}}}
{"ts":"2026-01-06T10:00:02.945Z","name":"approval_required","trace_id":"2bb0...","run_id":"a9d1...","payload":{"binding_hash":"sha256:9a71...","expires_at":"2026-01-06T10:05:02Z","approver":"user:stu_123"}}
```

### 19) User approves (UI event)

```json
{"ts":"2026-01-06T10:00:10.000Z","name":"approval_submitted","trace_id":"2bb0...","run_id":"a9d1...","payload":{"binding_hash":"sha256:9a71...","decision":"approve","approver":"user:stu_123"}}
```

### 20) Commit phase: re-check policy + TOCTOU binding, then execute send_email

```json
{"ts":"2026-01-06T10:00:10.010Z","name":"policy_decision","trace_id":"2bb0...","run_id":"a9d1...","payload":{"phase":"commit","tool":"send_email","decision":"allow","reason":"approval_token_valid+binding_hash_match"}}
{"ts":"2026-01-06T10:00:10.020Z","name":"outbox_record_created","trace_id":"2bb0...","run_id":"a9d1...","payload":{"tool":"send_email","idempotency_key":"sha256:55a8...","status":"pending"}}
{"ts":"2026-01-06T10:00:10.400Z","name":"tool_call_completed","trace_id":"2bb0...","run_id":"a9d1...","payload":{"tool":"send_email","outcome":"success","result":{"status":"sent","message_id":"email_8f12"},"result_hash":"sha256:0ee3..."}}
{"ts":"2026-01-06T10:00:10.405Z","name":"outbox_record_committed","trace_id":"2bb0...","run_id":"a9d1...","payload":{"idempotency_key":"sha256:55a8...","status":"committed"}}
```

### 21) Run completes

```json
{"ts":"2026-01-06T10:00:10.420Z","name":"run_completed","trace_id":"2bb0...","run_id":"a9d1...","payload":{"outcome":"success","steps_used":7,"total_cost_usd":0.06,"high_risk_actions_committed":1,"escalations":0}}
```

---

## What this trace proves (and what it doesn’t)

### It proves (if implemented correctly)
- The actor is non-authoritative: it proposes; the kernel executes (Constitution Article I; Kernel K2/K4/K5).
- Untrusted content never enters instruction channels without sanitization (K18).
- Privileged reads are mediated (K5-lite).
- High-risk actions require approval bound to a hash (K5 + K15).
- Idempotency/outbox prevents duplicate commits on retry/resume (K10).
- You can reconstruct what happened from logs (K9).
- You can replay safely if tool/model recordings are enabled (K11).

### It does not prove
- The plan is pedagogically optimal (that’s strategy).
- The model never hallucinates (it will).
- The email content is “correct” unless you add domain verifiers for correctness claims (K7).

---

## How to use this trace in practice

1. **As a debugging template:** your real traces should look structurally like this.
2. **As an eval case:** copy the scenario into a suite and assert:
   - policy decisions appear,
   - approval is required for `send_email`,
   - commit is impossible without a matching approval token.
3. **As an audit checklist:** auditors can follow the event chain:
   - tool intent → policy decision → preview → approval → commit → outbox.

---

## Suggested next step

Tie this doc into your repo by linking it from `adoption.md` and by adding an eval case that asserts the “no commit without approval” property.