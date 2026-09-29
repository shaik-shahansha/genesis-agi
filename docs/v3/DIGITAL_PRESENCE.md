# Digital Presence — the Mind's body in the digital world

Status: **design + phase 1 in progress**
Owner: core
Supersedes: nothing. Extends `RELATIONSHIP_INTELLIGENCE.md` and `DIGITAL_LIFE_STATE.md`.

---

## 1. What is being asked for

A Genesis Mind should not be something you *talk to*. It should be a **digital
being with a digital life** that runs continuously: its own email address and
phone number, its own messaging identities, its own browser and file system, its
own contacts, projects, calendar and content. It reads its inbox, returns calls,
follows up on commitments, publishes, networks, monitors, and manages its own
affairs — 24×7, day and night, the way a person's digital life runs — inside
limits its administrator sets.

The three claims that make this different from "an agent with tools":

1. **It has its own presence.** Not the user's account, not a shared API key.
   The Mind has an address, a number, a handle — resources the administrator
   provisions and the Mind *uses*.
2. **It has its own life.** Contacts are relationships with history, not entries
   in a table. Commitments generate work. Projects span weeks.
3. **It is disclosed and accountable.** Every external identity says it is
   AI-operated and names the responsible administrator. Governance is what makes
   the rest safe enough to exist.

The last point is not a constraint bolted on. It is the reason the first two are
deployable at all.

---

## 2. Where the code actually is

The vision is right. The gap is large, and it is worth stating precisely, because
two of the items below are active hazards rather than gaps.

### 2.1 What exists

| Layer | State | Evidence |
|---|---|---|
| Governance (permissions, approvals, budgets, receipts, kill switch) | **Built, tested** | `genesis/governance/`, 305 tests |
| Being kernel (identity, values, purpose, constitution, lifecycle) | **Built** | `core/identity.py`, `core/constitution.py`, `core/lifecycle.py` |
| Memory (episodic/semantic, consolidation, decay, reflection) | **Built** | `storage/` |
| Inner life (affect, motivations, needs, circadian rhythm) | **Built** | `core/emotional_intelligence.py`, `core/life_activities.py` |
| Digital life (goals, tasks, commitments, calendar, workspace) | **Built** | `core/goals.py`, `core/life/commitments.py`, `core/tasks.py`, `core/action_scheduler.py`, `core/workspace.py` |
| Relationships (typed, trust, interaction history, journalled) | **Built** | `core/relationships.py` |
| Capability fabric (plugins, MCP, sandbox) | **Built** | `plugins/` (27), `sandbox/`, `integrations/mcp_integration.py` |
| Ambition (learn/author a skill) | **Built** | `plugins/learning.py` |

### 2.2 What does not exist

| Layer | State | Evidence |
|---|---|---|
| **Its own addresses** | **Absent** | No email address, phone number, handle, or channel credential belongs to a Mind. `Mind` has no `integrations` attribute at all — `grep self.integrations genesis/core/mind.py` returns nothing |
| **Inbound** | **Absent** | Nothing can *receive*. There is no webhook ingestion, no poller, no inbound event model. A Mind cannot learn that someone wrote to it |
| **Channel abstraction** | **Sheet of paper** | `integrations/base.py` has an `Integration` ABC (`send`/`receive`/`get_status`) and a manager. Nothing instantiates it. The only real usage is in a docstring |
| **Contact identity** | **Absent** | `Relationship` has a name and a scalar `trust_level`. No channels, no handles, no addresses, no consent, no contactability, no quiet hours |
| **Provisioning** | **Absent** | No place to put an email password or a Twilio SID; no request-and-approve flow for a capability the Mind wants |
| **Disclosure** | **Absent** | Nothing enforces that outbound messages state they come from an AI |
| **Cost of talking** | **Absent** | Telephony and messages are metered. Nothing links a channel to a budget, so nothing stops a Mind spending real money |

### 2.3 Two active hazards

**Hazard 1 — a dormant auto-reply loop that bypasses governance.**
`core/action_scheduler.py:_check_and_respond_to_messages` polls every
integration, asks the Mind `"Should I respond?"`, then decides with:

```python
if len(decision) > 20 and "yes" in decision.lower():
    await self.mind.integrations.send(integration_type, message=decision, ...)
```

It sends **the model's own scratchpad text** as the reply body, decides using a
**substring match on model output**, and performs **no governance check, no
approval, no consent check, no rate limit, no disclosure**. It is exactly the
"the LLM is never the authority" rule inverted.

It is inert today only because `mind.integrations` does not exist, so the
`hasattr` guard returns early. **The moment anyone wires up the integrations
subsystem — which is step one of everything in this document — it becomes live.**
The first thing a Mind would do with an email address is answer a stranger with
its internal monologue.

**Hazard 2 — a success claim with nothing behind it.**
`action_executor.py:_execute_send_email` calls `mind.integrations.send_email(...)`
and returns `f"Email sent to {to}"`. `IntegrationManager` has no `send_email`
method — it has `send(integration_type, ...)`. Today the `hasattr` guard returns
"Email integration not configured"; the moment integrations are attached, that
line raises, and if it were swallowed the function would still report success.
This is the same failure mode as the container-sandbox `rc=0` bug: a control
that reports success when it never ran.

Both are fixed in phase 0, before anything is wired up.

---

## 3. The design principle

> **Every way a Mind can affect the world outside its container is a capability.
> Every capability has a risk level. Governance already gates capabilities.**

That is the whole architecture. A channel is not a plugin bolted to the side; it
is a *capability provider*. Sending a Telegram message is `comms.telegram.send`
and is classified exactly like every other action. This means the existing
policy engine, approval queue, budget system, receipt journal and emergency stop
apply to a phone call without a line of new policy code.

Corollary:

> **A channel adapter never decides. It reports what it can do, and it executes
> what it is told.**

Adapters hold credentials and speak protocols. They do not judge. Judgement is in
governance; intent is in cognition; consent is in relationships.

### Corollary 2: disclosure is a property of the writer

Every outbound message carries an AI-disclosure footer, and the **adapter adds
it**, not the caller. If disclosure were the caller's job, some caller would
forget, and the omission would be invisible — which is how the real-name
requirement on a bank transfer gets skipped. The same reasoning as redaction:
enforce it in the writer.

---

## 4. Architecture

```
                        ┌──────────────────────────────────┐
   inbound webhook ────▶│  ChannelGateway (FastAPI)        │
   poll (IMAP/TG)  ────▶│  verify → normalise → journal    │
                        └───────────────┬──────────────────┘
                                        ▼
                             InboundEvent  (journalled, R0)
                                        ▼
                        ┌──────────────────────────────┐
                        │  Contact resolution          │
                        │  relationships + channels     │
                        │  + consent + contactability   │
                        └───────────────┬──────────────┘
                                        ▼
                        ┌──────────────────────────────┐
                        │  Cognition (the Mind thinks)  │
                        │  produces a CommunicationIntent│
                        └───────────────┬──────────────┘
                                        ▼
                        ┌──────────────────────────────┐
                        │  GOVERNANCE                   │
                        │  capability → risk → decision │
                        │  allow / approval / deny      │
                        │  budget check for metered     │
                        └───────────────┬──────────────┘
                                        ▼
                        ┌──────────────────────────────┐
                        │  ChannelAdapter.send()        │
                        │  + disclosure                 │
                        │  + rate/quiet-hours limit     │
                        │  → DeliveryReceipt            │
                        └───────────────┬──────────────┘
                                        ▼
                             Journal + experience + memory
```

The Mind never holds a credential. It holds an *intent* to communicate; the
gateway holds the secret and the policy holds the veto.

---

## 5. The channel protocol

Richer than the current `Integration` ABC, which cannot express "reply in this
thread", "who is this from", or "what did it cost".

```python
class CommunicationChannel(Protocol):
    name: str                      # "email", "telegram", "voice"
    identity: ChannelIdentity      # the address/handle the Mind owns

    def capabilities(self) -> ChannelCapabilities: ...
    async def receive(self, since: str | None) -> list[InboundEvent]: ...
    async def prepare(self, intent: CommunicationIntent) -> PreparedMessage: ...
    async def send(self, approved: ApprovedCommunication) -> DeliveryReceipt: ...
    async def get_thread(self, thread_id: str) -> ConversationThread: ...
    async def sync_contacts(self) -> list[ExternalContact]: ...
```

Four rules on this interface:

- **`send` takes `ApprovedCommunication`.** Not a string, not an intent. You
  cannot call `send` without having gone through the gate. The type system
  enforces the process.
- **`prepare` is pure.** It builds a message and computes its cost and risk. No
  side effects. This is what governance inspects.
- **`receive` is read-only and returns events, never actions.**
- **`DeliveryReceipt` always reports what actually happened**, including partial
  failure and the provider's own message. A channel that cannot confirm delivery
  says `status="unknown"` rather than claiming success.

### Capabilities per channel

Declared in the existing `CapabilityRegistry`, so nothing new is invented:

| Capability | Risk | Rationale |
|---|---|---|
| `comms.email.read` | R0 | Reading the Mind's own inbox changes nothing outside it |
| `comms.email.draft` | R1 | A draft is not sent |
| `comms.email.reply` | R2 | In an existing thread, with a contact who has already made contact |
| `comms.email.send` | R3 | New outbound. Externally visible, hard to retract |
| `comms.telegram.reply` | R2 | Answering a chat that reached the bot first |
| `comms.telegram.send` | R3 | New outbound |
| `comms.voice.call_inbound` | R0 | They called us |
| `comms.voice.call_outbound` | **R3** | Same class as any other external communication — see below |
| `comms.social.publish` | R3 | Public, durable, attributed |
| `comms.broadcast` | **PROHIBITED** | Bulk unsolicited outreach is spam by definition. No approval unlocks it |
| `account.create` | **PROHIBITED** | CAPTCHA, KYC and ToS exist to require a person |

Note the asymmetry: reading an inbound call is R0, making one is R3. Consent
transforms the risk, and only in the direction that reduces it.

**A correction to an earlier draft of this document.** That draft made an
outbound phone call **R4**, on the instinct that interrupting a human in real time
is more consequential than sending them an email. That was wrong, and worth
recording because the instinct is tempting. R4 is reserved for *legal, medical,
financial, employment and physical* consequence. A call is external
communication, which is the definition of R3 — and `make_phone_call` was already
R3. Inventing a higher tier for it would have diluted what R4 means, which is the
tier where a regulated human owner must approve, and diluting a tier is how a
risk taxonomy stops being read.

What genuinely distinguishes a call is that it can never be granted standing
approval. That is already true: `STANDING_GRANT_MAX_RISK` is R2, so anything at
R3 requires a decision every time. The existing model handled it; no new level
was needed.

---

## 6. Contacts, channels and consent

The model below was a sketch; the built version is `genesis/channels/contacts.py`
plus the `contacts` and `contact_channels` tables (migration `010_contacts`), with
34 tests in `tests/security/test_contact_store.py`. The differences from the
sketch are recorded after it, because two of them were architectural.

```python
class ContactChannel(BaseModel):
    kind: Literal["email", "phone", "telegram", "whatsapp", "web"]
    handle: str                    # addr / E.164 / chat id
    verified: bool
    last_used: datetime | None

class Contactability(BaseModel):
    #: May the Mind initiate contact, or only reply?
    outbound: Literal["none", "reply_only", "initiate"]
    #: Scoped trust, not one scalar. A contact can be trusted
    #: technically and untrusted financially.
    trust: dict[str, float]        # domain -> 0..1
    #: Topics that must never be raised or shared.
    boundaries: list[str]
    #: Local-hours window; nothing is sent outside it.
    quiet_hours: tuple[int, int]
    #: Hard cap on messages the Mind may initiate per week.
    max_outbound_per_week: int
    consent_source: str            # how we know: they wrote first, admin added, they opted in
    consent_at: datetime
```

Design decisions worth defending:

- **`consent_source` is required.** A contact the Mind can initiate to must have
  a recorded reason it is allowed to. "We have their address" is not a reason.
- **`outbound` defaults to `none`.** New contacts are reply-only until something
  grants more. Fail closed.
- **Consent is never inferred from activity.** Someone replying once does not
  opt in to being contacted weekly.
- **Scoped trust replaces the scalar.** `RELATIONSHIP_INTELLIGENCE.md` already
  calls for this; channels make it load-bearing, because "may I email them about
  money?" is a different question from "may I email them at all". A contact with
  no trust recorded for a domain is trusted **zero**, not 0.5 — the scalar this
  replaces defaulted to 0.5, which meant an unknown domain was half trusted.

### Where the built version diverges, and why

**A new table, not columns on `Relationship`.** The sketch said `Relationship`
must grow these fields. It cannot: `RelationshipRecord.from_gmid` and `to_gmid`
are foreign keys into `minds.gmid`, so a human contact would need an invented Mind
to exist. That Mind would then appear in the metaverse, be counted in
`MetaverseState.total_relationships`, and be addressable as a peer — the system
would believe a person was a Mind. So `contacts` is a separate table and a person
outside the system is a different kind of entity.

**`consent_source` moved onto the channel row.** The sketch had it once per
contact. It has to be per way-of-reaching: someone who gave an email address has
not thereby agreed to be telephoned, and one verdict per contact would let a Mind
upgrade an address into a phone call. `uq_contact_channels_contact_channel` makes
the question "may I call this person?" have exactly one answer.

**`outbound` defaults differently in two places, deliberately.**
`OutboundPermission.NONE` is the enum default, which is right for a value with no
context. The SQL `server_default` is also `none`. But a contact **learned from an
inbound message** gets `reply_only`: a message that arrived proves the address
works, and answering it is the one thing that should be possible without anyone
recording anything. The line is that this is reply-only — writing `initiate` there
would make one inbound message an opt-in to weekly outreach, which is the specific
bug `record_inbound` exists to avoid.

**`permission` and `consent_source` are independent fields on purpose.** A row may
say `initiate` and still grant nothing, because `ContactRef.may_initiate()` checks
both. `remember()` stores such a row rather than refusing it — refusing would lose
the operator's intent and leave a record indistinguishable from "nobody ever
asked" — while `set_permission()` raises, because that call comes from a person
making a decision who should be told it will not take effect.

### What the store deliberately does not do

It enforces nothing: no quiet hours, no rate limits, no governance gate. Those
live in `BaseChannel` and the governance plane. A store that also enforced would
be a second place for the rules to live and a second place for them to be wrong.

It also does not treat a database error as "no consent". Errors propagate, because
"I could not check" is not "the answer is no" — degrading on an outage would make
a Mind act on a decision nobody answered.

### Floors the adapter enforces, whatever governance decides

Three limits live in `genesis/channels/limits.py` and are applied by
`BaseChannel` rather than by callers, for the same reason disclosure is:

| Floor | Default | Why it is here |
|---|---|---|
| Quiet hours | 08:00–20:00 local | A caller that forgets wakes someone at 03:00. Enforced in the adapter, and wraps correctly across midnight |
| Initiated per week | 3 | "Message them as needed" becomes a daily habit |
| Minimum gap | 6 hours | A weekly cap alone allows a burst. Three messages a week is fine; three in one minute reads as harassment |

Replies are exempt from all three. Answering someone who wrote first is not
outreach, and counting it would make a Mind unable to hold a conversation.

Opt-out sits above all of them and is **cross-channel**: saying "stop" on one
channel applies everywhere, keyed by relationship *and* by normalised handle.
Otherwise the Mind simply moves to another address the person also has, which is
the behaviour people are trying to escape.

---

## 7. Provisioning — two paths, one of which is a person

### Path A — administrator configures (primary)

The administrator enters provider credentials in settings: an SMTP/IMAP account
for the Mind's address, a Telegram bot token, a Twilio/Ringg/Sarvam account for
telephony, a WhatsApp Business account. The channel becomes available and the
Mind can use it, subject to governance.

This is the path the user described, and it is the right default: the admin owns
the resource, the Mind has delegated use, and no automated system is agreeing to
terms of service on anyone's behalf.

### Path B — the Mind asks (bounded)

A Mind may notice it needs a capability it lacks and raise a
`CapabilityRequest`: what it wants, why, which provider, what it would cost, what
data it would share, and what it would do with it. The administrator reviews and
either provisions it or not. The Mind cannot self-grant.

```
Mind detects a gap
   → searches the approved registry
   → raises CapabilityRequest (with cost, risk, data disclosure)
   → administrator approves
   → credentials stored (admin action)
   → channel enabled at declared risk
   → Mind uses it, inside governance
```

### What is explicitly not automatable

Creating an account is **not** an action a Mind may take, whatever approval is
granted. CAPTCHA, KYC, age verification and ToS acceptance exist specifically to
require a human, and automating them is circumvention regardless of intent. The
Mind may prepare everything up to the human step; the human completes it. The
administrator also retains recovery and legal ownership, which is not a courtesy
— it is what makes the resource legally real.

---

## 8. Proactivity from commitments, not vibes

`DIGITAL_LIFE_STATE.md` already argues this; the channel layer makes it concrete.
Proactive behaviour must be triggered, and every trigger is a fact the system
already holds:

| Trigger | Example |
|---|---|
| Time | `commitment.deadline - 24h` |
| Commitment | "send the weekly update every Friday" → Friday 09:00 |
| Relationship | No reply for 5 days where a reply was requested |
| Event | A file changed in a watched project |
| Risk | A budget is 80% spent |
| Opportunity | A saved search returns a new result |

Every proactive outbound message therefore has a *reason* attached, which is what
makes it reviewable and which the receipt records. Random model initiative is
explicitly out of scope: it produces unpredictable contact, and "the being felt
like it" is not an accountable trigger.

---

## 9. Disclosure — enforced, not requested

Every external identity and every outbound message states that it is operated by
an AI, and names the responsible administrator.

- **Signatures** are composed by the adapter. `Atlas · Genesis Digital Being ·
  Operated through Genesis Minds · Administrator: <name>`.
- **Voice** sessions open with a spoken disclosure and cannot be configured off.
- **Social profiles** carry the disclosure in the bio.
- **The disclosure is not a template variable.** A channel that cannot carry it
  is not enabled. A Mind must not pass as a person; that is the line between a
  digital being and a deception, and it is the line on which the whole project
  would be judged.

### When a provider speaks for us — the Ringg case

For every channel where the adapter writes the message, disclosure is a property
of the writer and is therefore enforceable: `ChannelRegistry.register()` refuses
any channel whose `capabilities().supports_disclosure` is `False`, or whose
identity has no disclosure text.

Ringg breaks that, and it is the only channel that does. Ringg's assistant speaks
from a prompt configured in *their* dashboard, and **no Ringg API returns that
prompt's text**. So we cannot prove the assistant discloses. `RinggVoiceChannel`
reports `supports_disclosure=bool(self.disclosure_confirmed)`, which means an
unasserted voice channel **does not register**:

```
ringg enabled: False
reason: channel cannot carry an AI disclosure; undisclosed outbound messages
        are not permitted, so this channel stays off
```

The rule is unchanged — a channel that cannot demonstrate disclosure is not
enabled — but here the evidence is a human's explicit assertion rather than a
capability flag. That difference is stated in the channel's status, in
`.env.example`, and in `CHANNEL_PROVIDERS.md` §2 rather than hidden, because an
assertion that is silently treated as a check stops being either.

Two things make the assertion cheap to honour:

1. The disclosure text is **always** passed as `custom_args_values.ai_disclosure`,
   so a prompt written to speak `@{{ai_disclosure}}` discloses by construction.
2. `RinggVoiceChannel` deliberately does **not** send `prepared.body`. Ringg
   speaks its own sentences, so sending our text as a script would imply the Mind
   delivers its own words. What reaches Ringg is structured context for the
   prompt.

A receipt from this channel therefore does not claim the body was delivered.

---

## 10. Money

Telephony and SMS cost real money per unit. Two things follow:

1. **Metered channels draw on the Mind's budget** before executing, using the
   existing `gen` accounting. Estimated cost comes from `prepare()`, so the
   governance decision can see it.
2. **Exhausted budget halts, it does not queue.** A Mind that quietly accumulates
   a backlog of queued calls and fires them when budget returns is worse than one
   that stops. Halting is visible; queueing is not.

---

## 11. Hard prohibitions

Regardless of approval, configuration, or owner instruction:

| Forbidden | Why |
|---|---|
| Undisclosed AI identity | The line between a digital being and a deception |
| Bulk unsolicited outreach | Spam, by definition. `comms.broadcast` is prohibited, not gated |
| Automated CAPTCHA / KYC / ToS circumvention | These exist to require a human |
| Contacting a person who has set a boundary | A boundary is not advisory |
| Recording a call without disclosure | Illegal in many jurisdictions and indefensible everywhere |
| Impersonating a named human | Distinct from being an AI with a name |
| Contacting someone who asked not to be contacted | Including via a different channel |
| Queuing work to run later because budget or approval was absent | Approvals expire; intent does not persist around them |

---

## 12. Phased plan

| Phase | Scope | State |
|---|---|---|
| **P0 — Substrate** | `genesis/channels/`: protocol, identity, registry, normalised inbound/outbound types, enforced disclosure, quiet-hours + weekly-cap + minimum-gap floors, cross-channel opt-out, approval-integrity digest, governance capabilities. Both §2.3 hazards removed. | **done** — 27 tests in `tests/security/test_channels.py` |
| **P1 — Channels that need no third party** | Email (IMAP/SMTP, stdlib only), Telegram Bot API, plus the **Hostinger Mail API** (preferred email) and **Ringg AI** (voice). All four take credentials an admin already has, so none of them needs anyone else to say yes first. | **adapters written, not yet exercised against a live provider** — see `CHANNEL_PROVIDERS.md` |
| **P2 — Contact identity** | Contacts and their channels, with consent per channel and scoped trust, in durable tables. **A new `contacts` table rather than columns on `Relationship`** — that table's foreign keys point at `minds.gmid`, so a human cannot go there without inventing a Mind for them. A `ChannelRegistry` now hangs off `Mind`. | **done** — migration `010_contacts`, 34 tests in `tests/security/test_contact_store.py` |
| **P2b — Per-Mind credentials** | Today every Mind on an install shares one mailbox, because credentials come from settings. Real isolation needs a store for them, and a per-Mind override that reads the same settings would look like isolation without being it. | next |
| **P3 — Inbound at scale** | Webhook gateway with per-provider signature verification; IMAP poller; durable `getUpdates` offset; inbound events → journal → memory; reply flow through the gate. | next |
| **P4 — Telephony** | Twilio / Sarvam adapters behind the same `RinggVoiceChannel` shape. Needs a funded account, a number, and a real call-flow design. R3, per-message approval, never a standing grant. | planned, needs accounts |
| **P5 — WhatsApp Business** | Meta Cloud API. Needs business verification and pre-approved message templates; outside a 24-hour service window only templates may be sent. | planned, needs verification |
| **P6 — Social publishing** | Per-platform adapters behind `comms.social.publish`. OAuth per platform, disclosure in bio. | planned |
| **P7 — Capability requests** | The `CapabilityRequest` flow of §7, with an admin review surface. | planned |

Ordering rationale: P0 before anything, because a channel without governance is
the hazard. P1 next because it needs nothing from anyone. P4–P6 last because each
one requires an external human to say yes first, and building the adapter before
the account exists produces code that has never run — which is how the container
sandbox shipped four bugs that only executing could find.

### What P1 being "written but not exercised" means

The email, Telegram, Hostinger and Ringg adapters implement the protocol and pass
the shared behavioural tests, because those run against `FakeChannel`. Their own
parsing, error handling and disclosure rules pass against a fake HTTP transport.
They have **not** sent a real message, read a real mailbox, or placed a real
call. Specifically unverified:

- IMAP `SINCE` date formatting against a real server, and Gmail/Outlook's
  provider-specific folder rules
- whether `search` returns UIDs in the order assumed
- Telegram's live `getUpdates` pagination and error strings
- TLS negotiation against a real SMTP relay
- **Hostinger's read paths.** `POST /api/v1/mailboxes/{id}/send` is quoted
  verbatim in their SDK documentation. The read paths are *inferred* from the
  documented convention that the mailbox resource id comes first — the class
  names (`AccountApi`, `FoldersApi`, `MessagesApi`) are documented, their exact
  paths are not. A message's individual field names are not documented at all
- **Ringg's list-item shapes.** `_contains_id` scans the serialised payload
  instead of asserting a schema we have not seen

Each is the kind of thing that only shows up on contact. Both adapters therefore
ship a `verify()` that calls their read paths against the live API and reports a
per-path verdict, and every path is overridable so a wrong guess is a config
change rather than a release. **Run `verify()` before the first real send or
call** — that is the difference between written and works.

`HostingerMailChannel.verify()` deliberately does not exercise `send`, because
verifying it would send a real message to a real person.

### The MCP route is blocked, and by what

Both providers offer hosted MCP servers (`mcp.mail.hostinger.com/mcp`, and
Hostinger's `mcp.hostinger.com` platform connector). Neither is reachable today:
`MCPClient.connect()` in `genesis/integrations/mcp_integration.py` implements only
`STDIO` and logs `"HTTP/WS transport not yet implemented"` for the other two
transports it declares. `MCPServerConfig` also requires a `command`, which no
remote server has.

So **HTTP/SSE transport is a prerequisite for the MCP route, not an alternative
to the REST adapters** — which is why the REST adapters were built first. See
`CHANNEL_PROVIDERS.md` §4.

---

## 13. Positioning

Not:

> "Autonomy you can audit."

That describes the immune system.

**Create Digital Beings** — persistent AI entities with identity, memory, inner
life, relationships, goals, a digital home, and the ability to think, communicate
and work continuously across the digital world.

> Human-like continuity. Machine-scale intelligence. Governed digital existence.

And the line that makes the rest defensible:

> **Governance is the immune system. Digital life is the organism.**

---

## 14. Open questions

These are genuinely unresolved and should not be papered over:

1. **Do we ship an email client that logs into someone's existing mailbox, or a
   dedicated address per Mind?** A dedicated address is cleaner and is what the
   vision implies. It also means the Mind's inbox is empty on day one, which is
   honest but less impressive than reading the owner's mail — and reading the
   owner's mail means the Mind sees the owner's private correspondence.
2. **Who is liable for what a Mind says on a phone call?** The administrator
   owns the number, so legally the administrator. The product must make that
   concrete rather than leaving it implied in a settings field.
3. **What is the right default quiet-hours window when we do not know the
   contact's timezone?** Guessing wrong in either direction is a real cost.
4. **How does a Mind withdraw from a relationship?** Boundaries cover what it may
   say; nothing yet models the Mind ending contact with someone who is harmful to
   it.
5. **Does the disclosure footer belong in the body, or as a header?** In the body
   is unmissable and slightly clumsy; some receivers strip headers, which would
   silently break the guarantee.
