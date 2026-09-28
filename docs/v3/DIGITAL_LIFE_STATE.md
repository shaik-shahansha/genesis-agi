# Digital Life State — design

> **Status:** designed, not implemented. This document specifies Phase N.
> Nothing here exists in the code yet; where a concept is already partially
> present elsewhere, that is called out explicitly.

## Why this is not "memory"

Genesis has memory that is *good at facts*: deduplicated, decayed, consolidated,
searchable. That is the right substrate for "the user prefers metric units" or
"the deploy failed last Tuesday".

It is the wrong substrate for "I owe Paul a decision by Friday" or "I am
responsible for the classroom's safety" or "I have been meeting Harmen monthly
for two years and our last three conversations went badly".

The difference is not storage, it is **commitment**:

| Memory | Life state |
|---|---|
| Describes | Obliges |
| Has a timestamp and an importance | Has a deadline and an owner |
| Retrieval is a similarity question | Retrieval is a *what am I on the hook for* question |
| Fades when irrelevant | Must **not** fade — forgetting an obligation is a failure, not decay |
| Nobody is accountable for it | A human can be shown exactly what the being promised |

A Mind that only has memory will answer questions well and be unreliable. A Mind
with life state can be *relied on*. That distinction is the product.

This is why "commitments" are a first-class entity rather than a memory with a
tag: **decay must not apply to them**, they need a state machine, and the
governance plane has something to say about creating and breaking them.

## The entities

Seven kinds of state, in rough order of importance.

### 1. Commitments — what the being owes someone

The core new concept. A promise, a deadline, an obligation, with a named
beneficiary and an explicit lifecycle.

```
OPEN → IN_PROGRESS → FULFILLED
                   ├─ MISSED        (deadline passed, not done)
                   ├─ RENEGOTIATED  (beneficiary agreed to a change)
                   └─ WITHDRAWN     (withdrawn, with a reason)
```

Required fields: `beneficiary` (a human or another Mind, not a string),
`deadline` (nullable but explicit when absent), `provenance` (which conversation
or objective created it), `created_at`, `status`.

Two rules that matter more than the schema:

1. **A commitment is created from a human-visible event.** Not inferred silently
   from a phrase in passing. The governance plane already has the machinery: an
   commitment about a third party is at least R2 (it reaches outside the being),
   and one that binds a human is R3.
2. **Missing one is a recorded event, not a silent expiry.** `MISSED` is an
   audit event and appears in the timeline. A being that quietly drops its
   obligations is worse than one that never made them.

Neither exists today. The repo has `goals.py` (aspirations the Mind sets itself)
and `tasks.py` (units of work), and neither carries a beneficiary or an
accountability trail. `commitment.` exists only as an event-type prefix in
`genesis/governance/models.py`.

### 2. Responsibilities — standing obligations

Long-lived, unlike commitments: "I am the Mind for grade 10 science", "I monitor
this inbox", "I keep this workspace tidy".

Distinct from commitments because they have no single completion — they are a
role's ongoing obligations, and they are the reason a being shows up at all
without being prompted.

Partially present: `role.py` has `add_responsibility(str)`, so a responsibility
is a line of text on a role. That is not queryable, not time-bounded, and cannot
be suspended. It needs to become a record with a scope, an owner, and a review
interval.

### 3. Projects — durable containers for work

A project is a container: a goal, a set of commitments, an artifact set, a
timeline, and participants. It is what makes a long effort coherent rather than a
stream of unrelated tasks.

Not present. `goals.py` is the closest, and a project is a goal with membership,
artifacts and a history.

### 4. Habits and routines — recurring behaviour

A schedule plus an intention plus a history of adherence. "Every weekday at 08:00
summarise overnight events."

`life_activities.py` (39 KB) and the circadian machinery in
`consciousness_v2.py` already implement *rhythms* — sleep, reflection, daily
routine. What is missing is the ability for a being (or its owner) to *declare*
a habit, and to see whether it kept it. That is a small addition to something that
already exists, and it is what makes "24/7 autonomy" legible.

### 5. Assets — what the being owns or holds

Files and artifacts it produced, credentials it is allowed to use (by reference,
never by value), environments it occupies, budget it can spend, skills it has.

Mostly present but scattered: the workspace holds files, `essence.py`/`gen.py`
hold the economy, the plugin registry holds capabilities. What is missing is a
single answer to "what does this being have?" — which is exactly the question a
new owner asks, and what an export needs (Phase F).

### 6. Calendar — when things happen

One time axis joining deadlines, habits, and scheduled actions. Without it,
"when is the being busy?" is answered by three different systems.

`action_scheduler.py` and `tasks.py` both carry times today. This is
consolidation, not new construction.

### 7. Relationships — who matters, and how

Covered in detail in Phase O. Summary: `relationships.py` and
`RelationshipRecord` model a *link* and a type. They do not model trust, shared
history, expectations, or what should not be mentioned. The design note is that
relational state belongs **here**, in life state, not in the memory store — a
relationship is not a fact about the world, it is a fact about two beings.

## How governance applies

Life state is where the governance plane earns its keep, and the mapping is
direct:

| Life-state action | Risk | Why |
|---|---|---|
| Read own commitments | R0 | Owner-authorized |
| Create a commitment to your own owner | R1 | Reversible, internal |
| Create a commitment binding a third party | **R2/R3** | Reaches outside the being; a human should see it |
| Mark a commitment fulfilled | R1 | Reversible, internal |
| Mark a commitment withdrawn | R2 (receipt) | Someone was relying on it |
| Create a responsibility with external effect | **R3** | Standing authority to act is the consequential thing |
| Spend from an asset budget | **R3** | Money |
| Attach a credential asset | **R4** | Regulated, and a leak is severe |

This is already expressible with `CapabilityProfile`; the work is declaring the
capabilities, not building new governance.

## Relationship to the existing tree

Be honest about what this is: **two new entities (commitments, projects), two
upgrades of existing concepts (responsibilities, habits), and one consolidation
(assets, calendar).** It is not a greenfield subsystem, and it should not be
implemented as one.

| Concept | Today | Phase N |
|---|---|---|
| Goals | `core/goals.py` | unchanged; projects reference goals |
| Tasks | `core/tasks.py` | unchanged; tasks can satisfy a commitment |
| Routines | `core/life_activities.py`, `consciousness_v2.py` | expose as declarable, tracked habits |
| Responsibilities | `core/role.py` string | first-class record with scope + review interval |
| Relationships | `core/relationships.py` | extended in Phase O |
| Commitments | ✗ | **new** |
| Projects | ✗ | **new** |
| Assets | scattered (workspace, GEN, plugins) | one queryable view |
| Calendar | `action_scheduler.py`, `tasks.py` | one queryable time axis |

## Why this should come before Phase E (memory V3)

This reverses my earlier ordering, and the reasoning is:

1. **Life state defines what memory must serve.** Bi-temporal memory is a
   substantial engineering effort (ADR-0003/0004). Building it before knowing
   whether validity intervals are needed for *commitments* (they are, critically)
   or for *facts* (useful, less critical) risks optimising the wrong axis.
2. **It is the product difference.** Memory V3 makes retrieval better. Life state
   makes the being *reliable*, which is the thing a user can feel on day one.
3. **It is cheap relative to memory V3.** Two new tables, two upgrades, one
   consolidation — against replacing the vector store and adding a temporal graph.

The counter-argument, which is real: commitments benefit from bi-temporal storage
("the deadline was Friday, renegotiated on Thursday") and implementing life state
on the current memory store means migrating it later. That migration is the cost
of doing it in this order, and it is worth paying.

## Non-goals

- **Not an ERP.** No invoicing, no resource planning, no team management.
- **Not a task manager UI.** The workspace shows commitments because a human must
  be able to see what the being owes, not because this is a to-do app.
- **Not autonomous commitment creation.** A being that invents obligations on its
  own is a liability. Commitments come from a human-visible event or the being's
  own explicit proposal, which the governance plane then gates.
- **Not applied to memories.** Existing memory keeps decaying. Only commitments
  are exempt, and that exemption is the whole point.

## Open questions

1. **Who may create a commitment on whose behalf?** A Mind committing its owner
   to something external is exactly the R3 case; a Mind committing *itself* is
   R1. This needs to be explicit in the policy context, not inferred.
2. **How are commitments transferred?** If a being is exported (Phase F), do its
   outstanding commitments transfer, and does the beneficiary get told? Arguably
   an export that silently moves obligations is a governance incident.
3. **Does a retired being's unfulfilled commitments surface anywhere?** Phase C
   (kernel extraction) adds lifecycle states; a retired Mind with open
   commitments should not simply vanish.
4. **How much of the calendar should be shared?** A being that knows its owner is
   busy is useful; a being that mirrors their entire calendar is a privacy
   problem. Default to only what the being was told.
