# Provider setup

Two providers are wired for a Mind's own presence: **Hostinger Mail** for email
and **Ringg AI** for voice. This is what to configure, what each one actually
does, and — importantly — what has and has not been verified.

Read §3 before you trust either one.

---

## 1. Hostinger Mail (the Mind's email address)

### Why this over plain IMAP/SMTP

The `EmailChannel` adapter speaks IMAP and SMTP with the standard library, and it
works. Hostinger's Mail API is preferred when available, for four reasons that
matter to this product rather than in general:

| | Why it matters here |
|---|---|
| **A token scoped to specific mailboxes** | The credential a Mind uses cannot reach anything it was not granted. Same shape as our capability model |
| **Threading done by the provider** | `inReplyTo` makes the API copy the original's message id and references and flag the source as answered. Header assembly is exactly where a reply silently stops being a reply |
| **An outgoing allow list** | Rejects a send to anyone not listed. Turns "the agent emailed the wrong person" into a rejected send — and it holds even if our code is wrong |
| **Webhooks for new mail** | Reacting to inbound does not need a poll loop |

### Setup

1. In hPanel, open the email domain's sidebar → **Agentic Mail** → **API access**.
2. Create a named token. **It is shown once.**
3. Scope it to the mailboxes this Mind should reach, and choose permissions —
   SMTP/IMAP actions and webhook management are separate.
4. Copy the token and the mailbox's `AC...` resource id into the environment:

```bash
MIND_HOSTINGER_MAIL_API_TOKEN=<token>
MIND_HOSTINGER_MAILBOX_ID=AC1a2b3c4d5e6f7g
MIND_HOSTINGER_MAIL_ADDRESS=sage@yourdomain.com
MIND_HOSTINGER_MAIL_DISPLAY_NAME=Sage
MIND_ADMINISTRATOR_NAME="Your Company"
```

5. **Configure the allow list** (Agentic Mail → Allow list). Recommended: put the
   domains the Mind is allowed to write to. This is the one control that holds
   when our own code is wrong.

Email is attempted only when **both** the token and the mailbox id are set. One
without the other is a half-configured channel that would fail on first use, so it
is not registered at all.

### What the Mind can then do

- **Read** the inbox — R0. Reading changes nothing outside the container.
- **Reply** in a thread — R2. In an existing thread, with someone who wrote first.
- **Initiate** — R3. New outbound, externally visible, hard to retract.
- **Draft** — R1. A draft is not sent.

Every outbound message carries the AI disclosure, and **the adapter adds it** —
not the caller. A caller that forgets produces an invisible omission; that is the
same reasoning as redaction in the audit plane.

---

## 2. Ringg AI (the Mind's phone number)

### How this differs from every other channel, and why that matters

Ringg runs the voice assistant. The Mind decides **who** to call and **what
context** to give it; Ringg's assistant speaks, from a prompt and voice configured
in Ringg's dashboard.

So:

- **The prepared body is not sent.** `prepare()` runs — the floors apply, the
  disclosure is composed, and a human reads what the call is *for* — but what
  reaches Ringg is `custom_args_values`: structured context for the prompt, not a
  script.
- **`send()` places a call, it does not deliver a message.** The receipt carries a
  `call_id`.
- **The transcript arrives later**, by webhook or from call history. That is how a
  call becomes a memory rather than just an action.

A receipt from this channel therefore does not claim the body was delivered, and
does not imply the Mind speaks its own sentences over the phone.

### Setup

1. Ringg dashboard → **Settings → API Key → Generate**. **Shown once**, and
   regenerating it revokes the previous key immediately.
2. Create an assistant; note its `agent_id`.
3. `GET /workspace/numbers` or the dashboard; note a `from_number_id`.
4. Configure the assistant's prompt to **open with the AI disclosure**, using the
   `ai_disclosure` variable (see below).
5. Then, and only then:

```bash
MIND_RINGG_API_KEY=<key>
MIND_RINGG_AGENT_ID=<agent id>
MIND_RINGG_FROM_NUMBER_ID=<number id>
MIND_RINGG_PHONE_NUMBER=+15550000000
MIND_RINGG_DISCLOSURE_CONFIRMED=true
MIND_ADMINISTRATOR_NAME="Your Company"
```

### `MIND_RINGG_DISCLOSURE_CONFIRMED` is an assertion, not a check

The channel stays **disabled** until this is true, and the reason is worth stating
plainly.

Every other channel can prove it discloses, because the adapter composes the
disclosure into the body it sends. Ringg cannot: the words spoken come from a
prompt in Ringg's dashboard, and **no API returns that prompt's text**.

An undisclosed voice channel is the one outcome this product must not ship. A
phone call is the most human-seeming thing a Mind can do, and a person who
believes they are talking to a person has been deceived regardless of intent.

So the rule is the same as everywhere else — a channel that cannot demonstrate
disclosure is not enabled — with one honest difference: here the evidence is a
human's explicit assertion rather than a capability flag. That difference is
recorded in the channel's status and in this document rather than hidden.

To make the assertion cheap to honour, the disclosure text is always passed to the
assistant as `custom_args_values.ai_disclosure`. Write the prompt to speak
`@{{ai_disclosure}}` and the assistant discloses by construction. What we cannot
do is prove the prompt does.

### Cost

Telephony is metered at the provider. `capabilities().metered` is `True`, which is
what tells governance a budget check is required. The per-minute rate is not known
without a plan, so `unit_cost_usd` is 0.0 — the *fact* of being metered is
reported, the figure is not guessed.

Voice is R3, and can never hold a standing grant: `STANDING_GRANT_MAX_RISK` is R2,
so every call needs a decision.

### `MIND_RINGG_CALL_WINDOW`, and why there are two windows

Ringg enforces its own calling window through `call_config.call_time`. That is the
provider's control, and it is the one that ultimately decides whether a call
happens.

`MIND_RINGG_CALL_WINDOW` sets **our** quiet-hours floor to match it. This matters
because the two can disagree: if our floor is *wider* than Ringg's, the Mind
believes a call is allowed, passes its own checks, and then Ringg refuses it —
which surfaces as an unexplained delivery failure rather than a policy refusal,
and a failure that looks like a bug is one nobody investigates properly.

An unparseable value keeps the default (08:00–20:00) and logs a warning:

```
MIND_RINGG_CALL_WINDOW='business hours' is not a window like '09:00-18:00';
the default quiet hours (8:00-20:00) stay in force
```

Silently treating a typo as "no hours configured" would remove a control while
looking like a configuration change, which is the failure mode this project keeps
having to fix.

---

## 3. What is verified, and what is not

This section exists because both adapters were written from documentation, and
"written" is not "works".

### Verified

- **All shared channel behaviour**, against `FakeChannel`: disclosure in the
  writer, the approval gate, quiet hours wrapping midnight, the weekly cap
  exempting replies, cross-channel opt-out, approval-integrity digest, and honest
  `unknown` delivery. 27 tests.
- **Both adapters' logic**, against a fake HTTP transport: envelope unwrapping,
  error-code translation, message normalisation, pagination caps, and the
  disclosure rule. 52 tests.
- **The Ringg disclosure refusal** — an unasserted voice channel does not register.
- **The gateway loop**: inbound → responder → floors → gate → send, including
  every failure path leaving the Mind unable to send.

### Not verified

- **Any real API call.** Neither account exists yet.
- **The Hostinger read paths.** `POST /api/v1/mailboxes/{id}/send` is quoted
  verbatim in Hostinger's SDK documentation and is trustworthy. The read paths are
  **inferred** from a documented convention: *"The mailbox resource ID comes
  first. Every operation except `getCurrentAccount` is scoped to one mailbox;
  message operations take the folder next."* The class names (`AccountApi`,
  `FoldersApi`, `MessagesApi`, …) are documented; their exact paths are not.
- **A Hostinger message's individual field names.** The envelope and pagination
  keys are documented; the fields inside a message are not. The adapter reads
  several plausible spellings per field and treats absent as absent, so a rename
  degrades to an empty field rather than an empty mailbox — but that is a
  mitigation, not a verification.
- **Ringg's list-item shapes.** `_contains_id` does a substring scan over the
  serialised payload rather than asserting a schema we have not seen.
- **Webhooks from either provider.** Not implemented; inbound for voice therefore
  reports `can_receive: False`.

### How to close the gap

Every path is overridable, so a wrong guess is a config change rather than a
release:

```python
from genesis.channels.hostinger_mail import HostingerMailChannel

channel = HostingerMailChannel(
    api_token="...", mailbox_id="AC...", address="sage@example.com",
    paths={"messages": "/api/v1/mailboxes/{mailbox}/folders/{folder}/messages"},
)
print(await channel.verify())
```

`verify()` calls each read path against the live API and returns a per-path
verdict — including the status and the provider's error code for any that fail.
It deliberately does **not** exercise `send`, "not exercised — verifying it would
send a real message".

For Ringg, `verify()` checks the four things its own troubleshooting guide lists
as reasons a call does not start: the workspace (and its credit balance), the
assistant id, the caller number id, and whether the disclosure has been asserted.

Run these before the first real call or message. That is the difference between
"written" and "works", and it is one call rather than a guess.

---

## 4. The MCP route, and why it is not used

Both providers offer hosted MCP servers:

- Hostinger: `https://mcp.mail.hostinger.com/mcp` — read and search mail, send and
  manage messages, manage folders and webhooks
- Hostinger's platform connector: `https://mcp.hostinger.com`

**Neither is reachable from this codebase today.** `genesis/integrations/mcp_integration.py`
declares `MCPTransportType.HTTP` and `WEBSOCKET`, but `MCPClient.connect()`
handles only `STDIO`:

```python
elif self.config.transport in [MCPTransportType.HTTP, MCPTransportType.WEBSOCKET]:
    logger.warning(f"HTTP/WS transport not yet implemented for {self.config.name}")
    return False
```

`MCPServerConfig` also requires a `command`, which no remote server has. So the
enum advertises a transport that does not exist, and every hosted MCP endpoint is
unreachable.

**Implementing HTTP/SSE transport is therefore a prerequisite for the MCP route,
not an alternative to the REST one.** Until that lands, the REST adapters are the
only path that works — which is why they were built first. If you want a hosted
MCP server connected, that transport is the work, and it is worth doing on its own
rather than smuggled in beside a provider.

The same applies to the `@hostinger/mcp` npm package: it is a local server, so it
would work over stdio, and it exposes the *hosting* API (372 tools for hosting,
domains and DNS) — not the Mail API. For mail, it is `mcp.mail.hostinger.com`, or
the REST API.

---

## 5. Current limits, stated rather than implied

| Limit | Consequence |
|---|---|
| Outbound rate limits are **in memory** | `InMemoryOutboundLedger.durable` is `False`. The weekly cap and minimum gap do not survive a restart, so they are a per-process floor, not a durable one |
| No webhook ingestion | Inbound is polled. Webhooks are the provider's recommendation and the next phase |
| Attachments are not downloaded | Attachments are not decoded or stored. Decoding arbitrary attachments is a parsing attack surface that belongs behind the sandbox, not in a channel adapter |
| A stranger's reply earns no trust | `DatabaseContacts` returns unknown senders as reply-only with no `consent_source`. Someone writing once does not opt in to being contacted weekly |
| Channel credentials are install-level | Every Mind on an install shares one mailbox and one phone number. `Mind.channels` says so rather than implying isolation |
| Call transcripts are not ingested | Ringg's assistant speaks and the transcript arrives later; nothing fetches it, so a call is an action and not yet a memory |

---

## 6. Answering: what happens when the Mind replies

This is the part an operator most often gets wrong, so it is worth reading before
turning anything on.

### It is off until you turn it on

`MIND_CHANNEL_AUTOREPLY_ENABLED=false` by default. A Mind with credentials can be
*reached*; it does not *answer* until this is set. The default is not timidity: a
Mind that starts answering the moment it has credentials, with no approval policy
configured, raises one approval request per message and looks broken — and with a
policy configured by accident, sends replies nobody reviewed.

`build_poller` returns `None` when this is off **or** when no channel is enabled, so
"answering is off" and "answering is on but there is nothing to read" can never look
the same. Both are logged with the reason.

### Without a standing grant, every reply asks you first

That is the correct default and it is not a bug. `comms.email.reply` is R3, so the
policy engine returns `require_approval` and the gateway records an approval id. The
Mind is waiting for a human, once per message.

### An email reply can never be auto-approved, and a Telegram one can

This is the finding worth knowing about, and it comes from the governance plane
rather than from anything in the channel layer.

`comms.email.reply` declares `data_sensitivity="personal"`, and the policy engine's
sensitivity floor maps `personal` to **R3**. Standing grants are capped at
`STANDING_GRANT_MAX_RISK = R2`. So:

| Action | Risk | Standing grant covers it? |
|---|---|---|
| `comms.telegram.reply` | R2 | **Yes** — a Mind can hold an autonomous conversation |
| `comms.email.reply` | R3 | **No** — every reply needs a human |
| `comms.email.send` / `comms.telegram.send` | R3 | No — starting a conversation always needs a human |

Why the difference is defensible: a reply carries content *outward*, and an email
reply carries personal data across the trust boundary. A Telegram reply is declared
not to. The two declarations differ, so the two behaviours differ.

**What was wrong before this was found.** `comms.email.reply` was declared **R2**
while resolving to **R3**, and the comment beside it said standing grants "already cap
at R2, so that is handled" — true only while the declaration and the behaviour
disagreed. A reader consulting `risk.py` would have concluded an email reply could be
granted standing approval and configured a policy that silently did nothing. The
declaration is R3 now, and `tests/security/test_channel_poller.py` pins the effective
risk of every channel action so the two cannot drift apart again.

The same audit found `comms.email.read` declaring **R0** *and*
`data_sensitivity="personal"`, which resolved to R3 with `require_approval` — a Mind
that could not read its own inbox without a human, contradicting the R0 rationale
written directly above it. The sensitivity floor is about data *crossing a boundary*,
not about data being looked at, so the read no longer declares it.

### If you want autonomous email replies

The change is to `comms.email.reply`'s `data_sensitivity` in
`genesis/governance/risk.py`. That is a governance decision, not a configuration
change, and it should be made deliberately: it removes the control that keeps
personal data from leaving without a human. It is not something to slip in beside a
provider integration.

---

## 7. Answering twice, and why that is the thing to get right

A mailbox is re-read after every restart. So a poller without a ledger re-answers
everything it has already handled, by default, and the person receives duplicate
replies carrying the name of a human administrator. Nothing in the system looks
wrong.

`inbound_events` exists for that. Claiming a message is an `INSERT` and the unique
constraint **is** the "already handled" signal — a `SELECT` before the `INSERT` would
be a race, and two pollers against one mailbox is exactly the configuration where
that race produces the duplicate.

The ledger claims **before** the gateway sees a message, which gives at-most-once
and has a real cost: if the process dies between claiming and sending, the reply is
never sent. The alternatives are worse. Claiming after the send means a crash
re-answers, and a duplicate is externally visible, attributed to a named person, and
cannot be retracted. A missing auto-reply is recoverable by a person reading the
report; a duplicate is not recoverable at all.

A claim with no outcome means the process died mid-flight. Those are reported by
`ChannelPoller` (and journalled as `channel.reply_not_sent`) and **never retried**,
because a retry may answer a message that was already answered before the crash.
Someone has to look. That is the honest option; the alternative is a system that
quietly re-sends and a bug report nobody can reproduce.

Verified by mutation rather than by reading: making the poller ignore the claim fails
3 tests, and making the in-memory ledger claim everything fails 2.

### A mailbox that is unreachable is not an empty mailbox

`PollReport.read_failures` is separate from `received == 0`, and the daemon logs the
difference. Reporting a broken mailbox as "no new mail" is the same class of failure
as reporting a failed fetch as "no calls recorded".

---

## 8. What the Mind is told when it drafts a reply

`MindResponder` composes the prompt, and what it **omits** matters more than what it
includes:

- **No risk level, no approval state, no mention that a gate exists.** A prompt that
  mentioned them invites the model to reason about its own constraints, and a model
  reasoning about its constraints is a model trying to satisfy them conversationally
  — the failure where a Mind explains why it *should* be permitted to do something.
  A test asserts the absence, because an absence is what a reviewer cannot see.
- **Actions are disabled during a draft.** `enable_actions=True` would let cognition
  act while composing, which is a second route to acting that bypasses the channel
  gate: the model could send a message *while drafting* the message.
- **Boundaries are stated as prohibitions**, because a model cannot respect a boundary
  it was never told about, and the failure would look like disregard rather than
  ignorance.
- **Declining is a first-class answer.** The prompt names a sentinel string, and the
  responder returns `None` for it. A responder that could only return text would make
  a Mind that answers everything, including things it should leave alone.
- **The disclosure is not added here.** `apply_disclosure` runs in the adapter.
  Duplicating it would be harmless and is still not done, because harmless duplication
  is how a rule ends up with two definitions.

---

## 9. Turning it on: a checklist

1. Configure a channel (`MIND_HOSTINGER_MAIL_*` or `MIND_TELEGRAM_*`) and confirm
   `GET` the Mind's channel status shows it `enabled` with no reason.
2. Set `MIND_CHANNEL_GRANTED_SCOPES` to the scopes for the channels you enabled.
   Without a scope, every reply is refused for `missing_scope`.
3. Decide the approval policy. Doing nothing means one approval request per message.
   `MIND_CHANNEL_TENANT_POLICY` is how you opt into autonomous replies, and it works
   for Telegram and not for email.
4. Run `adapter.verify()` against each provider **before** enabling the poller, so
   the first thing the loop does is not fail in a way you have to read logs to
   understand.
5. Set `MIND_CHANNEL_AUTOREPLY_ENABLED=true`.
6. Watch the first few passes. The log line is
   `channel poll: N received, N answered, N already handled, N refused, N failed`,
   and `N already handled` rising is the ledger working.
7. Check the journal for `channel.` events. Each reply that was refused records why,
   and each stuck claim is a person who will never get an answer.

**If `N refused` stays at `N received`, read the approval queue.** That is the
expected state without a standing grant, and it is not a fault.

