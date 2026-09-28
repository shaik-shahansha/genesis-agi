"""Sandbox provider selection.

One place decides which provider is active, so a misconfiguration cannot
silently downgrade to an unsandboxed execution path.

Three providers, in increasing strength:

``fake``
    Executes nothing. Test/development only.
``local``
    Hardened subprocess. Enforces environment scrubbing, resource limits,
    timeouts, bounded output and artifact control — but **no filesystem, PID or
    (reliably) network isolation**. Reports that honestly via ``capabilities()``.
``container``
    Hardened container. Real filesystem/PID/cgroup/network isolation, plus an
    optional kernel boundary via gVisor or Kata. Fails closed if the runtime is
    unavailable.

Guard on downgrade: if ``container`` is requested but the runtime is unusable,
selection raises rather than falling back to ``local``. A silent, security-
relevant downgrade is exactly the failure mode this module exists to prevent.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from genesis.sandbox.base import SandboxError, SandboxProvider
from genesis.sandbox.fake import FakeSandboxProvider
from genesis.sandbox.local import LocalSandboxProvider

logger = logging.getLogger(__name__)

_provider: Optional[SandboxProvider] = None

VALID_PROVIDERS = ("local", "fake", "container")
#: Environments in which the fake provider is permitted.
_FAKE_ALLOWED_ENVS = ("test", "development")


def _resolve_name(explicit: Optional[str] = None) -> str:
    return (explicit or os.environ.get("GENESIS_SANDBOX_PROVIDER") or "local").strip().lower()


def _resolve_container_runtime() -> tuple[Optional[str], bool]:
    """Container runtime to request, and whether a kernel boundary is required.

    Read from the environment so an operator chooses the isolation level at
    deploy time rather than having it guessed from whatever happens to be
    installed.
    """
    runtime = (
        os.environ.get("GENESIS_SANDBOX_RUNTIME", "").strip().lower() or None
    )
    require_isolation = os.environ.get(
        "GENESIS_SANDBOX_REQUIRE_ISOLATION_RUNTIME", ""
    ).strip().lower() in ("1", "true", "yes", "on")

    # If an operator asks for a kernel boundary without naming a runtime, prefer
    # gVisor then Kata over silently running on runc.
    if runtime is None and require_isolation:
        runtime = "runsc"

    return runtime, require_isolation


def get_sandbox_provider(explicit: Optional[str] = None) -> SandboxProvider:
    """Return the configured sandbox provider (cached per process).

    Args:
        explicit: Override the configured provider. Used by tests.

    Raises:
        SandboxError: if the requested provider is unknown, if the fake provider
            is requested outside a test/development environment, or if the
            container provider is requested but its runtime is unusable. In the
            last case there is deliberately **no** fallback to ``local``.
    """
    global _provider

    name = _resolve_name(explicit)

    if name not in VALID_PROVIDERS:
        raise SandboxError(
            f"Unknown sandbox provider '{name}'. Valid options: {', '.join(VALID_PROVIDERS)}"
        )

    if name == "fake":
        env = os.environ.get("GENESIS_ENV", "").strip().lower()
        if env not in _FAKE_ALLOWED_ENVS:
            raise SandboxError(
                "The fake sandbox provider executes nothing and must not be used outside "
                f"test/development environments (GENESIS_ENV is '{env or 'unset'}'). "
                "Set GENESIS_SANDBOX_PROVIDER=local instead."
            )

    if _provider is not None and getattr(_provider, "name", None) == name:
        return _provider

    if name == "fake":
        _provider = FakeSandboxProvider()
    elif name == "container":
        # Imported lazily so the local/fake paths never require a container CLI.
        from genesis.sandbox.container import (
            ContainerSandboxProvider,
            SandboxRuntimeUnavailable,
        )

        runtime, require_isolation = _resolve_container_runtime()
        candidate = ContainerSandboxProvider(
            image=os.environ.get("GENESIS_SANDBOX_IMAGE", "genesis-sandbox:latest"),
            runtime=runtime,
            require_isolation_runtime=require_isolation,
        )

        # Probe now, at selection time, so a broken runtime is a startup failure
        # rather than a surprise on the first untrusted execution.
        try:
            candidate._require_runtime()
        except SandboxRuntimeUnavailable as exc:
            raise SandboxError(
                f"GENESIS_SANDBOX_PROVIDER=container was requested but the container "
                f"runtime is unusable: {exc} "
                "Refusing to fall back to the local provider, which is not a security "
                "boundary. Fix the runtime, or set GENESIS_SANDBOX_PROVIDER=local "
                "knowingly."
            ) from exc

        logger.info(
            "container sandbox provider active: image=%s runtime=%s",
            candidate.image,
            runtime or "daemon-default",
        )
        _provider = candidate
    else:
        _provider = LocalSandboxProvider()

    return _provider


def reset_sandbox_provider() -> None:
    """Clear the cached provider. Intended for tests."""
    global _provider
    _provider = None


__all__ = ["VALID_PROVIDERS", "get_sandbox_provider", "reset_sandbox_provider"]
