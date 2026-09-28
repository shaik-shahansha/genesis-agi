"""Network isolation probing and honest reporting (plan item B5).

The bug this module's tests exist to prevent: the old check reported
``network_isolation: True`` whenever the ``unshare`` binary was present, without
ever attempting a connection. It proved that a namespace *could be created*, which
is not the same claim as "egress is blocked", and it was reported as `true` in
environments where the namespace could not actually run.

Three things are asserted here:

1. The probe distinguishes *verified* (host has egress **and** the namespace
   blocks it) from *unverified* (nothing to demonstrate) from *unavailable*.
2. A run that could not block egress says so in its result, rather than
   succeeding silently.
3. ``capabilities()`` never claims isolation it has not demonstrated.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from genesis.sandbox.base import ExecutionResult, SandboxPolicy, SandboxSpec
from genesis.sandbox.local import LocalSandboxProvider, NetworkIsolationProbe


@pytest.fixture
def provider(tmp_path: Path) -> LocalSandboxProvider:
    return LocalSandboxProvider(root=tmp_path / "sbx")


# =========================================================================== #
# The probe's verdicts
# =========================================================================== #


def test_probe_is_cached(provider):
    """Each verdict costs up to three subprocesses, so it is probed once."""
    first = provider.probe_network_isolation()
    second = provider.probe_network_isolation()
    assert first is second


def test_windows_reports_unavailable_with_a_reason(provider, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    probe = provider._run_network_probe()
    assert probe.verified is False
    assert "Windows" in probe.reason
    assert "container" in probe.reason.lower()


def test_missing_unshare_reports_unavailable_with_a_reason(provider, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("shutil.which", lambda name: None)
    probe = provider._run_network_probe()
    assert probe.verified is False
    assert "unshare" in probe.reason


def test_namespace_creation_failure_is_not_reported_as_isolation(provider, monkeypatch):
    """`unshare` existing is not evidence; failing to create the namespace is."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/unshare")

    class Completed:
        returncode = 1
        stdout = b""
        stderr = b"unshare: operation not permitted"

    monkeypatch.setattr("subprocess.run", lambda *a, **k: Completed())

    probe = provider._run_network_probe()
    assert probe.verified is False
    assert "could not create" in probe.reason


def test_verified_requires_a_demonstrated_block(provider, monkeypatch):
    """Both halves must hold: the host has egress, and the namespace stops it."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/unshare")

    calls: list[list[str]] = []

    class Completed:
        def __init__(self, stdout: bytes) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = b""

    def fake_run(args, **kwargs):
        calls.append(list(args))
        if "-rn" in args and "genesis-probe-ok" in " ".join(map(str, args)):
            return Completed(b"genesis-probe-ok\n")
        if "-rn" in args:
            # Inside the namespace: egress blocked.
            return Completed(b"genesis-egress=blocked\n")
        # Outside: the host can reach the network.
        return Completed(b"genesis-egress=1.1.1.1:443\n")

    monkeypatch.setattr("subprocess.run", fake_run)

    probe = provider._run_network_probe()
    assert probe.verified is True
    assert probe.host_has_egress is True
    assert probe.namespace_blocks_egress is True
    assert len(calls) == 3, "expected namespace check, host egress check, in-namespace check"


def test_a_host_without_egress_is_reported_as_unverified_not_isolated(provider, monkeypatch):
    """Otherwise a network-less host would look isolated for the wrong reason."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/unshare")

    class Completed:
        def __init__(self, stdout: bytes) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = b""

    def fake_run(args, **kwargs):
        if "genesis-probe-ok" in " ".join(map(str, args)):
            return Completed(b"genesis-probe-ok\n")
        return Completed(b"genesis-egress=blocked\n")

    monkeypatch.setattr("subprocess.run", fake_run)

    probe = provider._run_network_probe()
    assert probe.verified is False
    assert probe.host_has_egress is False
    assert "nothing to demonstrate" in probe.reason


def test_a_namespace_that_does_not_block_is_reported_honestly(provider, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/unshare")

    class Completed:
        def __init__(self, stdout: bytes) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = b""

    def fake_run(args, **kwargs):
        if "genesis-probe-ok" in " ".join(map(str, args)):
            return Completed(b"genesis-probe-ok\n")
        # Both inside and outside: reachable, so isolation is not working.
        return Completed(b"genesis-egress=1.1.1.1:443\n")

    monkeypatch.setattr("subprocess.run", fake_run)

    probe = provider._run_network_probe()
    assert probe.verified is False
    assert probe.namespace_blocks_egress is False
    assert "NOT isolated" in probe.reason


def test_probe_never_raises(provider, monkeypatch):
    """Detection must degrade to 'not verified', never break execution."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/unshare")

    def boom(*args, **kwargs):
        raise RuntimeError("probe exploded")

    monkeypatch.setattr("subprocess.run", boom)
    probe = provider._run_network_probe()
    assert probe.verified is False
    assert "could not be verified" in probe.reason


def test_probe_serialises_for_receipts():
    probe = NetworkIsolationProbe(
        verified=True, reason="ok", host_has_egress=True, namespace_blocks_egress=True
    )
    payload = probe.to_dict()
    assert payload == {
        "verified": True,
        "reason": "ok",
        "host_has_egress": True,
        "namespace_blocks_egress": True,
    }


# =========================================================================== #
# capabilities() must not claim what it has not demonstrated
# =========================================================================== #


def test_capabilities_never_claims_unverified_isolation(provider, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    provider._network_probe = None
    caps = provider.capabilities()
    assert caps["network_isolation"] is False
    assert caps["network_probe"]["verified"] is False
    assert caps["recommendation"]


def test_capabilities_reports_verified_isolation(provider, monkeypatch):
    provider._network_probe = NetworkIsolationProbe(
        verified=True, reason="verified", host_has_egress=True, namespace_blocks_egress=True
    )
    caps = provider.capabilities()
    assert caps["network_isolation"] is True
    assert caps["recommendation"] is None


def test_capabilities_never_claims_to_be_a_security_boundary(provider):
    """The local provider is not one, and must keep saying so."""
    caps = provider.capabilities()
    assert caps["is_security_boundary"] is False
    assert caps["filesystem_isolation"] is False
    assert caps["pid_isolation"] is False


# =========================================================================== #
# Per-execution reporting
# =========================================================================== #


def _execute(provider, code, policy=None):
    handle = asyncio.run(provider.create(SandboxSpec(policy=policy or SandboxPolicy(wall_timeout_s=30))))
    try:
        return asyncio.run(provider.execute(handle, code, policy=policy))
    finally:
        asyncio.run(provider.terminate(handle))


def _script_that_may_report_egress() -> str:
    return (
        "import socket\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 443), timeout=2).close()\n"
        "    print('EGRESS=reachable')\n"
        "except OSError:\n"
        "    print('EGRESS=blocked')\n"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="resource limits are POSIX-only")
def test_execution_records_that_egress_was_not_isolated(provider, monkeypatch):
    """When the host cannot block egress, the result must say so."""
    monkeypatch.setattr(sys, "platform", "win32")
    provider._network_probe = None

    result = _execute(provider, "print('done')")
    assert result.success
    assert result.network_isolated is False
    assert any("NOT blocked" in warning for warning in result.warnings)


@pytest.mark.skipif(sys.platform == "win32", reason="resource limits are POSIX-only")
def test_execution_records_isolation_when_the_probe_verified_it(provider, monkeypatch):
    provider._network_probe = NetworkIsolationProbe(
        verified=True, reason="verified", host_has_egress=True, namespace_blocks_egress=True
    )
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/unshare")

    result = _execute(provider, "print('done')")
    assert result.network_isolated is True
    assert not [w for w in result.warnings if "NOT blocked" in w]


def test_policy_enabling_network_warns_that_destinations_are_not_restricted(provider):
    """The local provider cannot enforce allowed_domains, so it must say so."""
    policy = SandboxPolicy(
        wall_timeout_s=30, network_enabled=True, allowed_domains=("api.example.com",)
    )
    result = _execute(provider, "print('done')", policy=policy)
    assert result.network_isolated is False
    assert any("cannot restrict to allowed domains" in warning for warning in result.warnings)


def test_execution_result_serialises_the_new_fields():
    result = ExecutionResult(
        success=True,
        network_isolated=False,
        warnings=["Egress was NOT blocked for this run: reason"],
    )
    payload = result.to_dict()
    assert payload["network_isolated"] is False
    assert payload["warnings"] == ["Egress was NOT blocked for this run: reason"]


# =========================================================================== #
# The facts reach the tool outcome, and therefore the receipt
# =========================================================================== #


def test_tool_outcome_carries_the_isolation_facts():
    from genesis.sandbox.tool_runner import ToolRunOutcome

    outcome = ToolRunOutcome(
        success=True,
        result={"ok": True},
        provider="local",
        network_isolated=False,
        warnings=["Egress was NOT blocked for this run"],
    )
    payload = outcome.to_dict()
    assert payload["network_isolated"] is False
    assert payload["warnings"] == ["Egress was NOT blocked for this run"]
    assert payload["provider"] == "local"


def test_tool_outcome_defaults_do_not_imply_isolation():
    """`None` means 'the provider does not isolate', which is not `True`."""
    from genesis.sandbox.tool_runner import ToolRunOutcome

    outcome = ToolRunOutcome(success=True)
    assert outcome.network_isolated is None
    assert outcome.warnings == []


def test_tool_runner_propagates_isolation_into_the_outcome(tmp_path: Path, monkeypatch):
    """A tool run through the sandbox must report the same facts."""
    from genesis.sandbox import tool_runner

    provider = LocalSandboxProvider(root=tmp_path / "toolsbx")
    monkeypatch.setattr(sys, "platform", "win32")
    provider._network_probe = None

    outcome = tool_runner.execute_tool_code_sync(
        "def run(input_data):\n    return {'echo': input_data}\n",
        {"a": 1},
        provider=provider,
    )
    assert outcome.network_isolated is not None
    assert isinstance(outcome.warnings, list)
