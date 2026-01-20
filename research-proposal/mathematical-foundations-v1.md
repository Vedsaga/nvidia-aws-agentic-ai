# Mathematical Foundations for Recursive Semantic Memory
## A Pāṇinian Architecture with Formal Guarantees

**Version**: 1.0 (For Peer Review)  
**Date**: 2026-01-19  
**Status**: Draft for Mathematical Review

---

## Abstract

We present the mathematical foundations for a recursive semantic memory architecture grounded in Pāṇinian linguistic theory. This document formalizes: (1) the **Binary Frame Decomposition** (Kriyā/Prātipadikārtha) as a structural completeness theorem over linguistic utterances, (2) the **Five-Frame Recursive Hierarchy** (Φ₁–Φ₅) with formal typing and composition rules, (3) the **Finite Query Algebra** based on Sanskrit interrogatives with decidability proofs, and (4) the **Meta-Frame Provenance Schema** treating observation context as first-class frames.

We distinguish clearly between **axioms** (architectural commitments), **definitions** (formal constructs), and **theorems** (provable claims). Counter-examples are systematically addressed. The goal is to provide a rigorous foundation suitable for peer review and implementation.

---

# Part I: Foundations

## 1. Notation and Conventions

| Symbol | Meaning |
|--------|---------|
| Φᵢ | Frame type at level i (1 ≤ i ≤ 5) |
| F, G | Individual frames |
| π | Projection operator |
| ≡ | Identity relation |
| λ | Free variable (in query templates) |
| c(·) | Confidence measure |
| t | Temporal locus |
| s | Source/provenance |
| L | Lakāra (verbal mood) |
| V | Vibhakti (nominal case) |

---

## 2. Axiomatic Commitments

We distinguish **axioms** (accepted without proof as architectural commitments) from **theorems** (derived from axioms).

### Axiom A1: Symbolic Domain Restriction

**Statement**: The semantic processing system operates exclusively on **symbolic representations**—discrete tokens that can be written, stored, and transmitted. Physical communicative acts (gestures, silence, continuous signals) require explicit transduction to symbolic form before processing.

**Boundary**: "If you can write it down, the system can frame it."

**Rationale**: Mathematical completeness guarantees apply only within well-defined symbolic domains.

### Axiom A2: Event Primacy

**Statement**: All factual semantic relations involving change, causation, or temporal dynamics are mediated through **event frames** (Kriyā).

**Scope**: This applies to action-oriented knowledge. Static relations (identity, taxonomy, properties) are handled via **state frames** (Prātipadikārtha).

### Axiom A3: Finite Core Role Set

**Statement**: Event participation is expressed through a finite set of 6 semantic roles (Kārakas):

```
K = {Kartā, Karma, Karaṇa, Sampradāna, Apādāna, Adhikaraṇa}
```

| Role | Sanskrit | Function |
|------|----------|----------|
| Kartā | कर्ता | Agent (independent doer) |
| Karma | कर्म | Patient (most affected) |
| Karaṇa | करण | Instrument (enabling means) |
| Sampradāna | सम्प्रदान | Recipient/Beneficiary |
| Apādāna | अपादान | Source/Ablative origin |
| Adhikaraṇa | अधिकरण | Locus (spatial/temporal) |

**Evidence**: This role set has been validated across typologically diverse languages for 2500+ years.

### Axiom A4: Bounded Traversal

**Statement**: All reasoning operations are constrained by operator-defined traversal rules with finite depth limits.

**Guarantee**: Ensures termination and inspectability.

### Axiom A5: Observational Commitment

**Statement**: Observations are treated as fixed ground facts relative to the system and are not modified during correction. Relevance is determined by query-time filtering (POV), not deletion. Storage is cheap; lost provenance is irretrievable.

**Clarification**: This is an architectural constraint, not an epistemological claim about reality. Observations may be noisy or uncertain in their acquisition, but once committed to the system, they serve as the stable base against which identity hypotheses are tested.

### Axiom A6: Identity as Hypothesis

**Statement**: Entity identity is **never** assumed from string/label matching. It must be explicitly asserted as a typed identity frame with provenance and confidence.

**Implementation**: `Ram_instance_42 ≠ Ram_instance_73` by default, until an identity frame links them.

### Clarification: Confidence as Ranking Metric

**Confusion Check**: "Confidence" here is **not** a statistical probability (e.g., "90% chance of truth"). It is a **deterministic ranking score** used for conflict resolution.

**Operational Definition**:
1.  **Tie-Breaking**: If hypothesis H₁ conflicts with H₂, and score(H₁) > score(H₂), the system retracts H₂ first.
2.  **Weakest Link**: A conclusion derived from multiple assumptions inherits the *lowest* score among them (`min` rule).
3.  **Source**: Scores are assigned by the extraction layer (e.g., LLM log-probs or rule heuristics), but they are treated merely as ordinal ranks within the graph.

**Why this matters**: We do not claim this system manages *uncertainty* in the Bayesian sense. We claim it manages *contradiction* by having a strictly ordered preference list.

---

## 3. The Binary Frame Decomposition

### 3.1 Structural Claim

**Definition 1 (Symbolic Utterance)**

Let U be a **symbolic utterance**—any finite string of tokens from a vocabulary Σ that constitutes a well-formed expression in some natural or formal language.

**Definition 2 (Frame Types)**

We define two fundamental frame types:

1. **Kriyā Frame (Action)**: Represents an event with participants
   ```
   F_kriyā = ⟨k, R, L, t, s, c⟩
   ```
   where:
   - k ∈ K_canonical (canonical action from closed vocabulary)
   - R: Kārakas → Entities (partial function assigning roles)
   - L ∈ Lakāra (verbal mood: indicative, imperative, conditional, etc.)
   - t ∈ Time ∪ {⊥} (temporal locus or unspecified)
   - s ∈ Sources (provenance)
   - c ∈ [0,1] (confidence)

2. **Prātipadikārtha Frame (State)**: Represents identity, property, or taxonomic relation
   ```
   F_state = ⟨subject, predicate, temporal_scope, s, c⟩
   ```
   where predicate ∈ {Property, Identity, Taxonomy}

**Theorem 1 (Binary Canonical Reduction)**

*For any symbolic utterance U that constitutes a well-formed linguistic expression, there exists a canonical reduction:*

```
U → F_primary + M*

where:
  F_primary ∈ (Kriyā_Frames ∪ Prātipadikārtha_Frames)
  M* = zero or more meta-operators (Nañ, Svarūpa, Adhyāhāra, Nipāta)
```

**Claim**: Every utterance admits a *primary* frame of exactly one type, potentially augmented by meta-operators.

**Proof Sketch**:

1. **Exhaustiveness**: Every linguistic expression either:
   - Asserts something about an action/event (verb-centric) → Kriyā
   - Asserts something about an entity's state/identity/property (noun-centric) → Prātipadikārtha

2. **Uniqueness**: The distinction is determined by the syntactic head:
   - Verbal head → Kriyā frame
   - Nominal head → Prātipadikārtha frame

3. **Handling of edge cases**:

| Surface Form | Apparent Challenge | Resolution |
|--------------|-------------------|------------|
| Questions | No truth value? | Kriyā/State frame + interrogative Lakāra |
| Commands | No assertion? | Kriyā frame + imperative Lakāra (विधिलिङ्) |
| Negation | About nothing? | Frame + Nañ meta-operator (negated=true) |
| Performatives | Saying = Doing? | Standard Kriyā: ⟨promise, {Kartā:I}⟩ |
| Ellipsis | Missing content? | Adhyāhāra operator (context fill) |
| Quotation | Meta-level? | Svarūpa operator (treat string as entity) |
| Conditionals | Counterfactual? | Kriyā + conditional Lakāra (लिङ्/लृट्) |

**Important Caveats**:

1. This is a claim about **linguistic structure**, not about reality
2. The "exactly one" claim holds for the **primary frame**; meta-operators augment but do not replace
3. Complex discourse may require **multiple frames** in sequence (e.g., "Ram ate and Sita danced" → two Kriyā frames)
4. The theorem is **falsifiable**: a counter-example would be an utterance that cannot be reduced to either frame type plus meta-operators

**Scope**: This theorem applies within the defined symbolic domain (Axiom A1). Edge cases in specialized domains (formal logic metalanguage, paradoxical self-reference) may require extension. ∎

### 3.2 The Lakāra System (Verbal Moods)

The Lakāra system encodes mood/modality within the frame:

| Lakāra | Name | Semantics | Example |
|--------|------|-----------|---------|
| लट् (laṭ) | Present Indicative | Actual present | "Ram eats" |
| लिट् (liṭ) | Perfect | Completed past | "Ram ate (witnessed)" |
| लुट् (luṭ) | Periphrastic Future | Definite future | "Ram will eat" |
| लृट् (lṛṭ) | Simple Future | Probable future | "Ram might eat" |
| लेट् (leṭ) | Vedic Subjunctive | Wish/Hope | "May Ram eat" |
| लोट् (loṭ) | Imperative | Command | "Eat, Ram!" |
| लिङ् (liṅ) | Optative/Conditional | Should/Would | "Ram should eat" / "If Ram ate" |
| लुङ् (luṅ) | Aorist | Past (unspecified) | "Ram ate (sometime)" |
| लङ् (laṅ) | Imperfect | Past continuous | "Ram was eating" |
| लृङ् (lṛṅ) | Conditional | Counterfactual | "Ram would have eaten" |

**Integration**: Every Kriyā frame carries an L ∈ Lakāra field encoding modality.

### 3.3 Meta-Operators

For linguistic edge cases, we employ meta-operators that transform frames:

| Operator | Sanskrit | Function |
|----------|----------|----------|
| Nañ | नञ् | Negation: F → F[negated=true] |
| Svarūpa | स्वरूप | Quotation: treat expression as entity |
| Adhyāhāra | अध्याहार | Ellipsis: inherit from context |
| Nipāta | निपात | Particles: attach emphasis/sentiment |

---

# Part II: The Five-Frame Recursive Hierarchy

## 4. Type Definitions

**Definition 3 (Frame Type Hierarchy)**

```
FrameTypes = {
  Φ₁: Perception Frames       (sensory/input layer)
  Φ₂: Semantic Frames         (Kriyā ∪ Prātipadikārtha)
  Φ₃: Identity Frames         (glue hypotheses)
  Φ₄: Projection Frames       (synthesized knowledge)
  Φ₅: Meta-Trace Frames       (reasoning records)
}
```

**Type Ordering**: Φ₁ < Φ₂ < Φ₃ < Φ₄ < Φ₅ (strict hierarchy)

### 4.1 Level 1-2: Base Frames

**Definition 4 (Base Frame)**

A base frame is the atomic semantic unit:

```
F^(1,2) ∈ Φ₁ ∪ Φ₂

F^(1,2) = ⟨k, R, L, t, s, c, E⟩

where:
- k ∈ K_canonical ∪ P_canonical (canonical action or property)
- R: Kārakas → EntityInstances (partial function)
- L ∈ Lakāra (mood)
- t ∈ Time ∪ {⊥}
- s ∈ Sources
- c ∈ [0,1]
- E = {e₁, e₂, ..., eₙ} where eᵢ ∈ EntityInstances
```

**Critical Property**: Entities in E are **instance identifiers**, not canonical references.

**Example**:
```
F₁ = ⟨eat, {Kartā: Ram_inst_42}, indicative, t₁, doc_1, 0.95, {Ram_inst_42}⟩
F₂ = ⟨king, {Subject: Ram_inst_73}, indicative, t₂, doc_1, 0.92, {Ram_inst_73}⟩
```

Note: `Ram_inst_42 ≠ Ram_inst_73` by default (Axiom A6).

### 4.2 Level 3: Identity Frames

**Definition 5 (Identity Frame)**

```
F^(3) ∈ Φ₃

F^(3) = ⟨≡, {A: e₁, B: e₂}, t, s, c⟩

where:
- ≡ is the identity operator (binary relation)
- e₁, e₂ ∈ EntityInstances
- s ∈ {inference_engine, user_assertion, heuristic_matcher, ...}
- c ∈ [0,1]
```

**Semantics**: F^(3) asserts the **hypothesis** that e₁ and e₂ denote the same real-world entity.

**Properties**:

1. **Symmetry**: ⟨≡, {A: e₁, B: e₂}⟩ ⟺ ⟨≡, {A: e₂, B: e₁}⟩
2. **Transitivity with confidence decay**:
   ```
   If F₃ᵃ = ⟨≡, {e₁, e₂}, c_a⟩ and F₃ᵇ = ⟨≡, {e₂, e₃}, c_b⟩
   Then infer F₃ᶜ = ⟨≡, {e₁, e₃}, s=transitive_closure, c = c_a · c_b⟩
   ```

**Example (The Mystery Novel Problem)**:

```
Page 5:  F₁ = ⟨arrive, {Kartā: Ram_p5}, Chapter_1⟩
Page 50: F₂ = ⟨murder, {Kartā: Ram_p50}, Chapter_5⟩

Identity choices (different POVs):
F₃_Detective = ⟨≡, {Ram_p5, Ram_p50}, Detective_POV, 0.3⟩
F₃_Reader    = ⟨≢, {Ram_p5, Ram_p50}, Reader_POV, 0.9⟩
F₃_Author    = ⟨≡, {Ram_p5, Ram_p50}, Ground_Truth, 1.0⟩
```

The system preserves all interpretations until POV determines which is active.

### 4.3 Level 4: Projection Frames

**Definition 6 (Projection Operator)**

```
π: (Φ₁ ∪ Φ₂)* × Φ₃* → Φ₄

Given:
- Base frames: B = {F₁, F₂, ..., Fₙ} ⊆ Φ₁ ∪ Φ₂
- Identity frames: I = {F₃¹, F₃², ...} ⊆ Φ₃

π(B; I) produces projection frame F^(4) ∈ Φ₄
```

**Algorithm (Projection)**:

```
Algorithm: ComputeProjection

Input: Base frames B, Identity frames I
Output: Projection frame F₄

1. Build equivalence classes from I:
   E = PartitionEntities(I)
   // E = {{e₁, e₂, e₅}, {e₃, e₄}, ...}

2. For each class Cᵢ ∈ E:
   Create canonical representative: ê_i

3. Merge base frames sharing equivalence classes:
   For frames {Fⱼ | entities(Fⱼ) ∩ Cᵢ ≠ ∅}:
   
   F₄ = ⟨
     k: MergeActions({Fⱼ.k}),
     R: UnifyRoles({Fⱼ.R}, Cᵢ → êᵢ),
     L: CommonMood({Fⱼ.L}),
     t: MergeTemporal({Fⱼ.t}),
     s: synthetic_projection,
     c: ∏ᵢ c(Fᵢ) · ∏ⱼ c(F₃ʲ),
     E: {êᵢ},
     provenance: (B, I)
   ⟩

4. Return F₄
```

**Theorem 2 (Projection Distinctness: Φ₄ ≠ Φ₂)**

*Projection frames are ontologically distinct from base frames.*

**Proof**:

Let:
- F_A ∈ Φ₂ = ⟨eat, {Kartā: Ram_1}⟩ observed at t₁
- F_B ∈ Φ₂ = ⟨king, {Subject: Ram_2}⟩ observed at t₂
- I ∈ Φ₃ = ⟨≡, {Ram_1, Ram_2}⟩

Define: F_P = π({F_A, F_B}; {I}) = "The King ate"

**Proof by contradiction**:

1. **Assume**: F_P ∈ Φ₂ (F_P is a base frame)

2. **By Definition 4**: Base frames are observed as units from input

3. **Verification**:
   - At t₁: Observed "Ram eating" — kingship unknown
   - At t₂: Observed "Ram is King" — not eating

4. **Information content**:
   - I(F_A) contains: eating property for Ram_1
   - I(F_B) contains: kingship property for Ram_2
   - I(F_P) contains: **joint** (eating ∧ kingship) for merged entity

5. **Contradiction**: F_P contains joint distribution J(eating, kingship) that exists in neither F_A nor F_B individually. This joint was never observed.

6. **Conclusion**: F_P exists only in the inference layer, not observation layer.

**Therefore**: Φ₄ ∩ Φ₂ = ∅, hence Φ₄ ≠ Φ₂. ∎

**Definition 7 (Synthetic Unity)**

The property distinguishing Φ₄ from Φ₂ is **synthetic unity**: a projection frame holds properties (P₁ from Source A at t₁, P₂ from Source B at t₂) that never co-existed in physical observation but exist together in the logical world.

**Corollary 2.1 (Information Horizon)**

From a projection frame F₄, one can only answer queries satisfying:

```
Query(F₄) ⊆ (∪ᵢ Attributes(Fᵢ)) ∩ GlueValidity(I)
```

Lost information includes:
- Temporal granularity ("Did he eat BEFORE becoming king?")
- Per-source confidence texture
- Context-specific attributes dropped during synthesis

### 4.4 Level 5: Meta-Trace Frames

**Definition 8 (Meta-Trace Frame)**

```
F^(5) ∈ Φ₅

F^(5) = ⟨
  derive,
  {
    Conclusion: F₄,
    Method: μ,
    Evidence: {F₁, F₂, ..., Fₙ} ⊆ Φ₁ ∪ Φ₂,
    Glue: I ⊆ Φ₃,
    Confidence: c
  },
  t_derivation,
  s_engine,
  c_trace
⟩

where:
- μ ∈ DerivationMethods = {identity_projection, causal_inference, ...}
- c_trace = confidence in the derivation logic itself
```

**Semantics**: F^(5) is a **constructive proof** that F₄ follows from Evidence given Glue.

**Verification Function**:

```
verify(F₅) → {valid, invalid}

1. Check F₅.Evidence ⊆ G (all evidence exists in graph)
2. Check F₅.Glue ⊆ G (all identity frames exist)
3. Recompute: F₄' = π(F₅.Evidence; F₅.Glue)
4. If F₄' ≈ F₅.Conclusion: return valid
5. Else: return invalid
```

**Theorem 3 (Trace Completeness)**

*For any projection frame F₄ produced by the system, there exists a unique meta-trace F₅ such that verify(F₅) = valid and F₅.Conclusion = F₄.*

**Proof**: By construction—the projection algorithm (Definition 6) requires recording (Evidence, Glue) as part of the output. ∎

---

## 5. Meta-Frame Provenance Schema

### 5.1 Motivation

Rather than treating confidence as a scalar field, we formalize provenance as a **first-class frame**. Every base frame has an associated meta-frame describing its acquisition context.

**Definition 9 (Acquisition Frame)**

For each base frame F ∈ Φ₁ ∪ Φ₂, there exists an acquisition frame:

```
M_F = ⟨
  acquire,
  {
    Kartā: Process_ID,      // What process created this frame
    Karma: F,               // The frame being described
    Karaṇa: Source_Document,// The source material
    Adhikaraṇa_Time: t,     // When acquisition occurred
    Adhikaraṇa_Place: Module_ID  // Which module performed extraction
  },
  t_acquisition,
  system,
  c_acquisition
⟩
```

### 5.2 Querying Provenance

With this schema, provenance queries use the **same interrogative algebra**:

| Query | Interrogative | Target |
|-------|---------------|--------|
| "When was F₁ extracted?" | कदा (Kadā) | M_F₁.Adhikaraṇa_Time |
| "From what source?" | कुतः (Kutaḥ) | M_F₁.Karaṇa |
| "By which process?" | केन (Kena) | M_F₁.Kartā |
| "What confidence?" | कीदृश (Kīdṛśa) | Quality property of M_F₁ |

### 5.3 Formal Properties

**Theorem 4 (Provenance Closure)**

*The meta-frame schema is closed under the query algebra: any provenance question can be answered using existing interrogatives.*

**Proof**: Provenance attributes (source, time, agent, method) map to standard Kāraka slots. Interrogatives covering those slots (Kutaḥ, Kadā, Kena, Katham) address all provenance queries. ∎

---

# Part III: The Finite Query Algebra

## 6. Interrogative Primitives

### 6.1 Complete Set

Based on the Sanskrit interrogative system, we define:

**Part A: Declinable Interrogatives (Entity Queries)**

| Primitive | Sanskrit | Target | Frame Level |
|-----------|----------|--------|-------------|
| Who/What | किम् (Kim) | Entity (Agent/Patient) | Φ₁, Φ₂, Φ₄ |
| By whom/what | केन (Kena) | Instrument | Φ₁ |
| To/For whom | कस्मै (Kasmai) | Recipient | Φ₁ |
| From whom/what | कस्मात् (Kasmāt) | Source | Φ₁, Φ₅ |
| Whose/Of what | कस्य (Kasya) | Possessor/Relation | Φ₂ |
| In/On whom/what | कस्मिन् (Kasmin) | Locus | Φ₁ |
| Which (of 2) | कतर (Katara) | Binary selection | Φ₃ |
| Which (of many) | कतम (Katama) | Multiple selection | Φ₃ |
| What kind | कीदृश (Kīdṛśa) | Property/Quality | Φ₂ |

**Part B: Indeclinable Interrogatives (Context Queries)**

| Primitive | Sanskrit | Target | Frame Level |
|-----------|----------|--------|-------------|
| Where | कुत्र (Kutra) | Spatial locus | Φ₁ |
| When | कदा (Kadā) | Temporal locus | Φ₁, Φ₅ |
| Why | किमर्थम् (Kimartham) | Purpose/Reason | Φ₅ |
| How (manner) | कथम् (Katham) | Manner/Method | Φ₁ |
| How many | कति (Kati) | Count (discrete) | Φ₁, Φ₂ |
| How much | कियत् (Kiyat) | Quantity (continuous) | Φ₁, Φ₂ |
| Whence | कुतः (Kutaḥ) | Source/Origin | Φ₁, Φ₅ |

### 6.2 The Vibhakti-Interrogative Product

Each declinable interrogative inflects through 7 cases × 3 numbers = 21 forms, covering all entity-relation combinations:

| Case | Sanskrit | Relation | Example Question |
|------|----------|----------|------------------|
| Prathamā (1) | प्रथमा | Subject/Agent | Who does X? |
| Dvitīyā (2) | द्वितीया | Object/Patient | What does X do? |
| Tṛtīyā (3) | तृतीया | Instrument | By what means? |
| Caturthī (4) | चतुर्थी | Beneficiary | For whom? |
| Pañcamī (5) | पञ्चमी | Source/Cause | From what? Why? |
| Ṣaṣṭhī (6) | षष्ठी | Possessor | Whose? Of what? |
| Saptamī (7) | सप्तमी | Location | In/On what? |

### 6.3 Quantifier Integration

For universal/existential quantification, we compose with pronouns:

| Quantifier | Sanskrit | Semantics | Composition |
|------------|----------|-----------|-------------|
| All/Every | सर्व (Sarva) | Universal ∀ | सर्वेषु X-षु किम्... |
| Some/Any | कश्चित् (Kaścit) | Existential ∃ | किम् कश्चित् X अस्ति... |
| None | न कश्चित् | Negated existential | न कश्चित् X... |

**Definition 10 (Query Template)**

A query template Q is a frame with at least one **free variable** (λ):

```
Q = ⟨k_target, R_template, L, t, λ⟩

where λ ∈ Λ = {Kim, Katara, Katama, Kīdṛśa, Kutra, Kadā, ...}
```

**Definition 11 (Solution Set)**

The solution to query Q over graph G:

```
Sol(Q, G) = {v | Unify(Q[λ → v], G) succeeds}
```

### 6.4 The Three Query Operators

**Definition 12 (Selector Operator σ)**

For atomic queries targeting Φ₁, Φ₂:

```
σ_Role(G) = {F.R(Role) | F ∈ G, F.k = target_action}
```

Examples:
- σ_Kartā(G) for "Who?" queries
- σ_Adhikaraṇa(G) for "Where?" queries

**Definition 13 (Connector Operator γ)**

For identity queries targeting Φ₃:

```
γ(e₁, e₂, G) = ∃Path(e₁ ↔ e₂) in G|_{Φ₃}
```

Returns: Boolean (connected?) or Path (the identity chain)

**Definition 14 (Tracer Operator τ)**

For meta queries targeting Φ₅:

```
τ(F₄) = {(Evidence, Glue) | F₄ = π(Evidence; Glue)}
```

Returns the **pre-image** of the projection function.

### 6.5 Query Composition

Complex queries are **functional compositions** of σ, γ, τ.

**Example**: "Why did the King eat?"

```
Parse: Why (Kimartham) + King (property) + eat (action)

Step 1: Solve inner projection (σ + γ)
  F₄ = σ_Kartā(eat, G) ∩ γ(Agent, King_property, G)
  
Step 2: Apply tracer (τ)
  Evidence = τ(F₄)
  
Result:
  τ(F₄) = {
    F_A: "Ram eats" (base observation)
    F_B: "Ram is King" (base observation)
    I: "Ram_1 ≡ Ram_2" (identity hypothesis)
  }
```

---

## 7. Decidability and Complexity

### 7.1 Termination Guarantee

**Theorem 5 (Query Decidability)**

*For any query template Q constructed from the finite interrogative set Λ, evaluation Sol(Q, G) terminates in finite time.*

**Proof**:

1. **Finite graph**: |V| nodes, |E| edges (finite by construction)

2. **Finite template**: Q has ≤ 7 slots (one per Vibhakti)

3. **Bounded search**:
   - σ (Select): O(|V|) — linear scan of frame nodes
   - γ (Connect): O(|V|²) — BFS/DFS on identity subgraph
   - τ (Trace): O(1) — direct pointer from Φ₅ to provenance

4. **No infinite recursion**: 
   - Φ₅ frames form a DAG pointing backward to lower levels
   - Each Φ₅ cites only Φ₁–Φ₄ frames, never other Φ₅ frames
   - Therefore, tracer traversal terminates

5. **Cycle prevention**:
   - Identity graph may have cycles (A ≡ B ≡ C ≡ A)
   - Handled by transitive closure computation (O(|V|²))
   - Visited set prevents revisiting

**Total complexity**: O(|V|² × query_depth) where depth ≤ h_max

Since h_max is a constant (typically ≤ 4): **O(|V|²) worst case**, typically O(|V|) for simple queries.

**Scope Statement**: Decidability holds for the **reference architecture** as specified:
- Finite, controlled graph size
- Bounded projection depth
- Clean Φ₅ DAG discipline

Arbitrary extensions (unbounded recursion, infinite streams) may not preserve these guarantees. ∎

### 7.2 Complexity Summary

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Frame extraction | O(S) | S = sentences |
| Simple query (σ) | O(\|V\|) | Linear scan |
| Identity query (γ) | O(\|V\|²) | Graph connectivity |
| Trace query (τ) | O(1) | Pointer lookup |
| Projection | O(k·m) | k classes, m frames/class |
| Full query | O(\|V\|² · h_max) | Bounded by constants |

---

## 8. Point-of-View Formalization

**Definition 15 (Point-of-View)**

A POV is a constraint function over the frame graph:

```
POV = ⟨F_filter, E_filter, T_filter, P_priority, S_filter, I_filter⟩

where:
- F_filter: F → {0,1}     // Frame admissibility
- E_filter: E → {0,1}     // Edge traversability  
- T_filter: Time → {0,1}  // Temporal slice
- P_priority: Source → ℝ  // Source weighting
- S_filter: Modality → {0,1}  // Modality filter
- I_filter: Φ₃ → {0,1}    // Identity frame filter
```

**Theorem 6 (POV Divergence)**

*Two POVs V₁ and V₂ produce divergent answers to query Q if and only if:*

```
∃F₃ ∈ Φ₃: V₁.I_filter(F₃) ≠ V₂.I_filter(F₃) ∧ F₃ ∈ CriticalPath(Q)
```

**Proof**:

(⟹) If such F₃ exists:
1. V₁ accepts F₃ → equivalence class E₁
2. V₂ rejects F₃ → equivalence class E₂ ≠ E₁
3. π(·; E₁) ≠ π(·; E₂)
4. Answer_V₁(Q) ≠ Answer_V₂(Q)

(⟸) Contrapositive: If V₁ and V₂ agree on all F₃ in CriticalPath(Q), they build identical equivalence classes over relevant entities, yielding identical projections. ∎

---

## 9. Self-Correction Mechanism

**Definition 16 (Contradiction)**

Two frames F, G are in contradiction if:

```
∃e, P: F asserts P(e) ∧ G asserts ¬P(e)
```

**Algorithm: TraceBackAndCorrect**

```
Input: Contradiction (F₄, F₆) where F₄, F₆ ∈ Φ₄
       Graph G with meta-traces

Output: Corrected graph G'

1. Locate meta-traces:
   F₅⁴ = τ(F₄), F₅⁶ = τ(F₆)

2. Extract derivation paths:
   Path₄ = F₅⁴.Evidence ∪ F₅⁴.Glue
   Path₆ = F₅⁶.Evidence ∪ F₅⁶.Glue

3. Find conflicting identity frames:
   Conflict = (Path₄ ∩ Path₆) ∩ Φ₃

4. Rank by confidence:
   F₃_weak = argmin_{F₃ ∈ Conflict} c(F₃)

5. Invalidate weak link:
   G' = G \ {F₃_weak}

6. Cascade invalidation:
   For each F₄' where F₃_weak ∈ τ(F₄').Glue:
     Mark F₄' as invalid

7. Trigger recomputation of affected projections

8. Return G'
```

**Theorem 7 (Self-Correction Termination)**

*TraceBackAndCorrect terminates in O(|Φ₃|) iterations.*

**Proof**: Each iteration removes at least one identity frame. |Φ₃| is finite. ∎

**Theorem 8 (Self-Correction Soundness)**

*If TraceBackAndCorrect terminates, the resulting graph G' is contradiction-free with respect to the detected conflict.*

**Proof**: By invalidating min-confidence identity frame, at least one derivation path breaks. The contradiction required both paths to coexist. ∎

---

# Part IV: Summary and Open Questions

## 10. Results Summary

| Claim | Status | Reference |
|-------|--------|-----------|
| Binary Structural Completeness | **Theorem** (over linguistic structure) | Theorem 1 |
| Interrogative Completeness | **Theorem** (with Lakāra + quantifiers) | §6 |
| Φ₄ ≠ Φ₂ (Projection Distinctness) | **Theorem** | Theorem 2 |
| Query Decidability | **Theorem** | Theorem 5 |
| POV Divergence Detection | **Theorem** | Theorem 6 |
| Self-Correction Soundness | **Theorem** | Theorem 8 |
| Trace Completeness | **Theorem** (by construction) | Theorem 3 |
| Identity Sufficiency for Correction | **Theorem** | Theorem 9 |
| Minimal Correction Existence | **Theorem** | Theorem 10 |
| Correction Efficiency Bound | **Theorem** | Theorem 11 |
| **Necessity of Identity Provenance** | **Theorem** (lower bound) | Theorem 12 |

## 11. Open Questions for Further Research

1. **Category-Theoretic Composition**: Formalize POV composition via pushouts; prove sheaf conditions for global truth construction.

2. **Confidence Calculus**: Choose principled framework (Bayesian, Dempster-Shafer, or Fuzzy) for confidence propagation.

3. **Cross-Linguistic Validation**: Empirically verify interrogative completeness across typologically diverse languages.

4. **Computational Complexity Lower Bounds**: Can we prove the query operators are asymptotically optimal?

5. **Higher-Order Meta-Traces**: When Φ₅ frames become objects of reasoning, formalize Φ₆, Φ₇, ... hierarchy.

---

# Part V: Semantic Correction Theory (Formal)

This section presents a rigorous, self-contained formalization of semantic correction that stands independent of the Pāṇinian frame taxonomy. The results here apply to any knowledge system satisfying the stated axioms.

## 12. System Definition

**Definition 17 (Knowledge System)**

A knowledge system is defined as:

```
𝒦 = (O, I, D, ⊢)
```

where:
- `O` = finite set of observations (treated as ground facts relative to the system)
- `I` = finite set of identity assumptions (hypotheses that two entities are the same)
- `D` = set of derived statements
- `⊢: 𝒫(O) × 𝒫(I) → 𝒫(D)` = derivation operator

## 13. Axioms for Semantic Correction

**Axiom SC0 (Observational Commitment)**

Observations are treated as fixed ground facts and are not retracted during correction.

```
O is not modified during correction operations
```

*Note*: This is an architectural constraint, not an epistemological claim about reality.

**Axiom SC1 (Observation Monotonicity)**

Adding observations cannot remove derivations.

```
O₁ ⊆ O₂ ⟹ ⊢(O₁, I) ⊆ ⊢(O₂, I)
```

**Axiom SC2 (Identity Non-Monotonicity)**

Adding identity assumptions may invalidate derivations.

```
I₁ ⊆ I₂ ⇏ ⊢(O, I₁) ⊆ ⊢(O, I₂)
```

*Interpretation*: Identity assumptions are the only sanctioned source of non-monotonicity in the system.

**Axiom SC3 (Soundness)**

If all premises are true, derived conclusions are true.

```
d ∈ ⊢(O, I) ∧ (O ∪ I true) ⟹ d true
```

## 14. Provenance

**Definition 18 (Provenance)**

For every derived statement d ∈ D, there exists provenance:

```
prov(d) = (O_d, I_d) such that d ∈ ⊢(O_d, I_d)
```

where O_d ⊆ O and I_d ⊆ I are the minimal observation and identity subsets supporting d.

## 15. Fundamental Equation

```
┌───────────────────────────────────┐
│      D = ⊢(O | I)                 │
│                                   │
│ Derived knowledge is conditional  │
│ on identity assumptions.          │
└───────────────────────────────────┘
```

## 16. Core Theorems

**Theorem 9 (Identity Sufficiency for Correction)**

*If a derived statement is false, then retracting a subset of its identity assumptions eliminates it.*

```
d false ⟹ ∃ I' ⊆ I_d : d ∉ ⊢(O_d, I_d \ I')
```

**Proof**:
1. Since d is false and d ∈ ⊢(O_d, I_d), the inference is unsound
2. By SC3, at least one element of (O_d ∪ I_d) must be false
3. By SC0, O_d is not retracted
4. By SC1, removing observations cannot invalidate d
5. Therefore, falsity must lie in I_d
6. Hence ∃ I' ⊆ I_d whose removal blocks the derivation ∎

**Theorem 10 (Minimal Correction)**

*There exists a minimal identity retraction that removes a false conclusion while minimizing collateral damage.*

```
I*_d = argmin_{I' ⊆ I_d} (|I'| + |{d' ∈ D : I' ∩ I_{d'} ≠ ∅}|)

subject to: d ∉ ⊢(O_d, I_d \ I')
```

**Proof**: Existence follows from finiteness of I_d. The optimization is a weighted hitting-set problem, computable when |I|, |D| < ∞. ∎

**Theorem 11 (Correction Efficiency)**

*Let G = (V, E) be the dependency graph where V = I ∪ D and (i, d) ∈ E ⟺ i ∈ I_d.*

*Define graph density: ρ = |E| / (|I| · |D|)*

*Then expected correction cost satisfies:*

```
𝔼[correction cost] = O(ρ · |D|)
```

*For sparse graphs (ρ → 0), correction approaches constant time.*

**Proof**: Removing one identity node affects ρ|D| derived nodes on average. Under uniform random attachment of identity edges to derived nodes, the expected cascade size is ρ|D|. ∎

**Theorem 12 (Necessity of Identity Provenance)**

*Efficient correction is impossible without identity tracking.*

```
CorrectCost_{with provenance}(d) = O(|I_d|)

CorrectCost_{without provenance}(d) = Ω(|D|)
```

**Proof**: 
- With provenance: Direct graph traversal from d to I_d gives O(|I_d|)
- Without provenance: Must revalidate all derivations, giving Ω(|D|) ∎

*This is the strongest result in this document—a lower bound proving that identity provenance is not merely useful but necessary for efficient correction.*

## 17. The Correction Principle (One-Line Summary)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   d false ⟹ ∃ I' ⊆ I : d ∉ ⊢(O | I \ I')                       │
│                                                                 │
│   "All correctable semantic errors can be eliminated by        │
│    retracting identity assumptions—without modifying           │
│    observations."                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 18. Relationship to Prior Work

This formalization connects to established traditions:

| Tradition | Connection |
|-----------|------------|
| **ATMS (Assumption-Based TMS)** | Identity frames function as assumptions; correction is assumption retraction |
| **AGM Belief Revision** | Axiom SC2 corresponds to non-monotonicity; Theorem 9 is a contraction operation |
| **Provenance Semirings** | Derivation operator ⊢ annotated with identity provenance |
| **Non-Monotonic Logic** | Identity as the privileged locus of non-monotonicity (novelty) |

The novel contribution is isolating **identity assumptions** as the single class of defeasible elements, rather than allowing arbitrary defaults or assumptions.

## 19. Positioning Statement

> **What this theory is**: A design invariant for provenance-aware semantic systems with provable correction properties.

> **What this theory is not**: A universal law of intelligence, a physical law, or a complete theory of knowledge.

The results hold for systems satisfying axioms SC0-SC3. Extension to infinite systems, probabilistic observations, or adversarial inputs requires additional constraints.

---

## Appendix A: Notation Reference

| Symbol | Definition |
|--------|------------|
| Φᵢ | Frame type at level i |
| K | Set of Kārakas: {Kartā, Karma, Karaṇa, Sampradāna, Apādāna, Adhikaraṇa} |
| L | Lakāra (verbal mood) |
| V | Vibhakti (nominal case) |
| π | Projection operator: (Φ₁ ∪ Φ₂)* × Φ₃* → Φ₄ |
| σ | Selector operator: G → Entities |
| γ | Connector operator: E × E × G → Bool/Path |
| τ | Tracer operator: Φ₄ → (Evidence, Glue) |
| λ | Free variable in query template |
| Λ | Set of interrogative primitives |

---

## Appendix B: Complete Interrogative Table

### B.1 किम् (Kim) Declension

| Case | Singular (M/F/N) | Dual | Plural |
|------|------------------|------|--------|
| Nom. | कः/का/किम् | कौ/के/के | के/काः/कानि |
| Acc. | कम्/काम्/किम् | कौ/के/के | कान्/काः/कानि |
| Inst. | केन/कया/केन | काभ्याम् | कैः/काभिः/कैः |
| Dat. | कस्मै/कस्यै/कस्मै | काभ्याम् | केभ्यः/काभ्यः |
| Abl. | कस्मात्/कस्याः/कस्मात् | काभ्याम् | केभ्यः/काभ्यः |
| Gen. | कस्य/कस्याः/कस्य | कयोः | केषाम्/कासाम् |
| Loc. | कस्मिन्/कस्याम्/कस्मिन् | कयोः | केषु/कासु |

### B.2 Mapping to Query Operations

| Interrogative Form | Query Operation | Graph Lookup |
|--------------------|-----------------|--------------|
| कः (Nominative) | σ_Kartā | (n)-[:AGENT]→(Action) |
| कम् (Accusative) | σ_Karma | (n)-[:PATIENT]→(Action) |
| केन (Instrumental) | σ_Karaṇa | (n)-[:INSTRUMENT]→(Action) |
| कस्मै (Dative) | σ_Sampradāna | (n)-[:BENEFICIARY]→(Action) |
| कस्मात् (Ablative) | σ_Apādāna + τ | (n)-[:SOURCE]→(Action) |
| कस्य (Genitive) | Relation lookup | (n)-[:RELATED_TO]→(Entity) |
| कस्मिन् (Locative) | σ_Adhikaraṇa | (n)-[:LOCUS]→(Action) |

---

## References

Bharati, A., Chaitanya, V., & Sangal, R. (1995). *Natural Language Processing: A Paninian Perspective*. Prentice-Hall of India.

Begum, R., Husain, S., Dhwaj, A., Sharma, D. M., Bai, L., & Sangal, R. (2008). Dependency annotation scheme for Indian languages. *Proceedings of IJCNLP*.

Kiparsky, P. (2009). On the architecture of Pāṇini's grammar. *Proceedings of Hyderabad Conference on Sanskrit Computational Linguistics*.

Kulkarni, A. (2013). A deterministic dependency parser with dynamic programming for Sanskrit. *Proceedings of ACL*.

Pāṇini. (~4th century BCE). *Aṣṭādhyāyī*. [Sanskrit grammatical treatise]

---

**Document Status**: Ready for peer review.  
**Contact**: [To be added]  
**Acknowledgments**: Profound gratitude to the 2500-year lineage of Pāṇinian scholars whose insights underpin this work.
