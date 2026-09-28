# ADR-0002 — Canonical persistence: PostgreSQL, with SQLite as the edge mode

- **Status:** Accepted
- **Date:** 2026-09-28
- **Related:** ADR-0003, ADR-0004, ADR-0006

## Context

The current system writes to **three stores with no single source of truth**:

| Store | Contents | Location |
|---|---|---|
| SQLite (SQLAlchemy 2 + Alembic) | minds, conversations, tasks, GEN ledger, thoughts, access control (17 tables) | `genesis_home/genesis.db` |
| ChromaDB (persistent client per Mind) | memory vectors | `data_dir/chroma/{mind_id}` |
| JSON files | Mind identity/state, plugin config, action logs (JSONL) | `minds_dir`, `logs_dir` |

Verified problems:

1. **No cross-store transaction.** A memory can be written to ChromaDB while the related
   conversation write fails (or vice versa), leaving divergent state with no repair path.
2. **No tenancy.** No tenant column anywhere; `mind_access` is a per-mind grant table only.
3. **Deletion is incomplete.** Deleting a memory does not purge its vector entry as part of one
   unit of work.
4. **Path split.** `database_url`'s default (`sqlite:///genesis.db`) is ignored by
   `database/base.py` and `alembic/env.py`, which both derive the path from `genesis_home`
   instead — two sources of truth for a single file.
5. SQLite serialises writers, which conflicts with concurrent Minds in one process.
6. V3 requires row-level security, tenant isolation, audit export, and legal hold — none of
   which SQLite supports.

## Decision

**PostgreSQL is the canonical store for all durable domain state**, with `pgvector` for
embeddings, PostgreSQL full-text search for lexical retrieval, and object storage for blobs.
**SQLite remains a supported edge/local mode**, obtained by keeping the SQLAlchemy repository
interfaces dialect-agnostic.

Rules:

1. The domain layer talks to **repository interfaces**, never to a raw engine.
2. All durable writes for one logical operation happen in **one transaction**.
3. Redis is **ephemeral only** (cache, locks, event fan-out) — never a source of truth.
4. Blobs (workspace files, artifacts, exports) go to S3-compatible storage, not the database.
5. `database_url` becomes the single authoritative configuration; the `genesis_home`-derived
   path is removed (see ADR-0017 for the container implication).

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Stay on SQLite | Cannot satisfy RLS, tenancy, concurrent writers, or audit/legal-hold requirements |
| Keep three stores, add reconciliation jobs | Reconciliation cannot recover information lost by a non-atomic write; complexity without a correctness guarantee |
| MongoDB / document store | Loses relational integrity for identities, grants, approvals, and audit chains that are inherently relational |
| Embed a graph DB as the primary store | Graph is a derived index (ADR-0016), not an authority; would couple core state to an optional component |
| Postgres + ChromaDB side by side (dual store) | Keeps the divergence problem; acceptable only as a *temporary* migration step |

## Consequences

**Positive**
- One transactional authority ⇒ provenance, supersession, and deletion become sound.
- Unlocks RLS, tenancy, audit export, legal hold, and cost/usage reporting.
- `pgvector` + FTS gives hybrid retrieval in one database (ADR-0003, ADR-0004).
- SQLite edge mode preserves the "runs on your laptop, fully private" differentiator.

**Negative / costs**
- Operational surface grows for self-hosters (a database to run).
- Requires the migration tooling in `MIGRATION_STRATEGY.md` §4 before anything can be deleted.
- Alembic history must be reconcilable with databases created by `create_all()`.

## Risks

| Risk | Mitigation |
|---|---|
| Data loss during migration | Dry-run + resume + count/checksum validation; **never delete the old store until validation passes** (V3 §45) |
| Dual-write divergence during transition | Feature-flagged dual-write with the legacy store still authoritative until read-switch; explicit cutover step |
| Dialect-specific SQL creeping in | Repository interfaces + run the test suite against both dialects in CI |
| Self-hosters blocked by Postgres requirement | Keep SQLite as a first-class edge mode and default for local dev |

## Reversibility

**Medium.** Moving to Postgres is a one-way door for *data*, but not for *code*: keeping
repository interfaces dialect-agnostic preserves the ability to run on SQLite. The migration
itself is reversible in practice because the legacy store is retained read-only.

## Migration effect

- Plan items **A2** (test isolation), **E1–E4** (memory schema + migrator), **K1** (tenants/RLS).
- Requires resolving the `database_url` vs `genesis_home` contradiction (ADR-0017).
- Alembic gains a `stamp` path for pre-existing `create_all()` databases
  (already implemented in `deploy/docker/entrypoint.sh`).
