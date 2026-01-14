# Kāraka NexusGraph: Foundational Axioms

**Status:** CANONICAL  
**Version:** 3.1  
**Last Updated:** 2026-01-14

This document defines the foundational axioms of the Kāraka NexusGraph system. These axioms are **invariants**—they must not be violated by any implementation, extension, or optimization.

---

## 1. Core Ontological Commitment

### Axiom 1: Event Primacy (The Dhātu Principle)

> **All semantic relations in the ground truth layer are mediated exclusively through events (kriyā).**

This means:
- Entities NEVER connect directly to other entities in the ground truth layer
- Every relationship between entities is expressed through their participation in a shared event
- The kriyā (verb/action) is the nucleus of all relational meaning

**Example:**
```
❌ FORBIDDEN (ground truth):
   Ram ──related_to──> mango
   Ram ──eats──> mango  (entity-entity edge)

✅ REQUIRED (ground truth):
   Ram ──[Kartā]──> EVENT:EAT <──[Karma]── mango
```

**Rationale:**  
This constraint prevents semantic pollution, enforces temporal grounding, and enables proper causal reasoning. Most knowledge graphs allow entity-entity edges for convenience—we reject this because it conflates ground truth with derived views.

---

### Axiom 2: Dual-Layer Architecture

> **The system maintains two distinct layers: Ground Truth (event-mediated) and Views (projected edges).**

```
┌─────────────────────────────────────────────────────────────┐
│                     VIEW LAYER                              │
│  (materialized projections for query convenience)           │
│                                                             │
│  Ram ──husband_of──> Sita      (derived from MARRY event)  │
│  mango ──is_ripe──> true       (derived from STATE event)  │
│                                                             │
│  ⚠️  Views are NEVER treated as source of truth            │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ projection / materialization
                              │
┌─────────────────────────────────────────────────────────────┐
│                   GROUND TRUTH LAYER                        │
│  (event-mediated, dhātu-centric, append-only)               │
│                                                             │
│  EVENT:MARRY                                                │
│  ├─ Kartā: Ram                                              │
│  ├─ Karma: Sita                                             │
│  └─ Locus_Time: t₁                                          │
│                                                             │
│  EVENT:EAT                                                  │
│  ├─ Kartā: Ram                                              │
│  ├─ Karma: mango                                            │
│  └─ Locus_Time: t₂                                          │
└─────────────────────────────────────────────────────────────┘
```

**Invariants:**  
- If a contradiction exists between a view edge and the underlying events, the events are authoritative.
- Ground truth events are **append-only and versioned**, not destructively modified. Corrections create new versions; originals are preserved for audit.

---

### Axiom 3: States Are Degenerate Events (Non-Kāraka)

> **Static properties and states are represented as STATE nodes with temporal bounds. States use STATE-SPECIFIC roles (Holder, Property), NOT kāraka roles.**

**CRITICAL CLARIFICATION:** STATE_EXIST is technically an event node (for temporal tracking), but it does NOT use kāraka roles. This resolves the apparent contradiction with Axiom 11.

"Ram is tall" is **not** a kāraka structure. It is:

```
STATE_EXIST (not an action event)
├─ Holder: Ram           ← NOT a kāraka role
├─ Property: Tall        ← NOT a kāraka role  
├─ Valid_From: t₁
├─ Valid_To: ∞ (or t₂ if state changes)
├─ event_type: state     ← distinguishes from action events
```

**State vs. Action Events:**
| Type | Uses Kārakas | Example |
|------|--------------|---------|
| ACTION_EVENT | YES | EVENT:EAT (Kartā, Karma, etc.) |
| STATE_EXIST | NO | STATE:TALL (Holder, Property) |
| MENTAL_EVENT | LIMITED | DESIRE (Experiencer, Desired_Event) |

**Why this matters:**
- States can change over time
- We can query "when did Ram become tall?"
- We can detect contradictions ("Ram is tall" vs "Ram is short")
- States are tracked like events but don't have action semantics
- The validation rule "every event has at least one kāraka" applies ONLY to ACTION_EVENT nodes

---

## 2. The Eight Kāraka Roles

### Axiom 4: Kārakas Exhaust Event Participation

> **For each event–entity participation, the entity is assigned exactly one of the eight kāraka roles.**

**Note:** An entity *may* participate in the same event with multiple roles in rare constructions (e.g., reflexive actions). In such cases, each participation is recorded as a separate kāraka link.

| # | Sanskrit | English | Definition |
|---|----------|---------|------------|
| 1 | **Kartā** | Agent | Independent actor who initiates the action |
| 2 | **Karma** | Object | Primary target/patient of the action |
| 3 | **Karaṇa** | Instrument | Tool or means used to accomplish the action |
| 4 | **Sampradāna** | Recipient | Beneficiary or destination of the action |
| 5 | **Apādāna** | Source | Origin or point of separation |
| 6 | **Adhikaraṇa (Space)** | Locus_Space | Physical location where action occurs |
| 7 | **Adhikaraṇa (Time)** | Locus_Time | Temporal location when action occurs |
| 8 | **Adhikaraṇa (Topic)** | Locus_Topic | Abstract subject matter of the action |

**Note on Adhikaraṇa Split:**  
Classical Sanskrit grammar has one Adhikaraṇa role. We split it into three sub-types for precision in modern semantic applications. This is a **justified extension**, not a violation of tradition.

### Kāraka Assignment Rules

**Active Voice:**
- Subject → Kartā (Agent)
- Direct Object → Karma (Object)

**Passive Voice:**
- Subject → Karma (Object)
- "by" phrase → Kartā (Agent)
- If no "by" phrase, Agent may be NULL (this is valid)

**Locus Classification Decision Tree:**
```
Q1: Is this a date, time, or duration?
    → YES: Locus_Time
    → NO: Q2

Q2: Can you physically walk into this place?
    → YES: Locus_Space
    → NO: Q3

Q3: Is this an abstract concept, idea, or subject matter?
    → YES: Locus_Topic
```

---

## 3. The Causal Layer

### Axiom 5: Causation Is Event-to-Event

> **Causal relations connect events to events, never entities to entities.**

```
EVENT:GO (Ram going to Lanka)
    │
    ├──[prayojana]──> EVENT:RESCUE (rescuing Sita)
    │                  (purpose/goal)
    │
    └──[kāraṇa]──> EVENT:ABDUCT (Ravana abducting Sita)
                   (mechanistic cause)
```

### The Three Types of "Why" (Sanskrit Causal Taxonomy)

| Sanskrit | Type | Applies To | Example |
|----------|------|------------|---------|
| **Kāraṇa** | Efficient/Mechanistic Cause | Physical events, inanimate actors | "Why did the ball move?" → "It was pushed" |
| **Prayojana** | Purpose/Goal | Intentional agents | "Why did Ram go to Lanka?" → "To rescue Sita" |
| **Hetu** | Reason/Explanation | Discourse, justification | "Why do we believe this?" → "Evidence X" |

**Invariant:**  
The LLM query router must disambiguate which type of "why" is being asked before querying the causal layer.

---

## 4. Graph Topology Constraints

### Axiom 6: No Spurious Edges

> **Every edge in the ground truth layer must be one of:**
> 1. Entity → Event (via a kāraka role)
> 2. Event → Event (via a causal relation)

**Forbidden edge types in ground truth:**
- Entity → Entity (any relation)
- Entity → Property (use STATE event instead)
- Event → Entity (reverse direction—use entity → event)

### Axiom 7: Multi-Role Participation

> **The same entity may participate in multiple events with different roles.**

```
"Ram ate the mango that fell from the tree."

EVENT:EAT
├─ Kartā: Ram
├─ Karma: mango

EVENT:FALL
├─ Kartā: mango      ← same entity, different role
├─ Apādāna: tree
```

This is not a violation—it's correct modeling. Entities are not "owned" by events.

---

## 5. Temporal Semantics

### Axiom 8: Events Are Temporally Anchored

> **Every event has a temporal locus (explicit or implicit).**

If the source text does not specify time:
- Use `Locus_Time: UNSPECIFIED`
- Do not infer or hallucinate temporal information

**Temporal Ordering:**
- Events with explicit times can be ordered
- Events with `UNSPECIFIED` time cannot be reliably ordered
- Cross-document temporal inference requires explicit evidence

---

## 6. Non-Event Knowledge

### Axiom 9: Taxonomies Are Constraints, Not Facts

> **Type hierarchies (is-a relations) are stored as schema constraints, not as event edges.**

```
❌ Do not model as event:
   EVENT:BE_TYPE (mango → Kartā, fruit → Karma)

✅ Model as schema/constraint:
   TYPE_CONSTRAINT: mango ∈ Fruit
```

**Rationale:**  
"A mango is a fruit" is not an event that happened at a time. It's a definitional constraint that governs how mango entities behave in all events.

**Where Constraints Live:**  
Constraints are stored in the **schema/ontology layer** and are applied during validation and inference, not stored as event nodes.

### Axiom 10: Identity Is Derived

> **Identity relations (same-as, alias) are derived from entity resolution, not stored as primitive edges.**

```
"Ram" and "King of Ayodhya" are the same entity.

❌ Do not model as:
   Ram ──same_as──> King of Ayodhya

✅ Model as:
   ENTITY: Ram
   ├─ canonical_name: "Ram"
   ├─ aliases: ["King of Ayodhya", "Raghava", ...]
```

### Axiom 11: Copular Sentences Are Not Kāraka Structures

> **Not every grammatical sentence instantiates a kāraka structure. Copular sentences (role/state assertions) are handled via underlying events or state projections.**

**The Problem:**
```
"Ram is the husband of Sita."
```

This sentence has:
- ❌ No action
- ❌ No change  
- ❌ No event unfolding in time
- ❌ No agent acting on an object

**Key Insight:**  
"Husband" is a **role**, not an **action**. The copular verb "is" does not introduce a kriyā.

**The Rule of Thumb:**
> "Is anything *happening* here, or is something merely *being true*?"
> - If something is **happening** → kriyā → kārakas
> - If something is **being true** → state / role / type → non-kāraka layer

**Handling Copular Sentences:**

| Approach | When To Use | Representation |
|----------|-------------|----------------|
| **Underlying Event** (preferred) | When the role derives from a known event type | Store the generating event (e.g., MARRY) |
| **State Projection** | When event is unknown/irrelevant | Store as derived state with provenance |

**Approach 1: Store the Generating Event (Preferred)**

"Husband" is not primitive—it derives from a marriage event:

```
EVENT:MARRY
├─ Kartā: Ram
├─ Karma: Sita
├─ Locus_Time: t (may be UNSPECIFIED)
├─ Source: inferred_from_text
├─ Confidence: inferred
```

The role assertion "Ram is husband of Sita" becomes a **query-time projection**:
```
IF EXISTS MARRY(Ram, Sita) AND marriage_not_dissolved
→ Ram has_role Husband_of(Sita)
```

**Approach 2: Store as State Projection (When Event Unknown)**

```
StateProjection: SPOUSE_ROLE
├─ Person_A: Ram
├─ Person_B: Sita
├─ Asserted_By: sentence_id
├─ Confidence: asserted (not inferred)
├─ is_derived: TRUE
```

This lives **outside** the Kāraka DB, in the state/projection layer.

**Why This Is Not Information Loss:**

Naive KG stores: `Ram ──husband_of──> Sita`

This cannot answer:
- When did this start?
- Is it still true?
- Who asserted it?
- Can it be revoked?

Our system stores event/state + provenance + temporal bounds.  
**This is strictly more information, not less.**

**Invariant:**  
Never store copular projections as ground truth. Always mark them as derived or inferred.

---

## 7. System Boundaries

### What This System IS

| Capability | Status |
|------------|--------|
| Semantic role extraction | ✅ Core function |
| Event-centric knowledge representation | ✅ Core function |
| Multi-hop reasoning via graph traversal | ✅ Enabled |
| Temporal grounding of facts | ✅ Native |
| Causal chain representation | ✅ Enabled (via causal layer) |
| Audit-ready reasoning traces | ✅ Enabled |
| Contradiction detection | ✅ Enabled |
| Cross-document entity linking | ✅ Enabled |

### What This System IS NOT

| Capability | Status | Alternative |
|------------|--------|-------------|
| General QA chatbot | ❌ Not the goal | Use RAG + LLM |
| Real-time answer generation | ❌ Too slow | Use cached views |
| Axiomatic/mathematical reasoning | ❌ Out of scope | Use rule engines |
| Probabilistic inference | ⚠️ Limited | Confidence scores on causal links |
| Natural language generation | ❌ Not native | LLM synthesis from graph |

### Role of LLMs in This System

> **LLMs are used for semantic normalization and inference at ingestion and query time, but never as sources of ground truth.**

Specifically, LLMs are responsible for:
- **Kriyā normalization:** Mapping surface verbs to root dhātus
- **Copular inference:** Determining underlying events for role assertions
- **Causal disambiguation:** Routing "why" queries to correct causal type
- **Answer synthesis:** Composing natural language from graph traversals

LLM outputs are **validated** before storage. The graph, not the LLM, is authoritative.

---

## 8. Extraction Pipeline Alignment

The extraction pipeline must respect these axioms:

```
Sentence
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Entity Extraction                              │
│  Output: List of entity mentions                │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Kriyā Extraction                               │
│  Output: List of events (root dhātu + tense)    │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Kāraka Linking                                 │
│  Output: Entity → Event edges with roles        │
│  ⚠️ No entity-entity edges produced            │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Causal Relation Extraction (optional phase)    │
│  Output: Event → Event edges with causal type   │
│  (kāraṇa, prayojana, hetu)                      │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│  View Materialization (query-time or batch)     │
│  Output: Projected entity-entity edges          │
│  ⚠️ Marked as derived, not ground truth        │
└─────────────────────────────────────────────────┘
```

---

## 9. Validation Rules

These rules can be enforced programmatically:

### Rule 1: No Direct Entity Edges
```sql
-- Ground truth layer must not contain entity-entity edges
ASSERT NOT EXISTS (
  SELECT 1 FROM ground_truth_edges
  WHERE source_type = 'entity' AND target_type = 'entity'
)
```

### Rule 2: Every Event Has At Least One Kāraka
```sql
-- Every event must have at least one participant
ASSERT NOT EXISTS (
  SELECT 1 FROM events e
  WHERE NOT EXISTS (
    SELECT 1 FROM karaka_links k
    WHERE k.event_id = e.event_id
  )
)
```

### Rule 3: Causal Links Connect Events Only
```sql
ASSERT NOT EXISTS (
  SELECT 1 FROM causal_links c
  WHERE source_type != 'event' OR target_type != 'event'
)
```

### Rule 4: Views Are Marked As Derived
```sql
-- All view-layer edges must have is_derived = TRUE
ASSERT NOT EXISTS (
  SELECT 1 FROM view_edges
  WHERE is_derived = FALSE OR is_derived IS NULL
)
```

---

## 10. Glossary

| Term | Definition |
|------|------------|
| **Kriyā** | An event/action, identified by a root verb (dhātu) |
| **Dhātu** | The verbal root in Sanskrit grammar; the nucleus of action |
| **Kāraka** | A semantic role linking an entity to an event |
| **Kartā** | Agent—the independent initiator of action |
| **Karma** | Object—the primary target of action |
| **Karaṇa** | Instrument—the means by which action is accomplished |
| **Sampradāna** | Recipient—the beneficiary or destination |
| **Apādāna** | Source—the origin or point of separation |
| **Adhikaraṇa** | Locus—the spatial, temporal, or topical setting |
| **Kāraṇa** | (Causal) Efficient/mechanistic cause |
| **Prayojana** | (Causal) Purpose or goal |
| **Hetu** | (Causal) Reason or justification |
| **Ground Truth** | The canonical, event-mediated layer of knowledge |
| **View** | A derived, projected representation for query convenience |
| **Copular Sentence** | A sentence using "is/are/was" that asserts a state or role, not an action |
| **State Projection** | A derived fact about ongoing states, stored with provenance |
| **Eventive** | Describing something happening (action, change) |
| **Stative** | Describing something being true (role, property, type) |
| **Polarity** | Whether an event occurred (positive) or did not occur (negative) |
| **Modality** | The reality status of an event (actual, potential, obligatory, hypothetical) |
| **Confidence** | Evidential basis of an event (explicit, inferred_copular, inferred_causal) |
| **State Lifecycle** | The temporal validity period of a STATE_EXIST event (valid_from → valid_to) |
| **Event Identity** | Criteria for determining if two event mentions refer to the same event |
| **Narrative Atomicity** | Principle that one verb mention = one event (no over-decomposition) |
| **Temporal Frame** | Document-level context (contemporary, historical, fictional) affecting state interpretation |
| **View Coherence** | Property that views stay consistent with their ground truth dependencies |
| **Entity Grounding** | Validation rule that entities must exist in source text |
| **Admissibility** | Validation status of LLM-generated extractions |
| **Event Aspect** | Temporal structure of event: punctual, durative, iterative, or ambient |
| **Mental Event** | Events representing cognitive states: DESIRE, BELIEVE, INTEND, FEAR, DOUBT |
| **Reflexive** | When an entity fills multiple kāraka roles in the same event |
| **Negation Scope** | Whether negation applies to event or to causal/relational edge |
| **Agentless Event** | Event with NULL Kartā and agent_type: unspecified/absent/causative_process |
| **Instance Multiplicity** | Constraint on how many times a kriyā can occur per entity pair |
| **Composite Event** | Multi-sentence action linked as ordered sub-events |
| **Topic-Comment** | Language construction where topic differs from grammatical subject |
| **Co-Kartā** | Co-equal agents in reciprocal actions (marry, fight, meet) |
| **Temporal Constraint** | Relative ordering (before, after, during) stored in constraint layer |
| **Contradiction Protocol** | Rules for resolving conflicting facts with precedence and logging |
| **Quantification** | Quantity modifiers (cardinal, universal, existential) on Karma |
| **Causal Acyclicity** | Invariant that causal graph cannot have cycles |
| **Event Retraction** | Marking events as false/superseded without deletion |

---

## 12. Extended Event Semantics

### Axiom 12: Event Granularity (Narrative Atomicity)

> **One verb mention in the source text = one event in the graph. Event granularity follows narrative structure, not physical decomposition.**

```
"Ram fought Ravana for 10 days."

✅ CORRECT:
EVENT:FIGHT
├─ Kartā: Ram
├─ Karma: Ravana  
├─ Locus_Time: 10 days (duration)
├─ granularity: narrative

❌ WRONG: 10 separate FIGHT events (over-decomposition)
❌ WRONG: 1000 STRIKE events (physical decomposition)
```

**Event Composition Rules:**
| Scenario | Representation |
|----------|----------------|
| Single verb, long duration | One event with duration attribute |
| Explicit sub-events in text | Separate events with `part_of` relation |
| Implicit sub-events | NOT extracted (no hallucination) |

**Sub-event Linking (when explicitly mentioned):**
```
"Ram fought Ravana. On day 5, Ram killed Ravana."

EVENT:FIGHT (e1)
├─ duration: 10 days

EVENT:KILL (e2)
├─ Locus_Time: day 5
├─ part_of: e1
```

---

### Axiom 13: Polarity and Modality

> **Every event carries `polarity` and `modality` metadata. These are not separate events—they are attributes of the event node.**

**Event Polarity:**
| Value | Meaning | Example |
|-------|---------|---------|
| `positive` | Event occurred/is asserted | "Ram ate the mango" |
| `negative` | Event explicitly did NOT occur | "Ram did NOT eat the mango" |

**Event Modality:**
| Value | Meaning | Example |
|-------|---------|---------|
| `actual` | Event factually occurred | "Ram ate the mango" |
| `potential` | Event might occur | "Ram might eat the mango" |
| `obligatory` | Event should/must occur | "Ram should eat the mango" |
| `hypothetical` | Counterfactual event | "If Ram had eaten the mango..." |
| `desired` | Event is wanted | "Ram wants to eat the mango" |

**Example Representation:**
```
"Ram did NOT eat the mango."

EVENT:EAT
├─ Kartā: Ram
├─ Karma: mango
├─ polarity: negative
├─ modality: actual

"Ram might eat the mango."

EVENT:EAT
├─ Kartā: Ram
├─ Karma: mango
├─ polarity: positive
├─ modality: potential
```

**Invariant:** Default values are `polarity: positive` and `modality: actual`. These must be explicitly set for non-default cases.

---

### Axiom 14: Cross-Document Event Identity

> **Two events are the same if and only if they share: (1) the same kriyā, (2) the same core participants (Kartā, Karma), and (3) overlapping temporal locus.**

**Event Identity Criteria:**
```
Same Event IF:
  kriyā_1 = kriyā_2  (same action type)
  AND Kartā_1 ≡ Kartā_2  (same agent, via entity resolution)
  AND Karma_1 ≡ Karma_2  (same object, via entity resolution)  
  AND Locus_Time_1 ∩ Locus_Time_2 ≠ ∅  (temporal overlap)
```

**Example:**
```
Document A: "The king went to the forest in 2024."
Document B: "Ram went to the forest last year."

IF "The king" ≡ "Ram" (via entity resolution)
AND "2024" ∩ "last year" (temporal overlap)
→ These are the SAME event, merged into one node

EVENT:GO (merged)
├─ Kartā: Ram (aliases: ["The king"])
├─ Locus_Space: forest
├─ Locus_Time: 2024
├─ sources: [doc_A, doc_B]
```

**Merge Rules:**
| Scenario | Action |
|----------|--------|
| Identical events from different sources | Merge, record all sources |
| Similar events, different details | Merge, union non-conflicting attributes |
| Conflicting attributes | Flag as contradiction, keep both versions |
| Uncertain temporal overlap | Do NOT merge, keep separate |

---

### Axiom 15: State Lifecycle and Closure

> **STATE_EXIST events have explicit lifecycle management. States are closed by contradiction, supersession, or temporal boundary.**

**State Lifecycle:**
```
STATE_EXIST
├─ holder: entity
├─ property: value
├─ valid_from: timestamp (required)
├─ valid_to: timestamp | OPEN | UNKNOWN
├─ closure_reason: NULL | contradiction | supersession | temporal_bound
```

**Closure Rules:**
| Trigger | Example | Action |
|---------|---------|--------|
| **Explicit negation** | "Ram is no longer tall" | Close state, set `closure_reason: contradiction` |
| **Superseding state** | "Ram became short" | Close old state, create new state |
| **Temporal boundary** | "Ram was tall as a child" | Set `valid_to` from context |
| **Document end** | (no closure trigger) | Set `valid_to: OPEN` (still valid) |

**Contradiction Detection:**
```
STATE_EXIST (s1)
├─ holder: Ram
├─ property: tall
├─ valid_from: t1
├─ valid_to: OPEN

New sentence: "Ram is short."

→ Create STATE_EXIST (s2)
├─ holder: Ram
├─ property: short
├─ valid_from: t2

→ Close s1:
├─ valid_to: t2
├─ closure_reason: supersession
├─ closed_by: s2
```

**Invariant:** States with `valid_to: OPEN` are considered currently true. States with `valid_to: UNKNOWN` require manual verification.

---

### Axiom 16: Possessive and Attributive Constructions

> **Possession is modeled as a STATE_POSSESS event, not an entity-entity edge. Attributive modifiers are properties of the entity mention, not the entity itself.**

**Possessive Constructions:**
```
"Ram's mango fell."

❌ FORBIDDEN:
Ram ──possesses──> mango

✅ REQUIRED:
STATE_POSSESS (implicit, may be inferred)
├─ holder: Ram
├─ possessed: mango
├─ valid_from: UNSPECIFIED
├─ valid_to: OPEN
├─ inference_type: possessive_construction

EVENT:FALL
├─ Kartā: mango
├─ mango.possessor_ref: Ram (entity metadata, not edge)
```

**Attributive Modifiers:**
```
"The ripe mango fell."

Entity: mango
├─ mention_text: "The ripe mango"
├─ attributes: [ripe]  ← attached to mention, not entity

EVENT:FALL
├─ Kartā: mango
```

**Why Mention-Level Attributes:**
- "The ripe mango fell, but the unripe mango stayed."
- Same entity (mango type), different mention attributes
- Attributes describe the mention, not universal entity properties

---

### Axiom 17: Event Confidence Levels

> **Every event has a `confidence` attribute indicating its evidential basis. Confidence affects query ranking but not graph structure.**

**Confidence Levels:**
| Level | Meaning | Example |
|-------|---------|---------|
| `explicit` | Directly stated in text | "Ram ate the mango" |
| `inferred_copular` | Inferred from copular sentence | "Ram is king" → CORONATION inferred |
| `inferred_causal` | Inferred from causal reasoning | Effect implies cause |
| `inferred_temporal` | Inferred from temporal context | Event order implies relationship |
| `asserted` | Stated without textual evidence | User/system assertion |

**Example:**
```
Text: "Ram is the king of Ayodhya."

EVENT:CORONATION
├─ Kartā: (ceremony performer, UNKNOWN)
├─ Karma: Ram
├─ result_role: king
├─ Locus_Space: Ayodhya
├─ Locus_Time: UNSPECIFIED
├─ confidence: inferred_copular
├─ source_sentence: "Ram is the king of Ayodhya"
```

**Query Behavior:**
- `confidence: explicit` events are preferred in answers
- `confidence: inferred_*` events are included but flagged
- Users can filter by confidence level

**Invariant:** Every event MUST have a confidence value. Default is `explicit` for directly extracted events.

---

### Axiom 18: LLM Output Validation Rules

> **LLM-generated extractions must pass admissibility checks before storage. Validation is rule-based, not LLM-based.**

**Admissibility Rules (All Must Pass):**

| Rule | Check | Failure Action |
|------|-------|----------------|
| **Entity Grounding** | Every entity in kāraka links must exist in source text | Reject extraction |
| **Dhātu Normalization** | Normalized verb must be in approved dhātu lexicon | Fallback to surface verb |
| **Role Sanity** | Kartā/Karma must be animate or contextually valid | Flag for review |
| **Temporal Consistency** | Locus_Time must not contradict document metadata | Flag contradiction |
| **No Hallucination** | Event type must be inferable from source text | Reject inferred events beyond one hop |

**Entity Grounding Check:**
```
Source: "Ram ate the mango."
LLM Output: { Kartā: "Ram", Karma: "mango", Karaṇa: "fork" }

❌ REJECTED: "fork" not in source text
✅ VALID: { Kartā: "Ram", Karma: "mango" }
```

**Dhātu Normalization Fallback:**
```
Source: "Ram devoured the mango."
LLM: { kriyā: "devour", normalized_dhātu: "खाद्" }

IF "खाद्" NOT IN approved_dhatu_lexicon:
  → Use surface verb "devour" as dhātu
  → Flag: dhatu_normalization_failed
```

**Hallucination Prevention:**
```
Source: "Ram is the king."

✅ ALLOWED (one-hop inference):
  → Infer CORONATION event with confidence: inferred_copular

❌ FORBIDDEN (multi-hop hallucination):
  → Infer DEFEAT_PREVIOUS_KING event
  → Infer INHERIT_THRONE event
```

**Invariant:** If validation fails, extraction is either rejected or stored with `validation_status: failed` for manual review. Failed extractions are NEVER treated as ground truth.

---

### Axiom 19: Document Temporal Framing

> **Every document has a `temporal_frame` that affects how states are interpreted. Historical documents do not create OPEN states.**

**Temporal Frame Types:**
| Frame | Meaning | State Handling |
|-------|---------|----------------|
| `contemporary` | Document describes current reality | States default to `valid_to: OPEN` |
| `historical` | Document describes past events | States default to `valid_to: DOCUMENT_END_TIME` |
| `fictional` | Document describes non-factual narrative | States marked `reality: fictional` |
| `undated` | Document temporal context unknown | States use `valid_to: UNKNOWN` |

**Example:**
```
Document: "The History of Ayodhya" (temporal_frame: historical, reference_time: 5000 BCE)

Sentence: "Ram was the king of Ayodhya."

STATE_EXIST
├─ holder: Ram
├─ property: king_of_Ayodhya
├─ valid_from: UNSPECIFIED
├─ valid_to: 5000 BCE (from document frame)
├─ temporal_frame: historical
```

**Contemporary Document Example:**
```
Document: "Current Government Officials" (temporal_frame: contemporary)

Sentence: "Modi is the Prime Minister."

STATE_EXIST
├─ holder: Modi
├─ property: prime_minister
├─ valid_from: UNSPECIFIED
├─ valid_to: OPEN
├─ temporal_frame: contemporary
```

**Invariant:** Document `temporal_frame` is set at ingestion time (from metadata or inference) and affects ALL state events from that document.

---

### Axiom 20: View Coherence and Invalidation

> **Views are materialized projections that must stay coherent with ground truth. When ground truth changes, affected views are invalidated and recomputed.**

**View Dependencies:**
```
VIEW: husband_of(Ram, Sita)
├─ depends_on: EVENT:MARRY(Ram, Sita, t₁)
├─ invalidated_by: EVENT:DIVORCE(Ram, Sita, t₂)
├─ invalidated_by: STATE_EXIST(Ram, deceased, t₃)
├─ invalidated_by: STATE_EXIST(Sita, deceased, t₄)
```

**Invalidation Triggers:**
| Ground Truth Change | View Action |
|---------------------|-------------|
| New event added | Check if view derivation still holds |
| State closed | Invalidate views depending on that state |
| Entity merged | Recompute all views involving merged entities |
| Contradiction detected | Flag affected views, do not auto-invalidate |

**Recomputation Strategy:**
| Strategy | When Used |
|----------|-----------|
| `eager` | Critical views (security, compliance) - recompute immediately |
| `lazy` | Non-critical views - recompute on next query |
| `batch` | Analytics views - recompute on schedule |

**Example: Divorce Invalidates Husband View:**
```
Ground Truth (t₁):
  EVENT:MARRY(Ram, Sita, t₁)
  
View (t₁):
  husband_of(Ram, Sita) ← VALID

Ground Truth (t₂):
  EVENT:DIVORCE(Ram, Sita, t₂)
  
View (t₂):
  husband_of(Ram, Sita) ← INVALIDATED
  former_husband_of(Ram, Sita) ← NEW VIEW CREATED
```

**Version Dependencies:**
```
VIEW
├─ view_id: v_123
├─ projection_type: husband_of
├─ depends_on_events: [e_456]
├─ valid_from_version: 3
├─ valid_to_version: 7 (invalidated at v7)
├─ invalidation_reason: "DIVORCE event e_789 added"
```

**Invariant:** Views NEVER outlive their ground truth dependencies. If a view's derivation no longer holds, the view MUST be invalidated (not silently stale).

---

## 13. Edge Case Axioms

### Axiom 21: Event Aspect Classification

> **Events are classified by aspect type: PUNCTUAL, DURATIVE, ITERATIVE, or AMBIENT. This affects granularity interpretation.**

**Aspect Types:**
| Type | Definition | Example | Granularity Rule |
|------|------------|---------|------------------|
| `punctual` | Instantaneous event | "Ram struck Ravana" | One event per mention |
| `durative` | Event with inherent duration | "Ram fought Ravana for 10 days" | One event with duration attribute |
| `iterative` | Repeated instances of same action | "Ram breathed while fighting" | One event with `iteration: ambient` |
| `ambient` | Background/continuous process | "The sun shone during the battle" | One event, duration inherited from context |

**Example:**
```
"Ram breathed while fighting Ravana for 10 days."

EVENT:FIGHT
├─ aspect: durative
├─ duration: 10 days

EVENT:BREATHE
├─ aspect: ambient
├─ iteration: continuous
├─ during_event: EVENT:FIGHT  ← temporal anchor, not counted
```

**Query Behavior:**
- "How many times did Ram breathe?" → UNANSWERABLE (ambient event)
- "Did Ram breathe during the fight?" → YES (ambient during durative)

---

### Axiom 22: State Taxonomy and Origin Requirements

> **States are classified by category. Some categories REQUIRE underlying events; others are PRIMITIVE.**

**State Categories:**
| Category | Examples | Underlying Event | Treatment |
|----------|----------|------------------|-----------|
| **Biological** | tall, old, alive | Optional (GROW, AGE, BE_BORN) | Primitive allowed |
| **Relational** | married, employed, owner | REQUIRED (MARRY, HIRE, ACQUIRE) | Must infer event |
| **Emotional** | angry, happy, sad | Optional (context-derived) | Primitive allowed |
| **Physical** | ripe, broken, frozen | REQUIRED (RIPEN, BREAK, FREEZE) | Must infer event |
| **Social Role** | king, president, CEO | REQUIRED (CORONATION, ELECTION, APPOINTMENT) | Must infer event |
| **Locational** | in Paris, at home | Optional (MOVE, TRAVEL) | Primitive allowed |

**Examples:**
```
"Ram is tall." → STATE_EXIST (biological, primitive OK)
"Ram is king." → Infer EVENT:CORONATION (social role, required)
"The mango is ripe." → Infer EVENT:RIPEN (physical, required)
"Ram is angry." → STATE_EXIST (emotional, primitive OK)
```

---

### Axiom 23: Multi-Causal Relations

> **A single event may have MULTIPLE causal relations of DIFFERENT types simultaneously. Causal links are not mutually exclusive.**

**Example:**
```
"Ram killed Ravana because Ravana kidnapped Sita."

EVENT:KILL
├─ Kartā: Ram
├─ Karma: Ravana
├─ causal_links:
│   ├─ [prayojana] → EVENT:RESCUE_SITA (Ram's goal)
│   ├─ [kāraṇa] → EVENT:KIDNAP (triggering cause)
│   └─ [hetu] → MORAL_JUSTIFICATION (dharmic duty)
```

**Invariant:** When extracting causation, LLM should identify ALL applicable causal types, not select one.

---

### Axiom 24: Event Uniqueness Constraints

> **Each kriyā type has an INSTANCE_MULTIPLICITY that constrains merging behavior.**

**Multiplicity Types:**
| Type | Meaning | Examples | Merge Rule |
|------|---------|----------|------------|
| `singleton` | At most one per entity pair | MARRY, DIE, BE_BORN | Merge if participants match |
| `bounded` | Countable instances per timeframe | EAT_MEAL (3/day typical) | Merge only if within same instance window |
| `unbounded` | Unlimited instances | SPEAK, WALK, THINK | Do NOT merge by default |

**Examples:**
```
Doc A: "Ram married Sita."
Doc B: "Ram and Sita got married."
→ MERGE (MARRY is singleton)

Doc A: "Ram ate a mango."
Doc B: "Ram ate a mango."
→ DO NOT MERGE unless same day/context (EAT is bounded)
```

---

### Axiom 25: Modal Stacking via Mental Events

> **Nested modalities are represented as MENTAL EVENTS (desire, belief, plan) that embed other events.**

**Mental Event Types:**
| Type | Meaning | Example |
|------|---------|---------|
| DESIRE | Want something to happen | "Ram wants to eat" |
| BELIEVE | Think something is true | "Ram believes Sita is safe" |
| INTEND | Plan to do something | "Ram intends to fight" |
| FEAR | Worry something will happen | "Ram fears Sita is captured" |
| DOUBT | Uncertain about something | "Ram doubts Ravana is honest" |

**Nested Modal Example:**
```
"Ram could have eaten the mango, but he might not have wanted to."

EVENT:EAT
├─ Kartā: Ram
├─ Karma: mango
├─ modality: potential
├─ polarity: positive (the eating itself)

MENTAL_EVENT:DESIRE
├─ experiencer: Ram
├─ desired_event: EVENT:EAT
├─ modality: potential  ← "might"
├─ polarity: negative   ← "not wanted"
```

---

### Axiom 26: Reflexive Action Marking

> **When an entity fills multiple kāraka roles in the same event, the participation is marked with `reflexive: true`.**

**Example:**
```
"Ram hurt himself."

EVENT:HURT
├─ Kartā: Ram
├─ Karma: Ram
├─ reflexive: true
├─ kāraka_links:
│   ├─ {entity: Ram, role: Kartā, reflexive: false}
│   └─ {entity: Ram, role: Karma, reflexive: true}  ← flagged
```

**Query Handling:**
- "Who did Ram hurt?" → "himself (reflexive)"
- "Who hurt Ram?" → "himself (reflexive)"

---

### Axiom 27: Negation Scope (Event vs. Relation)

> **Negation can apply to EVENT (the action didn't happen) or to RELATION (the relation doesn't hold). These are distinguished.**

**Negation Types:**
| Type | Example | Representation |
|------|---------|----------------|
| **Event Negation** | "Ram did NOT eat" | `EVENT:EAT (polarity: negative)` |
| **Causal Negation** | "Ram ate, but NOT because of hunger" | Causal edge with `negated: true` |
| **Role Negation** | "Not Ram (someone else) ate" | Different Kartā, not negation |

**Causal Negation Example:**
```
"Ram did not eat the mango because he was hungry."
(Meaning: Ram DID eat, but hunger was NOT the reason)

EVENT:EAT
├─ Kartā: Ram
├─ Karma: mango
├─ polarity: positive  ← he DID eat

CAUSAL_LINK
├─ source: EVENT:EAT
├─ target: STATE:HUNGRY(Ram)
├─ type: kāraṇa
├─ negated: true       ← the causal relation is negated
```

---

### Axiom 28: Implicit Participant Nodes

> **When a participant exists but is not mentioned, create an IMPLICIT node. Distinguish from truly absent participants.**

**Implicit Participant Types:**
| Type | Meaning | Example |
|------|---------|---------|
| `implicit_agent` | Actor exists but unnamed | "The mango was eaten" |
| `implicit_recipient` | Beneficiary exists but unnamed | "The gift was given" |
| `implicit_instrument` | Tool used but unnamed | "The door was opened" |
| `absent` | No such participant exists | "The ice melted" (no agent) |

**Example:**
```
"The mango was eaten."

EVENT:EAT
├─ Kartā: IMPLICIT_AGENT_001
├─ Karma: mango
├─ agent_type: implicit_agent
├─ agent_mentioned: false

"The ice melted."

EVENT:MELT
├─ Kartā: ice
├─ agent_type: absent  ← no external agent, ice melted itself
```

---

### Axiom 29: Relative Temporal Ordering

> **When absolute time is UNSPECIFIED but relative order IS given, capture ordering relations between events.**

**Temporal Relation Types:**
| Relation | Meaning | Linguistic Marker |
|----------|---------|-------------------|
| `before(e1, e2)` | e1 happened before e2 | "then", "after which", "subsequently" |
| `after(e1, e2)` | e1 happened after e2 | "after", "following" |
| `during(e1, e2)` | e1 happened during e2 | "while", "during", "as" |
| `simultaneous(e1, e2)` | e1 and e2 at same time | "at the same time", "meanwhile" |

**Example:**
```
"Ram ate the mango. Then he went to the forest."

EVENT:EAT (e1)
├─ Locus_Time: UNSPECIFIED

EVENT:GO (e2)
├─ Locus_Time: UNSPECIFIED
├─ temporal_relations:
│   └─ after(e1)  ← e2 happened after e1

Raw ordering: [e1, e2] where e1 < e2
```

---

### Axiom 30: Language-Specific Kāraka Mapping

> **Kāraka assignment rules vary by language typology. The system maintains language-specific mapping profiles.**

**Language Typologies:**
| Type | Languages | Subject Handling |
|------|-----------|------------------|
| **Nominative-Accusative** | English, Hindi, Sanskrit | Subject of transitive = Kartā |
| **Ergative-Absolutive** | Basque, Georgian, Hindi (perfective) | Subject of transitive = marked differently |
| **Topic-Prominent** | Japanese, Korean, Mandarin | Topic ≠ Agent necessarily |

**Hindi Ergative Example:**
```
Hindi: "राम ने आम खाया" (Rām ne ām khāyā)
Literal: "Ram ERG mango ate"

The "ne" marker indicates ERGATIVE case (perfective tense).
Subject "Ram" is STILL Kartā, but marked with ergative.

EVENT:EAT
├─ Kartā: Ram
├─ Karma: mango
├─ language: Hindi
├─ case_marking: ergative
```

**Japanese Topic Example:**
```
Japanese: "象は鼻が長い" (Zō wa hana ga nagai)
Literal: "Elephant TOPIC nose SUBJ long"

The elephant is TOPIC, not necessarily agent.

STATE_EXIST
├─ holder: elephant.nose
├─ property: long
├─ topic: elephant  ← separate from kāraka role
├─ language: Japanese
├─ construction: topic-comment
```

**Invariant:** Extraction prompts MUST specify source language, and kāraka assignment uses language-appropriate rules.

---

### Axiom 31: Event Composition and Sequence

> **When multiple sentences describe sub-events of a single complex action, they MAY be linked as a COMPOSITE EVENT.**

**Composition Types:**
| Type | Meaning | Example |
|------|---------|---------|
| `sequence` | Ordered sub-events of one action | "picked up bow, aimed, fired" |
| `parallel` | Simultaneous sub-actions | "walked and talked" |
| `causal_chain` | Each event causes the next | "dropped cup, cup broke, spilled water" |

**Example:**
```
"Ram picked up the bow. He aimed. He fired. The arrow struck Ravana."

COMPOSITE_EVENT: SHOOT_RAVANA
├─ composition_type: sequence
├─ sub_events:
│   ├─ EVENT:PICK_UP (bow)
│   ├─ EVENT:AIM
│   ├─ EVENT:FIRE
│   └─ EVENT:STRIKE (arrow → Ravana)
├─ overall_kartā: Ram
├─ overall_karma: Ravana

Individual events ALSO exist as separate nodes.
Composite provides query shortcut: "How did Ram kill Ravana?" → returns composite
```

**Invariant:** Composite events are DERIVED from atomic events, not replacements. Both levels are queryable.

---

## 13.5 Critical Amendments (v3.1)

These axioms address system-breaking edge cases identified through adversarial analysis.

### Axiom 32: Agentless Events (No Phantom Entities)

> **When an agent is genuinely absent or unspecified, use `agent_type: unspecified` or `agent_type: causative_process`. Do NOT create IMPLICIT_AGENT nodes.**

**Amendment to Axiom 28:** IMPLICIT_AGENT nodes are deprecated. Use these types instead:

| Type | Meaning | Example | Representation |
|------|---------|---------|----------------|
| `unspecified` | Agent exists but text doesn't say who | "The mango was eaten" | Kartā: NULL, agent_type: unspecified |
| `absent` | No agent (natural process) | "The ice melted" | Kartā: NULL, agent_type: absent |
| `causative_process` | Caused by process, not entity | "The bridge collapsed" | Kartā: NULL, agent_type: causative_process |
| `collective` | Agent is unnamed group | "The city was destroyed" | Kartā: NULL, agent_type: collective |

**Example:**
```
"The mango was eaten."

EVENT:EAT
├─ Kartā: NULL
├─ agent_type: unspecified
├─ Karma: mango

NOT:
├─ Kartā: IMPLICIT_AGENT_001  ❌ DEPRECATED
```

**Invariant:** NULL Kartā is valid for passive/agentless constructions. This does NOT violate kāraka completeness because Karma is still present.

---

### Axiom 33: Reciprocal Verbs (Co-Participant Role)

> **For symmetric/reciprocal actions where multiple entities are co-equal agents, use the CO-PARTICIPANT role.**

**New Role: Co-Kartā (Co-Agent)**

Reciprocal verbs where both entities are equally agents:
- marry, fight, converse, meet, collaborate

```
"Ram and Sita married."

EVENT:MARRY
├─ Co-Kartā: [Ram, Sita]  ← both are agents
├─ reciprocal: true
├─ individual_roles: NULL  ← no Kartā/Karma distinction

NOT:
├─ Kartā: Ram, Karma: Sita  ❌ WRONG (asymmetric)
```

**Asymmetric Interpretation Override:**
```
"Ram married Sita." (implies Ram initiated)

EVENT:MARRY
├─ Kartā: Ram (initiator)
├─ Karma: Sita (participant)
├─ reciprocal: true
├─ asymmetric_voice: active
```

---

### Axiom 34: Temporal Constraint Layer

> **Relative temporal orderings are CONSTRAINTS, not event metadata. They live in a separate CONSTRAINT layer and are resolved by a reasoner.**

**Three-Layer Temporal Model:**
```
LAYER 1: EVENT_TIMES (ground truth)
├─ Events with explicit Locus_Time values

LAYER 2: TEMPORAL_CONSTRAINTS (assertions)
├─ before(e1, e2)
├─ after(e1, e2)
├─ during(e1, e2)
├─ simultaneous(e1, e2)

LAYER 3: INFERRED_TIMES (derived, materialized)
├─ Computed by constraint solver when explicit times added
├─ Marked as derived, not ground truth
```

**Example:**
```
"Ram ate. Then he slept."

EVENTS:
├─ EVENT:EAT (Locus_Time: UNSPECIFIED)
├─ EVENT:SLEEP (Locus_Time: UNSPECIFIED)

CONSTRAINTS:
├─ before(EAT, SLEEP)

Later: "Ram slept at 10 PM."

EVENTS (updated):
├─ EVENT:SLEEP (Locus_Time: 22:00)

INFERRED (by reasoner):
├─ EVENT:EAT (Locus_Time: < 22:00)
├─ inference_type: constraint_propagation
├─ is_derived: true
```

**Contradiction Detection:**
```
If: before(e1, e2) AND Locus_Time(e1) > Locus_Time(e2)
→ TEMPORAL_CONTRADICTION flagged
→ Both events marked for review
→ No automatic resolution
```

---

### Axiom 35: Contradiction Resolution Protocol

> **When contradictions are detected, apply resolution rules in order. If no rule applies, flag for manual review.**

**Resolution Precedence:**
| Priority | Rule | Example |
|----------|------|---------|
| 1 | **Temporal Recency** | Later document wins | Doc(2025) > Doc(2024) |
| 2 | **Explicit > Inferred** | Stated facts beat inferences | "Ram is king" > inferred from "son of king" |
| 3 | **Domain Authority** | Verified source wins | Medical journal > blog |
| 4 | **Specificity** | More specific wins | "Ram is 6 feet tall" > "Ram is tall" |
| 5 | **Manual Review** | If none apply | Flag CONTRADICTION_UNRESOLVED |

**Contradiction Tracking:**
```
CONTRADICTION
├─ id: c_001
├─ conflicting_facts: [STATE:tall(Ram), STATE:short(Ram)]
├─ resolution_status: resolved | unresolved | manual_override
├─ applied_rule: temporal_recency
├─ winner: STATE:short(Ram)
├─ loser_status: superseded (not deleted)
```

**Invariant:** Contradictions are NEVER silently resolved. All resolutions are logged with justification.

---

### Axiom 36: Quantification Support

> **Quantity modifiers are stored as Karma attributes, not as event multiplication or separate entities.**

**Quantity Types:**
| Type | Example | Representation |
|------|---------|----------------|
| Cardinal | "3 mangoes" | quantity: 3, quantity_type: exact |
| Universal | "all mangoes" | quantity: ALL, quantity_type: universal |
| Existential | "some mangoes" | quantity: SOME, quantity_type: existential |
| Negative | "no mangoes" | quantity: ZERO, polarity: negative |
| Proportional | "most mangoes" | quantity: MOST, quantity_type: proportional |

**Example:**
```
"Ram ate three mangoes."

EVENT:EAT
├─ Kartā: Ram
├─ Karma: mango
│   ├─ quantity: 3
│   ├─ quantity_type: exact
├─ polarity: positive

NOT:
├─ 3 separate EAT events  ❌ WRONG
```

---

### Axiom 37: Causal Acyclicity

> **The causal graph MUST be acyclic. Cycles are detected and flagged as CAUSAL_PARADOX.**

**Cycle Detection:**
```
If path exists: e1 →[causes]→ e2 →[causes]→ ... →[causes]→ e1
→ CAUSAL_PARADOX detected
→ Most recently added edge flagged as SUSPECT
→ Manual review required
```

**Legitimate Feedback Loops:**
```
"Poverty causes crime, which causes poverty."

This is NOT a cycle of the SAME events.
These are:
├─ STATE:POVERTY (general) →[causes]→ CRIME_PATTERN (general)
├─ CRIME_PATTERN (general) →[causes]→ STATE:POVERTY (intensified)

Different event instances, different times.
Not a paradox.
```

**True Paradox:**
```
"Event A caused Event A."
→ Self-causation is FORBIDDEN
→ Flagged as extraction error
```

---

### Axiom 38: Event Retraction Protocol

> **Events can be marked as RETRACTED when proven false. Retracted events are excluded from queries by default.**

**Retraction Status:**
| Status | Meaning | Query Visibility |
|--------|---------|------------------|
| `active` | Normal event | Always visible |
| `retracted` | Proven false | Hidden by default |
| `disputed` | Contested | Visible with warning |
| `superseded` | Replaced by correction | Hidden, linked to successor |

**Retraction Record:**
```
EVENT:KILL (retracted)
├─ status: retracted
├─ retraction_reason: "Source document was fabricated"
├─ retracted_at: t
├─ retracted_by: user_id | system_validation
├─ original_preserved: true
```

**Invariant:** Retracted events are NEVER deleted. They are marked and hidden. Full audit trail preserved.

---

### Axiom 39: Reflexive Semantics (Beyond Boolean)

> **Reflexive actions are categorized by type to support semantic disambiguation.**

**Reflexive Types:**
| Type | Meaning | Example |
|------|---------|---------|
| `intentional_self_action` | Deliberate self-targeting | "Ram praised himself" |
| `accidental_self_action` | Unintended self-targeting | "Ram tripped himself" |
| `self_harm_voluntary` | Deliberate self-harm | "Ram starved himself" |
| `self_harm_involuntary` | Accidental self-harm | "Ram cut himself (by accident)" |
| `reflexive_benefactive` | Self-benefit | "Ram cooked for himself" |
| `introspective` | Mental self-reference | "Ram knows himself" |

**Example:**
```
"Ram killed himself."

EVENT:KILL
├─ Kartā: Ram
├─ Karma: Ram
├─ reflexive_type: self_harm_voluntary | self_harm_involuntary
├─ requires_disambiguation: true (if context insufficient)
```

**Query Handling:**
```
"Who killed Ram?"
→ "Ram (self, voluntary)" OR "Ram (self, accidental)"
→ Disambiguation based on reflexive_type
```

---

## 14. Instrumentation Metrics (For Prototype)

During prototype implementation, track these failure/calibration metrics:

| Metric | What It Measures | Target |
|--------|------------------|--------|
| **Copular Fallback Rate** | % of copular sentences stored as state projections (not events) | < 30% |
| **Entity Edge Leakage** | Count of entity-entity edges in ground truth (should be 0) | 0 |
| **LLM Normalization Rejection Rate** | % of LLM dhātu outputs rejected by validation | < 10% |
| **State Closure Backlog** | Count of STATE_EXIST events with `Valid_To = ∞` after document completion | Monitor |
| **Kāraka Ambiguity Rate** | % of participations requiring human disambiguation | < 5% |
| **Agentless Event Rate** | % of passive sentences with agent_type: unspecified | Monitor |
| **Temporal Order Capture Rate** | % of "then/after/before" markers correctly captured | > 90% |
| **Composite Event Detection** | % of multi-sentence actions linked as composites | Monitor |
| **Contradiction Detection Rate** | Count of CONTRADICTION records created | Monitor |
| **Causal Cycle Detection** | Count of CAUSAL_PARADOX flags raised | 0 (should be rare) |

These metrics will inform v3.x amendments

---

## 14. References

- Pāṇini's Aṣṭādhyāyī (सूत्र on kāraka: 1.4.23–1.4.55)
- Modern Semantic Role Labeling (SRL) theory
- Event-centric knowledge representation (Davidson, 1967)
- Temporal databases and bi-temporal modeling

---

## 15. Amendment Process

To modify these axioms:
1. Propose the change with rationale
2. Demonstrate that it does not violate existing invariants
3. Update this document with version increment
4. Update all extraction prompts and validation rules

**These axioms are the constitution of the system. They are not guidelines.**

---

*End of Document*

