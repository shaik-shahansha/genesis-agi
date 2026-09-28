# ADR-0005 — Sandbox isolation for all untrusted execution

- **Status:** Accepted
- **Date:** 2026-09-28
- **Related:** ADR-0006, ADR-0007, ADR-0008, ADR-0017
- **Security refs:** `SECURITY_BASELINE.md` SEC-03, SEC-04, SEC-06; `THREAT_MODEL.md` T-02, T-03, T-04

## Context

Genesis executes **model-generated code**. There are three independent execution paths, all
unsandboxed:

| Path | Mechanism | Verified line |
|---|---|---|
| Autonomous agent | `asyncio.create_subprocess_exec(python, script, cwd=tmpdir)` | `core/code_executor.py:155` |
| Tool code | `subprocess.run(['python3', tmp], preexec_fn=None)` | `core/tools.py:364` |
| Tool plugin | `subprocess.run(["python3", tmp])` | `plugins/tools.py:244` |

Confirmed deficiencies:

1. **No isolation.** No container, no seccomp/AppArmor, no namespaces, no cgroups. The child
   process inherits the parent's filesystem, network, and **entire environment** (all provider
   API keys).
2. **No resource limits.** The docstring admits it: *"2. Resource limits (future) … 4. No
   network access by default (future)"*. Comment on the `subprocess.run` call:
   *"Could add resource limits here"* — `preexec_fn=None`.
3. **Runtime package installation.** `_ensure_dependencies_installed()` runs
   `pip install -q {package}` where `{package}` is regex-extracted from model output. A model can
   therefore install an arbitrary PyPI package; package names are also interpolated into a `-c`
   string.
4. **An advertised control that does not exist.** `plugins/tools.py:188` emits
   `ALLOWED_IMPORTS = {...}` into generated code and **never consults it**. There is no
   `__import__` hook, no meta-path finder, no `__builtins__` restriction.
5. **Docker is a probe, not a provider.** `_docker_available()` runs `docker --version` and the
   result is unused; `code_executor.py:95` says *"For now, use subprocess (Docker support later)"*.
6. **Platform inconsistency.** Two paths invoke the literal `python3`, one invokes `python`, and
   execution is therefore ungovernable from any single place.

This is the single largest blocker: it prevents enterprise adoption and makes any physical
embodiment unsafe by construction.

## Decision

**All untrusted execution goes through a Genesis-owned `SandboxProvider` interface. Generated
code never executes inside the API, web, cognition, scheduler, or workflow process.**

### Interface

```python
class SandboxProvider(Protocol):
    async def create(self, spec: SandboxSpec) -> SandboxHandle: ...
    async def execute(self, handle, command, *, timeout, env, cwd) -> ExecutionResult: ...
    async def upload(self, handle, files) -> None: ...
    async def download(self, handle, declared_artifacts) -> list[Artifact]: ...
    async def snapshot(self, handle) -> SnapshotRef: ...
    async def restore(self, ref: SnapshotRef) -> SandboxHandle: ...
    async def terminate(self, handle) -> None: ...
```

### Mandatory controls (non-negotiable minimum)

| Control | Requirement |
|---|---|
| User | non-root |
| Filesystem | read-only base; exactly one temporary writable directory |
| Network | **disabled by default**; egress only via an allow-list proxy |
| Limits | CPU quota, memory cap, PID limit, disk quota, file-size cap, output-size cap, wall-clock timeout |
| Namespaces | no host PID namespace, no host network, no device mounts |
| Docker socket | **never mounted** |
| Environment | explicit allow-list of variables; never blanket `os.environ` |
| Secrets | passed as references resolved at the boundary, never in argv, prompts, logs, or files |
| Artifacts | only **declared** artifacts are exported |
| Lifecycle | terminate + clean up after every run unless an authorized checkpoint exists |
| Idempotency | repeated execution with the same key does not duplicate side effects |

### Additional decisions

1. **Runtime package installation is removed.** Replace with pre-baked tool images and a declared
   capability list. `CapabilityUnavailable` is a typed, expected error — not a silent `pip`.
2. **The fake/isolated-import restriction claim is deleted, not faked.** Restrictions are enforced
   by isolating filesystem and network, not by naming allowed imports.
3. **One interpreter, one entry point.** All three legacy paths become thin calls into the
   provider, preserving their public method signatures.
4. **Provider tiers, same interface:** local container (first, works on a single VPS) → gVisor →
   Kata → Firecracker → managed secure sandbox. Advanced providers are **not** required for local
   development.
5. **An in-process fake provider exists for tests**, so the suite is hermetic and needs no Docker.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Keep subprocess, add `resource.setrlimit` + `preexec_fn` | Linux-only, no filesystem/network isolation, trivially bypassed; does not address package installation |
| Restricted-Python (`ast` allow-list, no `__builtins__`) | Escapes are routine; and the task needs real libraries (pandas, matplotlib), which a restricted interpreter defeats |
| Docker-only, hardcoded | Couples the core to one runtime; blocks local dev without a daemon; V3 §5.18 forbids binding to one implementation |
| Remote managed sandbox as the only path | Adds a network dependency and cost for local/edge deployments; conflicts with the sovereignty story |
| WASM/Pyodide sandbox | Cannot run the required native scientific stack reliably today |
| **Do nothing until later** | Explicitly rejected: V3 §6 makes this the first priority, and everything after it (autonomy, voice, embodiment) is unsafe while it stands |

## Consequences

**Positive**
- Removes the host-compromise, credential-theft, and supply-chain vectors in one place.
- Makes policy governance meaningful: `PolicyService` (ADR-0006) has a real containment primitive
  to allow or deny.
- Unlocks enterprise conversations and is a prerequisite for embodiment (ADR-0012).
- Removes an unbounded dependency surface: a Mind's dependency set becomes declared, not open-ended.

**Negative / costs**
- Real latency and complexity per execution (container start, image management).
- Some capabilities become unavailable or require a declared image (e.g. an exotic library needs
  a new tool image rather than an on-the-fly install).
- Requires a snapshot/restore design for persistent workspaces (Phase H).

## Risks

| Risk | Mitigation |
|---|---|
| Container escape via kernel/runtime CVE | Provider tiers allow gVisor/Kata without changing call sites; keep base images pinned and scanned |
| Operators run the container provider with `--privileged` "to make it work" | Document as forbidden; assert non-privileged in provider startup checks and tests |
| Latency regressions break the agent loop | Warm pool of sandboxes; snapshot/restore for iterative work; measure in evals (B18) |
| Egress allow-list becomes an open door | Deny by default; require per-destination justification; log every allowed egress |
| Migration leaves one path unsandboxed | Test asserts *no* `subprocess` call sites exist outside `genesis/sandbox/` |

## Reversibility

**Low for the decision, high for the implementation.** The *requirement* to sandbox is not
reversible (removing it re-introduces remote code execution on the host). But the provider is
swappable behind the interface, and a feature flag can keep the legacy executor callable for one
release during migration — **never in production defaults**.

## Migration effect

- Plan items **B1–B6** (provider, container impl, routing, no-pip, egress-off, artifact export).
- `deploy/docker/entrypoint.sh` currently starts a single container with the API and nginx; a
  hardened executor implies a **separate** container/namespace for untrusted execution. Because
  the single-container deployment (ADR-0017) is a deployment convenience and not a security
  boundary, this must be stated plainly in the deployment docs until Phase B lands.
- Alembic/audit implications: every execution produces an `ActionReceipt` (ADR-0008).
