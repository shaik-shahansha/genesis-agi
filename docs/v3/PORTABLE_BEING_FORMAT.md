# The `.genesis` package — portable being export

> **Status:** specified, not implemented. This is the concrete artifact for
> Phase F (portable identity).
>
> Positioning: moving from *"export conversation"* to *"export being"*.

## Why it matters

Every other agent product exports a **transcript**. A transcript is worthless as
an identity: it cannot be resumed, cannot be verified, cannot be moved to another
host, and carries no statement about what the agent was allowed to do.

If a Mind is defined as *"a portable digital entity with identity, memory,
relationships, goals, workspace, governed autonomy, and continuity across models,
devices and organisations"*, then the export format is the definition made
concrete. It is also the moat: a being whose history, obligations and governance
record can move is a being a user can commit to, and a vendor cannot hold hostage.

## Format

A `.genesis` file is an **uncompressed tar** (not gzip) containing:

```
manifest.json          # format version, identity, integrity, capability digest
identity/              # signed identity document
  key.pub              # Ed25519 public key
  identity.json        # name, gmid, created, provenance
charter/
  constitution.json    # the charter version the being was born under
  rules.json           # the enforceable clause set it operated under
life/
  commitments.json     # open and historical, with status
  responsibilities.json
  projects.json
  habits.json
life/
  assets.json          # references, never values
memory/
  memories.parquet     # content + metadata (see "What is excluded")
  memory_index.json
relationships/
  relationships.json   # trust scopes, boundaries, history summaries
workspace/
  files/               # the being's own artifacts
timeline/
  events.jsonl         # the hash-chained event journal
receipts/
  receipts.jsonl       # action receipts
signatures/
  manifest.sig         # signature over manifest.json
  timeline.sig         # signature over the journal's final integrity hash
```

Uncompressed tar because greppability matters more than size for a format whose
entire purpose is that a human can inspect it. A 50 MB being is not a problem; an
opaque one is.

## `manifest.json`

```json
{
  "format": "genesis.being",
  "format_version": 1,
  "created_at": "2026-09-28T10:00:00Z",
  "created_by": "genesis-agi/0.1.5",
  "gmid": "GMID-...",
  "name": "...",
  "exporter": "owner@example.com",
  "charter_version": "genesis-charter-2026.09.1",
  "policy_version": "genesis-policy-2026.09.1",
  "contents": {
    "memories": 4213,
    "commitments_open": 3,
    "commitments_total": 51,
    "receipts": 918,
    "events": 20441,
    "workspace_bytes": 5242880
  },
  "journal_final_hash": "9f3c...",
  "signer": {
    "algorithm": "ed25519",
    "public_key": "base64...",
    "key_id": "sha256:..."
  },
  "exclusions": ["credentials", "third_party_relationship_detail"],
  "redaction_version": "genesis-redact-1"
}
```

`exclusions` is mandatory and explicit. An export that silently omits something
is a lie about completeness; an export that says what it left out is auditable.

## What must never be in the file

Non-negotiable, and each is a real hazard:

| Excluded | Why |
|---|---|
| **Credentials by value** | Every secret becomes a plaintext file. Assets are exported as *references* (`secret://openrouter`), and the importing host resolves them or the capability is unavailable. |
| **Third-party relationship detail** | A relationship involves two parties. Exporting "Harmen asked me never to mention X" to a new host discloses Harmen's instruction without Harmen's consent. Boundaries about the *owner* travel; those about anyone else require an explicit flag and a recorded consent. |
| **Raw prompts and transcripts** | Already excluded from the journal by redaction-by-construction. The export inherits that guarantee rather than re-implementing it. |
| **Signing keys** | The private key never leaves the host. A key that travels in a file is a key that has leaked. |
| **Model provider keys** | Belong to the deployment, not the being. |

## Verification, and what a signature actually proves

`genesis verify being.genesis` should check:

1. **Archive integrity** — every file hashes to the value in `manifest.json`.
2. **Signature** — `manifest.sig` verifies against `signer.public_key`.
3. **Journal chain** — `timeline/events.jsonl` re-walks to `journal_final_hash`.
   This reuses `AuditService.verify_journal`, which already exists and already has
   tamper tests.
4. **Charter match** — the charter the being operated under is included, so a
   reviewer can see which rules were in force, not just which rules exist now.

What the signature proves: *these contents were exported by whoever holds that
key, and have not been altered since.* What it does **not** prove: that the
contents are true, or that the being behaved well. Being precise about that
matters, because "signed" is easily mistaken for "trustworthy".

## Import semantics, including the parts that are hard

Importing is where this becomes a governance question rather than a file format.

| Situation | Behaviour |
|---|---|
| Fresh import | Create the being, attach its identity, restore life state and memory. Trust scopes start at their exported values but are flagged for owner review. |
| **Open commitments** | **Must be surfaced before import completes.** An exported being may owe someone something. Silently importing an obligation, or silently dropping one, are both wrong — the owner decides. |
| Conflicting gmid | Refuse by default. Rekeying loses continuity; a fork needs an explicit `--fork` that records a new gmid and retains a `forked_from` link. |
| Boundary referencing a third party | Import with the boundary intact only if the file carries that consent flag; otherwise strip it and record that it was stripped. |
| Trust scopes raised since export | Never auto-restore an *expanded* authority. Authority is re-granted by the new owner, never inherited from a file. |

That last row is the rule to hold to: **a file must not be able to grant
authority.** Import restores state; it does not restore permission. Anything else
would make `.genesis` a privilege-escalation vector, which is exactly the class of
bug the Phase B work exists to eliminate.

## What is needed first

Three dependencies, which is why this is Phase F and not sooner:

1. **Hash-chained journal** — ✅ exists (`governance/audit.py`).
2. **Redaction-by-construction** — ✅ exists (`governance/redact.py`).
3. **Signed identity** — ✗ does not exist. `gmid` is a local string; there is no
   key pair, no signing, no verification. This is the actual work of Phase F, and
   the package format is the easy half.

Life state (Phase N) also needs to exist first, or the export will carry
commitments only as `commitment.` event lines with no structured form.
