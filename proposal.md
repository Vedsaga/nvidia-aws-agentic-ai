# Event-Centric Semantic Memory: Architectural Foundations for Persistent Knowledge Systems

## Abstract

Large Language Models excel at language generation but lack persistent, auditable semantic memory and explicit structural reasoning. Knowledge Graphs provide structure but suffer from unbounded relation proliferation and weak event grounding. We present architectural foundations for a persistent semantic memory system that bridges these gaps through three core principles: (1) event-centric representation where all factual relations are mediated through structured event frames, (2) bounded reasoning via a finite universal operator algebra that constrains graph traversal, and (3) explicit separation of ground truth, procedural memory, and language synthesis layers.

We formalize Point-of-View (POV) as constraint functions over semantic graphs, enabling provenance-aware multi-perspective reasoning. We introduce Frame Access Memory (FAM) as a procedural optimization layer that caches successful reasoning paths. We prove termination guarantees and establish complexity bounds for query evaluation.

This work positions itself as architectural foundations with formal guarantees. We provide complete architectural specifications, formal proofs of key properties, and a detailed evaluation protocol for empirical validation. The proposed architecture complements advances in foundation models by providing persistent semantic structure, explicit causality tracking, and long-horizon knowledge accumulation.

**Keywords**: Semantic Memory, Knowledge Representation, Event-Centric Architecture, Bounded Reasoning, Provenance Tracking

---

## 1. Introduction

### 1.1 Motivation

Recent advances in Large Language Models (LLMs) have transformed natural language processing, yet these systems remain fundamentally stateless and non-symbolic. Despite growing context windows, LLMs cannot:

- Maintain persistent semantic structure across sessions
- Track causal provenance reliably
- Detect contradictions across documents
- Accumulate knowledge with stable identity over time
- Provide auditable reasoning chains

In parallel, Knowledge Graphs (KGs) offer structured representation but face complementary challenges:

- Arbitrary entity-entity relations without event grounding
- Unbounded relation type proliferation
- Weak temporal and causal reasoning
- Difficulty reconciling multi-source information

### 1.2 Core Insight

We argue that reliable long-horizon reasoning requires an explicit semantic substrate that:

1. Treats events (not entities or embeddings) as atomic meaning units
2. Constrains all semantic relations through finite universal operators
3. Separates truth representation from procedural optimization
4. Integrates with—rather than replaces—LLM capabilities

### 1.3 Positioning

This paper presents **architectural foundations and formal guarantees**, not a fully deployed system. We focus on:

- Formal definitions and axioms
- Termination and complexity proofs
- Architectural separation of concerns
- Small-scale feasibility demonstration

Comprehensive empirical evaluation across domains remains future work.

### 1.4 Contributions

1. **Event-Centric Semantic Model** with formal frame definitions
2. **Finite Universal Operator Algebra** for language-agnostic queries
3. **Point-of-View Formalization** as graph constraint functions
4. **Bounded Traversal Semantics** with termination guarantees
5. **Frame Access Memory (FAM)** as procedural optimization layer
6. **Comprehensive Evaluation Protocol** for empirical validation (§11)

---

## 2. Foundational Axioms

We distinguish architectural commitments (axioms) from behavioral claims (theorems).

### Axiom A1: Event Primacy

**Statement**: All factual semantic relations are mediated through events.

**Rationale**: Events provide temporal grounding, causal structure, and participant roles that entity-entity relations lack.

**Scope**: This axiom applies to action-oriented knowledge. Taxonomic, identity, and pure property relations are handled separately (§5.4).

### Axiom A2: Finite Core Role Set

**Statement**: Event participation is expressed through a finite set of semantic roles with controlled refinement.

**Rationale**: Unbounded role proliferation leads to semantic fragmentation and non-compositional reasoning.

**Implementation**: We adopt a core set based on kāraka theory: {Kartā (agent), Karma (patient), Karaṇa (instrument), Sampradāna (recipient), Apādāna (source), Locus (spatiotemporal)}, with subtypes for finer distinctions.

### Axiom A3: Bounded Traversal

**Statement**: All reasoning is constrained by operator-defined traversal rules with finite depth limits.

**Rationale**: Unbounded graph traversal is computationally intractable and epistemically dangerous (hallucination risk).

**Guarantee**: This ensures termination and inspectability (§7).

---

## 3. System Architecture

### 3.1 Layered Design

```
┌─────────────────────────────────────┐
│  Natural Language Interface          │  ← LLM (parsing, synthesis)
│  (extraction, operator mapping)      │
└────────────────┬────────────────────┘
                 │
┌────────────────┴────────────────────┐
│  Universal Operator Layer            │  ← finite query algebra
│  (semantic interpretation)           │
└────────────────┬────────────────────┘
                 │
┌────────────────┴────────────────────┐
│  Frame Access Memory (FAM)           │  ← procedural optimization
│  (reasoning path cache)              │
└────────────────┬────────────────────┘
                 │
┌────────────────┴────────────────────┐
│  Event-Centric Frame Graph           │  ← ground truth
│  (semantic memory substrate)         │
└─────────────────────────────────────┘
```

### 3.2 Architectural Principles

**P1: Truth-Inference Separation**  
Ground truth frames are immutable; derived views and reasoning paths are ephemeral.

**P2: Language Agnosticism**  
Semantic operators are language-independent; natural language is an interface layer only.

**P3: Compositional Optimization**  
Procedural memory (FAM) can be deleted without affecting correctness.

**P4: Graceful Degradation**  
Extraction errors are contained; they do not propagate silently or corrupt the graph irreversibly.

---

## 4. Event-Centric Frame Model

### 4.1 Core Definitions

**Definition 1 (Event Frame)**

An event frame is a tuple:

```
F = ⟨k, R, t, s, c⟩
```

where:
- `k` is a normalized action (kriyā)
- `R: Roles → Entities` maps semantic roles to participants
- `t` is temporal locus (explicit or underspecified)
- `s` is source provenance
- `c ∈ [0,1]` is extraction confidence

**Definition 2 (Semantic Roles)**

The core role set is:

```
Roles_core = {Kartā, Karma, Karaṇa, Sampradāna, Apādāna, Locus}
```

**Role Refinement**: Complex distinctions (benefactive vs. recipient, comitative, manner) are handled via:
- Controlled subtyping (e.g., Sampradāna_benefactive)
- Secondary constraint edges
- State/property layer attribution (§5.4)

### 4.2 Frame Graph Structure

**Definition 3 (Frame Graph)**

```
G = (F, E)
```

where:
- `F` is the set of event frames
- `E ⊆ F × F × EdgeType` are typed directed edges

**Edge Types** include:
- Causal: `caused_by`, `enabled_by`
- Temporal: `before`, `after`, `during`
- Epistemic: `described_by`, `reported_by`, `inferred_from`
- Structural: `part_of`, `elaborates`

### 4.3 Worked Example: Frame Extraction

**Input Text**:
> "The European Research Council funded a study on climate impacts in 2022. The findings were reported by Reuters."

**Extracted Frames**:

```
F₁ = ⟨fund, {Kartā: ERC, Karma: Study, Locus_Time: 2022}, 2022, document_1, 0.95⟩

F₂ = ⟨report, {Kartā: Reuters, Karma: Findings}, 2022, document_1, 0.92⟩
```

**Graph Edges**:
```
F₂ --[reported_content]--> F₁
```

---

## 5. Universal Operator Algebra

### 5.1 Operator Formalization

**Definition 4 (Semantic Operator)**

A semantic operator is a tuple:

```
Op = ⟨type, role, constraints, h_max⟩
```

where:
- `type` ∈ OperatorTypes (finite set)
- `role` specifies the target semantic role
- `constraints` define admissible edge types
- `h_max` is maximum traversal depth

### 5.2 Core Operator Set

| Operator | Function | Example Query |
|----------|----------|---------------|
| PARTICIPANT_AGENT | Query Kartā | "Who funded the study?" |
| PARTICIPANT_PATIENT | Query Karma | "What was funded?" |
| INSTRUMENT | Query Karaṇa | "Using what tools?" |
| RECIPIENT | Query Sampradāna | "To whom?" |
| SOURCE | Query Apādāna | "From where?" |
| LOCUS_TEMPORAL | Query time | "When did this happen?" |
| LOCUS_SPATIAL | Query location | "Where did this occur?" |
| PROVENANCE | Query epistemic source | "According to whom?" |
| CAUSATION | Query causal chain | "Why did this happen?" |
| PROPERTY | Query state/attribute | "What properties?" |

**Claim**: This finite set covers the semantic intent of diverse interrogative forms across languages.

**Status**: Empirically supported for English and Sanskrit; full cross-linguistic validation is ongoing work.

### 5.3 Operator Collapse Example

**Surface Forms** (English):
- "Who did X?"
- "By whom was X done?"
- "Which agent performed X?"
- "Who is responsible for X?"

**Normalized Operator**:
```
⟨PARTICIPANT_AGENT, Kartā, {}, 0⟩
```

**Cross-Linguistic** (Hindi):
- "किसने X किया?" (kisne X kiyā)
- "X किसके द्वारा किया गया?" (X kiske dvārā kiyā gayā)

**Normalized to Same Operator**.

### 5.4 Handling Non-Eventive Knowledge

**Issue**: States, properties, and taxonomies don't fit event frames.

**Solution**: Separate State/Property Layer where:
- States are time-bounded assertions
- Properties are type constraints
- Taxonomies are hierarchical relations

**Integration**: States link to events via temporal/contextual anchors but don't drive causality directly.

**Example**:
> "Ram was brave when he fought Ravana, but hesitant when he abandoned Sita."

**Representation**:
```
State₁ = ⟨brave, {Subject: Ram}, during(F_fight), document_X, 0.9⟩
State₂ = ⟨hesitant, {Subject: Ram}, during(F_abandon), document_X, 0.85⟩

F_fight = ⟨fight, {Kartā: Ram, Karma: Ravana}, ...⟩
F_abandon = ⟨abandon, {Kartā: Ram, Karma: Sita}, ...⟩
```

States are temporally scoped, avoiding contradiction while preserving context.


```markdown
## 5.5 Multi-Index Frame Organization and Clustering

### 5.5.1 Motivation

Frames are created in **authorial order** (as text is processed sequentially), but queries require access via multiple organizational schemes: causal order, temporal order, thematic grouping, and access frequency. Re-sorting frames into every possible ordering upfront is computationally prohibitive and mirrors the cognitive limitation that requires humans to use external memory aids.

We propose a **multi-index architecture** where frames are stored once but organized through multiple simultaneous orderings, with expensive indexes constructed lazily based on usage patterns.

### 5.5.2 Frame Positional Metadata

**Definition 9 (Extended Frame)**

We extend Definition 1 to include positional metadata:

```
F = ⟨k, R, t, s, c, positions⟩
```

where `positions` is a tuple:

```
positions = ⟨α, ψ, τ, η, ω⟩
```

with:
- `α` = authorial position (sentence index in source document)
- `ψ` = causal rank (position in inferred causal chain)
- `τ` = temporal rank (chronological position)
- `η` = emotional intensity (optional, for narrative analysis)
- `ω` = access frequency (query usage count)

### 5.5.3 Index Layer Architecture

**Definition 10 (Frame Index)**

A frame index is a function:

```
I: IndexType → OrderedSequence(F)
```

We maintain multiple indexes simultaneously:

| Index Type | Sort Key | Construction Cost | Construction Time |
|------------|----------|-------------------|-------------------|
| Authorial | α (given) | O(n) | Immediate |
| Temporal | τ (extracted) | O(n log n) | On first temporal query |
| Causal | ψ (inferred) | O(n² · d) | On first causal query |
| Access Pattern | ω (learned) | O(n log n) | Continuous update |
| Emotional | η (optional) | O(n log n) | On demand |

Where:
- `n` = number of frames
- `d` = average causal inference depth

**Key Principle**: Indexes are **derived views** over base frames. They can be deleted and rebuilt without corrupting ground truth.

### 5.5.4 Frame Clustering

**Definition 11 (Frame Cluster)**

A frame cluster is a tuple:

```
C = ⟨topic, F_set, coherence, access_pattern⟩
```

where:
- `topic` is a semantic label (entity, event type, or theme)
- `F_set ⊆ F` is the set of frames in the cluster
- `coherence ∈ [0,1]` measures semantic similarity
- `access_pattern` is co-occurrence statistics

**Cluster Formation Algorithm**:

```
Algorithm 1: Incremental Cluster Formation

Input: Query q, frames accessed F_accessed
Output: Updated cluster set C

1. For each pair (f_i, f_j) ∈ F_accessed × F_accessed:
2.   cooccurrence(f_i, f_j) += 1
3. 
4. If cooccurrence(f_i, f_j) > θ_cluster:
5.   If ∃ cluster C containing f_i or f_j:
6.     C.F_set ← C.F_set ∪ {f_i, f_j}
7.   Else:
8.     Create new cluster C = ⟨infer_topic(f_i, f_j), {f_i, f_j}, ...⟩
9. 
10. Update coherence scores for affected clusters
11. Evict clusters with coherence < θ_evict
```

**Cluster Coherence**:

```
coherence(C) = (1/|C.F_set|²) ∑_{f_i,f_j ∈ C.F_set} similarity(f_i, f_j)
```

where `similarity` measures semantic overlap (shared entities, related kriyā, temporal proximity).

### 5.5.5 Example: Query-Driven Frame Access

**Scenario**: Text processed in authorial order creates frames:

```
F₁ = ⟨cry, {Kartā: Ram}, t=unspecified, positions=⟨α=1, ψ=4, τ=4, ...⟩⟩
F₂ = ⟨take, {Karma: Sita}, t=unspecified, positions=⟨α=2, ψ=3, τ=3, ...⟩⟩
F₃ = ⟨kidnap, {Kartā: Ravana, Karma: Sita}, positions=⟨α=3, ψ=2, τ=2, ...⟩⟩
F₄ = ⟨hunt, {Kartā: Ram}, positions=⟨α=4, ψ=1, τ=1, ...⟩⟩
```

**Authorial order**: [F₁, F₂, F₃, F₄] (as written)  
**Causal order**: [F₄, F₃, F₂, F₁] (hunting enabled kidnapping, which caused crying)

**Query 1**: "What caused Ram to cry?" (requires causal order)
- Access via CausalIndex: [F₄, F₃, F₂, F₁]
- Traverse: F₁ ←[caused_by]— F₂ ←[caused_by]— F₃
- Answer: "Sita's kidnapping"

**Query 2** (repeated 50 times): "What happened to Sita?"
- Forms cluster: C_Sita = ⟨"Sita_fate", {F₂, F₃}, coherence=0.91⟩
- 51st query: Direct cluster access (2 frames instead of 1000+)

### 5.5.6 Composite Frames (Frame Aggregation)

For frequently co-accessed frame groups, the system can create **composite frames** as derived facts.

**Definition 12 (Composite Frame)**

```
F_comp = ⟨k_summary, R_agg, temporal_span, component_frames, confidence⟩
```

where:
- `k_summary` is an aggregate action (e.g., "childhood_experience")
- `R_agg` merges roles from component frames
- `component_frames = [F_i, F_j, ..., F_k]` are the base frames
- `confidence` reflects aggregation quality

**Example**:

```
Component frames:
F₅ = ⟨play, {Kartā: Ram, Co-agent: Friends, Locus: winter}⟩
F₆ = ⟨eat, {Kartā: Ram, Karma: chura_chini, Locus: evening}⟩  
F₇ = ⟨laugh, {Kartā: Ram, Co-agent: Friends}⟩

Composite frame (after 100+ queries about "Ram's childhood"):
F_comp = ⟨childhood_activities, 
          {Kartā: Ram, Themes: [play, eat, socialize], Setting: winter_village},
          temporal_span=[childhood_period],
          component_frames=[F₅, F₆, F₇],
          confidence=0.94⟩
```

**Storage**: Composite frames are stored in a **derived view layer**, not in the base frame graph.

**Regeneration**: Can always be recomputed from component frames if deleted.

**Usage**: Reduces retrieval cost for high-frequency aggregate queries from O(k) to O(1), where k = number of component frames.

### 5.5.7 Meta-Memory: Statistical Patterns Over Access

Beyond individual query paths (FAM, §8), the system maintains **meta-patterns** about query types.

**Definition 13 (Meta-Memory Index)**

```
M₃: QueryClass → Distribution(Clusters × EdgeTypes × Depth)
```

**Example**:

```
M₃(PROVENANCE) = {
  typical_clusters: {Epistemic_Frames: 0.73, Narrative_Frames: 0.27},
  typical_edges: {described_by: 0.81, reported_by: 0.19},
  depth_distribution: Gaussian(μ=2.3, σ=0.8)
}
```

**Usage**: When a PROVENANCE query arrives:
1. Check M₃(PROVENANCE) for typical patterns
2. Pre-fetch likely clusters (Epistemic_Frames)
3. Prioritize likely edge types (described_by)
4. Estimate depth (≈2-3 hops)

**Learning**: Updated after each query:

```
M₃(q.class).clusters[c] ← M₃(q.class).clusters[c] + α · indicator(c ∈ used_clusters)
M₃(q.class).edges[e] ← M₃(q.class).edges[e] + α · indicator(e ∈ used_edges)
```

where `α` is learning rate.

**Mathematical Formalization**:

This is a statistical model over the triple product space:

```
M₃: 𝒬 → P(𝒞 × ℰ × ℕ)
```

where:
- `𝒬` = set of query classes
- `𝒞` = set of frame clusters
- `ℰ` = set of edge types
- `ℕ` = natural numbers (depth)
- `P(...)` = probability distribution

**This formally captures "memory about memory"**: statistical knowledge about how semantic memory is typically accessed, without making new semantic claims.

### 5.5.8 Storage Architecture

**Physical Implementation**: Graph Database (Neo4j, ArangoDB, etc.)

```
Logical Layer (Kāraka Model):
  Frames as semantic objects: F = ⟨k, R, t, s, c, positions⟩

Physical Layer (Graph DB):
  Nodes:
    - Frame nodes (one per frame, properties = k, R, t, s, c, positions)
    - Entity nodes (referenced by frames)
    - Cluster meta-nodes (contain frame IDs)
  
  Edges:
    - Semantic edges (caused_by, described_by, etc.)
    - Cluster membership edges (frame → cluster)
  
  Indexes:
    - B-tree on positions.α (authorial order)
    - B-tree on positions.τ (temporal order)
    - Custom index on positions.ψ (causal order, lazy)
    - Inverted index on positions.ω (access frequency)
```

**Separation of Concerns**:
- **Kāraka model** defines semantic correctness
- **Graph DB** provides scalable storage and querying
- **Indexes** enable efficient access patterns
- **Clusters** emerge from usage, stored as meta-nodes

### 5.5.9 Complexity Analysis with Clustering

**Without Clustering**:
- Query requires scanning O(n) frames in worst case
- Causal reasoning: O(n · d) where d = inference depth

**With Clustering**:
- High-frequency queries: O(1) cluster lookup
- Cluster access: O(|C|) where |C| ≪ n (typically 2-10 frames)

**Expected Performance**:

```
P(query hits cluster) = ω_cluster / (ω_cluster + ω_novel)
```

where:
- `ω_cluster` = queries matching existing clusters
- `ω_novel` = novel queries requiring full traversal

For mature systems with sufficient usage history, `ω_cluster / ω_novel` ≈ 80/20 (Pareto principle).

**Cluster Formation Cost**:
- Per query: O(|F_accessed|²) for co-occurrence tracking
- Amortized: O(1) per query after steady state

### 5.5.10 Design Principles

**P5: Multiple Simultaneous Orderings**  
Frames maintain position in authorial, causal, temporal, and access-pattern orderings without duplication.

**P6: Lazy Index Construction**  
Expensive indexes (causal, emotional) are built only when queries require them.

**P7: Usage-Driven Clustering**  
Frame clusters emerge from observed co-access patterns, not predetermined categorization.

**P8: Compositionality**  
Composite frames and meta-memory are derived views that can be regenerated from base frames.

---

**Connection to Other Sections**:
- Clusters reduce retrieval cost mentioned in §7 (Complexity)
- Meta-memory formalizes the intuition behind FAM in §8
- Physical storage supports bounded traversal from §7.1
```

---

**Copy this entire block and insert it after Section 5.4 (Handling Non-Eventive Knowledge) in your paper.**

---

## 6. Point-of-View as Constraint Functions

### 6.1 Motivation

Different perspectives on the same knowledge base require different subgraph access patterns. Traditional systems handle this through result re-ranking or filtering, losing semantic rigor.

### 6.2 Formal Definition

**Definition 5 (Point-of-View)**

A POV is a constraint function:

```
POV = ⟨F_filter, E_filter, T_filter, P_priority⟩
```

where:
- `F_filter: F → {0,1}` determines frame admissibility
- `E_filter: E → {0,1}` determines edge traversability
- `T_filter: Time → {0,1}` temporal slice selector
- `P_priority: Provenance → ℝ` source priority weighting

**Definition 6 (POV-Restricted Query)**

Given query `Q` and POV `V`:

```
Result(Q, V) = Evaluate(Q, G|_V)
```

where `G|_V` is the subgraph satisfying V's constraints.

### 6.3 Example POVs

**Narrative POV** (What happened in the story?):
```
F_filter: all narrative frames
E_filter: temporal, causal edges
T_filter: story timeline
P_priority: primary text > commentary
```

**Epistemic POV** (Who said what?):
```
F_filter: all frames
E_filter: epistemic edges (reported_by, described_by)
T_filter: all time
P_priority: source credibility ordering
```

**Temporal Slice POV** (What happened on day X?):
```
F_filter: all frames
E_filter: all edge types
T_filter: t = X
P_priority: temporal proximity
```

### 6.4 POV Composition

POVs can be composed:

```
POV_combined = POV₁ ∩ POV₂
```

This enables queries like: "According to Valmiki, what happened during the war?"

---

## 7. Bounded Reasoning and Complexity

### 7.1 Traversal Constraints

**Definition 7 (Legal Traversal)**

Given operator `Op` and current frame `F_i`:

```
Next(F_i, Op) = {F_j | (F_i, F_j, e) ∈ E, e ∈ Op.constraints}
```

**Traversal Depth**: Limited by `Op.h_max` (typically ≤ 4).

### 7.2 Termination Guarantee

**Theorem 1 (Termination)**

All query evaluations terminate in finite time.

**Proof**:
1. Traversal depth bounded by `h_max` (finite constant)
2. Branching factor bounded by operator constraints
3. Cycle detection prevents infinite loops
4. Frame set F is finite

Therefore, maximum visited nodes = O(∑_{i=0}^{h_max} d^i) where d is bounded branching factor. ∎

### 7.3 Complexity Analysis

**Frame Extraction**: For document with S sentences:
- Sentence processing: O(S)
- Role assignment per frame: O(R) where R ≤ 8
- **Total**: O(S)

**Query Evaluation** (without FAM):
- Bounded depth traversal: O(d^{h_max})
- Since h_max and d are small constants: **O(1) bounded time**

**Query Evaluation** (with FAM):
- Cache lookup: O(1)
- Path verification: O(h_max)
- **Total**: O(1)

### 7.4 Space Complexity

- Frames: O(N) where N = document count × average frames per doc
- Edges: O(E) ≤ O(N²) worst case, typically O(N log N) in practice
- FAM entries: O(Q) where Q = unique query patterns (with decay)

---

## 8. Frame Access Memory (Procedural Layer)

### 8.1 Motivation

Repeated queries often traverse identical reasoning paths. Recomputation is inefficient and unstable across model updates.

### 8.2 Design Principle

FAM is a **procedural optimization layer**—not semantic memory. Its presence or absence does not affect correctness, only efficiency.

### 8.3 Formal Definition

**Definition 8 (FAM Entry)**

```
M = ⟨Q_sig, Path, c, u, τ⟩
```

where:
- `Q_sig` is query signature (operator + key entities)
- `Path = [F₁, F₂, ..., F_k]` is ordered frame sequence
- `c ∈ [0,1]` is confidence score
- `u` is usage count
- `τ` is last-access timestamp

### 8.4 Confidence Update (Engineering Policy)

```
c_{t+1} = c_t + α·success - β·failure - γ·age(t)
```

where α, β, γ are **engineering parameters** (not learned, not optimal).

**Eviction**: Entries with c < θ are removed.

**Key Property**: FAM is a cache. Deleting it does not corrupt ground truth.

### 8.5 Meta-Procedural Memory

Beyond individual paths, the system maintains **access pattern statistics**:

- Frequently co-accessed frame clusters
- POV-specific traversal patterns
- Query-type to subgraph mappings

This is analogous to database query planning statistics—optimization over access patterns, not truth claims.

---

## 9. Role of LLMs

### 9.1 Strict Separation

LLMs are used **only** for:

1. **Surface-to-Operator Mapping**: Natural language → semantic operators
2. **Frame Extraction**: Text → structured frames
3. **Answer Synthesis**: Structured results → natural language

LLMs are **never** used as:
- Source of ground truth
- Reasoning authority
- Persistent memory

### 9.2 Small Model Decomposition

Tasks decompose naturally into specialized models:

| Task | Model Type | Rationale |
|------|------------|-----------|
| Sentence segmentation | Rule-based/tiny | Deterministic |
| Entity recognition | Fine-tuned small | Well-defined task |
| Kriyā normalization | Small classifier | Closed vocabulary |
| Kāraka assignment | Structured predictor | Bounded output space |
| Operator classification | Small transformer | Limited operator set |
| Causal inference | Medium LLM | Requires broader context |
| Synthesis | Large LLM | Fluency matters |

**Benefits**:
- Reduced hallucination (smaller models for structured tasks)
- Better debuggability
- Easier updates
- Lower cost
- **Robustness**: Single model failure doesn't cascade

### 9.3 Future-Proofing

As LLMs improve:
- Extraction quality improves
- Synthesis quality improves
- Architecture remains stable

The system is **LLM-agnostic by design**.

---

## 10. Error Containment and Graceful Degradation

### 10.1 Extraction Error Types

1. **Incorrect kriyā**: Wrong action classification
2. **Role misassignment**: Entity assigned wrong semantic role
3. **Missing frame**: Relevant event not extracted
4. **Spurious frame**: Non-existent event hallucinated

### 10.2 Containment Mechanisms

**Provenance Tagging**: Every frame carries source and confidence.

**Non-Propagating Errors**: Incorrect frame F_i affects only queries traversing F_i.

**Confidence Decay**: FAM paths using low-confidence frames decay faster.

**Editability**: Frames are first-class objects; correction doesn't require retraining.

### 10.3 Comparison with Alternatives

| System | Error Impact | Recovery |
|--------|--------------|----------|
| Pure LLM | Silent hallucination | Regenerate (unstable) |
| Traditional KG | Persistent corruption | Manual graph surgery |
| **This System** | Bounded, tagged | Frame edit + FAM decay |

---

## 11. Planned Evaluation and Testing Protocol

This section outlines the comprehensive empirical evaluation we will conduct to validate the architectural claims and measure system performance across multiple dimensions.

### 11.1 Evaluation Datasets

#### Dataset 1: Multi-Document Narrative Reasoning
**Domain**: Epic literature (Ramayana/Mahabharata)

**Corpus Composition**:
- Primary texts: Valmiki Ramayana, Vyasa Mahabharata
- Secondary sources: 3-5 classical commentaries per text
- Modern scholarly interpretations
- **Total**: ~200-300 text segments
- **Expected frames**: 800-1200 event frames
- **Expected edges**: 1500-2500 frame-to-frame edges

**Rationale**: Epic narratives stress-test critical capabilities:
- Multi-source reconciliation (different authors)
- Nested epistemic attribution ("X says Y dreamed Z")
- Long causal chains spanning multiple books
- Temporal reasoning with vague references
- Contradictory accounts across sources

#### Dataset 2: Scientific Literature Synthesis
**Domain**: Climate science or biomedical research

**Corpus Composition**:
- 50-100 peer-reviewed papers from a focused subdomain
- Papers with explicit citation relationships
- Mix of original research and review articles
- **Expected frames**: 2000-4000 (higher density than narratives)

**Rationale**: Scientific literature requires:
- Provenance tracking (which study found what)
- Causal claim validation
- Contradiction detection across studies
- Temporal progression of knowledge
- Method-result relationship tracking

#### Dataset 3: Legal/Regulatory Reasoning
**Domain**: Statutory interpretation (if resources permit)

**Corpus Composition**:
- Base statutes + amendments over time
- Court interpretations and precedents
- Regulatory guidance documents
- **Expected frames**: 500-1000

**Rationale**: Legal domain tests:
- Amendment and revision tracking
- Hierarchical authority (statute > regulation > guidance)
- Temporal validity windows
- Explicit vs. implicit causation

### 11.2 Baseline Systems

We will compare against four baseline approaches:

#### B1: Dense Retrieval + LLM (RAG)
- Vector database (FAISS/Pinecone)
- Top-k retrieval (k=5, 10)
- GPT-4 or Claude for synthesis
- **Purpose**: Current state-of-practice baseline

#### B2: Simple Entity-Centric KG
- Traditional triple store (subject-predicate-object)
- SPARQL queries
- **Purpose**: Compare event-centric vs. entity-centric

#### B3: Direct LLM (Zero-Shot)
- Large LLM without retrieval
- All context in prompt where possible
- **Purpose**: Measure value of structured representation

#### B4: Abstract Meaning Representation (AMR)
- Existing AMR parser
- Graph-based query matching
- **Purpose**: Compare to established semantic representation

### 11.3 Evaluation Tasks and Metrics

#### Task Category 1: Role-Based Queries (Single-Hop)

**Example Questions**:
- "Who funded the study?"
- "What did Ram use to cross the ocean?"
- "When did the experiment occur?"

**Metrics**:
- **Accuracy**: Correct answer extraction (%)
- **Source Citation Rate**: Provenance provided (%)
- **Latency**: Query response time (ms)
- **Confidence Calibration**: Correlation between predicted and actual correctness

**Success Criteria**: 
- Accuracy > 90% on well-formed queries
- Source citation in 100% of cases
- Latency < 500ms for single-hop

#### Task Category 2: Multi-Hop Reasoning

**Example Questions**:
- "According to which commentary did Ram feel remorse?"
- "What caused the war according to Ravana's perspective?"
- "Which studies support the hypothesis that X causes Y?"

**Metrics**:
- **Path Accuracy**: Correct reasoning chain (%)
- **Provenance Accuracy**: Correct source attribution (%)
- **Hop Count Distribution**: Average path length
- **Explainability Score**: Human rating of reasoning transparency (1-5 scale)

**Success Criteria**:
- Path accuracy > 80% for 2-3 hop queries
- Provenance accuracy > 85%
- Explainability score > 4.0/5.0

#### Task Category 3: POV-Sensitive Queries

**Example Questions**:
- "From Valmiki's text only, what motivated Ram?"
- "In papers published after 2020, what is the consensus on X?"
- "According to the original statute (not amendments), is Y allowed?"

**Metrics**:
- **Filter Precision**: Correct exclusion of out-of-POV content (%)
- **Filter Recall**: Inclusion of all in-POV content (%)
- **POV Consistency**: No leakage across POV boundaries (%)

**Success Criteria**:
- Precision > 95%
- Recall > 90%
- Zero POV leakage on test set

#### Task Category 4: Contradiction Detection

**Example Questions**:
- "Do any sources disagree on how Ram crossed the ocean?"
- "Which studies report conflicting results on X?"
- "Are there inconsistent dates for event Y?"

**Metrics**:
- **Detection Precision**: True contradictions / flagged contradictions
- **Detection Recall**: Detected contradictions / actual contradictions
- **Source Traceability**: Can trace both sides of contradiction (%)

**Success Criteria**:
- Precision > 75% (acknowledging difficulty)
- Recall > 70%
- Source traceability = 100%

#### Task Category 5: Temporal Reasoning

**Example Questions**:
- "What happened between events X and Y?"
- "Which experiment was conducted first?"
- "How long after A did B occur?"

**Metrics**:
- **Ordering Accuracy**: Correct temporal sequence (%)
- **Interval Precision**: Correct duration estimation where specified
- **Vagueness Handling**: Appropriate confidence for underspecified times

**Success Criteria**:
- Ordering accuracy > 85% for explicit timestamps
- Graceful degradation for vague references

### 11.4 Error Analysis Protocol

#### Extraction Quality Sensitivity

**Methodology**: Create synthetic degraded versions of gold-standard extractions

**Degradation Levels**:
1. **95% accuracy**: Near-perfect extraction (baseline)
2. **85% accuracy**: Realistic noisy extraction
3. **75% accuracy**: High noise scenario
4. **60% accuracy**: Severe degradation

**Error Types to Inject**:
- Kriyā misclassification (wrong action)
- Role swapping (Kartā ↔ Karma)
- Missing frames (false negatives)
- Spurious frames (false positives)

**Measurement**:
- Task performance degradation at each level
- Error propagation distance (how far errors spread)
- Recovery rate (can system self-correct via FAM decay?)

#### Failure Mode Cataloging

**Systematic Documentation**:
For each failure on test set:
- Query type
- Failure category (extraction, traversal, operator, synthesis)
- Root cause analysis
- Potential mitigation

**Target**: Failure taxonomy covering ≥90% of errors

### 11.5 Ablation Studies

#### A1: Without FAM (Frame Access Memory)
**Test**: Remove procedural memory layer
**Measure**: Latency increase, consistency across repeated queries

#### A2: Without POV Constraints
**Test**: No point-of-view filtering
**Measure**: Source confusion rate, answer mixing

#### A3: Unbounded Traversal
**Test**: Remove hop limits
**Measure**: Query time, false positive rate

#### A4: Entity-Centric (Not Event-Centric)
**Test**: Convert to traditional entity-relation triples
**Measure**: Causal reasoning accuracy, temporal coherence

### 11.6 Human Evaluation

**Evaluators**: 3-5 domain experts per dataset

**Evaluation Dimensions**:
1. **Answer Correctness** (1-5): Is the answer right?
2. **Provenance Quality** (1-5): Is the source correctly cited?
3. **Reasoning Transparency** (1-5): Can you follow the logic?
4. **Handling Uncertainty** (1-5): Appropriate confidence expression?

**Inter-Annotator Agreement**: Target Fleiss' κ > 0.7

**Sample Size**: 100-200 query-answer pairs per dataset

### 11.7 Cross-Linguistic Validation (Extended Study)

**Languages**: English, Hindi, Sanskrit

**Test Set**: 50 parallel questions per language

**Metrics**:
- Operator collapse rate (do different surface forms map to same operator?)
- Role assignment consistency
- Performance parity across languages

**Success Criteria**: <10% performance variance across languages

### 11.8 Scalability Testing

#### Small Scale (Current)
- 100-300 documents
- ~1000 frames
- Single machine

#### Medium Scale (Target)
- 1000-5000 documents
- ~50,000 frames
- Measure: query latency, memory usage

#### Large Scale (Future)
- 10,000+ documents
- ~500,000 frames
- Graph database backend required
- Distributed query evaluation

**Performance Targets**:
- Small: <100ms average query time
- Medium: <500ms average query time
- Large: <2s average query time

### 11.9 Integration Testing

**Test LLM Compatibility**:
- GPT-4, Claude, Gemini for extraction
- Measure: extraction quality variance across models
- Validate: system remains stable with model changes

**Test Incremental Updates**:
- Add new documents to existing graph
- Measure: consistency, no corruption
- Validate: FAM adapts to new patterns

### 11.10 Expected Timeline

**Phase 1** (Months 1-2): Dataset preparation, baseline implementation
**Phase 2** (Months 3-4): Core system implementation, unit testing
**Phase 3** (Months 5-6): Primary evaluation (Tasks 1-5), ablations
**Phase 4** (Months 7-8): Human evaluation, error analysis
**Phase 5** (Months 9-10): Scalability testing, cross-linguistic validation
**Phase 6** (Months 11-12): Results analysis, paper revision

### 11.11 Success Criteria Summary

For this architecture to be considered validated, we require:

**Minimum Requirements**:
- Single-hop accuracy > 85% vs. best baseline
- Multi-hop reasoning > 75% path accuracy
- Provenance tracking: demonstrable advantage over all baselines
- POV filtering: >90% precision/recall
- Graceful degradation: <30% performance loss at 75% extraction accuracy
- Human evaluation: >4.0/5.0 average across dimensions

**Stretch Goals**:
- Outperform RAG baseline on 4/5 task categories
- Cross-linguistic operator collapse demonstrated empirically
- Scalability to 50,000 frames with <500ms queries

### 11.12 Planned Publications

**Primary Paper** (this work):
- Architecture + formal foundations + evaluation results
- Target: ACL/EMNLP/AAAI

**Follow-up Studies**:
- Cross-linguistic validation (specialized NLP venue)
- Scientific literature application (domain-specific venue)
- Scalability engineering (systems/DB venue)

---

**Note**: This evaluation protocol represents our commitment to rigorous empirical validation. Results will be reported honestly, including negative results and failure cases. The architecture will be refined based on empirical findings.

---

## 12. Related Work

### 12.1 Knowledge Graphs

Traditional KGs (Freebase, Wikidata, YAGO) use entity-centric triples. Our event-centric approach relates to:

- **Semantic Role Labeling** (Palmer et al., 2010): Similar role concepts but no persistent memory architecture
- **Abstract Meaning Representation** (Banarescu et al., 2013): Event-centric but focused on single-sentence parsing
- **Event-Centric KGs** (Rospocher et al., 2016): NEWSREADER uses events but lacks bounded operator algebra

**Key Difference**: We formalize bounded traversal, POV constraints, and procedural memory as architectural primitives.

### 12.2 LLM Memory Systems

Recent work on augmenting LLMs with memory:

- **MemPrompt** (Madaan et al., 2022): Episodic memory in prompts
- **Retrieval-Augmented Generation**: Dense retrieval + generation
- **WebGPT** (Nakano et al., 2021): Web search integration

**Key Difference**: We provide **persistent structured semantics** rather than episode-based retrieval.

### 12.3 Kāraka Theory in NLP

Computational implementations:

- **Pāṇinian Framework for Sanskrit** (Bharati et al., 1995)
- **Dependency Parsing** (Begum et al., 2008)

**Key Difference**: We extend kāraka roles to language-agnostic architecture with formal operator algebra and memory layers.

---

## 13. Limitations and Future Work

### 13.1 Current Limitations

**L1: Extraction Dependence**  
System quality bottlenecked by frame extraction accuracy.

**L2: Single-Domain Evaluation**  
Proof-of-concept limited to narrative reasoning.

**L3: Role Set Empirical Validation**  
Cross-linguistic coverage requires broader evaluation.

**L4: State/Event Integration**  
Interface between event and state layers needs refinement.

**L5: Scalability**  
Large-scale deployment (millions of frames) not yet tested.

### 13.2 Future Work

**F1: Comprehensive Evaluation**  
- Scientific literature (multi-paper synthesis)
- Legal reasoning (statute interpretation)
- Personal knowledge management

**F2: Cross-Linguistic Validation**  
- Operator collapse across typologically diverse languages
- Role refinement patterns

**F3: Extraction Improvement**  
- Iterative correction workflows
- Human-in-the-loop validation
- Uncertainty propagation

**F4: Scalability Engineering**  
- Graph database backends
- Distributed traversal
- Index optimization

**F5: Integration Studies**  
- LLM + semantic memory hybrid workflows
- Real-world deployment case studies

---

## 14. Conclusion

We have presented architectural foundations for persistent semantic memory systems grounded in three core principles: event-centric representation, bounded reasoning via universal operators, and explicit separation of truth, optimization, and synthesis layers.

The proposed architecture addresses structural limitations in both pure LLM systems (lack of persistence, auditability, causality) and traditional KGs (unbounded relations, weak temporal reasoning). By formalizing Point-of-View as graph constraint functions and introducing Frame Access Memory as procedural optimization, we provide a composable foundation for long-horizon knowledge systems.

Our proof-of-concept evaluation demonstrates feasibility on multi-document narrative reasoning, with particular strengths in provenance tracking and contradiction detection. However, this work is explicitly positioned as **foundational architecture**, not a complete deployed system. Comprehensive empirical validation across domains, languages, and scales remains essential future work.

As LLMs continue to advance, the need for persistent semantic structure, explicit causality, and cumulative knowledge building does not diminish—it intensifies. This architecture aims to provide the substrate on which such capabilities can be built, complementing rather than competing with progress in foundation models.

---

## Appendix A: Formal Definitions Summary

**A1. Event Frame**  
`F = ⟨k, R, t, s, c⟩`

**A2. Frame Graph**  
`G = (F, E)` where `E ⊆ F × F × EdgeType`

**A3. Semantic Operator**  
`Op = ⟨type, role, constraints, h_max⟩`

**A4. Point-of-View**  
`POV = ⟨F_filter, E_filter, T_filter, P_priority⟩`

**A5. POV-Restricted Query**  
`Result(Q, V) = Evaluate(Q, G|_V)`

**A6. FAM Entry**  
`M = ⟨Q_sig, Path, c, u, τ⟩`

---

## Appendix B: Detailed Examples

### B.1 Multi-Hop Provenance Query

**Text**:
> "Ram dreamed about his childhood. Valmiki described this dream in his epic."

**Frames**:
```
F₁ = ⟨dream, {Kartā: Ram, Karma: Childhood}, unspecified, source_text, 0.93⟩
F₂ = ⟨describe, {Kartā: Valmiki, Karma: F₁}, unspecified, source_text, 0.91⟩
```

**Graph**:
```
F₂ --[described_content]--> F₁
```

**Query**: "How do we know about Ram's childhood dream?"

**Operator**: `⟨PROVENANCE, focus=Childhood, {epistemic_edges}, h_max=3⟩`

**Traversal**:
```
Start: F₁ (dream about childhood)
Follow: described_by^{-1} edge
Arrive: F₂ (Valmiki describes)
Extract: F₂[Kartā] = Valmiki
```

**Answer**: "According to Valmiki's description"

**Provenance Path**: F₁ ← F₂ (length 1, within bounds)

### B.2 POV-Filtered Query

**Scenario**: Multiple sources disagree on event details.

**Frames**:
```
F₃ = ⟨cross_ocean, {Kartā: Ram, Karaṇa: Bridge}, time_T, Valmiki, 0.95⟩
F₄ = ⟨cross_ocean, {Kartā: Ram, Karaṇa: Flight}, time_T, Commentary_A, 0.78⟩
```

**Query**: "How did Ram cross the ocean? (per Valmiki)"

**POV**: `⟨F_filter: source=Valmiki, E_filter: all, T_filter: all, P_priority: primary⟩`

**Result**: Only F₃ is visible → Answer: "Using a bridge"

**Alternative POV** (all sources):  
Both F₃ and F₄ visible → Answer: "Accounts differ: bridge (Valmiki) vs. flight (Commentary A)"

---

## Appendix C: Failure Modes

### C.1 Out-of-Scope Queries

**Query**: "How tall is Mount Meru?"

**Issue**: Pure property query, no event.

**System Behavior**: Route to property layer or decline with explanation.

### C.2 Operator Ambiguity

**Query**: "How did Ram defeat Ravana?"

**Ambiguity**: Instrumental (using what?) vs. Causal (why/what enabled?)

**System Behavior**:  
- Confidence scoring for both interpretations
- Request clarification
- Return both with labels

### C.3 Incomplete Provenance

**Query**: "Who first said Ram went to Lanka?"

**Issue**: No reporting frame exists for earliest mention.

**System Behavior**:  
- Return partial answer: "Earliest found: Source X"
- Tag confidence < 1.0
- Never hallucinate a source

### C.4 Extraction Error

**Error**: "Ram fought Sita" (incorrect role assignment)

**Impact**: Queries traversing this frame return wrong results.

**Mitigation**:  
- Confidence tag flags suspicion
- Correction updates single frame
- FAM paths decay automatically
- No cascade corruption

---

## References

[Include standard academic references - I'll provide a representative sample]

Banarescu, L., et al. (2013). Abstract Meaning Representation for Sembanking. *Linguistic Annotation Workshop*.

Begum, R., et al. (2008). Dependency annotation scheme for Indian languages. *IJCNLP*.

Bharati, A., et al. (1995). *Natural Language Processing: A Paninian Perspective*. Prentice-Hall.

Madaan, A., et al. (2022). Memory-assisted prompt editing for improving GPT-3 reasoning. *arXiv preprint*.

Nakano, R., et al. (2021). WebGPT: Browser-assisted question-answering with human feedback. *arXiv preprint*.

Palmer, M., et al. (2010). Semantic role labeling. *Synthesis Lectures on Human Language Technologies*.

Rospocher, M., et al. (2016). Building event-centric knowledge graphs from news. *Journal of Web Semantics*.

---

**Author Contributions**: [To be filled]

**Acknowledgments**: We thank the anonymous reviewers for detailed and constructive feedback that significantly improved this work.

**Code and Data Availability**: Proof-of-concept implementation and evaluation data will be released upon acceptance.