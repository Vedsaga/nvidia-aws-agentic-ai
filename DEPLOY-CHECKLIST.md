# Deployment Checklist

## Pre-Deployment Verification

- [x] All code changes completed
- [x] No syntax errors (diagnostics passed)
- [x] JSON schemas match prompt outputs
- [x] Temperature values correct (0.4 for generation)
- [x] Step Functions retry logic added
- [x] All Lambda permissions configured

## Deployment Steps

### 1. Review Changes
```bash
git status
git diff
```

### 2. Deploy CDK Stack
```bash
cd /home/vedsaga/hackathon/aws-ai-agent
cdk deploy
```

**Expected output:**
- Stack update successful
- All Lambda functions updated
- Step Functions state machine updated

### 3. Verify Deployment
```bash
# Check Lambda functions exist
aws lambda list-functions --query 'Functions[?contains(FunctionName, `Extract`) || contains(FunctionName, `Score`)].FunctionName'

# Check Step Functions state machine
aws stepfunctions list-state-machines --query 'stateMachines[?contains(name, `Karaka`)].name'
```

### 4. Upload Prompts (if not already done)
```bash
# Get bucket name
BUCKET=$(aws s3 ls | grep knowledge-graph | awk '{print $3}')

# Upload prompts
aws s3 sync prompts/ s3://$BUCKET/prompts/

# Verify
aws s3 ls s3://$BUCKET/prompts/
```

### 5. Test with Sample Document
```bash
# Create test file
echo "Rama eats mango." > test-gssr.txt

# Run test script
./test-fresh-upload.sh
```

### 6. Monitor Execution

**Check Step Functions:**
```bash
# Get execution ARN from test output
# Then check status
aws stepfunctions describe-execution --execution-arn <ARN>
```

**Check CloudWatch Logs:**
```bash
# Entity extraction logs
aws logs tail /aws/lambda/ExtractEntities --follow

# Kriya extraction logs
aws logs tail /aws/lambda/ExtractKriya --follow

# Event extraction logs
aws logs tail /aws/lambda/BuildEvents --follow

# Scorer logs
aws logs tail /aws/lambda/ScoreExtractions --follow
```

**Check DynamoDB:**
```bash
# Check Sentences table
aws dynamodb scan --table-name Sentences --max-items 5

# Check LLMCallLog
aws dynamodb scan --table-name LLMCallLog --max-items 10
```

## Post-Deployment Validation

### 1. Verify GSSR Flow
Look for these log patterns:

**In l9/l10/l11 logs:**
```
Phase 1: Generating 3 JSONs for <hash>
Phase 2: Fidelity check
Phase 2a: Consensus check
Phase 3: Scoring Pass 1
Pass 1 scores: [X, Y, Z]
Phase 4: Scoring Pass 2
Pass 2 scores: [X, Y, Z]
Phase 5: Selecting best
Best score: X (JSON Y)
```

### 2. Verify Retry Logic
If scores < 70, should see:
```
All scores < 70 in Pass 1, retrying...
```

And Step Functions should loop back to same task.

### 3. Verify Consensus Optimization
If all 3 JSONs identical:
```
Consensus achieved! Score=100
```

Should skip scoring phases.

### 4. Check Database Updates

**Sentences table should have:**
- `d1_attempts` (number)
- `d2a_attempts` (number)
- `d2b_attempts` (number)
- `best_score` (number)
- `needs_review` (boolean)
- `status` (string)

**LLMCallLog should have:**
- `pipeline_stage` (D1_Entities, D2a_Kriya, D2b_Karakas, Scorer_*)
- `attempt_number` (1-5)
- `generation_index` (1-3)
- `temperature` (0.4 for generation, 0.0/0.3 for scoring)
- `raw_request` (full payload)
- `raw_response` (full response)
- `extracted_json` (parsed JSON)
- `extracted_reasoning` (reasoning block)

## Troubleshooting

### Issue: Lambda timeout
**Solution:** Increase timeout in CDK (currently 15 min)

### Issue: Scorer returns [0, 0, 0]
**Solution:** Check scorer.txt prompt format, verify LLM response parsing

### Issue: Retry not working
**Solution:** Check Step Functions Choice state conditions, verify Lambda returns `{'status': 'retry'}`

### Issue: Fidelity check always fails
**Solution:** Check entity text extraction, verify case-insensitive matching

### Issue: Consensus never achieved
**Solution:** Check JSON serialization with sort_keys=True, verify LLM consistency

## Rollback Plan

If deployment fails or issues found:

```bash
# Rollback CDK stack
cdk deploy --rollback

# Or restore previous version
git checkout <previous-commit>
cdk deploy
```

## Success Criteria

✅ Deployment successful if:
1. All Lambda functions updated without errors
2. Step Functions state machine updated
3. Test document processes successfully
4. GSSR flow logs appear in CloudWatch
5. Sentences table updated with attempts and scores
6. LLMCallLog has enhanced metadata
7. Graph nodes/edges created correctly

## Next Actions After Successful Deployment

1. Monitor first few documents for quality
2. Check average scores and retry rates
3. Review sentences with `needs_review = TRUE`
4. Optimize prompts based on scorer feedback
5. Adjust temperature/thresholds if needed
