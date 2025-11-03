# KG Extraction Implementation Summary

## ✅ What Was Implemented

### 1. Prompt Template Fixes
**Fixed:** All prompts now use single braces `{VARIABLE}` instead of `{{VARIABLE}}`

**Files Updated:**
- `prompts/entity_prompt.txt` - `{SENTENCE_HERE}`
- `prompts/kriya_concept_prompt.txt` - `{SENTENCE_HERE}`
- `prompts/event_instance_prompt.txt` - `{SENTENCE_HERE}`, `{ENTITY_LIST_JSON}`, `{KRIYA_LIST_JSON}`
- `prompts/relation_prompt.txt` - `{SENTENCE_HERE}`, `{ENTITY_LIST_JSON}`, `{EVENT_INSTANCES_JSON}`
- `prompts/attribute_prompt.txt` - `{SENTENCE_HERE}`, `{ENTITY_LIST_JSON}`, `{EVENT_INSTANCES_JSON}`
- `prompts/auditor_prompt.txt` - `{SENTENCE_HERE}`, `{EVENT_INSTANCES_JSON}`
- `prompts/answer_synthesizer_prompt.txt` - `{QUERY}`, `{CONTEXT}`

### 2. Lambda Input Chaining
**Fixed:** Lambdas now load previous outputs and pass them to prompts

**L11 Build Events:**
```python
# Loads entities from L9 and kriya from L10
'inputs': {
    'SENTENCE_HERE': text,
    'ENTITY_LIST_JSON': json.dumps(entities_data, indent=2),
    'KRIYA_LIST_JSON': json.dumps(kriya_data, indent=2)
}
```

**L12 Audit Events:**
```python
# Loads events from L11
'inputs': {
    'SENTENCE_HERE': text,
    'EVENT_INSTANCES_JSON': json.dumps(events_data, indent=2)
}
```

**L13 Extract Relations:**
```python
# Loads entities from L9 and events from L11
'inputs': {
    'SENTENCE_HERE': text,
    'ENTITY_LIST_JSON': json.dumps(entities_data, indent=2),
    'EVENT_INSTANCES_JSON': json.dumps(events_data, indent=2)
}
```

**L14 Extract Attributes:**
```python
# Loads entities from L9 and events from L11
'inputs': {
    'SENTENCE_HERE': text,
    'ENTITY_LIST_JSON': json.dumps(entities_data, indent=2),
    'EVENT_INSTANCES_JSON': json.dumps(events_data, indent=2)
}
```

### 3. NetworkX Graph Storage (L15/L16)

**L15 Graph Node Ops:**
- Creates NetworkX DiGraph
- Adds entity nodes with attributes (type, entity_type, sentence_hash, job_id)
- Adds event instance nodes with attributes (kriya_concept, surface_text, prayoga)
- Saves as pickled graph to `graphs/{sentence_hash}_nodes.gpickle`

**L16 Graph Edge Ops:**
- Loads graph from L15
- Adds Karaka edges (event → entity with role)
- Adds relation edges (entity/event → entity/event with relation_type)
- Adds attribute edges (entity/event → attribute node)
- Saves complete graph to `graphs/{sentence_hash}.gpickle`
- Updates sentence status to `kg_done` in DynamoDB

### 4. Embedding Storage (L8)
**Already Working:**
- Generates embeddings via NVIDIA NIM
- Saves as `.npy` files in `embeddings/{sentence_hash}.npy`

## 📊 Complete Pipeline Flow

```
Document Upload
    ↓
L2: ValidateDoc (S3 trigger)
    ↓
L3: SanitizeDoc (Split sentences)
    ↓
Step Functions (for each sentence):
    ↓
Parallel:
├─ L9: Extract Entities → entities.json
├─ L10: Extract Kriya → kriya.json
└─ L8: Generate Embedding → {hash}.npy
    ↓
L11: Build Events (uses entities + kriya) → events.json
    ↓
L12: Audit Events (uses events) → audit.json
    ↓
Parallel:
├─ L13: Extract Relations (uses entities + events) → relations.json
└─ L14: Extract Attributes (uses entities + events) → attributes.json
    ↓
Parallel:
├─ L15: Graph Node Ops → {hash}_nodes.gpickle
└─ L16: Graph Edge Ops → {hash}.gpickle + update DynamoDB
```

## 🗂️ Storage Structure

```
S3: knowledge-graph-{account}-{region}/
├── embeddings/
│   └── {sentence_hash}.npy          # Numpy embedding vector
│
├── temp_kg/{sentence_hash}/
│   ├── entities.json                # L9 output
│   ├── kriya.json                   # L10 output
│   ├── events.json                  # L11 output
│   ├── audit.json                   # L12 output
│   ├── relations.json               # L13 output
│   └── attributes.json              # L14 output
│
├── graphs/
│   ├── {sentence_hash}_nodes.gpickle  # L15 intermediate
│   └── {sentence_hash}.gpickle        # L16 final graph
│
└── prompts/
    └── *.txt                        # All prompt templates
```

## ⚠️ Current Issue

**Status:** LLM calls still at 0

**Possible Causes:**
1. **NVIDIA NIM endpoints not responding** - Check if LLM/embedding endpoints are running
2. **Lambda timeout** - Check CloudWatch logs for errors
3. **Step Functions not starting** - Check SFN execution status
4. **Prompt loading error** - Check if prompts synced to S3

## 🔍 Debugging Steps

### 1. Check NVIDIA NIM Endpoints
```bash
# Check LLM endpoint
curl -X POST "http://a72a7b27168ef4f2f825fe7aae9ce8ed-2069339664.us-east-1.elb.amazonaws.com:80/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model": "nvidia/llama-3.1-nemotron-nano-8b-v1", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}'

# Check embedding endpoint
curl -X POST "http://ac5f3892aa1654ccbb5e6e97382f31f8-582704769.us-east-1.elb.amazonaws.com:80/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"model": "nvidia/llama-3.2-nv-embedqa-1b-v2", "input": "test", "input_type": "passage"}'
```

### 2. Check Step Functions Execution
```bash
# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:151534200269:stateMachine:KarakaKGProcessing \
  --max-results 5

# Get execution details
aws stepfunctions describe-execution \
  --execution-arn <execution_arn>
```

### 3. Check CloudWatch Logs
```bash
# Check L3 SanitizeDoc logs
aws logs tail /aws/lambda/ServerlessStack-SanitizeDoc* --since 10m

# Check L9 ExtractEntities logs
aws logs tail /aws/lambda/ServerlessStack-ExtractEntities* --since 10m

# Check L7 LLMCall logs
aws logs tail /aws/lambda/ServerlessStack-LLMCall* --since 10m
```

### 4. Check Prompts in S3
```bash
# List prompts
aws s3 ls s3://knowledge-graph-151534200269-us-east-1/prompts/

# Download and verify a prompt
aws s3 cp s3://knowledge-graph-151534200269-us-east-1/prompts/entity_prompt.txt -
```

### 5. Check DynamoDB LLMCallLog
```bash
# Scan for recent calls
aws dynamodb scan --table-name LLMCallLog \
  --filter-expression "job_id = :jid" \
  --expression-attribute-values '{":jid":{"S":"87f24e1f-8bac-4900-b6e9-974ef007b3c7"}}' \
  --limit 10
```

## 📝 Next Steps

1. **Verify NVIDIA NIM endpoints are running**
   - Check EKS cluster status
   - Verify pods are running
   - Test endpoints directly

2. **Check Step Functions execution**
   - Verify SFN is starting
   - Check which step is failing
   - Review error messages

3. **Review CloudWatch logs**
   - Look for Lambda errors
   - Check timeout issues
   - Verify prompt loading

4. **Test individual components**
   - Test L7 LLM call directly
   - Test L9 entity extraction
   - Verify prompt formatting

## ✅ What's Confirmed Working

- ✅ Upload API
- ✅ Status API
- ✅ Docs API
- ✅ S3 trigger
- ✅ Sentence splitting
- ✅ Prompt templates fixed
- ✅ Lambda input chaining implemented
- ✅ NetworkX graph storage implemented
- ✅ Embedding storage implemented

## ❌ What Needs Verification

- ❌ NVIDIA NIM endpoints responding
- ❌ Step Functions executing
- ❌ LLM calls succeeding
- ❌ Graph files being created
- ❌ Embeddings being generated

## 🎯 Success Criteria

When working, you should see:
1. `llm_calls_made` increasing (0 → 6 → 12 for 2 sentences)
2. Files in `temp_kg/{hash}/` (entities.json, kriya.json, etc.)
3. Files in `graphs/{hash}.gpickle`
4. Files in `embeddings/{hash}.npy`
5. Sentence status changing to `kg_done` in DynamoDB
