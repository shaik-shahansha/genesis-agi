# Embodiment abstraction — design

> **Status:** interface designed, not implemented. This specifies the small part
> of Phase L that should be built **early** (during Phase C), even though real
> hardware is Phase L.

## The argument for doing this early

There is no hardware layer in this repository. `actuate_robot` exists only as a
governance entry at R4 — a risk classification with nothing behind it.

The temptation is to defer all of embodiment to Phase L. That is the wrong
call, for one reason: **the shape of the interface is what constrains the
architecture, and it is cheap now and expensive later.**

Concretely, if the kernel is extracted in Phase C without a presence/actuation
seam, then every one of chat, voice, the workspace, and a future robot will each
grow their own path into the Mind, and by Phase L there will be four of them to
reconcile. Defining a three-method interface first costs a day; retrofitting it
costs a refactor of the exact subsystem Phase C exists to clean up.

So: **define the interface during Phase C, implement `WebBody` immediately,
leave the rest as refused stubs.**

## The interface

Deliberately three methods, because the useful distinction is between *sensing*
and *acting*, and between *doing* and *observing*:

```python
class Body(Protocol):
    """A presence through which a Mind perceives and acts."""

    name: str

    async def perceive(self) -> list[Observation]:
        """Return anything sensed since the last call. Must not block."""

    async def act(self, intent: Intent) -> ActuationResult:
        """Attempt an action in the world. May be refused."""

    async def observe(self) -> BodyState:
        """Describe this body's own state. Must never have side effects."""
```

Three properties are load-bearing:

1. **`perceive` does not block.** A body that can hang the cognition loop is a
   liability. Sensing is polled or event-driven; it is never a long call.
2. **`act` can be refused.** A body is not an authorization mechanism. It may
   refuse for physical reasons (out of reach, motors disabled, camera off), and
   it must not be able to *grant* permission the governance plane withheld. The
   order is always policy → body, never body → policy.
3. **`observe` has no side effects.** A human must be able to ask "what is this
   being's body doing?" without changing the answer. This is the emergency-stop
   read path.

## Implementations, and when each arrives

| Body | Phase | Notes |
|---|---|---|
| `WebBody` | **C** | Chat and the workspace. Perceive = new messages and workspace changes. Act = send a message, write a file. This is the one that exists today, just not behind an interface. |
| `NullBody` | **C** | Perceives nothing, acts nothing, always refuses. The honest default for a headless deployment, so "no body" is an explicit state rather than an implicit absence. |
| `VoiceBody` | J | Realtime audio. Perceive = transcript segments. Act = speak with barge-in. |
| `MobileBody` | J+ | Push notifications, device sensors, on-device presence. |
| `ROSBody` | L | Hardware. Perceive = sensor topics. Act = commanded motion. **Requires a safety-rated stop before it is usable at all.** |

## The safety precondition for `ROSBody`

This is the part worth stating plainly, because it is what separates an
embodiment feature from a hazard.

A robot body must not be reachable through `act()` until all of the following
exist:

1. **A safety-rated stop that is not software-dependent.** The existing
   `EmergencyStopService` is in-process state. For a physical body there must be
   a path that stops motion when the process is dead, hung, or has lost the
   network — i.e. a watchdog that fails *safe* (motion stops) rather than
   *permissive* (motion continues, unpoliced).
2. **A watchdog with a bounded deadman timer.** Motion requires a live heartbeat.
   A being that loses its supervisor stops, rather than continuing a plan it can
   no longer reason about.
3. **Hard limits enforced below the policy layer.** Joint limits, force limits and
   speed limits belong in the controller, not in a policy the Mind evaluates.
   Policy decides *whether*; the controller decides *how much*, and the second
   must hold even when the first is wrong.
4. **`actuate_robot` remains R4.** A human approves physical actions. That
   classification is already in the registry, and it should not be relaxed once
   the capability becomes real — which is exactly when pressure to relax it will
   appear.

Until (1)–(4) exist, `ROSBody` should raise `CapabilityUnavailableError` rather
than do anything. A refused stub is the correct implementation.

## What this does *not* include

- No simulation environment. Genesis World (Phase M) is where that belongs.
- No hardware abstraction for specific vendors. `ROSBody` targets ROS, and
  vendor specifics stay behind it.
- No claim that the interface above is sufficient for every body. It is
  sufficient for web, voice and a simple mobile presence, which is what the five
  phases before embodiment need.
