# KG Processing Issues - Analysis

## ⚠️ Critical Issue Found

### Problem: Prompt Template Format Mismatch

**Location:** `src/lambda_src/llm_gateway/l7_llm_call/lambda_function.py`

**Issue:**
```python
# Lambda code uses Python .format()
formatted_prompt = prompt_template.format(**inputs_dict)
```

**But prompts use double braces:**
```
# prompts/entity_prompt.txt
SENTENCE:
{{SENTENCE_HERE}}
```

**Python .format() expects single braces:**
```
{SENTENCE_HERE}  ← Correct for Python
{{SENTENCE_HERE}} ← This escapes to literal {{SENTENCE_HERE}}
```

### Impact
- Prompts are NOT being filled with actual sentence text
- LLM receives literal `{{SENTENCE_HERE}}` instead of actual sentence
- KG extraction fails or produces garbage
- Processing stuck at 0%

### Evidence
1. ✅ APIs working (upload, status, docs)
2. ✅ S3 trigger working (status changes to `processing_kg`)
3. ✅ Sentence splitting working (2 sentences detected)
4. ❌ LLM calls not progressing (`llm_calls_made: 0`)

## 🔧 Required Fixes

### Fix 1: Update Prompt Templates
**Change all prompts from:**
```
{{VARIABLE_NAME}}
```

**To:**
```
{VARIABLE_NAME}
```

**Files to update:**
- `prompts/entity_prompt.txt` - Change `{{SENTENCE_HERE}}` → `{SENTENCE_HERE}`
- `prompts/kriya_concept_prompt.txt` - Change `{{SENTENCE_HERE}}` → `{SENTENCE_HERE}`
- `prompts/event_instance_prompt.txt` - Change `{{SENTENCE_HERE}}`, `{{ENTITY_LIST_JSON}}`, `{{KRIYA_LIST_JSON}}`
- `prompts/relation_prompt.txt`
- `prompts/attribute_prompt.txt`
- `prompts/auditor_prompt.txt`
- `prompts/answer_synthesizer_prompt.txt` - Change `{{QUERY}}`, `{{CONTEXT}}`

### Fix 2: Verify Input Key Names
**L9 Extract Entities:**
```python
'inputs': {'SENTENCE_HERE': text}  ← Must match prompt variable
```

**Prompt must have:**
```
{SENTENCE_HERE}  ← Must match input key
```

### Fix 3: Check Event Instance Prompt
**L11 needs to pass:**
```python
'inputs': {
    'SENTENCE_HERE': text,
    'ENTITY_LIST_JSON': json.dumps(entities),
    'KRIYA_LIST_JSON': json.dumps(kriyas)
}
```

**Prompt must have:**
```
{SENTENCE_HERE}
{ENTITY_LIST_JSON}
{KRIYA_LIST_JSON}
```

## 🧪 Testing After Fix

### Test 1: Check Prompt Formatting
```bash
# After fixing prompts, redeploy
bash deploy-backend.sh

# Upload new test document
curl -X POST "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/upload" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test-fix.txt"}'

# Upload file and monitor
# Should see llm_calls_made increasing
```

### Test 2: Check LLM Logs
```bash
# Query LLMCallLog table
aws dynamodb scan --table-name LLMCallLog \
  --filter-expression "job_id = :jid" \
  --expression-attribute-values '{":jid":{"S":"<job_id>"}}' \
  --limit 5
```

**Expected:** Logs with `status: "success"` and actual responses

### Test 3: Check S3 Outputs
```bash
# Check if KG files are created
aws s3 ls s3://knowledge-graph-151534200269-us-east-1/temp_kg/ --recursive

# Should see:
# temp_kg/{hash}/entities.json
# temp_kg/{hash}/kriya.json
# temp_kg/{hash}/events.json
```

## 📊 Current Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Upload API | ✅ Working | Tested successfully |
| Status API | ✅ Working | Returns correct data |
| Docs API | ✅ Working | Lists all jobs |
| S3 Trigger | ✅ Working | Auto-fires on upload |
| Sentence Split | ✅ Working | Detects 2 sentences |
| Step Functions | ⚠️ Started | Execution begins |
| LLM Calls | ❌ Failing | Prompt format issue |
| KG Extraction | ❌ Not Working | Blocked by LLM calls |
| Embeddings | ❌ Not Working | Blocked by LLM calls |
| Graph Storage | ❌ Not Implemented | L15/L16 are TODO stubs |

## 🎯 Priority Actions

### Immediate (Blocking)
1. ✅ Fix prompt templates (change `{{}}` to `{}`)
2. ✅ Verify input key names match prompt variables
3. ✅ Redeploy backend
4. ✅ Test with new document

### Short Term
1. Implement L15/L16 graph operations
2. Add NetworkX graph serialization
3. Update L18 to load graphs

### Long Term
1. Add GSVR (Generate-Score-Verify-Retry) logic
2. Implement prompt chaining for complex extractions
3. Add error recovery and retry logic

## 🔍 How to Verify Fix

```bash
# 1. Fix prompts
# 2. Deploy
bash deploy-backend.sh

# 3. Upload test
TEST_RESPONSE=$(curl -s -X POST "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/upload" \
  -H "Content-Type: application/json" \
  -d '{"filename": "verify-fix.txt"}')

JOB_ID=$(echo $TEST_RESPONSE | jq -r '.job_id')
UPLOAD_URL=$(echo $TEST_RESPONSE | jq -r '.pre_signed_url')

echo "Rama teaches Sita. Sita learns quickly." > verify-fix.txt
curl -X PUT --upload-file verify-fix.txt "$UPLOAD_URL"

# 4. Monitor (should see llm_calls_made increasing)
for i in {1..10}; do
  echo "Check $i:"
  curl -s "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/status/$JOB_ID" | jq '.llm_calls_made'
  sleep 5
done
```

**Expected:** `llm_calls_made` should increase from 0 → 6 → 12 (2 sentences × 6 stages each)

## 📝 Conclusion

**APIs are ready for client integration** ✅

**KG processing needs prompt template fix** ❌

Once prompts are fixed, the full pipeline should work as designed.
