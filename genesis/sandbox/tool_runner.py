"""Shared helper for running tool code inside the sandbox.

Both `genesis/core/tools.py` and `genesis/plugins/tools.py` execute stored tool
code. Previously each had its own subprocess implementation (and the plugin
version advertised an import allow-list that was never enforced: SEC-06).

They now share this runner, which:

* builds a single, explicit wrapper contract (``run``/``execute``/``main``);
* passes input through a file, not ``argv``, so nothing has to be quoted;
* executes only through ``SandboxProvider``;
* returns a typed outcome instead of a bare value, so callers can report why
  something failed.

``_ALLOWED_IMPORTS`` has been deleted. Restricting imports by *name* is not a
security control - ``importlib``, ``__import__`` and attribute walking defeat it.
Real restriction is the sandbox's job: scrubbed environment, no installs, no
isolation escape, bounded resources.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from genesis.sandbox.base import SandboxError, SandboxPolicy, SandboxSpec
from genesis.sandbox.factory import get_sandbox_provider

#: Entry-point function names a tool may define, in precedence order.
ENTRY_POINT_NAMES = ("run", "execute", "main")

_WRAPPER_TEMPLATE = '''\
"""Genesis tool runner - generated, do not edit."""
import json
import sys
import traceback

_INPUT_PATH = __INPUT_PATH__
_ENTRY_NAMES = __ENTRY_NAMES__


def _load_input():
    try:
        with open(_INPUT_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _emit(payload):
    sys.stdout.write("__RESULT__:" + json.dumps(payload, default=str))


try:
    # --- tool code ---------------------------------------------------------
__TOOL_CODE__

    # --- invocation --------------------------------------------------------
    _input = _load_input()
    _entry = None
    for _name in _ENTRY_NAMES:
        _candidate = locals().get(_name)
        if callable(_candidate):
            _entry = _candidate
            break

    if _entry is None:
        raise RuntimeError(
            "Tool defines no entry point. Expected one of: " + ", ".join(_ENTRY_NAMES)
        )

    # Tools in the wild use two conventions, and the previous implementations
    # disagreed about which to use:
    #   execute(input_data)   - payload taken positionally as one argument
    #   run(a=..., b=...)     - payload unpacked as keyword arguments
    # Decide from the signature rather than catching TypeError, so a TypeError
    # raised *inside* the tool is not mistaken for a calling-convention mismatch.
    _use_keywords = False
    if isinstance(_input, dict):
        try:
            import inspect

            _sig = inspect.signature(_entry)
            _params = list(_sig.parameters.values())
            _accepts_var_kwargs = any(p.kind == p.VAR_KEYWORD for p in _params)
            _named = set(
                p.name
                for p in _params
                if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
            )
            _use_keywords = _accepts_var_kwargs or set(_input.keys()) <= _named
        except (TypeError, ValueError):
            _use_keywords = False

    if _use_keywords:
        _result = _entry(**_input)
    else:
        _result = _entry(_input)

    _emit({"success": True, "result": _result})

except Exception as _exc:  # noqa: BLE001 - reported to the caller as data
    _emit(
        {
            "success": False,
            "error": str(_exc),
            "error_type": type(_exc).__name__,
            "traceback": traceback.format_exc()[-2000:],
        }
    )
    sys.exit(1)
'''


@dataclass
class ToolRunOutcome:
    """Outcome of a tool execution."""

    success: bool
    result: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    stderr: str = ""
    exit_reason: str = "completed"
    provider: str = "unknown"


def run_coroutine_sync(coro):
    """Run a coroutine from synchronous code.

    Tools are executed through the async sandbox provider, but
    ``ToolManager.use_tool`` is synchronous and is part of the public surface, so
    the sync signature is preserved rather than changed.

    If no event loop is running, ``asyncio.run`` is used directly. If one *is*
    running (the normal case inside the API or a daemon), the coroutine is
    executed in a dedicated worker thread with its own loop: an event loop cannot
    be nested, and blocking here is acceptable because tool execution is bounded
    by the sandbox policy timeout.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def execute_tool_code(
    tool_code: str,
    input_data: Any,
    *,
    timeout_s: int = 10,
    provider=None,
) -> ToolRunOutcome:
    """Execute stored tool code in the sandbox and return a typed outcome.

    Args:
        tool_code: The tool's Python source.
        input_data: Passed to the tool's entry point.
        timeout_s: Wall-clock limit; also used for the CPU limit.
        provider: Override the configured sandbox provider (tests).
    """
    if not tool_code or not tool_code.strip():
        return ToolRunOutcome(success=False, error="Tool has no code to execute")

    sandbox = provider or get_sandbox_provider()
    provider_name = getattr(sandbox, "name", "unknown")

    bounded = max(1, min(int(timeout_s), 300))
    policy = SandboxPolicy(
        wall_timeout_s=bounded,
        cpu_seconds=bounded,
        memory_mb=512,
    )

    handle = None
    try:
        handle = await sandbox.create(
            SandboxSpec(policy=policy, label="tool_execution")
        )

        # Input travels as a file so no quoting or escaping is involved.
        input_path = Path("_tool_input.json")
        workdir = getattr(handle, "host_workdir", None)
        if workdir is not None:
            (Path(workdir) / input_path.name).write_text(
                json.dumps(input_data, default=str), encoding="utf-8"
            )

        wrapper = (
            _WRAPPER_TEMPLATE
            .replace("__INPUT_PATH__", repr(input_path.name))
            .replace("__ENTRY_NAMES__", repr(list(ENTRY_POINT_NAMES)))
            .replace("__TOOL_CODE__", _indent(tool_code, 4))
        )

        execution = await sandbox.execute(handle, wrapper, policy=policy)

        if execution.exit_reason == "policy_denied":
            return ToolRunOutcome(
                success=False,
                error=execution.error or "Execution denied by sandbox policy",
                stderr=execution.stderr,
                exit_reason=execution.exit_reason,
                provider=provider_name,
            )

        if execution.timed_out:
            return ToolRunOutcome(
                success=False,
                error=f"Tool execution exceeded {bounded}s",
                stderr=execution.stderr,
                exit_reason="timeout",
                provider=provider_name,
            )

        payload = _parse_envelope(execution.stdout)
        if payload is None:
            return ToolRunOutcome(
                success=False,
                error=(
                    "Tool produced no parsable result. "
                    f"stderr: {execution.stderr[-500:] or '(empty)'}"
                ),
                stderr=execution.stderr,
                exit_reason=execution.exit_reason,
                provider=provider_name,
            )

        if payload.get("success"):
            return ToolRunOutcome(
                success=True,
                result=payload.get("result"),
                stderr=execution.stderr,
                provider=provider_name,
            )

        return ToolRunOutcome(
            success=False,
            error=payload.get("error"),
            error_type=payload.get("error_type"),
            stderr=execution.stderr or payload.get("traceback", ""),
            exit_reason=execution.exit_reason,
            provider=provider_name,
        )

    except SandboxError as exc:
        return ToolRunOutcome(
            success=False, error=f"Sandbox error: {exc}", provider=provider_name
        )
    except Exception as exc:  # noqa: BLE001 - reported, never swallowed
        return ToolRunOutcome(
            success=False,
            error=f"Tool execution error: {exc}",
            error_type=type(exc).__name__,
            provider=provider_name,
        )
    finally:
        if handle is not None:
            try:
                await sandbox.terminate(handle)
            except Exception:  # noqa: BLE001 - cleanup is best-effort
                pass


def execute_tool_code_sync(
    tool_code: str,
    input_data: Any,
    *,
    timeout_s: int = 10,
    provider=None,
) -> ToolRunOutcome:
    """Synchronous wrapper around :func:`execute_tool_code`."""
    return run_coroutine_sync(
        execute_tool_code(
            tool_code, input_data, timeout_s=timeout_s, provider=provider
        )
    )


def _indent(code: str, spaces: int) -> str:
    """Indent every non-empty line, so the tool code sits inside the try block."""
    prefix = " " * spaces
    return "\n".join(
        (prefix + line) if line.strip() else line for line in code.splitlines()
    )


def _parse_envelope(stdout: str) -> Optional[dict]:
    """Extract the ``__RESULT__:`` JSON envelope from stdout."""
    marker = "__RESULT__:"
    if marker not in stdout:
        return None
    payload = stdout.split(marker, 1)[1].strip()
    try:
        parsed = json.loads(payload)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


__all__ = [
    "ENTRY_POINT_NAMES",
    "ToolRunOutcome",
    "execute_tool_code",
    "execute_tool_code_sync",
    "run_coroutine_sync",
]
