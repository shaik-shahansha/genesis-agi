# SECURITY_BASELINE.md

> Recorded **before** any behavioural change, per V3 §7. Every finding below cites the exact
> file and line inspected. Severity reflects impact on a default deployment.
>
> Severity: **C**ritical (host compromise / unauthorised data access today) ·
> **H**igh (trivially exploitable or blocks enterprise use) · **M**edium (real but requires
> preconditions) · **L**ow (hardening).

---

## 0. Summary

| ID | Severity | Finding |
|---|---|---|
| SEC-01 | ~~**C**~~ **FIXED** | Unauthenticated WebSocket accepts any `user_email` and falls back to a shared identity |
| SEC-02 | ~~**C**~~ **FIXED** | Arbitrary host file write via unsanitised `filename` in workspace upload/create |
| SEC-03 | **C** → **MITIGATED (partial)** | Model-generated code executes with no sandbox, no resource limits, no egress control |
| SEC-04 | ~~**C**~~ **FIXED** | Runtime `pip install` driven by imports found in model-generated code |
| SEC-05 | **H** → **PARTIAL** | Full host environment inherited by subprocesses: fixed for the sandbox; **MCP servers still inherit `os.environ`** |
| SEC-06 | ~~**H**~~ **FIXED** | Advertised import allow-list in tool sandbox is never enforced |
| SEC-07 | **H** | Arbitrary marketplace tool code persisted and later executed |
| SEC-08 | **H** → **PARTIAL** | In-memory user store, hardcoded default admin password, default JWT secret. The password and the secret are closed; the in-memory store is not |
| SEC-09 | **H** | API process spawns and kills OS processes (daemon control, `psutil`) |
| SEC-10 | **H** | CORS default `*` combined with `allow_credentials=True` |
| SEC-11 | **M** | Permission model cannot satisfy `REQUIRES_CONFIRMATION`; approval setting unwired |
| SEC-12 | **M** | "Constitution" is a substring keyword blocklist |
| SEC-13 | **M** | Action audit log is mutable local JSONL with no integrity protection |
| SEC-14 | ~~**M**~~ **FIXED** | Unbounded memory read on file upload (no size limit) |
| SEC-15 | **M** | Memory poisoning: LLM-extracted memories written with no provenance/validation |
| SEC-16 | **M** | Prompt-injection surface: web/file/MCP content shares the instruction context |
| SEC-17 | **M** | No tenant isolation; shared mutable Mind instances in a process-wide cache |
| SEC-18 | **M** | `NODE_TLS_REJECT_UNAUTHORIZED=0` in frontend dev/build scripts |
| SEC-19 | **M** | No dependency locking; container base images unpinned; container runs as root |
| SEC-20 | **L** | Naive `datetime.utcnow()`/`datetime.now()` throughout (230 + 20 lint hits) |
| SEC-21 | **L** | No observability/trace context; logs may carry prompts and personal content |
| SEC-22 | **M** | Placeholder endpoints presented as functional (`POST /settings/api-keys` is a no-op) |

---

## 1. Direct code execution — **MITIGATED (partial)** 2026-09-28

> **Resolution.** All three paths now execute through ``SandboxProvider``
> (`genesis/sandbox/`). Direct process spawning outside that package is blocked by an
> architectural guard test (`tests/security/test_sandbox_boundary.py`).
>
> **Enforced now:** a scrubbed environment with only an explicit allow-list (SEC-05),
> CPU/address-space/file-size/process limits via a self-limiting runner, wall-clock
> timeout with process-group kill, bounded stdout/stderr, no runtime package
> installation (SEC-04), a single private working directory, artifact export restricted to
> declared names, and honest capability reporting so a receipt can record what was actually
> enforced.
>
> **Not yet enforced:** filesystem isolation, PID-namespace isolation, and network
> isolation. The local provider is explicitly *not* a security boundary; it reports
> ``is_security_boundary: False``. Real containment needs the container provider
> (gVisor/Kata), which requires a Docker endpoint and therefore belongs in a dedicated
> sandbox-manager service rather than in the API container (ADR-0005).
>
> **Also found and fixed while testing:**
> * ``pids_limit`` defaulted to 64, but ``RLIMIT_NPROC`` is per-*user*, so the API and
>   nginx threads counted against the sandbox. Numeric libraries (OpenBLAS inside numpy)
>   failed to create threads and aborted with SIGINT. Default raised to 1024, with BLAS/OMP
>   thread pools capped to 1 in the sandbox environment.
> * Wall-clock timeouts were reported as successful completions: the kill sets
>   ``returncode``, so inferring timeout from ``returncode is None`` afterwards was a race.
>   ``_drain`` now returns the flag explicitly.
>
> **Verification:** `deploy/docker/verify_sandbox.py` — 8/8 checks in the running container,
> including that provider secrets are invisible to sandboxed code and that the timeout and
> output caps hold.

### Original finding (retained for the record)

**Three independent execution paths exist, none sandboxed.**

### 1a. `genesis/core/code_executor.py` — the autonomous agent path (SEC-03, SEC-04)
- Line ~155: `asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE, cwd=str(tmpdir))`
  where `cmd = ["python", str(code_file)]`.
- The docstring itself states the truth: *"Security layers: 1. Subprocess with timeout
  2. Resource limits (future) 3. Output truncation 4. No network access by default (future)"*.
  Layers 2 and 4 do not exist.
- No seccomp/AppArmor, no cgroups, no memory/CPU/PID caps, no separate network namespace,
  no read-only rootfs. The subprocess inherits the parent process environment (all secrets)
  and the host network.
- Line ~95 comment: *"For now, use subprocess (Docker support later)"*, and
  `_docker_available()` (line ~347) is only a probe — Docker is never actually used.
- Docker socket is **not** mounted, which is correct and must be preserved.

### 1b. `genesis/core/tools.py` — `ToolManager._execute_tool_code` (SEC-03)
- Line ~310: local `import subprocess`.
- Line ~364: `subprocess.run(['python3', temp_file, json.dumps(input_data)], capture_output=True, text=True, timeout=execution_timeout, preexec_fn=None)`.
- The comment on the same call reads *"Security: Limit resources (Linux only)"* followed by
  `preexec_fn=None,  # Could add resource limits here`. No limits are applied.
- The generated wrapper embeds `{tool.code}` verbatim; line ~345 executes
  `eval(input_data)` when no `execute`/`main` symbol is found.

### 1c. `genesis/plugins/tools.py` — `ToolsPlugin._execute_tool_real` (SEC-03, SEC-06) — **FIXED**
- Line ~244 previously ran `subprocess.run(["python3", temp_file], ...)` with the comment
  *"Note: This doesn't fully sandbox - use Docker for production"*.
- The wrapper emitted `ALLOWED_IMPORTS = {self.allowed_imports}`, which was **never
  consulted** — no `__import__` hook, no meta-path finder, no `__builtins__` restriction.
  Name-based import restriction is not a control (`importlib` and `__import__` defeat it),
  so the constant has been **removed rather than faked**, along with the claim in the
  plugin's system prompt. Both are now asserted absent by a test.

### 1d. Platform inconsistency (correctness + security)
Paths 1b and 1c invoke the literal string `python3`; path 1a invokes `python`. On Windows two
of the three paths cannot run at all. This also means no single place governs which
interpreter executes untrusted code.

### 1e. `genesis/core/code_parser.py` — verified **not** a live call site
`exec(code)` appears at line ~214 **inside a docstring usage example** for the convenience
function `extract_python`. There is no live `exec`/`eval` in the main process. This is
recorded explicitly so that a future grep-based audit does not re-raise it as a false
positive, and so the real call sites above stay the focus.

---

## 2. Shell execution

- `genesis/cli/main.py:459` `subprocess.run(["genesis","daemon","stop", gmid], ...)`;
  `:1002` `subprocess.Popen(...)` with a log file handle.
- `genesis/api/routes.py:2606` `subprocess.Popen([python_exe, "-m", "genesis.daemon",
  "--mind-id", mind_id], stdout=PIPE, stderr=PIPE, start_new_session=True)`.
- No `shell=True` was found anywhere. Command arguments are list-form, so classic shell
  injection via argument strings is **not** present in these call sites — the risk here is
  privilege and lifecycle (SEC-09), not string interpolation.
- MCP transport: `genesis/integrations/mcp_integration.py:100`
  `subprocess.Popen([self.config.command] + self.config.args, ..., env=env, text=True, bufsize=1)`
  where `env = {**os.environ, **self.config.env}` at line ~98. **Every secret in the API
  process is handed to every configured MCP server** (SEC-05). `command` and `args` come from
  server configuration with no allow-list.

---

## 3. Dynamic installation

`genesis/core/code_executor.py`:

```
_extract_dependencies_from_code(code)        # regex over 'import X' / 'from X import Y'
    → map to PyPI names via package_map (pandas, matplotlib, PyPDF2, pdfplumber, ...)
_ensure_dependencies_installed(deps, tmpdir)
    → subprocess.run(['python', '-c', f'import {package}'])
    → if that fails: subprocess.run(['python', '-m', 'pip', 'install', '-q', package])
```

Consequences:
1. **A model can cause arbitrary PyPI packages to be installed** into the host interpreter
   by emitting an import. This is a direct supply-chain execution primitive (SEC-04).
2. Package names are interpolated into a `-c` string (`f'import {pkg}'`) — names come from
   regex over model output, so this is also a **string-injection** point.
3. Installations are global and persistent; they mutate the runtime for every Mind.
4. There is no allow-list, no version pinning, no hash verification, no lockfile.
5. `genesis/plugins/browser_use_plugin.py:102` similarly instructs runtime installation of
   `browser-use playwright langchain-openai` plus a Chromium download.

---

## 4. Untrusted deserialization

- No `pickle`, `marshal`, or `yaml.load` (unsafe) usage was found in the audited paths.
- JSON is used throughout (`json.loads`), which is safe by construction.
- Residual risk: `plugins` and marketplace item payloads arrive as `Dict[str, Any]` and are
  applied with little validation (§7). Archive handling for any `.zip`/`.tar` upload is
  **not implemented and not verified** — treated as an open item rather than a confirmed
  finding.

---

## 5. Secret handling

| Issue | Evidence |
|---|---|
| Default JWT secret shipped in code | `settings.py`: `api_secret_key: str = "your-secret-key-change-this-in-production"`; also `secret_key` same value. `api/auth.py` reads it with no guard. |
| Secret not documented in onboarding | `.env.example` (35 lines) documents model keys, CORS, Ollama, consciousness, safety, Firebase — but **not** `API_SECRET_KEY`/`SECRET_KEY`. Deployments will run on the default. |
| Secrets inherited by subprocesses | Every execution path inherits the parent environment; MCP doubles down at `mcp_integration.py:98`. |
| Secrets in prompt/log surface | `settings_router.get_api_keys` returns masked values from `os.getenv` at request time; the execution engine prints stdout/stderr of untrusted code (`print("[CODE EXEC] ...")`) into process logs. |
| No secret broker | There is no `SecretReference` concept; keys are raw environment strings read directly by providers. |

---

## 6. Authentication risks

- `genesis/api/auth.py` holds `USERS_DB: Dict[str, Dict[str, Any]] = {}` — an **in-memory
  user store**, reset on every restart, with the code comment *"should be replaced with
  database in production"*. **Still open.** It is why the bootstrap account below mattered so
  much: with the store in memory, the seeded `admin` was the only account that survived a
  restart, so it was not merely a leftover default but the *only* way into a restarted
  deployment.
- ~~`_initialize_default_users()` seeds `admin` with password **`genesis-admin-2026`**, public
  in the source. There is no forced rotation and the value is not marked as a placeholder in
  any startup warning.~~ **Fixed.** The account is now created only in test/development, or
  when `GENESIS_ADMIN_PASSWORD` is set and at least 12 characters. Outside those it is not
  created at all, and the process logs the command needed to bootstrap one. `docker-compose.yml`
  requires the variable, so a deploy fails fast rather than starting with a known credential.
  Guarded by `tests/security/test_default_admin.py` (10 tests), including that an unset
  `GENESIS_ENV` is treated as production and that the seed no longer happens as a side effect
  of a login attempt.
- `API_KEYS: Dict[str, Dict[str, Any]] = {}` is also in-memory; API keys do not survive
  restarts, and their format is `gen-api-<random>` (verified in `tests/api/test_auth.py`).
- Token lifetime is 24 hours (`ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24`), with no refresh or
  revocation mechanism.
- No brute-force protection on `POST /api/v1/auth/token` (rate limiting is only applied to
  `/` and `/health`).
- Firebase verification is optional and the code path degrades silently on failure
  (`except Exception: pass` patterns in the WebSocket handler).

---

## 7. Authorization risks — SEC-01 (critical) — **FIXED 2026-09-28**

> **Resolution.** The endpoint now authenticates during the handshake, before
> `accept()`, using the same verification path as HTTP (`resolve_user_from_token` /
> `resolve_user_from_api_key` via the new `authenticate_websocket` helper). The user
> identity is derived server-side from the verified credential; `?user_email=` is no
> longer read at all. Unauthenticated handshakes are refused with HTTP 403; a user
> without access to the Mind is closed with code 1008. Mind access follows the same
> rules as the HTTP endpoints (admin / explicit grant / public / creator).
>
> Covered by `tests/security/test_websocket_auth.py` (17 tests, all passing) and by
> `deploy/docker/smoke_test.py`, which asserts an unauthenticated handshake is refused
> against the running container.
>
> *Remaining:* the environment WebSocket (`/api/v1/environments/ws/{id}`) still has its
> original handling. A token in a query string can also reach access logs, so the
> bundled nginx config strips query strings from its log format.

### Original finding (retained for the record)

`genesis/api/routes.py:3003`:

```python
@minds_router.websocket("/{mind_id}/stream")
async def websocket_chat(websocket: WebSocket, mind_id: str):
    await websocket.accept()                       # ← accepted before any auth check

    user_email = websocket.query_params.get("user_email")   # ← client-supplied identity
    ...
    if not user_email:
        user_email = "web_user@genesis.local"      # ← silent shared fallback
        logger.warning("WebSocket connected without user_email; defaulting to ...")
```

Then:

```python
mind = await _get_cached_mind(mind_id)
mind.notification_manager.register_websocket(user_email, websocket)
await send_pending_notifications(mind, user_email, websocket)
... 
async for chunk in mind.stream_think(message, user_email=user_email):
```

Impact:
1. **No authentication.** `accept()` precedes every check, and the handler proceeds with a
   default identity if none is supplied. Anyone who can reach the port and knows/guesses a
   `mind_id` can open a full chat session.
2. **Identity spoofing.** `user_email` is a query parameter. Passing
   `?user_email=victim@example.com` makes the Mind treat the caller as that user for memory
   scoping and personalisation.
3. **Data exposure.** `send_pending_notifications` delivers the *other user's* pending
   proactive notifications to the socket, and `register_websocket` registers the attacker's
   socket under the victim's email so subsequent proactive messages are delivered to them.
4. The Bearer-token fallback is wrapped in `except Exception: pass`, so a present-but-invalid
   token is treated the same as no token.

This is the highest-severity product finding: it defeats the per-user memory isolation that
the rest of the system is built around.

---

## 8. Tenant isolation risks — SEC-17

- No `tenant` concept exists in the schema or in authorization.
- `_get_cached_mind` returns a **shared mutable `Mind` object** across requests; concurrent
  requests for the same GMID share one instance, its memory manager, its notification
  registrations, and its plugin state. There is no per-request isolation and no locking.
- `max_minds_per_user = 1` is the only cross-user guard; it is a product limit, not a
  security boundary.
- Cross-user data risk is therefore real: any bug in memory scoping (the existing failing
  test `test_users_and_env_access` suggests scoping is already incorrect) exposes other
  users' memories.

---

## 9. Network exposure

- `settings.api_host = "0.0.0.0"` by default; the compose file publishes `8000:8000`.
- `DISABLE_MULTIMODAL=true` in compose reduces the exposed surface — a mitigation worth
  preserving.
- No TLS termination in the application; no HSTS; no security headers middleware
  (no CSP, `X-Content-Type-Options`, `X-Frame-Options`, or `Referrer-Policy`).
- WebSocket is `ws://` (no `wss://` enforcement).
- SSRF: the agent fetches URLs (web search, browser-use, generated code, MCP HTTP/WS
  transports). There is no URL allow-list, no private-IP/link-local blocking, no redirect
  policy, and no egress proxy. Generated code also has unrestricted outbound network.

---

## 10. File upload risks — SEC-02 (critical), SEC-14 — **FIXED 2026-09-28**

> **Resolution.** A shared path-safety module (`genesis/core/paths.py`) now provides
> `safe_filename()` (rejects separators, traversal, absolute/UNC paths, drive letters,
> control characters, device names, over-length, and normalises Unicode) and
> `ensure_within()` (resolves and asserts containment, so symlink escapes are rejected too).
> `WorkspaceManager` validates on create and re-validates on **every** read/update/delete,
> because a persisted registry is also untrusted input. Callers no longer join
> `workspace_path` themselves: binary uploads go through `create_file(raw_bytes=...)`.
>
> Three additional problems were found and fixed while addressing this:
>
> 1. **`delete_file` could unlink outside the workspace.** It joined the stored
>    (attacker-influenced) `filepath` onto the workspace root with no check.
> 2. **`GET /minds/{id}/artifacts/download` had no authentication at all**, and its
>    containment check used `str(path).startswith(str(dir))` — a classic prefix bypass
>    (`/data-evil` starts with `/data`). With `Path.cwd()` allow-listed, arbitrary file
>    read under the app directory was reachable.
> 3. **Uploads were read entirely into memory** with no bound; now capped by
>    `MAX_UPLOAD_SIZE_MB` (default 100) with a 413 response.
>
> Coverage: `tests/security/test_workspace_paths.py` (32 tests) plus
> `deploy/docker/verify_sec02.py`, which replays live traversal and unauthenticated
> download attempts against the running container (9/9 pass, and a filesystem scan
> confirms nothing was written outside `/data`).

### Original finding (retained for the record)

`genesis/api/routes.py:1759` `POST /minds/{mind_id}/workspace/upload`:

```python
content = await file.read()                       # ← no size limit; whole file in memory
...
mind_file = mind.workspace.create_file(
    filename=file.filename,                       # ← unsanitised, client-controlled
    ...
)
if not content_str:
    file_path = mind.workspace.workspace_path / mind_file.filepath
    file_path.write_bytes(content)
```

`genesis/core/workspace.py:109`:

```python
filepath = self.workspace_path / filename
filepath.write_text(content)
```

`filename` is never validated. `pathlib` semantics mean:
- `filename = "sub/dir/x.txt"` escapes the intended flat layout;
- `filename = "../../../../etc/cron.d/x"` traverses upward;
- an **absolute path** (e.g. `C:\Windows\...` on Windows, `/etc/...` on Linux)
  **replaces the base path entirely** in `base / absolute`.

Result: **arbitrary file write with attacker-controlled content, as the API process user.**
No extension allow-list, no MIME/type verification, no content scanning, no size cap, and no
post-write containment. This is directly exploitable by any authenticated user with write
access to a mind.

Related: `genesis/core/workspace.py` write paths (lines ~153, ~168, ~182) repeat the same
`self.workspace_path / mind_file.filepath` pattern, so any code that can influence
`filepath` reaches the same primitive.

---

## 11. Prompt injection and tool injection surfaces — SEC-16

Everything below is concatenated into the same context handed to the model, with no
separation between *instructions* and *data*:

- Web search results (`ddgs`, Perplexity plugin).
- Fetched pages and browser-use output (`plugins/browser_use_plugin.py`).
- Uploaded file contents, including PDFs and documents (`universal_file_handler.py`).
- Retrieved memories — **including memories previously derived from any of the above**
  (self-reinforcing; see SEC-15).
- MCP tool **descriptions and schemas** from external servers (`integrations/mcp_integration.py`).
- Plugin metadata from the marketplace.

There is no untrusted-content wrapping, no data/instruction delimiting, no provenance tag on
retrieved content, and no model-side policy classifier. `constitution.py` is applied to the
*user prompt* only, as a substring scan — it does not inspect retrieved content at all.

---

## 12. Memory poisoning risks — SEC-15

- `genesis/storage/memory_extractor.py` runs an LLM over conversation content and writes the
  result as memory. The write path validates shape but has no notion of *source trust*.
- A poisoned document (or a poisoned web page, or a poisoned memory recalled from earlier)
  therefore becomes a durable, high-trust fact that is re-injected into future contexts and
  can influence autonomous action.
- There is **no provenance, no confidence, no sensitivity class, no access scope, no
  contradiction record, and no supersession** on stored memories. Nothing can be corrected
  reliably because there is no revision identity.
- Deletion does not purge derived vector/graph state as a transaction.

---

## 13. Logging leakage — SEC-21

- `genesis/core/mind_logger.py` writes JSONL logs; `genesis/safety/permissions.py` writes
  `logs/{mind_id}/actions.jsonl`. Both persist verbatim action details and reasoning.
- The execution engine prints raw stdout/stderr from untrusted code to stdout
  (`print("[CODE EXEC] ...")`), which lands in container/daemon logs.
- No redaction layer exists for prompts, memory content, tokens, or personal data.
- Logs are plaintext files with no access control beyond OS permissions and no retention
  policy. `DELETE /minds/{id}/logs` is an operator control, not a user data-rights feature.

---

## 14. Cross-user / cross-tenant data risks

- Memory scoping by `user_email` exists but is *derived from client-supplied input* on the
  WebSocket path (SEC-01).
- `test_memory_user_scoping.py` exists but cross-user isolation is not proven; the
  environment-access test currently **fails** (`assert 'alice@example.com' not in [...]`).
- The Mind object is shared in a process-wide cache (SEC-17).
- Conversation history is stored in SQLite with no per-user column enforcement verified.

---

## 15. Frontend / supply chain

- `web-playground/package.json` sets `NODE_TLS_REJECT_UNAUTHORIZED=0` in `dev` and `build`
  (both POSIX and Windows variants). This disables TLS verification for the Node process,
  weakening build-time integrity (SEC-18).
- No lockfile was found in this pass; `npm ci` reproducibility is unverified.
- No Python lockfile; all constraints are `>=`, so installs are non-deterministic (SEC-19).
- Container base image is not pinned by digest; no `USER` directive, so the container runs
  as **root**; `pip install -e .` runs at build time without hash verification.
- Declared-but-unused and mismatched dependencies (`google-genai` vs `google.generativeai`)
  indicate the dependency set is not actively audited.

---

## 16. Robot / physical-action risks

Not applicable today — **no embodiment surface exists**. Confirmed: no `Embodiment`,
`Actuator`, `ROS`, or command-publication code anywhere.

The relevant architectural fact to preserve is V3 §6.10: when embodiment arrives, the LLM
must never publish actuator commands. Given that model-generated *arbitrary code* is
currently executed with host network access, an embodiment added on this runtime would be
unsafe by construction. This is why Phase B precedes Phase L.

---

## 17. Controls that exist and must be preserved

- No `shell=True` anywhere.
- Docker socket is not mounted to the API or execution paths.
- `DISABLE_MULTIMODAL` flag in compose genuinely reduces the attack surface.
- `slowapi` rate limiting is wired (though only on two routes).
- Endpoints consistently use FastAPI auth dependencies (`get_current_active_user`,
  `require_write_access`, `require_admin`) — the HTTP surface is far better protected than
  the WebSocket surface.
- `permissions.py` deliberately **denies** actions requiring confirmation rather than
  silently allowing them — a fail-closed default that should be kept when the approval
  service is built.
- `GET /settings/api-keys` returns **masked** values only.

---

## 18. Required controls before any autonomy feature (Phase B gate)

1. `SandboxProvider` interface + one hardened container provider; **all three** execution
   paths routed through it; direct subprocess execution forbidden from API/cognition/
   scheduler processes.
2. Network **disabled by default** in the sandbox; allow-list egress only.
3. Non-root sandbox user; read-only base FS; single temporary writable dir; CPU/mem/PID/
   disk/output/time limits; no host env; no host PID/net namespace; no device mounts.
4. **Remove runtime package installation.** Replace with pre-baked tool images and a declared
   capability list.
5. `PolicyService` with deterministic evaluation and risk classification, replacing the
   keyword constitution.
6. `ApprovalService` with a persistent state machine and a real approval surface.
7. `AuditService` + append-only event journal; immutable `ActionReceipt` for allowed,
   blocked, failed, and rolled-back attempts.
8. Fix SEC-01 (authenticate before `accept()`, server-derived identity only).
9. Fix SEC-02 (reject traversal/absolute paths; canonicalise and assert containment; size
   caps; type allow-list).
10. Fix SEC-05 (explicit env allow-list for subprocesses; no blanket `os.environ`).
11. Remove `NODE_TLS_REJECT_UNAUTHORIZED=0`; add lockfiles; pin base images; add `USER`.
12. Security test suite covering the 19 cases enumerated in V3 §6.26.
