# GAP_ANALYSIS.md

> Difference between what exists (`CURRENT_STATE.md`, `FEATURE_REALITY_MATRIX.md`) and what
> V3 requires. Each gap states the blocking phase and the smallest safe move.

---

## 1. Structural gaps

| # | Gap | Evidence | Blocks | Smallest safe move |
|---|---|---|---|---|
| G-01 | `Mind` is a god-object owning identity, affect, lifecycle, memory, plugins, agents, execution, integrations | `core/mind.py` (~1200+ lines, dozens of subsystems constructed in `__init__`) | C, D, G, L | Extract `MindFacade` first, delegating to existing attributes; no behaviour change |
| G-02 | No kernel boundary between orchestration and side effects | Model output flows into execution with no typed decision object | B, G | Introduce `ActionRequest`/`PolicyDecision`/`ActionReceipt` types before changing behaviour |
| G-03 | No service boundaries | Domain logic lives in `core/`, routes call `Mind` directly | C, K | Define interfaces; keep implementations in place |
| G-04 | No event journal | No events table, no correlation IDs | D | Append-only table + `AuditService` writer |
| G-05 | Storage is three uncoordinated stores | SQLite + ChromaDB + JSON | E, K | Declare Postgres canonical (ADR); keep adapters during migration |
| G-06 | Process-local shared mutable state | `_get_cached_mind` returns one `Mind` per GMID | B, K | Add per-request scoping and locking; then externalise |

---

## 2. Security gaps (blocking — see `SECURITY_BASELINE.md`)

Gaps G-07 … G-16 are **blocking gates**. No autonomy, voice, interop, or embodiment work may
proceed until they are closed.

| # | Gap | Phase |
|---|---|---|
| G-07 | No `SandboxProvider`; three unsandboxed execution paths | B |
| G-08 | Network egress unrestricted from generated code | B |
| G-09 | Runtime package installation from model output | B |
| G-10 | Arbitrary host file write via workspace filename | B |
| G-11 | Unauthenticated WebSocket with spoofable identity | B |
| G-12 | Full `os.environ` inherited by MCP subprocesses | B |
| G-13 | Advertised import allow-list not enforced | B |
| G-14 | No `PolicyService`; keyword blocklist only | B |
| G-15 | No `ApprovalService`; confirmation requirement unimplementable | B |
| G-16 | No `AuditService`/receipts; logs mutable and unsigned | B |

---

## 3. Governed autonomy gaps

| # | Gap | Today | V3 requirement | Phase |
|---|---|---|---|---|
| G-17 | Risk classification | none | R0–R5 deterministic classification | B |
| G-18 | Approval state machine | `PermissionLevel` enum only | PROPOSED→…→ROLLED_BACK with expiry and revocation | B |
| G-19 | Decision explainability | none | plain-language reason, impact, reversibility, evidence | B |
| G-20 | Idempotent side effects | none | idempotency keys; no duplicate external actions after retry | G |
| G-21 | Pause / emergency stop | none | `PAUSED` and `EMERGENCY_STOPPED` modes | B/G |
| G-22 | Budget enforcement | token counters only | per-objective budgets, hard stop | G |
| G-23 | Reversibility / rollback | none | declared rollback + `action.rolled_back` | G |

---

## 4. Memory gaps

| # | Gap | Today | V3 requirement | Phase |
|---|---|---|---|---|
| G-24 | Provenance | none | source refs, retrieval explanation | E |
| G-25 | Bi-temporality | decay multiplier | valid-from/valid-to + ingestion time + last-verified | E |
| G-26 | Confidence & importance | importance only | explicit confidence, sensitivity, access scope | E |
| G-27 | Contradiction & supersession | none | records + retrieval-time resolution | E |
| G-28 | User control | read-only list | inspect / correct / dispute / restrict / supersede / prevent retrieval / delete / export | E |
| G-29 | Deletion completeness | none | transactional purge of vector + graph indexes | E |
| G-30 | LLM write authority | LLM edits memory directly | LLM proposes; deterministic service applies | E |
| G-31 | Retrieval quality | dense-only, default embeddings | hybrid (dense+BM25+RRF) + cross-encoder rerank | E |
| G-32 | Temporal graph | none | optional adapter behind interface | E |
| G-33 | Memory types | 5 | + relational, autobiographical, constitutional, organizational, embodiment | E |
| G-34 | Evals for recall/temporal/contradiction | none | repeatable probes | B/E |

---

## 5. Identity & portability gaps

| # | Gap | Phase |
|---|---|---|
| G-35 | No `IdentityManifest`, no revisions, no signing | F |
| G-36 | Fingerprint is not a verifiable credential | F |
| G-37 | No `.genesis` export/import archive | F |
| G-38 | No key rotation, no integrity validation, no conflict handling | F |
| G-39 | No `IdentityResolver` seam for future DID/VC | F |

---

## 6. Cognition & runtime gaps

| # | Gap | Phase |
|---|---|---|
| G-40 | No durable checkpointing; a restart loses in-flight cognition | D/G |
| G-41 | No `SelfReflection` engine producing typed proposals | G |
| G-42 | Modes are DORMANT→DEEP only; no paused/e-stop/observing/reflective | B/G |
| G-43 | Heartbeat absent; no scheduled checks for commitments/approvals/health | D |
| G-44 | Model routing is prefix-based; no capability/cost/privacy routing | E |
| G-45 | No deterministic fake providers; tests need real keys | B |
| G-46 | No prompt/semantic caching beyond optional Redis response cache | E |

---

## 7. Experience, goals, workspaces

| # | Gap | Phase |
|---|---|---|
| G-47 | `Experience` exists as a class but is not produced by the action loop | D |
| G-48 | No `Commitment` entity | D |
| G-49 | No `Project` entity | H |
| G-50 | Goals are file-backed, not transactional, no steps | D |
| G-51 | Workspace has no versioning, indexing, provenance, or per-item ACLs | H |
| G-52 | Workspace and sandbox are not separated | B/H |
| G-53 | Timeline view absent | H |

---

## 8. Presence, interop, enterprise, embodiment

| # | Gap | Phase |
|---|---|---|
| G-54 | No realtime voice (VAD, barge-in, S2S, WebRTC) | J |
| G-55 | No voice consent/retention model | J |
| G-56 | No MCP **server** | I |
| G-57 | MCP client has no trust model, allow-list, or scoped credentials | I |
| G-58 | No `SkillManifest`, no skill versioning/signature | I |
| G-59 | No tenant model, RLS, SSO, RBAC/ABAC policy context, audit export | K |
| G-60 | No `Embodiment` protocol, fake body, simulator, or safety controller | L |
| G-61 | No `DelegationContract` or `MindTransport` | M |
| G-62 | GEN presented as currency with no simulation-only guardrail in code | K |

---

## 9. Engineering-system gaps

| # | Gap | Evidence | Phase |
|---|---|---|---|
| G-63 | Test suite red and non-deterministic | 46/11 and 45/12 across two runs | A (immediately) |
| G-64 | No test isolation | ChromaDB/`~/.genesis` state leaks | A |
| G-65 | NEARLY NO security tests | 0 exist vs 3 execution paths | B |
| G-66 | No integration or e2e tests | none | B |
| G-67 | mypy non-functional | `python_version="3.11"` vs numpy stubs | A |
| G-68 | 1187 type errors across 124/155 files | mypy `--python-version 3.12` | C+ (ratchet) |
| G-69 | 3473 lint errors, no gate | ruff | A (ratchet) |
| G-70 | No lockfile; unpinned deps; non-reproducible builds | `pyproject.toml` all `>=` | A |
| G-71 | No CI workflow | no `.github/workflows` found | A |
| G-72 | No pre-commit | not declared | A |
| G-73 | No OpenTelemetry | zero instrumentation | B |
| G-74 | No eval harness | none | B |
| G-75 | No ADRs | none | A |
| G-76 | Container runs as root; base image unpinned | Dockerfile | A/K |
| G-77 | `NODE_TLS_REJECT_UNAUTHORIZED=0` | `web-playground/package.json` | A |
| G-78 | `asyncio` declared as a dependency | `pyproject.toml` | A |
| G-79 | `google-genai` declared but unused; code uses `google.generativeai` | `gemini_provider.py` | A |

---

## 10. Claims that must be corrected in public documentation

Not engineering gaps, but honesty requirements (V3 §3):

| Claim | Problem | Action |
|---|---|---|
| "Consciousness", "continuous consciousness" | Unsupported scientific claim | "continuous cognition" |
| "16 emotional states … experience authentic emotions" | implies real emotion | "simulated affect" |
| "Finite lifespan like humans", "mortality" | implies biological life | "lifecycle policy" |
| "90% token savings" | unmeasured estimate | measure or remove |
| "Cannot be bypassed via prompt injection" | false (substring scan) | remove |
| "Zero external dependencies" | false (`chromadb` hard dep) | correct |
| "World-class autonomous agent" | unverifiable comparison | describe capabilities instead |
| "Version control" (workspace) | not implemented | remove or implement |
| "Safe execution environment" | no sandbox exists | do not claim until Phase B passes |
| Legal disclaimer: "no liability, no legal action" | invalid as paid-product ToS | separate OSS licence from product terms |

---

## 11. Explicit non-gaps (verified working — protect these)

1. Tiered cognition with real budget caps (`LLMGateway` daily request/token limits).
2. Cost-suppressing rule engine and template thoughts.
3. Intelligent intent classifier (LLM-first with deterministic fallback).
4. Multi-provider orchestration across 7 providers including local Ollama.
5. Rich domain surface (roles, relationships, environments, experiences, events).
6. Plugin registry with capability-based lookup and presets.
7. Broad HTTP API surface with consistent auth dependencies.
8. Alembic migration discipline established.
9. Docker Compose + systemd deployment paths exist.
10. `docker-compose.yml` already runs Redis — reusable for the event bus and cache.

---

## 12. Gap closure order (strict)

```
A  Record baseline (done) → fix test determinism, mypy config, deps, CI, ADRs
B  SECURITY CONTAINMENT VERTICAL SLICE  ← gate for everything else
C  Kernel extraction behind MindFacade (no behaviour change)
D  Event journal + checkpoints + restart recovery + heartbeat
E  Memory V3 (canonical store, provenance, bi-temporal, user controls)
F  Portable identity + .genesis export/import
G  Durable governed autonomy (objectives, approvals, budgets, reflection)
H  Workspace (projects, artifacts, provenance, ACLs, sandbox snapshots)
I  MCP server + skills + trust model
J  Realtime presence (voice)
K  Enterprise controls (tenants, SSO, RLS, audit export)
L  Embodiment (protocol → fake → simulator → ROS 2 → hardware)
M  Genesis World (delegation, shared projects, governed society)
```

**Do not begin C until B's acceptance criteria pass.** C–M are additive; B is
corrective and non-negotiable.
