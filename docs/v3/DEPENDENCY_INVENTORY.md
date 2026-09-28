# DEPENDENCY_INVENTORY.md

> Every dependency must have a documented purpose, an owner abstraction, configuration,
> tests, failure handling, and an exit strategy (V3 §10). This file establishes that record
> for the current tree and flags the ones with no exit strategy or no owner abstraction.

---

## 1. Python runtime

| Item | Current | Target | Notes |
|---|---|---|---|
| Python | `>=3.11` declared; verified on **3.12.10** | 3.12 | Classifiers claim 3.11/3.12. mypy config pins `python_version = "3.11"` which is now incompatible with installed numpy stubs (see §6). |

---

## 2. Direct runtime dependencies (`pyproject.toml`)

| Package | Declared | Purpose | Owner abstraction | Exit strategy | Risk |
|---|---|---|---|---|---|
| `fastapi` | `>=0.108.0` | HTTP API | `genesis/api/server.py` | Low (framework-standard) | Low |
| `uvicorn[standard]` | `>=0.25.0` | ASGI server | `api/server.py:run_server` | n/a | Low |
| `typer` | `>=0.9.0` | CLI | `genesis/cli/main.py` | n/a | Low |
| `rich` | `>=13.7.0` | CLI rendering | CLI only | n/a | Low |
| `pydantic` | `>=2.5.0` | Domain models | pervasive | n/a | Low |
| `pydantic-settings` | `>=2.1.0` (duplicated entry) | Config | `config/settings.py` | n/a | Low (duplicate key) |
| `sqlalchemy` | `>=2.0.25` | ORM | `database/models.py` | n/a | Low |
| `alembic` | `>=1.13.0` | Migrations | `alembic/` | n/a | Low |
| `chromadb` | `>=0.4.22` | Vector store | `storage/vector_store.py` | **Weak** — no provider interface | **High** (see §3) |
| `openai` | `>=1.7.0` | OpenAI + OpenRouter(compat) | `models/openai_provider.py`, `openrouter_provider.py` | Medium | Medium |
| `anthropic` | `>=0.8.0` | Claude | `models/anthropic_provider.py` | Medium | Medium |
| `google-genai` | unpinned | Gemini (declared) | `models/gemini_provider.py` uses **`google.generativeai`**, not `google-genai` | **Broken/mismatched** | **High** |
| `groq` | `>=0.4.0` | Fast inference + Whisper | `models/groq_provider.py`, `multimodal/processor.py` | Medium | Medium |
| `websockets` | `>=12.0` | WS transport | FastAPI/uvicorn + environments | n/a | Low |
| `python-multipart` | `>=0.0.6` | File uploads | API | n/a | Low |
| `python-jose[cryptography]` | `>=3.3.0` | JWT | `api/auth.py`, `api/firebase_auth.py` | Medium | Medium |
| `passlib[bcrypt]` | `>=1.7.4` | Password hashing | `api/auth.py` | n/a | Low |
| `python-dotenv` | `>=1.0.0` | `.env` loading | settings | n/a | Low |
| `firebase-admin` | `>=6.3.0` | Firebase auth | `api/firebase_auth.py` | Medium | Medium |
| `httpx` | `>=0.26.0` | HTTP client | providers, integrations | n/a | Low |
| `aiofiles` | `>=23.2.1` | Async file I/O | workspace | n/a | Low |
| `schedule` | `>=1.2.0` | Scheduling | core | n/a | Low |
| `asyncio` | `>=3.4.3` | **Invalid dependency** | stdlib backport; shadows stdlib on 3.11+ | **Remove** | **Medium** |
| `aiosmtplib` | `>=3.0.0` | Email SMTP | `integrations/email_integration.py` | Medium | Low |
| `aioimaplib` | `>=1.0.1` | Email IMAP | `integrations/email_integration.py` | Medium | Low |
| `slowapi` | `>=0.1.9` | Rate limiting | `api/server.py` | n/a | Low |
| `pillow` | `>=10.0.0` | Images | multimodal | n/a | Low |
| `browser-use` | `>=0.1.5` | Browser automation | `plugins/browser_use_plugin.py` | **Weak** — guided install at runtime | **High** |
| `playwright` | `>=1.40.0` | Browser driver | browser use | Weak | High |
| `opencv-python` | `>=4.8.0` | Vision | `senses/vision.py` | Weak | Medium |
| `fer` | `>=22.5.0` | Facial emotion | vision | Weak | Medium |
| `deepface` | `>=0.0.79` | Face analysis | vision | Weak | **High** (pulls heavy TF/keras stack) |
| `requests` | `>=2.31.0` | Sync HTTP | residual | n/a | Low |
| `numpy` | `>=1.24.0` | Numerics | residual | n/a | Low |
| `psutil` | `>=5.9.0` | Process control | `api/routes.py` daemon stop | n/a | Medium (privileged) |
| `ddgs` | `>=6.0.0` | Web search | search plugin | Medium | Medium |

### Findings

1. **`google-genai` is declared but not used.** `genesis/models/gemini_provider.py`
   imports `google.generativeai` and instructs users to `pip install google-generativeai`.
   Declared dependency and code disagree.
2. **`pydantic-settings` is listed twice** in `dependencies`.
3. **`asyncio` must be removed** from `dependencies`.
4. **`deepface`/`fer`/`opencv-python` are hard runtime dependencies for a vision feature that
   is disabled in the production compose file** (`DISABLE_MULTIMODAL=true`). These pull a
   very large transitive surface (TensorFlow/keras) for zero production value. Move to an
   optional extra.
5. **`browser-use` + `playwright` ship in the default install** and are invoked by an agent
   that executes model-directed browser actions. High supply-chain and capability risk with
   no owner abstraction.
6. **`chromadb` has no provider interface.** It is imported directly in
   `storage/vector_store.py:3`. Migrating to pgvector requires touching call sites.
7. **No dependency pinning strategy.** All constraints are `>=`; no lockfile exists
   (no `requirements.txt`, no `uv.lock`, no `poetry.lock`). Builds are not reproducible.

---

## 3. Transitive / implicit dependencies

| Item | Used by | Notes |
|---|---|---|
| `redis` | `models/cache.py` (optional, guarded import) | Present in compose; not in `pyproject` |
| `google-api-python-client` | `integrations/calendar_integration.py` | Not declared; runtime warning |
| `slack-sdk`, `discord.py` | `integrations/chat_integration.py` | Not declared; runtime warning |
| `twilio` | `integrations/notification_integration.py` | Not declared; runtime warning |
| `pyaudio`, `pydub` | `senses/speech_*` | `senses` extra |
| `google-cloud-speech`, `google-cloud-texttospeech` | `senses` extra | Declared but not used in the code paths inspected |
| `matplotlib`, `pandas`, `pdfplumber`, `PyPDF2`, `python-pptx` | **generated code at runtime** | Never declared anywhere; produced by the code generator and installed on demand |

The last row is the core architectural problem: **the dependency set of a Genesis Mind is
open-ended at runtime** because generated code may import anything.

---

## 4. Frontend dependencies (`web-playground/package.json`)

| Package | Version | Notes |
|---|---|---|
| `next` | `^14.0.0` | App router |
| `react`, `react-dom` | `^18.2.0` | |
| `typescript` | `^5.2.2` | |
| `tailwindcss` | `^3.3.0` | |
| `firebase` | `^10.7.1` | Client auth |
| `axios` | `^1.6.0` | API client |
| `@monaco-editor/react` | `^4.6.0` | Code display |

Dev-only risk: `dev`/`build` scripts set `NODE_TLS_REJECT_UNAUTHORIZED=0`.

No lockfile was inspected in this pass; `npm ci` reproducibility is unverified.

---

## 5. Container / deployment dependencies

| Item | Notes |
|---|---|
| `redis:7-alpine` | Pinned by major tag only |
| Base Python image | Dockerfile base not pinned by digest; `pip install -e .` at build |
| System packages | None installed explicitly; `playwright install chromium` is a documented manual step for browser use |
| Docker socket | Not mounted (good) |
| Container user | No `USER` directive observed — container runs as root |

---

## 6. Toolchain / development dependencies

| Tool | Declared | Status at baseline |
|---|---|---|
| `pytest` | `>=7.4.3` | Installed 9.1.1 — runs |
| `pytest-asyncio` | `>=0.21.1` | Installed; `asyncio_mode = "auto"` in config |
| `pytest-cov` | `>=4.1.0` | Not verified |
| `black` | `>=23.12.1` | Config present (`line-length = 100`) |
| `ruff` | `>=0.1.9` | Ran: **3473 errors**, 2302 auto-fixable |
| `mypy` | `>=1.8.0` | **Broken under repo config** — `python_version = "3.11"` vs numpy 2.5 stubs; 1187 errors with `--python-version 3.12` |
| `pre-commit` | not declared | Absent (V3 §10 requires it) |

No `Makefile`, no `tox.ini`, no CI workflow files were found in the repository root.

---

## 7. Required remediation (dependency-driven)

1. Remove `asyncio` from dependencies; de-duplicate `pydantic-settings`.
2. Reconcile `google-genai` vs `google.generativeai`, or drop the unused declaration.
3. Move `deepface`, `fer`, `opencv-python`, `browser-use`, `playwright` into optional
   extras so the default install is small and auditable.
4. Add a lockfile and pin container base images by digest for reproducible builds.
5. Introduce a `VectorStoreProvider`/`MemoryStore` interface so `chromadb` becomes an
   adapter rather than a hard import (Phase E).
6. Replace open-ended runtime installation with **declared, pre-baked tool images** (Phase B).
7. Add `pre-commit` with ruff + mypy + tests, and fix the mypy `python_version` setting.
