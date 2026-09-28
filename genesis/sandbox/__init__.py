"""Sandbox providers for untrusted execution.

All model-generated code and third-party tool code must execute through a
``SandboxProvider``. Direct ``subprocess`` use for untrusted code is forbidden
outside this package (see docs/architecture/adr/ADR-0005-sandbox-isolation.md).

Providers, in increasing isolation strength:

* ``FakeSandboxProvider``     - records requests, executes nothing. Tests only.
* ``LocalSandboxProvider``    - hardened subprocess: scrubbed environment,
                                resource limits, timeout, output caps, no
                                runtime package installation.
* ``ContainerSandboxProvider``- hardened container (gVisor/Kata compatible).
                                Requires a Docker endpoint, so it belongs in a
                                dedicated sandbox-manager service rather than in
                                the API process.
"""

from genesis.sandbox.base import (
    Artifact,
    CapabilityUnavailableError,
    ExecutionResult,
    SandboxError,
    SandboxHandle,
    SandboxPolicy,
    SandboxPolicyError,
    SandboxProvider,
    SandboxResourceError,
    SandboxSpec,
    SandboxTimeoutError,
    SandboxUnavailableError,
    SnapshotRef,
)
from genesis.sandbox.factory import get_sandbox_provider, reset_sandbox_provider

__all__ = [
    "Artifact",
    "CapabilityUnavailableError",
    "ExecutionResult",
    "SandboxError",
    "SandboxHandle",
    "SandboxPolicy",
    "SandboxPolicyError",
    "SandboxProvider",
    "SandboxResourceError",
    "SandboxSpec",
    "SandboxTimeoutError",
    "SandboxUnavailableError",
    "SnapshotRef",
    "get_sandbox_provider",
    "reset_sandbox_provider",
]
