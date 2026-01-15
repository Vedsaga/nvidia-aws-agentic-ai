# Pāṇinian Interrogative → Kāraka Mapping

This document maps Sanskrit interrogative pronouns (from Vibhakti/case system) to Kāraka roles, 
providing the theoretical foundation for question-answering in the Kāraka Frame Graph system.

## The Core Insight

In Sanskrit grammar, every interrogative word is formed by combining:
1. An interrogative stem (क- / kim- "what/who")
2. A case ending (Vibhakti) that determines the semantic role

This means **every possible question type systematically maps to a Kāraka role**.

## Vibhakti → Kāraka → English Mapping

| # | Vibhakti (Case) | Sanskrit Example | Kāraka Role | English Interrogative | Example Question |
|---|-----------------|------------------|-------------|----------------------|------------------|
| 1 | **प्रथमा** (Nominative) | कः / का / किम् | **Kartā** (Agent) | Who? What? | "Who funded the study?" |
| 2 | **द्वितीया** (Accusative) | कम् / काम् / किम् | **Karma** (Object) | Whom? What? (as object) | "What did they fund?" |
| 3 | **तृतीया** (Instrumental) | केन / कया | **Karaṇa** (Instrument) | By whom? By what? With what? How? | "By what means was it done?" |
| 4 | **चतुर्थी** (Dative) | कस्मै / कस्यै | **Sampradāna** (Recipient) | To whom? For whom? For what purpose? | "To whom was it given?" |
| 5 | **पञ्चमी** (Ablative) | कस्मात् / कस्याः | **Apādāna** (Source) | From whom? From where? | "From where did it originate?" |
| 6 | **षष्ठी** (Genitive) | कस्य / कस्याः | *(Possession relation)* | Whose? Of what? | "Whose study was it?" |
| 7 | **सप्तमी** (Locative) | कस्मिन् / कस्याम् | **Adhikaraṇa** (Locus) | In/On whom? Where? When? About what? | "Where was it conducted?" |

## English Interrogatives → Kāraka

| English Word | Primary Kāraka | Notes |
|-------------|----------------|-------|
| **Who** | Kartā | When asking about doer/agent |
| **Whom** | Karma or Sampradāna | Object of action or recipient |
| **What** (subject) | Kartā | Inanimate agent |
| **What** (object) | Karma | What was acted upon |
| **Where** | Locus_Space | Spatial location |
| **When** | Locus_Time | Temporal location |
| **How** | Karaṇa | Instrument/means |
| **Why** | Prayojana (causal) | Purpose/reason (not a Kāraka) |
| **From where** | Apādāna | Source/origin |
| **To whom** | Sampradāna | Recipient/beneficiary |
| **About what** | Locus_Topic | Subject matter |

## Special Cases

### Passive Voice Questions
- "Who was X done by?" → Still looking for Kartā (agent in "by" phrase)
- "What was done?" → Looking for Karma (the thing acted upon)

### Causal Questions (Beyond Kārakas)
| Question | Relation Type |
|----------|---------------|
| "Why did X happen?" | Prayojana (purpose) - if intentional |
| "What caused X?" | Kāraṇa (efficient cause) - if mechanical |
| "What is the reason for X?" | Hetu (justification) - if explanatory |

## Implementation for Q&A

When a user asks a question:
1. Parse the interrogative word (who/what/where/when/how/why)
2. Map it to the corresponding Kāraka role
3. Search frames for that role
4. Return the value of that role from matching frame(s)

### Example Workflow

**Question**: "Who funded the study?"

1. **Parse**: Interrogative = "Who" → Kartā
2. **Extract constraint**: "funded" → Kriyā = "fund", "study" → Karma
3. **Query**: Find frame where Kriyā="fund" AND Karma contains "study"
4. **Return**: Kartā of that frame
5. **Answer**: "The European Research Council funded the study."

**Question**: "Where was it conducted?"

1. **Parse**: Interrogative = "Where" → Locus_Space
2. **Extract constraint**: "conducted" → Kriyā = "conduct"
3. **Query**: Find frame where Kriyā="conduct"
4. **Return**: Locus_Space of that frame
5. **Answer**: "It was conducted in Copenhagen."

## This is the Key Insight

Traditional NLP treats question-answering as:
- keyword matching
- vector similarity
- span extraction from text

Pāṇinian Q&A treats it as:
- Systematic mapping from interrogative to semantic role
- Structured traversal of event frames
- Deterministic answer retrieval from the correct role

**The 2500-year-old system has already solved the question taxonomy problem.**
