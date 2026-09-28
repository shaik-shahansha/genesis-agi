# ADR-0007 — Approval service as a persistent state machine

- **Status:** Accepted
- **Date:** 2026-09-28
- **Related:** ADR-0006, ADR-0008, ADR-0015
- **Security refs:** `SECURITY_BASELINE.md` SEC-11; `THREAT_MODEL.md` T-11

## Context

`genesis/core/autonomy.py` defines a permission ladder
(`ALWAYS_ALLOWED`, `AUTO_APPROVED_WITH_LOG`, `REQUIRES_CONFIRMATION`,
`REQUIRES_APPROVAL_WITH_REVIEW`, `ABSOLUTELY_FORBIDDEN`) and `autonomy.py` maps action names to
levels. `genesis/safety/permissions.py` then implements it as:

```python
if permission_level == PermissionLevel.REQUIRES_CONFIRMATION:
    # For now, deny (in production, would ask user)
    return False, "Requires user confirmation (not implemented in auto mode)"

if permission_level == PermissionLevel.REQUIRES_APPROVAL_WITH_REVIEW:
    return False, "Requires user approval with review"
```

Three consequences:

1. **The control does not exist.** There is no queue, no request record, no surface, no expiry,
   and no way for a human to approve anything. The code comment says so.
2. **The system is described as autonomous but cannot close the loop** on any consequential
   action. Every confirmation-required action is silently refused, which is a *product* gap as
   much as a safety gap.
3. **The configuration lies.** `settings.require_approval_for_external_actions = True` implies a
   working approval path.

The only adjacent artefact is an append-only-ish JSONL action log
(`logs/{mind_id}/actions.jsonl`) which records outcomes but cannot grant permission, cannot
expire, and has no integrity protection.

## Decision

**Implement an `ApprovalService` as a persistent, auditable state machine, and require explicit
approval for consequential, external, irreversible, or privileged actions.**

### State machine

```
PROPOSED → POLICY_EVALUATED → WAITING_FOR_APPROVAL
                                 ├─ APPROVED
                                 ├─ REJECTED
                                 └─ EXPIRED
                                        ↓
                                    EXECUTING
                                        ├─ COMPLETED
                                        ├─ FAILED
                                        └─ ROLLED_BACK
```

### Binding rules (the security core of this ADR)

1. **Bound to exact parameters.** An approval binds to a hash of the action's material
   parameters. **Changing any material parameter invalidates the approval.**
2. **Bound to an exact scope** (this mind, this recipient, this resource path, this amount).
3. **Bound to an expiry.** A grant that is not used in time expires.
4. **Non-transferable by default.** A grant for one mind, user, or objective does not apply to
   another.
5. **Revocable while not yet executed.** Once execution has begun, the escape hatch becomes
   rollback, not revocation.
6. **Every transition is an audit event** (ADR-0008).

### Request content (plain language, for a non-engineer)

requested action · reason · expected impact · data accessed · external recipient · financial cost
· reversibility · risk level · requested duration · scope · expiry · proposed rollback · evidence.

### Surfaces

Approval requests must be actionable outside the web app: email, Slack/Teams, and mobile push,
plus an in-app inbox with a badge. The web workspace must show *what needs approval, why, what it
costs, and what can be reversed* (V3 §40).

### Persistence and durability

Approvals live in the canonical store (ADR-0002) and survive restart. A Mind waiting on approval
is **durably suspended**, not spinning — this connects to the durable runtime (ADR-0015).

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Keep deny-by-default (status quo) | Makes autonomy unusable; configuration is misleading; the stated product promise is unfulfillable |
| Auto-approve with logging | Removes the human from consequential actions; unacceptable for R3/R4 |
| Approve-by-prompt ("are you sure?") inside the chat turn | Not durable, not attributable, easily socially engineered, unusable for long-running objectives |
| Time-boxed blanket grants only (no per-action approval) | Useful for R1/R2 convenience and adopted as *standing grants*, but insufficient alone for R3/R4 |
| Approvals in Redis / in-memory | Lost on restart; violates durability and audit requirements |

## Consequences

**Positive**
- The permission ladder finally functions; the Mind can act autonomously *and* safely.
- Every consequential action has an attributable, revocable human decision.
- Enables R2/R3/R4 capabilities that are currently impossible (external email, purchases, deploys).
- Directly supplies the "approval inbox" and "action receipts" surfaces V3 requires.

**Negative / costs**
- New tables, migrations, services, notification integrations, and UI.
- Human latency becomes part of some workflows; the agent loop must handle suspension/resumption.
- Notification channels are themselves a privacy and security surface (who can approve?).

## Risks

| Risk | Mitigation |
|---|---|
| Approval fatigue → rubber-stamping | Standing grants for low-risk recurring actions; batch similar requests; keep requests rare and meaningful |
| Parameter-binding miss lets an approved action change | Hash all material parameters; freeze the exact serialized request; test mutation-invalidates-approval |
| Replay of an approval | Single-use grants, idempotency keys, and an execution lock |
| Wrong person approves (esp. organizational minds) | Explicit approver policy per risk level and per tenant (Phase K); record approver identity |
| Suspended objectives accumulate | Heartbeat surfaces pending approvals; expiry closes stale ones; budget/time limits bound waiting |

## Reversibility

**High.** The approval path is additive. An operator can widen auto-approval for specific
low-risk classes, but the state machine and audit trail remain. Reducing controls below R3
requires an explicit, logged organizational decision (Phase K).

## Migration effect

- Plan items **B14** (service + state machine), **B7/B15** (surfaces + audit), **D** (durable
  suspension), **H/G6** (approval inbox UI).
- New entities: `ApprovalRequest`, `PermissionGrant`, `ActionRequest`, `ActionReceipt`.
- `PermissionLevel.REQUIRES_CONFIRMATION` and `REQUIRES_APPROVAL_WITH_REVIEW` stop being
  permanent denials and become routable states — preserving the enum while changing behaviour.
