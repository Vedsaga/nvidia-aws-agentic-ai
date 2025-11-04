# GSSR End-to-End Testing Guide

## Overview

This guide covers testing the complete pipeline from file upload to answer synthesis, with focus on verifying the GSSR (Generate-Score-Select-Repeat) flow.

---

## Quick Start

### Run Complete E2E Test
```bash
./test-e2e-gssr.sh
```

This single script tests the entire flow:
1. ✅ File upload
2. ✅ Sentence splitting
3. ✅ GSSR KG creation (D1, D2a, D2b)
4. ✅ Embedding storage
5. ✅ NetworkX graph storage
6. ✅ Query submission
7. ✅ Sentence retrieval via embedding
8. ✅ Graph context fetch
9. ✅ Answer synthesis

**Expected duration:** 2-5 minutes depending on sentence complexity

---

## Detailed Testing Steps

### 1. Monitor GSSR Flow in Real-Time

**Terminal 1 - Start monitoring:**
```bash
./monitor-gssr-flow.sh
```

This tails CloudWatch logs showing:
- Phase 1: Generation (3x JSONs)
- Phase 2: Fidelity checks
- Phase 2a: Consensus checks
- Phase 3: Scoring Pass 1
- Phase 4: Scoring Pass 2
- Phase 5: Best selection

**Terminal 2 - Run test:**
```bash
./test-e2e-gssr.sh
```

You'll see real-time logs like:
```
[D1-ENTITIES] Phase 1: Generating 3 JSONs for abc123...
[D1-ENTITIES] Phase 2: Fidelity check
[D1-ENTITIES] Phase 2a: Consensus check
[D1-ENTITIES] Consensus achieved! Score=100
[D2a-KRIYA] Phase 1: Generating 3 JSONs for abc123...
[SCORER] Scoring 3 JSONs with temp=0.0
```

---

### 2. Inspect GSSR Results

After processing completes, inspect the results:

```bash
# Get job_id from test output, then:
./inspect-gssr-results.sh <job_id>
```

**This shows:**
- Sentences processed with their text
- GSSR attempts per stage (d1_attempts, d2a_attempts, d2b_attempts)
- Best scores achieved
- Sentences needing review
- Average attempts and scores
- LLM call breakdown by stage and temperature

**Example output:**
```
Sentence: Dr. Elena Kowalski served as chief neuroscientist...
Hash: abc123...
Status: KG_COMPLETE
Best Score: 92
Needs Review: false
D1 Attempts: 1
D2a Attempts: 1
D2b Attempts: 2

GSSR Statistics:
Average attempts:
  D1 (Entities): 1.0
  D2a (Kriya): 1.2
  D2b (Events): 1.5
Average best score: 88.5
Sentences needing review: 0 / 2
```

---

### 3. Manual Step-by-Step Testing

If you want to test each step manually:

#### Step 1: Upload File
```bash
# Create test file
echo "Rama eats mango." > test.txt

# Request upload URL
curl -X POST "${VITE_API_URL}upload" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.txt"}' | jq '.'

# Save job_id and pre_signed_url from response
```

#### Step 2: Upload to S3
```bash
curl -X PUT "<pre_signed_url>" \
  -H "Content-Type: text/plain" \
  --data-binary "@test.txt"
```

#### Step 3: Monitor Processing
```bash
# Check status every 5 seconds
watch -n 5 "curl -s ${VITE_API_URL}status/<job_id> | jq '.'"
```

#### Step 4: Check Processing Chain
```bash
# See all LLM calls made during GSSR
curl -s "${VITE_API_URL}processing-chain/<job_id>" | jq '.'

# Count calls by stage
curl -s "${VITE_API_URL}processing-chain/<job_id>" | \
  jq -r '.llm_calls[] | .pipeline_stage' | sort | uniq -c
```

#### Step 5: Check Sentence Details
```bash
# Get sentence hash from processing chain
SENTENCE_HASH=$(curl -s "${VITE_API_URL}processing-chain/<job_id>" | \
  jq -r '.llm_calls[0].sentence_hash')

# Get detailed sentence processing
curl -s "${VITE_API_URL}sentence-chain/${SENTENCE_HASH}" | jq '.'
```

#### Step 6: Submit Query
```bash
curl -X POST "${VITE_API_URL}query/submit" \
  -H "Content-Type: application/json" \
  -d '{"question": "Who eats mango?"}' | jq '.'

# Save query_id from response
```

#### Step 7: Check Query Status
```bash
curl -s "${VITE_API_URL}query/status/<query_id>" | jq '.'
```

---

## Verification Checklist

### ✅ GSSR Flow Verification

**Check CloudWatch Logs for:**
- [ ] "Phase 1: Generating 3 JSONs" appears
- [ ] "Phase 2: Fidelity check" appears
- [ ] "Phase 2a: Consensus check" appears
- [ ] Either "Consensus achieved! Score=100" OR "Phase 3: Scoring Pass 1"
- [ ] If scoring: "Pass 1 scores: [X, Y, Z]"
- [ ] If scoring: "Phase 4: Scoring Pass 2"
- [ ] If scoring: "Pass 2 scores: [X, Y, Z]"
- [ ] "Phase 5: Selecting best" appears
- [ ] "Best score: X (JSON Y)" appears

**Check DynamoDB Sentences Table:**
- [ ] `d1_attempts` field exists and is >= 1
- [ ] `d2a_attempts` field exists and is >= 1
- [ ] `d2b_attempts` field exists and is >= 1
- [ ] `best_score` field exists and is > 0
- [ ] `needs_review` field exists (true/false)
- [ ] `status` is "KG_COMPLETE" or "NEEDS_REVIEW"

**Check DynamoDB LLMCallLog Table:**
- [ ] `pipeline_stage` includes "D1_Entities", "D2a_Kriya", "D2b_Karakas"
- [ ] `attempt_number` ranges from 1-5
- [ ] `generation_index` is 1, 2, or 3 for generation calls
- [ ] `temperature` is 0.4 for generation, 0.0/0.3 for scoring
- [ ] `raw_request` and `raw_response` are populated
- [ ] `extracted_json` and `extracted_reasoning` are populated

---

## Expected GSSR Patterns

### Pattern 1: Consensus (Best Case)
```
Phase 1: Generate 3 JSONs (temp=0.4)
Phase 2: Fidelity check (all pass)
Phase 2a: Consensus check
→ All 3 JSONs identical
→ Score = 100
→ Skip scoring phases
→ Total LLM calls: 3
```

### Pattern 2: Scoring (Normal Case)
```
Phase 1: Generate 3 JSONs (temp=0.4)
Phase 2: Fidelity check (all pass)
Phase 2a: Consensus check (different)
Phase 3: Scoring Pass 1 (temp=0.0)
→ At least one score >= 70
Phase 4: Scoring Pass 2 (temp=0.3)
→ At least one score >= 70
Phase 5: Select best by average
→ Total LLM calls: 3 + 1 + 1 = 5
```

### Pattern 3: Retry (Low Scores)
```
Attempt 1:
  Phase 1-4: All scores < 70
  → Retry triggered
  
Attempt 2:
  Phase 1: Generate 3 JSONs (with scorer feedback)
  Phase 2-4: At least one score >= 70
  Phase 5: Select best
→ Total LLM calls: 5 + 5 = 10
```

### Pattern 4: Max Attempts (Fallback)
```
Attempts 1-5: All scores < 70
→ Select best from attempt 5
→ Mark needs_review = TRUE
→ Total LLM calls: 5 * 5 = 25
```

---

## Performance Metrics

### Expected LLM Call Counts

**Per sentence, per stage:**
- Best case (consensus): 3 calls
- Normal case (scoring): 5 calls
- Retry case: 10-25 calls (depending on attempts)

**Total per sentence (D1 + D2a + D2b):**
- Best case: 9 calls (3 per stage)
- Normal case: 15 calls (5 per stage)
- Worst case: 75 calls (25 per stage)

### Expected Processing Times

**Per sentence:**
- Best case (consensus): 30-60 seconds
- Normal case (scoring): 60-120 seconds
- Retry case: 120-300 seconds

**Per document:**
- Depends on sentence count
- Example: 10 sentences = 10-30 minutes

---

## Troubleshooting

### Issue: No GSSR logs appearing

**Check:**
```bash
# Verify Lambda functions exist
aws lambda list-functions | grep -E "Extract|Score"

# Check Lambda logs directly
aws logs tail /aws/lambda/ServerlessStack-ExtractEntities --follow
```

### Issue: All scores are 0

**Check:**
```bash
# Verify scorer prompt exists in S3
aws s3 ls s3://knowledge-graph-*/prompts/scorer.txt

# Check scorer Lambda logs
aws logs tail /aws/lambda/ServerlessStack-ScoreExtractions --follow
```

### Issue: Fidelity check always fails

**Check:**
```bash
# Look for fidelity errors in logs
aws logs filter-pattern "fidelity" \
  --log-group-name /aws/lambda/ServerlessStack-ExtractEntities
```

### Issue: Retry not working

**Check:**
```bash
# Verify Step Functions has Choice states
aws stepfunctions describe-state-machine \
  --state-machine-arn <arn> | jq '.definition' | grep -A5 "CheckD1Retry"
```

---

## Success Criteria

✅ **Test passes if:**

1. File uploads successfully
2. Sentences are split and hashed
3. GSSR flow executes for all stages (D1, D2a, D2b)
4. At least one of these occurs per stage:
   - Consensus achieved (score=100), OR
   - Scoring produces score >= 70, OR
   - Fallback selection after max attempts
5. Embeddings created and stored
6. Graph nodes/edges created in NetworkX
7. Query retrieves relevant sentences
8. Answer is synthesized with graph context
9. All DynamoDB fields populated correctly
10. No Lambda errors in CloudWatch

---

## Advanced Testing

### Test Retry Logic

Create a sentence that's hard to parse:
```bash
echo "The study, which was conducted by researchers who had previously worked on similar projects in multiple countries, showed significant results." > complex.txt
```

This should trigger retries due to complexity.

### Test Consensus Optimization

Create a simple, unambiguous sentence:
```bash
echo "John eats pizza." > simple.txt
```

This should achieve consensus (all 3 JSONs identical).

### Test Multiple Sentences

Create a document with varied complexity:
```bash
cat > varied.txt << EOF
John eats pizza.
Dr. Smith, a renowned scientist, conducted research at MIT from 2010 to 2020.
The complex study examining neuroplasticity was funded by multiple organizations.
EOF
```

This tests GSSR across different difficulty levels.

---

## Monitoring Dashboard Queries

### Get GSSR success rate
```bash
aws dynamodb scan --table-name Sentences \
  --projection-expression "best_score,needs_review" | \
  jq '[.Items[] | select(.best_score.N | tonumber >= 70)] | length'
```

### Get average attempts per stage
```bash
aws dynamodb scan --table-name Sentences | \
  jq '[.Items[].d1_attempts.N | tonumber] | add / length'
```

### Get consensus rate
```bash
aws dynamodb scan --table-name Sentences | \
  jq '[.Items[] | select(.best_score.N == "100")] | length'
```

---

## Next Steps After Testing

1. **Review sentences with needs_review=TRUE**
2. **Analyze scorer feedback for common issues**
3. **Optimize prompts based on failure patterns**
4. **Adjust temperature/thresholds if needed**
5. **Monitor costs and optimize LLM call counts**

---

## Support

If tests fail, collect this information:
1. Job ID
2. CloudWatch logs from all Lambdas
3. DynamoDB Sentences table entries
4. DynamoDB LLMCallLog entries
5. Step Functions execution history
