# Codebase Alignment Check

**Date:** Current review
**Comparing:** Actual codebase vs `tasks.md` + `GSSR-IMPLEMENTATION-PLAN.md`

---

## ✅ COMPLETED ITEMS

### 1. LLM Gateway (l7_llm_call) - DONE ✅
- [x] Temperature parameter accepted from caller (default 0.6)
- [x] Enhanced LLMCallLog with metadata:
  - pipeline_stage, attempt_number, generation_index
  - temperature, raw_request, raw_response
  - extracted_json, extracted_reasoning
- **Status:** Fully implemented

### 2. Shared Utilities - DONE ✅
- [x] `json_schemas.py` - D1, D2a, D2b schemas defined
- [x] `fidelity_validator.py` - All 3 validators (D1, D2a, D2b)
- [x] `gssr_utils.py` - Consensus check, JSON parsing, scorer parsing
- **Status:** Fully implemented

### 3. Scorer Lambda (l24) - DONE ✅
- [x] Created at `src/lambda_src/kg_agents/l24_score_extractions/`
- [x] Loads scorer.txt prompt
- [x] Calls LLM with 3 JSONs
- [x] Parses scores from response
- **Status:** Fully implemented

### 4. Entity Extraction (l9) - DONE ✅
- [x] Full GSSR flow implemented:
  - Phase 1: Generate 3 JSONs (temp=0.6)
  - Phase 2: Fidelity check with correction loop
  - Phase 2a: Consensus check
  - Phase 3: Scoring Pass 1 (temp=0.0)
  - Phase 4: Scoring Pass 2 (temp=0.3)
  - Phase 5: Select best
- [x] Retry logic with attempts tracking
- [x] Scorer feedback integration
- [x] Updates Sentences table with d1_attempts
- **Status:** Fully implemented

---

## ⚠️ GAPS & ISSUES FOUND

### 1. Database Schema - PARTIALLY MISSING ⚠️

**Sentences Table:**
```python
# Current CDK definition (serverless_stack.py lines 69-88):
- partition_key: sentence_hash ✅
- GSI: ByJobId ✅

# Missing fields in schema definition:
❌ original_sentence (String)
❌ document_ids (List)
❌ status (String) - Enum values
❌ best_score (Number)
❌ failure_reason (String)
❌ needs_review (Boolean)
❌ d1_attempts (Number)
❌ d2a_attempts (Number)
❌ d2b_attempts (Number)
```

**Issue:** DynamoDB is schemaless, so fields can be added at runtime, BUT the CDK definition should document expected attributes for clarity.

**Impact:** Code in l9 writes these fields, but they're not documented in CDK. This works but is not best practice.

**Recommendation:** Add attribute definitions as comments in CDK for documentation.

---

### 2. Kriya Extraction (l10) - NOT UPDATED ❌

**Current state:** Still using old single-call approach
**Expected:** Full GSSR flow like l9

**Missing:**
- ❌ 3x generation calls
- ❌ Fidelity validation
- ❌ Consensus check
- ❌ 2-pass scoring
- ❌ Retry logic
- ❌ d2a_attempts tracking
- ❌ Prompt change to D2a_kriya_extraction.txt

**File:** `src/lambda_src/kg_agents/l10_extract_kriya/lambda_function.py`

---

### 3. Event/Karaka Extraction (l11) - NOT UPDATED ❌

**Current state:** Still using old single-call approach
**Expected:** Full GSSR flow + dependency on D1/D2a outputs

**Missing:**
- ❌ Load D1 entities from S3
- ❌ Load D2a kriyas from S3
- ❌ Format D2b prompt with INPUT ENTITIES and INPUT KRIYĀS
- ❌ 3x generation calls
- ❌ Fidelity validation (check entity references)
- ❌ Consensus check
- ❌ 2-pass scoring
- ❌ Retry logic
- ❌ d2b_attempts tracking
- ❌ Prompt change to D2b_event_karaka_extraction.txt

**File:** `src/lambda_src/kg_agents/l11_build_events/lambda_function.py`

---

### 4. Step Functions Retry Logic - NOT IMPLEMENTED ❌

**Current state:** Linear flow without retry handling
**Expected:** Choice states after each extraction to handle retry signals

**Missing in `serverless_stack.py`:**
```python
# Current (lines 710-780):
entities_task.next(kriya_task).next(build_events_task)...

# Expected:
entities_task.next(check_d1_retry)
check_d1_retry.when(
    Condition.string_equals("$.status", "retry"),
    entities_task  # Loop back
).otherwise(
    kriya_task  # Continue
)
```

**Impact:** Retry signals from l9 are ignored, no actual retry happens

---

### 5. CDK Stack - l24 Not Added ❌

**Issue:** l24_score_extractions Lambda not defined in CDK stack

**Missing in `serverless_stack.py`:**
```python
# Need to add:
score_extractions = _lambda.Function(
    self,
    "ScoreExtractions",
    runtime=_lambda.Runtime.PYTHON_3_12,
    handler="lambda_function.lambda_handler",
    code=_lambda.Code.from_asset(
        os.path.join("src", "lambda_src", "kg_agents", "l24_score_extractions")
    ),
    timeout=Duration.minutes(5),
    memory_size=1024,
    environment={
        "LLM_CALL_LAMBDA_NAME": llm_call.function_name,
        "KG_BUCKET": kg_bucket.bucket_name
    }
)

# Grant permissions
score_extractions.add_to_role_policy(s3_permissions)
score_extractions.add_to_role_policy(dynamodb_permissions)
llm_call.grant_invoke(score_extractions)

# Add to extraction Lambdas environment
extract_entities.add_environment("SCORER_LAMBDA_NAME", score_extractions.function_name)
extract_kriya.add_environment("SCORER_LAMBDA_NAME", score_extractions.function_name)
build_events.add_environment("SCORER_LAMBDA_NAME", score_extractions.function_name)

# Grant invoke permissions
score_extractions.grant_invoke(extract_entities)
score_extractions.grant_invoke(extract_kriya)
score_extractions.grant_invoke(build_events)
```

---

### 6. Prompt Names - PARTIALLY WRONG ⚠️

**l9 (entities):**
- Current: Uses `D1_entity_extraction.txt` ✅
- Expected: `D1_entity_extraction.txt` ✅

**l10 (kriya):**
- Current: Uses `kriya_concept_prompt.txt` ❌
- Expected: `D2a_kriya_extraction.txt` ❌

**l11 (events):**
- Current: Uses `karak_prompt.txt` ❌
- Expected: `D2b_event_karaka_extraction.txt` ❌

---

### 7. JSON Schema Misalignment ⚠️

**Issue:** Schemas in `json_schemas.py` don't match prompt outputs

**D2a Schema says:**
```python
"required": ["surface_text", "lemma"]
```

**But D2a_kriya_extraction.txt prompt outputs:**
```json
{
  "kriyās": [
    {
      "canonical_form": "serve",  // NOT "lemma"
      "surface_text": "served",
      "prayoga": "active",
      "is_copula": false
    }
  ]
}
```

**Fix needed:** Update schema to match prompt:
```python
D2A_SCHEMA = {
    "type": "object",
    "required": ["kriyās"],
    "properties": {
        "kriyās": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["canonical_form", "surface_text", "prayoga", "is_copula"],
                "properties": {
                    "canonical_form": {"type": "string"},
                    "surface_text": {"type": "string"},
                    "prayoga": {"type": "string", "enum": ["active", "passive"]},
                    "is_copula": {"type": "boolean"}
                }
            }
        }
    }
}
```

**D2b Schema says:**
```python
"required": ["event_id", "kriyā", "kāraka_links"]
```

**But D2b_event_karaka_extraction.txt prompt outputs:**
```json
{
  "event_instances": [
    {
      "instance_id": "event_1",  // NOT "event_id"
      "kriyā_concept": "serve",  // NOT "kriyā"
      "surface_text": "served",
      "prayoga": "active",
      "kāraka_links": [...]
    }
  ]
}
```

**Fix needed:** Update schema to match prompt:
```python
D2B_SCHEMA = {
    "type": "object",
    "required": ["event_instances"],
    "properties": {
        "event_instances": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["instance_id", "kriyā_concept", "surface_text", "prayoga", "kāraka_links"],
                "properties": {
                    "instance_id": {"type": "string"},
                    "kriyā_concept": {"type": "string"},
                    "surface_text": {"type": "string"},
                    "prayoga": {"type": "string"},
                    "kāraka_links": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["role", "entity", "reasoning"],
                            "properties": {
                                "role": {"type": "string"},
                                "entity": {"type": "string"},
                                "reasoning": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    }
}
```

---

### 8. Temperature Values - INCONSISTENT ⚠️

**Plan says:**
- Generation: 0.4
- Scoring Pass 1: 0.0
- Scoring Pass 2: 0.3

**l9 actually uses:**
- Generation: 0.6 ❌ (should be 0.4)
- Scoring Pass 1: 0.0 ✅
- Scoring Pass 2: 0.3 ✅

**Fix:** Change line in l9:
```python
# Line ~180
llm_response = call_llm(text, sentence_hash, job_id, 0.6, ...)
# Should be:
llm_response = call_llm(text, sentence_hash, job_id, 0.4, ...)
```

---

### 9. Fidelity Validator Bug ⚠️

**Issue in `fidelity_validator.py` line 67:**
```python
def validate_d2b_fidelity(events_json, sentence, entities_json):
    # ...
    for event in events:
        event_id = event.get('event_id', 'unknown')  # ❌ Wrong key
```

**Should be:**
```python
event_id = event.get('instance_id', 'unknown')  # ✅ Matches prompt
```

---

### 10. l9 Correction Prompt Issue ⚠️

**Line 234 in l9:**
```python
'ORIGINAL_REASONING': '',  # TODO: Extract from LLM response
```

**Issue:** Reasoning not extracted, correction prompt gets empty reasoning

**Fix:** Use `extract_reasoning_block()` from gssr_utils:
```python
from gssr_utils import extract_reasoning_block

# In correction loop:
original_reasoning = extract_reasoning_block(content)
'ORIGINAL_REASONING': original_reasoning
```

---

## 📋 PRIORITY ACTION ITEMS

### Critical (Blocks GSSR functionality):
1. **Update l10 (kriya extraction)** - Copy GSSR flow from l9, adapt for D2a
2. **Update l11 (event extraction)** - Copy GSSR flow from l9, add D1/D2a loading, adapt for D2b
3. **Add l24 to CDK stack** - Define Lambda and wire permissions
4. **Add Step Functions retry logic** - Add Choice states for retry handling
5. **Fix JSON schemas** - Align with prompt outputs

### Important (Improves quality):
6. **Fix temperature in l9** - Change 0.6 to 0.4
7. **Fix fidelity validator** - Use correct key names
8. **Fix l9 correction** - Extract reasoning properly
9. **Update prompt names in l10/l11** - Use D2a/D2b prompts

### Nice to have (Documentation):
10. **Document Sentences table schema in CDK** - Add comments for expected fields

---

## 🎯 ALIGNMENT SUMMARY

| Component | Status | Notes |
|-----------|--------|-------|
| LLM Gateway (l7) | ✅ DONE | Fully aligned |
| Shared Utilities | ✅ DONE | Minor schema fixes needed |
| Scorer Lambda (l24) | ⚠️ PARTIAL | Code done, not in CDK |
| Entity Extraction (l9) | ⚠️ PARTIAL | GSSR done, minor fixes needed |
| Kriya Extraction (l10) | ❌ NOT DONE | Still old approach |
| Event Extraction (l11) | ❌ NOT DONE | Still old approach |
| Step Functions | ❌ NOT DONE | No retry logic |
| Database Schema | ⚠️ PARTIAL | Works but undocumented |
| Prompts | ⚠️ PARTIAL | l9 correct, l10/l11 wrong |

**Overall Progress: ~40% complete**

---

## 📝 NEXT STEPS

1. Fix JSON schemas to match prompts
2. Add l24 to CDK stack
3. Update l10 with GSSR flow
4. Update l11 with GSSR flow + D1/D2a loading
5. Add Step Functions retry logic
6. Fix minor issues in l9 (temperature, reasoning extraction)
7. Deploy and test end-to-end

**Estimated time to complete:** 60-90 minutes
