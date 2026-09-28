# Relationship intelligence — design

> **Status:** designed, not implemented. This specifies Phase O.
> `core/relationships.py` and `RelationshipRecord` already model a *link*; this
> specifies what is missing.

## What exists, and what it cannot express

Today a relationship is a typed edge between two gmids:

```
RelationshipRecord(from_gmid, to_gmid, relationship_type, ...)
```

That answers "are these two connected, and how?" It cannot answer any of the
questions that actually matter when a being acts on someone's behalf:

- How much does this being trust this person's instructions?
- What has this being learned *about* them over time, as distinct from what it
  knows about the world?
- What should it not bring up?
- What has it promised them? *(Phase N — commitments carry a beneficiary, which
  is deliberately a relationship, not a string.)*
- Has it been burned before? A relationship where a request was later disputed
  should not behave identically to one with no history.

The current model reduces a relationship to a label. For an agent that acts with
standing authority, that is the wrong granularity: the label is the least
interesting part.

## What a relationship should hold

Four additions, each with a reason.

### 1. Trust, scoped rather than global

Not "trust = 0.8". Trust is per **domain**, because that is how it actually works:

```
trust(domain="calendar") = high
trust(domain="finance")  = low
trust(domain="health")   = none
```

`none` is a distinct value, not a low number. A being must be able to hold
"this person may move my meetings" and "this person may not instruct me about
money at all" at once — which a single scalar cannot express, and which a global
threshold would get wrong.

This is also the natural input to the policy context: trust is already a field
there (`trust_level`), and scoped trust replaces the guess.

### 2. Relational memory, kept separate from world memory

What a being knows *about a person* — their preferences, their history, what they
have shared — belongs to the relationship, not to general memory.

The reason is retrieval and privacy, and they pull the same way. General memory
degrades with decay and reranking, so a personal detail can fade; a relationship
detail should not. And general memory is searchable by topic, so a personal
detail can surface in an unrelated context; a relationship detail should be
retrieved only when that relationship is in play.

Practically: a `relationship_id` scope on memory writes, resolved as a filter at
retrieval. Not a new store.

### 3. Shared history and expectations

An ordered log of significant exchanges: what was discussed, what was agreed,
what went badly. Not the full transcript — a summary per significant exchange,
because the transcript is already stored elsewhere and duplicating it doubles the
privacy surface.

This is what lets a being say "last time we discussed this you asked me not to
raise it again" and be *correct*, rather than plausibly wrong.

### 4. Boundaries — what not to do

Explicit prohibitions attached to a relationship: topics not to raise, information
not to share, times not to contact.

These are different from trust because they are not inferences. A boundary is
something a person stated, and it must be honoured literally rather than
statistically. It is also the safest possible way to give a user control:
"stop mentioning my health" is a instruction a being can obey exactly.

## How governance applies

Relationship state changes are consequential, because they change what a being is
*allowed to infer*:

| Action | Risk | Why |
|---|---|---|
| Read own relationship summary | R0 | Owner-authorized |
| Add a relationship fact about the owner | R1 | Internal, reversible |
| Record a **boundary** stated by a person | R1 | Reversible, and it *restricts* the being |
| Change a **trust scope** upward | **R3** | Grants authority; needs a human decision |
| Share relational detail with a third party | **R4** | Discloses personal data about someone |
| Create a relationship with a person not yet known | R2 | Reaches outside |

Trust *upward* being R3 while a boundary is R1 is the deliberate asymmetry: it is
always easy to restrict a being and never automatic to expand it.

## The risk worth naming

Relational state is the most sensitive data this project would hold. A being that
models how much it trusts each person, what it has agreed with them, and what they
asked it not to mention is holding a map of someone's relationships.

Consequences that must be designed in, not added later:

1. **Bounds on retention.** Shared history summaries expire; boundaries do not
   (a boundary is a standing instruction).
2. **Scoped export.** Phase F exports a being; a relationship involving a *third
   party* must not travel without their consent. An export that carries "Harmen
   asked me never to mention X" to a new host is a disclosure.
3. **No covert profiling.** Relationship state is visible to the person it is
   about, on request. This is a product property: a being that keeps a private
   assessment of each person is not trustworthy, and the project's own charter
   (Law 4, Truth) forbids it.
4. **Redaction already applies.** Everything here flows through the journal's
   redaction-by-construction path, so relational payloads cannot leak by accident.

## Why Phase O and not earlier

Trust scopes are an input to the policy engine, so they are tempting to build
early. Two reasons not to:

1. **Nothing sets them yet.** A trust scope with no surface to set it is an empty
   field. It becomes useful when the workspace (Phase H) can show a person what
   the being believes about them, and when there is enough history for a scope to
   be earned rather than configured.
2. **Commitments define who matters.** Phase N introduces beneficiaries. Building
   relationship state before commitments exist means guessing which relationships
   need depth.

The one piece worth pulling earlier: **boundaries**. They are cheap, they only
restrict, and they give a user immediate control over a being that is already
acting. They could land with Phase N.
