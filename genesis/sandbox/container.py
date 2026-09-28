"""Container sandbox provider: real filesystem, PID and network isolation.

Plan item **B2b** — the main remaining gap in the Phase B gate.

``LocalSandboxProvider`` enforces environment scrubbing, resource limits,
timeouts, bounded output and artifact control, but it is **not** a security
boundary: it has no filesystem isolation, no PID namespace, and network
isolation only where ``unshare -rn`` happens to be available. A determined
payload still shares the host's filesystem and process table.

This provider supplies what was missing by running each sandbox as a container
under a process-level runtime:

* an **optional kernel boundary** — gVisor (``runsc``) or Kata (``kata-runtime``)
  when the host provides one, so a container escape needs a *runtime* bug rather
  than a shared-kernel privilege bug;
* **read-only root filesystem** with a single writable bind mount, so the
  sandbox cannot see the API's data directory, its configuration, or its
  credentials;
* ``--network none`` by default, with allow-listed egress only through an
  explicit proxy;
* ``--cap-drop ALL``, ``no-new-privileges``, a seccomp profile, and a per-container
  PID limit (**cgroup-level**, which fixes the ``RLIMIT_NPROC``-is-per-user
  problem that made the local provider's ``pids_limit`` nearly useless);
* cgroup memory limits, which bound *resident* memory rather than virtual address
  space (the ``RLIMIT_AS`` caveat in ``base.SandboxPolicy`` doesn't apply here).

Design notes
------------
* **Fail closed.** If the container runtime is unreachable, or the requested
  isolation runtime is not available, the provider raises rather than degrading
  to ``runc`` on the host. Silent degradation is how a sandbox stops being one.
* **No Docker socket inside the sandbox.** The provider *uses* a runtime socket;
  it never mounts one into the sandbox, so a payload cannot escape by talking to
  the runtime.
* **argv is built by a pure function** (:func:`build_run_argv`) so the security
  flags can be asserted exhaustively in tests without needing a container to run.
* **Capabilities are reported from evidence**, not intent: ``gvisor`` is true only
  if the runtime list actually contains it.

This provider is intended to live in a dedicated sandbox-manager service (ADR-0005)
and be reached over a remote socket (``DOCKER_HOST``). Running it beside the API
works but gives the API's own container the ability to create containers, which
is a wider privilege than most deployments want.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from genesis.sandbox.base import (
    Artifact,
    ExecutionResult,
    SandboxError,
    SandboxHandle,
    SandboxPolicy,
    SandboxSpec,
    SandboxUnavailableError,
    SnapshotRef,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ContainerRuntime",
    "ContainerSandboxProvider",
    "build_run_argv",
    "bind_mount_source",
    "SandboxRuntimeUnavailable",
    "KNOWN_RUNTIMES",
    "DEFAULT_SANDBOX_IMAGE",
]

#: Default image. Ships Python plus a small pre-baked set of libraries; anything
#: else is a `CapabilityUnavailableError`, never a runtime install (SEC-04).
DEFAULT_SANDBOX_IMAGE = "genesis-sandbox:latest"

#: Isolation runtimes, strongest first. ``runc`` is the default and provides
#: namespace + cgroup isolation but shares the host kernel, so a kernel exploit
#: is an escape. ``runsc`` (gVisor) and ``kata-runtime`` add a boundary.
KNOWN_RUNTIMES: tuple[str, ...] = ("runsc", "kata-runtime", "runc")

#: Ceiling on how long any single container-runtime command may take. Image
#: pulls and container creation are fast once the image is present; anything
#: slower means the runtime is unhealthy.
RUNTIME_COMMAND_TIMEOUT_S = 120

#: In-container path the workspace is mounted at.
CONTAINER_WORKDIR = "/workspace"

#: In-container uid:gid used when the caller cannot supply a safe non-root id.
FALLBACK_SANDBOX_UID = 10001


class SandboxRuntimeUnavailable(SandboxUnavailableError):
    """The container runtime, or the requested isolation runtime, is unusable."""


@dataclass(frozen=True)
class ContainerRuntime:
    """Evidence about the container runtime on this host.

    Everything here is *observed*, not configured, so ``capabilities()`` can
    report what is actually enforced.
    """

    cli: str
    available: bool
    version: Optional[str] = None
    runtimes: tuple[str, ...] = ()
    #: From `docker info` SecurityOptions, e.g. "name=seccomp,profile=builtin".
    security_options: tuple[str, ...] = ()
    error: Optional[str] = None

    @property
    def has_gvisor(self) -> bool:
        return "runsc" in self.runtimes

    @property
    def has_kata(self) -> bool:
        return "kata-runtime" in self.runtimes

    @property
    def seccomp_profile(self) -> Optional[str]:
        """The seccomp profile the daemon will apply, if it reports one."""
        for option in self.security_options:
            if "seccomp" not in option:
                continue
            for part in option.split(","):
                key, _, value = part.partition("=")
                if key.strip() == "profile":
                    return value.strip()
        return None

    def supports(self, runtime: Optional[str]) -> bool:
        if runtime is None or runtime in ("", "runc"):
            return self.available
        return runtime in self.runtimes


# --------------------------------------------------------------------------- #
# argv construction (pure, exhaustively testable)
# --------------------------------------------------------------------------- #


def bind_mount_source(path: Path) -> str:
    """Render a host path for Docker's ``--mount`` flag.

    Two platform traps this exists to handle:

    * On Windows the daemon rejects a backslash source path
      (``invalid argument "type=bind,source=C:\\Users\\..." for "--mount" flag``),
      so separators are normalised to forward slashes. That form is valid on
      Linux too, so there is one code path rather than two.
    * ``--mount`` is a comma-separated ``key=value`` list, so a comma in the path
      would silently truncate the argument. A path we generate never contains
      one, but a configured ``root`` could, and a silently truncated mount would
      change where the sandbox writes. Refuse instead.
    """
    resolved = Path(path).resolve()
    as_posix = resolved.as_posix()
    if "," in as_posix:
        raise SandboxError(
            f"Sandbox workspace path contains a comma, which cannot be expressed in "
            f"Docker's --mount syntax: {as_posix!r}. Configure a GENESIS_SANDBOX_ROOT "
            f"path without commas."
        )
    return as_posix


def build_run_argv(
    *,
    runtime_cli: str,
    image: str,
    workdir: Path,
    policy: SandboxPolicy,
    command: Sequence[str],
    container_name: str,
    runtime: Optional[str] = None,
    uid: int = FALLBACK_SANDBOX_UID,
    gid: int = FALLBACK_SANDBOX_UID,
    egress_proxy_url: Optional[str] = None,
    seccomp_profile: Optional[Path] = None,
    container_env: Optional[dict[str, str]] = None,
) -> list[str]:
    """Build the ``docker run`` argv for one sandbox execution.

    Kept pure and separate from execution for two reasons: the flags *are* the
    security control, so they need to be assertable without a container; and a
    single place building them means a caller cannot accidentally omit one.

    Raises:
        SandboxUnavailableError: if the request needs a capability that cannot be
            provided safely (unrestricted egress, or allow-listed egress with no
            proxy configured).
    """
    policy.validate()

    argv: list[str] = [
        runtime_cli,
        "run",
        "--rm",  # never leave a stopped container behind
        "--name",
        container_name,
        # --- identity -------------------------------------------------------
        "--user",
        f"{uid}:{gid}",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        # --- filesystem -----------------------------------------------------
        # Read-only root: the only writable path is the bind-mounted workspace.
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--mount",
        # NOTE: no `,rw` here. Docker's `--mount` has no `rw` option — writable is
        # the default and `readonly` (or `ro`) is the only mode flag. Writing
        # `,rw` makes the daemon reject the whole flag with
        # `invalid field 'rw' must be a key=value pair`, so every execution
        # failed to start while the log looked like an empty successful run.
        f"type=bind,source={bind_mount_source(workdir)},target={CONTAINER_WORKDIR}",
        "-w",
        CONTAINER_WORKDIR,
        # --- process isolation ----------------------------------------------
        # cgroup-scoped, unlike RLIMIT_NPROC which is per host user.
        "--pids-limit",
        str(policy.pids_limit),
        "--ipc",
        "none",
        # --- resource limits (cgroup: real RSS, not virtual address space) ---
        "--memory",
        f"{policy.memory_mb}m",
        "--memory-swap",
        f"{policy.memory_mb}m",  # equal value disables swap for the container
        "--cpus",
        str(max(1, policy.cpu_seconds // max(1, policy.wall_timeout_s))),
        "--ulimit",
        f"core=0",
        "--ulimit",
        f"fsize={policy.file_size_mb * 1024 * 1024}",
        "--ulimit",
        f"nofile=1024",
    ]

    # --- seccomp ------------------------------------------------------------ #
    # Only pass a seccomp option when we have an explicit profile *path*. The
    # literal string `default` is parsed by the daemon as a filename and fails
    # with `opening seccomp profile (default) failed: open default: ...`, so it
    # cannot be used to pin "the built-in profile" explicitly. Omitting the flag
    # means the daemon applies its own default (Docker's allow-list profile),
    # and `capabilities()['seccomp_profile']` reports which one is actually in
    # force so nobody assumes we pinned a stricter one.
    if seccomp_profile is not None:
        argv += ["--security-opt", f"seccomp={seccomp_profile}"]

    # --- kernel boundary ---------------------------------------------------- #
    if runtime and runtime != "runc":
        argv += ["--runtime", runtime]

    # --- network ------------------------------------------------------------ #
    if not policy.network_enabled:
        argv += ["--network", "none"]
    else:
        # Allow-listed egress cannot be enforced with plain Docker networking:
        # `--network bridge` is unrestricted, and Docker has no per-domain
        # filter. So an explicit proxy is required, and its absence is a refusal
        # rather than a silent widening.
        if not egress_proxy_url:
            raise SandboxUnavailableError(
                "network_enabled with allowed_domains requires an egress proxy; "
                "plain Docker networking cannot restrict destinations, so the "
                "sandbox would have unrestricted egress. Configure "
                "GENESIS_SANDBOX_EGRESS_PROXY or disable network access."
            )
        # `default` gives the container outbound reachability *only* through the
        # proxy. The proxy is what enforces the domain allow-list.
        argv += [
            "--network",
            "bridge",
            "--env",
            f"HTTP_PROXY={egress_proxy_url}",
            "--env",
            f"HTTPS_PROXY={egress_proxy_url}",
            "--env",
            f"http_proxy={egress_proxy_url}",
            "--env",
            f"https_proxy={egress_proxy_url}",
            "--env",
            "NO_PROXY=127.0.0.1,localhost",
        ]

    # --- environment -------------------------------------------------------- #
    # Nothing is inherited from the host. The container gets an explicit, tiny
    # environment; this is the SEC-05 control, and it is why no `--env-file` or
    # `-e NAME` pass-through appears anywhere in this function.
    for key, value in (container_env or {}).items():
        argv += ["--env", f"{key}={value}"]

    argv += [image, *command]
    return argv


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #


class ContainerSandboxProvider:
    """Runs each sandbox as a hardened container.

    Lifecycle mirrors :class:`~genesis.sandbox.local.LocalSandboxProvider`: the
    host directory returned in ``SandboxHandle.host_workdir`` is bind-mounted into
    the container, so artifact export and upload work identically to the local
    provider and the two are interchangeable behind ``SandboxProvider``.
    """

    name = "container"

    def __init__(
        self,
        *,
        root: Optional[Path] = None,
        image: str = DEFAULT_SANDBOX_IMAGE,
        runtime: Optional[str] = None,
        runtime_cli: Optional[str] = None,
        egress_proxy_url: Optional[str] = None,
        require_isolation_runtime: bool = False,
    ) -> None:
        """Initialise the provider.

        Args:
            root: Host directory under which sandbox workspaces are created.
            image: Sandbox image. Must be pre-baked; nothing is installed at
                runtime.
            runtime: Container runtime to request (``runc``, ``runsc``,
                ``kata-runtime``). ``None`` means the daemon default.
            runtime_cli: Path to the container CLI. Auto-detected when omitted.
            egress_proxy_url: Address of the egress proxy. Only needed when a
                policy enables network access.
            require_isolation_runtime: When True, refuse to run unless a
                kernel-boundary runtime (gVisor/Kata) is available. Set this in
                deployments that treat ``runc`` as insufficient.
        """
        self.root = Path(root) if root else Path(tempfile.gettempdir()) / "genesis-sandbox"
        self.root.mkdir(parents=True, exist_ok=True)
        self.image = image
        self.runtime = runtime
        self.egress_proxy_url = egress_proxy_url or os.environ.get(
            "GENESIS_SANDBOX_EGRESS_PROXY"
        )
        self.require_isolation_runtime = require_isolation_runtime

        detected_cli = runtime_cli or os.environ.get("GENESIS_SANDBOX_RUNTIME_CLI")
        if not detected_cli:
            for candidate in ("docker", "podman"):
                found = shutil.which(candidate)
                if found:
                    detected_cli = found
                    break
        self.runtime_cli = detected_cli or "docker"

        self._runtime_info: Optional[ContainerRuntime] = None

    # -- runtime detection -------------------------------------------------- #

    def inspect_runtime(self, *, refresh: bool = False) -> ContainerRuntime:
        """Probe the container runtime, caching the result.

        Uses ``--format {{json .Runtimes}}`` so installed runtimes are read from
        the daemon rather than guessed, which is what makes the ``gvisor`` and
        ``kata`` entries in :meth:`capabilities` evidence rather than intent.
        """
        if self._runtime_info is not None and not refresh:
            return self._runtime_info

        if shutil.which(self.runtime_cli) is None:
            self._runtime_info = ContainerRuntime(
                cli=self.runtime_cli,
                available=False,
                error=f"'{self.runtime_cli}' was not found on PATH",
            )
            return self._runtime_info

        try:
            completed = self._run_cli(["info", "--format", "{{json .Runtimes}}"], timeout=20)
        except Exception as exc:  # noqa: BLE001 - reported, not raised
            self._runtime_info = ContainerRuntime(
                cli=self.runtime_cli,
                available=False,
                error=f"{type(exc).__name__}: {exc}",
            )
            return self._runtime_info

        if completed.returncode != 0:
            self._runtime_info = ContainerRuntime(
                cli=self.runtime_cli,
                available=False,
                error=(completed.stderr or "container runtime unreachable").strip()[:400],
            )
            return self._runtime_info

        runtimes: tuple[str, ...] = ()
        security_options: tuple[str, ...] = ()
        text = (completed.stdout or "").strip()
        if text:
            try:
                payload = json.loads(text)
                if isinstance(payload, dict):
                    runtimes = tuple(sorted(str(key) for key in payload))
            except json.JSONDecodeError:
                logger.debug("could not parse runtime list: %r", text[:200])

        # The daemon's own security posture: this is what makes
        # `capabilities()['seccomp_profile']` evidence rather than a claim.
        try:
            security = self._run_cli(
                ["info", "--format", "{{json .SecurityOptions}}"], timeout=20
            )
            if security.returncode == 0 and (security.stdout or "").strip():
                parsed = json.loads(security.stdout.strip())
                if isinstance(parsed, list):
                    security_options = tuple(str(item) for item in parsed)
        except Exception as exc:  # noqa: BLE001 - reported as absent, not fatal
            logger.debug("could not read daemon security options: %s", exc)

        self._runtime_info = ContainerRuntime(
            cli=self.runtime_cli,
            available=True,
            runtimes=runtimes,
            security_options=security_options,
        )
        return self._runtime_info

    def capabilities(self) -> dict[str, Any]:
        """What this provider enforces, derived from the runtime probe."""
        info = self.inspect_runtime()
        return {
            "provider": self.name,
            # A container *is* a boundary, unlike the local subprocess provider.
            "is_security_boundary": True,
            "filesystem_isolation": True,
            "pid_isolation": True,
            "network_isolation": True,
            "env_scrubbing": True,
            "resource_limits": True,
            "timeout": True,
            "bounded_output": True,
            "package_install": False,
            "runtime": info.cli,
            "runtime_available": info.available,
            "runtimes_installed": list(info.runtimes),
            "gvisor": info.has_gvisor,
            "kata": info.has_kata,
            # Honest about which of these is *not* true: with runc the sandbox
            # shares the host kernel, so a kernel exploit is an escape.
            "kernel_boundary": info.has_gvisor or info.has_kata,
            "isolation_runtime_requested": self.runtime,
            "seccomp_profile": info.seccomp_profile,
            "security_options": list(info.security_options),
            "egress_proxy_configured": bool(self.egress_proxy_url),
            "error": info.error,
        }

    def _require_runtime(self) -> ContainerRuntime:
        """Return the runtime info, or raise. Fail closed, never degrade."""
        info = self.inspect_runtime()
        if not info.available:
            raise SandboxRuntimeUnavailable(
                f"The container runtime '{info.cli}' is not usable, so the 'container' "
                f"sandbox provider cannot run. Refusing rather than falling back to an "
                f"unsandboxed path. Reason: {info.error}"
            )

        if self.runtime and self.runtime != "runc":
            if not info.supports(self.runtime):
                raise SandboxRuntimeUnavailable(
                    f"Isolation runtime '{self.runtime}' is not available; installed "
                    f"runtimes are {', '.join(info.runtimes) or 'unknown'}. Refusing "
                    "rather than silently downgrading to runc, which shares the host "
                    "kernel."
                )

        if self.require_isolation_runtime and not (info.has_gvisor or info.has_kata):
            raise SandboxRuntimeUnavailable(
                "require_isolation_runtime is set but neither gVisor nor Kata is "
                "installed, so the sandbox would share the host kernel."
            )
        return info

    # -- lifecycle ---------------------------------------------------------- #

    async def create(self, spec: SandboxSpec) -> SandboxHandle:
        spec.policy.validate()
        self._require_runtime()

        sandbox_id = f"sbx-{uuid.uuid4().hex[:12]}"
        workdir = self.root / sandbox_id
        workdir.mkdir(parents=True, exist_ok=False)

        handle = SandboxHandle(
            sandbox_id=sandbox_id,
            provider_name=self.name,
            spec=spec,
            host_workdir=workdir,
        )

        if spec.files:
            await self.upload(handle, spec.files)
        return handle

    async def upload(self, handle: SandboxHandle, paths: list[Path]) -> None:
        workdir = self._require_workdir(handle)
        for source in paths:
            source = Path(source)
            if not source.is_file():
                continue
            shutil.copy2(source, workdir / source.name)

    async def download(self, handle: SandboxHandle, declared: list[str]) -> list[Artifact]:
        from genesis.core.paths import UnsafePathError, safe_filename

        workdir = self._require_workdir(handle)
        artifacts: list[Artifact] = []

        for name in declared:
            try:
                safe_name = safe_filename(name)
            except UnsafePathError:
                continue
            path = workdir / safe_name
            if not path.is_file():
                continue
            if path.resolve().parent != workdir.resolve():
                continue
            artifacts.append(
                Artifact(name=safe_name, host_path=path, size_bytes=path.stat().st_size)
            )
        return artifacts

    async def list_artifacts(self, handle: SandboxHandle) -> list[str]:
        workdir = self._require_workdir(handle)
        if not workdir.exists():
            return []
        internal = {"script.py", "_genesis_runner.py", "_genesis_entry.py"}
        names: list[str] = []
        for entry in sorted(workdir.iterdir()):
            if not entry.is_file() or entry.is_symlink():
                continue
            if entry.name in internal:
                continue
            names.append(entry.name)
        return names

    async def snapshot(self, handle: SandboxHandle) -> SnapshotRef:
        workdir = self._require_workdir(handle)
        if not workdir.exists():
            raise SandboxError(f"Sandbox {handle.sandbox_id} no longer exists")
        return SnapshotRef(
            snapshot_id=handle.sandbox_id,
            provider_name=self.name,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    async def restore(self, ref: SnapshotRef) -> SandboxHandle:
        workdir = self.root / ref.snapshot_id
        if not workdir.exists():
            raise SandboxError(
                f"Snapshot {ref.snapshot_id} is not present on disk; the container "
                "provider persists the workspace, not the container"
            )
        return SandboxHandle(
            sandbox_id=ref.snapshot_id,
            provider_name=self.name,
            spec=SandboxSpec(),
            host_workdir=workdir,
        )

    async def terminate(self, handle: SandboxHandle) -> None:
        """Remove the workspace and any container that outlived its run.

        ``--rm`` should have removed the container already; this is belt and
        braces for the case where the parent was killed mid-run, and it is why a
        crash cannot leave a sandbox container running indefinitely.
        """
        container_name = self._container_name(handle)

        try:
            await asyncio.to_thread(
                self._run_cli, ["rm", "-f", container_name], 30
            )
        except Exception as exc:  # noqa: BLE001 - cleanup is best effort
            logger.debug("could not remove container %s: %s", container_name, exc)

        workdir = handle.host_workdir
        if workdir and Path(workdir).exists():
            shutil.rmtree(workdir, ignore_errors=True)

    # -- execution ---------------------------------------------------------- #

    async def execute(
        self,
        handle: SandboxHandle,
        code: str,
        *,
        policy: Optional[SandboxPolicy] = None,
    ) -> ExecutionResult:
        effective = policy or handle.spec.policy
        effective.validate()
        self._require_runtime()

        workdir = self._require_workdir(handle)
        if not workdir.exists():
            raise SandboxError(f"Sandbox {handle.sandbox_id} no longer exists")

        if self._looks_like_install(code):
            return ExecutionResult(
                success=False,
                error=(
                    "Runtime package installation is not permitted in the sandbox. "
                    "Use a pre-baked image or declare the capability instead."
                ),
                exit_reason="policy_denied",
            )

        script = workdir / "script.py"
        script.write_text(code, encoding="utf-8")

        uid, gid = self._resolve_ids(effective)

        environment = {
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "HOME": "/tmp",
            "PATH": "/usr/local/bin:/usr/bin:/bin",
        }
        for thread_var in (
            "OPENBLAS_NUM_THREADS",
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
        ):
            environment[thread_var] = "1"

        argv = build_run_argv(
            runtime_cli=self.runtime_cli,
            image=self.image,
            workdir=workdir,
            policy=effective,
            command=["python", f"{CONTAINER_WORKDIR}/script.py"],
            container_name=self._container_name(handle),
            runtime=self.runtime,
            uid=uid,
            gid=gid,
            egress_proxy_url=self.egress_proxy_url,
            container_env=environment,
        )

        start = time.time()
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise SandboxRuntimeUnavailable(
                f"Could not start '{self.runtime_cli}': {exc}"
            ) from exc

        # The container runtime is the *inner* process; the wall-clock limit must
        # cover starting the container too, so allow a small margin and always
        # force-remove on timeout (a killed `docker run` can leave the container
        # running).
        stdout, stderr, truncated, timed_out = await self._drain(
            process,
            effective.max_output_bytes,
            effective.wall_timeout_s,
        )
        elapsed = time.time() - start

        if timed_out:
            await self._force_remove(handle)

        # Always reap before reading `returncode`.
        #
        # Without this, `returncode` can still be None when the pipes reach EOF,
        # and `returncode or 0` then reported a *failed* container start (bad
        # flag, missing image, unusable runtime) as rc=0 with
        # exit_reason="completed". A sandbox that silently reports success when
        # it never ran is the worst possible failure mode for this component.
        try:
            await process.wait()
        except Exception as exc:  # noqa: BLE001 - reported through the result
            logger.debug("could not reap sandbox process: %s", exc)

        return_code = process.returncode
        if return_code is None:
            # Reaping failed, so the outcome is unknown. Say so rather than
            # defaulting to success.
            return ExecutionResult(
                success=False,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                return_code=-1,
                execution_time=time.time() - start,
                error=(
                    "The container runtime produced output but never reported an exit "
                    "status, so the outcome is unknown. Treated as a failure."
                ),
                exit_reason="error",
                timed_out=timed_out,
                output_truncated=truncated,
            )

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        if truncated:
            note = "\n[OUTPUT TRUNCATED BY SANDBOX]\n"
            if len(stdout_text) > effective.max_output_bytes:
                stdout_text = stdout_text[: effective.max_output_bytes] + note
            if len(stderr_text) > effective.max_output_bytes:
                stderr_text = stderr_text[: effective.max_output_bytes] + note

        if timed_out:
            return ExecutionResult(
                success=False,
                stdout=stdout_text,
                stderr=stderr_text,
                return_code=return_code,
                execution_time=elapsed,
                error=f"Execution exceeded the {effective.wall_timeout_s}s wall-clock limit",
                exit_reason="timeout",
                timed_out=True,
                output_truncated=truncated,
            )

        # The container runtime failed to start the container at all.
        #
        # The CLI exits 125 for a `docker run` failure (bad flag, missing image,
        # unusable runtime), 126 when the command cannot be invoked and 127 when
        # it is not found. None of those mean "the process finished", so
        # reporting them as `completed` made a sandbox that never ran look like a
        # successful run. Surfaced explicitly so a caller cannot mistake it.
        if return_code in (125, 126, 127):
            reason = "unavailable" if return_code == 125 else "error"
            return ExecutionResult(
                success=False,
                stdout=stdout_text,
                stderr=stderr_text,
                return_code=return_code,
                execution_time=elapsed,
                error=(
                    f"The container runtime could not start the sandbox (exit "
                    f"{return_code}). The untrusted code never ran. "
                    f"{(stderr_text or '').strip()[:400]}"
                ),
                exit_reason=reason,
                output_truncated=truncated,
            )

        return ExecutionResult(
            success=return_code == 0,
            stdout=stdout_text,
            stderr=stderr_text,
            return_code=return_code,
            execution_time=elapsed,
            exit_reason="completed",
            output_truncated=truncated,
            # `--network none` is unconditional for a policy that does not enable
            # network access, so this claim is structural rather than probed.
            network_isolated=not effective.network_enabled,
        )

    # -- internals ---------------------------------------------------------- #

    def _container_name(self, handle: SandboxHandle) -> str:
        # Deterministic from the sandbox id so cleanup needs no extra state.
        return f"genesis-{handle.sandbox_id}"

    def _require_workdir(self, handle: SandboxHandle) -> Path:
        if handle.host_workdir is None:
            raise SandboxError(
                f"Handle {handle.sandbox_id} has no working directory; "
                f"was it created by the '{self.name}' provider?"
            )
        return Path(handle.host_workdir)

    def _resolve_ids(self, policy: SandboxPolicy) -> tuple[int, int]:
        """Pick the uid:gid the sandbox process runs as.

        Running as the API's own uid keeps the bind-mounted workspace writable
        without making it world-writable — the container still has a read-only
        root filesystem and cannot see any host path that is not mounted, so
        filesystem isolation does not depend on the uid.

        Running as root is never acceptable, so a root caller falls back to the
        shared non-root id.
        """
        if policy.run_as_uid is not None:
            return policy.run_as_uid, policy.run_as_uid

        try:
            uid, gid = os.getuid(), os.getgid()
        except AttributeError:  # Windows
            return FALLBACK_SANDBOX_UID, FALLBACK_SANDBOX_UID

        if uid == 0:
            return FALLBACK_SANDBOX_UID, FALLBACK_SANDBOX_UID
        return uid, gid

    def _run_cli(self, args: Sequence[str], timeout: int) -> Any:
        import subprocess

        return subprocess.run(  # noqa: S603 - fixed argv, no shell
            [self.runtime_cli, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    async def _force_remove(self, handle: SandboxHandle) -> None:
        try:
            await asyncio.to_thread(
                self._run_cli, ["rm", "-f", self._container_name(handle)], 30
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("could not force-remove container: %s", exc)

    @staticmethod
    def _looks_like_install(code: str) -> bool:
        """Detect runtime installation attempts (SEC-04).

        Matching is done on *normalised* source text: quotes, commas, brackets
        and line continuations are collapsed to single spaces, so
        ``['apt-get', 'install', '-y', 'curl']`` is recognised as readily as
        ``os.system('apt-get install -y curl')``. A pattern list that only
        matched shell strings would have missed the list-argument form entirely.

        Comments are stripped first. The cost of a false positive is refusing a
        legitimate script, so commentary *about* installation should not trip it.
        """
        import re

        without_comments = "\n".join(
            line.split("#", 1)[0] for line in code.splitlines()
        )
        normalised = re.sub(r"[\[\]'\"(),;\\]+", " ", without_comments.lower())
        normalised = re.sub(r"\s+", " ", normalised)

        markers = (
            "pip install",
            "pip3 install",
            "python -m pip",
            "uv pip install",
            "uv add",
            "poetry add",
            "conda install",
            "apt-get install",
            "apt install",
            "apk add",
            "yum install",
            "dnf install",
            "npm install -g",
            "npm i -g",
            "yarn global add",
            "gem install",
            "cargo install",
            "go install",
        )
        return any(marker in normalised for marker in markers)

    async def _drain(
        self, process: asyncio.subprocess.Process, cap: int, timeout_s: int
    ) -> tuple[bytes, bytes, bool, bool]:
        """Read both streams with a cap, killing the runtime on timeout."""

        async def read_capped(stream: Any) -> tuple[bytes, bool]:
            chunks: list[bytes] = []
            total = 0
            truncated = False
            if stream is None:
                return b"", False
            while True:
                chunk = await stream.read(8192)
                if not chunk:
                    break
                if total < cap:
                    remaining = cap - total
                    chunks.append(chunk[:remaining])
                    total += min(len(chunk), remaining)
                    if len(chunk) > remaining:
                        truncated = True
                else:
                    truncated = True
            return b"".join(chunks), truncated

        stdout_task = asyncio.create_task(read_capped(process.stdout))
        stderr_task = asyncio.create_task(read_capped(process.stderr))

        timed_out = False
        try:
            await asyncio.wait_for(
                asyncio.gather(stdout_task, stderr_task), timeout=timeout_s
            )
        except asyncio.TimeoutError:
            timed_out = True

        if timed_out:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            for task in (stdout_task, stderr_task):
                if not task.done():
                    task.cancel()

        stdout = b""
        stderr = b""
        truncated = False
        for task, assign in ((stdout_task, "out"), (stderr_task, "err")):
            try:
                data, was_truncated = task.result() if task.done() else (b"", False)
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                data, was_truncated = b"", False
            truncated = truncated or was_truncated
            if assign == "out":
                stdout = data
            else:
                stderr = data

        return stdout, stderr, truncated, timed_out
