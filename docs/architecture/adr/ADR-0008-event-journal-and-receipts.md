# ADR-0008 — Append-only event journal and immutable action receipts

- **Status:** Accepted
- **Date:** 2026-09-28
- **Related:** ADR-0002, ADR-0006, ADR-0007, ADR-0010
- **Security refs:** `SECURITY_BASELINE.md` SEC-13, SEC-21; `THREAT_MODEL.md` T-12

## Context

What exists today:

| Artefact | Location | Character |
|---|---|---|
| Action log | `logs/{mind_id}/actions.jsonl` | plain file, appended by any process, no integrity, no retention |
| Mind logs | `mind_logger.py` → JSONL | free-text, verbatim reasoning and action details |
| Thought records | SQLite `thoughts` table | per-Mind thought history |
| LLM call records | API `/llm-calls` | usage and cost tracking |
| Conversation | SQLite `conversation_messages` | chat history |

Problems:

1. **No integrity.** Any process (including compromised or model-generated code) can append to or
   edit `actions.jsonl`. There is no hash chain and no signature, so an action cannot be proven
   and behaviour cannot be repudiated or confirmed.
2. **No single timeline.** Action, policy decision, approval, execution, memory write, and affect
   change are recorded in different places with no correlation and no causation linkage. It is
   impossible to answer "why did the Mind send that email?" from the data.
3. **No completeness guarantee.** There is no record for *blocked* or *denied* actions — precisely
   the events a security review needs.
4. **No redaction layer.** Prompts, memory content, and personal data are written verbatim;
   the code executor prints raw subprocess stdout/stderr into process logs.
5. **No retention policy** and no export, which blocks enterprise adoption and data-subject
   requests.

V3 requires an append-only event journal with correlation/causation IDs and immutable
`ActionReceipt`s for allowed, blocked, failed, cancelled, and rolled-back attempts.

## Decision

**Introduce an append-only event journal as the authoritative record of what happened, and an
immutable `ActionReceipt` for every action attempt.**

### 1. Event journal

Append-only table (Postgres) with projections for efficient querying. **Not strict event sourcing
for every table** — V3 §13 explicitly warns against that in the first migration. Domain tables
remain the source of truth for current state; the journal is the source of truth for *history*.

Required event families (from V3 §13): `mind.*`, `identity.*`, `constitution.*`, `relationship.*`,
`goal.*`, `commitment.*`, `experience.recorded`, `memory.*` (proposed/accepted/rejected/corrected/
disputed/superseded/forgotten/deleted), `skill.*`, `action.*` (proposed/policy_evaluated/
approval_requested/approved/rejected/expired/executing/executed/failed/rolled_back/
**blocked**), `embodiment.*`.

Every event carries: event id, type, **schema version**, timestamp (UTC, tz-aware), tenant id,
mind id, actor type, actor id, **correlation id**, **causation id**, **redacted payload**, and an
**integrity hash**.

### 2. Action receipts

Every action attempt — allowed, blocked, failed, cancelled, or rolled back — produces a receipt:
action id, mind/tenant/objective id, requested intent, selected skill, **redacted arguments +
arguments hash**, risk level, policy decision, approval identity + timestamp, start/completion
time, outcome, affected resources, artifacts, evidence, model invocations, cost, error
classification, rollback information, and an integrity hash.

Receipts are **user-visible in the Mind Workspace** — this is a product feature, not just
compliance machinery.

### 3. Integrity

Events and receipts are hash-chained **within a mind/tenant stream** and signed where a signing
key exists (ADR-0010). Verification is a first-class operation with a test. Tampering is
detectable, not merely discouraged.

### 4. Redaction by construction

Payloads are redacted **before** persistence: no secrets, tokens, credentials, unnecessary
personal data, or sensitive memory content. Redaction happens in the writer, so a caller cannot
bypass it. Raw prompts are not stored unless explicitly required and consented.

### 5. Observability is separate

Traces/metrics (ADR-0009 observability, plan B17) are for **operations**. The journal is for
**accountability**. Both may reference the same correlation id, but the journal must be complete
even if tracing is disabled — the system must function without the optional observability product.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Keep JSONL file logs | No integrity, no correlation, no atomicity, no queryability, no retention |
| Strict event sourcing for all state | Large change, hard to migrate, not required; V3 warns against it initially |
| Rely on OpenTelemetry traces as the audit record | Sampling, retention limits, and mutable backends make traces unsuitable for accountability |
| Blockchain / distributed ledger | Unjustified complexity; a hash-chained, signed append-only table delivers verifiability without consensus |
| Log everything verbatim to maximize evidence | Violates privacy obligations and creates a new breach surface; redaction is mandatory |
| Store blocked actions only in application logs | Denials are the highest-interest security events and must be queryable and exportable |

## Consequences

**Positive**
- Makes "accountable autonomy" concrete: every decision and outcome is attributable and
  explainable.
- Enables audit export, compliance review, incident reconstruction, and user-facing action history.
- Creates the evidence base for evals: goal completion, unjustified autonomy, intervention rate.
- Blocked-action records turn policy tuning from guesswork into data.

**Negative / costs**
- Every write path must emit events — discipline plus a helper/service to make it the path of
  least resistance.
- Storage growth requires partitioning and retention policy design.
- Hash chaining means concurrent writers need per-stream ordering care.

## Risks

| Risk | Mitigation |
|---|---|
| Journal becomes an ungoverned surveillance record | Redaction by construction; retention limits; **explicit prohibition** of covert employee monitoring (V3 §35, plan K6) |
| Missing events silently break the audit trail | An eval asserts a required-event set for a sample objective; receipts are mandatory (a missing receipt is itself an incident) |
| Performance cost of signing/hashing | Hash per event (cheap), sign per batch/stream segment |
| Schema drift across versions | Every event carries `schema_version`; readers tolerate older versions |
| Payload redaction missed → leakage | Redaction in the writer; tests feed secrets through every event type and assert absence |

## Reversibility

**High for implementation, low for the principle.** Additional event types are additive. Removing
the journal would remove accountability evidence that the product's value proposition depends on,
so it is not a candidate for reversal.

## Migration effect

- Plan items **B15** (service + receipts), **D1–D3** (tables, backfill, correlation IDs),
  **B17** (tracing alongside, not instead), **K3** (audit export).
- Backfill: emit synthetic `mind.born` events from existing `minds` rows, preserving ids.
- `logs/actions.jsonl` becomes a projection; the file may be written for one release for
  compatibility, then retired.
- New entities: `AuditEvent`, `ActionReceipt`, and their migrations.
