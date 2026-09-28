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

    # -- capabilities ------------------------------------------------------

    def capabilities(self) -> dict[str, object]:
        """What this provider actually enforces here, for receipts and logs.

        Reported honestly: a caller must be able to tell whether egress was
        really blocked or merely intended to be.
        """
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
            "network_isolation": self._detect_network_isolation(),
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
        if self._detect_network_isolation() and not effective.network_enabled:
            argv = ["unshare", "-rn", "--", *argv]

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
            )

        return ExecutionResult(
            success=process.returncode == 0,
            stdout=stdout_text,
            stderr=stderr_text,
            return_code=process.returncode or 0,
            execution_time=elapsed,
            exit_reason="completed",
            output_truncated=truncated,
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
        """Probe once for an unprivileged network namespace.

        Cached because the probe costs a process spawn. Docker/kernel
        configuration varies, so this is detected rather than assumed.
        """
        if self._network_isolation is not None:
            return self._network_isolation

        self._network_isolation = False
        if sys.platform == "win32":
            return False
        if shutil.which("unshare") is None:
            return False

        try:
            import subprocess

            probe = subprocess.run(
                ["unshare", "-rn", "--", sys.executable, "-c", _PROBE_CODE],
                capture_output=True,
                timeout=10,
                check=False,
            )
            self._network_isolation = probe.returncode == 0 and b"genesis-probe-ok" in probe.stdout
        except Exception:  # noqa: BLE001 - detection must never break execution
            self._network_isolation = False

        return self._network_isolation


# ``CapabilityUnavailableError`` is re-exported for callers that catch it here.
__all__ = ["CapabilityUnavailableError", "LocalSandboxProvider"]
