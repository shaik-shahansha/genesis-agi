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
| A — Single-container deployment | `[x]` built, running, 10/10 smoke checks pass |
| B — Security containment | `[~]` **B1, B3, B4, B6, B7, B8, B10, B13, B14, B15, B16 done**; container isolation (B2b), full egress blocking (B5), MCP env scrubbing (B9), API-tier process spawning (B11) outstanding |
| C–M | `[ ]` not started |

---

## Phase A — Discovery & enablement

| ID | Task | Files | Evidence / gate | Status |
|---|---|---|---|---|
| A1 | Record discovery, reality matrix, security baseline, dependency inventory, gap analysis, threat model, test baseline | `docs/v3/*` | documents exist and cite file:line | `[x]` |
| A2 | Make the test suite deterministic (isolate ChromaDB + `~/.genesis` per test) | `tests/conftest.py` | two consecutive runs give identical results | `[x]` — `GENESIS_VECTOR_STORE_MODE=ephemeral` plus an autouse fixture that fails the session if the mode is not `ephemeral`. Removed two of the twelve "pre-existing" failures; they were the shared ChromaDB, not the code |
| A3 | Fix dependency declarations | `pyproject.toml` | removed invalid `asyncio`, de-duplicated `pydantic-settings`, moved vision/browser to extras, added `cache` extra | `[x]` |
| A4 | Fix mypy configuration (`python_version` vs numpy stubs) | `pyproject.toml` | `mypy genesis` runs to completion | `[ ]` |
| A5 | Commit a lockfile; use `npm ci` | `web-playground/package-lock.json`, `Dockerfile` | lockfile generated; Dockerfile uses `npm ci` | `[x]` |
| A6 | Add CI (lint ratchet + tests + migration up/down) and `pre-commit` | `.github/workflows/`, `.pre-commit-config.yaml` | CI green on the branch | `[x]` — three jobs in `.github/workflows/ci.yml`: tests on 3.11 and 3.12 (with an 11-entry quarantine list that prints each reason), migrations from an empty database with a full round trip, and the sandbox-argv security suite. Replicated locally before committing. `pre-commit` still absent |
| A7 | Remove `NODE_TLS_REJECT_UNAUTHORIZED=0` | `web-playground/package.json`, `next.config.js` | grep returns no matches in app code | `[x]` |
| A8 | Create ADRs (0001–0007) | `docs/architecture/adr/` | 7 ADRs present | `[x]` (0008 added too — events/receipts) |
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
| B1 | Define `SandboxProvider` interface (`create/execute/upload/download/list_artifacts/snapshot/restore/terminate`) + in-process fake for tests | `genesis/sandbox/base.py`, `genesis/sandbox/fake.py` | interface tests pass with no Docker | ✅ **DONE** |
| B2 | Implement the local container provider (non-root, read-only rootfs, single temp dir, cgroup CPU/mem/PID/disk limits, output cap, timeout, no host env/PID/net ns, no devices, no Docker socket) | — | all limits enforced in tests | ⚠️ **PARTIAL**: `LocalSandboxProvider` enforces env scrubbing, CPU/AS/FSIZE/NPROC limits, timeout, output caps, artifact control, no installs. **Filesystem/PID/network isolation NOT implemented** — that needs the container provider below |
| B3 | Route **all three** execution paths through the provider; forbid direct `subprocess` from API/web/cognition/scheduler | `genesis/core/code_executor.py`, `genesis/core/tools.py`, `genesis/plugins/tools.py`, `genesis/sandbox/tool_runner.py` | architectural guard test passes | ✅ **DONE** |
| B4 | Disable runtime package installation; return a typed `CapabilityUnavailable` error; pre-bake tool images | `genesis/sandbox/local.py`, `pyproject.toml` (`tools` extra), `Dockerfile` | emitting an unknown import makes no network call to PyPI | ✅ **DONE** (guard blocks install commands; caps pre-baked at build time) |
| B5 | Network **off** by default; allow-listed egress proxy when required | `genesis/sandbox/` | metadata/loopback/private-IP requests blocked and logged | ⚠️ **PARTIAL**: policy defaults `network_enabled=False` and requires named domains, and `unshare -rn` is used when the kernel permits. Detected as unavailable in the current container, so egress is **not** actually blocked there — reported honestly via `capabilities()` |
| B6 | Export only declared artifacts; terminate and clean up after every run | `genesis/sandbox/` | no residual container/files after execution | ✅ **DONE** |
| **B2b** | **NEW**: implement `ContainerSandboxProvider` (gVisor/Kata-capable) in a dedicated sandbox-manager service, to supply filesystem, PID and network isolation | — | escape tests fail to escape | `[ ]` **NEW — the main remaining gap** |

### B7–B8 · Immediate critical fixes (independent of the sandbox)
| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| B7 | **Fix SEC-01**: authenticate *before* `accept()`; derive identity from a verified token only; never trust `user_email`; bind notifications to the verified subject | `genesis/api/routes.py` (`websocket_chat`), `genesis/api/auth.py` | connect without a token is closed; spoofed email is ignored; 17 tests + container smoke check | ✅ **DONE** |
| B8 | **Fix SEC-02**: reject absolute paths and traversal in workspace writes; canonicalise and assert containment; size cap; type allow-list | `genesis/core/paths.py` (new), `genesis/core/workspace.py`, `genesis/api/routes.py` | traversal/absolute/symlink/oversize attempts rejected; 32 unit tests + live verification | ✅ **DONE** (type allow-list still open) |
| B9 | Scrub subprocess environments; introduce `SecretReference`; stop passing `os.environ` to MCP servers | `genesis/core/code_executor.py`, `genesis/integrations/mcp_integration.py` | a subprocess printing `os.environ` reveals no key | ⚠️ **PARTIAL**: the sandbox now scrubs its environment (verified). **MCP servers still receive `os.environ`** — outstanding |
| B10 | Remove the unenforced `ALLOWED_IMPORTS` claim (or enforce it in the sandbox) | `genesis/plugins/tools.py` | claim matches behaviour | ✅ **DONE** (claim and constant removed; asserted absent by test) |
| B11 | Stop API-tier process spawning; move daemon lifecycle to a worker/supervisor | `genesis/api/routes.py`, `genesis/daemon.py` | API cannot signal arbitrary processes | `[ ]` |
| B12 | Fail fast on default secrets; generate/document `API_SECRET_KEY`; rate-limit the token endpoint | `genesis/config/settings.py`, `genesis/api/auth.py`, `docker-compose.yml` | startup/config fails with default secret | `[~]` compose already enforces; app-level check outstanding |

### B13–B16 · Governance control plane
| ID | Task | Files | Gate | Status |
|---|---|---|---|---|
| B13 | `PolicyService`: deterministic R0–R5 risk classification and allow / allow_with_receipt / require_approval / deny / emergency_stop; model classifier advisory only | `genesis/governance/policy.py`, `genesis/governance/risk.py` | table-driven policy tests; classifier cannot override | ✅ **DONE** — pure/deterministic, fails closed, advisory can only ratchet up; undeclared capability floors at R3 |
| B14 | `ApprovalService`: `PROPOSED→POLICY_EVALUATED→WAITING_FOR_APPROVAL→APPROVED/REJECTED/EXPIRED→EXECUTING→COMPLETED/FAILED/ROLLED_BACK`; grants bound to parameter hash + scope + expiry; non-transferable | `genesis/governance/approval.py` | parameter change invalidates approval; replay produces no duplicate side effect | ✅ **DONE** — illegal transitions refused; single-use grants; 5 tests cover binding/replay/expiry |
| B15 | `AuditService` + append-only event journal + immutable `ActionReceipt` for allowed, blocked, failed, cancelled and rolled-back attempts | `genesis/governance/audit.py`, `genesis/governance/models.py`, migrations | receipts appear in the workspace UI; tampering breaks integrity verification | ✅ **DONE** (service + journal + receipts + API + migration 008). Workspace UI lands with the playground revamp |
| B16 | Convert `constitution.py` from keyword blocklist into versioned enforceable rules; keep the human-readable charter text | `genesis/core/constitution.py`, `genesis/governance/constitution_rules.py` | rules are data, versioned, and tested | ✅ **DONE** — 13 versioned clauses; `validate_user_prompt` is advisory and no longer drops the user's turn; `validate_action` delegates to the engine; a test fails if any `ConstitutionalViolation` lacks a clause |

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
| D1 | `events`, `cognitive_checkpoints`, `objective_runs`, `objective_steps` tables + migrations | `[~]` — `events` done (`008_governance_plane`). `cognitive_checkpoints`, `objective_runs`, `objective_steps` not built |
| D2 | Backfill `mind.born` for existing minds (ids preserved) | `[ ]` |
| D3 | Correlation + causation IDs through the turn | `[x]` — `genesis/governance/context.py`: `correlation_scope`, `current_correlation_id`, `explain_chain`. Chat turns are scoped; `causation_id` is not yet threaded |
| D4 | Restart recovery test (pause → restart → resume without identity loss) | `[ ]` — needs checkpoints |
| D5 | Heartbeat: commitments, pending approvals, workflow health, retries, budgets — **no LLM unless real work exists** | `[ ]` — `CommitmentManager.sweep_overdue` exists and is the right primitive to drive it |
| D6 | `Experience` produced by the action loop (not just chat) | `[~]` — the action loop now emits journals and receipts; memory-write experiences are still chat-only |
| D7 | `Commitment` + `GoalStep` entities | `[~]` — `Commitment` done (`genesis/core/life/commitments.py`), classified as Phase N work). `GoalStep` not built |

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

## Phase N — Digital Life State (**promoted above Phase E**)

> Design: [`DIGITAL_LIFE_STATE.md`](DIGITAL_LIFE_STATE.md).
>
> **This phase was promoted ahead of memory V3 after review.** The reasoning:
> memory V3 makes retrieval better; life state makes the being *reliable*, which
> is the property a user notices on day one. It is also much cheaper (two new
> entities, two upgrades, one consolidation — against replacing the vector store
> and adding a temporal graph). The cost of this ordering is that commitments will
> later need migrating onto bi-temporal storage, which is worth paying.
>
> Verified as genuine gaps before writing this: `commitment.` and `embodiment.`
> exist **only** as event-type prefixes in `genesis/governance/models.py`, and
> `add_responsibility` in `core/role.py` stores a plain string.

| ID | Task | Files | Status |
|---|---|---|---|
| N1 | `Commitment` entity: beneficiary (a relationship, not a string), deadline, provenance, status machine (OPEN → IN_PROGRESS → FULFILLED / MISSED / RENEGOTIATED / WITHDRAWN) | `genesis/core/life/commitments.py` (new) | `[x]` — built. Adds PROPOSED (a cross-Mind proposal needs the owner's approval) and tracks `is_overdue` separately from `MISSED` |
| N2 | **Commitments are exempt from memory decay.** A forgotten obligation is a failure, not a fading fact | `genesis/core/life/commitments.py` | `[x]` — commitments never enter the vector store, so decay cannot reach them. Durable by construction rather than by exemption |
| N3 | `MISSED` is an audit event surfaced in the timeline, not a silent expiry | `genesis/core/life/`, `genesis/governance/audit.py` | `[x]` — every transition journals `commitment.*` through `DomainJournal`; `sweep_overdue` marks, it does not expire silently |
| N4 | Declare the governance capabilities: commitment to owner R1, commitment binding a third party R2/R3, withdrawal R2 with receipt | `genesis/governance/risk.py` | `[x]` — five capabilities: `create_commitment` R1, `create_commitment_cross_mind` R2, `commit_to_third_party` R3, `fulfil_commitment` R1, `withdraw_commitment` R2. Capability registry now reports 41 |
| N5 | `Responsibility` as a first-class record: scope, owner, review interval, suspendable (upgrade the `role.py` string) | `genesis/core/role.py`, `genesis/core/life/` | `[ ]` |
| N6 | `Project` entity: goal, commitments, artifacts, timeline, participants | `genesis/core/life/projects.py` (new) | `[ ]` |
| N7 | Habits: expose the existing circadian routines (`life_activities.py`, `consciousness_v2.py`) as *declarable* habits with an adherence history | `genesis/core/life/habits.py` (new) | `[ ]` |
| N8 | Assets view: one queryable answer to "what does this being have?" (files, GEN budget, skills, environments, credential *references*) | `genesis/core/life/assets.py` (new) | `[ ]` |
| N9 | Calendar: one time axis joining commitments, habits and scheduled actions (consolidate `action_scheduler.py` + `tasks.py`) | `genesis/core/life/calendar.py` (new) | `[ ]` |
| N10 | Workspace surface: commitments visible to a human, with provenance | Phase H | `[ ]` |
| N11 | Anti-requirement: **no autonomous commitment creation.** A being that invents obligations is a liability | test | `[x]` — creation requires an explicit beneficiary and provenance; a cross-Mind beneficiary yields PROPOSED, which the owner must approve. Tested |

---

## Phase O — Relationship intelligence

> Design: [`RELATIONSHIP_INTELLIGENCE.md`](RELATIONSHIP_INTELLIGENCE.md).
>
> `core/relationships.py` models a typed edge. It cannot express trust, shared
> history, expectations, or what should not be mentioned — which is the
> granularity that matters for a being acting with standing authority.

| ID | Task | Status |
|---|---|---|
| O1 | **Boundaries** (what not to mention, not to share, when not to contact). Pull these forward with Phase N: cheap, only *restrict*, and give a user immediate control | `[ ]` |
| O2 | Trust **scoped per domain**, with `none` as a distinct value rather than a low number | `[ ]` |
| O3 | Relational memory: a `relationship_id` scope on memory writes, resolved as a retrieval filter (not a new store) | `[ ]` |
| O4 | Shared history: summarised significant exchanges, with retention bounds (boundaries persist; summaries expire) | `[ ]` |
| O5 | Governance: trust **upward** is R3, a boundary is R1 (the asymmetry is deliberate); relational detail shared with a third party is R4 | `[ ]` |
| O6 | Scoped export: a relationship involving a third party does not travel without that party's consent | `[ ]` |
| O7 | Transparency: a person can see what the being believes about them. Anti-requirement: **no private assessment of a person** | `[ ]` |

---

## Phase L — Embodiment

> Design: [`EMBODIMENT_ABSTRACTION.md`](EMBODIMENT_ABSTRACTION.md).
>
> **L1 (`Body` protocol) was moved into Phase C**, because the shape of the
> actuation seam is what constrains the kernel split. Defining it later means
> four competing paths in (chat, voice, workspace, robot) to reconcile.

| ID | Task | Status |
|---|---|---|
| L0 | `Body` protocol (`perceive` non-blocking, `act` refusable, `observe` side-effect-free) + `NullBody` + `WebBody` — **in Phase C** | `[ ]` |
| L1 | `Embodiment` protocol + manifest (capabilities, sensors, actuators, safety constraints, e-stop) | `[ ]` |
| L2 | Fake body → simulator adapter (MuJoCo/Isaac) | `[ ]` |
| L3 | Deterministic safety controller **outside** the LLM (speed, force, joint limits, collision, zones, human proximity, battery, e-stop, command expiry, approval scope) | `[ ]` |
| L4 | ROS 2 adapter skeleton — **must refuse rather than actuate until L3 and L5 exist** | `[ ]` |
| L5 | Hardware with a **physically independent** emergency stop that fails *safe* (motion stops) rather than permissive | `[ ]` |
| L6 | Physical safety survives LLM failure, network loss, service crash (bounded deadman watchdog) | `[ ]` |
| L7 | Keep `actuate_robot` at R4 once it becomes real — the pressure to relax it will appear exactly then | `[ ]` |

---

## Phase M — Genesis World

| ID | Task | Status |
|---|---|---|
| M1 | `DelegationContract` (scope, allowed/prohibited data, budget, deadline, evidence, cancellation, result schema) | `[ ]` |
| M2 | `MindTransport` interface; A2A adapter later | `[ ]` |
| M3 | No inherited permissions, no uncontrolled shared memory, no hidden impersonation | `[ ]` |
| M4 | Shared projects/workspaces; reputation from verified outcomes | `[ ]` |

---

## Phase P — Digital presence: the Mind's own life outside the container

> Design and rationale: [`DIGITAL_PRESENCE.md`](DIGITAL_PRESENCE.md).
>
> This phase exists because the previous plan treated external communications as
> "integrations" — adapters bolted to the side — when they are the Mind's body.
> A Mind with its own email address, phone number and messaging identity is a
> different product from a Mind inside a chat window, and the governance work
> already completed is what makes it deployable rather than the thing it is.

| ID | Task | Status |
|---|---|---|
| P0.1 | `CommunicationChannel` protocol: `receive` / `prepare` / `send` / `get_thread` / `sync_contacts`, with `send` accepting only an approved message | `[x]` |
| P0.2 | Enforced AI disclosure in the writer; a channel that cannot disclose is refused at registration | `[x]` |
| P0.3 | Contactability floors in the adapter: quiet hours (wrapping midnight), weekly initiated cap, minimum gap, cross-channel opt-out | `[x]` |
| P0.4 | Approval integrity: a digest over the approved body, verified at send, so a persisted-then-edited approval cannot send | `[x]` |
| P0.5 | Channel capabilities in the governance registry; `comms.broadcast`, `account.create`, `circumvent_human_verification`, `impersonate_human`, `undisclosed_outreach` prohibited | `[x]` |
| P0.6 | Remove the ungoverned auto-reply loop and the false "Email sent" claim in `action_executor` | `[x]` |
| P0.7 | `ChannelRegistry` with per-channel enable/disable **and a reason**, so a refused channel is visible rather than absent | `[x]` |
| P1.1 | Email adapter (IMAP/SMTP, stdlib only) | `[~]` written; never exercised against a live server |
| P1.2 | Telegram Bot API adapter | `[~]` written; never exercised against a live bot |
| P1.3 | **Hostinger Mail API adapter** (preferred email: scoped token, provider-side threading, allow list, webhooks). Read paths inferred from their documented convention; `verify()` reports per-path verdicts | `[~]` written and tested against a fake transport; never called live |
| P1.4 | **Ringg AI voice adapter**: Mind decides who and what context, Ringg's assistant speaks. Disclosure asserted by the operator and the channel refuses to register without it | `[~]` written and tested; never called live |
| P1.5 | **HTTP/SSE transport for `MCPClient`**, without which no hosted MCP server (including `mcp.mail.hostinger.com/mcp`) is reachable. `MCPServerConfig.command` must become optional for remote servers | `[ ]` prerequisite for the MCP route |
| P1.6 | `ChannelGateway`: inbound → responder → floors → approval → send → receipt, each outcome recorded | `[x]` logic done; not yet driven by the daemon |
| P1.7 | Contact resolution behind a `ContactResolver` protocol, with unknown senders reply-only and no `consent_source` | `[x]` in-memory default; durable store is P2.1 |
| P2.1 | Contact identity: scoped trust, `consent_source`, quiet hours and a weekly cap per contact | `[x]` **not on `Relationship`** — see P2.3. Consent lives on the channel row, because someone who gave an email address has not agreed to be telephoned |
| P2.2 | Attach a `ChannelRegistry` to `Mind` | `[x]` `Mind.channels`, lazily built so a misconfigured channel raises where the caller can see it instead of printing a warning like every other optional subsystem in `Mind.__init__` |
| P2.3 | Durable contact store: `contacts` + `contact_channels`, migration `010_contacts`, `DatabaseContacts` resolving | `[x]` 34 tests. A **new table** rather than columns on `Relationship`: that table's FKs point at `minds.gmid`, so a human contact needs an invented Mind, which would then appear in the metaverse and be addressable as a peer |
| P2.4 | Per-Mind channel credentials | `[ ]` every Mind on an install currently shares one mailbox, and `Mind.channels` says so rather than implying isolation |
| P3.1 | Webhook gateway with per-provider signature verification | `[ ]` |
| P3.2 | IMAP poller as a background task, on the existing scheduler | `[x]` `ChannelPoller`, driven from `MindDaemon` via `_channel_loop`. Off unless `MIND_CHANNEL_AUTOREPLY_ENABLED` |
| P3.3 | Inbound events → journal → memory, so the Mind remembers who wrote and when | `[~]` journal `[x]` (`channel.*` event family); **memory `[ ]`** — an inbound message is not yet something the Mind remembers |
| P3.4 | Reply flow: inbound → cognition → intent → gate → send, with the receipt as the reply's record | `[x]` `MindResponder` → `GovernanceAuthorizer` → `ChannelGateway`. The responder is told nothing about policy, and actions are disabled during a draft |
| P3.5 | Durable outbound ledger (replaces the in-memory default, which resets on restart) | `[ ]` |
| P3.6 | Durable Telegram `getUpdates` offset, or dedup by message id | `[~]` dedup by message id `[x]` (`inbound_events`); the offset itself is still per-process |
| P3.7 | Durable **inbound** ledger: at most one reply per message across restarts | `[x]` `inbound_events`, migration `011_inbound_events`. Claims before dispatch, so a crash loses a reply rather than duplicating one. Verified by mutation |
| P3.8 | Stuck claims surfaced and journalled rather than retried | `[x]` `PollReport.stuck` + `channel.reply_not_sent` |
| P4.1 | Telephony adapters (Ringg.ai done; Twilio / Sarvam behind the same channel shape), R3, per-message approval, never a standing grant | `[~]` Ringg written; others `[ ]` |
| P4.2 | Spoken AI disclosure at call open, not configurable off. Done for Ringg by passing `ai_disclosure` as a prompt variable and refusing to register until the operator asserts the prompt speaks it | `[x]` for Ringg, with the assertion recorded rather than hidden |
| P4.3 | Call transcript → memory, so a call becomes something the Mind remembers rather than only an action it took | `[ ]` |
| P4.4 | Call recording requires disclosure and is off by default | `[ ]` |
| P5.1 | WhatsApp Business via Meta Cloud API; template-based outside the 24-hour window | `[ ]` |
| P6.1 | Social publishing adapters, disclosure in bio, per-platform OAuth | `[ ]` |
| P7.1 | `CapabilityRequest`: the Mind asks for a capability it lacks; admin provisions or declines. The Mind cannot self-grant | `[ ]` |
| P7.2 | Admin surface for channel credentials and capability requests | `[ ]` |
| P8.1 | Metered-channel budgeting: estimate from `prepare()`, check the budget before executing, **halt rather than queue** on exhaustion | `[ ]` |
| P8.2 | Proactivity from triggers (commitment/deadline/event), each recorded as the message's reason | `[ ]` |

**Anti-requirements, tested rather than documented:**

| ID | Anti-requirement | Status |
|---|---|---|
| P-A1 | No path from model output to a provider that does not pass the gate | `[x]` |
| P-A2 | No undisclosed outbound message, on any channel | `[x]` |
| P-A3 | No bulk unsolicited outreach, at any approval level | `[x]` |
| P-A4 | No automated circumvention of CAPTCHA, KYC, age checks or ToS | `[x]` |
| P-A5 | No contact with someone who opted out — on any channel, by any address | `[x]` |

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
