"""Sandbox provider interface and value types.

The interface is deliberately small and provider-neutral so that a local
subprocess implementation, a hardened container (gVisor/Kata/Firecracker) and a
managed remote sandbox are interchangeable.

Design notes
------------
* ``SandboxPolicy`` is data, not behaviour, so it can be persisted, reviewed and
  compared as part of a policy decision (see ADR-0006).
* Limits are always explicit: there is no "unlimited" default for memory, CPU,
  processes, disk or wall time.
* Network access is **off by default**. Enabling it requires naming the
  destinations, which makes the egress surface reviewable.
* ``ExecutionResult`` records *why* something stopped (timeout, limit, policy) so
  the caller can produce an accurate ``ActionReceipt``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SandboxError(Exception):
    """Base class for sandbox failures."""


class SandboxUnavailableError(SandboxError):
    """The provider cannot run at all (no runtime, daemon unreachable, ...).

    Callers must treat this as a hard failure. It is never silently downgraded
    to an unsandboxed execution.
    """


class SandboxTimeoutError(SandboxError):
    """Execution exceeded the wall-clock limit."""


class SandboxResourceError(SandboxError):
    """Execution exceeded a resource limit (memory, CPU, processes, disk)."""


class SandboxPolicyError(SandboxError):
    """The request violates the sandbox policy and was refused before running."""


class CapabilityUnavailableError(SandboxError):
    """The request needs a capability the sandbox does not provide.

    This is the replacement for the previous behaviour of installing packages on
    demand from model-generated import statements (SEC-04). It is a normal,
    expected outcome and callers should report it rather than retry blindly.
    """


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SandboxPolicy:
    """Resource and capability limits for one sandbox.

    Every limit has a finite default. Tighten per capability; widening requires
    an explicit policy decision.
    """

    # Resource limits (per execution unless stated otherwise)
    wall_timeout_s: int = 60
    cpu_seconds: int = 60
    #: Memory ceiling. NOTE: the local provider enforces this with RLIMIT_AS,
    #: which bounds *virtual address space*, not resident memory. Scientific
    #: libraries (numpy/OpenBLAS) reserve large virtual regions, so the ceiling
    #: must leave generous headroom or they abort with allocation errors. Exact
    #: physical-memory control requires cgroup-level limits, i.e. the container
    #: provider.
    memory_mb: int = 2048
    #: Process/thread ceiling.
    #: NOTE: the local provider enforces this with RLIMIT_NPROC, which counts
    #: processes and threads for the whole *user*, not just this sandbox. Because
    #: the API, nginx and the sandbox run as the same user, a low value starves
    #: the sandbox: numeric libraries (OpenBLAS inside numpy) fail to create
    #: threads and abort with SIGINT during import. cgroup-level pids limits,
    #: which are per-container, require the container provider.
    pids_limit: int = 1024
    disk_mb: int = 256
    file_size_mb: int = 64
    max_output_bytes: int = 100_000

    # Networking: disabled unless explicitly allowed
    network_enabled: bool = False
    allowed_domains: tuple[str, ...] = ()

    # Filesystem: a single writable temporary directory, nothing else
    read_only_root: bool = True
    writable_tmp: bool = True

    # Isolation knobs honoured by providers that support them
    run_as_uid: Optional[int] = None
    no_new_privileges: bool = True
    drop_all_capabilities: bool = True

    # Environment: only these variables are passed through. Everything else,
    # including every API key in the parent process, is dropped (SEC-05).
    env_allowlist: tuple[str, ...] = ("PATH", "LANG", "LC_ALL", "TZ", "PYTHONHASHSEED")

    # Package installation is never permitted at runtime (SEC-04).
    allow_package_install: bool = False

    def validate(self) -> None:
        """Reject a policy that would be unsafe or meaningless."""
        if self.wall_timeout_s <= 0:
            raise SandboxPolicyError("wall_timeout_s must be positive")
        if self.wall_timeout_s > 3600:
            raise SandboxPolicyError("wall_timeout_s must not exceed 3600")
        if self.memory_mb < 16:
            raise SandboxPolicyError("memory_mb must be at least 16")
        if self.pids_limit < 1:
            raise SandboxPolicyError("pids_limit must be at least 1")
        if self.allow_package_install:
            raise SandboxPolicyError(
                "Runtime package installation is not permitted. "
                "Use a pre-baked image or declare the capability instead."
            )
        if self.network_enabled and not self.allowed_domains:
            raise SandboxPolicyError(
                "network_enabled requires at least one allowed domain; "
                "unrestricted egress is not supported."
            )


@dataclass
class SandboxSpec:
    """A request to create a sandbox."""

    language: Literal["python"] = "python"
    policy: SandboxPolicy = field(default_factory=SandboxPolicy)
    # Host paths copied into the sandbox before execution.
    files: list[Path] = field(default_factory=list)
    # Opaque caller label, for tracing and receipts.
    label: str = ""


@dataclass
class SandboxHandle:
    """A live sandbox. Obtained from ``SandboxProvider.create``."""

    sandbox_id: str
    provider_name: str
    spec: SandboxSpec
    #: Host directory that mirrors the sandbox working directory, when the
    #: provider is local. Container providers leave this None.
    host_workdir: Optional[Path] = None


@dataclass
class Artifact:
    """A file produced by execution and exported from the sandbox."""

    name: str
    host_path: Optional[Path]
    size_bytes: int


@dataclass
class ExecutionResult:
    """Outcome of one execution. Also the basis of an ``ActionReceipt``."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1
    execution_time: float = 0.0
    error: Optional[str] = None
    artifacts: list[Artifact] = field(default_factory=list)

    # Why it stopped. "completed" means the process finished on its own.
    exit_reason: Literal[
        "completed", "timeout", "resource_limit", "policy_denied", "unavailable", "error"
    ] = "completed"

    timed_out: bool = False
    output_truncated: bool = False

    #: Whether egress was actually blocked for THIS run. ``None`` means the
    #: provider does not isolate the network at all, which is different from
    #: ``False`` (it should have, and did not). Recorded so an ActionReceipt can
    #: state the fact rather than imply it.
    network_isolated: Optional[bool] = None

    #: Non-fatal observations worth recording alongside the outcome, such as
    #: "egress was not blocked because this host has no usable network
    #: namespace". Surfaced instead of being swallowed into a log line.
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "execution_time": self.execution_time,
            "error": self.error,
            "exit_reason": self.exit_reason,
            "timed_out": self.timed_out,
            "output_truncated": self.output_truncated,
            "network_isolated": self.network_isolated,
            "warnings": list(self.warnings),
            "artifacts": [
                {"name": a.name, "size_bytes": a.size_bytes, "host_path": str(a.host_path) if a.host_path else None}
                for a in self.artifacts
            ],
        }


@dataclass
class SnapshotRef:
    """A durable reference to a sandbox state, for resume/rollback."""

    snapshot_id: str
    provider_name: str
    created_at: str  # ISO-8601 UTC


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------


@runtime_checkable
class SandboxProvider(Protocol):
    """Executes untrusted code under a policy.

    Lifecycle: ``create`` -> (``upload``|``execute``)* -> ``terminate``.
    Implementations must clean up in ``terminate`` and must not leave processes
    or containers running.
    """

    #: Stable identifier used in traces, receipts and configuration.
    name: str

    async def create(self, spec: SandboxSpec) -> SandboxHandle:
        """Create an isolated sandbox and its single writable directory."""

    async def execute(
        self,
        handle: SandboxHandle,
        code: str,
        *,
        policy: Optional[SandboxPolicy] = None,
    ) -> ExecutionResult:
        """Run ``code`` (Python source) inside the sandbox.

        Must never raise for an ordinary execution failure; return an
        ``ExecutionResult`` with ``success=False`` and an ``exit_reason``
        instead. Raises only for provider-level faults.
        """

    async def upload(self, handle: SandboxHandle, paths: list[Path]) -> None:
        """Copy host files into the sandbox working directory."""

    async def download(
        self, handle: SandboxHandle, declared: list[str]
    ) -> list[Artifact]:
        """Export **only** the named artifacts out of the sandbox.

        Names are declared by the caller, never self-declared by the code being
        executed, so a runaway process cannot exfiltrate arbitrary files.

        Implementations must reject names that are not bare filenames inside the
        sandbox working directory.
        """

    async def list_artifacts(self, handle: SandboxHandle) -> list[str]:
        """List plain files present in the sandbox working directory.

        Returns bare filenames only, and never includes the sandbox's own
        runner/script scaffolding. Used to discover what a run produced; the
        caller then passes those names to ``download``.
        """

    async def snapshot(self, handle: SandboxHandle) -> SnapshotRef:
        """Persist the sandbox state so it can be resumed later."""

    async def restore(self, ref: SnapshotRef) -> SandboxHandle:
        """Recreate a sandbox from a snapshot."""

    async def terminate(self, handle: SandboxHandle) -> None:
        """Stop the sandbox and remove its resources. Must be idempotent."""
