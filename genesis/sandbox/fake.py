"""Fake sandbox provider for tests and explicit development modes.

Executes nothing. It records what *would* have run and returns a canned result,
so the whole test suite is hermetic: no subprocesses, no containers, no network,
no paid API keys.

Never use this in production. ``get_sandbox_provider`` refuses to select it
unless ``GENESIS_ENV`` is ``test`` or ``development``, so a misconfiguration
fails closed rather than silently executing nothing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from genesis.sandbox.base import (
    Artifact,
    ExecutionResult,
    SandboxError,
    SandboxHandle,
    SandboxPolicy,
    SandboxSpec,
    SnapshotRef,
)


@dataclass
class RecordedExecution:
    """One execution the fake provider was asked to perform."""

    sandbox_id: str
    code: str
    policy: SandboxPolicy
    artifacts: list[str] = field(default_factory=list)


class FakeSandboxProvider:
    """Records executions instead of performing them."""

    name = "fake"

    def __init__(
        self,
        *,
        stdout: str = "",
        stderr: str = "",
        return_code: int = 0,
        artifacts: dict[str, bytes] | None = None,
    ) -> None:
        self.default_stdout = stdout
        self.default_stderr = stderr
        self.default_return_code = return_code
        self.canned_artifacts = artifacts or {}

        self.executions: list[RecordedExecution] = []
        self.created: list[SandboxSpec] = []
        self.terminated: list[str] = []
        self.uploaded: dict[str, list[str]] = {}

    def capabilities(self) -> dict[str, object]:
        return {
            "provider": self.name,
            "is_security_boundary": False,
            "executes_code": False,
            "env_scrubbing": True,
            "resource_limits": True,
            "timeout": True,
            "bounded_output": True,
            "package_install": False,
            "filesystem_isolation": True,
            "pid_isolation": True,
            "network_isolation": True,
        }

    async def create(self, spec: SandboxSpec) -> SandboxHandle:
        spec.policy.validate()
        sandbox_id = f"fake-{uuid.uuid4().hex[:8]}"
        self.created.append(spec)
        return SandboxHandle(
            sandbox_id=sandbox_id,
            provider_name=self.name,
            spec=spec,
            host_workdir=None,
        )

    async def execute(
        self,
        handle: SandboxHandle,
        code: str,
        *,
        policy: SandboxPolicy | None = None,
    ) -> ExecutionResult:
        effective = policy or handle.spec.policy
        effective.validate()

        self.executions.append(
            RecordedExecution(sandbox_id=handle.sandbox_id, code=code, policy=effective)
        )

        artifacts = [
            Artifact(name=name, host_path=None, size_bytes=len(data))
            for name, data in self.canned_artifacts.items()
        ]

        return ExecutionResult(
            success=self.default_return_code == 0,
            stdout=self.default_stdout or '{\n  "result": "fake sandbox output"\n}',
            stderr=self.default_stderr,
            return_code=self.default_return_code,
            execution_time=0.0,
            artifacts=artifacts,
            exit_reason="completed",
        )

    async def upload(self, handle: SandboxHandle, paths: list[Path]) -> None:
        self.uploaded.setdefault(handle.sandbox_id, []).extend(p.name for p in paths)

    async def download(self, handle: SandboxHandle, declared: list[str]) -> list[Artifact]:
        return [
            Artifact(name=name, host_path=None, size_bytes=len(self.canned_artifacts[name]))
            for name in declared
            if name in self.canned_artifacts
        ]

    async def list_artifacts(self, handle: SandboxHandle) -> list[str]:
        return sorted(self.canned_artifacts)

    async def snapshot(self, handle: SandboxHandle) -> SnapshotRef:
        return SnapshotRef(
            snapshot_id=handle.sandbox_id,
            provider_name=self.name,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    async def restore(self, ref: SnapshotRef) -> SandboxHandle:
        if ref.provider_name != self.name:
            raise SandboxError("Snapshot belongs to a different provider")
        return SandboxHandle(
            sandbox_id=ref.snapshot_id,
            provider_name=self.name,
            spec=SandboxSpec(),
            host_workdir=None,
        )

    async def terminate(self, handle: SandboxHandle) -> None:
        self.terminated.append(handle.sandbox_id)


__all__ = ["FakeSandboxProvider", "RecordedExecution"]
