# IMPLEMENTATION_BACKLOG.md

> Actionable backlog derived from `GAP_ANALYSIS.md`, ordered by the mandatory sequence in
> V3 §47. **Phase B is a gate: nothing after it starts until it passes.**
>
> Status legend: `[ ]` not started · `[~]` in progress · `[x]` done on this branch ·
> `[!]` blocked

---

## Status snapshot (branch `feature/v3-digital-beings-os`)

| Phase | State |
|---|---|
| A — Repository discovery | `[x]` baseline docs written, tests/lint/types measured |
| B — Security containment | `[ ]` **next, and blocking** |
| C–M | `[ ]` not started |

---

## Phase A — Discovery & enablement

| ID | Task | Files | Evidence / gate | Status |
|---|---|---|---|---|
| A1 | Record discovery, reality matrix, security baseline, dependency inventory, gap analysis, threat model, test baseline | `docs/v3/*` | documents exist and cite file:line | `[x]` |
| A2 | Make the test suite deterministic (isolate ChromaDB + `~/.genesis` per test) | `tests/conftest.py` | two consecutive runs give identical results | `[ ]` |
| A3 | Fix dependency declarations | `pyproject.toml` | removed invalid `asyncio`, de-duplicated `pydantic-settings`, moved vision/browser to extras, added `cache` extra | `[x]` |
| A4 | Fix mypy configuration (`python_version` vs numpy stubs) | `pyproject.toml` | `mypy genesis` runs to completion | `[ ]` |
| A5 | Commit a lockfile; use `npm ci` | `web-playground/package-lock.json`, `Dockerfile` | lockfile generated; Dockerfile uses `npm ci` | `[x]` |
| A6 | Add CI (lint ratchet + tests + migration up/down) and `pre-commit` | `.github/workflows/`, `.pre-commit-config.yaml` | CI green on the branch | `[ ]` |
| A7 | Remove `NODE_TLS_REJECT_UNAUTHORIZED=0` | `web-playground/package.json`, `next.config.js` | grep returns no matches in app code | `[x]` |
| A8 | Create ADRs (0001–0007) | `docs/architecture/adr/` | 7 ADRs present | `[ ]` |
| A9 | Pin container base image by digest; add non-root `USER` | `Dockerfile` | `USER genesis` present; digest pinned | `[~]` non-root done, digest not pinned |
| A10 | Fix / document the `/data` volume coverage | `docker-compose.yml` | `DATA_DIR`/`MINDS_DIR`/`LOGS_DIR` set explicitly | `[x]` |
| A11 | Correct unsupported public claims (consciousness, 16 emotions, 90% savings, "cannot be bypassed") | `README.md`, `website/`, `genesisagi.in` content | claims replaced with precise terminology | `[ ]` |

---

## Phase B — Security containment vertical slice (**GATE**)

**Objective:** one end-to-end governed execution path, with no unsandboxed escape hatch.
Visual or feature work must not start before this passes.

### B1–B3 · Sandboxing
| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| B1 | Define `SandboxProvider` interface (`create/execute/upload/download/snapshot/restore/terminate`) + in-process fake for tests | `genesis/sandbox/base.py`, `genesis/sandbox/fake.py` | interface tests pass with no Docker | `[ ]` |
| B2 | Implement the local container provider (non-root, read-only rootfs, single temp dir, cgroup CPU/mem/PID/disk limits, output cap, timeout, no host env/PID/net ns, no devices, no Docker socket) | `genesis/sandbox/container.py` | all limits enforced in tests | `[ ]` |
| B3 | Route **all three** execution paths through the provider; forbid direct `subprocess` from API/web/cognition/scheduler | `genesis/core/code_executor.py`, `genesis/core/tools.py`, `genesis/plugins/tools.py` | grep shows no execution outside the provider; existing facade preserved | `[ ]` |
| B4 | Disable runtime package installation; return a typed `CapabilityUnavailable` error; pre-bake tool images | `genesis/core/code_executor.py` | emitting an unknown import makes no network call to PyPI | `[ ]` |
| B5 | Network **off** by default; allow-listed egress proxy when required | `genesis/sandbox/`, provider config | metadata/loopback/private-IP requests blocked and logged | `[ ]` |
| B6 | Export only declared artifacts; terminate and clean up after every run | `genesis/sandbox/container.py` | no residual container/files after execution | `[ ]` |

### B7–B8 · Immediate critical fixes (independent of the sandbox)
| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| B7 | **Fix SEC-01**: authenticate *before* `accept()`; derive identity from a verified token only; never trust `user_email`; bind notifications to the verified subject | `genesis/api/routes.py` (`websocket_chat`) | connect without a token is closed; spoofed email is ignored; no cross-user notification delivery | `[ ]` |
| B8 | **Fix SEC-02**: reject absolute paths and traversal in workspace writes; canonicalise and assert containment; size cap; type allow-list | `genesis/core/workspace.py`, `genesis/api/routes.py` (upload) | traversal/absolute/symlink/oversize attempts rejected | `[ ]` |
| B9 | Scrub subprocess environments; introduce `SecretReference`; stop passing `os.environ` to MCP servers | `genesis/core/code_executor.py`, `genesis/integrations/mcp_integration.py` | a subprocess printing `os.environ` reveals no key | `[ ]` |
| B10 | Remove the unenforced `ALLOWED_IMPORTS` claim (or enforce it in the sandbox) | `genesis/plugins/tools.py` | claim matches behaviour | `[ ]` |
| B11 | Stop API-tier process spawning; move daemon lifecycle to a worker/supervisor | `genesis/api/routes.py`, `genesis/daemon.py` | API cannot signal arbitrary processes | `[ ]` |
| B12 | Fail fast on default secrets; generate/document `API_SECRET_KEY`; rate-limit the token endpoint | `genesis/config/settings.py`, `genesis/api/auth.py`, `docker-compose.yml` | startup/config fails with default secret | `[~]` compose already enforces; app-level check outstanding |

### B13–B16 · Governance control plane
| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| B13 | `PolicyService`: deterministic R0–R5 risk classification and allow / allow_with_receipt / require_approval / deny / emergency_stop; model classifier advisory only | `genesis/governance/policy.py` | table-driven policy tests; classifier cannot override | `[ ]` |
| B14 | `ApprovalService`: `PROPOSED→POLICY_EVALUATED→WAITING_FOR_APPROVAL→APPROVED/REJECTED/EXPIRED→EXECUTING→COMPLETED/FAILED/ROLLED_BACK`; grants bound to parameter hash + scope + expiry; non-transferable | `genesis/governance/approval.py` | parameter change invalidates approval; replay produces no duplicate side effect | `[ ]` |
| B15 | `AuditService` + append-only event journal + immutable `ActionReceipt` for allowed, blocked, failed, cancelled and rolled-back attempts | `genesis/governance/audit.py`, `genesis/events/journal.py`, migrations | receipts appear in the workspace UI; tampering breaks integrity verification | `[ ]` |
| B16 | Convert `constitution.py` from keyword blocklist into versioned enforceable rules; keep the human-readable charter text | `genesis/core/constitution.py`, `genesis/governance/` | rules are data, versioned, and tested | `[ ]` |

### B17–B19 · Observability, evals, tests
| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| B17 | OpenTelemetry on the turn + execution path; self-hosted Langfuse export; redaction of secrets/personal content | `genesis/observability/` | one trace shows perceive→retrieve→plan→policy→execute→receipt→memory | `[ ]` |
| B18 | `genesis/evals/` harness + ≥20 golden scenarios + cost/latency report | `genesis/evals/` | `make eval` prints pass rate, cost, p95 | `[ ]` |
| B19 | Security test suite — the 19 cases in V3 §6.26 | `tests/security/` | all pass; each maps to a threat in `THREAT_MODEL.md` | `[ ]` |
| B20 | Deterministic fake model providers so the suite runs without paid keys | `genesis/models/fake.py` | tests pass with no API keys | `[ ]` |

### Phase B acceptance criteria (from V3 §47-B)
- [ ] No host filesystem access
- [ ] No Docker socket access
- [ ] No network unless allow-listed
- [ ] No host secret inheritance
- [ ] Resource limits enforced
- [ ] Timeout enforced
- [ ] Approval scope enforced
- [ ] `ActionReceipt` generated for every attempt
- [ ] **Existing public Mind API preserved** (`Mind.birth`, `start_living`, `think`, `handle_request`)

---

## Phase C — Kernel extraction (behaviour-preserving)

| ID | Task | Notes | Status |
|---|---|---|---|
| C1 | Introduce `MindFacade` exposing exactly today's surface, delegating to today's code | no behaviour change; watermark unchanged | `[ ]` |
| C2–C10 | Extract `IdentityService`, `MemoryService`, `AffectService`, `RelationshipService`, `GoalService`, `PolicyService`, `CapabilityService`, `AuditService`, `CognitionEngine` | one service per change, each with an interface and a re-export shim | `[ ]` |
| C11 | Extract `MindKernel` (`perceive/attend/deliberate/evaluate_policy/request_approval/act/experience/reflect/checkpoint/resume`) | typed; schema-validated model output rejected if invalid | `[ ]` |
| C12 | Migrate the 7 awareness levels + add `PAUSED` / `EMERGENCY_STOPPED` | map `PASSIVE→OBSERVING`, `ALERT→RESPONSIVE`, `DEEP→REFLECTIVE` | `[ ]` |

---

## Phase D — Event journal & checkpoints

| ID | Task | Status |
|---|---|---|
| D1 | `events`, `cognitive_checkpoints`, `objective_runs`, `objective_steps` tables + migrations | `[ ]` |
| D2 | Backfill `mind.born` for existing minds (ids preserved) | `[ ]` |
| D3 | Correlation + causation IDs through the turn | `[ ]` |
| D4 | Restart recovery test (pause → restart → resume without identity loss) | `[ ]` |
| D5 | Heartbeat: commitments, pending approvals, workflow health, retries, budgets — **no LLM unless real work exists** | `[ ]` |
| D6 | `Experience` produced by the action loop (not just chat) | `[ ]` |
| D7 | `Commitment` + `GoalStep` entities | `[ ]` |

---

## Phase E — Memory V3

| ID | Task | Status |
|---|---|---|
| E1 | Canonical Postgres + pgvector schema with provenance, confidence, sensitivity, access scope, bi-temporal columns, revision number | `[ ]` |
| E2 | `MemoryStore` interface; ChromaDB becomes a legacy adapter | `[ ]` |
| E3 | Compatibility reader + dual-write behind a flag | `[ ]` |
| E4 | Migrator (dry-run, resume, counts, checksums) — do not delete Chroma data until validated | `[ ]` |
| E5 | Hybrid retrieval (dense + BM25 + RRF) + cross-encoder reranking + contextual chunk headers | `[ ]` |
| E6 | Proposal→validate write pipeline; `memory_tools` proposes instead of mutating | `[ ]` |
| E7 | User controls: inspect / correct / dispute / restrict / supersede / prevent retrieval / delete / export | `[ ]` |
| E8 | Deletion transactionally purges vector + graph indexes | `[ ]` |
| E9 | Temperamental graph adapter behind `TemporalKnowledgeGraph`; system works with it disabled | `[ ]` |
| E10 | Evals: recall, temporal recall, multi-hop, contradiction, stale facts, deletion compliance | `[ ]` |
| E11 | Appraisal-based affect (event → appraisal → affect → action tendency), affect modulating tone/initiative/retrieval | `[ ]` |
| E12 | `PersonalityProfile` trait vector compiled into a versioned `PersonaArtifact`; fork/rollback | `[ ]` |

---

## Phase F — Portable identity

| ID | Task | Status |
|---|---|---|
| F1 | `IdentityManifest` + `IdentityRevision` | `[ ]` |
| F2 | Ed25519 keypair per Mind; sign memory writes and tool calls; key rotation | `[ ]` |
| F3 | `.genesis` export/import with integrity validation, conflict handling, encryption marking | `[ ]` |
| F4 | `IdentityResolver` seam (DID/VC later; not a first-stage dependency) | `[ ]` |
| F5 | Replace the decorative `digital_fingerprint` with a verifiable public key (keep the old value for display) | `[ ]` |

---

## Phase G — Durable governed autonomy

| ID | Task | Status |
|---|---|---|
| G1 | `DurableCognitionRuntime` interface + first adapter (LangGraph); one engine per responsibility | `[ ]` |
| G2 | Objective runs with pause/resume/cancel and approval interrupts | `[ ]` |
| G3 | Idempotency keys; no duplicate external actions after retry | `[ ]` |
| G4 | Per-objective budgets with hard stop | `[ ]` |
| G5 | `ReflectionEngine` producing typed proposals (never mutating constitution/policy/permissions/ownership/audit) | `[ ]` |
| G6 | User-visible objective inspector (what it is doing, why, cost, what can be cancelled/reversed) | `[ ]` |
| G7 | `LifecyclePolicy` values: IMMORTAL / ARCHIVAL / MISSION_BOUND / SUCCESSION / FINITE / ORGANIZATIONAL; mortal-by-default removed | `[ ]` |

---

## Phase H — Workspace

| ID | Task | Status |
|---|---|---|
| H1 | `/workspace` layout (`inbox`, `projects`, `knowledge`, `notes`, `artifacts`, `skills`, `shared`, `.genesis`) | `[ ]` |
| H2 | Projects, notes, artifacts with versioning and provenance | `[ ]` |
| H3 | Workspace search + provenance inspection | `[ ]` |
| H4 | Item-level access controls; explicit sharing | `[ ]` |
| H5 | Separate workspace from sandbox: sandbox receives a scoped snapshot, never the live root | `[ ]` |

---

## Phase I — MCP & skills

| ID | Task | Status |
|---|---|---|
| I1 | `SkillManifest` (versioned, signed, risk-classified, permissions, cost class, timeout, network needs, approval policy) | `[ ]` |
| I2 | MCP **server** exposing ask/search/workspace/draft/propose/status/artifacts — never raw private memory, secrets, or unapproved actions | `[ ]` |
| I3 | MCP client trust model: server + tool allow-lists, scoped credentials, schema validation, timeouts, injection protection, revocation | `[ ]` |
| I4 | Tool availability filtered by tenant, mind, user, objective, grant, risk, budget, sensitivity, network policy | `[ ]` |
| I5 | Route marketplace tool installation through the skill manifest + policy (no ungoverned executable code) | `[ ]` |

---

## Phase J — Realtime presence

| ID | Task | Status |
|---|---|---|
| J1 | Provider-neutral voice interfaces (VAD, STT, TTS, realtime sessions, interruption, partials) + fakes | `[ ]` |
| J2 | LiveKit- or Pipecat-compatible adapter | `[ ]` |
| J3 | Barge-in, push-to-talk, wake-word, visible listening/recording state, explicit consent | `[ ]` |
| J4 | Temporary vs persistent session modes, transcript deletion, retention controls | `[ ]` |
| J5 | Voice content passes through the same experience/memory/consent/policy/access paths | `[ ]` |

---

## Phase K — Enterprise controls

| ID | Task | Status |
|---|---|---|
| K1 | Tenants + RLS; ownership models (personal / organizational / shared) | `[ ]` |
| K2 | SSO adapter interface; RBAC + ABAC-ready policy context | `[ ]` |
| K3 | Audit export, retention policy, legal-hold interface | `[ ]` |
| K4 | Model allow-lists, connector permissions, cost budgets, BYO storage/model gateway, secret management | `[ ]` |
| K5 | Admin emergency controls; user-visible permissions | `[ ]` |
| K6 | Prohibit and test against: hidden surveillance, emotion inference, secret productivity scoring, autonomous performance ratings | `[ ]` |
| K7 | GEN becomes a budget/simulation guardrail in code — never represented as real money | `[ ]` |

---

## Phase L — Embodiment

| ID | Task | Status |
|---|---|---|
| L1 | `Embodiment` protocol + manifest (capabilities, sensors, actuators, safety constraints, e-stop) | `[ ]` |
| L2 | Fake body → simulator adapter (MuJoCo/Isaac) | `[ ]` |
| L3 | Deterministic safety controller **outside** the LLM (speed, force, joint limits, collision, zones, human proximity, battery, e-stop, command expiry, approval scope) | `[ ]` |
| L4 | ROS 2 adapter skeleton | `[ ]` |
| L5 | Hardware with physical emergency stop | `[ ]` |
| L6 | Physical safety survives LLM failure, network loss, service crash | `[ ]` |

---

## Phase M — Genesis World

| ID | Task | Status |
|---|---|---|
| M1 | `DelegationContract` (scope, allowed/prohibited data, budget, deadline, evidence, cancellation, result schema) | `[ ]` |
| M2 | `MindTransport` interface; A2A adapter later | `[ ]` |
| M3 | No inherited permissions, no uncontrolled shared memory, no hidden impersonation | `[ ]` |
| M4 | Shared projects/workspaces; reputation from verified outcomes | `[ ]` |

---

## First release gate (V3 §48)

The 20-step scenario must pass end-to-end, including:

- [ ] create/import a Mind, persist its identity, hold a conversation
- [ ] create a sourced `Experience`; propose a memory; approve/reject by policy
- [ ] create a project and a goal
- [ ] propose one R1 code/tool action, evaluate policy, execute in the sandbox, return an artifact
- [ ] produce an `ActionReceipt`
- [ ] **pause → restart the service → resume without identity loss**
- [ ] retrieve the relevant memory **with provenance**
- [ ] display identity, memory, goal, artifact, approval and receipt in the web workspace
- [ ] export a signed `.genesis` archive; import into a clean environment; verify continuity

Explicitly **not** built before this gate: realtime voice, inter-Mind society, physical robotics,
a new frontend, recursive self-modification, direct LLM motor control, real cryptocurrency.
