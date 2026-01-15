# POC Robustness Improvements

## Deep Dive Analysis

After reading all files in `architecture/` and `prompts/`, here's a comprehensive analysis of gaps and improvements.

---

## Architecture Insights (from architecture/ dir)

### 1. **39 Kāraka Axioms** (karaka-axioms.md)
The system has a complete axiomatic foundation:
- **Axiom 1**: Event Primacy (Dhātu Principle) - All meaning is event-mediated
- **Axiom 2**: Dual-Layer Architecture - Ground Truth (events) + Views (projections)  
- **Axiom 3**: States use non-kāraka roles (Holder, Property)
- **Axiom 4**: The 8 Kārakas exhaust event participation
- **Axiom 18**: LLM outputs must pass validation (entity grounding)

**POC Gap**: We don't validate LLM output or check entity grounding.

### 2. **Three-Layer Pāṇinian Governance** (axiom-layer-mapping.md)
```
Layer 3: META-GOVERNANCE (7 axioms) - Rules about rules
    ↓ governs
Layer 2: OPERATIONAL (24 axioms) - Domain rules with scope
    ↓ uses
Layer 1: FOUNDATION (8 axioms) - Immutable primitives
```

### 3. **GSSR Pipeline** (kg-processing-flow.md)
Production uses Generate-Score-Select-Retry:
```
Phase: Entity/Kriya/Karaka
├── Generate 3 variations
│   ├── V1 → Fidelity Check
│   ├── V2 → Fidelity Check  
│   └── V3 → Fidelity Check
├── Consensus Check → If all match, skip scorer
├── Scorer (if no consensus)
│   ├── temp=0 → Score (1-100)
│   ├── temp=0.6 → Score (1-100)
│   └── Average < 70? → Regenerate
└── Selection → Pick best variation
```

**POC Gap**: Single-pass extraction with no GSSR.

### 4. **Multi-Phase Pipeline** (prompts/)
Production breaks extraction into 3 phases:
```
D1: Entity Extraction
    → Who/what entities exist in this sentence?
    → Output: [{text: "Dr. Chen", type: "PERSON"}, ...]
         ↓
D2a: Kriyā Extraction  
    → What verbs? Active/passive voice?
    → Output: [{canonical_form: "fund", prayoga: "passive"}, ...]
         ↓
D2b: Kāraka Binding
    → Which entity plays which role in which event?
    → Uses entities from D1 + kriyās from D2a
    → FIDELITY RULE: Every entity must exist in D1 list
```

**POC Gap**: We try to do everything in one call → fragile.

### 5. **Fidelity Validation** (sentence-split-flow.md)
Every extraction is validated against source:
- >95% character coverage
- Extracted entities must exist verbatim
- No hallucination allowed

**POC Gap**: No fidelity checking at all.

### 6. **Queue-Based LLM** (llm-call-flow.md)
- Single worker prevents rate limit issues
- Retry with exponential backoff
- Token counting before submission
- Error classification (rate limit, timeout, parse error)

**POC Gap**: Direct synchronous calls, no retry.

---

## Production Prompts Analysis (from prompts/ dir)

### D1_entity_extraction.txt
Key patterns:
- `<reasoning>` block BEFORE `<json>` block
- "IMPORTANT: Take your time. Quality > Speed."
- Explicit entity boundary rules
- EXACT text preservation

### D2a_kriya_extraction.txt
Key patterns:
- Voice detection CHECKLIST
- "When unsure: Ask 'Who/what is DOING the action vs RECEIVING it?'"
- Tricky cases section

### D2b_event_karaka_extraction.txt  
Key patterns:
- LOCUS DECISION TREE (critical for disambiguation)
- "PASSIVE VOICE WITHOUT AGENT - THIS IS VALID"
- Every entity must match D1 input list

### Key Prompt Design Patterns:
1. **Reasoning blocks**: Force chain-of-thought
2. **Decision trees**: For disambiguation
3. **Checklists**: For common patterns (voice detection)
4. **Negative examples**: Show what NOT to do
5. **Exact-match requirements**: Prevent hallucination

---

## Issues in Current POC

### 1. **Extraction Failures (100% failure rate)**
- Single-prompt extraction is fragile
- Free models don't follow strict JSON output  
- No reasoning/chain-of-thought prompting
- Missing fidelity validation

### 2. **Sentence Splitting Issues**
- "Dr. Chen" was split incorrectly - "Dr." became its own sentence
- Need abbreviation handling from production prompt

### 3. **Q&A Brittleness**
- Original: Tries to match exact `kriya` verb from question
- If parsing fails due to rate limit, no answer returned

### 4. **Rate Limits**
- Free tier = 50 requests/day
- No caching, retry logic, or graceful degradation

---

## Implemented Fixes

### ✅ 1. Demo Mode (Bypass Live Extraction)
- Created `demo_frames.json` with 4 correctly extracted frames
- Server auto-loads on startup
- "Load Demo" button in UI
- **Completely bypasses API calls** for investor demo

### ✅ 2. Context-Aware Q&A (More Robust)
- Rewrote `qa_engine.py` to pass **ALL frames** to LLM
- LLM has full context and can semantically match
- **Fallback keyword matching** when LLM is rate-limited

### ✅ 3. Better Extraction Prompt
Updated `frame_extractor.py` with patterns from D2a/D2b:
- `<reasoning>` block before `<json>` block
- Voice Detection Checklist
- Locus Decision Tree
- "Passive voice without agent is valid"
- Explicit "prayoga" field for voice

### ✅ 4. Better Logging
- LLM client logs model being called
- Shows raw response for debugging
- Frame extractor shows detailed error traces

---

## Future Improvements (Post-Demo)

### Phase 1: Add Fidelity Validation
```python
def validate_frame(frame, source_sentence):
    """Ensure extracted values exist in source text."""
    for role in [frame.karta, frame.karma, ...]:
        if role and role.lower() not in source_sentence.lower():
            return False, f"'{role}' not found in source"
    return True, None
```

### Phase 2: Two-Stage Extraction (D2a → D2b)
Instead of one call, split into:
1. **D2a (Kriyā extraction)**: Just get verbs + voice
2. **D2b (Kāraka binding)**: Given verbs, extract roles

### Phase 3: Entity Pre-Extraction (D1)
Add D1 phase before D2a:
1. **D1**: Extract entities first
2. **D2a**: Extract verbs
3. **D2b**: Bind entities to events (MUST use D1 entities)

### Phase 4: GSSR Implementation (for production)
- Generate 3 variations
- Fidelity check each
- Consensus detection
- Scorer for tie-breaking

### Phase 5: Production LLM System
- Queue-based async processing
- Retry with exponential backoff
- Multiple model fallback
- Rate limit handling

---

## Demo Strategy

### For Investor Demo with Rate Limits:
1. ✅ Pre-extract frames using a paid API (once) → `demo_frames.json`
2. ✅ Load on startup → skip live extraction
3. ✅ Q&A uses pre-extracted frames → still demonstrates concept
4. ✅ Fallback keyword matching → works even without LLM

### Demo Flow:
1. Open http://localhost:8000
2. Click "Load Demo" → Instantly shows 4 frames + graph
3. Ask questions:
   - "Who funded the study?" → The European Research Council
   - "Where was the study conducted?" → Copenhagen
   - "What did Dr. Chen lead?" → the research
   - "Who published the results?" → The team

---

## Files Changed

| File | Change |
|------|--------|
| `demo_frames.json` | NEW: Pre-extracted demo frames |
| `server.py` | Added demo mode loading + load_demo WebSocket command |
| `qa_engine.py` | Context-aware Q&A with fallback keyword matching |
| `llm_client.py` | Better logging for debugging |
| `frame_extractor.py` | Better extraction prompt with reasoning blocks |
| `static/index.html` | Added "Load Demo" button |

---

## Comparison: POC vs Production

| Aspect | POC | Production |
|--------|-----|------------|
| Extraction phases | 1 (all-in-one) | 3 (D1 → D2a → D2b) |
| Variations | 1 | 3 (GSSR) |
| Fidelity check | ❌ | ✅ |
| Scorer | ❌ | ✅ (temp=0 + temp=0.6) |
| Entity grounding | ❌ | ✅ (must match D1) |
| LLM queue | Direct calls | Queue-based worker |
| Retry logic | ❌ | ✅ (exponential backoff) |
| Rate limit handling | ❌ (crashes) | ✅ (graceful) |

---

## Key Pāṇinian Concepts for Future

From `panini-advanced-integration.md`:

1. **Ākāṅkṣā** (Mutual Expectancy): Each dhātu has required kārakas
2. **Yogyatā** (Semantic Compatibility): Kartā of "eat" must be animate
3. **Lakāra** (10-way tense-aspect-mood): More nuanced than 5-value modality
4. **Upasarga** (Verb prefixes): "go" vs "come" vs "return" are all गम् variants

---

## Summary

The POC is now **demo-ready** with:
- Pre-loaded frames (no API calls needed)
- Context-aware Q&A with fallback
- Better extraction prompts

For production, we need:
- Multi-phase extraction (D1 → D2a → D2b)
- GSSR methodology
- Fidelity validation
- Queue-based LLM with retry
