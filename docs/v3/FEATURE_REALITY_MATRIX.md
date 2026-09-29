# FEATURE_REALITY_MATRIX.md

> V3 §4 requires each claimed capability to be classified against what is actually
> implemented. **A capability is not credited for appearing in a README, type definition,
> route, comment, TODO, or UI.** Evidence is a file path that was read.
>
> Maturity: **PR** Production-ready · **FI** Functional but incomplete · **PT** Prototype ·
> **PH** Placeholder · **DO** Documentation-only · **UN** Unsafe · **BR** Broken ·
> **DEP** Deprecated · **NF** Not found

---

## A. Identity, lifecycle, and being-level features

| Feature | Doc claim | Implementation | Entry point | Tests | Security | Maturity | Migration |
|---|---|---|---|---|---|---|---|
| Mind identity (GMID) | "Unique identity" | `core/identity.py` `MindIdentity`, `generate_gmid()` | `Mind.__init__` | indirect | plain data | **PR** | Wrap in `IdentityService` + manifest |
| Digital fingerprint | "cryptographic hash" framing | `generate_fingerprint()` — SHA-256 of `gmid:timestamp:creator:random` | same | none | **decorative, not verifiable** | **PT** | Replace with Ed25519 public key in manifest |
| Identity portability / export-import | implied by "transfer to robotics" | none | — | none | n/a | **NF** | Phase F |
| Identity revision history | not claimed | none | — | none | n/a | **NF** | Phase F |
| Mortality / finite lifespan | "finite lifespan creates urgency" | `core/lifecycle.py` `LifecycleState.update_state()` | `lifecycle` plugin | none | n/a | **FI** | Make optional via `LifecyclePolicy` |
| Purpose / role / guidance notes | "purpose-driven existence" | `identity.py` fields; alembic `20260128_1400_add_purpose_role_guidance` | settings API | none | n/a | **FI** | Fold into `Persona`/`IdentityManifest` |
| Genesis Constitution (15 laws) | "actively enforced, cannot be bypassed" | `core/constitution.py` — `HARMFUL_KEYWORDS` substring scan | `validate_user_prompt()` | none | **bypassable trivially** | **UN** | Replace with `PolicyService`; keep text as charter |
| Constitutional enforcement on retrieval/actions | "system-level validation" | prompt-scan only; not applied to tool args, retrieved content, or code | — | none | **UN** | **PH** | Phase B |
| GEN economy | "GEN currency for motivation" | `core/gen.py` `GenManager`, `core/gen_intelligence.py`, `gen_transactions` table | `gen` plugin | partial | simulated only | **FI** | Keep as internal budget; never money |

---

## B. Cognition and consciousness

| Feature | Doc claim | Implementation | Entry point | Tests | Security | Maturity | Migration |
|---|---|---|---|---|---|---|---|
| 24/7 continuous cognition | "continuous consciousness" | `core/living_mind.py` `LivingMind`, `core/consciousness_v2.py` `ConsciousnessEngineV2` | daemon loop | none | **risky config defaults** | **FI** | Rename to continuous cognition; add pause/e-stop |
| Awareness tiers (5 modes) | "5 awareness modes" | `AwarenessLevel` IntEnum DORMANT→DEEP | `select_model()` | none | n/a | **FI** | Map to V3 7 modes incl. paused/e-stop |
| Cost-aware tiering + budget caps | "90-95% cost reduction, 50-100 LLM calls/day" | `LLMGateway` with `daily_request_limit=200`, `daily_token_limit=100000` | `LLMGateway.request()` | none | n/a | **FI** | Wire to real money; add per-objective budgets |
| Circadian rhythm / routines | "circadian-inspired" | `CircadianPhase`, `RoutineManager`, `DailyScheduleManager` | `LivingMind` | none | n/a | **PT** | Keep; feed into `LifeState` |
| Needs system | "needs" | `NeedsState` (social, curiosity, achievement, purpose, creativity, autonomy) | `consciousness_v2.py` | none | n/a | **PT** | Keep as motivation signals |
| Biological state (energy/fatigue) | implied | `BiologicalState` dataclass | same | none | n/a | **PT** | Keep |
| Rule engine (no-LLM path) | "rule engine, template thoughts" | `RuleEngine` class in `consciousness_v2.py` | same | none | n/a | **PT** | Keep — this is the cost moat |
| Reflection | "self-awareness" | **no dedicated reflection engine exists**; `core/genesis_core.py` and memory consolidation approximate it | — | none | n/a | **NF** | Phase G (`ReflectionEngine`) |
| Attention management | not claimed | `AttentionManager` (event queue, priority) | same | none | n/a | **PT** | Becomes `AttentionEngine` |
| Cognitive checkpoints / resume | not claimed | none | — | none | n/a | **NF** | Phase D |
| Durable workflow execution | not claimed | none (no LangGraph/Temporal) | — | none | n/a | **NF** | Phase G |

---

## C. Memory

| Feature | Doc claim | Implementation | Entry point | Tests | Security | Maturity | Migration |
|---|---|---|---|---|---|---|---|
| 5 memory types | "5 types" | `MemoryType` in `storage/memory.py` | `add_memory()` | partial | n/a | **FI** | Map to V3 taxonomy + new types |
| Vector semantic search | "<50ms" | `storage/vector_store.py` ChromaDB **default embeddings** | `search()` | yes | n/a | **PR** (works) | Behind `MemoryStore`; pgvector adapter |
| Deduplication | "85% similarity threshold" | `storage/memory_deduplication.py` | `SmartMemoryManager` | yes | n/a | **FI** | Keep semantics |
| Temporal decay | "1% per day" | `storage/memory.py` ~line 89 — **relevance multiplier only** | `search` ranking | yes | **cannot express validity** | **FI** | Replace with bi-temporal model |
| LLM reranking | "optional LLM reranking" | `storage/memory_reranker.py` | `search_memories_smart` | yes | cost risk | **FI** | Replace with cross-encoder + RRF |
| Consolidation | "auto-consolidation" | `storage/memory_consolidation.py` | scheduled | **failing test** | n/a | **BR** | Phase E |
| Auto-extraction | "zero manual memory creation" | `storage/memory_extractor.py` (LLM) | chat flow | indirect | **poisonable** | **FI** | Add proposal→validate pipeline |
| Memory blocks (Letta pattern) | "persistent in-context memory" | `storage/memory_blocks.py` `CoreMemory` | `Mind.core_memory` | none | n/a | **FI** | Keep as working-memory projection |
| Agent self-editing | "replace, insert, consolidate" | `tools/memory_tools.py` | action executor | none | **LLM mutates memory directly** | **UN** | Must become proposals + validation |
| Provenance / confidence / sensitivity | not claimed | **none** | — | none | n/a | **NF** | Phase E |
| Valid-time vs ingestion-time | not claimed | **none** | — | none | n/a | **NF** | Phase E |
| Contradiction / supersession | "conflict" not claimed | **none** | — | none | n/a | **NF** | Phase E |
| User-visible correction / dispute / delete | not claimed | partial: `GET /minds/{id}/memories`, `DELETE` none for memories | API | no | privacy gap | **PH** | Phase E |
| Deletion purges derived indexes | not claimed | none | — | none | n/a | **NF** | Phase E |
| Temporal knowledge graph | not claimed | none | — | none | n/a | **NF** | Phase E (optional adapter) |
| Cross-user memory isolation | "memory isolation by email" | email-scoped filtering | chat flow | **failing test** | **web socket bypass SEC-01** | **BR** | Phase B/E |

---

## D. Affect and personality

| Feature | Doc claim | Implementation | Entry point | Tests | Security | Maturity | Migration |
|---|---|---|---|---|---|---|---|
| 16 emotional states (arousal/valence) | "16 affective states" | `core/emotions.py` `EmotionalState` | `Mind.emotional_state` | 2 tests, both **fail** | n/a | **FI** | Keep, relabel "simulated affect" |
| Emotional intelligence engine | "empathetic responses" | `core/emotional_intelligence.py`, `emotional_patterns.py` | `Mind.emotional_intelligence` | 1 failing test | n/a | **FI** | Keep |
| Affect causes behaviour | implied | **affect is mostly cosmetic**; no action tendency | — | none | n/a | **PT** | Phase E: appraisal pipeline |
| Appraisal theory pipeline | not claimed | none | — | none | n/a | **NF** | Phase E |
| Personality as data | "unique identity & personality" | `plugins/profiles.py`; template-based | `Mind.profile` | none | n/a | **PT** | `PersonalityProfile` + trait vector |
| Persona artifact | not claimed | none (prompt assembled ad hoc) | — | none | n/a | **NF** | Phase E |
| Affective state visible to user | not claimed | exposed in playground | `/minds/{id}` | no | n/a | **FI** | Must be labelled "simulated" |

---

## E. Autonomy and action

| Feature | Doc claim | Implementation | Entry point | Tests | Security | Maturity | Migration |
|---|---|---|---|---|---|---|---|
| Dynamic code generation | "generates code for ANY task" | `core/code_generator.py` `IntelligentCodeGenerator` | `AutonomousOrchestrator` | none | n/a | **FI** | Keep; constrain + validate schema |
| Code execution | "safe execution environment" | `core/code_executor.py` | `execute_code()` | 1 failing | **UN — no sandbox (SEC-03)** | **UN** | Phase B (blocking) |
| Plan → reason → reflect loop | "autonomous planning" | `core/autonomous_reasoner.py`, `autonomous_orchestrator.py` | `handle_request()` | none | n/a | **FI** | Move behind durable runtime |
| Goals | "goal planning" | `core/goals.py` `GoalManager` (+ `plugins/experimental/goals.py`), **JSON-backed** | `Mind.goals` | none | n/a | **PT** | Phase D/E: ORM `goals`/`goal_steps` |
| Commitments | not claimed | **none** (goals only) | — | none | n/a | **NF** | Phase D |
| Projects | not claimed | **none** | — | none | n/a | **NF** | Phase H |
| Intent classification | not claimed | `core/intent_classifier.py` (LLM-first) + `task_detector.py` | chat | none | n/a | **FI** | Keep |
| Background task execution | "crash recovery" | `core/background_task_executor.py`, `background_tasks` table | chat | none | n/a | **FI** | Phase D: checkpointed objectives |
| Action scheduler | "proactive actions" | `core/action_scheduler.py` | daemon | none | n/a | **FI** | Phase G |
| Permission levels | "enforced" | `core/autonomy.py` `PermissionLevel` | `is_action_allowed()` | none | **fail-closed but unusable** | **FI** | Phase B policy engine |
| Approval workflow | "require approval for external actions" | `settings.require_approval_for_external_actions=True`; `permissions.check_permission` **returns False for REQUIRES_CONFIRMATION with comment "not implemented in auto mode"** | — | none | **control cannot be satisfied** | **PH** | Phase B `ApprovalService` |
| Action receipts | not claimed | **none** | — | none | n/a | **NF** | Phase B |
| Audit log | "violation tracking & logging" | `safety/permissions.py` → `logs/{mind}/actions.jsonl` | `log_action()` | none | **mutable, no integrity** | **PT** | Phase B `AuditService` |

---

## F. Execution environments

| Feature | Doc claim | Implementation | Entry point | Tests | Security | Maturity | Migration |
|---|---|---|---|---|---|---|---|
| Sandbox | "safe execution environment" / "subprocess sandbox" | raw subprocess ×3 (`code_executor.py`, `core/tools.py`, `plugins/tools.py`) | — | 1 failing | **UN (SEC-03/04/06)** | **UN** | Phase B |
| `SandboxProvider` abstraction | not claimed | **NF** | — | none | n/a | **NF** | Phase B |
| Docker isolation | "Docker support for maximum isolation" | only `_docker_available()` probe; never used | — | none | n/a | **DO** | Phase B |
| Runtime package install | not claimed | `_ensure_dependencies_installed()` pip installs from model output | agent loop | none | **C (SEC-04)** | **UN** | Phase B: remove |
| Workspace (files) | "personal file storage" | `core/workspace.py` `WorkspaceManager`, `mind_files` table | `/workspace/*` | no | **C: path traversal (SEC-02)** | **UN** | Phase B fix, Phase H full |
| Workspace versioning | "version control" | not found in `workspace.py` | — | none | n/a | **DO** | Phase H |
| Workspace sandboxing separation | not claimed | **none** — workspace is the same FS the sandbox can reach | — | none | **UN** | **NF** | Phase B/H |

---

## G. Senses, voice, multimodal

| Feature | Doc claim | Implementation | Entry point | Tests | Security | Maturity | Migration |
|---|---|---|---|---|---|---|---|
| Vision | "image processing" | `senses/vision.py` (opencv, `fer`, `deepface`) | `SensorySystem` | none | heavy deps | **PT** | Optional extra; provider interface |
| Speech-to-text | "speech input" | Groq Whisper (`multimodal/processor.py:254`), OpenAI Whisper (`senses/speech_input.py`) | `/multimodal/*` | none | key-dependent | **FI** | Phase J provider interface |
| Text-to-speech | "speech output" | ElevenLabs REST, OpenAI TTS, browser TTS | `speech_output.py` | none | key-dependent | **FI** | Phase J |
| Live / realtime voice | "direct live talk" (site implies presence) | **absent** — no VAD, barge-in, or S2S session | — | none | n/a | **NF** | Phase J |
| Touch / proprioception / network senses | "touch (multi-modal)" | `core/senses.py` dataclasses + stubs | `SensorySystem` | none | n/a | **PT** | Phase L (embodiment) |
| Image generation | "Pollinations" | `multimodal/processor_pollinations.py` | avatar/chat | none | external service | **FI** | Keep as skill |

---

## H. Interop, integrations, platform

| Feature | Doc claim | Implementation | Entry point | Tests | Security | Maturity | Migration |
|---|---|---|---|---|---|---|---|
| MCP **client** | "MCP (Model Context Protocol)" | `integrations/mcp_integration.py` (stdio/HTTP/WS), `plugins/mcp.py` | plugin | none | **H: env inheritance (SEC-05), no allow-list** | **FI** | Phase I |
| MCP **server** | not claimed | **NF** | — | none | n/a | **NF** | Phase I (priority) |
| A2A / agent delegation | not claimed | **NF** | — | none | n/a | **NF** | Phase M |
| Email / calendar / chat integrations | "Slack, Discord, Email, Calendar" | `integrations/*.py` with guarded optional imports | plugins | none | unscoped credentials | **PT** | Phase I: scoped OAuth |
| **Channel substrate** (the Mind's own comms) | new, `DIGITAL_PRESENCE.md` | `channels/{base,disclosure,limits,adapter,registry,fake}.py` | `ChannelRegistry`, `ChannelGateway` | `tests/security/test_channels.py` (27) | **enforced disclosure, contactability floors, approval-integrity digest; `comms.broadcast`/`account.create`/`impersonate_human`/`undisclosed_outreach` prohibited at R5** | **FI** | P2: contact identity; P3: durability |
| Mind sends/reads **email** | new | `channels/email.py` (stdlib IMAP/SMTP), `channels/hostinger_mail.py` (Mail API: scoped token, provider-side threading, allow list) | `ChannelRegistry` | `test_channel_providers.py` (52) | disclosure in the writer; R0 read / R1 draft / R2 reply / R3 initiate | **PT** | **never called a real server.** Hostinger send path documented; read paths inferred. Run `verify()` |
| Mind **places voice calls** | new | `channels/ringg_voice.py` (Ringg AI) | `ChannelRegistry` | `test_channel_providers.py` | **does not register unless disclosure is asserted** — no Ringg API returns the assistant's prompt, so this is a human assertion, recorded rather than hidden; R3, never a standing grant | **PT** | **never placed a real call.** `can_receive: False`; no transcript ingestion |
| Mind **receives inbound** comms | new | `channels/gateway.py` (`handle`/`drain`) | not scheduled | `test_channel_providers.py` | refusal on any floor leaves the Mind unable to send; a refused message produces **no** approval card | **PT** | **nothing drives it**; no webhook ingestion |
| Hosted **MCP servers** | "MCP (Model Context Protocol)" | `connect()` implements **stdio only** — HTTP/WS return `False` after a warning; `MCPServerConfig.command` required | plugin | none | inherits the SEC-05 allowlist | **NF** | **HTTP/SSE transport is a prerequisite**; affects `mcp.mail.hostinger.com/mcp` |
| Notifications (Twilio/Firebase) | "SMS, Push" | `integrations/notification_integration.py`, `core/notification_manager.py` | websocket/API | none | **delivered to spoofable identity (SEC-01)** | **FI** | Phase B fix |
| Browser automation | "browser automation plugin" | `plugins/browser_use_plugin.py` | plugin | none | **H: model-directed browsing + SOCKS proxy guidance** | **UN** | Phase I |
| Web search | "free web search (DuckDuckGo)" | `ddgs`; `plugins/perplexity_search.py` | plugin | none | injection surface | **FI** | Phase I |
| Genesis World / environments | "shared digital universe" | `environments/{manager,server,realtime,client,templates}.py`, `environment_routes.py` | `/environments/*` | none | shared mutable DB, no tenant | **PT** | Phase M |
| Marketplace | "marketplace" | `marketplace/{manager,installer}.py`, `api/marketplace_routes.py` | `/marketplace/*` | none | **H: installs arbitrary tool code (SEC-07)** | **UN** | Phase I |
| Plugins (20) | "hot-swappable, capability-aware" | `plugins/registry.py` + 20 modules; `MindConfig` presets | CLI/API/UI | none for most | **executes third-party code in-process** | **FI** | Phase C: in-process allow-list |
| CLI | "genesis birth/chat/daemon" | `cli/main.py` (Typer) | `genesis` script | none | spawns processes | **FI** | Preserve; add `genesis v3` cmds |
| REST API | "25+ endpoints" | 89 decorators in `routes.py` | `/api/v1/*` | 3 modules | mixed (SEC-01) | **FI** | Preserve via facade |
| Web playground | "Mind management dashboard" | `web-playground/` Next.js 14 | browser | none | `NODE_TLS_...=0` | **FI** | Becomes Mind Workspace |
| Mobile app | "Flutter" | **submodule, not present in this checkout** | — | none | unverifiable | **NF** | Verify separately |
| Authentication | Firebase/JWT | `api/auth.py`, `api/firebase_auth.py` | `/auth/*` | yes | **H (SEC-08)** | **FI** | Phase K: SSO interface |
| Authorization | RBAC | FastAPI dependencies + `mind_access` table | routes | partial | **no tenant/RLS** | **FI** | Phase K |
| Multi-tenancy | not claimed | **NF** | — | none | n/a | **NF** | Phase K |
| Observability | "logs viewer, LLM call tracking" | `mind_logger.py`, `/llm-calls`, `/logs`; **no OTel** | API/UI | none | no redaction | **PT** | Phase B: OTel |
| Evaluations | not claimed | **NF** | — | none | n/a | **NF** | Phase B: harness |
| Deployment | Docker, K8s | Docker Compose + Dockerfile + systemd unit; **no K8s/Helm** | — | none | root container, unpinned | **FI** | Phase K |

---

## I. Summary counts

| Maturity | Count |
|---|---|
| **PR** Production-ready | 1 |
| **FI** Functional but incomplete | 32 |
| **PT** Prototype | 17 |
| **PH** Placeholder | 3 |
| **DO** Documentation-only | 2 |
| **UN** Unsafe | 7 |
| **BR** Broken | 2 |
| **NF** Not found | 19 |

> **Note on the channel rows.** Four of the five added to §H are marked **PT**
> rather than **FI** for a specific reason: their code is tested, but *nothing has
> ever talked to the other end*. A channel adapter that has never reached a
> provider is a prototype no matter how many tests pass against a fake transport —
> that is the same standard applied to the container sandbox, which was only
> upgraded once it had been run against a real runtime.

### The 7 **Unsafe** items, ranked by urgency
1. Code execution with no sandbox — `core/code_executor.py`
2. Runtime package installation from model output — same file
3. Arbitrary host file write via workspace filename — `core/workspace.py:109`
4. Unauthenticated WebSocket with spoofable identity — `api/routes.py:3003`
5. Constitution as keyword blocklist — `core/constitution.py`
6. LLM directly self-editing canonical memory — `tools/memory_tools.py`
7. Marketplace installing arbitrary tool code — `marketplace/installer.py:258`

### Documentation claims with **no implementation at all** (must be relabelled or removed)
- "90% token savings" — no measurement exists in code; `get_compression_stats()` returns an
  estimate. Must be measured before repeating.
- "Zero external dependencies (pure built-in features)" for memory — contradicted by the
  `chromadb` hard dependency and the heavy optional vision stack.
- "Version control" for workspace — not implemented.
- "Cannot be bypassed via prompt injection" (Constitution) — substring scan only.
- "World-class autonomous agent… same architecture as Code Interpreter/Manus/OpenHands" —
  the loop exists, but without sandboxing, receipts, or approvals it is not equivalent to
  those systems.
