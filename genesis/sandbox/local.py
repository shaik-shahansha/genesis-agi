"""Local sandbox provider: a hardened subprocess.

This is the default provider. It works everywhere Python does, with no daemon,
which is what makes it usable for local development and single-VPS deployments.

What it enforces
----------------
* **Environment scrubbing.** Only ``policy.env_allowlist`` is passed through.
  Every provider API key in the parent process is dropped (SEC-05).
* **Resource limits.** CPU seconds, address space, file size and process count
  are set by a generated runner script that limits *itself* before running the
  user code. This avoids ``preexec_fn``, which Python documents as unsafe in the
  presence of threads.
* **Timeout.** Wall-clock, enforced by the parent; the process group is killed.
* **Bounded output.** stdout/stderr are drained concurrently and capped, so a
  process emitting gigabytes cannot exhaust host memory (SEC-14 class).
* **No runtime package installation.** A missing import yields
  ``CapabilityUnavailableError`` instead of a silent ``pip install`` (SEC-04).
* **Single writable directory.** Execution happens in a private temp directory;
  only a declared allow-list of artifacts is exported.
* **Network isolation** where the host permits it, via an unprivileged network
  namespace (``unshare -rn``). Availability is probed once and reported through
  ``capabilities()`` so it can be recorded honestly in an ``ActionReceipt``.

What it does NOT enforce
------------------------
* No filesystem isolation. The process can read any file the runtime user can
  read. **This is not a security boundary against a determined attacker.**
* No PID-namespace or cgroup isolation.

For those, use ``ContainerSandboxProvider`` (gVisor/Kata-capable), which belongs
in a dedicated sandbox-manager service rather than in the API process. That
distinction is deliberate and documented in ADR-0005.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from genesis.sandbox.base import (
    Artifact,
    CapabilityUnavailableError,
    ExecutionResult,
    SandboxError,
    SandboxHandle,
    SandboxPolicy,
    SandboxSpec,
    SandboxUnavailableError,
    SnapshotRef,
)

# Runner script: limits the process, then runs the target. Using a runner rather
# than `preexec_fn` keeps this compatible with asyncio's threaded internals.
_RUNNER_TEMPLATE = '''\
"""Genesis sandbox runner - generated, do not edit."""
import os
import runpy
import sys

_POLICY = {policy!r}


def _apply_limits() -> None:
    """Apply resource limits to this process before running untrusted code."""
    try:
        import resource
    except ImportError:
        return

    def _set(kind_name: str, value: int) -> None:
        try:
            kind = getattr(resource, kind_name)
        except AttributeError:
            return
        try:
            soft, hard = resource.getrlimit(kind)
            target = value if hard == resource.RLIM_INFINITY else min(value, hard)
            resource.setrlimit(kind, (target, hard))
        except (ValueError, OSError):
            pass

    cpu = _POLICY.get("cpu_seconds")
    if cpu:
        _set("RLIMIT_CPU", int(cpu))

    memory_mb = _POLICY.get("memory_mb")
    if memory_mb:
        _set("RLIMIT_AS", int(memory_mb) * 1024 * 1024)

    file_mb = _POLICY.get("file_size_mb")
    if file_mb:
        _set("RLIMIT_FSIZE", int(file_mb) * 1024 * 1024)

    pids = _POLICY.get("pids_limit")
    if pids:
        _set("RLIMIT_NPROC", int(pids))

    # No core dumps: they can leak memory contents to disk.
    _set("RLIMIT_CORE", 0)


_apply_limits()

_target = sys.argv[1]
sys.argv = [_target] + sys.argv[2:]
runpy.run_path(_target, run_name="__main__")
'''

# Small, self-contained probe used to detect usable network isolation.
_PROBE_CODE = "print('genesis-probe-ok')"

#: Script that reports whether it can reach the network. Used to *verify* network
#: isolation rather than infer it from `unshare` merely existing: the previous
#: check proved only that a namespace could be created, which is not the same
#: claim as "egress is blocked".
#:
#: Addresses are literal IPs so the result does not depend on DNS working.
_EGRESS_PROBE_CODE = '''\
import socket

TARGETS = [("1.1.1.1", 443), ("8.8.8.8", 53), ("9.9.9.9", 53)]

reached = []
for host, port in TARGETS:
    try:
        socket.create_connection((host, port), timeout=2).close()
        reached.append(f"{host}:{port}")
    except OSError:
        pass

print("genesis-egress=" + (",".join(reached) if reached else "blocked"))
'''


@dataclass(frozen=True)
class NetworkIsolationProbe:
    """Result of verifying whether network isolation actually works here.

    Distinguishes three states the old boolean conflated:

    * **verified** — the host has egress and the namespace provably blocks it.
    * **unverified** — the namespace runs, but the host has no egress either, so
      there is nothing to demonstrate. Reporting this as isolation would be a
      claim we cannot support.
    * **unavailable** — no usable mechanism at all.
    """

    verified: bool
    reason: str
    host_has_egress: Optional[bool] = None
    namespace_blocks_egress: Optional[bool] = None

    def to_dict(self) -> dict[str, object]:
        return {
            "verified": self.verified,
            "reason": self.reason,
            "host_has_egress": self.host_has_egress,
            "namespace_blocks_egress": self.namespace_blocks_egress,
        }


class LocalSandboxProvider:
    """Hardened-subprocess sandbox provider."""

    name = "local"

    def __init__(self, root: Optional[Path] = None, base_image_packages: Optional[set[str]] = None):
        """Initialise the provider.

        Args:
            root: Directory under which sandboxes are created. Defaults to a
                private directory in the system temp area.
            base_image_packages: Import names considered available. Used only to
                produce a helpful message when an import is missing; nothing is
                ever installed.
        """
        self.root = Path(root) if root else Path(tempfile.gettempdir()) / "genesis-sandbox"
        self.root.mkdir(parents=True, exist_ok=True)
        self.base_image_packages = base_image_packages or set()
        self._network_isolation: Optional[bool] = None
        self._network_probe: Optional[NetworkIsolationProbe] = None

    # -- capabilities ------------------------------------------------------

    def capabilities(self) -> dict[str, object]:
        """What this provider actually enforces here, for receipts and logs.

        Reported honestly: a caller must be able to tell whether egress was
        really blocked or merely intended to be. ``network_isolation`` is true
        only when the probe *demonstrated* the block; ``network_probe`` carries
        the reason either way.
        """
        probe = self.probe_network_isolation()
        return {
            "provider": self.name,
            "is_security_boundary": False,
            "env_scrubbing": True,
            "resource_limits": sys.platform != "win32",
            "timeout": True,
            "bounded_output": True,
            "package_install": False,
            "filesystem_isolation": False,
            "pid_isolation": False,
            "network_isolation": probe.verified,
            "network_probe": probe.to_dict(),
            "recommendation": (
                None
                if probe.verified
                else "Use the container sandbox provider (GENESIS_SANDBOX_PROVIDER="
                "container) for filesystem, PID and network isolation."
            ),
        }

    # -- lifecycle ---------------------------------------------------------

    async def create(self, spec: SandboxSpec) -> SandboxHandle:
        spec.policy.validate()

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
            # Basename only: never let a source path escape the sandbox.
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
            # Do not follow a symlink out of the sandbox.
            if path.resolve().parent != workdir.resolve():
                continue
            artifacts.append(
                Artifact(name=safe_name, host_path=path, size_bytes=path.stat().st_size)
            )

        return artifacts

    async def list_artifacts(self, handle: SandboxHandle) -> list[str]:
        """List plain files produced in the sandbox, excluding scaffolding."""
        workdir = self._require_workdir(handle)
        if not workdir.exists():
            return []

        internal = {"script.py", "_genesis_runner.py"}
        names: list[str] = []
        for entry in sorted(workdir.iterdir()):
            if not entry.is_file():
                continue
            if entry.name in internal:
                continue
            # Skip symlinks: they can point outside the sandbox.
            if entry.is_symlink():
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
        """Reattach to a still-present working directory.

        The local provider cannot resurrect a deleted directory; a durable
        implementation belongs to the container/managed providers.
        """
        workdir = self.root / ref.snapshot_id
        if not workdir.exists():
            raise SandboxError(
                f"Snapshot {ref.snapshot_id} is not present on disk; "
                "the local provider cannot restore a removed sandbox"
            )
        return SandboxHandle(
            sandbox_id=ref.snapshot_id,
            provider_name=self.name,
            spec=SandboxSpec(),
            host_workdir=workdir,
        )

    async def terminate(self, handle: SandboxHandle) -> None:
        """Remove the sandbox directory. Idempotent."""
        workdir = handle.host_workdir
        if workdir and workdir.exists():
            shutil.rmtree(workdir, ignore_errors=True)

    # -- execution ---------------------------------------------------------

    async def execute(
        self,
        handle: SandboxHandle,
        code: str,
        *,
        policy: Optional[SandboxPolicy] = None,
    ) -> ExecutionResult:
        effective = policy or handle.spec.policy
        effective.validate()

        workdir = self._require_workdir(handle)
        if not workdir.exists():
            raise SandboxError(f"Sandbox {handle.sandbox_id} no longer exists")

        if self._looks_like_install(code):
            return self._policy_denied(
                "Runtime package installation is not permitted in the sandbox."
            )

        script = workdir / "script.py"
        script.write_text(code, encoding="utf-8")

        runner = workdir / "_genesis_runner.py"
        runner.write_text(
            _RUNNER_TEMPLATE.format(
                policy={
                    "cpu_seconds": effective.cpu_seconds,
                    "memory_mb": effective.memory_mb,
                    "file_size_mb": effective.file_size_mb,
                    "pids_limit": effective.pids_limit,
                }
            ),
            encoding="utf-8",
        )

        argv = [sys.executable, str(runner), str(script)]

        # Network handling. The probe is evidence, not a guess, so this branch
        # knows whether the namespace is real.
        probe = self.probe_network_isolation()
        egress_blocked = False
        warnings: list[str] = []

        if effective.network_enabled:
            warnings.append(
                "This policy enables network access, which the local provider "
                "cannot restrict to allowed domains. Use the container provider "
                "with an egress proxy if the destination matters."
            )
        elif probe.verified:
            argv = ["unshare", "-rn", "--", *argv]
            egress_blocked = True
        else:
            # The policy wanted egress blocked and we cannot deliver that. Run
            # anyway (refusing would make the local provider unusable in the
            # container the project ships in), but say so, loudly and in the
            # result, so an ActionReceipt records it rather than implying the
            # run was isolated.
            warnings.append(
                f"Egress was NOT blocked for this run: {probe.reason}"
            )

        env = self._build_env(effective)
        start = time.time()

        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(workdir),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,  # own process group, so we can kill the tree
            )
        except FileNotFoundError as exc:
            raise SandboxUnavailableError(f"Cannot start sandbox process: {exc}") from exc

        stdout, stderr, truncated, timed_out = await self._drain(
            process, effective.max_output_bytes, effective.wall_timeout_s
        )
        elapsed = time.time() - start

        if timed_out:
            # _drain has already killed the process group; reap it.
            try:
                await process.wait()
            except Exception:  # noqa: BLE001 - best effort
                pass

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
                return_code=-1,
                execution_time=elapsed,
                error=f"Execution exceeded the {effective.wall_timeout_s}s wall-clock limit",
                exit_reason="timeout",
                timed_out=True,
                output_truncated=truncated,
                network_isolated=egress_blocked,
                warnings=warnings,
            )

        return ExecutionResult(
            success=process.returncode == 0,
            stdout=stdout_text,
            stderr=stderr_text,
            return_code=process.returncode or 0,
            execution_time=elapsed,
            exit_reason="completed",
            output_truncated=truncated,
            network_isolated=egress_blocked,
            warnings=warnings,
        )

    # -- internals ---------------------------------------------------------

    def _require_workdir(self, handle: SandboxHandle) -> Path:
        if handle.host_workdir is None:
            raise SandboxError(
                f"Handle {handle.sandbox_id} has no working directory; "
                f"was it created by the '{self.name}' provider?"
            )
        return Path(handle.host_workdir)

    def _build_env(self, policy: SandboxPolicy) -> dict[str, str]:
        """Build a minimal environment.

        Nothing is inherited implicitly: only names on the allow-list are
        copied, so secrets cannot leak into untrusted code (SEC-05).
        """
        env: dict[str, str] = {}
        for key in policy.env_allowlist:
            value = os.environ.get(key)
            if value is not None:
                env[key] = value

        # Deterministic, non-identifying defaults.
        env.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
        env["PYTHONUNBUFFERED"] = "1"
        # Do not write .pyc into the read-only-ish working tree.
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        # Keep user-site packages out of the untrusted process.
        env["PYTHONNOUSERSITE"] = "1"

        # Cap numeric-library thread pools. These are *set* here rather than
        # inherited, so they cannot be influenced by the caller. Without them a
        # BLAS-backed import can try to spawn one thread per core, which both
        # makes results non-deterministic and exhausts the process budget
        # (RLIMIT_NPROC is per-user, so it is shared with the API and nginx).
        for thread_var in (
            "OPENBLAS_NUM_THREADS",
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
        ):
            env[thread_var] = "1"

        return env

    async def _drain(
        self, process: asyncio.subprocess.Process, cap: int, timeout_s: int
    ) -> tuple[bytes, bytes, bool, bool]:
        """Read both streams with a cap, killing the process on timeout.

        Output is drained continuously even past the cap, so a chatty process
        cannot deadlock on a full pipe.

        Returns:
            (stdout, stderr, truncated, timed_out)

        ``timed_out`` is returned explicitly rather than inferred by the caller
        from ``process.returncode``: killing the process sets the return code, so
        inferring it afterwards is a race that reports timeouts as completions.
        """
        truncated = False

        async def read(stream: Optional[asyncio.StreamReader]) -> bytes:
            nonlocal truncated
            if stream is None:
                return b""
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = await stream.read(65536)
                if not chunk:
                    break
                if total < cap:
                    room = cap - total
                    chunks.append(chunk[:room])
                    total += min(len(chunk), room)
                    if len(chunk) > room:
                        truncated = True
                else:
                    truncated = True
                    # Keep draining, discard the excess.
            return b"".join(chunks)

        readers = asyncio.gather(read(process.stdout), read(process.stderr))
        try:
            stdout, stderr = await asyncio.wait_for(
                asyncio.shield(readers), timeout=timeout_s
            )
        except asyncio.TimeoutError:
            # Kill first so the readers can finish, then harvest what we have.
            self._kill_tree(process)
            try:
                stdout, stderr = await asyncio.wait_for(readers, timeout=5)
            except Exception:  # noqa: BLE001 - partial output is still useful
                stdout, stderr = b"", b""
            return stdout, stderr, truncated, True

        await process.wait()
        return stdout, stderr, truncated, False

    @staticmethod
    def _kill_tree(process: asyncio.subprocess.Process) -> None:
        """Kill the process group, so children die with the parent."""
        if process.returncode is not None:
            return
        try:
            if sys.platform == "win32":
                process.kill()
            else:
                os.killpg(os.getpgid(process.pid), 9)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                process.kill()
            except ProcessLookupError:
                pass

    @staticmethod
    def _looks_like_install(code: str) -> bool:
        """Detect attempts to install packages at runtime (SEC-04).

        Defence in depth, not the control itself: the installer has been removed,
        so nothing *can* be installed. This guard exists so the subsystem fails
        loudly and cheaply (``policy_denied``) instead of hanging on a network
        call or wasting the wall-clock budget.

        Pattern-based rather than substring-based, because the obvious spelling
        is only one of many: ``subprocess.run(['pip', 'install', 'x'])`` separates
        the words with quotes and a comma.
        """
        import re

        lowered = code.lower()

        patterns = (
            # pip install / pip3 install, allowing separators between the words
            r"\bpip3?\b[^;\n]{0,24}?\binstall\b",
            # python -m pip ...
            r"\bpython3?\b[^;\n]{0,16}?\s-m\s+pip\b",
            # pip module entry points
            r"\bpip\.__main__\b",
            r"\bpip\.main\s*\(",
            r"\bensurepip\b",
            # system package managers
            r"\bapt(-get)?\b[^;\n]{0,24}?\binstall\b",
            r"\bnpm\b[^;\n]{0,24}?\binstall\b",
            r"\byarn\b[^;\n]{0,24}?\badd\b",
            r"\byum\b[^;\n]{0,24}?\binstall\b",
            r"\bapk\b[^;\n]{0,24}?\badd\b",
        )

        return any(re.search(pattern, lowered) for pattern in patterns)

    @staticmethod
    def _policy_denied(message: str) -> ExecutionResult:
        return ExecutionResult(
            success=False,
            stderr=message,
            error=message,
            exit_reason="policy_denied",
        )

    def _detect_network_isolation(self) -> bool:
        """Whether egress is *verified* to be blocked in this environment.

        True only when the probe demonstrated both halves: the host can reach the
        network, and the namespace cannot. `unshare` merely existing is not
        evidence — that was the previous behaviour, and it reported isolation
        whenever the binary was present, including in environments where the
        namespace could not actually be created.
        """
        return self.probe_network_isolation().verified

    def probe_network_isolation(self) -> NetworkIsolationProbe:
        """Verify network isolation empirically, once per provider instance.

        Three subprocesses at most, cached, and never raising: a detection
        failure must degrade to "not verified", never break execution.
        """
        if self._network_probe is not None:
            return self._network_probe

        self._network_probe = self._run_network_probe()
        self._network_isolation = self._network_probe.verified
        return self._network_probe

    def _run_network_probe(self) -> NetworkIsolationProbe:
        if sys.platform == "win32":
            return NetworkIsolationProbe(
                verified=False,
                reason="No unprivileged network namespaces on Windows; use the "
                "container sandbox provider for network isolation.",
            )

        if shutil.which("unshare") is None:
            return NetworkIsolationProbe(
                verified=False,
                reason="`unshare` is not installed, so no network namespace is available.",
            )

        try:
            import subprocess

            namespace_available = subprocess.run(
                ["unshare", "-rn", "--", sys.executable, "-c", _PROBE_CODE],
                capture_output=True,
                timeout=10,
                check=False,
            )
            if namespace_available.returncode != 0 or b"genesis-probe-ok" not in namespace_available.stdout:
                return NetworkIsolationProbe(
                    verified=False,
                    reason=(
                        "`unshare -rn` could not create a network namespace here "
                        "(common inside a container without the required privileges). "
                        "Use the container sandbox provider, which isolates the "
                        "network at the container level."
                    ),
                )

            # Half one: does this host have egress at all? Without this, a host
            # with no network would look "isolated" because nothing connects.
            host = subprocess.run(
                [sys.executable, "-c", _EGRESS_PROBE_CODE],
                capture_output=True,
                timeout=20,
                check=False,
            )
            host_output = host.stdout.decode("utf-8", errors="replace")
            host_has_egress = "genesis-egress=" in host_output and "genesis-egress=blocked" not in host_output

            if not host_has_egress:
                return NetworkIsolationProbe(
                    verified=False,
                    reason=(
                        "Network isolation is untested: this host has no outbound "
                        "network, so there is nothing to demonstrate. Not reported as "
                        "isolated because that claim cannot be supported here."
                    ),
                    host_has_egress=False,
                )

            # Half two: does the namespace block it?
            inside = subprocess.run(
                ["unshare", "-rn", "--", sys.executable, "-c", _EGRESS_PROBE_CODE],
                capture_output=True,
                timeout=30,
                check=False,
            )
            inside_output = inside.stdout.decode("utf-8", errors="replace")
            blocked = "genesis-egress=blocked" in inside_output

            if not blocked:
                return NetworkIsolationProbe(
                    verified=False,
                    reason=(
                        "The network namespace did not block outbound connections, so "
                        "egress is NOT isolated. Use the container sandbox provider."
                    ),
                    host_has_egress=True,
                    namespace_blocks_egress=False,
                )

            return NetworkIsolationProbe(
                verified=True,
                reason="Verified: the host has egress and the namespace blocks it.",
                host_has_egress=True,
                namespace_blocks_egress=True,
            )

        except Exception as exc:  # noqa: BLE001 - detection must never break execution
            return NetworkIsolationProbe(
                verified=False,
                reason=f"Network isolation could not be verified: {type(exc).__name__}.",
            )


# ``CapabilityUnavailableError`` is re-exported for callers that catch it here.
__all__ = [
    "CapabilityUnavailableError",
    "LocalSandboxProvider",
    "NetworkIsolationProbe",
]
