#!/usr/bin/env python3
"""Sandbox verification against a running Genesis container.

Proves, inside the real deployment, that untrusted execution is contained:

  1. The sandbox reports its capabilities honestly (no overclaiming).
  2. Provider secrets in the API process are NOT visible to sandboxed code.
  3. Runtime package installation is refused.
  4. The wall-clock timeout is enforced.
  5. Output is bounded.
  6. Declared-artifact export works, and traversal names are refused.
  7. Normal execution still works, so containment did not cost capability.

Usage (from the host):
    docker compose cp deploy/docker/verify_sandbox.py genesis:/tmp/
    docker compose exec genesis python /tmp/verify_sandbox.py

Exit 0 = all assertions held.
"""

from __future__ import annotations

import asyncio
import os
import sys

from genesis.sandbox import SandboxPolicy, SandboxSpec
from genesis.sandbox.factory import get_sandbox_provider

results: list[tuple[bool, str, str]] = []


def record(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""), flush=True)


async def run(provider, code, policy=None):
    handle = await provider.create(SandboxSpec(policy=policy or SandboxPolicy()))
    try:
        return await provider.execute(handle, code, policy=policy)
    finally:
        await provider.terminate(handle)


async def main() -> int:
    provider = get_sandbox_provider()
    print(f"Sandbox provider: {provider.name}\n")

    caps = provider.capabilities() if hasattr(provider, "capabilities") else {}

    # 1. Honest reporting.
    record(
        caps.get("is_security_boundary") is False,
        "capabilities() does not overclaim",
        f"is_security_boundary={caps.get('is_security_boundary')} "
        f"network_isolation={caps.get('network_isolation')} "
        f"resource_limits={caps.get('resource_limits')}",
    )

    # 2. Secrets must not be visible. These are set in the container environment.
    probes = ["OPENROUTER_API_KEY", "API_SECRET_KEY", "GROQ_API_KEY", "FIREBASE_API_KEY"]
    present_parent = [name for name in probes if os.environ.get(name)]
    result = await run(
        provider,
        "import os\nprint('|'.join(sorted(os.environ)))",
    )
    visible = [name for name in probes if name in result.stdout]
    record(
        not visible,
        "provider secrets are not visible to sandboxed code",
        f"parent had {len(present_parent)} secret(s); leaked={visible or 'none'}",
    )

    # 3. No runtime package installation.
    install = await run(
        provider, "import subprocess\nsubprocess.run(['pip', 'install', 'requests'])"
    )
    record(
        install.exit_reason == "policy_denied",
        "runtime package installation is refused",
        f"exit_reason={install.exit_reason}",
    )

    # 4. Timeout.
    timeout = await run(
        provider,
        "import time\nwhile True: time.sleep(0.5)",
        SandboxPolicy(wall_timeout_s=2),
    )
    record(
        timeout.timed_out,
        "wall-clock timeout enforced",
        f"exit_reason={timeout.exit_reason} success={timeout.success} "
        f"rc={timeout.return_code} elapsed={timeout.execution_time:.2f} "
        f"stderr={timeout.stderr[:120]!r}",
    )

    # 5. Bounded output.
    flood = await run(
        provider,
        "import sys\nc='x'*4096\n[sys.stdout.write(c) for _ in range(3000)]",
        SandboxPolicy(max_output_bytes=8192, wall_timeout_s=30),
    )
    record(
        flood.output_truncated and len(flood.stdout) < 8192 + 200,
        "output is bounded",
        f"truncated={flood.output_truncated} bytes={len(flood.stdout)}",
    )

    # 6. Artifact export: declared only, traversal refused.
    handle = await provider.create(SandboxSpec())
    try:
        from pathlib import Path

        workdir = getattr(handle, "host_workdir", None)
        if workdir:
            (Path(workdir) / "report.txt").write_text("ok", encoding="utf-8")
            good = await provider.download(handle, ["report.txt"])
            evil = await provider.download(handle, ["../../etc/passwd", "../escape"])
            record(
                [a.name for a in good] == ["report.txt"] and evil == [],
                "artifact export is declared-only",
                f"exported={[a.name for a in good]} refused={len(evil)}",
            )
        else:
            record(False, "artifact export is declared-only", "no host workdir (container provider?)")
    finally:
        await provider.terminate(handle)

    # 7. Capability preserved: the pre-baked tools extra must be usable.
    library = await run(
        provider,
        "import pandas, matplotlib, openpyxl\nprint('libs-ok', pandas.__version__)",
    )
    record(
        library.success and "libs-ok" in library.stdout,
        "pre-baked libraries are available (capability preserved)",
        library.stdout.strip().splitlines()[-1] if library.stdout.strip() else library.stderr[-160:],
    )

    # 8. Ordinary execution.
    basic = await run(provider, "print('sandbox works')")
    record(basic.success and "sandbox works" in basic.stdout, "ordinary execution works")

    passed = sum(1 for ok, _, _ in results if ok)
    total = len(results)
    print(f"\n{passed}/{total} checks passed")
    if passed != total:
        for ok, name, detail in results:
            if not ok:
                print(f"  - {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
