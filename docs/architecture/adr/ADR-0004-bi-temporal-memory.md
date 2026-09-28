# ADR-0004 — Bi-temporal memory (valid-time vs ingestion-time)

- **Status:** Accepted
- **Date:** 2026-09-28
- **Related:** ADR-0002, ADR-0003, ADR-0013

## Context

Memory today models time as **a single scalar decay multiplier**:

```python
# genesis/storage/memory.py (~line 89)
# Temporal decay (1% per day, exponential)
```
```python
# genesis/storage/memory.py (~line 76)
"""Calculate current relevance score with temporal decay."""
```

Consequences of this design:

1. A memory is either **present or faded**. There is no way to express *"X was true in March but
   was superseded in July"* — the July fact and the March fact compete purely on similarity and
   decay, so the stale one can win.
2. **No `valid_from` / `valid_to`.** The system cannot answer "what did I believe on date D?" or
   "was this true at the time I acted?"
3. **No contradiction record and no supersession.** Conflicting facts coexist silently.
4. **No provenance.** `memory_extractor.py` writes LLM-derived facts with no record of the
   source (conversation, tool, observation, document) or its trust level — so a poisoned document
   becomes a durable, high-trust belief (see `THREAT_MODEL.md` T-10).
5. **No confidence separation.** Importance exists; confidence does not. A guess and a verified
   fact are indistinguishable at retrieval time.
6. **No user correction path.** Because revisions are not modelled, a user cannot correct,
   dispute, or supersede a memory — and deletion cannot reliably purge derived indexes.

A being that is expected to live for years and to act on what it remembers needs memory that can
represent **change over time** and **where a belief came from**.

## Decision

**Adopt bi-temporal memory records with explicit provenance.**

Every canonical memory carries:

| Group | Fields |
|---|---|
| Identity | memory id, mind id, tenant id, memory type, revision number |
| Content | content, normalised claims |
| **Ingestion time** | `created_at` (when the Mind learned it), `last_verified_at` |
| **Valid time** | `valid_from`, `valid_to` (when it was true in the world) |
| Provenance | source references (conversation/tool/observation/document id), provenance type, trust level |
| Epistemics | confidence, importance, sensitivity, access scope |
| Lifecycle | status, `superseded_by`, contradiction references, retention policy |
| Indexes | embedding reference, graph reference |

Rules:

1. **Two timelines are never conflated.** "When we learned it" and "when it was true" are
   separate columns and separate query filters.
2. **Retrieval is validity-filtered by default.** A query returns facts valid at the requested
   time (default: now), with superseded records excluded unless explicitly requested.
3. **Supersession is explicit.** A new fact that replaces an old one sets `valid_to` on the old
   record and links `superseded_by`. It never deletes.
4. **Contradictions are recorded, not resolved by similarity.** A contradiction reference is
   stored and surfaced to the Mind and the user rather than being silently out-ranked.
5. **Provenance and trust are mandatory.** Every write records where it came from; trust is
   carried into ranking and into policy evaluation.
6. **Decay becomes a ranking signal, not a truth signal.** The old 1%/day multiplier is retained
   only as one input to ranking and no longer implies anything about validity.
7. **Correction is first-class.** A user correction sets confidence/label and supersedes the
   previous revision, preserving the audit trail.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Keep decay-only (status quo) | Cannot represent supersession or answer time-scoped questions; the core failure this ADR addresses |
| Delete superseded memories | Destroys the audit trail and answers to "what did you believe then?"; breaks accountability |
| Event-source all memory | Over-engineered for this stage; V3 explicitly warns against strict event sourcing for every table in the first migration |
| Put temporal handling only in the graph | The graph is an optional derived index (ADR-0016); temporal correctness must survive with the graph disabled |
| Store only "current truth", no history | Loses the ability to explain past actions from the beliefs held at the time (a stated V3 evaluation requirement) |

## Consequences

**Positive**
- Enables time-scoped recall, stale-fact detection, and correct explanation of past actions.
- Makes poisoning tractable: untrusted provenance is recorded and can be discounted or blocked.
- Gives supersession, contradiction, and deletion well-defined semantics (ADR-0003 indexes purge
  becomes deterministic).
- Directly satisfies V3 evaluation criteria: temporal recall, contradiction handling, stale-fact
  handling, memory correction, memory deletion.

**Negative / costs**
- More columns and more complex write path (proposal → validate → supersede/contradict → write).
- Every read path must apply validity filters correctly; a missed filter is a correctness bug.
- Contradiction detection needs a strategy (embedding proximity + claim comparison) and will
  produce false positives to tune.

## Risks

| Risk | Mitigation |
|---|---|
| Validity filters forgotten on some read path | Centralise in `MemoryStore.search`; forbid ad-hoc collection queries |
| Contradiction false positives annoy users | Record contradictions as advisory; surface with evidence; never auto-delete |
| Backfill invents `valid_from` for legacy rows | Backfill `valid_from = ingested_at` explicitly and mark the row as inferred; document it |
| Supersession chains become deep | Cap chain traversal depth and always prefer the head; expose the chain to the user |

## Reversibility

**Medium.** Adding columns is additive and safe. The *behavioural* change (validity-filtered
retrieval, supersession instead of deletion) is the hard-to-reverse part, and it is a deliberate
correctness improvement. Legacy rows keep working via backfilled defaults.

## Migration effect

- Plan items **E1** (schema), **E4** (backfill with explicit inferred markers), **E6** (proposal
  pipeline), **E7** (user controls), **E10** (temporal/contradiction evals).
- `memory_tools.py` self-editing must become **proposal-based**; the LLM may no longer mutate
  canonical memory directly (V3 §17).
