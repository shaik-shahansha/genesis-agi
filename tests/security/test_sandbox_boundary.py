"""Architectural guards for the sandbox boundary (ADR-0005).

These tests assert a *structural* property that is easy to regress and hard to
notice: that untrusted execution happens in exactly one place.

They parse the source with ``ast`` rather than scanning text, so a docstring that
*describes* the removed behaviour (which is useful documentation) is never
mistaken for the behaviour itself. Only executable constructs are inspected.

They are cheap - no execution - so they can run in every CI pass.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GENESIS = REPO_ROOT / "genesis"
SANDBOX = GENESIS / "sandbox"

#: The three modules that previously each had their own unsandboxed subprocess
#: implementation. They must now delegate to the sandbox.
FORMER_EXECUTION_PATHS = [
    GENESIS / "core" / "code_executor.py",
    GENESIS / "core" / "tools.py",
    GENESIS / "plugins" / "tools.py",
]

#: subprocess/os entry points that spawn a process.
SPAWN_ATTRS = {
    "run",
    "Popen",
    "call",
    "check_call",
    "check_output",
    "create_subprocess_exec",
    "create_subprocess_shell",
}
SPAWN_MODULES = {"subprocess", "os"}


def _parse(path: Path) -> ast.Module:
    # utf-8-sig strips a leading BOM. Python's own import machinery tolerates
    # BOMs, but ast.parse rejects U+FEFF as a non-printable character, and some
    # files in this repository carry one.
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def _iter_calls(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node


def _attribute_chain(node: ast.AST) -> tuple[str, str] | None:
    """Return (module, attr) for ``module.attr(...)`` style calls."""
    if isinstance(node, ast.Attribute):
        value = node.value
        if isinstance(value, ast.Name):
            return value.id, node.attr
        # ``asyncio.subprocess.create_subprocess_exec``
        if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name):
            return f"{value.value.id}.{value.attr}", node.attr
    return None


def _spawn_calls(tree: ast.AST):
    """Yield (lineno, description) for process-spawning calls."""
    for call in _iter_calls(tree):
        chain = _attribute_chain(call.func)
        if not chain:
            continue
        module, attr = chain

        if module in SPAWN_MODULES and attr in SPAWN_ATTRS:
            yield call.lineno, f"{module}.{attr}"

        # asyncio.subprocess.*
        if module.endswith("subprocess") and attr.startswith("create_subprocess"):
            yield call.lineno, f"{module}.{attr}"


def _constant_strings(node: ast.AST) -> list[str]:
    """All string constants anywhere beneath ``node``."""
    return [
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    ]


def _preexec_keywords(tree: ast.AST):
    """Yield line numbers of calls passing ``preexec_fn=``."""
    for call in _iter_calls(tree):
        for keyword in call.keywords:
            if keyword.arg == "preexec_fn":
                yield call.lineno


# ---------------------------------------------------------------------------
# The former execution paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", FORMER_EXECUTION_PATHS, ids=lambda p: p.name)
def test_execution_paths_do_not_spawn_processes(path):
    """Untrusted execution must go through SandboxProvider (ADR-0005)."""
    offenders = [f"{path.name}:{line}: {desc}" for line, desc in _spawn_calls(_parse(path))]

    assert not offenders, (
        "Untrusted execution must go through SandboxProvider (ADR-0005). "
        "Direct process spawning found:\n" + "\n".join(offenders)
    )


@pytest.mark.parametrize("path", FORMER_EXECUTION_PATHS, ids=lambda p: p.name)
def test_execution_paths_do_not_eval_untrusted_code(path):
    """No in-process exec/eval of untrusted code."""
    offenders = []
    for call in _iter_calls(_parse(path)):
        if isinstance(call.func, ast.Name) and call.func.id in {"exec", "eval"}:
            offenders.append(f"{path.name}:{call.lineno}: {call.func.id}()")

    assert not offenders, (
        "In-process eval/exec of untrusted code found:\n" + "\n".join(offenders)
    )


@pytest.mark.parametrize("path", FORMER_EXECUTION_PATHS, ids=lambda p: p.name)
def test_execution_paths_do_not_pass_shell_true(path):
    offenders = []
    for call in _iter_calls(_parse(path)):
        for keyword in call.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant):
                if keyword.value.value is True:
                    offenders.append(f"{path.name}:{call.lineno}: shell=True")

    assert not offenders, "shell=True found:\n" + "\n".join(offenders)


# ---------------------------------------------------------------------------
# Repository-wide invariants
# ---------------------------------------------------------------------------


def test_preexec_fn_is_not_used_anywhere():
    """preexec_fn is documented as unsafe with threads; a runner script is used."""
    offenders = [
        f"{path.relative_to(REPO_ROOT)}:{line}"
        for path in GENESIS.rglob("*.py")
        for line in _preexec_keywords(_parse(path))
    ]

    assert not offenders, "preexec_fn found (unsafe with threads):\n" + "\n".join(offenders)


def test_process_spawning_stays_inside_the_sandbox_package():
    """``create_subprocess_*`` must only appear in genesis/sandbox/."""
    offenders = []
    for path in GENESIS.rglob("*.py"):
        if SANDBOX in path.parents:
            continue
        for line, desc in _spawn_calls(_parse(path)):
            if "create_subprocess" in desc:
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{line}: {desc}")

    assert not offenders, (
        "Process spawning outside genesis/sandbox/ found:\n" + "\n".join(offenders)
    )


def test_runtime_package_installation_is_gone():
    """SEC-04: nothing may install packages from model output at runtime."""
    offenders = []

    for path in GENESIS.rglob("*.py"):
        if SANDBOX in path.parents:
            # The sandbox's own detector necessarily names the commands it blocks.
            continue
        for call in _iter_calls(_parse(path)):
            chain = _attribute_chain(call.func)
            if not chain:
                continue
            module, attr = chain
            if module not in SPAWN_MODULES or attr not in SPAWN_ATTRS:
                continue

            strings = [s.lower() for s in _constant_strings(call)]
            touches_pip = any(s in {"pip", "pip3"} for s in strings)
            touches_install = "install" in strings
            if touches_pip and touches_install:
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{call.lineno}")

    assert not offenders, (
        "Runtime package installation found (SEC-04):\n" + "\n".join(offenders)
    )


def test_import_allowlist_claim_is_not_advertised():
    """SEC-06: name-based import restriction must not be claimed or emitted."""
    path = GENESIS / "plugins" / "tools.py"
    text = path.read_text(encoding="utf-8-sig")

    # The attribute may be retained for configuration compatibility, but it must
    # never be emitted into generated code nor described as a control.
    assert "ALLOWED_IMPORTS = " not in text, (
        "plugins/tools.py emits an ALLOWED_IMPORTS constant into generated code "
        "but never enforced it (SEC-06)."
    )
    assert "Allowed imports:" not in text, (
        "plugins/tools.py still advertises an import allow-list as a control."
    )


def test_sandbox_defaults_are_safe():
    """The abstraction itself must exist with secure defaults."""
    from genesis.sandbox import SandboxPolicy, SandboxSpec

    policy = SandboxPolicy()
    assert policy.network_enabled is False
    assert policy.allowed_domains == ()
    assert policy.allow_package_install is False
    assert policy.read_only_root is True
    assert policy.no_new_privileges is True
    assert policy.drop_all_capabilities is True
    assert "OPENROUTER_API_KEY" not in policy.env_allowlist
    assert "API_SECRET_KEY" not in policy.env_allowlist

    assert SandboxSpec().policy.network_enabled is False
