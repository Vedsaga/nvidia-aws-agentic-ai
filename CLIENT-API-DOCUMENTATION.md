# Client API Documentation

## Base URL
```
https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod
```

## ✅ Working APIs (Tested & Verified)

### 1. Upload Document
**Endpoint:** `POST /upload`

**Description:** Get a pre-signed URL to upload a document

**Request:**
```bash
curl -X POST "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/upload" \
  -H "Content-Type: application/json" \
  -d '{"filename": "my-document.txt"}'
```

**Request Body:**
```json
{
  "filename": "my-document.txt"
}
```

**Response (200 OK):**
```json
{
  "message": "Pre-signed URL generated successfully.",
  "job_id": "39a624ec-85af-4372-ac20-3cc2c1637efe",
  "pre_signed_url": "https://raw-documents-151534200269-us-east-1.s3.amazonaws.com/...",
  "s3_key": "39a624ec-85af-4372-ac20-3cc2c1637efe/my-document.txt"
}
```

**Next Step:** Upload file to the pre-signed URL
```bash
curl -X PUT --upload-file my-document.txt "<pre_signed_url>"
```

**Status:** ✅ WORKING
- Generates unique job_id
- Creates pre-signed S3 URL (valid for 1 hour)
- Creates job entry in DynamoDB with status `PENDING_UPLOAD`

---

### 2. Get All Documents
**Endpoint:** `GET /docs`

**Description:** List all uploaded documents

**Request:**
```bash
curl "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/docs"
```

**Response (200 OK):**
```json
{
  "data": [
    {
      "filename": {"S": "api-test.txt"},
      "job_id": {"S": "39a624ec-85af-4372-ac20-3cc2c1637efe"},
      "status": {"S": "processing_kg"}
    },
    {
      "filename": {"S": "trigger-test.txt"},
      "job_id": {"S": "d110a076-d160-464a-854b-8a7a4435e78d"},
      "status": {"S": "processing_kg"}
    }
  ],
  "pagination": {
    "total": 11,
    "limit": 20
  }
}
```

**Status:** ✅ WORKING
- Returns all jobs from DynamoDB
- Shows current status for each document
- Includes pagination info

**Note:** Response format uses DynamoDB notation (`{"S": "value"}`). Frontend should parse this.

---

### 3. Get Document Status
**Endpoint:** `GET /status/{job_id}`

**Description:** Get detailed status of a specific document

**Request:**
```bash
curl "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/status/39a624ec-85af-4372-ac20-3cc2c1637efe"
```

**Response (200 OK):**
```json
{
  "job_id": "39a624ec-85af-4372-ac20-3cc2c1637efe",
  "filename": "api-test.txt",
  "status": "processing_kg",
  "total_sentences": 2,
  "completed_sentences": 0,
  "llm_calls_made": 0,
  "created_at": "",
  "progress_percentage": 0.0
}
```

**Status:** ✅ WORKING
- Returns clean JSON (not DynamoDB format)
- Shows processing progress
- Includes sentence count

**Status Values:**
- `PENDING_UPLOAD` - Waiting for file upload
- `validating` - File uploaded, validating
- `processing_kg` - Extracting knowledge graph
- `completed` - Processing finished
- `error` - Processing failed

---

## 📋 Complete Upload Flow

### Step 1: Request Upload URL
```bash
curl -X POST "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/upload" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.txt"}'
```

**Save the response:**
- `job_id` - Use this to check status
- `pre_signed_url` - Use this to upload file

### Step 2: Upload File
```bash
curl -X PUT --upload-file test.txt "<pre_signed_url_from_step_1>"
```

**Expected:** HTTP 200 or 204 response

### Step 3: Check Status (Poll every 5 seconds)
```bash
curl "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/status/<job_id_from_step_1>"
```

**Status progression:**
```
PENDING_UPLOAD → validating → processing_kg → completed
```

### Step 4: Monitor Progress
```bash
# Keep polling status endpoint
while true; do
  curl -s "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/status/<job_id>" | jq
  sleep 5
done
```

---

## 🧪 Test Example

```bash
# 1. Upload
RESPONSE=$(curl -s -X POST "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/upload" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.txt"}')

JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
UPLOAD_URL=$(echo $RESPONSE | jq -r '.pre_signed_url')

echo "Job ID: $JOB_ID"

# 2. Create test file
echo "Krishna guides Arjuna. Arjuna fights bravely." > test.txt

# 3. Upload file
curl -X PUT --upload-file test.txt "$UPLOAD_URL"

# 4. Wait and check status
sleep 5
curl -s "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/status/$JOB_ID" | jq

# 5. List all docs
curl -s "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/docs" | jq
```

---

## ⚠️ Known Issues

### Issue 1: Processing Stuck at 0%
**Symptom:** Status shows `processing_kg` but `llm_calls_made: 0`

**Cause:** KG extraction pipeline may not be fully functional

**Workaround:** Check Step Functions execution in AWS Console

### Issue 2: DynamoDB Format in /docs
**Symptom:** Response has `{"S": "value"}` format

**Solution:** Frontend should parse DynamoDB notation:
```javascript
const filename = item.filename.S;
const status = item.status.S;
```

---

## 📊 Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (missing filename) |
| 404 | Job not found |
| 500 | Internal server error |

---

## 🔒 CORS Headers

All endpoints include CORS headers:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

---

## 🔍 Query API (NEW - Working)

### 1. Submit Query
**Endpoint:** `POST /query/submit`

**Description:** Submit a question to query the knowledge base

**Request:**
```bash
curl -X POST "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/query/submit" \
  -H "Content-Type: application/json" \
  -d '{"question": "Who eats mango?"}'
```

**Request Body:**
```json
{
  "question": "Who eats mango?"
}
```

**Response (200 OK):**
```json
{
  "query_id": "390630b0-2efb-4e76-a019-66a3da58c30e",
  "question": "Who eats mango?",
  "status": "processing"
}
```

**Status:** ✅ WORKING

---

### 2. Get Query Status/Answer
**Endpoint:** `GET /query/status/{query_id}`

**Description:** Get the answer for a submitted query

**Request:**
```bash
curl "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/query/status/390630b0-2efb-4e76-a019-66a3da58c30e"
```

**Response (200 OK - Processing):**
```json
{
  "query_id": "390630b0-2efb-4e76-a019-66a3da58c30e",
  "question": "Who eats mango?",
  "status": "processing"
}
```

**Response (200 OK - Completed):**
```json
{
  "query_id": "390630b0-2efb-4e76-a019-66a3da58c30e",
  "question": "Who eats mango?",
  "status": "completed",
  "answer": "Rama eats mango. (doc1:s4)",
  "references": [
    {
      "sentence_text": "Rama eats mango. ",
      "sentence_hash": "e8e902adacf4c1f83ccfaea24805be62755b766e8075c05588aab02f4384fe5c",
      "doc_id": "ee516097-f99b-47e6-a702-7930cec9343c",
      "kg_snippet": {
        "nodes": [
          {
            "id": "Rama",
            "node_type": "entity",
            "sentence_hash": "e8e902adacf4c1f83ccfaea24805be62755b766e8075c05588aab02f4384fe5c",
            "sentence_text": "Rama eats mango. ",
            "job_id": "ee516097-f99b-47e6-a702-7930cec9343c"
          },
          {
            "id": "mango",
            "node_type": "entity",
            "sentence_hash": "e8e902adacf4c1f83ccfaea24805be62755b766e8075c05588aab02f4384fe5c",
            "sentence_text": "Rama eats mango. ",
            "job_id": "ee516097-f99b-47e6-a702-7930cec9343c"
          }
        ],
        "edges": [
          {
            "source": "Rama",
            "target": "mango",
            "edge_type": "karaka",
            "relation": "eat",
            "karaka_role": "Agent->Object",
            "sentence": "Rama eats mango. ",
            "sentence_hash": "e8e902adacf4c1f83ccfaea24805be62755b766e8075c05588aab02f4384fe5c"
          }
        ]
      }
    }
  ]
}
```

**Status:** ✅ WORKING

**Query Status Values:**
- `processing` - Query is being processed
- `completed` - Answer ready
- `error` - Query failed

---

## 📝 Notes for Frontend Team

1. **Polling Interval:** Poll status every 3-5 seconds
2. **Timeout:** Pre-signed URLs expire in 1 hour
3. **File Size:** No explicit limit, but Lambda timeout is 15 minutes
4. **File Format:** Currently only `.txt` files trigger processing
5. **Job ID:** Always save the job_id from upload response
6. **Query Processing:** Queries typically complete in 5-10 seconds
7. **KG References:** Each answer includes full knowledge graph snippets with entities and relations
8. **Embedding Search:** Uses semantic similarity (not keyword matching) for better retrieval

---

## ✅ WORKING: Complete RAG Pipeline with Knowledge Graph (2025-11-03)

### All Components Working:
- ✅ Upload API (`POST /upload`)
- ✅ File upload to S3
- ✅ S3 trigger fires automatically
- ✅ Status API (`GET /status/{job_id}`)
- ✅ Docs API (`GET /docs`)
- ✅ Sentence splitting (LLM call)
- ✅ **KG Extraction Pipeline (Entity + Kriya + Events + Relations)**
- ✅ **NetworkX Graph Storage**
- ✅ **Sentence Embeddings (llama-3.2-nv-embedqa-1b-v2)**
- ✅ **Query API with Embedding Similarity Search**
- ✅ **Answer Synthesis with KG Context**

### Test Evidence (Job: `ee516097-f99b-47e6-a702-7930cec9343c`):
```
Input: "Rama eats mango."
Processing: COMPLETED
Query: "Who eats mango?"
Answer: "Rama eats mango. (doc1:s4)"
References: Full KG with nodes (Rama, mango) and edge (Rama-eat->mango)
```

### Storage Structure (Fully Functional):
```
s3://knowledge-graph-{account}-{region}/
├── graphs/
│   └── {sentence_hash}.gpickle          ← NetworkX graph (nodes + edges)
├── embeddings/
│   └── {sentence_hash}.npy              ← Sentence embeddings (2048-dim)
├── temp_kg/
│   └── {sentence_hash}/
│       ├── entities.json                 ← Entity extraction results
│       ├── events.json                   ← Event/Kriya extraction
│       └── relations.json                ← Relations between entities
└── prompts/                              ← LLM prompts
```

### Graph Structure:
**Nodes:**
- Entity nodes: `{id: "Rama", node_type: "entity", sentence_text: "...", job_id: "..."}`

**Edges:**
- Karaka links: `{source: "Rama", target: "mango", edge_type: "karaka", relation: "eat", karaka_role: "Agent->Object"}`

**Format:** NetworkX DiGraph serialized with pickle

### Query Flow:
1. Generate query embedding using llama-3.2-nv-embedqa-1b-v2
2. Calculate cosine similarity with all sentence embeddings
3. Retrieve top 3 similar sentences
4. Load NetworkX graphs for retrieved sentences
5. Extract sentence text and KG from graph nodes
6. Build context with entities and relations
7. Pass to LLM for answer synthesis
8. Return answer with full KG references

### Status Values:
- `PENDING_UPLOAD` - Waiting for file upload
- `validating` - File uploaded, validating
- `processing_kg` - Extracting knowledge graph
- `completed` - Processing finished ✅
- `error` - Processing failed
