# ADR-0001 — Modular monolith before microservices

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Principal Architect
- **Related:** ADR-0005, ADR-0007, ADR-0009

## Context

The V3 plan defines ~14 logical packages (`genesis-kernel`, `genesis-memory`,
`genesis-policy`, …) and ~6 services (`api`, `workflow-worker`, `sandbox-manager`, …).

The current repository is a **single Python package** (`genesis/`, 155 modules) shipped as one
distribution. `Mind` (`genesis/core/mind.py`) is a god-object that constructs identity, affect,
lifecycle, memory, plugins, agents, execution, and integrations in `__init__`. Nothing has a
stable interface; there are no service boundaries; storage is three uncoordinated stores
(SQLite + ChromaDB + JSON).

Two pressures pull in opposite directions: the target architecture wants clear boundaries, while
the migration constraints (V3 §5.12–5.16) forbid a big-bang rewrite and require backward
compatibility.

## Decision

**Adopt a modular monolith with enforced internal module boundaries, and defer any
microservice extraction until those boundaries are clean and tested.**

Concretely:

1. Create the logical package boundaries **inside the existing `genesis/` layout first**
   (`genesis/governance/`, `genesis/sandbox/`, `genesis/observability/`, …) rather than
   moving to a `packages/` monorepo.
2. Each boundary is expressed as an **interface (Protocol/ABC) + an implementation**, with
   dependency direction pointing inward (domain must not import transport/framework code).
3. Introduce `MindFacade` first (Phase C) so the public surface is frozen before internals move.
4. Extract one service per change, each with a re-export shim so existing imports keep working.
5. Move files/directories only after compatibility tests pass.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Immediate `packages/` monorepo with uv/workspaces | High churn, breaks `pip install -e .`, no test coverage to catch regressions (suite is red at baseline) |
| Extract microservices now (api + worker + sandbox-manager) | Premature: boundaries undefined, so the seams would be wrong. Also multiplies operational surface for a single-VPS deployment |
| Leave as-is, refactor opportunistically | No enforced boundary ⇒ the god-object regrows; ADR would be meaningless |
| Full DDD rewrite of `Mind` | Explicitly forbidden by V3 §5.13; would discard working behaviour |

## Consequences

**Positive**
- Boundaries become enforceable and testable without changing deployment topology.
- The single-container deployment keeps working throughout (ADR-0017).
- Each extraction is individually revertible.
- Avoids distributed-systems failure modes while the domain model is still moving.

**Negative / costs**
- Boundaries are conventions, not physical enforcement — needs lint/import rules and review
  discipline to prevent violations.
- Some duplication during the transition (old path + facade path).
- A later extraction to real services is still required work.

## Risks

| Risk | Mitigation |
|---|---|
| Boundaries drift as new code lands | Add an import-linter rule in CI (plan A6) |
| Facade becomes a second god-object | Facade delegates only; no new logic inside it; cap its size in review |
| Extraction changes behaviour silently | Extract-only commits, no semantic changes bundled; watermark test run per commit |

## Reversibility

**High.** Internal module boundaries are cheap to dissolve. Nothing here commits to a
deployment topology. The facade can be kept indefinitely.

## Migration effect

- **No data migration.**
- Plan items: A6 (CI import rules), C1–C11 (extraction sequence).
- The target `packages/` and `services/` layouts in V3 §9 are treated as **eventual**, reached
  only after Phase C stabilises.
