## API Reference for KarakaKG Service

This document maps the API routes exposed by the Serverless backend to their HTTP methods, request and response shapes, example calls, and which frontend component should use each route. I ran live tests against the deployed endpoint listed in `cdk-outputs-backend.json` (ApiUrl).

Base API URL (from CDK outputs):

```
https://k25fzxzgqi.execute-api.us-east-1.amazonaws.com/prod/
```

---

### 1) POST /upload
- Purpose: Create a new Document job and return a pre-signed S3 upload URL.
- Request:
  - Headers: `Content-Type: application/json`
  - Body: { "filename": "yourfile.txt" }
- Example request body:

```json
{ "filename": "test-e2e-doc.txt" }
```
- Successful response (200):

```json
{
  "message": "Pre-signed URL generated successfully.",
  "job_id": "b5bc288e-938b-427c-8bf4-62835987fdb6",
  "pre_signed_url": "https://raw-documents-...s3.amazonaws.com/...",
  "s3_key": "<s3-key>"
}
```
- Notes: The `pre_signed_url` is a full PUT/POST URL — the frontend should upload the file directly to S3 using that URL. The returned `job_id` is used for status checks and processing.
- Frontend component: `DocumentList` upload button + `DocumentStatus` (to monitor job_id)

---

### 2) GET /status/{job_id}
- Purpose: Get current status and progress of a document/job.
- Request: path param `job_id`
- Example call: `GET /status/b5bc288e-938b-427c-8bf4-62835987fdb6`
- Successful response (200):

```json
{
  "job_id": "b5bc288e-938b-427c-8bf4-62835987fdb6",
  "filename": "test-e2e-doc.txt",
  "status": "PENDING_UPLOAD",
  "total_sentences": 0,
  "completed_sentences": 0,
  "llm_calls_made": 0,
  "created_at": "",
  "progress_percentage": 0
}
```
- Notes: `status` values seen: `PENDING_UPLOAD`, `processing_kg`, `completed`, `validating` (when triggered). The frontend should poll this endpoint every 5s while processing.
- Frontend component: `DocumentStatus`

---

### 3) GET /docs
- Purpose: List all uploaded documents and lightweight metadata (job_id, filename, status).
- Request: none
- Example response (200):

```json
{
  "data": [
    { "filename": { "S": "test2.txt" }, "job_id": { "S": "..." }, "status": { "S": "completed" }},
    ...
  ],
  "pagination": { "total": 6, "limit": 20 }
}
```
- Notes: The response uses DynamoDB-style typed attributes (S/ N) in current implementation. The frontend should map these to plain JS objects for display.
- Frontend component: `DocumentList`

---

### 4) POST /query
- Purpose: Synchronous query + answer synthesis (synthesize_answer Lambda). Used for quick questions returning an answer immediately.
- Request:
  - Headers: `Content-Type: application/json`
  - Body: { "query": "Who worked at the Berlin Institute?" }
- Example request body:

```json
{ "query": "Who worked at the Berlin Institute?" }
```
- Successful response (200) — example returned during live test:

```json
{
  "answer": "<reasoning>... synthesized answer text ...",
  "references": []
}
```
- Notes: The `references` array contains supporting evidence when available. This endpoint is synchronous and will attempt to return the synthesized answer in-line. Use for chat-style quick queries when low latency is desired.
- Frontend component: `ChatInterface` (synchronous query flow)

---

### 5) POST /query/submit
- Purpose: Submit an asynchronous query job (stores a Query and starts processing via `QueryProcessor`).
- Request body: the lambda expects a field named `question` (not `query`). If you pass `query` you will get a `400: question is required` response.
- Example request body (correct):

```json
{ "question": "List notable researchers at the Berlin Institute" }
```
- Error response when `question` missing (400):

```json
{ "error": "question is required" }
```
- Notes: On success the API returns a `query_id` (and maybe polling details). The frontend should POST here to start a long-running query and then poll `/query/status/{query_id}`.
- Frontend component: `ChatInterface` (async query/submit flow)

---

### 6) GET /query/status/{query_id}
- Purpose: Polling endpoint to retrieve the status and final answer of an async query submitted to `/query/submit`.
- Request: path param `query_id`
- Response: (typical shape)

```json
{
  "query_id": "<id>",
  "status": "pending|running|completed|failed",
  "answer": "...",
  "references": [ ... ]
}
```
- Notes: Use 2s polling intervals while waiting for an answer.
- Frontend component: `ChatInterface`

---

### 7) GET /processing-chain/{doc_id}
- Purpose: Observability endpoint that returns the processing chain / LLM gate logs for a given document/job.
- Example response (successful) should include a timeline of LLM calls, pipeline stages, and brief excerpts. In live testing this endpoint returned an internal server error (502) for one sample doc — indicates a lambda error or missing logs.
- Frontend component: `DocumentStatus` (processing chain view)

---

### 8) GET /sentence-chain/{sentence_hash}
- Purpose: Return the LLM chain and KG snippet for a single sentence identified by its hash.
- Request: path param `sentence_hash`
- Response: should include the `kg_snippet` nodes/edges and the extraction timeline.
- Frontend component: `DocumentStatus` -> supporting evidence panel

---

### 9) POST /trigger/{job_id}
- Purpose: Manual trigger to (re-)start processing for a job; useful when uploads aren't triggering S3 lambda events or for manual retries.
- Example response (200):

```json
{
  "message": "Processing triggered successfully",
  "job_id": "b5bc288e-938b-427c-8bf4-62835987fdb6",
  "status": "validating"
}
```
- Notes: This calls the `ManualTrigger` lambda which invokes `SanitizeDoc` and may start the Step Function. Use this for debugging or manual replays.
- Frontend component: `DocumentStatus` (manual trigger button)

---

Notes and Observations from live tests
- The deployed API URL in `cdk-outputs-backend.json` responded and permitted POST /upload, POST /query, GET /docs, GET /status and POST /trigger.
- `POST /upload` returned a pre-signed S3 URL and `job_id`. After upload, a subsequent `GET /status/{job_id}` will reflect `PENDING_UPLOAD` until the file is PUT to the presigned URL.
- `POST /query/submit` expects the field `question` (not `query`). Passing `query` leads to 400 `{"error": "question is required"}`.
- `GET /processing-chain/{doc_id}` returned `502 Internal server error` for one doc when tested — likely a lambda-side error; check CloudWatch logs for `GetProcessingChain` or the lambda implementation if you need to debug.

Security / Auth
- Currently the API is publicly reachable (no Authorization header required during these tests), but check your deployment and API Gateway stage for any usage plan or CORS restrictions the frontend may need.

How frontend should integrate (quick checklist)
- Upload flow: call `POST /upload` → receive `pre_signed_url` + `job_id` → PUT file to `pre_signed_url` → call `POST /trigger/{job_id}` (or wait for S3 event) → poll `GET /status/{job_id}` until `completed`.
- Chat (sync): call `POST /query` with `{query}` and render `answer` and `references`.
- Chat (async): call `POST /query/submit` with `{question}` to get a `query_id`, poll `GET /query/status/{query_id}` until `completed`.
- Docs list: call `GET /docs` to populate the left sidebar.

Where to look for details in the codebase
- API routes are registered in `nvidia_aws_agentic_ai/serverless_stack.py` (see `api.root.add_resource(...)` and `add_method(...)`).
- Lambda handlers are in `src/lambda_src/*` (e.g. `job_mgmt`, `rag`, `api_tools` subfolders).

Next steps / Recommendations
- Update `QuerySubmit` frontend code to send `question` as the field name.
- Add small response normalization helpers to the frontend to convert DynamoDB-typed objects into plain objects.
- For `/processing-chain` errors, check Lambda CloudWatch logs for `GetProcessingChain` and fix any marshalling exceptions.

---

If you'd like, I can:
- Create a small Postman collection / HTTPie script with the tested requests and the captured responses.
- Add a minimal frontend helper file (`frontend/src/lib/api.ts`) showing typed TypeScript wrappers for these endpoints.

End of `API_REFERENCE.md`
