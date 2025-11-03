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

## 📝 Notes for Frontend Team

1. **Polling Interval:** Poll status every 5 seconds, not faster
2. **Timeout:** Pre-signed URLs expire in 1 hour
3. **File Size:** No explicit limit, but Lambda timeout is 15 minutes
4. **File Format:** Currently only `.txt` files trigger processing
5. **Job ID:** Always save the job_id from upload response

---

## ❌ CRITICAL: KG EXTRACTION NOT WORKING (2025-11-03)

### Working Components:
- ✅ Upload API (`POST /upload`)
- ✅ File upload to S3
- ✅ S3 trigger fires automatically
- ✅ Status API (`GET /status/{job_id}`)
- ✅ Docs API (`GET /docs`)
- ✅ Sentence splitting (LLM call successful)

### Broken Components:
- ❌ **KG Extraction Pipeline FAILING**
- ❌ All KG extraction steps return error: `"list indices must be integers or slices, not str"`
- ❌ No knowledge graph data generated
- ❌ S3 buckets empty (no graphs, no temp_kg data)
- ❌ All sentences stuck at `kg_status: "pending"`

### Test Evidence (Job: `ee4173b2-2941-4c07-83f9-2df48bdd9af3`):
```
Input: "Rama teaches Sita. Sita learns quickly."
Step Function: SUCCEEDED (but with errors)
Output: {"map_results": [[{"status": "error", "error": "list indices must be integers or slices, not str"}]]}
```

### Storage Structure (Expected but NOT Created):
```
s3://knowledge-graph-{account}-{region}/
├── graphs/
│   └── {sentence_hash}.gpickle          ← NetworkX graph (nodes + edges)
├── temp_kg/
│   └── {sentence_hash}/
│       ├── entities.json                 ← Entity extraction results
│       ├── events.json                   ← Event/Kriya extraction
│       ├── relations.json                ← Relations between entities
│       └── attributes.json               ← Entity attributes
└── prompts/                              ← LLM prompts (exists)
```

### Graph Structure (When Working):
**Nodes:**
- Entity nodes: `{text: "Krishna", type: "PERSON"}`
- Event nodes: `{instance_id: "evt_1", kriya_concept: "teaches"}`
- Attribute nodes: `{value: "blue", attribute_type: "color"}`

**Edges:**
- Karaka links: Event → Entity (role: "karta", "karma", etc.)
- Relations: Entity → Entity (type: "teaches", "fights")
- Attributes: Entity → Attribute

**Format:** NetworkX DiGraph serialized with pickle

### Root Cause:
Lambda functions in Step Function Map state receiving incorrect event structure. The Map iterator is not passing sentence objects correctly to child Lambdas.

### Impact:
**NO KNOWLEDGE GRAPH DATA IS BEING CREATED**. The system only performs sentence splitting. All downstream KG operations (entity extraction, event detection, graph building) are non-functional.

**Recommendation:** DO NOT integrate frontend until KG extraction is fixed. APIs work but produce no usable output.
