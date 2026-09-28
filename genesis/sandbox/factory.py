"""Sandbox provider selection.

One place decides which provider is active, so a misconfiguration cannot
silently downgrade to an unsandboxed execution path.
"""

from __future__ import annotations

import os
from typing import Optional

from genesis.sandbox.base import SandboxError, SandboxProvider
from genesis.sandbox.fake import FakeSandboxProvider
from genesis.sandbox.local import LocalSandboxProvider

_provider: Optional[SandboxProvider] = None

VALID_PROVIDERS = ("local", "fake")
#: Environments in which the fake provider is permitted.
_FAKE_ALLOWED_ENVS = ("test", "development")


def _resolve_name(explicit: Optional[str] = None) -> str:
    return (explicit or os.environ.get("GENESIS_SANDBOX_PROVIDER") or "local").strip().lower()


def get_sandbox_provider(explicit: Optional[str] = None) -> SandboxProvider:
    """Return the configured sandbox provider (cached per process).

    Args:
        explicit: Override the configured provider. Used by tests.

    Raises:
        SandboxError: if the requested provider is unknown, or if the fake
            provider is requested outside a test/development environment.
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

    if _provider is None or getattr(_provider, "name", None) != name:
        if name == "fake":
            _provider = FakeSandboxProvider()
        else:
            _provider = LocalSandboxProvider()

    return _provider


def reset_sandbox_provider() -> None:
    """Clear the cached provider. Intended for tests."""
    global _provider
    _provider = None


__all__ = ["VALID_PROVIDERS", "get_sandbox_provider", "reset_sandbox_provider"]
