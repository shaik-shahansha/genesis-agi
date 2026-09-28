"""Tests for the Phase B hardening unit: B9, B11, B12.

Three unrelated-looking changes, one shared shape: the API tier was holding
authority or leaking data it had no business holding, and every fix is verified
by asserting the *old* behaviour is impossible rather than that the new one
exists.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

# =========================================================================== #
# B9 — MCP servers must not inherit the host environment (SEC-05)
# =========================================================================== #


@pytest.fixture
def mcp_module():
    import genesis.integrations.mcp_integration as module

    return module


@pytest.fixture
def host_secrets(monkeypatch):
    """Put secret-shaped variables in the environment, as a real deployment has."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-live-do-not-leak")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-do-not-leak")
    monkeypatch.setenv("API_SECRET_KEY", "jwt-signing-key-do-not-leak")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@host/db")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_do-not-leak")
    # Deliberately named without any secret-ish substring, or it would be
    # redacted by the very check under test and the test would pass vacuously.
    monkeypatch.setenv("MCP_PASSTHROUGH_MARKER", "fine-to-pass")


def test_mcp_environment_does_not_contain_host_secrets(mcp_module, host_secrets):
    config = mcp_module.MCPServerConfig(name="filesystem", command="npx", args=["-y", "srv"])
    env = mcp_module.build_mcp_environment(config)

    for name in (
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "API_SECRET_KEY",
        "DATABASE_URL",
        "GITHUB_TOKEN",
    ):
        assert name not in env, f"{name} leaked into the MCP server environment"


def test_mcp_environment_keeps_what_a_process_needs(mcp_module, host_secrets):
    config = mcp_module.MCPServerConfig(name="filesystem", command="npx")
    env = mcp_module.build_mcp_environment(config)
    # Without PATH an MCP server cannot even be spawned.
    assert "PATH" in env


def test_mcp_environment_honours_deliberate_per_server_values(mcp_module, host_secrets):
    """The supported way to give a server a credential: pass it explicitly."""
    config = mcp_module.MCPServerConfig(
        name="private",
        command="npx",
        env={"SERVICE_CREDENTIAL": "explicitly-provided"},
    )
    env = mcp_module.build_mcp_environment(config)
    assert env["SERVICE_CREDENTIAL"] == "explicitly-provided"


def test_mcp_environment_refuses_secrets_even_when_requested(mcp_module, host_secrets, caplog):
    """A server listing a secret in pass_through_env must still not receive it."""
    config = mcp_module.MCPServerConfig(
        name="greedy",
        command="npx",
        pass_through_env=["OPENROUTER_API_KEY", "DATABASE_URL", "MCP_PASSTHROUGH_MARKER"],
    )
    with caplog.at_level("WARNING"):
        env = mcp_module.build_mcp_environment(config)

    assert "OPENROUTER_API_KEY" not in env
    assert "DATABASE_URL" not in env
    # A non-secret explicitly requested variable is still allowed.
    assert env.get("MCP_PASSTHROUGH_MARKER") == "fine-to-pass"
    assert "refusing" in caplog.text.lower()


@pytest.mark.parametrize(
    "name",
    [
        "OPENROUTER_API_KEY",
        "openai_api_key",
        "ANTHROPIC-API-KEY",
        "GITHUB_TOKEN",
        "MY_SECRET",
        "DB_PASSWORD",
        "USER_CREDENTIAL",
        "AWS_PRIVATE_KEY",
        "SIGNING_KEY",
        "DATABASE_URL",
        "STRIPE_SECRET",
        "SESSION_COOKIE",
    ],
)
def test_never_passed_detects_secret_shaped_names(mcp_module, name):
    assert mcp_module.is_never_passed(name)


@pytest.mark.parametrize(
    "name",
    ["PATH", "HOME", "LANG", "NODE_OPTIONS", "TZ", "TMPDIR", "MCP_PASSTHROUGH_MARKER"],
)
def test_never_passed_allows_process_basics(mcp_module, name):
    assert not mcp_module.is_never_passed(name)


def test_pass_through_env_defaults_to_empty(mcp_module):
    """Opting in must be deliberate: the default forwards nothing extra."""
    config = mcp_module.MCPServerConfig(name="x", command="y")
    assert config.pass_through_env == []


def test_mcp_client_uses_the_builder(mcp_module):
    """The client must not reach for os.environ itself any more.

    Checked on the AST rather than the source text: a substring match on source
    is satisfied (or broken) by *comments*, and the fix's own comment explains
    what the old code did, so it mentions `os.environ`. Prose is not code.
    """
    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(mcp_module.MCPClient.connect)))

    reads_environ = any(
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
        for node in ast.walk(tree)
    )
    calls_builder = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_mcp_environment"
        for node in ast.walk(tree)
    )

    assert calls_builder, "connect() must build the child environment explicitly"
    assert not reads_environ, "connect() must not read os.environ"


def test_os_is_imported_at_module_top(mcp_module):
    """`import os` used to sit at the bottom of the file, below its first use."""
    source = Path(mcp_module.__file__).read_text(encoding="utf-8")
    first_use = source.index("os.environ")
    last_import = source.index("import os")
    assert last_import < first_use, "os must be imported before it is used"


# =========================================================================== #
# B11 — the API tier must not spawn or signal processes
# =========================================================================== #


@pytest.fixture
def supervisor_module():
    import genesis.core.supervisor as module

    return module


def test_no_supervisor_refuses_lifecycle_actions(supervisor_module):
    supervisor = supervisor_module.NoSupervisor()
    start = supervisor.start("gm_1")
    stop = supervisor.stop("gm_1")

    assert not start.ok and start.unavailable
    assert not stop.ok and stop.unavailable
    # The refusal must tell the operator what to do instead.
    assert "systemctl" in start.detail
    assert start.backend == "none"


def test_no_supervisor_status_is_not_an_error(supervisor_module):
    result = supervisor_module.NoSupervisor().status("gm_1")
    assert result.ok
    assert result.state == {"running": False, "managed": False}


def test_unknown_supervisor_name_is_refused(supervisor_module, monkeypatch):
    monkeypatch.setenv("GENESIS_SUPERVISOR", "supervisord-typo")
    with pytest.raises(supervisor_module.SupervisorUnavailable):
        supervisor_module.get_supervisor()


def test_supervisor_defaults_to_none(monkeypatch, supervisor_module):
    monkeypatch.delenv("GENESIS_SUPERVISOR", raising=False)
    supervisor_module.reset_supervisor()
    monkeypatch.setattr(
        supervisor_module, "get_supervisor",
        lambda explicit=None: supervisor_module.NoSupervisor(),
    )
    assert supervisor_module.NoSupervisor().name == "none"
    supervisor_module.reset_supervisor()


@pytest.mark.parametrize(
    "mind_id,expected",
    [
        ("GMID-12345678", True),
        ("gm_abc123", True),
        ("GMD-99.1", True),
        ("a" * 128, True),
        ("a" * 129, False),
        ("", False),
        ("../../etc/passwd", False),
        ("gm; rm -rf /", False),
        ("gm id with spaces", False),
        ("gm$(whoami)", False),
        ("gm`id`", False),
        ("gm\n--now", False),
    ],
)
def test_systemd_mind_id_validation(supervisor_module, mind_id, expected):
    """A unit name is not a place to discover an id was attacker-controlled."""
    assert supervisor_module.SystemdSupervisor.is_valid_mind_id(mind_id) is expected


def test_systemd_refuses_an_unsafe_mind_id(supervisor_module):
    supervisor = supervisor_module.SystemdSupervisor()
    result = supervisor.start("../../etc/passwd")
    assert not result.ok
    assert "unsafe Mind id" in result.detail


def test_systemd_builds_a_fixed_argv_with_no_shell(supervisor_module, monkeypatch):
    """The command must be argv, never a shell string."""
    calls: list = []

    class Completed:
        returncode = 0
        stdout = "ok\n"
        stderr = ""

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return Completed()

    supervisor = supervisor_module.SystemdSupervisor(systemctl="/bin/systemctl")
    monkeypatch.setattr(supervisor, "_run", fake_run)
    supervisor.start("GMID-1")

    args, kwargs = calls[0]
    assert args == ["start", "genesis-mind@GMID-1.service"]
    assert "shell" not in kwargs


def test_systemd_status_reports_not_running_when_inactive(supervisor_module, monkeypatch):
    class Completed:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    responses = iter(
        [Completed(3, "inactive\n"), Completed(0, "MainPID=0\nSubState=dead\n")]
    )
    supervisor = supervisor_module.SystemdSupervisor(systemctl="/bin/systemctl")
    monkeypatch.setattr(supervisor, "_run", lambda args: next(responses))

    result = supervisor.status("GMID-1")
    assert result.ok
    assert result.state["running"] is False
    assert result.state["managed"] is True


def test_systemd_status_reports_pid_when_active(supervisor_module, monkeypatch):
    class Completed:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    responses = iter(
        [Completed(0, "active\n"), Completed(0, "MainPID=4242\nSubState=running\n")]
    )
    supervisor = supervisor_module.SystemdSupervisor(systemctl="/bin/systemctl")
    monkeypatch.setattr(supervisor, "_run", lambda args: next(responses))

    result = supervisor.status("GMID-1")
    assert result.state["running"] is True
    assert result.pid == 4242


def test_systemd_start_failure_is_reported_not_swallowed(supervisor_module, monkeypatch):
    class Completed:
        returncode = 1
        stdout = ""
        stderr = "Failed to start: unit not found"

    supervisor = supervisor_module.SystemdSupervisor(systemctl="/bin/systemctl")
    monkeypatch.setattr(supervisor, "_run", lambda args: Completed())

    result = supervisor.start("GMID-1")
    assert not result.ok
    assert "unit not found" in result.detail


def test_routes_do_not_spawn_or_signal_processes():
    """The architectural guard for B11.

    AST-based, because a grep for `subprocess` would match the supervisor module
    itself and the point is that *routes.py* no longer contains a spawn or a
    signal call.
    """
    import ast

    import genesis.api.routes as routes

    tree = ast.parse(Path(routes.__file__).read_text(encoding="utf-8-sig"))
    offenders: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name in ("Popen", "run", "call", "check_output"):
            # Only subprocess.* matters; psutil conversions also have `run`.
            owner = getattr(func, "value", None)
            owner_name = getattr(owner, "id", None)
            if owner_name == "subprocess":
                offenders.append(f"subprocess.{name} at line {node.lineno}")
        if name in ("kill", "send_signal", "terminate"):
            offenders.append(f".{name}() at line {node.lineno}")

    assert not offenders, (
        "genesis/api/routes.py must not spawn or signal processes (plan item B11): "
        + ", ".join(offenders)
    )


def test_daemon_endpoints_delegate_to_the_supervisor():
    import inspect

    import genesis.api.routes as routes

    for endpoint in (routes.start_daemon, routes.stop_daemon):
        source = inspect.getsource(endpoint)
        assert "get_supervisor" in source


def test_start_daemon_returns_501_when_no_supervisor(monkeypatch):
    """The honest failure mode: refuse and explain, never silently fork."""
    import asyncio

    import genesis.api.routes as routes

    monkeypatch.setattr(routes, "_load_mind", lambda mind_id: _async_none())

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            routes.start_daemon("gm_1", current_user=object())
        )
    assert excinfo.value.status_code == 501
    assert "GENESIS_SUPERVISOR" in excinfo.value.detail


async def _async_none():
    return None


# =========================================================================== #
# B12 — refuse a placeholder signing key outside test/development
# =========================================================================== #


@pytest.fixture
def settings_module():
    import genesis.config.settings as module

    return module


def _settings(settings_module, monkeypatch, *, environment, api_key, secret_key):
    monkeypatch.setenv("GENESIS_ENV", environment)
    return settings_module.Settings(api_secret_key=api_key, secret_key=secret_key)


PLACEHOLDER = "your-secret-key-change-this-in-production"
REAL = "a" * 64


@pytest.mark.parametrize("environment", ["production", "prod", "", "staging"])
def test_placeholder_key_is_refused_outside_dev(settings_module, monkeypatch, environment):
    settings = _settings(
        settings_module, monkeypatch,
        environment=environment, api_key=PLACEHOLDER, secret_key=PLACEHOLDER,
    )
    with pytest.raises(settings_module.InsecureSecretError) as excinfo:
        settings.assert_secure_secrets()
    # The message must name the variable and give the fix.
    assert "API_SECRET_KEY" in str(excinfo.value)
    assert "token_hex" in str(excinfo.value)


@pytest.mark.parametrize("environment", ["test", "development", "dev", "local"])
def test_placeholder_key_is_tolerated_in_dev(settings_module, monkeypatch, environment):
    settings = _settings(
        settings_module, monkeypatch,
        environment=environment, api_key=PLACEHOLDER, secret_key=PLACEHOLDER,
    )
    settings.assert_secure_secrets()  # warns, does not raise


def test_real_key_is_accepted_in_production(settings_module, monkeypatch):
    settings = _settings(
        settings_module, monkeypatch,
        environment="production", api_key=REAL, secret_key=REAL,
    )
    settings.assert_secure_secrets()
    assert settings.insecure_secrets() == []


def test_one_placeholder_among_real_keys_still_refuses(settings_module, monkeypatch):
    """Partial configuration is the common mistake, so it must not slip through."""
    settings = _settings(
        settings_module, monkeypatch,
        environment="production", api_key=REAL, secret_key=PLACEHOLDER,
    )
    with pytest.raises(settings_module.InsecureSecretError) as excinfo:
        settings.assert_secure_secrets()
    assert "SECRET_KEY" in str(excinfo.value)
    assert "API_SECRET_KEY" not in str(excinfo.value).split("is still")[0]


def test_short_key_is_reported(settings_module, monkeypatch):
    settings = _settings(
        settings_module, monkeypatch,
        environment="production", api_key="short", secret_key=REAL,
    )
    assert settings.short_secrets() == ["API_SECRET_KEY"]
    settings.assert_secure_secrets()  # warns, does not raise


def test_default_environment_is_treated_as_production(settings_module, monkeypatch):
    """An unset GENESIS_ENV must assume the strictest case, not the loosest."""
    monkeypatch.delenv("GENESIS_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert settings_module.Settings.environment_name() == "production"


def test_app_refuses_to_start_with_a_placeholder_key(monkeypatch, settings_module):
    monkeypatch.setenv("GENESIS_ENV", "production")
    monkeypatch.setenv("API_SECRET_KEY", PLACEHOLDER)
    monkeypatch.setenv("SECRET_KEY", PLACEHOLDER)
    settings_module.get_settings.cache_clear()

    import genesis.api.server as server

    monkeypatch.setattr(server, "settings", settings_module.Settings())

    with pytest.raises(settings_module.InsecureSecretError):
        server.create_app()

    settings_module.get_settings.cache_clear()
