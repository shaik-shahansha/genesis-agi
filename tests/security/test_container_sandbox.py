"""Container sandbox provider tests (plan item B2b).

Two tiers, deliberately:

1. **argv and policy tests** — always run. The Docker flags *are* the security
   control, so they are asserted exhaustively without needing a container. These
   caught three real bugs during development: an invalid `,rw` mount field that
   made every execution fail to start, `seccomp=default` being parsed as a
   filename, and a return code read before the process was reaped that reported a
   failed container start as `rc=0 exit_reason="completed"`.

2. **escape tests** — run only when a container runtime and a test image are
   present, and skip otherwise. They execute real payloads that attempt to leave
   the sandbox. A provider that reports `filesystem_isolation: True` but does not
   enforce it is worse than one that admits it has none, so the claim is tested
   rather than trusted.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from genesis.sandbox.base import (
    SandboxError,
    SandboxPolicy,
    SandboxSpec,
    SandboxUnavailableError,
)
from genesis.sandbox.container import (
    CONTAINER_WORKDIR,
    ContainerRuntime,
    ContainerSandboxProvider,
    SandboxRuntimeUnavailable,
    bind_mount_source,
    build_run_argv,
)

# =========================================================================== #
# bind_mount_source
# =========================================================================== #


def test_bind_mount_source_uses_forward_slashes(tmp_path: Path):
    """The daemon rejects backslash sources, so separators are normalised."""
    rendered = bind_mount_source(tmp_path)
    assert "\\" not in rendered
    assert "/" in rendered


def test_bind_mount_source_refuses_a_comma(tmp_path: Path):
    """`--mount` is comma-separated, so a comma would truncate the argument."""
    awkward = tmp_path / "has,comma"
    awkward.mkdir()
    with pytest.raises(SandboxError) as excinfo:
        bind_mount_source(awkward)
    assert "comma" in str(excinfo.value)


# =========================================================================== #
# build_run_argv — the security flags
# =========================================================================== #


def _argv(**overrides):
    defaults = dict(
        runtime_cli="docker",
        image="genesis-sandbox:latest",
        workdir=Path("/tmp/sbx-1"),
        policy=SandboxPolicy(),
        command=["python", f"{CONTAINER_WORKDIR}/script.py"],
        container_name="genesis-sbx-1",
        uid=10001,
        gid=10001,
    )
    defaults.update(overrides)
    return build_run_argv(**defaults)


def _pairs(argv: list[str]) -> list[tuple[str, str]]:
    """Flag/value pairs, for assertions, tolerant of boolean flags.

    A naive pairwise walk is wrong here: ``--read-only`` and ``--rm`` take no
    value, so consuming the following argument as one swallows the next flag.
    Looking each flag up by index instead makes the assertions independent of
    how flags and switches are interleaved.
    """
    pairs: list[tuple[str, str]] = []
    for index, item in enumerate(argv[:-1]):
        if item.startswith("--") and not argv[index + 1].startswith("--"):
            pairs.append((item, argv[index + 1]))
    return pairs


def _values_of(argv: list[str], flag: str) -> list[str]:
    """All values supplied for a repeated flag (e.g. several ``--env``)."""
    values: list[str] = []
    for index, item in enumerate(argv[:-1]):
        if item == flag and not argv[index + 1].startswith("--"):
            values.append(argv[index + 1])
    return values


def _matching_runtime(**stdout_responses):
    """Build a fake container CLI whose responses depend on the arguments."""

    class Completed:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    def fake_run(args, timeout):
        joined = " ".join(args)
        for needle, stdout in stdout_responses.items():
            if needle.replace("_", ".") in joined or needle in joined:
                return Completed(stdout)
        return Completed("")

    return fake_run


def test_network_is_none_by_default():
    argv = _argv()
    assert ("--network", "none") in _pairs(argv)


def test_root_filesystem_is_read_only():
    assert "--read-only" in _argv()


def test_capabilities_are_all_dropped():
    assert ("--cap-drop", "ALL") in _pairs(_argv())


def test_no_new_privileges_is_set():
    assert ("--security-opt", "no-new-privileges") in _pairs(_argv())


def test_runs_as_a_non_root_user():
    assert ("--user", "10001:10001") in _pairs(_argv())


def test_pid_limit_is_cgroup_scoped():
    """cgroup-scoped, unlike the local provider's per-user RLIMIT_NPROC."""
    argv = _argv(policy=SandboxPolicy(pids_limit=64))
    assert ("--pids-limit", "64") in _pairs(argv)


def test_memory_limit_is_set_with_swap_disabled():
    argv = _argv(policy=SandboxPolicy(memory_mb=512))
    pairs = _pairs(argv)
    assert ("--memory", "512m") in pairs
    # Equal memory and memory-swap disables swap for the container, so the limit
    # cannot be evaded by swapping.
    assert ("--memory-swap", "512m") in pairs


def test_file_size_limit_is_set():
    argv = _argv(policy=SandboxPolicy(file_size_mb=8))
    assert ("--ulimit", "fsize=8388608") in _pairs(argv)


def test_core_dumps_are_disabled():
    assert ("--ulimit", "core=0") in _pairs(_argv())


def test_workspace_is_the_only_bind_mount():
    argv = _argv(workdir=Path("/tmp/sbx-42"))
    mounts = _values_of(argv, "--mount")
    assert len(mounts) == 1
    assert "target=/workspace" in mounts[0]
    assert "source=" in mounts[0]


def test_mount_has_no_rw_field():
    """There is no `rw` option in Docker's --mount; passing it breaks the flag."""
    mount = _values_of(_argv(), "--mount")[0]
    assert not mount.endswith(",rw")
    assert mount.endswith("/workspace")


def test_tmp_is_a_restricted_tmpfs():
    argv = _argv()
    assert "--tmpfs" in argv
    value = _values_of(argv, "--tmpfs")[0]
    assert "noexec" in value and "nosuid" in value and "nodev" in value


def test_container_is_removed_after_the_run():
    assert "--rm" in _argv()


def test_no_docker_socket_is_mounted():
    """The provider *uses* a runtime socket; the sandbox must never see one."""
    argv = _argv()
    assert "docker.sock" not in " ".join(argv)
    assert not any("docker.sock" in value for _, value in _pairs(argv))


def test_no_host_environment_is_passed_through():
    """Only explicitly supplied values appear; there is no --env-file or bare -e."""
    argv = _argv(container_env={"PATH": "/usr/bin", "HOME": "/tmp"})
    assert sorted(_values_of(argv, "--env")) == ["HOME=/tmp", "PATH=/usr/bin"]
    assert "--env-file" not in argv


def test_isolation_runtime_is_requested_when_configured():
    assert ("--runtime", "runsc") in _pairs(_argv(runtime="runsc"))


def test_default_runtime_is_not_overridden():
    """With no runtime requested the daemon default is used; we do not force runc."""
    assert "--runtime" not in _argv(runtime=None)


def test_seccomp_is_not_passed_as_the_literal_default():
    """`seccomp=default` is parsed as a filename and fails the whole run."""
    pairs = _pairs(_argv())
    assert ("--security-opt", "seccomp=default") not in pairs
    assert not any(v == "seccomp=default" for _, v in pairs)


def test_explicit_seccomp_profile_path_is_passed(tmp_path: Path):
    profile = tmp_path / "seccomp.json"
    profile.write_text("{}")
    assert ("--security-opt", f"seccomp={profile}") in _pairs(_argv(seccomp_profile=profile))


def test_image_and_command_are_last():
    argv = _argv(image="my-image:1", command=["python", "x.py"])
    assert argv[-3:] == ["my-image:1", "python", "x.py"]


def test_ipc_namespace_is_isolated():
    assert ("--ipc", "none") in _pairs(_argv())


def test_container_name_is_set_for_cleanup():
    assert ("--name", "genesis-sbx-1") in _pairs(_argv(container_name="genesis-sbx-1"))


# -- egress ----------------------------------------------------------------- #


def test_allow_listed_egress_requires_a_proxy():
    """Plain Docker networking cannot filter destinations, so refuse rather than widen."""
    policy = SandboxPolicy(network_enabled=True, allowed_domains=("api.example.com",))
    with pytest.raises(SandboxUnavailableError) as excinfo:
        build_run_argv(
            runtime_cli="docker",
            image="img",
            workdir=Path("/tmp/x"),
            policy=policy,
            command=["python"],
            container_name="c",
        )
    assert "proxy" in str(excinfo.value).lower()


def test_egress_goes_through_the_proxy_when_configured():
    policy = SandboxPolicy(network_enabled=True, allowed_domains=("api.example.com",))
    argv = build_run_argv(
        runtime_cli="docker",
        image="img",
        workdir=Path("/tmp/x"),
        policy=policy,
        command=["python"],
        container_name="c",
        egress_proxy_url="http://egress:3128",
    )
    env_values = _values_of(argv, "--env")
    assert "HTTPS_PROXY=http://egress:3128" in env_values
    assert "http_proxy=http://egress:3128" in env_values
    # And it is not `none`, so the proxy is reachable.
    assert ("--network", "none") not in _pairs(argv)


def test_invalid_policy_is_rejected_before_argv_is_built():
    policy = SandboxPolicy(allow_package_install=True)
    with pytest.raises(Exception):
        build_run_argv(
            runtime_cli="docker",
            image="img",
            workdir=Path("/tmp/x"),
            policy=policy,
            command=["python"],
            container_name="c",
        )


# =========================================================================== #
# Runtime detection and fail-closed behaviour
# =========================================================================== #


def test_missing_cli_is_reported_not_raised():
    provider = ContainerSandboxProvider(runtime_cli="definitely-not-a-real-cli")
    info = provider.inspect_runtime()
    assert info.available is False
    assert info.error
    caps = provider.capabilities()
    assert caps["runtime_available"] is False


def test_require_runtime_raises_when_unusable():
    provider = ContainerSandboxProvider(runtime_cli="definitely-not-a-real-cli")
    with pytest.raises(SandboxRuntimeUnavailable):
        provider._require_runtime()


def test_requested_isolation_runtime_absence_fails_closed(monkeypatch):
    """A missing gVisor must refuse, not silently run on runc."""
    provider = ContainerSandboxProvider(runtime="runsc")

    class Completed:
        returncode = 0
        stdout = '{"runc": {"path": "runc"}}'
        stderr = ""

    monkeypatch.setattr(provider, "_run_cli", lambda args, timeout: Completed())
    provider._runtime_info = None

    with pytest.raises(SandboxRuntimeUnavailable) as excinfo:
        provider._require_runtime()
    assert "runsc" in str(excinfo.value)
    assert "downgrading" in str(excinfo.value)


def test_require_isolation_runtime_flag_enforced(monkeypatch):
    provider = ContainerSandboxProvider(require_isolation_runtime=True)

    class Completed:
        returncode = 0
        stdout = '{"runc": {"path": "runc"}}'
        stderr = ""

    monkeypatch.setattr(provider, "_run_cli", lambda args, timeout: Completed())
    provider._runtime_info = None

    with pytest.raises(SandboxRuntimeUnavailable):
        provider._require_runtime()


def test_seccomp_profile_is_read_from_the_daemon(monkeypatch):
    provider = ContainerSandboxProvider()
    monkeypatch.setattr(
        provider,
        "_run_cli",
        _matching_runtime(
            Runtimes='{"runc": {}}',
            SecurityOptions='["name=seccomp,profile=builtin"]',
        ),
    )
    provider._runtime_info = None

    caps = provider.capabilities()
    assert caps["seccomp_profile"] == "builtin"


def test_capabilities_do_not_claim_a_kernel_boundary_without_one(monkeypatch):
    """`gvisor: False` with runc must not be reported as a kernel boundary."""
    provider = ContainerSandboxProvider()
    monkeypatch.setattr(
        provider,
        "_run_cli",
        _matching_runtime(Runtimes='{"runc": {}}', SecurityOptions="[]"),
    )
    provider._runtime_info = None

    caps = provider.capabilities()
    assert caps["is_security_boundary"] is True
    assert caps["kernel_boundary"] is False
    assert caps["gvisor"] is False


def test_capabilities_detect_gvisor_when_present(monkeypatch):
    provider = ContainerSandboxProvider(runtime="runsc")
    monkeypatch.setattr(
        provider,
        "_run_cli",
        _matching_runtime(Runtimes='{"runsc": {}, "runc": {}}', SecurityOptions="[]"),
    )
    provider._runtime_info = None

    caps = provider.capabilities()
    assert caps["gvisor"] is True
    assert caps["kernel_boundary"] is True
    # And it is accepted rather than refused.
    provider._require_runtime()


def test_factory_refuses_to_downgrade_from_container(monkeypatch, tmp_path):
    """Requesting `container` with a broken runtime must not fall back to `local`."""
    import genesis.sandbox.factory as factory

    monkeypatch.setenv("GENESIS_SANDBOX_PROVIDER", "container")
    monkeypatch.setenv("GENESIS_SANDBOX_RUNTIME_CLI", "definitely-not-a-real-cli")
    factory.reset_sandbox_provider()

    with pytest.raises(SandboxError) as excinfo:
        factory.get_sandbox_provider()
    message = str(excinfo.value)
    assert "container" in message
    assert "fall back" in message

    factory.reset_sandbox_provider()


def test_factory_reports_container_in_valid_providers():
    import genesis.sandbox.factory as factory

    assert "container" in factory.VALID_PROVIDERS


def test_factory_prefers_gvisor_when_isolation_is_required(monkeypatch):
    import genesis.sandbox.factory as factory

    monkeypatch.setenv("GENESIS_SANDBOX_REQUIRE_ISOLATION_RUNTIME", "1")
    monkeypatch.delenv("GENESIS_SANDBOX_RUNTIME", raising=False)
    runtime, required = factory._resolve_container_runtime()
    assert runtime == "runsc"
    assert required is True


# =========================================================================== #
# Policy and lifecycle logic that needs no container
# =========================================================================== #


@pytest.mark.parametrize(
    "code",
    [
        "import subprocess; subprocess.run(['pip', 'install', 'requests'])",
        "import os; os.system('pip install requests')",
        "import subprocess; subprocess.call(['apt-get', 'install', '-y', 'curl'])",
        'subprocess.run(["npm", "install", "-g", "serve"])',
        "import subprocess; subprocess.run(['uv', 'pip', 'install', 'httpx'])",
        "import subprocess; subprocess.check_call(['apk', 'add', 'curl'])",
    ],
)
def test_installation_attempts_are_detected(code):
    assert ContainerSandboxProvider._looks_like_install(code)


@pytest.mark.parametrize(
    "code",
    [
        "import json; print(json.dumps({'a': 1}))",
        "import numpy; print(numpy.arange(3))",
        "subprocess.run(['echo', 'installation complete'])",
        "packages = ['requests', 'httpx']\nprint(len(packages))",
    ],
)
def test_ordinary_code_is_not_flagged(code):
    assert not ContainerSandboxProvider._looks_like_install(code)


def test_a_comment_about_installing_is_not_flagged():
    """A false positive refuses a legitimate script, so commentary must not trip it."""
    assert not ContainerSandboxProvider._looks_like_install(
        "# no need to pip install anything here\nprint('ready')"
    )


def test_root_caller_does_not_run_the_sandbox_as_root(monkeypatch):
    """Running the sandbox as root would defeat the isolation it provides."""
    provider = ContainerSandboxProvider()
    monkeypatch.setattr(os, "getuid", lambda: 0, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 0, raising=False)
    uid, gid = provider._resolve_ids(SandboxPolicy())
    assert uid != 0 and gid != 0


def test_explicit_run_as_uid_is_honoured():
    provider = ContainerSandboxProvider()
    assert provider._resolve_ids(SandboxPolicy(run_as_uid=4242)) == (4242, 4242)


def test_handle_from_another_provider_is_rejected():
    from genesis.sandbox.base import SandboxHandle

    provider = ContainerSandboxProvider()
    handle = SandboxHandle(
        sandbox_id="sbx-x", provider_name="local", spec=SandboxSpec(), host_workdir=None
    )
    with pytest.raises(SandboxError):
        provider._require_workdir(handle)


# =========================================================================== #
# Escape tests — only run when a runtime and image are actually available
# =========================================================================== #

TEST_IMAGE = os.environ.get("GENESIS_SANDBOX_TEST_IMAGE", "python:3.11-slim")


def _runtime_ready() -> bool:
    if not (shutil.which("docker") or shutil.which("podman")):
        return False
    try:
        probe = subprocess.run(
            ["docker", "image", "inspect", TEST_IMAGE],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:  # noqa: BLE001
        return False
    return probe.returncode == 0


requires_runtime = pytest.mark.skipif(
    not _runtime_ready(),
    reason=(
        f"needs a container runtime and the {TEST_IMAGE} image; "
        "set GENESIS_SANDBOX_TEST_IMAGE or pull the image to enable escape tests"
    ),
)


@pytest.fixture
def container_provider(tmp_path: Path):
    provider = ContainerSandboxProvider(root=tmp_path / "sbx", image=TEST_IMAGE)
    provider._require_runtime()
    return provider


def _run(provider, handle, code, policy=None):
    return asyncio.run(provider.execute(handle, code, policy=policy))


@pytest.fixture
def sandbox(container_provider):
    handle = asyncio.run(
        container_provider.create(SandboxSpec(policy=SandboxPolicy(wall_timeout_s=60)))
    )
    yield handle
    asyncio.run(container_provider.terminate(handle))


@requires_runtime
def test_escape_runs_code(container_provider, sandbox):
    result = _run(container_provider, sandbox, "print('sandbox-alive')")
    assert result.success, result.stderr
    assert "sandbox-alive" in result.stdout


@requires_runtime
def test_escape_cannot_read_host_paths(container_provider, sandbox):
    """The claim being tested: `filesystem_isolation: True` is enforced, not asserted."""
    result = _run(
        container_provider,
        sandbox,
        "import os\n"
        "print('GENESIS_HOME=' + str(os.path.exists('/root/.genesis')))\n"
        "print('OPT_GENESIS=' + str(os.path.exists('/opt/genesis')))\n"
        "print('VAR_LIB=' + str(os.path.exists('/var/lib/genesis')))\n"
        "print('CWD=' + os.getcwd())",
    )
    assert result.success, result.stderr
    assert "GENESIS_HOME=False" in result.stdout
    assert "OPT_GENESIS=False" in result.stdout
    assert "VAR_LIB=False" in result.stdout
    assert f"CWD={CONTAINER_WORKDIR}" in result.stdout


@requires_runtime
def test_escape_root_filesystem_is_read_only(container_provider, sandbox):
    result = _run(
        container_provider,
        sandbox,
        "try:\n"
        "    open('/etc/genesis-should-not-exist', 'w').write('x')\n"
        "    print('WROTE=True')\n"
        "except OSError:\n"
        "    print('WROTE=False')",
    )
    assert result.success, result.stderr
    assert "WROTE=False" in result.stdout


@requires_runtime
def test_escape_network_is_unreachable(container_provider, sandbox):
    result = _run(
        container_provider,
        sandbox,
        "import socket\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 53), timeout=5)\n"
        "    print('CONNECTED=True')\n"
        "except OSError:\n"
        "    print('CONNECTED=False')",
    )
    assert result.success, result.stderr
    assert "CONNECTED=False" in result.stdout


@requires_runtime
def test_escape_runs_as_non_root(container_provider, sandbox):
    result = _run(container_provider, sandbox, "import os; print('UID=' + str(os.getuid()))")
    assert result.success, result.stderr
    assert "UID=0" not in result.stdout


@requires_runtime
def test_escape_timeout_is_enforced(container_provider, sandbox):
    result = _run(
        container_provider,
        sandbox,
        "while True:\n    pass",
        policy=SandboxPolicy(wall_timeout_s=6),
    )
    assert result.exit_reason == "timeout"
    assert result.timed_out
    assert not result.success


@requires_runtime
def test_escape_workspace_is_writable_and_artifacts_export(container_provider, sandbox):
    result = _run(
        container_provider,
        sandbox,
        "open('report.txt', 'w').write('produced')\nprint('done')",
    )
    assert result.success, result.stderr

    artifacts = asyncio.run(container_provider.download(sandbox, ["report.txt"]))
    assert artifacts and artifacts[0].host_path.read_text() == "produced"


@requires_runtime
def test_escape_output_is_bounded(container_provider, sandbox):
    result = _run(
        container_provider,
        sandbox,
        "print('x' * 400000)",
        policy=SandboxPolicy(max_output_bytes=4000),
    )
    assert len(result.stdout) <= 20_000
    assert result.output_truncated


@requires_runtime
def test_escape_installation_is_refused_before_start(container_provider, sandbox):
    result = _run(
        container_provider,
        sandbox,
        "import subprocess; subprocess.run(['pip', 'install', 'requests'])",
    )
    assert result.exit_reason == "policy_denied"


@requires_runtime
def test_escape_leaves_nothing_behind(container_provider, sandbox):
    """A crash or timeout must not leave a container or workspace running."""
    _run(
        container_provider,
        sandbox,
        "while True:\n    pass",
        policy=SandboxPolicy(wall_timeout_s=5),
    )
    running = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={container_provider._container_name(sandbox)}",
         "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    assert running.stdout.strip() == "", f"container left behind: {running.stdout}"

    asyncio.run(container_provider.terminate(sandbox))
    assert not Path(sandbox.host_workdir).exists()


@requires_runtime
def test_escape_a_failed_start_is_not_reported_as_success(container_provider):
    """Regression: a bad flag once produced rc=0 and exit_reason='completed'.

    A sandbox that never ran must never look like a successful run — that is the
    worst possible failure mode for this component, because the caller would
    treat the (empty) output as the result of the untrusted code.
    """
    handle = asyncio.run(
        container_provider.create(SandboxSpec(policy=SandboxPolicy(wall_timeout_s=30)))
    )
    try:
        original = container_provider.image
        container_provider.image = "genesis-does-not-exist:never"
        try:
            result = _run(container_provider, handle, "print('should not run')")
            assert not result.success
            assert result.exit_reason != "completed", (
                "a container that failed to start was reported as a completed run"
            )
            assert result.return_code != 0
            assert result.error and "never ran" in result.error
        finally:
            container_provider.image = original
    finally:
        asyncio.run(container_provider.terminate(handle))
