# Kāraka Axiom → Pāṇinian Layer Mapping

**Version:** 1.0  
**Date:** 2026-01-14  
**Purpose:** Map the 39 axioms from `karaka-axioms.md` to Pāṇinian governance layers

---

## Executive Summary

The current `karaka-axioms.md` contains **39 axioms** that can be organized into Pāṇini's three-layer architecture:

| Layer | Purpose | Count | Character |
|-------|---------|-------|-----------|
| **Foundation (Layer 1)** | Immutable primitives | 8 | Like Śiva Sūtrāṇi |
| **Operational (Layer 2)** | Domain rules with scope | 24 | Like Sūtras |
| **Meta-Governance (Layer 3)** | Rules about rules | 7 | Like Paribhāṣā |

**Key Finding:** Most axioms (24) are **Operational** — they're domain-specific rules that could have scope markers. Only 8 are truly **Foundational** (immutable primitives).

---

## Layer 1: Foundation (Śiva Sūtrāṇi Equivalent)

These are the **immutable ontological commitments** — the primitives from which everything else derives. They should NEVER change during operation.

### ✅ Foundational Axioms (8)

| # | Axiom | Justification |
|---|-------|---------------|
| **1** | Event Primacy (Dhātu Principle) | Core ontological commitment — all meaning is event-mediated |
| **2** | Dual-Layer Architecture | Fundamental structure — Ground Truth vs Views |
| **3** | States Are Degenerate Events | Defines the entity space (ACTION_EVENT vs STATE_EXIST) |
| **4** | Kārakas Exhaust Event Participation | Defines the 8 primitive roles (like phoneme inventory) |
| **5** | Causation Is Event-to-Event | Defines causal primitives (kāraṇa, prayojana, hetu) |
| **6** | No Spurious Edges | Graph topology constraint (fundamental structure) |
| **7** | Multi-Role Participation | Entities are not "owned" by events (basic entity semantics) |
| **8** | Events Are Temporally Anchored | Time is primitive dimension |

### Why These Are Foundation

```
These axioms define the PRIMITIVES:
├─ What exists: Events, Entities, States
├─ What roles exist: 8 Kārakas + state-specific roles
├─ What relations exist: Kāraka links, Causal links
├─ What structure exists: Ground Truth + Views

Like Śiva Sūtrāṇi:
├─ Define the alphabet (primitives)
├─ Everything else is COMPOSITION of these
├─ Cannot change without rebuilding entire system
```

### Foundation Layer Properties

```
INVARIANT: ∀p ∈ Foundation: ¬Modifiable(p) during operation
EXCEPTION: Only via Phase 0 revision protocol (extreme)
```

---

## Layer 2: Operational (Sūtra Equivalent)

These are **rules that operate on the foundation** — they have scope (adhikāra), can be revised, and govern specific domains.

### 📋 Operational Axioms (24)

#### A. SCOPE: Type/Taxonomy (4 axioms)

| # | Axiom | Scope | Notes |
|---|-------|-------|-------|
| **9** | Taxonomies Are Constraints | Schema Layer | Defines is-a as constraint, not event |
| **10** | Identity Is Derived | Entity Resolution | Aliases are entity attributes |
| **11** | Copular Sentences Are Not Kāraka | Linguistic Parsing | "is" doesn't create kriyā |
| **22** | State Taxonomy and Origin | State Classification | Which states need underlying events |

#### B. SCOPE: Extended Event Semantics (6 axioms)

| # | Axiom | Scope | Notes |
|---|-------|-------|-------|
| **12** | Event Granularity (Narrative Atomicity) | Narrative Extraction | One verb = one event |
| **13** | Polarity and Modality | Event Metadata | polarity/modality attributes |
| **14** | Cross-Document Event Identity | Entity/Event Resolution | Merge criteria |
| **15** | State Lifecycle and Closure | State Management | valid_from/valid_to semantics |
| **16** | Possessive and Attributive | Linguistic Parsing | Possession as STATE_POSSESS |
| **17** | Event Confidence Levels | Provenance | explicit/inferred markers |

#### C. SCOPE: Validation (3 axioms)

| # | Axiom | Scope | Notes |
|---|-------|-------|-------|
| **18** | LLM Output Validation Rules | Extraction Pipeline | Admissibility checks |
| **19** | Document Temporal Framing | Document Context | contemporary/historical/fictional |
| **20** | View Coherence and Invalidation | View Layer | When views expire |

#### D. SCOPE: Event Aspect & Classification (5 axioms)

| # | Axiom | Scope | Notes |
|---|-------|-------|-------|
| **21** | Event Aspect Classification | Event Typing | punctual/durative/iterative/ambient |
| **23** | Multi-Causal Relations | Causal Layer | Multiple causes allowed |
| **24** | Event Uniqueness Constraints | Event Merging | singleton/bounded/unbounded |
| **25** | Modal Stacking via Mental Events | Modal Logic | DESIRE/BELIEVE/INTEND as events |
| **31** | Event Composition and Sequence | Complex Events | COMPOSITE_EVENT linking |

#### E. SCOPE: Linguistic Specifics (3 axioms)

| # | Axiom | Scope | Notes |
|---|-------|-------|-------|
| **26** | Reflexive Action Marking | Reflexive Constructions | reflexive: true flag |
| **27** | Negation Scope | Negation Parsing | Event vs relation negation |
| **30** | Language-Specific Kāraka Mapping | Multi-Lingual | Ergative, topic-comment handling |

#### F. SCOPE: Temporal & Causal (3 axioms)

| # | Axiom | Scope | Notes |
|---|-------|-------|-------|
| **28** | Implicit Participant Nodes | Agent Handling | DEPRECATED by Axiom 32 |
| **29** | Relative Temporal Ordering | Temporal Relations | REFINED by Axiom 34 |
| **36** | Quantification Support | Quantity Modifiers | cardinal/universal/etc. |

### Operational Layer Properties

```
Each operational axiom has:
├─ SCOPE: Where it applies (like adhikāra)
├─ CONDITIONS: When it fires
├─ ACTION: What it produces
├─ PRIORITY: If conflicts with other rules

Example - Axiom 19 (Document Temporal Framing):
├─ SCOPE: Document ingestion
├─ CONDITION: Document has temporal metadata
├─ ACTION: Set default valid_to based on frame
├─ PRIORITY: Document frame > sentence inference
```

---

## Layer 3: Meta-Governance (Paribhāṣā Equivalent)

These are **rules about rules** — they govern how operational rules are applied, how conflicts are resolved, and how the foundation can evolve.

### ⚙️ Meta-Governance Axioms (7)

| # | Axiom | Meta-Function |
|---|-------|---------------|
| **32** | Agentless Events (No Phantom Entities) | **DEPRECATION PROTOCOL** — retires Axiom 28 |
| **33** | Reciprocal Verbs (Co-Kartā) | **ROLE EXTENSION PROTOCOL** — adds new role type |
| **34** | Temporal Constraint Layer | **LAYER SEPARATION** — constraints vs events |
| **35** | Contradiction Resolution Protocol | **CONFLICT RESOLUTION** — precedence rules |
| **37** | Causal Acyclicity | **INVARIANT ENFORCEMENT** — DAG constraint |
| **38** | Event Retraction Protocol | **VERSIONING PROTOCOL** — how to mark false |
| **39** | Reflexive Semantics (Beyond Boolean) | **DISAMBIGUATION PROTOCOL** — reflexive types |

### Why These Are Meta-Governance

```
These axioms don't CREATE facts — they GOVERN:
├─ How to handle conflicts (Axiom 35)
├─ How to deprecate old rules (Axiom 32)
├─ How to add new primitives (Axiom 33)
├─ How to separate layers (Axiom 34)
├─ How to enforce invariants (Axiom 37)
├─ How to version/retract (Axiom 38)
├─ How to disambiguate (Axiom 39)

Like Paribhāṣā:
├─ Rules about rule application
├─ Conflict resolution algorithms
├─ Self-governing system
```

### Meta Layer Properties

```
Meta-rules are:
├─ STABLE: Rarely change
├─ FORMAL: Mathematically specified
├─ CONSERVATIVE: High bar for changes
├─ SELF-GOVERNING: Meta-rules govern meta-rule changes
```

---

## Visual Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              LAYER 3: META-GOVERNANCE (7 axioms)            │
│                                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │Ax 32    │ │Ax 35    │ │Ax 37    │ │Ax 38            │   │
│  │Deprecate│ │Conflict │ │Acyclic  │ │Retract/Version  │   │
│  │Protocol │ │Resolve  │ │Enforce  │ │Protocol         │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘   │
│                                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                       │
│  │Ax 33    │ │Ax 34    │ │Ax 39    │                       │
│  │Role     │ │Layer    │ │Disambig │                       │
│  │Extend   │ │Separate │ │Protocol │                       │
│  └─────────┘ └─────────┘ └─────────┘                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ governs
┌──────────────────────────▼──────────────────────────────────┐
│              LAYER 2: OPERATIONAL (24 axioms)               │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SCOPE: Type/Taxonomy (Ax 9, 10, 11, 22)             │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SCOPE: Event Semantics (Ax 12-17)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SCOPE: Validation (Ax 18, 19, 20)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SCOPE: Aspect/Classification (Ax 21, 23, 24, 25, 31)│   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SCOPE: Linguistic (Ax 26, 27, 30)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SCOPE: Temporal/Causal (Ax 28*, 29*, 36)            │   │
│  │        (* = revised by meta-rules)                  │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ uses
┌──────────────────────────▼──────────────────────────────────┐
│              LAYER 1: FOUNDATION (8 axioms)                 │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ PRIMITIVES (like Śiva Sūtrāṇi)                        │ │
│  │                                                       │ │
│  │ Ax 1: Events are primitive                            │ │
│  │ Ax 2: Ground Truth + Views structure                  │ │
│  │ Ax 3: ACTION_EVENT vs STATE_EXIST                     │ │
│  │ Ax 4: 8 Kāraka roles                                  │ │
│  │ Ax 5: 3 Causal types (kāraṇa, prayojana, hetu)       │ │
│  │ Ax 6: Edge types (kāraka, causal only)               │ │
│  │ Ax 7: Entities cross events                          │ │
│  │ Ax 8: Events have time                               │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Compression Opportunities

### Current State: 39 Axioms

Your system has **39 axioms** — but with Pāṇinian compression:

### Potential Compressed Form: ~15 Core Sūtras

| Current (39) | Compressed |
|--------------|------------|
| Axioms 1-8 | **8 Foundational Primitives** (keep as-is) |
| Axioms 9-11, 22 | **1 Sūtra**: Type constraints live in schema layer |
| Axioms 12-17 | **2 Sūtras**: Event semantics + State lifecycle |
| Axioms 18-20 | **1 Sūtra**: Validation pipeline |
| Axioms 21, 23-25, 31 | **2 Sūtras**: Event classification + composition |
| Axioms 26-27, 30 | **1 Sūtra**: Language-specific parsing with profiles |
| Axioms 28-29, 36 | **1 Sūtra**: Implicit handling + temporal constraints |
| Axioms 32-39 | **4 Meta-rules** (governance, already compact) |

**Result:** ~15 core sūtras + 4 meta-rules = **~19 total** (vs 39)

### How Pāṇini Would Compress

```
Current (Axioms 12-17):
├─ Axiom 12: Event Granularity (one verb = one event)
├─ Axiom 13: Polarity and Modality (attributes)
├─ Axiom 14: Cross-Document Event Identity (merge rules)
├─ Axiom 15: State Lifecycle (valid_from/to)
├─ Axiom 16: Possessive Constructions (STATE_POSSESS)
├─ Axiom 17: Confidence Levels (explicit/inferred)

Pāṇinian Compression:
├─ Sūtra 1: "घटना-धातु-एकत्वम्" (Event-Dhātu Unity)
│   "One verb manifestation = one event with [polarity, modality, confidence] attributes"
│   
├─ Sūtra 2: "स्थिति-जीवनचक्रम्" (State Lifecycle)  
│   "States have [holder, property, valid_from, valid_to, closure_reason]"

The 6 axioms become 2 sūtras because:
├─ Axiom 12-13 are aspects of same EVENT structure
├─ Axiom 14 is merge rule (derivable from identity criteria)
├─ Axiom 15-16 are aspects of same STATE structure
├─ Axiom 17 is attribute (metadata, not separate axiom)
```

---

## Adhikāra (Scope) Markers

Each operational axiom should have explicit scope. Here's what's implicit:

| Axiom | Current Scope | Should Be Explicit |
|-------|---------------|-------------------|
| 11 | "Copular sentences" | `adhikāra: copular_parsing` |
| 18 | "LLM output" | `adhikāra: extraction_validation` |
| 19 | "Documents" | `adhikāra: document_ingestion` |
| 21 | "Events" | `adhikāra: event_classification` |
| 30 | "Languages" | `adhikāra: language_profile[en/hi/ja]` |

### Example: Axiom 30 with Adhikāra

```yaml
# Current (implicit scope)
Axiom 30: Language-Specific Kāraka Mapping

# With explicit adhikāra
sūtra:
  name: "भाषा-विशेष-कारक-नियमनम्"
  english: "Language-Specific Kāraka Rules"
  adhikāra: 
    - language: [nominative_accusative, ergative_absolutive, topic_prominent]
  condition: "extraction from non-Sanskrit text"
  action: "apply language-profile-specific role mapping"
  examples:
    - context: "Hindi perfective (ergative)"
      rule: "ne-marked subject → still Kartā"
    - context: "Japanese topic-comment"
      rule: "topic marker は → not necessarily agent"
```

---

## Utsarga-Apavāda (Priority) Analysis

Some axioms are **general (utsarga)** and others are **specific overrides (apavāda)**.

| General | Specific Override | Resolution |
|---------|-------------------|------------|
| Axiom 4: 8 Kārakas | Axiom 33: Co-Kartā role | Reciprocal verbs get Co-Kartā |
| Axiom 28: Implicit Agents | Axiom 32: No Phantom Entities | Use NULL + agent_type instead |
| Axiom 29: Temporal Ordering | Axiom 34: Constraint Layer | Move to separate layer |
| Axiom 26: Reflexive Boolean | Axiom 39: Reflexive Types | Use typed reflexivity |

### Pāṇinian Priority Rule

```
apavāda (specific) > utsarga (general)
depth(scope) determines priority

Example:
  Axiom 4 (8 Kārakas) has scope: Universal
  Axiom 33 (Co-Kartā) has scope: Reciprocal_Verbs
  
  When verb is reciprocal:
    depth(Reciprocal_Verbs) > depth(Universal)
    → Axiom 33 takes priority
```

---

## Anuvṛtti (Inheritance) Analysis

Some axioms **inherit context** from others (like Pāṇini's carry-forward):

```
Axiom 2 (Dual-Layer Architecture)
└─ Inherited by:
   ├─ Axiom 20 (View Coherence) — views depend on ground truth
   ├─ Axiom 15 (State Lifecycle) — states in ground truth layer
   ├─ Axiom 17 (Confidence) — marks ground truth vs inferred

Axiom 4 (8 Kārakas)
└─ Inherited by:
   ├─ Axiom 30 (Language-Specific Mapping) — maps to same 8 roles
   ├─ Axiom 33 (Co-Kartā) — extends the role set
   ├─ Axiom 26 (Reflexive) — same entity, multiple roles

Axiom 5 (Causation Is Event-to-Event)
└─ Inherited by:
   ├─ Axiom 23 (Multi-Causal) — multiple causal links allowed
   ├─ Axiom 37 (Acyclicity) — causal graph must be DAG
```

---

## Recommendations

### 1. Add Explicit Scope Markers

Every operational axiom should declare its `adhikāra`:

```markdown
### Axiom X: [Name]
> **Adhikāra:** [scope declaration]
> **Rule:** ...
```

### 2. Create Inheritance Graph

Document which axioms inherit from which (anuvṛtti):

```
Axiom 4
├─ → Axiom 30
├─ → Axiom 33
└─ → Axiom 26
```

### 3. Compress Where Possible

Group related axioms into single sūtras with sub-rules:

```markdown
### Sūtra: Event Semantics

**Sub-rules:**
- 12a: Granularity (one verb = one event)
- 12b: Polarity (positive/negative)
- 12c: Modality (actual/potential/obligatory/hypothetical)
- 12d: Confidence (explicit/inferred)
```

### 4. Separate Foundation Document

Extract Axioms 1-8 into a separate `foundation-primitives.md` that is marked as **immutable**.

### 5. Create Meta-Rule Document

Extract Axioms 32-39 into `meta-governance-rules.md` for governance protocol.

---

## Summary Table

| Aspect | Current State | Pāṇinian Ideal |
|--------|---------------|----------------|
| **Total Axioms** | 39 | ~19 (compressed) |
| **Foundation** | 8 (implicit) | 8 (explicit, immutable) |
| **Operational** | 24 (flat list) | Grouped by adhikāra |
| **Meta** | 7 (mixed in) | Separate governance doc |
| **Scope Markers** | Implicit | Explicit adhikāra |
| **Priority Rules** | Implicit | Explicit utsarga-apavāda |
| **Inheritance** | Not tracked | Explicit anuvṛtti graph |

---

## Next Steps

1. **Immediate:** Mark axioms 1-8 as FOUNDATIONAL in `karaka-axioms.md`
2. **Short-term:** Add adhikāra (scope) declarations to axioms 9-31
3. **Medium-term:** Compress related axioms into sūtra groups
4. **Long-term:** Create separate Foundation/Operational/Meta documents

---

*This mapping enables Pāṇinian governance architecture for the Kāraka system.*
