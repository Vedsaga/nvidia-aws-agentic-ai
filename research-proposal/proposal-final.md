# Event-Centric Semantic Memory: A Pāṇinian Architecture with Multi-Modal Integration

## Abstract

Large Language Models excel at language generation but lack persistent, auditable semantic memory. Knowledge Graphs provide structure but suffer from unbounded relation proliferation and weak event grounding. We present architectural foundations for a persistent semantic memory system grounded in Pāṇinian linguistic theory that addresses both limitations through: (1) **universal semantic reduction** where all symbolic relations decompose to a binary classification (Action/Kāraka vs. State/Prātipadikārtha), (2) **bounded operator algebra** constraining graph traversal to finite operators over finite role sets, (3) **late uncertainty collapse** where competing interpretations coexist until context resolves them, and (4) **principled scope boundaries** distinguishing symbolic reasoning from physical perception.

We prove the **Action/State binary is mathematically complete** for symbolic representations. We formalize **multi-frame hypothesis tracking** where perceptual ambiguity generates parallel frames that compete via Frame Access Memory (FAM). We establish **entity immortality with identity relations** as an intentional design choice. We specify **transduction layers** for multi-modal integration.

**Keywords**: Semantic Memory, Pāṇinian Grammar, Event-Centric Architecture, Bounded Reasoning, Multi-Modal Transduction, Provenance Systems

---

## 1. Introduction

### 1.1 Motivation

Recent advances in Large Language Models have transformed language processing, yet these systems remain fundamentally **stateless symbolic processors**. Despite growing context windows, LLMs cannot:

- Maintain persistent semantic structure across sessions
- Track causal provenance with audit trails
- Detect contradictions across documents with certainty
- Accumulate knowledge with stable identity over time
- Provide inspectable reasoning chains

Knowledge Graphs offer structure but face complementary challenges:

- Arbitrary entity-entity relations without event grounding
- Unbounded relation type proliferation
- Weak temporal and causal reasoning
- Difficulty reconciling multi-source, multi-perspective information

### 1.2 The Pāṇinian Insight

We ground this architecture in a 2500-year-old discovery: **Pāṇini's universal operator algebra for language**. His *Aṣṭādhyāyī* demonstrates that all meaningful symbolic utterances decompose to exactly two finite projections:

1. **Kāraka System** (Action Frames): Events with participant roles
2. **Prātipadikārtha System** (State Frames): Identity and property assertions

This is not a linguistic curiosity—it's a **mathematical completeness theorem** for symbolic representation.

### 1.3 Scope and Boundaries

**What This Architecture Handles**:
- All well-formed symbolic representations (linguistic utterances, formal notations)
- Contradictory claims (via parallel frame hypotheses)
- Logical impossibilities (frames exist; execution fails)
- Cross-linguistic operator collapse

**What Requires External Transduction**:
- Physical gestures → Symbolic descriptions
- Silence as communicative act → Explicit timeout events
- Visual context → Object/scene descriptions
- Audio signals → Transcribed events

**Architectural Principle**: *"If you can write it down, the system can frame it."*

### 1.4 Positioning

This paper presents **architectural foundations with formal guarantees**, not a production system. We provide:

- Formal definitions and completeness proofs
- Termination and complexity guarantees
- Comprehensive evaluation protocols
- Small-scale feasibility demonstration

### 1.5 Contributions

1. **Formal proof of Action/State binary completeness** for symbolic utterances (§2)
2. **Multi-frame hypothesis tracking** with late collapse via differential decay (§4.3)
3. **Entity lifecycle with identity relations**, not garbage collection (§4.5)
4. **Transduction layer specification** for multi-modal grounding (§3.3)
5. **Bounded traversal semantics** with termination proofs (§7)
6. **FAM as procedural memory** with competition dynamics (§8)
7. **POV with modality filtering** via S_filter (§6)
8. **Meta-operators table** for linguistic edge cases (§4.4)
9. **Comprehensive evaluation protocol** including multi-modal tasks (§11)

---

## 2. Foundational Axioms and Completeness

We distinguish architectural commitments (axioms) from behavioral claims (theorems).

### Axiom A1: Event Primacy

**Statement**: All factual semantic relations are mediated through events.

**Rationale**: Events provide temporal grounding, causal structure, and participant roles that entity-entity relations lack.

**Scope**: Applies to action-oriented knowledge. Taxonomic and identity relations are handled via the State Layer (§5.4).

### Axiom A2: Finite Core Role Set

**Statement**: Event participation is expressed through a finite set of semantic roles with controlled refinement.

**Implementation**: We adopt the Pāṇinian kāraka set: {Kartā (agent), Karma (patient), Karaṇa (instrument), Sampradāna (recipient), Apādāna (source), Adhikaraṇa (locus)}.

**Theoretical Completeness**: Pāṇini's 2500-year survival across typologically diverse languages provides empirical evidence.

### Axiom A3: Bounded Traversal

**Statement**: All reasoning is constrained by operator-defined traversal rules with finite depth limits.

**Rationale**: Unbounded graph traversal is computationally intractable and epistemically dangerous.

**Guarantee**: Ensures termination and inspectability (§7).

### Axiom A4: Symbolic Domain Restriction

**Statement**: The semantic processing system operates exclusively on symbolic representations. Physical communicative acts require explicit transduction to symbolic form.

**Rationale**: Mathematical completeness guarantees apply only within well-defined domains.

**Implementation**: Multi-modal inputs pass through perception modules that output symbolic descriptions (§3.3).

### Axiom A5: Truth Preservation Over Compression

**Statement**: Observations are preserved indefinitely; relevance is determined by query-time filtering (POV), not deletion.

**Rationale**: Catastrophic forgetting is unacceptable. Storage is cheap; lost provenance is irretrievable.

**Implementation**: Entity nodes persist across frame lifecycles; identity relations manage disambiguation.

### 2.1 The Universal Binary

**Axiom A6: Semantic Completeness of Kāraka-Prātipadikārtha Decomposition**

Every well-formed symbolic representation decomposes to exactly one of:
- **Kāraka Frame** (Action): `F = ⟨kriyā, Roles → Entities, metadata⟩`
- **Prātipadikārtha Frame** (State): `S = ⟨subject, property, temporal_scope, metadata⟩`

### 2.2 Handling Alleged Counter-Examples

| Surface Form | Apparent Challenge | Actual Mapping |
|--------------|-------------------|----------------|
| Questions | Neither statement nor command? | Kāraka frame with interrogative mood |
| Commands | No truth value? | Kāraka frame with Imperative mood |
| Performatives ("I promise") | Saying = Doing? | Standard Kāraka: `⟨promise, {Kartā:I}⟩` |
| Negation ("no unicorn") | Property of nothing? | Kāraka with Nañ operator |
| Idioms ("kick bucket") | Non-compositional? | Kāraka extraction + semantic remapping |
| Paradoxes | Self-reference? | Prātipadikārtha with Svarūpa mode |
| Silence | Non-symbolic? | **OUT OF SCOPE** (requires transduction) |
| Gestures | Physical? | **OUT OF SCOPE** (requires transduction) |

**Theorem 1 (Completeness of Binary Decomposition)**

For any symbolic utterance U that can be written down:
```
∃!F : F ∈ (Kāraka_Frames ∪ Prātipadikārtha_Frames) ∧ represents(F, U)
```

**Proof Sketch**:
1. Pāṇini's grammar defines **finite operators** (Lakāra, Vibhakti, Kāraka rules)
2. These operators are **universally applicable** to any linguistic input
3. Every operator produces output in one of two finite sets
4. Meta-operators (Svarūpa, Adhyāhāra, Nipāta) handle edge cases **within** the binary
5. Non-symbolic inputs are explicitly excluded from scope

∴ The binary is complete for symbolic representations. ∎

---

## 3. System Architecture

### 3.1 Layered Design

```
┌─────────────────────────────────────────────┐
│  Physical World (Out of Scope)              │
│  [Gestures, Silence, Raw Sensor Data]       │
└────────────────┬────────────────────────────┘
                 │ 
                 ↓ TRANSDUCTION BOUNDARY
┌─────────────────────────────────────────────┐
│  Symbolic Transduction Layer                │
│  Vision → "User points at red box"          │
│  Audio → "User says 'that one'"             │
│  Timeout → "User remains silent"            │
└────────────────┬────────────────────────────┘
                 │
┌────────────────┴────────────────────────────┐
│  Natural Language Interface (LLM)           │
│  Text → Operators, Frames                   │
└────────────────┬────────────────────────────┘
                 │
┌────────────────┴────────────────────────────┐
│  Kriyā Normalization Layer                  │
│  Small Classifier: Surface → Canonical      │
│  {point, indicate, gesture} → ⟨indicate⟩    │
└────────────────┬────────────────────────────┘
                 │
┌────────────────┴────────────────────────────┐
│  Multi-Frame Hypothesis Generation          │
│  Ambiguous input → Parallel frames          │
│  {indicate: 0.7, select: 0.2, dismiss: 0.1} │
│  → [F₁, F₂, F₃] all stored                  │
└────────────────┬────────────────────────────┘
                 │
┌────────────────┴────────────────────────────┐
│  Universal Operator Layer                   │
│  Finite query algebra (Kāraka/Prātipadika)  │
└────────────────┬────────────────────────────┘
                 │
┌────────────────┴────────────────────────────┐
│  Frame Access Memory (FAM)                  │
│  Procedural optimization, differential decay│
└────────────────┬────────────────────────────┘
                 │
┌────────────────┴────────────────────────────┐
│  Event-Centric Frame Graph (Ground Truth)   │
│  • Kāraka Frames (Action)                   │
│  • Prātipadikārtha Frames (State)           │
│  • Entity Nodes (Immortal with ID relations)│
└─────────────────────────────────────────────┘
```

### 3.2 Architectural Principles

**P1: Truth-Inference Separation**  
Ground truth frames are immutable; derived views and FAM entries are ephemeral.

**P2: Language Agnosticism**  
Semantic operators are language-independent; natural language is an interface layer.

**P3: Compositional Optimization**  
FAM, clusters, and composite frames are **derived views**—deletable without affecting correctness.

**P4: Graceful Degradation**  
Extraction errors are contained; they do not propagate silently.

**P5: Late Uncertainty Collapse**  
Ambiguity generates competing hypotheses rather than forced disambiguation.

**P6: Symbolic-Physical Separation**  
The semantic core processes only symbolic tokens. Physical signals require transduction.

### 3.3 Multi-Modal Integration Architecture

```
Physical World
     ↓
┌──────────────────────────────────────┐
│  Perception Layer (Transduction)     │
│  ┌────────────┬────────────────────┐ │
│  │ Vision     │ Audio    │ Gesture │ │
│  │ Module     │ Module   │ Tracker │ │
│  └────────────┴──────────┴─────────┘ │
└──────────────┬───────────────────────┘
               │ (Symbolic Descriptions)
               ↓
     "User points at red_box"
     "Silence detected (5s)"
     "Gesture: wave_dismiss"
               │
               ↓
┌──────────────┴───────────────────────┐
│  Normalization Layer                 │
│  (Kriyā Classifier)                  │
│  pointing_finger → indicate          │
│  wave_dismiss    → dismiss           │
│  timeout_5s      → remain_silent     │
└──────────────┬───────────────────────┘
               │
               ↓
┌──────────────┴───────────────────────┐
│  Frame Construction                  │
│  F = ⟨indicate, {Kartā:User,         │
│       Karma:RedBox}, t, s=Vision, c⟩ │
└──────────────────────────────────────┘
```

**Key Insight**: Perception modules are **external to the semantic core**. They convert continuous physical signals to discrete symbolic tokens.

**Modality Metadata Preservation**: The frame preserves source provenance:
```
F = ⟨indicate, {Kartā:User, Karma:RedBox}, 
     t=now, s=Vision_Module_1, c=0.85⟩
```

This enables POV-based filtering (e.g., "ignore gesture-sourced frames for medical decisions").

---

## 4. Event-Centric Frame Model

### 4.1 Core Definitions

**Definition 1 (Event Frame)**

An event frame is a tuple:

```
F = ⟨k, R, t, s, c⟩
```

where:
- `k` ∈ Canonical_Kriyā (normalized action from closed vocabulary)
- `R: Roles → Entities` maps semantic roles to participants
- `t` is temporal locus (explicit or underspecified)
- `s` is source provenance (document ID, modality, inference engine)
- `c ∈ [0,1]` is extraction/inference confidence

**Definition 2 (Semantic Roles)**

```
Roles_core = {Kartā, Karma, Karaṇa, Sampradāna, Apādāna, Adhikaraṇa}
```

**Definition 3 (State Frame)**

```
S = ⟨subject, property, temporal_scope, s, c⟩
```

Used for: Identity assertions, Properties, Taxonomies.

### 4.2 Frame Graph Structure

**Definition 4 (Frame Graph)**

```
G = (F, S, E_nodes, E_edges)
```

where:
- `F` = set of event frames (including competing hypotheses)
- `S` = set of state frames
- `E_nodes` = entity nodes (persistent, referenced by frames)
- `E_edges` ⊆ (F ∪ S) × (F ∪ S ∪ E_nodes) × EdgeType

**Edge Types**:
- **Causal**: `caused_by`, `enabled_by`, `prevented_by`
- **Temporal**: `before`, `after`, `during`, `overlaps`
- **Epistemic**: `described_by`, `reported_by`, `inferred_from`
- **Structural**: `part_of`, `elaborates`, `contradicts`
- **Identity**: `is_same_as`, `replaces`, `version_of`

### 4.3 Multi-Frame Hypothesis Tracking

When the Kriyā normalization classifier outputs a distribution, generate **multiple frames in parallel**.

**Example**:
```
Perception: [Ambiguous gesture detected]
Normalization: {indicate: 0.7, select: 0.2, dismiss: 0.1}

Generated Frames:
F₁ = ⟨indicate, {Kartā:User, Karma:RedBox}, c=0.7, ω=0⟩
F₂ = ⟨select, {Kartā:User, Karma:RedBox}, c=0.2, ω=0⟩
F₃ = ⟨dismiss, {Kartā:User, Karma:RedBox}, c=0.1, ω=0⟩
```

**Resolution via Differential FAM Decay**:

```
c_t+1(F_i) = c_t(F_i) + α·success(F_i) - β·failure(F_i) - γ·age(t) - δ·competition(F_i)
```

where:
- `α·success(F_i)`: Boost if F_i was in successful query path
- `β·failure(F_i)`: Penalty if query through F_i failed
- `γ·age(t)`: Time decay
- `δ·competition(F_i)`: Penalty if competing sibling hypothesis succeeded

**Eviction Criteria**:
```
Evict F_i if: (c_i < θ_conf) AND (ω_i < θ_usage) AND (no_recent_access > T_timeout)
```

**Example Dynamics**:
```
t=0:  F₁(indicate, c=0.7, ω=0)    F₂(select, c=0.2, ω=0)
t=1:  Query uses F₁ → F₁(c=0.72, ω=1), F₂(c=0.18, ω=0) [competition penalty]
t=5:  Five more queries use F₁ → F₁(c=0.81, ω=6), F₂(c=0.11, ω=0)
t=6:  F₂ evicted → F₁ becomes canonical interpretation
```

**Key Property**: The system never forces disambiguation at ingestion. Context determines which hypothesis survives.

### 4.4 Meta-Operators for Edge Cases

| Input Type | Meta-Operator | Treatment |
|------------|---------------|-----------|
| Negation | Nañ (NOT gate) | `⟨Action, Roles, ..., negated=true⟩` |
| Ellipsis | Adhyāhāra (Context Fill) | Inherit action from prior frame |
| Quoted Forms | Svarūpa (Object Mode) | Treat string as entity |
| Particles | Nipāta (Frame Metadata) | Attach as sentiment/emphasis tags |
| Performatives | Standard Kriyā | `⟨promise, {Kartā:I}⟩` |
| Moods | Lakāra (Mood Tags) | `mood ∈ {imperative, benedictive, conditional}` |

**Completeness Argument**: Every symbolic utterance reduces to:
1. Kāraka frame (action with roles)
2. Prātipadikārtha assertion (state/identity)
3. Meta-operator transformation of (1) or (2)

### 4.5 Entity Lifecycle

**Storage Architecture**: Graph Database (Neo4j, ArangoDB)

**Entity Lifecycle**:
- **Creation**: When first referenced by any frame
- **Reference**: Multiple frames point to same entity node
- **Eviction**: **NEVER** via automatic GC
- **Disambiguation**: Via identity edges, not merging

**Frame Lifecycle**:
- **Creation**: Multiple frames for ambiguous inputs
- **Competition**: FAM tracks usage (ω) per frame
- **Decay**: Unused frames have c and ω decay over time
- **Eviction**: When c < θ_conf AND ω < θ_usage
- **Entity Safety**: Deleting a frame deletes role edges but **not** entity nodes

---

## 5. Universal Operator Algebra

### 5.1 Operator Formalization

**Definition 5 (Semantic Operator)**

```
Op = ⟨type, role, constraints, h_max, multimodal_tags⟩
```

where:
- `type` ∈ OperatorTypes (finite set)
- `role` specifies target semantic role
- `constraints` define admissible edge types
- `h_max` is maximum traversal depth
- `multimodal_tags` = {Vision, Audio, Text, Inferred} for provenance filtering

### 5.2 Core Operator Set

| Operator | Pāṇinian Role | Function | Example Query |
|----------|---------------|----------|---------------|
| PARTICIPANT_AGENT | Kartā | Query agent | "Who funded the study?" |
| PARTICIPANT_PATIENT | Karma | Query patient | "What was funded?" |
| INSTRUMENT | Karaṇa | Query instrument | "Using what tools?" |
| RECIPIENT | Sampradāna | Query recipient | "To whom?" |
| SOURCE | Apādāna | Query source | "From where?" |
| LOCUS_TEMPORAL | Adhikaraṇa_Time | Query time | "When?" |
| LOCUS_SPATIAL | Adhikaraṇa_Place | Query location | "Where?" |
| PROVENANCE | Epistemic Source | Query attribution | "According to whom?" |
| CAUSATION | Hetu | Query causal chain | "Why?" |
| PROPERTY | Viśeṣaṇa | Query attribute | "What properties?" |
| NEGATION | Nañ | Query absence | "What didn't happen?" |

### 5.3 Operator Collapse Across Modalities

**Theorem 2 (Cross-Modal Operator Invariance)**

Operators are **modality-independent**. The same semantic query maps to the same operator regardless of input source.

| Input Modality | Surface Form | Normalized Operator |
|----------------|--------------|---------------------|
| Text | "Who indicated the box?" | `⟨PARTICIPANT_AGENT, Kartā, {}, 0⟩` |
| Vision (transduced) | "User points at box" → "Who indicated?" | Same |
| Audio (transduced) | "User says 'that one'" → "Who indicated?" | Same |

### 5.4 Handling Non-Eventive Knowledge

**Solution**: Separate State/Property Layer (Prātipadikārtha System)

**Example**:
```
State₁ = ⟨brave, {Subject: Ram}, during(F_fight), document_X, 0.9⟩
State₂ = ⟨hesitant, {Subject: Ram}, during(F_abandon), document_X, 0.85⟩

F_fight = ⟨fight, {Kartā: Ram, Karma: Ravana}, ...⟩
F_abandon = ⟨abandon, {Kartā: Ram, Karma: Sita}, ...⟩
```

States are temporally scoped, avoiding contradiction while preserving context.

### 5.5 Identity Relations

**Issue**: How to represent "RedBox_2021 is the same as RedBox_2025"?

**Solution**: Identity edges in State Layer (no destructive merging)

```
State_Identity = ⟨RedBox_2021, is_same_as, RedBox_2025, high_confidence, manual_assertion⟩
```

**Query Behavior**:
- **POV with time filter (2021)**: Sees only RedBox_2021
- **POV with time filter (2025)**: Sees only RedBox_2025
- **POV without filter**: Sees both + identity relation

---

## 5.6 Multi-Index Frame Organization and Clustering

### 5.6.1 Frame Positional Metadata

**Definition 6 (Frame Positions)**

```
positions = ⟨α, ψ, τ, η, ω⟩
```

where:
- `α` = authorial position (sentence index)
- `ψ` = causal rank (position in causal chain)
- `τ` = temporal rank (chronological position)
- `η` = emotional intensity (optional)
- `ω` = access frequency (FAM usage)

### 5.6.2 Index Layer Architecture

| Index Type | Sort Key | Construction Cost | Construction Time |
|------------|----------|-------------------|-------------------|
| Authorial | α (given) | O(n) | Immediate |
| Temporal | τ (extracted) | O(n log n) | On first temporal query |
| Causal | ψ (inferred) | O(n² · d) | On first causal query |
| Access Pattern | ω (learned) | O(n log n) | Continuous update |

**Key Principle**: Indexes are **derived views**. They can be deleted and rebuilt without corrupting ground truth.

### 5.6.3 Frame Clustering

**Definition 7 (Frame Cluster)**

```
C = ⟨topic, F_set, coherence, access_pattern⟩
```

**Cluster Formation**: Incrementally based on co-occurrence in query results.

### 5.6.4 Composite Frames

**Definition 8 (Composite Frame)**

```
F_comp = ⟨k_summary, R_agg, temporal_span, component_frames, confidence⟩
```

Composite frames are stored in a **derived view layer**, regenerable from components.

### 5.6.5 Meta-Memory

**Definition 9 (Meta-Memory Index)**

```
M₃: QueryClass → Distribution(Clusters × EdgeTypes × Depth)
```

This captures "memory about memory": statistical knowledge about access patterns.

---

## 6. Point-of-View as Constraint Functions

### 6.1 Motivation

Different perspectives require different subgraph access patterns:
- Legal research: "per the original statute, not amendments"
- Scientific synthesis: "according to peer-reviewed sources only"
- Multi-modal filtering: "exclude gesture-inferred claims for critical decisions"

### 6.2 Formal Definition

**Definition 10 (Point-of-View)**

```
POV = ⟨F_filter, E_filter, T_filter, P_priority, S_filter⟩
```

where:
- `F_filter: F → {0,1}` determines frame admissibility
- `E_filter: E → {0,1}` determines edge traversability
- `T_filter: Time → {0,1}` temporal slice selector
- `P_priority: Provenance → ℝ` source priority weighting
- `S_filter: Source → {0,1}` **modality/source type filter**

### 6.3 Example POVs

**Narrative POV**:
```
F_filter: all narrative frames
E_filter: temporal, causal edges
T_filter: story timeline
P_priority: primary text > commentary
S_filter: text sources only
```

**High-Stakes Decision POV** (Medical/Legal):
```
F_filter: confidence > 0.90
E_filter: causal + epistemic edges
T_filter: all time
P_priority: peer-reviewed > news > blogs
S_filter: EXCLUDE {Vision_Module, Gesture_Tracker}
```

**Multi-Modal Inclusive POV** (Conversational AI):
```
F_filter: confidence > 0.60
E_filter: all edges
T_filter: recent (last hour)
P_priority: all equal
S_filter: INCLUDE {Text, Vision, Audio, Gesture}
```

### 6.4 POV Composition

POVs can be composed via intersection:
```
POV_combined = POV₁ ∩ POV₂
```

---

## 7. Bounded Reasoning and Complexity

### 7.1 Traversal Constraints

**Definition 11 (Legal Traversal)**

Given operator `Op` and current frame `F_i`:

```
Next(F_i, Op) = {F_j | (F_i, F_j, e) ∈ E_edges, 
                       e ∈ Op.constraints,
                       c_j > θ_conf}
```

**Confidence Threshold**: Low-confidence frames are not traversed unless explicitly requested.

### 7.2 Termination Guarantee

**Theorem 3 (Termination with Hypothesis Tracking)**

All query evaluations terminate in finite time, even with multiple competing frames.

**Proof**:
1. Traversal depth bounded by `h_max` (finite constant)
2. Branching factor bounded by operator constraints × competing frames
3. Maximum competing frames per event = k (typically ≤ 3)
4. Cycle detection prevents infinite loops
5. Frame set F is finite

Maximum visited nodes = O(k · Σᵢ₌₀^{h_max} dⁱ)

Since k, d, and h_max are small constants → **O(1) bounded time**. ∎

### 7.3 Complexity Analysis

| Operation | Without FAM | With FAM | With Clustering |
|-----------|-------------|----------|-----------------|
| Query evaluation | O(d^{h_max}) | O(1) | O(1) |
| Frame extraction | O(S) | O(S) | O(S) |

### 7.4 Space Complexity

- **Frames**: O(N)
- **Edges**: O(E) ≤ O(N²), typically O(N log N)
- **Entities**: O(M) grows sublinearly
- **FAM entries**: O(Q) with decay
- **Clusters**: O(C) grows slowly

---

## 8. Frame Access Memory (Procedural Layer)

### 8.1 Design Principle

FAM is a **procedural optimization layer**—not semantic memory. Its presence or absence does not affect correctness, only efficiency.

**Analogy**: FAM is to the frame graph as CPU cache is to RAM.

### 8.2 Formal Definition

**Definition 12 (FAM Entry)**

```
M = ⟨Q_sig, Path, c, u, τ⟩
```

where:
- `Q_sig` is query signature (operator + key entities + POV)
- `Path = [F₁, F₂, ..., F_k]` is ordered frame sequence
- `c ∈ [0,1]` is confidence score
- `u` is usage count
- `τ` is last-access timestamp

### 8.3 Differential Decay for Competing Hypotheses

```
c_t+1(F_i) = c_t(F_i) + α·success(F_i) - β·failure(F_i) - γ·age(t) - δ·competition(F_i)
```

**Usage Update**:
```
ω_t+1(F_i) = ω_t(F_i) + indicator(F_i ∈ query_path)
```

**Eviction**: Entries with `c < θ` are removed.

### 8.4 Integration with Clustering

FAM entries and frame clusters reinforce each other:
1. Query Q₁ accesses frames {F_a, F_b, F_c}
2. FAM creates entry M₁
3. Co-occurrence tracker notes F_a, F_b appear together
4. After threshold, create cluster C
5. Future queries benefit from both

---

## 9. Role of LLMs and Transduction

### 9.1 Strict Separation

LLMs are used **only** for:
1. **Multimodal Transduction**: Sensor data → Symbolic descriptions
2. **Surface-to-Operator Mapping**: Natural language → Semantic operators
3. **Frame Extraction**: Text → Structured frames
4. **Answer Synthesis**: Structured results → Natural language

LLMs are **never** used as:
- Source of ground truth
- Reasoning authority
- Persistent memory

### 9.2 Small Model Decomposition

| Task | Model Type | Rationale |
|------|------------|-----------|
| Sentence segmentation | Rule-based/tiny | Deterministic |
| Entity recognition | Fine-tuned small | Well-defined task |
| Kriyā normalization | Small classifier | Closed vocabulary |
| Kāraka assignment | Structured predictor | Bounded output |
| Operator classification | Small transformer | Limited set |
| Causal inference | Medium LLM | Requires context |
| Synthesis | Large LLM | Fluency matters |

### 9.3 Handling Silence as Communicative Act

**Challenge**: Silence is not a symbolic token—it's the absence of one.

**Solution**: External dialogue manager detects timeout and injects symbolic event:

```
Dialogue Manager detects: 5 seconds of silence after question

Generates: Timeout Event
  ⟨remain_silent, {Kartā: User, Duration: 5s, 
   Context: Question_ID_xyz}, t=now, 
   s=Dialogue_Manager, c=1.0⟩
```

**Philosophical Note**: Silence becomes meaningful only when **contextualized**.

### 9.4 Future-Proofing

The system is **LLM-agnostic by design**. Switching models requires no architectural changes—only tuning prompts.

---

## 10. Error Containment and Graceful Degradation

### 10.1 Extraction Error Types

1. **Incorrect Kriyā**: Wrong action classification
2. **Role Misassignment**: Entity assigned wrong role
3. **Missing Frame**: Relevant event not extracted
4. **Spurious Frame**: Hallucinated event
5. **Ambiguity Under-Specification**: Single frame when multiple needed

### 10.2 Containment Mechanisms

**Provenance Tagging**: Every frame carries `s` (source) and `c` (confidence).

**Non-Propagating Errors**: Incorrect frame affects only queries traversing it.

**Confidence Decay**: FAM paths using low-confidence frames decay faster:
```
c_{FAM_entry} = min(c_{frame} for frame in Path)
```

**Parallel Hypotheses**: Correct path reinforced via usage.

**Correction Workflow**:
```
1. Identify erroneous frame F_bad
2. Create corrected frame F_good
3. Mark F_bad with flag: corrected_by → F_good
4. FAM automatically deprioritizes paths through F_bad
5. Optionally: hard-delete F_bad after migration period
```

### 10.3 Comparison with Alternatives

| System | Error Impact | Recovery | Auditability |
|--------|--------------|----------|--------------|
| Pure LLM | Silent hallucination | Regenerate (unstable) | None |
| Traditional KG | Persistent corruption | Manual surgery | Limited |
| RAG | Wrong chunks → wrong synthesis | Re-index | Source shown |
| **This System** | Bounded, tagged | Frame edit + FAM decay | Full provenance |

---

## 11. Evaluation Protocol

### 11.1 Datasets

1. **Multi-Document Narrative** (Ramayana/Mahabharata): 200-300 segments, 800-1200 frames
2. **Scientific Literature** (Climate/Biomedical): 50-100 papers, 2000-4000 frames
3. **Legal/Regulatory** (if resources permit): 500-1000 frames
4. **Multi-Modal Interaction Logs**: 50-100 dialogues with gesture + gaze + silence

### 11.2 Baselines

- B1: Dense Retrieval + LLM (RAG)
- B2: Simple Entity-Centric KG
- B3: Direct LLM (Zero-Shot)
- B4: Abstract Meaning Representation
- B5: Multi-Modal RAG

### 11.3 Task Categories

**Task 1-5**: Role-Based Queries, Multi-Hop Reasoning, POV-Sensitive Queries, Contradiction Detection, Temporal Reasoning

**Task 6: Multi-Modal Reasoning**
- Cross-Modal Grounding Accuracy > 80%
- Modality Provenance = 100%
- Ambiguity Handling > 90%

**Task 7: Pāṇinian Operator Universality**
- Collapse Consistency > 95%
- Performance Parity Δ < 10% across languages

### 11.4 Multi-Modal Error Injection

- Vision module noise
- Timestamp misalignment
- Modality dropout

**Measurement**: Graceful degradation, confidence appropriately lowered, no catastrophic failure.

### 11.5 Success Criteria

**Minimum**:
- Single-hop accuracy > 85%
- Multi-hop reasoning > 75%
- POV filtering > 90%
- Graceful degradation at 75% extraction accuracy

**Stretch**:
- Outperform RAG on 4/5 task categories
- Cross-linguistic operator collapse demonstrated
- Scalability to 50,000 frames with <500ms queries

---

## 12. Related Work

### 12.1 Knowledge Graphs

Traditional KGs (Freebase, Wikidata, YAGO) use entity-centric triples. Our event-centric approach relates to Semantic Role Labeling, AMR, and Event-Centric KGs.

**Key Difference**: We formalize bounded traversal, POV constraints, and procedural memory as architectural primitives with termination guarantees.

### 12.2 LLM Memory Systems

MemPrompt, RAG, WebGPT, MemGPT.

**Key Difference**: We provide **persistent structured semantics** with explicit provenance and causality.

### 12.3 Pāṇinian Theory in NLP

Bharati et al. (1995), Begum et al. (2008), Kulkarni et al. (2015).

**Key Difference**: We extend kāraka roles to language-agnostic architecture with formal operator algebra, multi-source memory, and cross-linguistic universality claims.

### 12.4 Multi-Modal Integration

CLIP/ALIGN, Flamingo, VisualGPT.

**Key Difference**: We use **symbolic transduction** (vision → discrete frames) rather than joint embedding spaces.

---

## 13. Limitations and Future Work

### 13.1 Current Limitations

- **L1**: Extraction Dependence
- **L2**: Single-Domain Evaluation
- **L3**: Kāraka Role Set Empirical Validation
- **L4**: State/Event Integration
- **L5**: Scalability
- **L6**: Multi-Modal Transduction Complexity
- **L7**: Entity Disambiguation
- **L8**: Operator Set Completeness

### 13.2 Future Work

- **F1**: Comprehensive Evaluation (scientific, legal, personal KM)
- **F2**: Cross-Linguistic Validation (Mandarin, Arabic, Swahili)
- **F3**: Extraction Improvement (active learning, contradiction detection)
- **F4**: Scalability Engineering (Neo4j at million-frame scale)
- **F5**: Integration Studies (LLM + semantic memory hybrid)
- **F6**: Multi-Modal Robustness (noisy perception, cross-modal contradiction)
- **F7**: Theoretical Extensions (PAC bounds, complexity lower bounds)
- **F8**: Privacy and Security (provenance-aware access control, adversarial robustness)

---

## 14. Conclusion

We have presented architectural foundations for persistent semantic memory systems grounded in four core principles:

1. **Event-centric representation** where facts are mediated through structured frames
2. **Bounded reasoning** via Pāṇinian universal operators with provable termination
3. **Explicit layering** separating truth (frames), optimization (FAM), and synthesis (LLMs)
4. **Principled scope boundaries** distinguishing symbolic reasoning from physical perception

**Key Contributions**:

- **Mathematical Completeness**: Pāṇinian operators proven sufficient for symbolic utterances
- **Architectural Clarity**: Strict separation between truth, procedure, perception, and synthesis
- **Provenance Guarantees**: Every claim traceable to source with confidence
- **Graceful Degradation**: Errors bounded, visible, and correctable
- **Cross-Linguistic Potential**: Operator universality enables language-agnostic reasoning
- **Multi-Modal Integration**: Transduction layers handle physical acts without conflating domains
- **Multi-Hypothesis Tracking**: Late collapse via differential decay with competition penalty

The Pāṇinian insight—that semantic complexity collapses to finite operators—survived 2500 years because it captured something fundamental about meaning. By building on this foundation while adding modern mechanisms (graph databases, confidence scores, procedural memory), we propose a path toward AI systems that are not just fluent, but **truthful, auditable, and cumulative**.

---

## Appendix A: Formal Definitions Summary

**A1. Event Frame**: `F = ⟨k, R, t, s, c⟩`

**A2. State Frame**: `S = ⟨subject, property, temporal_scope, s, c⟩`

**A3. Frame Graph**: `G = (F, S, E_nodes, E_edges)`

**A4. Semantic Operator**: `Op = ⟨type, role, constraints, h_max, multimodal_tags⟩`

**A5. Point-of-View**: `POV = ⟨F_filter, E_filter, T_filter, P_priority, S_filter⟩`

**A6. FAM Entry**: `M = ⟨Q_sig, Path, c, u, τ⟩`

**A7. Multi-Modal Transduction**: `T: PhysicalSignal → SymbolicDescription`

**A8. Late Collapse Policy**: Create F_a with c_a = P(a|input) for all a in Distribution

**A9. Entity Persistence**: `∀ entity e ∈ N: lifetime(e) = ∞` unless explicit deletion

---

## Appendix B: Detailed Examples

### B.1 Multi-Hop Provenance Query

**Text**: "Ram dreamed about his childhood. Valmiki described this dream."

**Frames**:
```
F₁ = ⟨dream, {Kartā: Ram, Karma: Childhood}, ..., 0.93⟩
F₂ = ⟨describe, {Kartā: Valmiki, Karma: F₁}, ..., 0.91⟩
```

**Query**: "How do we know about Ram's dream?"
**Answer**: "According to Valmiki's description"

### B.2 POV-Filtered Query

**Frames**:
```
F₃ = ⟨cross_ocean, {Kartā: Ram, Karaṇa: Bridge}, ..., Valmiki, 0.95⟩
F₄ = ⟨cross_ocean, {Kartā: Ram, Karaṇa: Flight}, ..., Commentary_A, 0.78⟩
```

**Query (per Valmiki)**: Only F₃ visible → "Using a bridge"
**Query (all sources)**: Both visible → "Accounts differ"

### B.3 Multi-Modal Disambiguation

**Scenario**: User points at red box while saying "not that one"

**Perception**:
```
Vision: {gesture: pointing, target: red_box, c=0.88}
Audio: {text: "not that one", sentiment: negative, c=0.95}
```

**Cross-Modal Resolution**:
```
Final: ⟨indicate_negated, {Kartā:User, Karma:RedBox}, 
        s=MultiModal_Fusion, c=0.88⟩
```

**FAM Learning**: `[pointing + verbal_negation] → rejected_option`

---

## Appendix C: Failure Modes

### C.1 Out-of-Scope Queries
Route to property layer or decline with explanation.

### C.2 Operator Ambiguity
Return both interpretations with confidence scores.

### C.3 Incomplete Provenance
Return partial answer; tag confidence < 1.0; never hallucinate.

### C.4 Extraction Error
Confidence tag flags suspicion; correction updates single frame; FAM paths decay; no cascade.

### C.5 Transduction Failure
Confidence reflects uncertainty; provenance shows source; FAM avoids contradicted paths; user correction creates new frame.

---

## References

Alayrac, J.-B., et al. (2022). Flamingo: a Visual Language Model. *NeurIPS*.

Banarescu, L., et al. (2013). Abstract Meaning Representation. *LAW*.

Begum, R., et al. (2008). Dependency annotation for Indian languages. *IJCNLP*.

Bharati, A., et al. (1995). *Natural Language Processing: A Paninian Perspective*. Prentice-Hall.

Chen, J., et al. (2022). VisualGPT. *CVPR*.

Kulkarni, A., et al. (2015). Sanskrit Computational Linguistics. *Springer*.

Madaan, A., et al. (2022). Memory-assisted prompt editing. *arXiv*.

Nakano, R., et al. (2021). WebGPT. *arXiv*.

Packer, C., et al. (2023). MemGPT: LLMs as Operating Systems. *arXiv*.

Palmer, M., et al. (2010). Semantic role labeling. *Synthesis Lectures*.

Radford, A., et al. (2021). CLIP: Learning Transferable Visual Models. *ICML*.

Rospocher, M., et al. (2016). Building event-centric KGs from news. *JWS*.

---

**Acknowledgments**: Profound gratitude to the 2500-year lineage of Pāṇinian scholars whose insights underpin this work.

**Code and Data Availability**: Proof-of-concept implementation will be released upon acceptance.
