# Single-Container Deployment

> **Status: implemented and build-verified on `feature/v3-digital-beings-os`.**
> Built and run with Docker 29.3.1 / Compose v5.1.1; **9/9 smoke checks pass** and state was
> proven to survive a container restart. See [Verification status](#verification-status) for the
> exact evidence.

Genesis runs as **one container behind one port**. Everything needed at runtime is in the
image:

```
                    ┌──────────────── nginx :8080 (front door) ────────────────┐
   browser ────────▶│  /                    → Next.js Mind Workspace  :3000    │
                    │  /api/  (+ WebSocket) → FastAPI / uvicorn       :8000    │
                    │  /health /docs /avatars/ /generated/ → FastAPI          │
                    │  redis-server                          :6379 (optional) │
                    └──────────────────────────────────────────────────────────┘
                                       │
                                   /data volume
                        (database · ChromaDB · minds · logs · redis)
```

This works because the web app talks to the API on the **same origin** (`/api/v1/...`), so
there is no CORS, no baked-in hostname, and no TLS bypass.

---

## Read this before exposing it to the internet

These are **known, unfixed** issues from `docs/v3/SECURITY_BASELINE.md`. The single container
does not change them, and putting it on a public VPS makes them reachable.

| Risk | Detail | Containment for now |
|---|---|---|
| ~~**SEC-01 — unauthenticated WebSocket**~~ | ~~`ws /api/v1/minds/{id}/stream` accepted connections before any auth check.~~ | ✅ **FIXED.** The handshake now requires a valid credential and identity is derived server-side. Verified in-container: an unauthenticated handshake is refused with HTTP 403. |
| ~~**SEC-02 — workspace path traversal**~~ | ~~Uploaded filenames were used unsanitised; artifact download had no auth and a prefix-match bypass.~~ | ✅ **FIXED.** Filenames validated, containment asserted on every filesystem operation, download now requires auth, uploads size-capped. Verified in-container: 9/9 escape attempts rejected. |
| ~~**SEC-04 — runtime `pip install`**~~ | ~~Imports found in model output could install arbitrary packages.~~ | ✅ **FIXED.** Installation removed and blocked; common libraries are pre-baked at build time via the `tools` extra. |
| ~~**SEC-06 — fake import allow-list**~~ | ~~`ALLOWED_IMPORTS` was emitted into generated code but never enforced.~~ | ✅ **FIXED.** The claim and the constant were removed rather than faked. |
| **SEC-03 — no filesystem/PID/network isolation** | Generated code now runs under a sandbox with a **scrubbed environment, CPU/memory/file/process limits, a wall-clock timeout, bounded output, no installs, and declared-artifact-only export** — but the local provider has **no filesystem, PID or network isolation**, and reports `is_security_boundary: False`. | **This is the remaining blocker.** Generated code can still read files the runtime user can read, and egress is not blocked where the kernel refuses `unshare`. Real containment needs the container provider (gVisor/Kata) in a dedicated sandbox-manager service. |
| **SEC-05 — inherited environment (partial)** | Fixed for the sandbox (verified: provider API keys are invisible to sandboxed code). **MCP server subprocesses still receive `os.environ`.** | Do not configure untrusted MCP servers. |
| **T-16 — default JWT secret** | The app ships a public default secret. | `docker-compose.yml` **refuses to start** unless `API_SECRET_KEY` is set. |
| In-container generated code | Even restricted, generated code shares the container's network and filesystem with the API. | Run the executor as a separate container (`SandboxProvider`, Phase B) before allowing untrusted use. |

**Bottom line:** the API surface is authenticated and path-safe, and untrusted code now runs under
real resource, environment and output controls with no install primitive. But without filesystem,
PID and network isolation it is still not safe to run untrusted code *from untrusted users*. Keep
the port bound to `127.0.0.1` behind a tunnel, or restrict it with a firewall allow-list, until the
container provider lands.

---

## Quick start

```bash
# 1. Configure
cp .env.example .env

# 2. REQUIRED: a real JWT signing key (compose fails fast without it)
#    Windows PowerShell:   [Convert]::ToHexString((1..32 | % {Get-Random -Max 256}))
#    Linux/macOS:
openssl rand -hex 32
#    -> paste into API_SECRET_KEY in .env

# 3. Set at least one model provider key in .env
#    OPENROUTER_API_KEY=...   (free tier: https://openrouter.ai/keys)
#    GROQ_API_KEY=...         (free tier: https://console.groq.com/keys)

# 4. Build and run
docker compose up -d --build

# 5. Open
#    http://<vps-ip>:8080
```

Confirm it is healthy:

```bash
curl -fsS http://localhost:8080/health
docker compose logs -f genesis
```

---

## Configuration reference

Set in `.env` (Compose reads it for both build args and runtime environment).

### Security

| Variable | Required | Notes |
|---|---|---|
| `API_SECRET_KEY` | **Yes** | JWT signing key. Compose aborts if missing. `openssl rand -hex 32`. |
| `CORS_ORIGINS` | No | Leave **empty** for this same-origin setup. Only set if the web app is served from a different origin. |

### Deployment

| Variable | Default | Notes |
|---|---|---|
| `FRONT_PORT` | `8080` | Host port for the single front door. |
| `RUN_MIGRATIONS` | `false` | `false` = the app self-initialises its schema via SQLAlchemy `create_all()`. `true` = Alembic owns the schema (see below). |
| `START_MINDS` | *(empty)* | Comma-separated GMIDs to run as supervised 24/7 daemons, e.g. `GMD-2025-4A7F-9B23`. |
| `ENABLE_REDIS` | `true` | In-container Redis for the LLM response cache. |

### Firebase (optional)

Firebase is **optional**. If `NEXT_PUBLIC_FIREBASE_API_KEY` / `..._PROJECT_ID` are empty the
web app skips Firebase entirely and uses the built-in JWT / API-key auth.

> `NEXT_PUBLIC_*` variables are inlined into the browser bundle at **image build time**.
> If you enable Firebase, set them in `.env` **before** `docker compose build`.

### Models

`OPENROUTER_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`GEMINI_API_KEY`, `DEFAULT_REASONING_MODEL`, `DEFAULT_FAST_MODEL`, `OLLAMA_BASE_URL`.

For fully local models on the VPS, point at a host Ollama:

```
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

---

## Persistence

All state is in the `genesis-data` volume mounted at `/data`:

```
/data
├── .genesis/
│   ├── genesis.db      SQLite: minds, conversations, tasks, GEN ledger, thoughts
│   ├── data/           ChromaDB vectors, generated outputs
│   ├── minds/          per-Mind identity/state JSON
│   └── logs/           action logs, Mind logs
└── redis/              optional cache (disposable)
```

> **Fixed in this branch.** The previous Dockerfile set only `GENESIS_HOME`. Because
> `data_dir`, `minds_dir` and `logs_dir` are *independent* settings, ChromaDB, Mind JSON and
> logs were being written outside `/data` and were **lost on every container rebuild** — only
> the database survived. `docker-compose.yml` now sets all four explicitly.

Backup:

```bash
docker run --rm -v genesis-minds_genesis-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/genesis-backup-$(date +%F).tar.gz -C /data .
```

---

## Operations

```bash
docker compose logs -f genesis          # all services, one stream
docker compose restart genesis          # restart the whole unit
docker compose down                     # stop (volume is kept)
docker compose up -d --build            # rebuild after code changes
docker compose exec genesis bash        # shell inside (as user `genesis`)
```

Logs from all four processes are multiplexed to the container's stdout/stderr, prefixed
`[genesis]`. Log rotation is capped at 3 × 10 MB by the Compose `logging` block.

### Running Minds 24/7

Either set `START_MINDS` (supervised by the entrypoint):

```
START_MINDS=GMD-2025-4A7F-9B23,GMD-2025-11CD-3E4F
```

or start them from the API/UI (`POST /api/v1/minds/{id}/daemon/start`). Daemons launched
through the API live inside this container, so they stop when the container stops — use
`START_MINDS` if you want them to come back automatically after a restart.

Mind daemons are treated as **non-critical**: if one crashes, the API and web workspace stay
up.

### Migrations

`RUN_MIGRATIONS=false` (default) matches how the application already behaves: it creates its
own schema from the current models.

Set `RUN_MIGRATIONS=true` if you want Alembic to own the schema. The entrypoint handles the
awkward case where a database was created by `create_all()` (no `alembic_version` table) by
running `alembic stamp head` instead of `upgrade`, so it does not fail with
"table already exists".

Caveat: `create_all()` only creates *missing tables*, never missing columns. Once you rely on
migrations for column changes, switch to `RUN_MIGRATIONS=true` permanently.

---

## Putting TLS in front

Terminate TLS outside this container and forward to `8080`, then set `FRONT_PORT=127.0.0.1:8080`
so the port is not publicly reachable:

```yaml
# docker-compose.override.yml
services:
  genesis:
    ports:
      - "127.0.0.1:8080:8080"
```

Example Caddy (automatic certificates):

```
genesis.example.com {
    reverse_proxy 127.0.0.1:8080
}
```

The web app derives `wss://` automatically when the page is served over HTTPS — no rebuild
needed for that.

---

## Files in this branch

| File | Purpose |
|---|---|
| `Dockerfile` | 3-stage build: Next.js → Python venv → runtime (nginx + api + web + redis) |
| `docker-compose.yml` | Single-service deployment, `/data` volume, healthcheck, log caps |
| `deploy/docker/entrypoint.sh` | Supervisor: starts/supervises all processes, runs migrations |
| `deploy/docker/nginx.conf` | One front door; WebSocket upgrade handling; no response buffering |
| `deploy/docker/smoke_test.py` | 10-check deployment verification (works from host or inside the container) |
| `deploy/docker/verify_sec02.py` | Replays live path-traversal and unauthenticated-download attempts |
| `deploy/docker/verify_sandbox.py` | 8-check sandbox verification: secrets invisible, install refused, timeout and output caps, artifact control, pre-baked libraries |
| `.dockerignore` | Keeps the build context small; excludes local state and secrets |
| `deploy/docker/docker-compose.split.yml` | The previous redis+api setup, preserved for reference |

### Code changes required to make one image work

| File | Change | Why |
|---|---|---|
| `web-playground/next.config.js` | `output: 'standalone'`; API URL empty in production | Needed for a self-contained server bundle and same-origin requests |
| `web-playground/lib/urls.ts` | **New.** Same-origin HTTP/WS resolution | WebSocket needs an absolute URL; upgrades to `wss://` on HTTPS |
| `web-playground/lib/firebase.ts` | Firebase initialisation is now optional and guarded | **This was a hard build blocker** — see below |
| `web-playground/lib/auth-context.tsx` | Guards all Firebase calls | Same |
| `web-playground/lib/api.ts`, `lib/websocket.ts`, `app/chat/[id]/page.tsx`, `app/create/page.tsx`, `app/mind/[id]/page.tsx`, `components/MindAvatar.tsx`, `components/NotificationBell.tsx`, `components/mind/MemoryTab.tsx` | API URL default changed from `http://localhost:8000` to same-origin | 8 separate hardcoded sites would otherwise call `localhost` from the user's browser |
| `web-playground/package.json` | Removed `NODE_TLS_REJECT_UNAUTHORIZED=0` from scripts | SEC-18; TLS verification is no longer disabled for build/dev |
| `pyproject.toml` | Removed `asyncio` (invalid backport) and a duplicate `pydantic-settings`; moved `opencv-python`/`deepface`/`fer`/`browser-use`/`playwright` into `vision`/`browser` extras; added a `cache` extra | `deepface` pulls TensorFlow — a multi-GB install that would make the image enormous and likely fail on slim. All of these are lazily imported and unused in production mode |
| `.env.example` | Documents `API_SECRET_KEY` and all container variables | The most security-critical setting was previously undocumented |

---

## Verification status

**Executed and passing** (Docker 29.3.1, Compose v5.1.1, local Docker Desktop):

| Check | Result |
|---|---|
| `docker compose build` | ✅ image built (3 stages) |
| `docker compose up -d` | ✅ `Up (healthy)` on `0.0.0.0:8080` |
| `GET /health` via nginx → API | ✅ `{"status":"healthy",...}` |
| `GET /` via nginx → Next.js | ✅ 200, `text/html`, 7.4 KB |
| `POST /api/v1/auth/token` via nginx | ✅ 200, token issued |
| `GET /api/v1/auth/me` with Bearer token | ✅ `user=admin` |
| WebSocket upgrade via nginx | ✅ handshake completes, API answers |
| Persistent layout | ✅ `/data/.genesis/{data,genesis.db,logs,minds}` |
| Database inside volume | ✅ 21 tables created |
| No state outside `/data` | ✅ `/app/.genesis` and `/root/.genesis` absent |
| Runs as non-root | ✅ `uid=10001(genesis)` |
| **State survives restart** | ✅ marker row written, `docker compose restart`, marker still present |

Reproduce with the committed smoke test:

```bash
docker compose cp deploy/docker/smoke_test.py genesis:/tmp/smoke_test.py
docker compose exec genesis python /tmp/smoke_test.py
```

**Not verified** (out of scope for this pass): HTTPS/TLS termination in front of the container,
Ollama connectivity, Firebase auth enabled end-to-end, multi-Mind daemons under `START_MINDS`,
and behaviour under concurrent load.

### Two bugs the real build exposed

Both were found by actually building and running, not by inspection:

**1. The runtime image had no Node.js.** The first run crash-looped with
`env: 'node': No such file or directory` — the runtime base is `python:3.11-slim`, but the web
workspace needs `node` to run the Next.js standalone server. Fixed by copying the `node` binary
from the build stage (both stages are Debian bookworm; `libstdc++6` and `libatomic1` are
installed to satisfy its shared-library deps). This is much cheaper than adding a second
toolchain, since the standalone bundle already ships its own `node_modules`.

**2. The web build failed without Firebase configuration.** `next build` failed with
`FirebaseError: Firebase: Error (auth/invalid-api-key)` while prerendering `/admin`, `/_not-found`,
`/create`, `/login`, `/settings`, `/marketplace`, `/environments` and `/`. `lib/firebase.ts`
called `initializeApp()` + `getAuth()` at **module scope**, which throws when the
`NEXT_PUBLIC_FIREBASE_*` variables are empty. Fixed by making initialisation conditional and
guarded, so the image builds with or without Firebase.

> If you *do* enable Firebase, the `NEXT_PUBLIC_*` values must be present at **build** time, and
> changing them requires a rebuild (not just a restart):
>
> ```bash
> docker compose build --no-cache && docker compose up -d
> ```
