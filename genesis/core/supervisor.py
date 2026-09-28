"""Mind daemon lifecycle, delegated to an operator-configured supervisor.

**Why this module exists (plan item B11).**

Mind daemons used to be started by the API tier:

```python
subprocess.Popen([sys.executable, "-m", "genesis.daemon", "--mind-id", mind_id],
                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
```

and stopped by scanning the *entire host process table* for anything whose
command line matched `genesis.daemon --mind-id <id>`. Three separate problems:

1. **Process authority in the web tier.** Anything that achieves code execution
   in the API could fork arbitrary processes with the API's privileges. The API
   should describe intent ("start this Mind"), not hold process-control
   authority over the host.
2. **A discarded pipe deadlock.** The child's stdout and stderr were PIPEs that
   nobody ever read. Once the daemon wrote ~64 KB the pipe buffer filled and the
   daemon blocked forever, mid-thought. Daemon logs were also thrown away.
3. **Unbounded targeting.** Killing by pattern-matching the global process table
   is not scoped to anything the API actually owns.

The replacement is a supervisor *interface*. The operator's process manager owns
lifecycle (systemd in the shipped deployment, via
``deployment/systemd/genesis-mind@.service``); the API asks it to act and reports
what it said.

The default backend is :class:`NoSupervisor`, which **refuses with an
explanation** rather than silently falling back to forking. That is deliberate:
a silent fallback would restore the exact behaviour this module removes.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)

__all__ = [
    "SupervisorUnavailable",
    "SupervisorActionError",
    "SupervisorResult",
    "Supervisor",
    "NoSupervisor",
    "SystemdSupervisor",
    "get_supervisor",
    "set_supervisor",
    "reset_supervisor",
    "VALID_SUPERVISORS",
    "SYSTEMD_UNIT_TEMPLATE",
]

#: Matches ``deployment/systemd/genesis-mind@.service``.
SYSTEMD_UNIT_TEMPLATE = "genesis-mind@{mind_id}"

VALID_SUPERVISORS = ("none", "systemd")

#: Bound on how long a supervisor command may take. `systemctl` against a local
#: bus is fast; anything slower means the supervisor itself is unhealthy.
SUPERVISOR_TIMEOUT_SECONDS = 30


class SupervisorUnavailable(RuntimeError):
    """No supervisor is configured, so lifecycle actions cannot be honoured."""


class SupervisorActionError(RuntimeError):
    """The supervisor was reachable but refused or failed the action."""


@dataclass(frozen=True)
class SupervisorResult:
    """Outcome of a lifecycle action, shaped for an HTTP response."""

    ok: bool
    action: str
    backend: str
    detail: str
    #: True when the action could not be attempted because no supervisor is
    #: configured. Distinguishes "refused by policy" from "failed".
    unavailable: bool = False
    pid: Optional[int] = None
    #: For `status`, the raw supervisor view.
    state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "success": self.ok,
            "action": self.action,
            "backend": self.backend,
            "detail": self.detail,
        }
        if self.unavailable:
            payload["unavailable"] = True
        if self.pid is not None:
            payload["pid"] = self.pid
        if self.state:
            payload["state"] = self.state
        return payload


class Supervisor(Protocol):  # pragma: no cover - structural typing
    """Lifecycle interface. Implementations must not fork Mind processes."""

    name: str

    def available(self) -> bool: ...

    def start(self, mind_id: str) -> SupervisorResult: ...

    def stop(self, mind_id: str) -> SupervisorResult: ...

    def status(self, mind_id: str) -> SupervisorResult: ...


class NoSupervisor:
    """Refuses lifecycle actions and explains what the operator should do.

    This is the default. It exists so that the absence of a process manager is a
    first-class, visible state rather than an invitation to spawn processes from
    the web tier.
    """

    name = "none"

    def available(self) -> bool:
        return False

    def _refuse(self, action: str, mind_id: str) -> SupervisorResult:
        unit = SYSTEMD_UNIT_TEMPLATE.format(mind_id=mind_id)
        return SupervisorResult(
            ok=False,
            action=action,
            backend=self.name,
            unavailable=True,
            detail=(
                "No process supervisor is configured, so this API will not start or stop "
                "Mind daemons itself. Starting processes from the web tier would give "
                "anything with code execution in the API process-control authority over "
                "the host. Ask your operator to run the daemon under a supervisor, e.g. "
                f"`systemctl {action} {unit}.service`, or set GENESIS_SUPERVISOR=systemd "
                "to let this API delegate to systemd."
            ),
        )

    def start(self, mind_id: str) -> SupervisorResult:
        return self._refuse("start", mind_id)

    def stop(self, mind_id: str) -> SupervisorResult:
        return self._refuse("stop", mind_id)

    def status(self, mind_id: str) -> SupervisorResult:
        return SupervisorResult(
            ok=True,
            action="status",
            backend=self.name,
            unavailable=True,
            detail="No supervisor configured; daemon state cannot be determined.",
            state={"running": False, "managed": False},
        )


class SystemdSupervisor:
    """Delegates lifecycle to systemd template units.

    Every command is a fixed argv built from a validated Mind id — no shell, no
    string interpolation into a command line. Mind ids are checked against a
    conservative pattern first, because ``%i`` in a unit name is not a place to
    discover that an identifier was attacker-controlled.
    """

    name = "systemd"

    #: Mind ids are ``GMD-...``/``GMID-...``/``gm_...`` in practice. Anything
    #: outside this set is refused rather than passed to systemd.
    _ALLOWED_ID_CHARS = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    )

    def __init__(self, systemctl: Optional[str] = None) -> None:
        self._systemctl = systemctl or shutil.which("systemctl") or "systemctl"

    def available(self) -> bool:
        return shutil.which(self._systemctl) is not None or self._systemctl == "systemctl"

    @classmethod
    def is_valid_mind_id(cls, mind_id: str) -> bool:
        return bool(mind_id) and len(mind_id) <= 128 and all(
            character in cls._ALLOWED_ID_CHARS for character in mind_id
        )

    def _unit(self, mind_id: str) -> str:
        if not self.is_valid_mind_id(mind_id):
            raise SupervisorActionError(
                f"refusing to build a systemd unit name from an unsafe Mind id: {mind_id!r}"
            )
        return f"{SYSTEMD_UNIT_TEMPLATE.format(mind_id=mind_id)}.service"

    def _run(self, args: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(  # noqa: S603 - fixed argv, no shell
            [self._systemctl, *args],
            capture_output=True,
            text=True,
            timeout=SUPERVISOR_TIMEOUT_SECONDS,
            check=False,
        )

    def _action(self, action: str, mind_id: str) -> SupervisorResult:
        try:
            unit = self._unit(mind_id)
        except SupervisorActionError as exc:
            return SupervisorResult(
                ok=False, action=action, backend=self.name, detail=str(exc)
            )

        try:
            completed = self._run([action, unit])
        except FileNotFoundError:
            return SupervisorResult(
                ok=False,
                action=action,
                backend=self.name,
                unavailable=True,
                detail="systemctl was not found, so the configured supervisor is unusable.",
            )
        except subprocess.TimeoutExpired:
            return SupervisorResult(
                ok=False,
                action=action,
                backend=self.name,
                detail=f"systemctl {action} timed out after {SUPERVISOR_TIMEOUT_SECONDS}s",
            )

        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        ok = completed.returncode == 0
        detail = stdout or stderr or f"systemctl {action} exited {completed.returncode}"
        if not ok:
            logger.warning("systemctl %s %s failed: %s", action, unit, detail)

        return SupervisorResult(
            ok=ok,
            action=action,
            backend=self.name,
            detail=detail,
            state={"unit": unit, "returncode": completed.returncode},
        )

    def start(self, mind_id: str) -> SupervisorResult:
        return self._action("start", mind_id)

    def stop(self, mind_id: str) -> SupervisorResult:
        return self._action("stop", mind_id)

    def status(self, mind_id: str) -> SupervisorResult:
        try:
            unit = self._unit(mind_id)
        except SupervisorActionError as exc:
            return SupervisorResult(
                ok=False, action="status", backend=self.name, detail=str(exc),
                state={"running": False, "managed": False},
            )

        try:
            active = self._run(["is-active", unit])
            properties = self._run(["show", unit, "-p", "MainPID", "-p", "SubState"])
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return SupervisorResult(
                ok=False,
                action="status",
                backend=self.name,
                unavailable=True,
                detail=f"could not query systemd: {type(exc).__name__}",
                state={"running": False, "managed": False},
            )

        state_text = (active.stdout or "").strip()
        running = active.returncode == 0 and state_text in ("active", "activating")

        pid: Optional[int] = None
        substate: Optional[str] = None
        for line in (properties.stdout or "").splitlines():
            key, _, value = line.partition("=")
            if key == "MainPID" and value.strip().isdigit():
                pid = int(value.strip())
            elif key == "SubState":
                substate = value.strip()

        return SupervisorResult(
            ok=True,
            action="status",
            backend=self.name,
            detail=f"systemd reports '{state_text or 'unknown'}' for {unit}",
            pid=pid or None,
            state={
                "running": running,
                "managed": True,
                "unit": unit,
                "systemd_state": state_text or None,
                "substate": substate,
                "pid": pid or None,
            },
        )


_supervisor: Optional[Supervisor] = None


def get_supervisor(explicit: Optional[str] = None) -> Supervisor:
    """Return the configured supervisor (cached per process).

    Resolution order: the ``explicit`` argument, then the ``supervisor`` setting,
    then ``GENESIS_SUPERVISOR``, then ``none``. ``Settings.supervisor`` defaults
    to ``None`` precisely so it cannot shadow the environment variable — with a
    non-``None`` default the environment variable was unreachable.

    ``GENESIS_SUPERVISOR`` selects the backend: ``systemd`` to delegate to
    systemd, ``none`` (the default) to refuse lifecycle actions with an
    explanation. An unknown value raises rather than guessing, because a typo
    that silently disabled process management would be worse than a startup
    error.
    """
    global _supervisor

    if explicit is not None:
        name = explicit
    else:
        configured = None
        try:
            from genesis.config import get_settings

            configured = getattr(get_settings(), "supervisor", None)
        except Exception:  # pragma: no cover - settings unavailable in some hosts
            configured = None
        name = configured or os.environ.get("GENESIS_SUPERVISOR") or "none"

    name = str(name).strip().lower()

    if name not in VALID_SUPERVISORS:
        raise SupervisorUnavailable(
            f"Unknown supervisor '{name}'. Valid options: {', '.join(VALID_SUPERVISORS)}"
        )

    if _supervisor is None or getattr(_supervisor, "name", None) != name:
        _supervisor = SystemdSupervisor() if name == "systemd" else NoSupervisor()

    return _supervisor


def set_supervisor(supervisor: Optional[Supervisor]) -> Optional[Supervisor]:
    """Install a specific supervisor (tests, embedded hosts)."""
    global _supervisor
    _supervisor = supervisor
    return _supervisor


def reset_supervisor() -> None:
    """Clear the cached supervisor."""
    global _supervisor
    _supervisor = None
