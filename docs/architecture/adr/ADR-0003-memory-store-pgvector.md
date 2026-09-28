# ADR-0003 — Memory: provider-neutral `MemoryStore` with pgvector as the default

- **Status:** Accepted
- **Date:** 2026-09-28
- **Related:** ADR-0002, ADR-0004, ADR-0016

## Context

Memory today is `SmartMemoryManager` (`genesis/storage/smart_memory.py`) extending
`MemoryManager` (`memory.py`), backed by `VectorStore` (`vector_store.py`):

```python
import chromadb                       # hard import at module scope
...
self.collection = self.client.get_or_create_collection(name=f"mind_{mind_id}")
self.collection.add(documents=[content], ids=[memory_id], metadatas=[...])
```

Findings:

1. **`chromadb` is a hard dependency**, imported directly — there is no provider seam. The
   README's claim that memory has "zero external dependencies" is false.
2. **Embeddings are ChromaDB's default function.** No embedding model is configured anywhere,
   so the model is implicit and version-coupled to the library.
3. **Retrieval is dense-only.** Exact identifiers, dates, names and codes — the things a
   long-lived assistant most needs to recall — are poorly served by dense vectors alone.
4. **Reranking is LLM-based** (`memory_reranker.py`), which is slow and costs tokens per query.
5. Memory semantics worth keeping: 5 types, importance scoring, access counts, decay as a
   relevance multiplier, dedup at ~85% similarity, consolidation, and agent self-editing.

V3 requires the memory *substrate* to be replaceable without touching call sites, and requires
hybrid retrieval with provenance.

## Decision

**Introduce a `MemoryStore` interface; keep `SmartMemoryManager` as the facade; make
PostgreSQL + `pgvector` the default implementation; demote ChromaDB to a legacy adapter.**

Interface responsibilities: `add`, `get`, `update`, `delete`, `search` (hybrid), `list`,
`count`, `purge_indexes`. The interface deals in **domain memory records**, not vendor rows.

Retrieval becomes **hybrid**: dense (pgvector) + lexical (PostgreSQL FTS) combined with
Reciprocal Rank Fusion, followed by a **cross-encoder reranker** replacing the LLM reranker.
Repeated-question reranking is cached.

Dedup, consolidation, and decay are **retained as domain behaviour** but implemented on the
canonical store rather than inside a vendor client.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Keep ChromaDB as primary | No provenance/transactions/RLS; vendor-coupled embeddings; second store to keep consistent |
| Qdrant / Weaviate as primary vector store | Introduces a second datastore for no gain over pgvector at this scale; adds an operator dependency |
| Keep LLM reranking as the only reranker | Per-query token cost and latency; cross-encoder is cheaper and better for this ranking task |
| Dense-only retrieval (unchanged) | Documented failure mode for exact-match recall; a digital being must recall a name or an ID |
| Agent-managed memory format (e.g. Letta-style blocks as the store) | Blocks are useful as *working memory* and are retained, but they are not an archival substrate |

## Consequences

**Positive**
- Memory substrate becomes swappable (pgvector locally, managed Postgres in cloud, edge mode on SQLite+sqlite-vec).
- Hybrid retrieval materially improves exact-match and date recall.
- Transactions make provenance, supersession, and index purge sound (ADR-0004).
- Removes a hard third-party dependency from the core path.

**Negative / costs**
- Migration from ChromaDB to pgvector requires backfill + validation.
- Two retrieval systems coexist during transition (mitigated by the adapter).
- Cross-encoder adds a model artifact to ship and warm up.

## Risks

| Risk | Mitigation |
|---|---|
| Recall regressions after the swap | Golden eval set (plan B18/E10) before and after; keep the adapter as a fallback |
| Embedding-model change invalidates existing vectors | Version the embedding model in the record; re-embed as an explicit, resumable job |
| Hybrid weighting poorly tuned | Make the fusion constant configuration, not a magic number; measure on the eval set |
| Cross-encoder latency | Cache; run only on the top-N candidate set |

## Reversibility

**Medium-high.** The interface is the reversible part — ChromaDB stays behind an adapter until
validation passes, so the read path can be switched back. Once pgvector holds the only copy of
new data, the data migration is one-way (mitigated by retaining the legacy store read-only).

## Migration effect

- Plan items **E1–E5**, **E10**.
- `storage/smart_memory.py` keeps its public methods; internals delegate to `MemoryStore`.
- Embedding-model choice becomes explicit configuration (currently implicit).
