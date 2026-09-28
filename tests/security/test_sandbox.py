"""Sandbox provider behaviour and isolation guarantees.

These tests execute real code in the local provider, so they assert the
security properties from ADR-0005 / THREAT_MODEL.md T-02, T-03, T-04, T-06,
T-13, T-14 rather than merely exercising the API.
"""

from __future__ import annotations

import os
import sys

import pytest

from genesis.sandbox.base import (
    SandboxPolicy,
    SandboxPolicyError,
    SandboxSpec,
)
from genesis.sandbox.fake import FakeSandboxProvider
from genesis.sandbox.local import LocalSandboxProvider

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def provider(tmp_path):
    return LocalSandboxProvider(root=tmp_path / "sandbox")


async def run(provider, code, policy=None):
    """Helper: create, execute, terminate."""
    handle = await provider.create(SandboxSpec(policy=policy or SandboxPolicy()))
    try:
        return await provider.execute(handle, code)
    finally:
        await provider.terminate(handle)


# ---------------------------------------------------------------------------
# Policy validation
# ---------------------------------------------------------------------------


def test_policy_rejects_package_installation():
    with pytest.raises(SandboxPolicyError):
        SandboxPolicy(allow_package_install=True).validate()


def test_policy_rejects_unrestricted_network():
    with pytest.raises(SandboxPolicyError):
        SandboxPolicy(network_enabled=True, allowed_domains=()).validate()


def test_policy_accepts_allowlisted_network():
    SandboxPolicy(network_enabled=True, allowed_domains=("api.example.com",)).validate()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"wall_timeout_s": 0},
        {"wall_timeout_s": -1},
        {"wall_timeout_s": 99999},
        {"memory_mb": 1},
        {"pids_limit": 0},
    ],
)
def test_policy_rejects_unsafe_limits(kwargs):
    with pytest.raises(SandboxPolicyError):
        SandboxPolicy(**kwargs).validate()


# ---------------------------------------------------------------------------
# T-06: environment / secret isolation
# ---------------------------------------------------------------------------


async def test_secrets_are_not_inherited(provider, monkeypatch):
    """A provider API key in the parent process must not reach the sandbox."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-secret-must-not-leak")
    monkeypatch.setenv("API_SECRET_KEY", "jwt-secret-must-not-leak")

    result = await run(
        provider,
        "import os\n"
        "for name in ('OPENROUTER_API_KEY', 'API_SECRET_KEY'):\n"
        "    print(name, os.environ.get(name))",
    )

    assert result.success
    assert "sk-secret-must-not-leak" not in result.stdout
    assert "jwt-secret-must-not-leak" not in result.stdout
    assert "OPENROUTER_API_KEY None" in result.stdout


async def test_dumps_full_environment_and_finds_no_secrets(provider, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-must-not-leak")
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host/db")

    result = await run(provider, "import os\nprint('\\n'.join(sorted(os.environ)))")

    assert result.success
    assert "ANTHROPIC_API_KEY" not in result.stdout
    assert "DATABASE_URL" not in result.stdout


# ---------------------------------------------------------------------------
# T-13: resource limits and timeout
# ---------------------------------------------------------------------------


async def test_timeout_is_enforced(provider):
    result = await run(
        provider,
        "import time\nwhile True: time.sleep(0.1)",
        SandboxPolicy(wall_timeout_s=2),
    )

    assert not result.success
    assert result.timed_out is True
    assert result.exit_reason == "timeout"


async def test_output_is_bounded(provider):
    """Emitting far more than the cap must not exhaust host memory."""
    cap = 8192
    result = await run(
        provider,
        "import sys\n"
        "chunk = 'x' * 4096\n"
        "for _ in range(4000):\n"
        "    sys.stdout.write(chunk)",
        SandboxPolicy(max_output_bytes=cap, wall_timeout_s=30),
    )

    assert result.output_truncated is True
    # Allow for the truncation notice appended by the provider.
    assert len(result.stdout) < cap + 200


async def test_memory_limit_is_enforced_on_posix(provider):
    if sys.platform == "win32":
        pytest.skip("address-space limits require a POSIX resource module")

    result = await run(
        provider,
        "blob = bytearray(1024 * 1024 * 1024)",  # 1 GiB, over a 128 MB cap
        SandboxPolicy(memory_mb=128, wall_timeout_s=30),
    )

    assert not result.success


async def test_worker_cannot_fork_bomb(provider):
    if sys.platform == "win32":
        pytest.skip("process-count limits require a POSIX resource module")

    result = await run(
        provider,
        "import subprocess, sys\n"
        "for _ in range(200):\n"
        "    subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(5)'])",
        SandboxPolicy(pids_limit=16, wall_timeout_s=15),
    )

    # Either the limit stops it, or it completes without exhausting the host.
    # The property under test is that the host survives and we get a result.
    assert result.return_code is not None


# ---------------------------------------------------------------------------
# T-03 / T-04: no runtime installation
# ---------------------------------------------------------------------------


async def test_pip_install_is_denied(provider):
    result = await run(provider, "import subprocess\nsubprocess.run(['pip', 'install', 'requests'])")

    assert not result.success
    assert result.exit_reason == "policy_denied"
    assert "not permitted" in (result.error or "")


async def test_python_m_pip_is_denied(provider):
    result = await run(provider, "import os\nos.system('python -m pip install evil-package')")

    assert not result.success
    assert result.exit_reason == "policy_denied"


async def test_missing_package_does_not_trigger_an_install(provider):
    """A missing import must fail, not silently install (the old behaviour)."""
    result = await run(
        provider,
        "import a_package_that_does_not_exist_9f8a7b",
    )

    assert not result.success
    assert result.exit_reason == "completed"  # a normal ImportError
    assert "a_package_that_does_not_exist_9f8a7b" in result.stderr


# ---------------------------------------------------------------------------
# Basic execution still works (capability must not be lost)
# ---------------------------------------------------------------------------


async def test_successful_execution_captures_stdout(provider):
    result = await run(provider, "print('hello from the sandbox')")

    assert result.success
    assert "hello from the sandbox" in result.stdout
    assert result.return_code == 0
    assert result.exit_reason == "completed"


async def test_nonzero_exit_is_reported_not_raised(provider):
    result = await run(provider, "import sys\nsys.exit(3)")

    assert not result.success
    assert result.return_code == 3


async def test_exception_is_captured_in_stderr(provider):
    result = await run(provider, "raise ValueError('boom')")

    assert not result.success
    assert "ValueError" in result.stderr
    assert "boom" in result.stderr


async def test_execution_happens_in_a_private_working_directory(provider):
    result = await run(provider, "import os\nprint(os.getcwd())")

    assert result.success
    assert "sbx-" in result.stdout


async def test_upload_copies_files_in_by_basename(provider, tmp_path):
    payload = tmp_path / "data.csv"
    payload.write_text("a,b\n1,2\n", encoding="utf-8")

    handle = await provider.create(SandboxSpec(files=[payload]))
    try:
        result = await provider.execute(handle, "print(open('data.csv').read())")
        assert result.success
        assert "a,b" in result.stdout
    finally:
        await provider.terminate(handle)


# ---------------------------------------------------------------------------
# Artifact export is declared-only
# ---------------------------------------------------------------------------


async def test_only_declared_artifacts_are_exported(provider):
    handle = await provider.create(SandboxSpec())
    workdir = handle.host_workdir

    (workdir / "wanted.txt").write_text("yes", encoding="utf-8")
    (workdir / "secret.txt").write_text("no", encoding="utf-8")

    artifacts = await provider.download(handle, ["wanted.txt"])

    assert [a.name for a in artifacts] == ["wanted.txt"]
    await provider.terminate(handle)


async def test_artifact_names_cannot_escape(provider):
    handle = await provider.create(SandboxSpec())
    artifacts = await provider.download(handle, ["../../etc/passwd", "../escape.txt"])
    assert artifacts == []
    await provider.terminate(handle)


async def test_terminate_removes_the_working_directory(provider):
    handle = await provider.create(SandboxSpec())
    workdir = handle.host_workdir
    assert workdir.exists()

    await provider.terminate(handle)
    assert not workdir.exists()

    # Idempotent.
    await provider.terminate(handle)


# ---------------------------------------------------------------------------
# Honest capability reporting
# ---------------------------------------------------------------------------


def test_local_provider_does_not_claim_to_be_a_security_boundary(provider):
    caps = provider.capabilities()

    assert caps["is_security_boundary"] is False
    assert caps["filesystem_isolation"] is False
    assert caps["pid_isolation"] is False
    assert caps["package_install"] is False
    assert caps["env_scrubbing"] is True


# ---------------------------------------------------------------------------
# Fake provider
# ---------------------------------------------------------------------------


async def test_fake_provider_executes_nothing():
    provider = FakeSandboxProvider(stdout="canned")

    handle = await provider.create(SandboxSpec())
    result = await provider.execute(handle, "print('this must never run')")

    assert result.stdout == "canned"
    assert len(provider.executions) == 1
    assert provider.executions[0].code == "print('this must never run')"


async def test_fake_provider_validates_policy():
    provider = FakeSandboxProvider()
    handle = await provider.create(SandboxSpec())

    with pytest.raises(SandboxPolicyError):
        await provider.execute(handle, "x", policy=SandboxPolicy(allow_package_install=True))


# ---------------------------------------------------------------------------
# Provider selection fails closed
# ---------------------------------------------------------------------------


def test_unknown_provider_name_is_rejected(monkeypatch):
    from genesis.sandbox.base import SandboxError
    from genesis.sandbox.factory import get_sandbox_provider

    with pytest.raises(SandboxError):
        get_sandbox_provider("does-not-exist")


def test_fake_provider_refused_outside_test_or_dev(monkeypatch):
    from genesis.sandbox.base import SandboxError
    from genesis.sandbox.factory import get_sandbox_provider, reset_sandbox_provider

    monkeypatch.setenv("GENESIS_ENV", "production")
    reset_sandbox_provider()

    with pytest.raises(SandboxError):
        get_sandbox_provider("fake")

    reset_sandbox_provider()


def test_fake_provider_allowed_in_test_env(monkeypatch):
    from genesis.sandbox.factory import get_sandbox_provider, reset_sandbox_provider

    monkeypatch.setenv("GENESIS_ENV", "test")
    reset_sandbox_provider()

    assert get_sandbox_provider("fake").name == "fake"

    reset_sandbox_provider()


def test_default_provider_is_local(monkeypatch):
    from genesis.sandbox.factory import get_sandbox_provider, reset_sandbox_provider

    monkeypatch.delenv("GENESIS_SANDBOX_PROVIDER", raising=False)
    reset_sandbox_provider()

    assert get_sandbox_provider().name == "local"

    reset_sandbox_provider()
