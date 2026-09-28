# ADR-0006 — Deterministic policy engine (replacing the keyword constitution)

- **Status:** Accepted
- **Date:** 2026-09-28
- **Related:** ADR-0005, ADR-0007, ADR-0008
- **Security refs:** `SECURITY_BASELINE.md` SEC-12; `THREAT_MODEL.md` T-08, T-19

## Context

Governance today is `genesis/core/constitution.py`:

```python
HARMFUL_KEYWORDS = {"violence": ["kill", "murder", ...], "illegal": ["hack", "steal", ...], ...}

def validate_user_prompt(self, prompt):
    prompt_lower = prompt.lower()
    for category, keywords in self.HARMFUL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in prompt_lower:          # substring match
                return False, message, violation
```

The README claims violations "cannot be bypassed via prompt injection". That is false:

1. **It is a substring scan on the user prompt only.** It is not applied to tool arguments, code
   being executed, retrieved document content, web results, or MCP tool descriptions.
2. **Trivially bypassable** by paraphrase, encoding, another language, or by placing the
   instruction in any retrieved content.
3. **`validate_action` trusts model self-reporting** for the worst case:
   `if action_type in ["modify_core", "disable_safety", "bypass_rules"]` — the model must
   volunteer that it is doing something forbidden.
4. **No risk model.** "send an email" and "delete a database" have no differentiated treatment.
5. **No context.** Tenant policy, ownership, data sensitivity, cost, reversibility, external
   impact, and lifecycle state are all ignored.
6. **The adjacent permission model cannot act.** `permissions.py` returns
   `"Requires user confirmation (not implemented in auto mode)"` → denied, so
   `require_approval_for_external_actions=True` is effectively a global off-switch for
   confirmation-required actions rather than a working control.

Meanwhile the setting `require_approval_for_external_actions` exists and implies a policy system
that was never built.

## Decision

**Governance becomes deterministic, context-aware, and enforceable at the action boundary —
not the prompt boundary.**

### 1. Policy engine

`PolicyEngine` with a Genesis-owned interface. **Python-native rules first** (testable, no new
runtime, fits the existing repo). An **OPA/Rego adapter** is optional for enterprise policy; a
Cedar adapter interface is reserved.

### 2. Evaluate at the boundary that matters

Policy is evaluated on the **`ActionRequest`**, immediately before execution — after the plan is
formed and before any capability is invoked. Prompt scanning is retained only as an early,
advisory filter, never as the control.

### 3. Risk levels R0–R5

| Level | Meaning | Default disposition |
|---|---|---|
| R0 | read-only public / owner-authorized data | allow |
| R1 | reversible action inside the Mind's isolated workspace | allow_with_receipt |
| R2 | modifies a connected external workspace | require_approval |
| R3 | external communication, deployment, purchasing, privileged admin | require_approval |
| R4 | legal, medical, financial, employment, safety-critical, physical-world impact | require_approval + human |
| R5 | prohibited / destructive / constitutionally disallowed | deny / emergency_stop |

### 4. Decisions

`allow` · `allow_with_receipt` · `require_approval` · `deny` · `emergency_stop`

### 5. Policy context is explicit and complete

Constitution, tenant policy, user permissions, ownership, skill risk, data sensitivity,
recipient, resource affected, cost, reversibility, external impact, physical impact, lifecycle
state, emergency-stop state, objective scope, available budget, and trust level of any external
server.

### 6. A model-based classifier may advise but is never authoritative

An LLM risk classifier is an **advisory signal only**. The final decision is deterministic. This
is deliberately asymmetric: a probabilistic component can raise risk, never lower the required
control below what deterministic rules demand.

### 7. The constitution becomes executable and versioned

The human-readable charter text is **kept**. It is mapped into versioned, machine-enforceable
rules with: what the Mind may do, must not do, what requires approval, what users may request,
what organizations may configure, memory handling, relationship representation, and pause /
export / transfer / archive / retire procedures. `constitution.py` becomes the charter +
adapter, not the mechanism.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Improve the keyword lists | Fundamentally the wrong layer; a blacklist cannot enumerate harmful intent |
| Prompt-only guardrails (system prompt rules) | Model output is untrusted by definition; V3 §5.4 forbids the LLM from being the authority |
| LLM-as-judge as the final authority | Non-deterministic, prompt-injectable, and unauditable; may advise only |
| OPA/Rego as the *only* engine | Adds a sidecar/runtime dependency for a single-VPS deployment; better as an enterprise adapter |
| Always require human approval | Destroys autonomy, the product's core value; must be risk-tiered |
| Full ABAC engine (XACML-style) now | Over-engineered before tenancy exists (Phase K) |

## Consequences

**Positive**
- Makes the security model meaningful: injection may still happen, but no consequential action
  occurs without a deterministic decision.
- Satisfies "accountable autonomy": every decision is explainable from recorded context.
- The same engine serves users, tenants, and organizations without duplicated logic.
- Unblocks the approval system (ADR-0007) by defining what needs approval.

**Negative / costs**
- Policy rules are code and must be reviewed and versioned like code.
- Every new capability must declare risk, scopes, cost class, and reversibility — friction that is
  intentional.
- Centralised enforcement is a single point of failure; must fail **closed**.

## Risks

| Risk | Mitigation |
|---|---|
| Misclassification lets something consequential through as R0/R1 | Conservative defaults; unknown capability ⇒ R3 minimum; tests per level; periodic review |
| Over-blocking makes the Mind useless ("false refusals") | Track false-refusal rate as an eval metric (plan B18); allow scoped, time-boxed standing grants |
| Policy engine becomes a bottleneck | Pure/deterministic evaluation with no I/O; rules cached; decision logged async |
| Rules drift from the charter text | Charter and rules are versioned together; a test asserts every charter clause maps to ≥1 rule |
| Fail-open on engine error | Explicitly fail closed and emit an audit event; tested |

## Reversibility

**Medium.** Rules are data/code and can be edited. The *decision to enforce deterministically at
the action boundary* should not be reversed — it is the foundation of accountable autonomy.

## Migration effect

- Plan items **B13** (engine), **B16** (constitution → versioned rules), plus **B14/B15** for
  approval and audit.
- `constitution.validate_user_prompt` / `validate_action` keep their signatures as shims that
  delegate to the engine, preserving existing call sites.
- New domain entities: `PolicyDecision`, plus a rules table/migration.
