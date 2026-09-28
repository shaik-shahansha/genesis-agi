# TEST_BASELINE.md

> Recorded before any modification to existing behaviour, as required by V3 §7.
> Commands were executed and outputs captured; nothing in this file is predicted.

---

## 1. Test commands

```powershell
# Python interpreter used (system, discovered by VS Code Python extension)
C:/Users/shaiks3423/AppData/Local/Python/pythoncore-3.12-64/python.exe

# Import check
python -c "import genesis; print('IMPORT OK')"

# Full suite
python -m pytest -q --no-header -p no:cacheprovider

# Suite with one-line failure reasons
python -m pytest -q --no-header -p no:cacheprovider --tb=line

# Lint
python -m ruff check genesis --statistics

# Types
python -m mypy genesis --ignore-missing-imports                      # fails to start
python -m mypy genesis --ignore-missing-imports --python-version 3.12
```

---

## 2. Environmental prerequisites discovered

The suite **could not run at all** on a clean interpreter. `tests/conftest.py:10` imports
`genesis.config`, which transitively imports `genesis.core.mind`, which pulls the whole
runtime. The following had to be installed before the suite would collect:

`pydantic-settings`, `python-multipart`, `python-jose[cryptography]`, `passlib[bcrypt]`,
`bcrypt`, `aiofiles`, `slowapi`, `psutil`, `pytest-asyncio`, `schedule`, `aioimaplib`,
`aiosmtplib`, `chromadb`, `openai`, `anthropic`, `groq`, `google-genai`, `firebase-admin`.

Already present in the environment: `alembic`, `fastapi`, `httpx`, `numpy`, `pillow`,
`pydantic`, `pytest`, `python-dotenv`, `rich`, `SQLAlchemy`, `typer`, `websockets`.

**Not installed** (declared in `pyproject.toml`, and never exercised): `browser-use`,
`playwright`, `opencv-python`, `fer`, `deepface`, `ddgs`.

**Baseline requirement:** the test suite is not runnable from a clean clone without an
install step, and no lockfile guarantees which versions that step resolves to.

---

## 3. Passing / failing counts (executed)

| Run | Passed | Failed | Errors | Warnings | Duration |
|---|---|---|---|---|---|
| Run 1 | **46** | **11** | 1 | 36 | 44.59s |
| Run 2 | **45** | **12** | 1 | 34 | 20.64s |

**The two consecutive runs disagree.** Run 2 additionally failed
`tests/storage/test_memory.py::TestMemoryManager::test_add_memory`. This is evidence of
**shared, non-isolated state** — most likely the persistent ChromaDB directory and/or the
`~/.genesis` data directory being reused between runs. Tests are order- and state-dependent.

---

## 4. Failing tests (with observed cause)

| Test | Observed assertion / error |
|---|---|
| `tests/api/test_routes.py::TestMindEndpoints::test_create_mind_with_auth` | `assert 400 in [200, 500]` — endpoint returned 400 |
| `tests/api/test_routes.py::TestSystemEndpoints::test_system_status` | `assert 401 == 200` — auth required but test unauthenticated (or vice versa) |
| `tests/api/test_routes.py::TestSystemEndpoints::test_get_providers` | `assert 401 == 200` |
| `tests/core/test_tools.py::TestToolManager::test_use_tool_execution` | `AssertionError: assert False` at line 164 |
| `tests/storage/test_memory.py::test_add_memory` | `assert 36 == 1` (run 1) / failed intermittently (run 2 variant) |
| `tests/storage/test_memory.py::test_consolidate_memories` | `assert 68 == 3` at line 166 |
| `tests/storage/test_memory.py::test_memory_serialization` | `KeyError: 'memories'` at line 179 |
| `tests/test_admin.py::test_is_global_admin_affects_user_role` | `RuntimeError: There is no current event loop in thread 'MainThread'` |
| `tests/test_emotional_intelligence.py::test_emotional_intelligence` | `pydantic_core.ValidationError` raised from `genesis/core/mind.py:113` for model `Intelligence` |
| `tests/test_emotional_intelligence.py::test_performance` | same `ValidationError` at `mind.py:113` |
| `tests/test_mind_gens_coercion.py::test_list_minds_coerces_float_gens` | `assert 0 == 1` |
| `tests/test_users_and_env_access.py::test_environment_access_controls` | `assert 'alice@example.com' not in ['alice@example.com']` |

**Error (collection):**

| Test | Cause |
|---|---|
| `tests/api/test_conversation_api.py::test_conversation_messages_endpoint` | Import/collection failure at `test_conversation_api.py:7`; related `RuntimeError: There is no current event loop in thread 'MainThread'` from `asyncio/events.py:702` |

### Classification of the failures

| Class | Tests | Meaning |
|---|---|---|
| Environment/interpreter-specific | `test_admin`, `test_conversation_api`, `test_emotional_intelligence` ×2 | Fail on Python 3.12 because code calls `asyncio.get_event_loop()` / constructs `Intelligence` without required keys. Not caused by my changes; were failing before |
| Test isolation | `test_memory.py` ×3, `test_add_memory` variance | Persistent ChromaDB/`~/.genesis` state leaks between tests |
| Likely real product defects | `test_environment_access_controls`, `test_mind_gens_coercion`, `test_create_mind_with_auth` | Access-control and coercion behaviour appears genuinely wrong |
| Platform | `test_use_tool_execution` | Subprocess tool execution fails locally (see below) |

### Platform-specific defect worth recording

`genesis/core/tools.py:364` and `genesis/plugins/tools.py:244` invoke the literal command
`python3`. On Windows there is no `python3` executable, so tool execution cannot work on
Windows. `test_use_tool_execution` fails for this reason. `genesis/core/code_executor.py`
uses `"python"` instead — an inconsistency across the three execution paths.

---

## 5. Coverage

`pytest-cov` is declared but coverage was not measured in this baseline. Estimated coverage
is low: only 16 test modules exist for 155 source files, and the largest subsystems
(`core/code_executor.py`, `core/autonomous_orchestrator.py`, `core/living_mind.py`,
`storage/smart_memory.py`, `api/routes.py`) have either no tests or trivial ones.

---

## 6. Missing test categories (all absent)

- `tests/security/` — none. No sandbox escape, path traversal, SSRF, secret leakage,
  network isolation, fork bomb, resource exhaustion, symlink, archive, or command-injection
  tests exist, despite three separate code-execution paths.
- `tests/integration/` — none. No test exercises reason → generate → execute → receipt.
- `tests/end-to-end/` — none. No Playwright or browser tests.
- `tests/memory-evals/`, `tests/autonomy-evals/`, `tests/continuity-evals/` — none.
- Migration tests — none. No test runs Alembic up/down against a clean database.
- Auth/authz matrix tests — none covering the WebSocket path or cross-user access.
- Concurrency tests — none, despite a cached-Mind dictionary shared across requests.

---

## 7. Lint status (executed)

```
python -m ruff check genesis --statistics
Found 3473 errors.
[*] 2302 fixable with the `--fix` option
```

Top categories (count):

| Count | Rule | Meaning |
|---|---|---|
| 883 | `UP006` | non-PEP585 annotation (`List[x]` → `list[x]`) |
| 827 | `UP045` | non-PEP604 optional (`Optional[x]` → `x \| None`) |
| 387 | `BLE001` | blind `except Exception` |
| 230 | `DTZ005` | `datetime.now()` without tzinfo |
| 192 | `UP035` | deprecated import |
| 187 | `I001` | unsorted imports |
| 152 | `F541` | f-string without placeholders |
| 122 | `F401` | unused import |
| **22** | **`F821`** | **undefined name** — includes `Mind` used in annotations without `TYPE_CHECKING` import (`concern_analyzer.py:66`, `intelligent_timing.py:63`, `scenario_handlers.py:45`, `spontaneous_conversation.py:50`) |
| 20 | `DTZ003` | `datetime.utcnow()` |
| 17 | `E722` | bare `except:` |
| 6 | `PLW1510` | `subprocess.run` without `check=` (includes all three `code_executor.py` calls) |
| 1 | `F823` | undefined local |
| 1 | `LOG015` | root logger call |

No lint gate is configured (no CI workflow, no pre-commit hook), so this count is unbounded
rather than enforced.

---

## 8. Type-check status (executed)

```
python -m mypy genesis --ignore-missing-imports
→ numpy/__init__.pyi:737: error: Type statement is only supported in Python 3.12 and greater
→ Found 1 error in 1 file (errors prevented further checking)
```

**mypy is non-functional with the repository's own configuration.** `pyproject.toml` sets
`python_version = "3.11"`, but the installed `numpy` 2.5 stubs require 3.12 syntax, so mypy
aborts before analysing any project code.

Forcing `--python-version 3.12`:

```
Found 1187 errors in 124 files (checked 155 source files)
```

So **124 of 155 files (80%) fail strict type checking**. `pyproject.toml` declares
`disallow_untyped_defs = true`, which is not being enforced anywhere.

---

## 9. Baseline summary for the quality gate

| Gate | Baseline | Gate target for Phase B |
|---|---|---|
| Import | OK (after manual dep install) | OK, no manual step |
| Test suite | 46 pass / 11 fail / 1 error, **plus run-to-run variance** | No new failures; document each pre-existing one |
| Test isolation | Broken (state leaks across runs) | Deterministic per-test isolation |
| Security tests | 0 exist | ≥ 20 covering the execution vertical slice |
| Ruff | 3473 errors, unenforced | Non-regression ratchet; no new errors |
| Mypy | Broken config; 1187 errors when forced | Config fixed; execution-slice modules typed |
| Migrations | Never tested | Up/down verified in CI |

**Known environmental requirements:** Windows dev machine, system Python 3.12.10, no Docker
verification performed yet, no Redis running, no API keys available. All sandbox work must
therefore be verifiable **without** paid API keys and **without** a running Docker daemon
where possible (a fake/in-process sandbox provider keeps tests hermetic).
