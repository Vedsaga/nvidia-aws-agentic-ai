# GSSR Implementation Plan

**Reference:** This implements `tasks.md` → "KG Pipeline Architecture: GSSR Implementation"

---

## Understanding the Flow

### GSSR applies to EACH stage independently:
1. **D1 (Entity Extraction):** Sentence → 3x JSONs → GSSR → Best entity list
2. **D2a (Kriya Extraction):** Sentence → 3x JSONs → GSSR → Best kriya list  
3. **D2b (Event/Karaka):** Sentence + D1 output + D2a output → 3x JSONs → GSSR → Best events

**Key insight:** D1 and D2a run independently (only need sentence). D2b depends on D1 and D2a outputs.

### GSSR Flow (per stage):
```
Phase 1: Generate 3 JSONs (temp=0.6, sequential not parallel)
Phase 2: Fidelity check each JSON
Phase 2a: Consensus check (all 3 identical?)
  → YES: Score=100, done
  → NO: Continue to Phase 3
Phase 3: Scorer Pass 1 (temp=0.0) → 3 scores
  → All < 70? Retry from Phase 1 (max 5 attempts)
Phase 4: Scorer Pass 2 (temp=0.3) → 3 scores  
  → All < 70? Retry from Phase 1 or fallback
Phase 5: Select best (avg of pass1+pass2), update Sentences table
```

---

## Current State Analysis

### What Works
- Document upload → S3 trigger → Validation → Sanitization → Sentence split
- Step Functions orchestration with Map state
- Single LLM call per stage (D1, D2a, D2b) with temp=0.1
- LLMCallLog table exists with basic logging
- Sentences table exists with basic schema
- Graph storage in NetworkX (nodes/edges)
- Prompts ready: D1_entity_extraction.txt, D2a_kriya_extraction.txt, D2b_event_karaka_extraction.txt, scorer.txt, correction_prompt.txt

### What's Missing

#### 1. Sentences Table Schema Updates
**Task Ref:** `tasks.md` → "Define Sentence Table & Caching Strategy"

**Current schema:** sentence_hash (PK), text, job_id, status
**Missing fields:**
- `original_sentence` (String) - Raw sentence text
- `document_ids` (List) - All source docs containing this sentence
- `status` (String) - Enum: KG_PENDING, KG_IN_PROGRESS, KG_COMPLETE, KG_FAILED, NEEDS_REVIEW
- `best_score` (Number) - Final combined score after GSSR
- `failure_reason` (String) - Why GSSR failed
- `needs_review` (Boolean) - Human review flag
- `attempts_count` (Number) - GSSR retry attempts
- `d1_attempts` (Number) - D1 stage attempts
- `d2a_attempts` (Number) - D2a stage attempts
- `d2b_attempts` (Number) - D2b stage attempts

**Note:** job_id still relevant for tracking which document triggered processing, but sentence can belong to multiple documents (document_ids list).

#### 2. LLMCallLog Table Enhancements
**Task Ref:** `tasks.md` → "Implement Comprehensive Logging Strategy"

**Current:** call_id (PK), timestamp (SK), job_id, sentence_hash, stage, status, response_json
**Missing fields:**
- `pipeline_stage` (String) - D1/D2a/D2b/Scorer/Correction
- `attempt_number` (Number) - Which GSSR attempt (1-5)
- `generation_index` (Number) - Which of 3 generations (1-3)
- `temperature` (Number) - Temperature used
- `prompt_template` (String) - Which prompt file
- `raw_request` (String) - Full request payload
- `raw_response` (String) - Full response (no cleanup)
- `extracted_json` (String) - Parsed JSON output
- `extracted_reasoning` (String) - Parsed reasoning block

#### 3. Temperature Parameter in LLM Gateway
**Task Ref:** `tasks.md` → "Temperature strategy: Generation = 0.6, Scoring Pass 1 = 0.0, Scoring Pass 2 = 0.3"

**Current:** Hardcoded temp=0.1 in l7_llm_call
**Needed:** Accept temperature as input parameter

#### 4. Fidelity Validation Utility
**Task Ref:** `tasks.md` → "Phase 2: Unidirectional Fidelity Check"

**Needed:** Programmatic check that all extracted text exists in sentence
- For D1: Check all `entity.text` values
- For D2a: Check all `kriya.surface_text` values
- For D2b: Check all `entity` references in `kāraka_links`
- Case-insensitive with warning
- Return: (is_valid, error_details)

#### 5. JSON Schema Validation
**User Requirement:** "schema check if LLM output have invalid JSON schema"

**Needed:** Define schemas for D1, D2a, D2b outputs and validate before processing

#### 6. Consensus Check Utility
**Task Ref:** `tasks.md` → "Phase 2a: Consensus Check"

**Needed:** Compare 3 JSONs using `json.dumps(sort_keys=True)`

#### 7. Scorer Lambda
**Task Ref:** `tasks.md` → "Phase 3: LLM Scoring (Pass 1)" + "Phase 4: LLM Scoring (Pass 2)"

**Needed:** New Lambda l24_score_extractions that:
- Takes 3 JSONs + sentence + stage
- Calls LLM with scorer.txt prompt
- Parses scores from response
- Returns array of 3 scores with reasoning

#### 8. GSSR Logic in Extraction Lambdas
**Task Ref:** All GSSR phases

**Needed:** Modify l9, l10, l11 to implement full GSSR flow:
- Generate 3 JSONs (sequential calls, temp=0.6)
- Fidelity check each
- Consensus check
- Scoring (2-pass)
- Retry logic with attempts tracking
- Fallback selection

#### 9. Step Functions Retry Logic
**Task Ref:** `tasks.md` → Retry logic throughout

**Needed:** Update state machine to handle retry signals from Lambdas

---

## Sequential Implementation Plan

**Total: ~100 minutes**

### Phase 1: Database Schema Updates (15 min)
**Why first:** All Lambdas depend on these schemas

1. **Update Sentences table in CDK** (10 min)
   - Add all missing fields listed above
   - Update GSI if needed
   - Deploy: `cdk deploy`

2. **Update LLMCallLog table in CDK** (5 min)
   - Add missing metadata fields
   - Deploy: `cdk deploy`

### Phase 2: Shared Utilities (20 min)
**Why second:** Extraction Lambdas will use these

3. **Create `src/lambda_src/shared/json_schemas.py`** (5 min)
   ```python
   D1_SCHEMA = {...}  # entities array
   D2A_SCHEMA = {...}  # kriyās array
   D2B_SCHEMA = {...}  # event_instances array
   ```

4. **Create `src/lambda_src/shared/fidelity_validator.py`** (8 min)
   ```python
   def validate_d1_fidelity(entities_json, sentence)
   def validate_d2a_fidelity(kriyas_json, sentence)
   def validate_d2b_fidelity(events_json, sentence, entities_json)
   ```

5. **Create `src/lambda_src/shared/gssr_utils.py`** (7 min)
   ```python
   def check_consensus(json1, json2, json3)
   def parse_llm_json_response(raw_response)
   def extract_reasoning_block(raw_response)
   ```

### Phase 3: LLM Gateway Enhancement (10 min)

6. **Modify `l7_llm_call/lambda_function.py`** (10 min)
   - Accept `temperature` parameter from event
   - Default to 0.6 if not provided
   - Update LLMCallLog writes to include all new metadata fields
   - Store raw_request, raw_response, extracted_json, extracted_reasoning

### Phase 4: Scorer Lambda (15 min)

7. **Create `l24_score_extractions/lambda_function.py`** (15 min)
   - Input: {sentence, json1, json2, json3, stage, temperature}
   - Load scorer.txt prompt
   - Format with sentence and 3 JSONs
   - Call l7_llm_call with specified temperature
   - Parse response to extract 3 scores
   - Return: {scores: [score1, score2, score3], reasoning: [...]}

8. **Add l24 to CDK stack** (included in step 7)
   - Grant invoke permissions to l9, l10, l11

### Phase 5: GSSR Implementation in Extraction Lambdas (35 min)

**For each of l9, l10, l11:**

9. **Modify `l9_extract_entities/lambda_function.py`** (12 min)
   - Change prompt to D1_entity_extraction.txt
   - Implement GSSR flow:
     - Loop: Generate 3 JSONs sequentially (temp=0.6)
     - Fidelity check each (use fidelity_validator)
     - If fidelity fails: Call with correction_prompt.txt once
     - Consensus check (use gssr_utils)
     - If consensus: score=100, done
     - Else: Call l24 twice (temp=0.0, then 0.3)
     - If all scores < 70: Check d1_attempts in Sentences table
     - If d1_attempts < 5: Increment, return retry signal
     - If d1_attempts == 5: Select best, mark needs_review
   - Update Sentences table with results
   - Store best JSON to S3

10. **Modify `l10_extract_kriya/lambda_function.py`** (12 min)
    - Same GSSR flow as l9
    - Change prompt to D2a_kriya_extraction.txt
    - Track d2a_attempts separately

11. **Modify `l11_build_events/lambda_function.py`** (12 min)
    - Load D1 and D2a outputs from S3 first
    - Format D2b prompt with INPUT ENTITIES and INPUT KRIYĀS
    - Same GSSR flow
    - Track d2b_attempts separately

### Phase 6: Step Functions Update (5 min)

12. **Update `serverless_stack.py` state machine** (5 min)
    - Add Choice states after each extraction task
    - Check for retry signal in output
    - If retry: Loop back to same task
    - If done: Continue to next task
    - Pass attempts through state context

---

## Detailed Implementation Notes

### 1. Fidelity Validation Logic

```python
def validate_d1_fidelity(entities_json, sentence):
    """Check all entity.text exists in sentence"""
    errors = []
    for entity in entities_json.get('entities', []):
        text = entity.get('text', '')
        if text.lower() not in sentence.lower():
            errors.append(f"Entity '{text}' not found in sentence")
        elif text not in sentence:
            errors.append(f"Warning: Case mismatch for '{text}'")
    return len(errors) == 0, errors

def validate_d2a_fidelity(kriyas_json, sentence):
    """Check all kriya.surface_text exists in sentence"""
    errors = []
    for kriya in kriyas_json.get('kriyās', []):
        text = kriya.get('surface_text', '')
        if text.lower() not in sentence.lower():
            errors.append(f"Kriya '{text}' not found in sentence")
    return len(errors) == 0, errors

def validate_d2b_fidelity(events_json, sentence, entities_json):
    """Check all entity references exist in INPUT ENTITIES"""
    errors = []
    entity_texts = [e['text'] for e in entities_json.get('entities', [])]
    
    for event in events_json.get('event_instances', []):
        for link in event.get('kāraka_links', []):
            entity = link.get('entity', '')
            if entity not in entity_texts:
                errors.append(f"Entity '{entity}' in kāraka not in D1 output")
    return len(errors) == 0, errors
```

### 2. GSSR Flow in Extraction Lambda

```python
def lambda_handler(event, context):
    sentence = event['text']
    sentence_hash = event['hash']
    job_id = event['job_id']
    stage = 'D1_Entities'  # or D2a_Kriya, D2b_Karakas
    
    # Get current attempts from Sentences table
    attempts = get_attempts_count(sentence_hash, stage)
    
    if attempts >= 5:
        # Max attempts reached, use fallback
        return handle_fallback(sentence_hash, stage)
    
    # Phase 1: Generate 3 JSONs
    jsons = []
    for i in range(3):
        response = call_llm(
            sentence=sentence,
            prompt='D1_entity_extraction.txt',
            temperature=0.6,
            metadata={'attempt': attempts+1, 'generation': i+1}
        )
        parsed = parse_llm_json_response(response)
        jsons.append(parsed)
    
    # Phase 2: Fidelity check
    valid_jsons = []
    for j in jsons:
        is_valid, errors = validate_d1_fidelity(j, sentence)
        if not is_valid:
            # Try correction once
            corrected = call_llm_with_correction(sentence, j, errors)
            is_valid, _ = validate_d1_fidelity(corrected, sentence)
            if is_valid:
                valid_jsons.append(corrected)
            else:
                valid_jsons.append(j)  # Use as-is
        else:
            valid_jsons.append(j)
    
    # Phase 2a: Consensus check
    if check_consensus(valid_jsons[0], valid_jsons[1], valid_jsons[2]):
        best_json = valid_jsons[0]
        best_score = 100
        update_sentences_table(sentence_hash, stage, best_score, attempts+1, False)
        save_to_s3(sentence_hash, stage, best_json)
        return event  # Continue to next stage
    
    # Phase 3: Scoring Pass 1
    scores_pass1 = call_scorer(sentence, valid_jsons, temperature=0.0)
    
    if all(s < 70 for s in scores_pass1):
        # Retry
        increment_attempts(sentence_hash, stage)
        return {'status': 'retry', 'stage': stage}
    
    # Phase 4: Scoring Pass 2
    scores_pass2 = call_scorer(sentence, valid_jsons, temperature=0.3)
    
    if all(s < 70 for s in scores_pass2):
        if attempts + 1 < 5:
            increment_attempts(sentence_hash, stage)
            return {'status': 'retry', 'stage': stage}
        else:
            # Fallback
            return handle_fallback_with_scores(
                sentence_hash, stage, valid_jsons, scores_pass1, scores_pass2
            )
    
    # Phase 5: Select best
    combined = [(s1+s2)/2 for s1, s2 in zip(scores_pass1, scores_pass2)]
    best_idx = combined.index(max(combined))
    best_json = valid_jsons[best_idx]
    best_score = combined[best_idx]
    
    update_sentences_table(sentence_hash, stage, best_score, attempts+1, False)
    save_to_s3(sentence_hash, stage, best_json)
    
    return event  # Continue to next stage
```

### 3. Scorer Lambda Implementation

```python
def lambda_handler(event, context):
    sentence = event['sentence']
    json1 = event['json1']
    json2 = event['json2']
    json3 = event['json3']
    temperature = event.get('temperature', 0.0)
    
    # Load scorer prompt
    prompt_template = load_prompt('scorer.txt')
    
    # Format prompt
    formatted = prompt_template.format(
        SENTENCE_HERE=sentence,
        JSON_1=json.dumps(json1, indent=2),
        JSON_2=json.dumps(json2, indent=2),
        JSON_3=json.dumps(json3, indent=2)
    )
    
    # Call LLM
    response = lambda_client.invoke(
        FunctionName=LLM_LAMBDA,
        Payload=json.dumps({
            'job_id': event.get('job_id'),
            'sentence_hash': event.get('sentence_hash'),
            'stage': 'Scorer',
            'prompt_name': 'scorer.txt',
            'temperature': temperature,
            'inputs': {'formatted_prompt': formatted}
        })
    )
    
    llm_output = json.loads(response['Payload'].read())
    
    # Parse scores from response
    scores = parse_scorer_response(llm_output)
    
    return {
        'scores': scores,  # [score1, score2, score3]
        'raw_response': llm_output
    }
```

### 4. Step Functions Retry Logic

```python
# In serverless_stack.py

# Add retry logic for each extraction stage
entities_task = tasks.LambdaInvoke(...)

check_d1_retry = sfn.Choice(self, "CheckD1Retry")
check_d1_retry.when(
    sfn.Condition.string_equals("$.status", "retry"),
    entities_task  # Loop back
).otherwise(
    kriya_task  # Continue to next stage
)

entities_task.next(check_d1_retry)

# Similar for D2a and D2b
```

### 5. LLMCallLog Enhanced Logging

```python
# In l7_llm_call
dynamodb.put_item(
    TableName=LOG_TABLE,
    Item={
        'call_id': {'S': call_id},
        'timestamp': {'N': str(int(time.time() * 1000))},
        'job_id': {'S': job_id},
        'sentence_hash': {'S': sentence_hash},
        'pipeline_stage': {'S': stage},  # NEW
        'attempt_number': {'N': str(attempt_number)},  # NEW
        'generation_index': {'N': str(generation_index)},  # NEW
        'temperature': {'N': str(temperature)},  # NEW
        'prompt_template': {'S': prompt_name},
        'raw_request': {'S': json.dumps(request_payload)},  # NEW
        'raw_response': {'S': json.dumps(response_data)},  # NEW
        'extracted_json': {'S': extracted_json_str},  # NEW
        'extracted_reasoning': {'S': reasoning_block},  # NEW
        'status': {'S': 'success'}
    }
)
```

---

## Key Corrections from Previous Plan

1. **NOT parallel calls:** Generate 3 JSONs sequentially (they're independent but not parallel to avoid rate limits)
2. **Stage-specific attempts:** Track d1_attempts, d2a_attempts, d2b_attempts separately (not global attempts_count)
3. **job_id still relevant:** Tracks which document triggered processing, but sentence can belong to multiple docs
4. **LLMCallLog enhancements:** Added all metadata fields for complete traceability
5. **D2b dependency:** Must load D1 and D2a outputs before generating D2b JSONs
6. **Sequential execution order:** Database schema → Utilities → LLM Gateway → Scorer → Extraction Lambdas → Step Functions

---

## Testing Strategy

1. **Unit tests:**
   - Fidelity validator with known good/bad cases
   - Consensus checker
   - JSON schema validation

2. **Integration tests:**
   - Single sentence through D1 GSSR
   - Single sentence through D2a GSSR
   - Single sentence through D2b GSSR (with D1/D2a outputs)
   - Retry scenario (inject low scores)
   - Max attempts fallback

3. **End-to-end:**
   - Full document with multiple sentences
   - Verify LLMCallLog has all metadata
   - Verify Sentences table updated correctly

---

## Success Criteria

- [ ] Sentences table has all new fields
- [ ] LLMCallLog has enhanced metadata
- [ ] Each extraction stage generates 3 JSONs with temp=0.6
- [ ] Fidelity check catches invalid extractions
- [ ] Consensus optimization works (skips scoring when identical)
- [ ] Scorer returns 3 scores correctly
- [ ] Retry logic works up to 5 attempts per stage
- [ ] Fallback selection works when max attempts reached
- [ ] Sentences table tracks stage-specific attempts and scores
- [ ] End-to-end test shows improved quality
