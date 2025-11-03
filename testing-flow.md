This is the most critical part: **a systematic test plan to be 100% sure your backend works** before the frontend team (or you) tries to integrate.

Here is the step-by-step checklist. **Do not skip any steps.**

### **Prerequisites**

  * **API URL:** Have your API Gateway URL ready (e.g., `https://{api_id}.execute-api.../prod`).
  * **Test File:** Have a simple, 2-sentence file ready at `test-files/test-doc-1.txt`.
      * *Content:* `Rama eats mango. Sita sings.`
  * **AWS Console:** Have S3, DynamoDB, and Step Functions open in separate tabs.

-----

### **Phase 1: Ingestion (Test `l1`, `l4`)**

*Goal: Prove a file can be uploaded and appears in the document list.*

  * [ ] **Test `POST /upload` (L1)**

      * **Action:** Run this `curl` command.
        ```bash
        curl -X POST "https://{api_id}.execute-api.../prod/upload" \
        -d '{"filename": "test-doc-1.txt", "md5_hash": "dummy-hash-for-test"}'
        ```
      * **✅ Verify (Response):** Get a `200 OK`. The response JSON includes a `job_id` and a long `upload_url`.
      * **ACTION:** **Copy the `job_id`** to your notepad.
      * **ACTION:** **Copy the entire `upload_url`** to your notepad.

  * [ ] **Verify `l1` DDB State**

      * **Action:** Go to DynamoDB \> `DocumentJobs` table.
      * **✅ Verify:** A new item exists with your `job_id`. Its `status` is **`pending_upload`**.

  * [ ] **Test S3 `PUT`**

      * **Action:** Run this `curl` command, pasting your `upload_url`.
        ```bash
        # Make sure to use 'PUT', not 'POST'
        curl -X PUT --upload-file "test-files/test-doc-1.txt" "PASTE_YOUR_UPLOAD_URL_HERE"
        ```
      * **✅ Verify (Response):** Get a `200 OK` (or `204`) from S3.
      * **✅ Verify (S3):** Go to S3 \> `raw-documents` bucket. The file `test-doc-1.txt` (or `{job_id}.txt`) exists.

  * [ ] **Test `GET /docs` (L4)**

      * **Action:** Wait \~5 seconds for the S3 trigger. Run this `curl` command.
        ```bash
        curl "https://{api_id}.execute-api.../prod/docs"
        ```
      * **✅ Verify (Response):** Get a `200 OK`. The `data` array in the JSON **contains your new `job_id`**. The `status` is likely **`validating`**.

**🏁 Phase 1 Complete: Ingestion API is working.**

-----

### **Phase 2: Processing (Test `l2`, `l3`, `l8-s3`, `l5`, SFN, `l9-l16`, `l8-embed`)**

*Goal: Prove the S3 trigger starts the SFN, and the *entire* SFN pipeline runs successfully.*

  * [ ] **Test SFN Trigger (L2, L3, L8)**

      * **Action:** Go to the AWS Step Functions Console \> `KarakaKGProcessing`.
      * **✅ Verify (SFN):** A new execution is **"Running"**. Click it.
      * **✅ Verify (DDB):** Go to `DocumentJobs`. Find your `job_id`. The `status` is now **`processing_kg`** and `total_sentences` is **`2`**.
      * **✅ Verify (S3):** Go to `verified-bucket`. A file named **`{job_id}/sentences.json`** now exists.

  * [ ] **Test SFN Map Execution (The Core Pipeline)**

      * **Action:** Stay on the SFN "Graph inspector" page and watch.
      * **✅ Verify (SFN):** `GetSentencesTask` (L8) turns **Green**.
      * **✅ Verify (SFN):** `ProcessAllSentencesMap` (the map) turns **Blue** (In Progress), then **Green**.
      * **✅ Verify (SFN Loop 1 - "Rama eats mango"):**
          * `CheckDedupTask` (L5) runs, returns `{"kg_status": "pending"}`.
          * `DedupChoice` takes the **`otherwise`** branch.
          * `ParallelEntitiesKriya` (L9, L10) & `EmbeddingTask` (L8) all run and turn **Green**.
          * `l11`...`l16` (the rest of the agents) all turn **Green**.
      * **✅ Verify (SFN Loop 2 - "Sita sings"):**
          * The same flow (L5 -\> L9...L16) runs and turns **Green**.
      * **✅ Verify (SFN Final):** The entire SFN execution status is **"Succeeded"**.

  * [ ] **Test Artifacts (The Results)**

      * **Action:** The SFN is "Succeeded". Now check the outputs.
      * **✅ Verify (S3 `knowledge-graph`):**
          * `embeddings/` folder: Contains two `.npy` files (one for each sentence hash).
          * `temp_kg/` folder: Contains two subfolders (one for each hash).
          * `temp_kg/{hash1}/`: Contains all 6 JSONs (`entities.json`, `kriya.json`, etc.).
      * **✅ Verify (DDB `SentencesTable`):**
          * Contains two new items (one for each hash).
          * Their `kg_status` is **`pending`** (set by L5, which is correct for this flow).
      * **✅ Verify (DDB `LLMCallLog`):**
          * Contains **12** new items (2 sentences \* 6 KG agents).
          * The `stage` column shows `D1_Entities`, `D2a_Kriya`, etc.
          * *(You should also see logs for the `EmbeddingTask` if you added logging there).*

**🏁 Phase 2 Complete: Core pipeline is working.**

-----

### **Phase 3: Status & Observability (Test `l3-api`, `l19`)**

*Goal: Prove the frontend polling APIs work and reflect the completed job.*

  * [ ] **Test `GET /docs/{job_id}/status` (L3-API)**

      * **Action:** Run this `curl` command (use your `job_id`):
        ```bash
        curl "https://{api_id}.execute-api.../prod/docs/{job_id}/status"
        ```
      * **✅ Verify (Response):** Get a `200 OK`. The JSON shows:
          * `"total_sentences": 2`
          * `"processed_sentences": 2` (or `0` if you forgot to update the status in the SFN, but `total_llm_calls` is the key)
          * `"total_llm_calls": 12`

  * [ ] **Test `GET /docs/{job_id}/chain` (L19)**

      * **Action:** Run this `curl` command:
        ```bash
        curl "https://{api_id}.execute-api.../prod/docs/{job_id}/chain"
        ```
      * **✅ Verify (Response):** Get a `200 OK`. The `data` array contains **12** log objects, sorted by `timestamp`.

**🏁 Phase 3 Complete: Observability APIs are working.**

-----

### **Phase 4: Query (Test `l18`, `l17`, `l8`, `l7`)**

*Goal: Prove the entire RAG + KG flow works and returns the demo answer.*

  * [ ] **Test `POST /query` (The Final Boss)**

      * **Action:** Run this `curl` command, pasting your `job_id`:
        ```bash
        curl -X POST "https://{api_id}.execute-api.../prod/query" \
        -d '{"query": "Who eats mango?", "doc_ids": ["{YOUR_JOB_ID_HERE}"]}'
        ```
      * **✅ Verify (Response):** Get a `200 OK`. The JSON response contains:
          * `"answer": "Rama..."` (or similar synthesized answer).
          * `"references"`: An array with **1 item**.
          * `references[0].sentence_text`: **`"Rama eats mango."`**
          * `references[0].doc_id`: Your `job_id`.
          * `references[0].kg_snippet`: A JSON object containing the pruned `nodes` and `edges` (from `entities.json` and `events.json`).

  * [ ] **Test Final Log**

      * **Action:** Go to DDB `LLMCallLog` table.
      * **✅ Verify:** There is **one new item** (for a total of 13). Its `stage` is **`RAG_Synthesize`**.

**🏁 Phase 4 Complete: Your demo is working.**