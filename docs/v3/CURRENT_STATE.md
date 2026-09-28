# CURRENT_STATE.md — Genesis AGI v0.1.5-alpha

> **Phase A discovery artifact.** All statements below were verified by inspecting the
> repository at the time of writing. Nothing here is copied from README claims unless the
> code was found to match; discrepancies are recorded in `FEATURE_REALITY_MATRIX.md`.
>
> Verified against commit state: "removed settings in prod" (repo head, ~8 months old).

---

## 1. Repository structure (verified)

```
genesis-agi/
├── alembic/                     8 migration revisions
├── deployment/systemd/          genesis-mind@.service (systemd template unit)
├── docs/                        11 markdown docs (+ this v3/ set)
├── examples/                    7 runnable examples
├── genesis/                     Python package — 155 .py files
│   ├── api/                     FastAPI app, routes, auth, firebase, multimodal
│   ├── cli/                     Typer CLI entry point
│   ├── config/                  pydantic-settings (settings.py, memory_config.py)
│   ├── core/                    57 modules — the Mind runtime
│   ├── database/                SQLAlchemy models + MetaverseDB manager, marketplace
│   ├── environments/            Genesis World: manager, server, realtime, client, templates
│   ├── integrations/            email, calendar, chat, notifications, mcp
│   ├── marketplace/             manager.py, installer.py, db init
│   ├── models/                  7 provider adapters + orchestrator + cache
│   ├── multimodal/              processor.py, processor_pollinations.py
│   ├── plugins/                 20 plugins + registry + base + experimental/
│   ├── safety/                  permissions.py, monitor.py
│   ├── senses/                  vision, speech_input, speech_output, orchestrator
│   ├── storage/                 memory stack (10 modules), conversation
│   ├── templates/               mind templates (loader)
│   └── tools/                   memory_tools, registry
├── mobile-app/                  git submodule (per .gitmodules)
├── tests/                       16 test modules across 4 dirs
├── web-playground/              Next.js 14 app
├── website/                     static marketing site (index.html, script.js, styles.css)
├── Dockerfile, docker-compose.yml, pyproject.toml, alembic.ini, .env.example
```

**Package count:** 155 Python source files under `genesis/`.

---

## 2. Python packages (declared in `pyproject.toml`)

Runtime: `fastapi`, `uvicorn[standard]`, `typer`, `rich`, `pydantic>=2.5`, `pydantic-settings`,
`sqlalchemy>=2.0.25`, `alembic`, `chromadb>=0.4.22`, `openai`, `anthropic`, `google-genai`,
`groq`, `websockets`, `python-multipart`, `python-jose[cryptography]`, `passlib[bcrypt]`,
`python-dotenv`, `firebase-admin`, `httpx`, `aiofiles`, `schedule`, `asyncio`,
`aiosmtplib`, `aioimaplib`, `slowapi`, `pillow`, `browser-use`, `playwright`,
`opencv-python`, `fer`, `deepface`, `requests`, `numpy`, `psutil`, `ddgs`.

Optional `senses` extra: `opencv-python`, `pyaudio`, `pydub`, `google-cloud-speech`,
`google-cloud-texttospeech`.

Note: `asyncio>=3.4.3` is declared as a dependency — the `asyncio` backport is **not** a
valid PyPI dependency for Python 3.11+ (it shadows the stdlib). See `DEPENDENCY_INVENTORY.md`.

`requires-python = ">=3.11"`; classifiers list 3.11 and 3.12. Verified running on **3.12.10**.

---

## 3. Frontend applications

| App | Stack | Location |
|---|---|---|
| Web Playground | Next.js 14, React 18, TypeScript 5, Tailwind 3, Firebase 10, axios, Monaco editor | `web-playground/` |
| Mobile | Flutter (git submodule, contents not present in this checkout) | `mobile-app/` |
| Marketing site | Static HTML/CSS/JS | `website/` |

`web-playground/package.json` scripts set `NODE_TLS_REJECT_UNAUTHORIZED=0` for `dev` and
`build`. This disables TLS certificate verification for the Node process. Recorded in
`SECURITY_BASELINE.md` §15.

---

## 4. API services

Single FastAPI application (`genesis/api/server.py`, `create_app()`), version string `0.1.5`.

Routers mounted:

| Router | Prefix | Declarations found |
|---|---|---|
| `auth_router` | `/api/v1/auth` | 7 |
| `minds_router` | `/api/v1/minds` | ~60 incl. 1 WebSocket |
| `system_router` | `/api/v1/system` | 8 |
| `metaverse_router` | `/api/v1/metaverse` | 10 |
| `settings_router` | `/api/v1/settings` | 3 |
| `marketplace_routes.router` | `/api/v1/marketplace` | separate module |
| `environment_routes.router` | `/api/v1/environments` | separate module |
| `admin_router` | `/api/v1/admin` | 15 |
| `multimodal_routes.router` | `/api/v1/multimodal` | gated by `DISABLE_MULTIMODAL` |

89 router decorators were enumerated in `genesis/api/routes.py` alone.

Cross-cutting middleware: `CORSMiddleware` with `allow_credentials=True`,
`allow_methods=["*"]`, `allow_headers=["*"]`; `slowapi` rate limiter on `/` (10/min) and
`/health` (30/min). Static mounts for `/avatars` and `/generated`.

---

## 5. Database technologies

Three concurrent persistence mechanisms, no single source of truth:

1. **SQLite** (`settings.database_url = "sqlite:///genesis.db"`) via SQLAlchemy 2 ORM +
   Alembic. Path resolves relative to CWD, while other data uses `~/.genesis/` — inconsistent.
2. **ChromaDB** persistent client per Mind at `settings.data_dir / "chroma" / mind_id`
   (`genesis/storage/vector_store.py`), default embedding function (no explicit embedding
   model is configured anywhere).
3. **JSON files** at `~/.genesis/minds/{gmid}.json` for Mind identity/state, plus
   `~/.genesis/logs/{mind_id}/actions.jsonl` for permission logs.

Redis is present in `docker-compose.yml` and referenced by `genesis/models/cache.py`, but is
optional and silently disabled when the `redis` package is missing.

---

## 6. Database schema (ORM tables verified in `genesis/database/models.py`)

`minds`, `environments`, `relationships`, `environment_visits`, `shared_events`,
`metaverse_state`, `tasks`, `gen_transactions`, `mind_files`, `mind_access`, `global_admins`,
`users`, `genesis_core`, `conversation_messages`, `concerns`, `background_tasks`, `thoughts`
— 17 tables. Plus marketplace tables in `genesis/database/marketplace_models.py`.

**Absent:** no tenant table, no ownership join table, no permissions/grants table, no policy
table, no approvals table, no action/receipt table, no audit/event table, no checkpoints, no
budgets, no secrets references, no embodiment tables, no goals/commitments/projects tables
(goals exist only as JSON/file state via `genesis/core/goals.py`).

`mind_access` exists and provides per-mind user grants, but there is no tenant scoping and no
row-level security.

---

## 7. Migration system

Alembic, 8 revisions, linear:

```
001_initial                          (2025-12-07) — metaverse schema
20251219_1200_add_access_control
20260104_1500_add_thought_storage
20260105_1600_add_state_emotional_fields
20260110_0001_add_mind_access_and_is_public
20260110_0002_add_global_admins
20260110_0003_add_users_table
20260128_1400_add_purpose_role_guidance
```

No migration has been added for any V3 control-plane concept (none exist).

---

## 8. Authentication

`genesis/api/auth.py`:
- JWT (HS256) via `python-jose`; `SECRET_KEY` from `settings.api_secret_key`, whose default
  is the literal string `"your-secret-key-change-this-in-production"`.
- Token lifetime: `ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24` (24h). Uses naive
  `datetime.utcnow()` (deprecated).
- `USERS_DB`, a module-level **in-memory dict**, reset on every restart. It previously
  auto-seeded `admin` with the hardcoded password `genesis-admin-2026`; that seed now happens
  only in test/development, or when `GENESIS_ADMIN_PASSWORD` (≥12 chars) is set. The in-memory
  store itself is unchanged — see the note below on why that matters.
- `API_KEYS`, another **in-memory dict**; API keys are lost on restart.
- Firebase ID token verification available (`genesis/api/firebase_auth.py`), optional.
- Password hashing: `bcrypt` via `passlib` import, direct `bcrypt` calls, 72-byte truncation.

Roles: `UserRole` = `admin | user | readonly`.

---

## 9. Authorization

- FastAPI dependencies: `require_admin`, `require_write_access`, and per-endpoint
  `Depends(require_write_access)` on mutating mind routes.
- Mind-level access enforced through the `mind_access` table and `_load_mind` checks.
- `max_minds_per_user: int = 1` settings guard (admins exempt).
- **Gaps:** the WebSocket endpoint performs no authorization (see `SECURITY_BASELINE.md` §7);
  authorization is endpoint-by-endpoint rather than centralized; there is no tenant
  boundary; `global_admins` is the only elevated concept.

---

## 10. Model providers

`genesis/models/orchestrator.py` — `ModelOrchestrator` with 7 adapters:
`openrouter`, `openai`, `anthropic`, `gemini`, `groq`, `pollinations` (no key required),
`ollama` (local, probed with `is_available()`).

Routing is **string-prefix based** (`parse_model_string`): `"provider/model"` or inferred from
name prefix (`gpt`→openai, `claude`→anthropic, `gemini`→gemini, `llama`/`mistral`→ollama).
Defaults: `openrouter/meta-llama/llama-3.3-70b-instruct:free` for both reasoning and fast.

`generate()` **raises `ValueError` if `model is None`** — model must always be passed
explicitly. There is no capability routing, no cost-aware selection, and no thinking-budget
control. `genesis/models/cache.py` provides optional Redis response caching.

---

## 11. Memory providers

`genesis/storage/` (10 modules):
`vector_store.py` (ChromaDB), `memory.py` (MemoryManager + MemoryType),
`smart_memory.py` (SmartMemoryManager), `memory_deduplication.py`, `memory_reranker.py`
(LLM-based), `memory_consolidation.py`, `memory_extractor.py` (LLM extraction),
`memory_blocks.py` (CoreMemory blocks), `conversation.py` (SQLite conversations).

Semantics present: 5 types (episodic/semantic/procedural/prospective/working), importance
scoring, access counts, "temporal decay" implemented as a **relevance multiplier**
(`1%`/day), dedup threshold ~85%, LLM reranking, consolidation, and agent self-editing via
`genesis/tools/memory_tools.py`.

Absent: provenance, confidence, valid-time vs ingestion-time, supersession, contradiction
records, access scope, sensitivity classification, revision history, retention policy,
user-facing correction/dispute/deletion workflow, and any deletion path that also purges the
vector index.

---

## 12. Voice providers

- STT: Groq `whisper-large-v3` via `AsyncGroq`
  (`genesis/multimodal/processor.py:254+`, `processor_pollinations.py:252+`) and OpenAI
  Whisper in `genesis/senses/speech_input.py`. Browser Web Speech API used client-side.
- TTS: ElevenLabs REST (`genesis/senses/speech_output.py:188+`), OpenAI TTS path, and
  browser-native TTS in the playground.
- No VAD, no barge-in, no streaming/realtime speech-to-speech session, no WebRTC.
- `pyaudio`/`pydub` are optional and warned about when missing.

---

## 13. Execution mechanisms (verified call sites)

| Location | Mechanism |
|---|---|
| `genesis/core/code_executor.py:155` | `asyncio.create_subprocess_exec(python, script, cwd=tmpdir)` |
| `genesis/core/code_executor.py:330` | `subprocess.run(['python','-c', f'import {pkg}'])` |
| `genesis/core/code_executor.py:335` | `subprocess.run(['python','-m','pip','install','-q', pkg])` — **auto-install** |
| `genesis/core/code_executor.py:350` | `subprocess.run(['docker','--version'])` (probe only) |
| `genesis/core/tools.py:364` | `subprocess.run(['python3', tmp, json])`, `preexec_fn=None` |
| `genesis/plugins/tools.py:244` | `subprocess.run(["python3", tmp])` |
| `genesis/api/routes.py:2606` | `subprocess.Popen([python, '-m', 'genesis.daemon', ...])` from an API route |
| `genesis/api/routes.py:2638+` | `psutil` process scan + signal to stop daemons |
| `genesis/cli/main.py:459,1002` | `subprocess.run/Popen` for daemon control |
| `genesis/integrations/mcp_integration.py:100` | `subprocess.Popen([cmd]+args, env={**os.environ, ...})` |

`genesis/core/code_parser.py:214` contains `exec(code)` **inside a docstring usage example
only** — there is no live `exec`/`eval` in the main process. This was checked explicitly
because it appeared in a naive grep and must not be reported as a real call site.
(`genesis/core/tools.py:345` does contain a live `eval(input_data)`, but it lives inside the
generated wrapper that is written to a temp file and executed in the subprocess.)

**No `SandboxProvider` abstraction exists anywhere in the repository.** Confirmed by
searching for `SandboxProvider`, `PolicyService`, `ApprovalService`, `AuditService`,
`ActionReceipt`, `EventJournal` — zero matches.

---

## 14. Background processes and daemons

- `genesis/daemon.py` — `MindDaemon`, run as `python -m genesis.daemon --mind-id <GMID>`,
  saving every 300s, graceful shutdown via signals.
- Architectural note in the file: **the daemon owns consciousness; the API server only
  handles user requests.** The API can still spawn the daemon (`routes.py:2606`).
- `genesis/core/action_scheduler.py`, `background_task_executor.py`,
  `genesis/core/living_mind.py` (`LivingMind` loop), `consciousness_v2.py`,
  `proactive_consciousness.py`, `spontaneous_conversation.py`.
- Deployment: `deployment/systemd/genesis-mind@.service` template unit; `docker-compose.yml`
  has the daemon service commented out.

---

## 15. Plugins, tools, agent loops

**Plugins (20):** base, registry, lifecycle, gen, tasks, workspace, roles, events,
relationships, experiences, essence, environments, senses, profiles, learning, sessions,
tools, mcp, perplexity_search, browser_use, proactive_behavior, autonomous_life, +
`experimental/{learning,knowledge,goals}.py`.

Presets in `MindConfig`: `minimal()`, `standard()`, `full()`, `experimental()`.

**Tool execution:** `genesis/tools/registry.py` + `genesis/core/tools.py` `ToolManager`;
`genesis/plugins/tools.py` overrides `_execute_tool_code` with real subprocess execution.

**Agent loop:** `genesis/core/autonomous_orchestrator.py` — `AutonomousOrchestrator`
orchestrates `autonomous_reasoner.py` (plan) → `code_generator.py` (generate) →
`code_executor.py` (execute) → memory write (learn). Supporting: `intent_classifier.py`
(LLM-first intent), `task_detector.py` (fallback), `universal_file_handler.py`,
`cognitive_framework.py`.

---

## 16. Deployment configuration

- `Dockerfile`: single image, `pip install --no-cache-dir -e .`.
- `docker-compose.yml`: `redis:7-alpine` + `genesis-api` (port 8000), volumes
  `genesis-data:/data` and `./genesis:/app/genesis`, `restart: unless-stopped`,
  healthcheck via `/health`. `DISABLE_MULTIMODAL=true`, `FIREBASE_ENABLED=true`.
  The web playground and mind-daemon services are commented out.
- No Kubernetes/Helm manifests exist.
- No non-root `USER` directive was observed in the Dockerfile.
- `deployment/systemd/genesis-mind@.service` for host-level 24/7 operation.

---

## 17. Tests

16 test modules (see `TEST_BASELINE.md` for the executed baseline):
`tests/{test_admin, test_conversation_pagination, test_emotional_intelligence,
test_memory_user_scoping, test_mind_access, test_mind_gens_coercion,
test_users_and_env_access}.py`, `tests/api/{test_routes, test_conversation_api,
test_auth}.py`, `tests/core/test_tools.py`, `tests/storage/test_memory.py`, `conftest.py`.

No `tests/security/`, no `tests/integration/`, no `tests/e2e/`, no `tests/evals/`.
No Playwright tests. No load tests. No migration tests.

---

## 18. Main domain entities (as implemented)

`MindIdentity` (pydantic, `core/identity.py`) with `gmid`, `digital_fingerprint` (a random
SHA-256-derived string, not a verifiable credential), `birth_timestamp`, `lifespan_years`,
`gens`, `is_public`, purpose/role/guidance fields.
`EmotionalState` (arousal/valence), `LifecycleState`, `Role`, `Relationship`, `Task`,
`GenTransaction`, `Environment`, `Experience`, `Event`, `Goal`, `Workspace`, `Tool`,
`Plugin`. Persistence is split across ORM, JSON, and ChromaDB.

---

## 19. Main runtime flows (verified)

**Chat:** HTTP `POST /api/v1/minds/{id}/chat` → `_load_mind` (with cache) → `mind.think` /
`stream_think` → intent classifier → memory retrieval → orchestrator `generate()` →
response → memory extraction → conversation persistence → GEN/lifecycle side effects.

**Autonomous agent:** request → `AutonomousOrchestrator` → reasoner plan → code generation →
`CodeExecutionEngine.execute_code` → subprocess → result → memory write.

**Consciousness (daemon):** `LivingMind` loop → `ConsciousnessEngineV2` awareness level from
biological state/needs/circadian phase → `RuleEngine` (no LLM when possible) → optional
`LLMGateway` call with daily budget caps → activity + thought persistence.

**WebSocket:** unauthenticated accept → `_get_cached_mind` → register socket against a
caller-supplied `user_email` → streaming chat loop.

---

## 20. External integrations

`genesis/integrations/`: email (SMTP/IMAP via aiosmtplib/aioimaplib), calendar (Google API,
optional import), chat (Slack SDK / discord.py, optional imports), notifications
(Twilio/Firebase, optional imports), MCP client (stdio/HTTP/WS transports).
`genesis/plugins/browser_use_plugin.py` (browser automation, optional), `perplexity_search`.
`genesis/marketplace/` (item listing, purchase, install).

---

## 21. Verified absences (V3 control plane)

Confirmed zero occurrences of: `SandboxProvider`, `PolicyService`, `ApprovalService`,
`AuditService`, `ActionReceipt`, `EventJournal`, `CognitiveCheckpoint`, `DurableCognition`,
`ModelRouter` (capability/cost-based), `IdentityManifest`, `Embodiment`, tenant isolation,
row-level security, OpenTelemetry instrumentation, MCP **server** (only a client exists).

---

## 22. Environment / configuration surface

`genesis/config/settings.py` (pydantic-settings, `.env`). Notable defaults:
`cors_origins = "*"`, `api_secret_key = "your-secret-key-change-this-in-production"`,
`database_url = "sqlite:///genesis.db"`, `action_logging_enabled = True`,
`require_approval_for_external_actions = True`, `max_autonomous_actions_per_hour = 100`,
`max_minds_per_user = 1`, `consciousness_tick_interval = 60`.

`.env.example` (35 lines) documents model keys, CORS, Ollama, consciousness, safety, and
Firebase — but **not** `API_SECRET_KEY`/`SECRET_KEY`, which is the most security-critical
setting in the system.
