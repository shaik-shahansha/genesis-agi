# TARGET_ARCHITECTURE.md — Genesis Minds V3

> Logical architecture for the Digital Beings Operating System. This is a **target**, and
> arrivals are gated by the phases in `IMPLEMENTATION_BACKLOG.md`.
>
> Two rules govern every diagram below:
> 1. **The LLM is not the Mind.** It is a replaceable cognitive component.
> 2. **No side effect happens outside the governance control plane.**

---

## 1. Layer model

```mermaid
flowchart TB
  subgraph EXP["Experience Layer"]
    W[Web · Mind Workspace]
    D[Desktop]
    M[Mobile]
    V[Voice · realtime]
    E[Enterprise integrations]
    X[Developer tools · MCP host]
    R[Robot embodiments]
  end

  subgraph GW["Genesis Gateway"]
    REST[REST API]
    WS[WebSocket]
    RTC[WebRTC / media]
    AUTHN[Authentication]
    AUTHZ[Authorization]
    TENANT[Tenant routing]
    SESS[Session routing]
    RL[Rate limiting]
  end

  subgraph RT["Digital Being Runtime"]
    FAC[MindFacade]
    KER[MindKernel]
    COG[CognitionEngine]
    ATT[AttentionEngine]
    GOAL[GoalEngine]
    CMT[CommitmentEngine]
    REF[ReflectionEngine]
    AFF[AffectEngine]
    REL[RelationshipEngine]
    LIFE[LifecycleEngine]
  end

  subgraph STATE["Cognitive State"]
    ID[Identity]
    CONST[Constitution]
    PER[Persona]
    LS[LifeState]
    MEM[Memory]
    RELS[Relationships]
    GOALS[Goals]
    COMM[Commitments]
    PROJ[Projects]
    EXP2[Experiences]
    TL[Timeline]
    WM[World model]
    PREF[Preferences]
    SK[Skills]
    EMB[Embodiments]
  end

  subgraph ACT["Action & Skills"]
    NS[Native skills]
    MCPT[MCP tools]
    HTTP[HTTP tools]
    BR[Browser tools]
    WST[Workspace tools]
    SBT[Sandbox tools]
    CONN[Connectors]
    HUM[Human approvals]
  end

  subgraph GOV["Governance Control Plane"]
    POL[Policy engine]
    PERM[Permission service]
    CONS[Consent service]
    APPR[Approval service]
    RISK[Risk classifier]
    BUD[Budget service]
    AUD[Audit service]
    ESTOP[Emergency stop]
  end

  subgraph PERS["Persistence"]
    PG[(PostgreSQL canonical)]
    PGV[(pgvector)]
    FTS[(Full-text search)]
    GRAPH[(Optional temporal graph)]
    OBJ[(Object storage)]
    JRN[(Event journal)]
    RDS[(Redis — ephemeral only)]
  end

  subgraph EXEC["Execution"]
    SBP[SandboxProvider]
    CNT[Container sandbox]
    DCR[DurableCognitionRuntime]
    MR[Model router]
    CKPT[Workflow checkpointing]
  end

  subgraph OBS["Observability"]
    OTEL[OpenTelemetry]
    LOGS[Structured logs]
    METR[Metrics]
    COST[Cost records]
    REC[Action receipts]
    EVAL[Evaluation results]
  end

  EXP --> GW --> RT
  RT --> STATE
  RT --> GOV
  GOV --> ACT
  ACT --> EXEC
  GOV --> PERS
  STATE --> PERS
  EXEC --> PERS
  RT --> OBS
  GOV --> OBS
  EXEC --> OBS
```

---

## 2. The kernel turn (perception → action → experience)

```mermaid
sequenceDiagram
  participant Src as Perception source
  participant K as MindKernel
  participant A as AttentionEngine
  participant C as CognitionEngine
  participant P as PolicyService
  participant Ap as ApprovalService
  participant Sb as SandboxProvider
  participant Au as AuditService
  participant M as MemoryService

  Src->>K: perceive(PerceptionEvent)
  K->>K: persist event (journal)
  K->>A: attend()
  A-->>K: AttentionFrame
  K->>C: deliberate(frame)
  C->>M: retrieve(scoped, temporal)
  M-->>C: memories + provenance
  C-->>K: Decision (schema-validated)
  K->>P: evaluate_policy(decision)
  P-->>K: PolicyDecision (allow / receipt / approval / deny / estop)
  alt requires approval
    K->>Ap: request_approval(decision)
    Ap-->>K: ApprovalRequest (pending)
    Note over K: execution suspended, durable
    Ap-->>K: approved (bound to params hash, scope, expiry)
  end
  K->>Sb: act(approved_action)
  Sb-->>K: ActionReceipt
  K->>Au: record(receipt)
  K->>M: propose memories (validated before write)
  K->>K: experience(receipt) → reflect()
  K->>K: checkpoint()
```

**Invariants**
- `deliberate()` output is schema-constrained and rejected if invalid. Invalid model output
  is never executed.
- Every `act()` produces a receipt — including blocked, failed, cancelled, and rolled-back
  attempts.
- `ApprovalService` grants bind to a hash of the exact parameters, a scope, and an expiry.
  Changing a material parameter invalidates the grant.
- Reflection produces **proposals only**; it never mutates constitution, policy,
  permissions, ownership, or audit history.

---

## 3. Cognitive modes (state machine)

```mermaid
stateDiagram-v2
  [*] --> DORMANT
  DORMANT --> OBSERVING: meaningful event
  OBSERVING --> RESPONSIVE: user interaction
  OBSERVING --> FOCUSED: authorized objective
  RESPONSIVE --> FOCUSED: objective accepted
  FOCUSED --> REFLECTIVE: objective complete/failed
  REFLECTIVE --> OBSERVING: proposals emitted
  RESPONSIVE --> OBSERVING: turn complete
  FOCUSED --> OBSERVING: objective paused
  DORMANT --> PAUSED: user pause
  OBSERVING --> PAUSED: user pause
  RESPONSIVE --> PAUSED: user pause
  FOCUSED --> PAUSED: user pause
  REFLECTIVE --> PAUSED: user pause
  PAUSED --> OBSERVING: resume
  DORMANT --> EMERGENCY_STOPPED: e-stop
  OBSERVING --> EMERGENCY_STOPPED: e-stop
  RESPONSIVE --> EMERGENCY_STOPPED: e-stop
  FOCUSED --> EMERGENCY_STOPPED: e-stop
  REFLECTIVE --> EMERGENCY_STOPPED: e-stop
  PAUSED --> EMERGENCY_STOPPED: e-stop
  EMERGENCY_STOPPED --> [*]: authorized recovery
```

| Mode | LLM | Side effects | Notes |
|---|---|---|---|
| `DORMANT` | none | none | heartbeat only |
| `OBSERVING` | none | indexing/classification only | deterministic |
| `RESPONSIVE` | yes | policy-gated | direct user turn |
| `FOCUSED` | yes | policy-gated | authorized objective |
| `REFLECTIVE` | yes | proposals only | consolidation |
| `PAUSED` | per policy | none autonomous | user-initiated |
| `EMERGENCY_STOPPED` | none | none | requires authorized recovery |

Maps from today's `AwarenessLevel(DORMANT, PASSIVE, ALERT, FOCUSED, DEEP)`:
`PASSIVE→OBSERVING`, `ALERT→RESPONSIVE`, `DEEP→REFLECTIVE`; `PAUSED`/`EMERGENCY_STOPPED` are new.

**Heartbeat rule:** the heartbeat checks scheduled commitments, pending approvals, workflow
health, retry eligibility, embodiment status, and budget status — and **must not invoke an
LLM unless meaningful work exists.**

---

## 4. Memory architecture

```mermaid
flowchart LR
  subgraph Write["Write pipeline"]
    E[Event / interaction] --> X[Experience extraction]
    X --> C[Candidate proposals]
    C --> D[Deduplication]
    D --> CT[Contradiction detection]
    CT --> S[Sensitivity classification]
    S --> P[Consent + policy validation]
    P --> CW[(Canonical memory write)]
    CW --> V[Vector index]
    CW --> G[Optional graph index]
  end

  subgraph Read["Read pipeline"]
    I[Current intent] --> T[Tenant + ownership filter]
    T --> AC[Access-control filter]
    AC --> TV[Temporal-validity filter]
    TV --> HR[Hybrid retrieval dense+BM25+RRF]
    HR --> RE[Relationship expansion]
    RE --> GE[Goal + project expansion]
    GE --> RK[Ranking]
    RK --> CB[Context budget selection]
    CB --> PA[Provenance attachment]
    PA --> RX[Retrieval explanation]
  end
```

**Canonical memory record** carries: id, mind, tenant, type, content, normalised claims,
source refs, provenance, confidence, importance, sensitivity, access scope, created,
ingested, valid-from, valid-to, last-verified, retention policy, status, superseded-by,
contradiction refs, embedding ref, graph refs, revision number.

**Temporal rule:** the record distinguishes **when the Mind learned it** (ingestion) from
**when it was true in the world** (validity). This is the difference between today's decay
multiplier and a memory that can survive years.

**Authority rule:** the LLM may *propose* new/corrected/superseding/contradicting/forgotten
memories, relationship updates, and preference updates. A **deterministic application
service** validates and applies them. The LLM never mutates canonical memory directly.

**Memory types:** working, episodic, semantic, procedural, prospective (existing) +
relational, autobiographical, constitutional, organizational, embodiment.

**Degradation rule:** the system must function with the temporal graph disabled.

---

## 5. Governance control plane

```mermaid
flowchart TB
  AR[ActionRequest] --> RC[Risk classifier R0–R5]
  RC --> PE[Policy engine]
  CTX[Constitution · tenant policy · permissions · ownership · skill risk · data sensitivity · cost · reversibility · physical impact · lifecycle mode · e-stop · objective scope · budget · server trust] --> PE
  PE --> D{Decision}
  D -->|allow| EX[Execute]
  D -->|allow_with_receipt| EX
  D -->|require_approval| AP[Approval service]
  D -->|deny| BL[Blocked + receipt]
  D -->|emergency_stop| ES[Emergency stop]
  AP -->|approved, bound to params+scope+expiry| EX
  AP -->|rejected/expired| BL
  EX --> RCP[ActionReceipt]
  BL --> RCP
  ES --> RCP
  RCP --> AUD[Audit service → event journal]
```

### Risk levels
| Level | Meaning | Default disposition |
|---|---|---|
| R0 | read-only public / owner-authorized data | allow |
| R1 | reversible inside the Mind's isolated workspace | allow_with_receipt |
| R2 | modifies a connected external workspace | require_approval |
| R3 | external communication, deploy, purchase, privileged admin | require_approval |
| R4 | legal, medical, financial, employment, safety-critical, physical | require_approval + human |
| R5 | prohibited / destructive / constitutionally disallowed | deny / emergency_stop |

### Policy engine
Deterministic Python rules first (fits the current repo, testable, no new runtime).
OPA/Rego adapter optional for enterprise. **A model-based classifier may advise but is never
the final authority.**

### Approval state machine
`PROPOSED → POLICY_EVALUATED → WAITING_FOR_APPROVAL → APPROVED | REJECTED | EXPIRED →
EXECUTING → COMPLETED | FAILED | ROLLED_BACK`

---

## 6. Sandbox architecture

```mermaid
flowchart LR
  REQ[Execution request] --> POL[Policy evaluation]
  POL --> SB[SandboxProvider.create]
  SB --> C1[Non-root user]
  SB --> C2[Read-only base FS]
  SB --> C3[Single temp writable dir]
  SB --> C4[Network: OFF by default]
  SB --> C5[Egress allow-list proxy]
  SB --> C6[CPU/mem/PID/disk/output/time limits]
  SB --> C7[No host env · no host PID/net ns · no devices]
  SB --> C8[No Docker socket]
  C1 & C2 & C3 & C4 & C5 & C6 & C7 & C8 --> RUN[Execute untrusted code]
  RUN --> ART[Declared artifact export only]
  ART --> KILL[Terminate + cleanup]
  KILL --> RCP[ActionReceipt]
```

Providers: local container (first), then gVisor / Kata / Firecracker / managed secure
sandbox behind the same interface. Advanced providers are **not** required for local dev.

**Hard rule:** generated code never executes inside the API, web, cognition, scheduler, or
workflow process.

---

## 7. Identity & portability

```
IdentityManifest {
  global_mind_id, name, creator, owner, guardians,
  birth_record, purpose, values, personality_traits,
  communication_preferences, constitution_ref,
  identity_revisions[], capability_declarations[],
  embodiment_history[], model_history[],
  public_signing_key, content_hashes[], manifest_version
}
```

- Ed25519 signing, verification, rotation, test signer.
- `.genesis` archive: manifest, constitution, revisions, relationships, selected memories +
  metadata, goals, commitments, projects, skill metadata, timeline, embodiment metadata,
  audit export, artifact references.
- `IdentityResolver` interface as the seam for future DID/VC. **W3C DID is not a
  first-stage dependency.**

---

## 8. Model routing

```
ModelRouter.select(task) considers:
  capability · privacy requirement · tenant allowlist · cost budget ·
  latency class · context length · modality · local-vs-remote ·
  data residency · availability · reliability history
```

Deterministic **fake providers** for tests so the entire suite runs without paid keys.
Identity and personality must not change because the provider changed.

---

## 9. Embodiment (Phase L only)

```mermaid
flowchart LR
  SENS[Sensors / simulator] --> ADP[Embodiment adapter]
  ADP --> NPE[Normalized Perception Events]
  NPE --> KER[Mind Kernel]
  KER --> PROP[Proposed Physical Action]
  PROP --> POL[Policy evaluation]
  POL --> HUM[Human approval when required]
  HUM --> SC[Deterministic safety controller]
  SC --> CMD[Bounded robot command]
  CMD --> ACT[Actuators]
```

**The LLM never publishes actuator commands.** The safety controller validates capability,
speed, force, joint limits, collision state, location, restricted zones, human proximity,
battery, emergency stop, command expiry, and approval scope. Physical safety must continue
to function if the LLM, network, Mind service, or cloud is unavailable.

Build order: protocol → fake body → simulator → ROS 2 skeleton → simulation tests → hardware.

---

## 10. Mapping from today's tree

| Target component | Today | Change type |
|---|---|---|
| `MindFacade` | `core/mind.py` `Mind` | wrap (no behaviour change) |
| `MindKernel` | split out of `Mind` + `cognitive_framework.py` | extract |
| `CognitionEngine` | `core/autonomous_reasoner.py`, `intent_classifier.py` | extract |
| `AttentionEngine` | `consciousness_v2.py` `AttentionManager` | rename/extract |
| `AffectEngine` | `core/emotions.py`, `emotional_intelligence.py` | extend (appraisal) |
| `GoalEngine` | `core/goals.py` | move to ORM |
| `CommitmentEngine` | — | new |
| `ReflectionEngine` | — | new |
| `RelationshipEngine` | `core/relationships.py` | wrap |
| `LifecycleEngine` | `core/lifecycle.py` | extend (policies) |
| `MemoryService` | `storage/smart_memory.py` | wrap + new store |
| `PolicyService` | `core/constitution.py` (keyword) | replace |
| `ApprovalService` | — | new |
| `AuditService` | `safety/permissions.py` (JSONL) | replace |
| `SandboxProvider` | `core/code_executor.py` | replace internals, keep facade |
| `DurableCognitionRuntime` | — | new |
| `ModelRouter` | `models/orchestrator.py` | extend |
| `SecretReference` | env vars read directly | new |
| Event journal | — | new |
| OTel | — | new |
| Evals | — | new |

Every one of these is an **extract-and-wrap**, not a rewrite. Existing public API
(`Mind.birth`, `start_living`, `think`, `handle_request`) is preserved via `MindFacade`
throughout.
