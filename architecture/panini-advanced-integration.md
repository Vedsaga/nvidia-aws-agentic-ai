# Advanced Pāṇinian Integration: State-of-the-Art Enhancements

**Status:** RESEARCH PROPOSAL  
**Version:** 0.1  
**Last Updated:** 2026-01-14

This document proposes advanced integrations from Pāṇini's Aṣṭādhyāyī that could elevate the Kāraka NexusGraph to state-of-the-art status.

---

## 0. The Seven Core Concepts of Pāṇini's Coding System

*Source: Pāṇinīya Coding System by Yash Salunke*

Before diving into advanced applications, we must understand the **seven foundational concepts** that make Pāṇini's grammar computationally implementable:

### 0.1 Śiva Sūtrāṇi (Fundamental Alphabet)

The 14 Śiva Sūtras define the phonetic inventory of Sanskrit in a **compressed, computationally efficient format**:

```
अ इ उ ण्     (a i u ṇ)
ऋ ऌ क्       (ṛ ḷ k)
ए ओ ङ्       (e o ṅ)
ऐ औ च्       (ai au c)
ह य व र ट्   (h y v r ṭ)
ल ण्         (l ṇ)
ञ म ङ ण न म्  (ñ m ṅ ṇ n m)
झ भ ञ्       (jh bh ñ)
घ ढ ध ष्     (gh ḍh dh ṣ)
ज ब ग ड द श्  (j b g ḍ d ś)
ख फ छ ठ थ च ट त व् (kh ph ch ṭh th c ṭ t v)
क प य्       (k p y)
श ष स र्     (ś ṣ s r)
ह ल्         (h l)
```

**Computational Insight:** The trailing consonants (ण्, क्, ङ्, etc.) are **meta-markers** (called इत्) that enable creating character classes called **pratyāhāras**.

---

### 0.2 Pratyāhāra (Character Classes)

A **pratyāhāra** is a compressed notation for a set of sounds - like regex character classes but invented 2500 years earlier.

**Formation Rule (आदिरन्त्येन सहेता):**
> Take the first letter and the trailing इत् marker from anywhere later in the Śiva Sūtras.

**Examples:**
| Pratyāhāra | Meaning | Equivalent Regex |
|------------|---------|------------------|
| **अच्** | All vowels (अ to औ + च्) | `[aeiouāīūṛṝḷēōaiāu]` |
| **हल्** | All consonants (ह to ल्) | `[^aeiou]` (approx.) |
| **इक्** | इ, उ, ऋ, ऌ | `[iuṛḷ]` |
| **यण्** | य्, व्, र्, ल् | `[yvrl]` |

**Application to Kāraka System:**
We can define **entity-class pratyāhāras**:
```
ENTITY_CLASS: "जीव्" (living beings)
├─ includes: humans, animals, deities
├─ formation: from जीव to व्

ENTITY_CLASS: "स्थान्" (locations)
├─ includes: cities, buildings, geographical features
```

---

### 0.3 Vibhakti (Case Endings as Operators)

Pāṇini uses **vibhakti (case endings)** not for normal meanings, but as **operators** that define the role of each element in a rule:

| Vibhakti | Normal Meaning | Pāṇinian Operator Meaning |
|----------|----------------|---------------------------|
| 1st (प्रथमा) | Subject | **Replacement/result** |
| 5th (पञ्चमी) | From/source | **After this position** |
| 6th (षष्ठी) | Of/possession | **In place of this** |
| 7th (सप्तमी) | In/location | **Before this position** |

**Example Rule: इको यणचि (iko yaṇaci)**
- इकः (6th) = इक् letters (इ, उ, ऋ, ऌ) → **in place of**
- यण् (1st) = य्, व्, र्, ल् → **replacement**
- अचि (7th) = before a vowel → **context**

**Meaning:** "Replace इक् vowels with यण् consonants when followed by a vowel."

**Application to Kāraka System:**
We can use similar operator semantics:
```
RULE: कर्ता-कर्म-विलोमः (kartā-karma-vilomaḥ)
├─ कर्तुः (6th) = in place of agent
├─ कर्म (1st) = object becomes subject
├─ कर्मणि (7th) = in passive construction

Meaning: "In passive voice, the object takes subject position."
```

---

### 0.4 Paribhāṣā Sūtrāṇi (Meta-Rules)

Meta-rules govern **how other rules apply** - like compiler directives:

| Meta-Rule | Meaning | Application |
|-----------|---------|-------------|
| **षष्ठी स्थानेयोगा** | 6th case = position of change | Rule ordering |
| **तस्मिन्निति निर्दिष्टे पूर्वस्य** | 7th case = change happens before | Context specification |
| **स्थानेऽन्तरतमः** | Closest substitute wins | Selectional preference |
| **विप्रतिषेधे परं कार्यम्** | Later rule wins in conflict | Conflict resolution |

**Application to Kāraka System:**
```
META_RULE: स्थानेऽन्तरतमः (sthāne'ntaratamaḥ)
├─ meaning: Among multiple possible role assignments, choose closest semantic match
├─ application: When both Kartā and Karaṇa could apply, prefer based on animacy
```

---

### 0.5 Anuvṛtti (Inheritance/Carry Forward)

**Anuvṛtti** means that elements from a previous rule **carry forward** to subsequent rules unless explicitly blocked.

**Example:**
```
Rule 1: संहितायाम् (saṃhitāyām) - "In the context of saṃhitā"
Rule 2: इको यणचि (iko yaṇaci) - (inherits संहितायाम्)
Rule 3: एचोऽयवायावः (eco'yavāyāvaḥ) - (inherits संहितायाम्)
```

Rules 2 and 3 don't repeat संहितायाम् because it's **inherited**.

**Application to Kāraka System:**
```
ADHIKĀRA: क्रियायाम् (kriyāyām) - "In the context of action"
├─ All kāraka rules inherit this context
├─ No need to repeat "for action events" in each rule

ADHIKĀRA_END: अनुवृत्ति-निवृत्तिः
├─ Explicitly ends the inheritance
```

---

### 0.6 Pūrvatrāsiddham (Rule of Non-Existence)

Pāṇini's algorithm is split into **two parts** with a visibility barrier:
- Part 1 rules **cannot see** the output of Part 2 rules
- Earlier Part 2 rules **cannot see** later Part 2 outputs

**Why This Matters:**
It prevents circular rule application and infinite loops - essential for any rule-based system.

**Application to Kāraka System:**
```
PHASE 1: Entity/Kriyā Extraction
├─ Cannot see outputs of Phase 2/3

PHASE 2: Kāraka Assignment
├─ Cannot see outputs of Phase 3
├─ Cannot re-trigger Phase 1

PHASE 3: Causal Linking
├─ Has read-only access to Phase 1/2 outputs
```

---

### 0.7 Ānupūrvī (Letter-Level Decomposition)

Every word is decomposed into **atomic letters** before rules apply:

```
कृष्णः = क् + ऋ + ष् + ण् + अः

रामः = र् + आ + म् + अः
```

**Why This Matters:**
- Rules apply at the **atomic level**, not word level
- Enables precise pattern matching
- Similar to tokenization in NLP

**Application to Kāraka System:**
```
Sentence decomposition:
"Ram ate mango" → [Ram][ate][mango]
                → [ENTITY:Ram][KRIYĀ:EAT][ENTITY:mango]
                → Atomic semantic units for rule application
```

---

## 1. Śābdabodha: The Four Conditions of Valid Meaning

> **Śābdabodha** (शाब्दबोध) = "verbal comprehension" — the formal theory of how words combine to produce sentence meaning.

The Sanskrit philosophical tradition (particularly Nyāya school) identified **four essential conditions** for a string of words to produce unified meaning:

### The Four Conditions (Vākyārtha-Pratyaya-Hetavaḥ)

| Sanskrit | Transliteration | Meaning | Application |
|----------|-----------------|---------|-------------|
| **आकाङ्क्षा** | Ākāṅkṣā | Mutual Expectancy | Words must syntactically "expect" each other |
| **योग्यता** | Yogyatā | Semantic Compatibility | Word meanings must not contradict |
| **सन्निधि** | Sannidhi | Contiguity | Words must be proximate (not scattered) |
| **तात्पर्य** | Tātparya | Speaker's Intent | Context determines intended meaning |

### Proposed Axiom 40: Ākāṅkṣā (Mutual Expectancy)

> **For a sentence to be valid, every kāraka role must be "expected" by the kriyā, and every entity must be "expected" by at least one kriyā.**

**Implementation:**

Each dhātu (verb root) has an **expectancy frame**:

```
DHĀTU: खाद् (khād - to eat)
├─ expects: Kartā (REQUIRED - someone eats)
├─ expects: Karma (REQUIRED - something is eaten)
├─ expects: Karaṇa (OPTIONAL - instrument)
├─ expects: Adhikaraṇa (OPTIONAL - location)

DHĀTU: दा (dā - to give)
├─ expects: Kartā (REQUIRED - giver)
├─ expects: Karma (REQUIRED - thing given)
├─ expects: Sampradāna (REQUIRED - recipient)
```

**Validation Rule:**
```sql
-- Every REQUIRED expectancy must be filled
ASSERT NOT EXISTS (
  SELECT 1 FROM events e
  JOIN dhatu_frames df ON e.dhatu = df.dhatu_id
  WHERE df.role_required = TRUE
    AND NOT EXISTS (
      SELECT 1 FROM karaka_links k
      WHERE k.event_id = e.event_id AND k.role = df.role
    )
)
```

**Why This Matters:**
- Current system allows events with missing required participants
- Ākāṅkṣā makes extraction *self-checking* - if a required role is missing, the extraction is incomplete

---

### Proposed Axiom 41: Yogyatā (Semantic Compatibility)

> **The fillers of kāraka roles must be semantically compatible with the verb and role.**

**Implementation:**

Define **selectional restrictions** per dhātu:

```
DHĀTU: खाद् (khād - to eat)
├─ Kartā: must be [+animate]
├─ Karma: must be [+edible] OR [+metaphorically_consumable]

DHĀTU: विद् (vid - to know)
├─ Kartā: must be [+sentient]
├─ Karma: must be [+knowable] (proposition, fact, entity)
```

**Violation Detection:**
```
"The stone ate the mango."

EVENT:EAT
├─ Kartā: stone
├─ yogyatā_violation: TRUE
├─ violation_type: selectional_restriction
├─ constraint: Kartā requires [+animate]
├─ filler_features: [-animate]
```

**Why This Matters:**
- Detects metaphor (intentional yogyatā violation)
- Detects extraction errors (unintentional violation)
- Enables common-sense reasoning ("stones don't eat")

---

### Proposed Axiom 42: Sannidhi (Contiguity)

> **Words that form a semantic unit must be expressed in proximity. Long-distance dependencies are marked.**

**Implementation:**

Track **discourse distance** between related elements:

```
"Ram, whom I saw yesterday and who was wearing blue, ate."

EVENT:EAT
├─ Kartā: Ram
├─ sannidhi_distance: 12 words (between "Ram" and "ate")
├─ interpolated_elements: [relative_clause_1, relative_clause_2]
├─ sannidhi_strain: high
```

**Why This Matters:**
- Long sannidhi distances increase parsing ambiguity
- Can trigger re-verification of distant linkages
- Important for document-level coreference

---

### Proposed Axiom 43: Tātparya (Contextual Intent)

> **The same sentence can have different meanings based on context. Tātparya captures the intended interpretation.**

**Implementation:**

```
"Bring the bat." (tātparya determines: cricket bat vs. animal)

SENTENCE: "Bring the bat"
├─ possible_interpretations:
│   ├─ INT_1: EVENT:BRING(Karma: cricket_bat)
│   └─ INT_2: EVENT:BRING(Karma: animal_bat)
├─ tātparya_signal: context_from_document
├─ selected_interpretation: INT_1 (if cricket context)
├─ confidence: 0.95
```

---

## 2. Lakāra System: 10-Way Tense-Aspect-Mood

Pāṇini encodes **10 Lakāras** (लकार) - verbal affixes that capture nuanced combinations of tense, aspect, and mood. This is far richer than our current 5-value modality system.

### The 10 Lakāras

| # | Lakāra | Sanskrit Name | Function | Example (√पठ् - to read) |
|---|--------|---------------|----------|--------------------------|
| 1 | **लट्** | laṭ | Present (actual ongoing) | पठति (he reads) |
| 2 | **लिट्** | liṭ | Past (witnessed/perfect) | पपाठ (he has read) |
| 3 | **लुट्** | luṭ | Future (general) | पठिता (he will read) |
| 4 | **लृट्** | lṛṭ | Future (proximate) | पठिष्यति (he is about to read) |
| 5 | **लेट्** | leṭ | Vedic subjunctive (rare) | (archaic) |
| 6 | **लोट्** | loṭ | Imperative (command) | पठतु (let him read!) |
| 7 | **लङ्** | laṅ | Past imperfect (narrative) | अपठत् (he was reading) |
| 8 | **लिङ्** | liṅ | Optative/potential | पठेत् (he should/would read) |
| 9 | **लुङ्** | luṅ | Aorist (simple past) | अपाठीत् (he read [once]) |
| 10 | **लृङ्** | lṛṅ | Conditional | अपठिष्यत् (he would have read) |

### Proposed Axiom 44: Lakāra-Based Temporal-Modal Encoding

> **Every event carries a lakāra classification that encodes tense, aspect, and mood in a single integrated value.**

**Enhanced Event Structure:**
```
EVENT:READ
├─ Kartā: Ram
├─ Karma: book
├─ lakāra: liṅ (optative)
├─ temporal_aspect:
│   ├─ tense: non-past
│   ├─ aspect: imperfective
│   └─ mood: potential/desiderative
├─ english_equivalent: "Ram should read the book" / "Ram would read the book"
```

**Lakāra → Modality Mapping (for English sources):**
```
"Ram reads" → laṭ (present actual)
"Ram read" → luṅ (aorist) or laṅ (imperfect) - context disambiguates
"Ram has read" → liṭ (perfect)
"Ram will read" → lṛṭ (future proximate) or luṭ (future general)
"Ram should read" → liṅ (optative)
"Ram might read" → liṅ (potential)
"Ram would have read" → lṛṅ (conditional)
"Read!" → loṭ (imperative)
```

---

## 3. Upasarga: Verbal Prefixes That Transform Meaning

Pāṇini identifies **22 upasargas** (उपसर्ग) - prefixes that attach to verb roots to systematically modify their meaning.

### The 22 Upasargas

| Upasarga | Meaning Modification | Example |
|----------|---------------------|---------|
| **प्र** (pra) | Forward, intensification | गम् (go) → प्रगम् (proceed, advance) |
| **परा** (parā) | Away, reversed | जय् (conquer) → पराजय् (defeat) |
| **अप** (apa) | Away, removal | नी (lead) → अपनी (lead away) |
| **सम्** (sam) | Together, completely | गम् (go) → संगम् (confluence, meet) |
| **अनु** (anu) | After, following | गम् (go) → अनुगम् (follow) |
| **अव** (ava) | Down, inferior | तर् (cross) → अवतर् (descend) |
| **निस्** (nis) | Out, completely | गम् (go) → निर्गम् (exit) |
| **निर्** (nir) | Without, out | णी (lead) → निर्णी (lead out, decide) |
| **दुस्** (dus) | Bad, difficult | कृ (do) → दुष्कृ (do badly) |
| **सु** (su) | Good, well | कृ (do) → सुकृ (do well) |
| **वि** (vi) | Apart, special | ज्ञा (know) → विज्ञा (discern, science) |
| **आ** (ā) | Towards, until | गम् (go) → आगम् (come) |
| **नि** (ni) | Down, into | पत् (fall) → निपत् (fall into) |
| **अधि** (adhi) | Over, upon | गम् (go) → अधिगम् (attain, learn) |
| **अपि** (api) | Also, even | (modifying particle) |
| **अति** (ati) | Beyond, excessive | गम् (go) → अतिगम् (transgress) |
| **सु** (su) | Well, good | (intensifier) |
| **उत्** (ut) | Up, upward | गम् (go) → उद्गम् (rise, originate) |
| **अभि** (abhi) | Towards (intensely) | गम् (go) → अभिगम् (approach) |
| **प्रति** (prati) | Against, back | गम् (go) → प्रतिगम् (return) |
| **परि** (pari) | Around, fully | गम् (go) → परिगम् (go around) |
| **उप** (upa) | Near, subsidiary | गम् (go) → उपगम् (approach) |

### Proposed Axiom 45: Upasarga-Aware Dhātu Normalization

> **When normalizing verbs to dhātus, preserve upasarga information as a semantic modifier.**

```
English: "Ram descended from the mountain."

Dhātu Analysis:
├─ surface_verb: descended
├─ root_dhātu: तर् (tṛ - to cross)
├─ upasarga: अव (ava - downward)
├─ composite: अवतर् (avatṛ - to descend)

EVENT:DESCEND
├─ Kartā: Ram
├─ Apādāna: mountain
├─ dhātu: तर्
├─ upasarga: अव
├─ semantic_modification: direction=downward
```

**Why This Matters:**
- "Go" vs "come" vs "return" vs "exit" are all modifications of गम् (gam - to go)
- Upasarga systematizes these relationships
- Enables reasoning: "If Ram went (गम्) somewhere and then returned (प्रतिगम्), he performed inverse motion"

---

## 4. Samāsa: Compound Word Decomposition

Sanskrit compounds encode complex semantic relationships in single words. Pāṇini classifies **4 major samāsa types**:

### Samāsa Types

| Type | Relationship | Example | Meaning |
|------|-------------|---------|---------|
| **Tatpuruṣa** | Determiner-determined | राज-पुरुषः | King's man (genitive) |
| **Karmadhāraya** | Appositional | नील-उत्पलम् | Blue lotus |
| **Dvandva** | Coordinative | राम-लक्ष्मणौ | Ram and Lakshman |
| **Bahuvrīhi** | Possessive/exocentric | पीत-अम्बरः | He whose garment is yellow (Vishnu) |

### Proposed Axiom 46: Samāsa-Aware Entity Analysis

> **Compound entities are decomposed and their internal semantic structure is preserved.**

```
Entity: "blue-eyed man"

ENTITY_COMPOUND
├─ surface_form: "blue-eyed man"
├─ samāsa_type: bahuvrīhi (possessive)
├─ head: man
├─ modifier_chain:
│   ├─ property: eye_color
│   └─ value: blue
├─ decomposed_meaning: "man who possesses blue eyes"
```

---

## 5. Paribhāṣā: Meta-Rules and Rule Ordering

Pāṇini's genius includes **meta-rules** (paribhāṣā) that govern how rules apply:

### Key Paribhāṣās

| Sūtra | Principle | Application |
|-------|-----------|-------------|
| **विप्रतिषेधे परं कार्यम्** | "In case of conflict, later rule wins" | Rule ordering precedence |
| **पूर्वपरनित्यान्तरङ्गापवादानाम्** | Priority hierarchy | Specificity beats generality |
| **अर्थवद्ग्रहणे नानर्थकस्य** | "A meaningful element implies its meaning" | Completeness condition |

### Proposed Axiom 47: Pāṇinian Rule Ordering

> **When multiple extraction rules apply, use Pāṇinian precedence: antaraṅga (more internal) > bahiraṅga (more external); apavāda (exception) > utsarga (general).**

```
Conflict: Two interpretations possible

INTERPRETATION_A (general rule):
├─ Kartā: Ram
├─ Karma: book

INTERPRETATION_B (specific exception):
├─ Kartā: Ram
├─ Karma: book
├─ Karaṇa: pen (implicit from context)

Per paribhāṣā: Interpretation B wins (apavāda overrides utsarga)
```

---

## 6. Padārtha Correspondence: Word-Thing Mapping

Classical Sanskrit philosophy developed sophisticated theories of **padārtha** (पदार्थ) - the correspondence between words and their referents.

### Proposed Axiom 48: Lakṣaṇā (Secondary Meaning)

> **When literal meaning violates yogyatā (compatibility), apply lakṣaṇā (metaphorical interpretation).**

**Types of Lakṣaṇā:**

| Type | Condition | Example |
|------|-----------|---------|
| **Jahallakṣaṇā** | Abandon literal, take figurative | "Village on the Ganges" → village on bank |
| **Ajahallakṣaṇā** | Retain literal + add figurative | "The White House said" → officials + building |
| **Jahadajahallakṣaṇā** | Partial retention | "He's a lion" → brave (like lion) |

```
"He devoured the book."

LITERAL: EVENT:EAT(Kartā: he, Karma: book)
├─ yogyatā_check: FAILED (books not edible)
├─ lakṣaṇā_applied: TRUE
├─ lakṣaṇā_type: jahadajahallakṣaṇā
├─ interpreted_as: EVENT:READ_INTENSELY(Kartā: he, Karma: book)
```

---

## 7. Sphoṭa Theory: Word-Meaning Unity

The **sphoṭa** (स्फोट) theory proposes that words and their meanings are unified wholes, not composed of parts.

### Proposed Application: Event Holism

> **Events are semantic wholes (sphoṭa), not just collections of kārakas. The kriyā-kāraka structure is an *analysis*, not the underlying reality.**

This suggests:
- Query understanding should start from holistic event recognition
- Kāraka decomposition is for *analysis*, not *storage*
- Two events with identical kārakas but different sphoṭa are different events

---

## 8. Integration Proposal: Pāṇinian Semantic Stack

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 5: TĀTPARYA (Contextual Intent Resolution)           │
│  - Disambiguates based on document/discourse context        │
└─────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4: YOGYATĀ (Semantic Compatibility Checking)         │
│  - Validates selectional restrictions                       │
│  - Detects metaphor (lakṣaṇā trigger)                       │
└─────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: ĀKĀṄKṢĀ (Expectancy Frame Matching)               │
│  - Validates required kārakas present                       │
│  - Checks dhātu-kāraka compatibility                        │
└─────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: LAKĀRA+UPASARGA (Verbal Semantics)                │
│  - 10-way tense-aspect-mood encoding                        │
│  - Prefix-based meaning modification                        │
└─────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: KĀRAKA EXTRACTION (Current System)                │
│  - Dhātu identification                                     │
│  - 8 kāraka role assignment                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Implementation Roadmap

### Phase 1: Ākāṅkṣā Integration (2-4 weeks)
- Build dhātu expectancy frames for top 100 verbs
- Add validation rules for required kārakas
- Flag extraction gaps

### Phase 2: Yogyatā Integration (2-4 weeks)
- Build selectional restriction database
- Implement yogyatā violation detection
- Add metaphor flagging (lakṣaṇā trigger)

### Phase 3: Lakāra System (4-6 weeks)
- Replace 5-value modality with 10-lakāra encoding
- Build English-to-lakāra mapping rules
- Integrate with existing temporal reasoning

### Phase 4: Upasarga Awareness (2-3 weeks)
- Build upasarga-dhātu combination rules
- Preserve semantic modification in normalization
- Enable inverse-action reasoning

### Phase 5: Tātparya Layer (4-8 weeks)
- Integrate discourse context into interpretation
- Build ambiguity resolution framework
- Connect to document temporal framing

---

## 10. Competitive Advantage

By integrating these Pāṇinian principles, the Kāraka NexusGraph would offer:

| Feature | Current NLP State-of-Art | Pāṇinian Enhancement |
|---------|-------------------------|---------------------|
| **Semantic Roles** | FrameNet, PropBank (English-centric) | Kāraka (language-universal, 2500 years refined) |
| **Tense-Aspect-Mood** | 3-5 simple categories | 10 lakāras with fine distinctions |
| **Metaphor Detection** | Statistical heuristics | Principled yogyatā + lakṣaṇā |
| **Verb Meaning** | Discrete verb senses | Compositional (dhātu + upasarga) |
| **Validation** | Post-hoc | Built-in (ākāṅkṣā frames) |
| **Philosophical Grounding** | Ad hoc | 2500 years of formal analysis |

---

## 11. Research References

- Pāṇini's Aṣṭādhyāyī (सूत्र 1.4.23-1.4.55 on kāraka)
- Bhartrhari's Vākyapadīya (on sphoṭa and sentence meaning)
- Nyāya-sūtra (on śābdabodha conditions)
- Mīmāṃsā-sūtra (on verbal testimony and interpretation)
- Modern: Kiparsky, P. - "On the Architecture of Pāṇini's Grammar"
- Modern: Kulkarni, A. - "Computational Aspects of Sanskrit Grammar"

---

*This document proposes a research agenda for integrating advanced Pāṇinian concepts into the Kāraka NexusGraph system.*
