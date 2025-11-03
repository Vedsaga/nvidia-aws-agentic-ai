This is a high-stakes, 5-hour sprint. The plan you have is excellent but needs more granular, step-by-step instructions for the agents (or yourselves) to execute flawlessly.

Here is the hyper-detailed, click-by-click execution plan. It incorporates the **critical fixes** (SFN concurrency, deduplication) and provides the exact logic for each Lambda.

**Your Goal:** A working demo of `GET /docs`, `GET /docs/{job_id}/status`, and `POST /query`.

## 🎉 IMPLEMENTATION STATUS SUMMARY

**✅ COMPLETED TASKS:**
- **P0: CRITICAL FIXES** - All CDK concurrency, deduplication, and embedding fixes implemented and deployed
- **P1: CORE APIs** - All 3 target APIs (`GET /docs`, `GET /docs/{job_id}/status`, `POST /query`) are implemented and working
- **P2: INGESTION FLOW** - Complete document processing pipeline from upload to Step Functions
- **P3: RAG & KG AGENTS** - All 6 KG extraction agents (l9-l14) and RAG components implemented

**⚠️ PARTIALLY COMPLETED:**
- **P4: OBSERVABILITY** - API endpoints exist but l19/l20 are stub implementations
- **Graph Operations** - l15/l16 are stub implementations (not critical for demo)

**🚀 DEMO READY:** The core functionality is complete and deployed. All target APIs are working.

-----

## 🎯 BACKEND (SERVERLESS) TASK LIST (5-Hour Plan)

### P0: CRITICAL FIXES (Est: 60 Mins) - **✅ COMPLETED**

This entire plan fails if you skip this. Your SFN will fail 66% of the time.

1.  **Fix CDK Concurrency (10 mins)**

      * [x] Open `serverless_stack.py`.
      * [x] Find the `sfn.Map` state (`ProcessAllSentencesMap`).
      * [x] Change **`max_concurrency=3`** to **`max_concurrency=1`**.
      * [x] Add a comment: `# MUST BE 1. This map processes 1 sentence, which spawns ~6 parallel agents. max_concurrency > 1 will overload l7_llm_call (limit 3).`

2.  **Fix CDK Dedup Bug (30 mins)**

      * [x] Open `serverless_stack.py`.
      * [x] **Add the missing `l5_check_dedup` Lambda:** Copy the CDK code for `l4_list_all_docs`, paste it, and change the ID and code path:
        ```python
        l5_check_dedup = _lambda.Function(
            self,
            "CheckDedupTask", # Renamed for clarity
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "job_mgmt", "l5_check_dedup") # Path from your tree
            ),
            timeout=Duration.minutes(1),
            memory_size=512,
            environment={
                "SENTENCES_TABLE": sentences_table.table_name
            },
        )
        ```
      * [x] **Add to `all_functions` list:** Add `l5_check_dedup` to the `all_functions` list so it gets DDB permissions.
      * [x] **Fix SFN:** Find `check_dedup_task = tasks.LambdaInvoke(...)`.
      * [x] Change `lambda_function=get_sentences_from_s3` to `lambda_function=l5_check_dedup`.

3.  **Fix CDK Embedding Bug (10 mins)**

      * [x] Open `serverless_stack.py`.
      * [x] Find `parallel_entities_kriya = sfn.Parallel(...)`.
      * [x] Add a new branch to it:
        ```python
        .branch(
            tasks.LambdaInvoke(self, "EmbeddingTask",
                lambda_function=embedding_call,
                payload_response_only=True
            )
        )
        ```

4.  **Deploy (10 mins)**

      * [x] Run `cdk deploy ServerlessStack`.

-----

### P1: IMPLEMENT CORE APIs (Est: 120 Mins) - **✅ COMPLETED**

**1. `l7_llm_call` (The Gateway) (60 mins)**

  * [x] Open `src/lambda_src/llm_gateway/l7_llm_call/lambda_function.py`.
  * [x] **Imports:** `import requests, boto3, os, json, datetime, uuid, time`.
  * [x] **Get Env Vars:** `LOG_TABLE = os.environ['LLM_CALL_LOG_TABLE']`, `KG_BUCKET = os.environ['KG_BUCKET']`, `GENERATE_ENDPOINT = "http://..."`.
  * [x] **Handler Logic:**
    1.  Parse `event`: `job_id`, `sentence_hash`, `prompt_name`, `stage`, `inputs_dict`.
    2.  `call_id = str(uuid.uuid4())`, `start_time = time.time()`.
    3.  **Load Prompt:** `s3.get_object(Bucket=KG_BUCKET, Key=f'prompts/{prompt_name}.txt')`... `prompt_template = ...read().decode('utf-8')`.
    4.  **Format Prompt:** `formatted_prompt = prompt_template.format(**inputs_dict)`.
    5.  **Log Request:** `dynamodb.put_item(TableName=LOG_TABLE, Item={... 'call_id': call_id, 'job_id': job_id, 'sentence_hash': sentence_hash, 'stage': stage, 'prompt_template': prompt_name, 'timestamp': int(start_time * 1000), 'status': 'pending'})`.
    6.  **Make HTTP Call:** `response = requests.post(GENERATE_ENDPOINT, json={'inputs': formatted_prompt, 'parameters': {...}})`. (Check your model's *exact* JSON schema).
    7.  `latency_ms = int((time.time() - start_time) * 1000)`.
    8.  **Log Response:** `dynamodb.update_item(...)` for `call_id` to set `status='success'`, `response_json=response.json()`, `latency_ms=latency_ms`.
    9.  **Return:** `return response.json()`.

**2. `l4_list_all_docs` (`GET /docs`) (30 mins)**

  * [x] Open `.../job_mgmt/l4_list_all_docs/lambda_function.py`.
  * [x] **Logic:**
    1.  `response = dynamodb.scan(TableName=os.environ['JOBS_TABLE'], Limit=20, Select='SPECIFIC_ATTRIBUTES', AttributesToGet=['job_id', 'filename', 'status', 'preview_text', 'created_at'])`.
    2.  Format as `{"data": response['Items'], "pagination": {}}`.
    3.  Return 200 OK.

**3. `l3_update_doc_status_api` (`GET /docs/{job_id}/status`) (30 mins)**

  * [x] Open `.../job_mgmt/l3_update_doc_status/lambda_function.py`.
  * [x] **Logic:**
    1.  `job_id = event['pathParameters']['job_id']`.
    2.  `doc_response = dynamodb.get_item(TableName=os.environ['JOBS_TABLE'], Key={'job_id': {'S': job_id}})` (Get `filename`, `status`, `total_sentences`).
    3.  `llm_count_res = dynamodb.query(TableName=os.environ['LLM_LOG_TABLE'], IndexName='ByJobId', KeyConditionExpression='job_id = :jid', ExpressionAttributeValues={':jid': {'S': job_id}}, Select='COUNT')`.
    4.  `sentence_count_res = dynamodb.query(TableName=os.environ['SENTENCES_TABLE'], IndexName='ByJobId', KeyConditionExpression='job_id = :jid', FilterExpression='kg_status = :done', ExpressionAttributeValues={...}, Select='COUNT')`.
    5.  Combine all 4 pieces into the final JSON and return 200 OK.

-----

### P2: IMPLEMENT INGESTION FLOW (Est: 60 Mins) - **✅ COMPLETED**

**1. `l2_validate_doc` (15 mins)**

  * [x] Open `.../job_mgmt/l2_validate_doc/lambda_function.py`.
  * [x] **Logic:**
    1.  Parse S3 event: `bucket = event['Records'][0]['s3']['bucket']['name']`, `key = event['Records'][0]['s3']['object']['key']`.
    2.  `job_id = key.split('.')[0]` (Assuming `job_id.txt`).
    3.  `dynamodb.update_item(TableName=os.environ['JOBS_TABLE'], Key={'job_id': {'S': job_id}}, UpdateExpression='SET #s = :stat', ExpressionAttributeNames={'#s': 'status'}, ExpressionAttributeValues={':stat': {'S': 'validating'}})`
    4.  Invoke `l3`: `lambda.invoke(FunctionName=os.environ['SANITIZE_LAMBDA_NAME'], InvocationType='Event', Payload=json.dumps({'job_id': job_id, 's3_key': key, 's3_bucket': bucket}))`.

**2. `l3_sanitize_doc` (20 mins)**

  * [x] Open `.../job_mgmt/l3_sanitize_doc/lambda_function.py`.
  * [x] **Logic:**
    1.  Get `job_id`, `s3_key`, `s3_bucket` from `event`.
    2.  Read file: `s3.get_object(Bucket=s3_bucket, Key=s3_key)`.
    3.  Split: `sentences = re.split(r'(?<=[.!?])\s+', text)`.
    4.  Create list: `sentence_list = [{'text': s, 'hash': hashlib.sha256(s.encode()).hexdigest(), 'job_id': job_id} for s in sentences]`.
    5.  Save JSON: `s3.put_object(Bucket=os.environ['VERIFIED_BUCKET'], Key=f'{job_id}/sentences.json', Body=json.dumps(sentence_list))`.
    6.  Update `DocumentJobs`: `update_item` to set `status: 'processing_kg'`, `total_sentences: len(sentence_list)`.
    7.  Start SFN: `sfn.start_execution(stateMachineArn=os.environ['STATE_MACHINE_ARN'], input=json.dumps({'job_id': job_id, 's3_path': f'{job_id}/sentences.json'}))`.

**3. `l8_get_sentences_from_s3` (10 mins)**

  * [x] Open `.../job_mgmt/l8_get_sentences_from_s3/lambda_function.py`.
  * [x] **Logic:**
    1.  Get `s3_path` from `event`.
    2.  Read file: `s3.get_object(Bucket=os.environ['VERIFIED_BUCKET'], Key=s3_path)`.
    3.  `data = json.loads(body)`.
    4.  Return `{'sentences': data}`.

**4. `l5_check_dedup` (The Fix Logic) (15 mins)**

  * [x] Open `.../job_mgmt/l5_check_dedup/lambda_function.py`.
  * [x] **Logic:**
    1.  Input is SFN Map item: `event = {'text': ..., 'hash': 'abc...', 'job_id': 'xyz...'}`.
    2.  `hash = event['hash']`, `job_id = event['job_id']`.
    3.  `response = dynamodb.get_item(TableName=os.environ['SENTENCES_TABLE'], Key={'sentence_hash': {'S': hash}})`
    4.  If `'Item'` in response:
          * If `response['Item']['kg_status']['S'] == 'kg_done'`:
              * *(Optional - skip for time)* Update `documents` list.
              * Return `{'kg_status': 'kg_done'}`.
    5.  *Else (Item not found or not done):*
          * `dynamodb.put_item(TableName=..., Item={... 'sentence_hash': hash, 'kg_status': 'pending', 'documents': [{'S': job_id}]})`
          * Return `{'kg_status': 'pending'}`.

-----

### P3: IMPLEMENT RAG & KG AGENTS (Est: 60 Mins) - **✅ COMPLETED**

**1. `l8_embedding_call` (10 mins)**

  * [x] Open `.../llm_gateway/l8_embedding_call/lambda_function.py`.
  * [x] **Logic:**
    1.  `EMBED_ENDPOINT = "http://..."`.
    2.  Input is `event`: `{'text': ..., 'hash': ..., 'job_id': ...}`.
    3.  `response = requests.post(EMBED_ENDPOINT, json={'text': event['text']})`.
    4.  Save vector to S3: `s3.put_object(Bucket=os.environ['KG_BUCKET'], Key=f'embeddings/{event["hash"]}.npy', Body=...)`.
    5.  Return `{'status': 'success'}`.

**2. `l9_extract_entities` (The Template) (15 mins)**

  * [x] Open `.../kg_agents/l9_extract_entities/lambda_function.py`.
  * [x] **Logic:**
    1.  `LLM_LAMBDA = os.environ['LLM_CALL_LAMBDA_NAME']`.
    2.  `event` is the SFN Map item. `text = event['text']`, `hash = event['hash']`, `job_id = event['job_id']`.
    3.  `payload = {'job_id': job_id, 'sentence_hash': hash, 'stage': 'D1_Entities', 'prompt_name': 'entity_prompt.txt', 'inputs': {'SENTENCE_HERE': text}}`.
    4.  `response = lambda.invoke(FunctionName=LLM_LAMBDA, Payload=json.dumps(payload))`.
    5.  `llm_output = json.loads(response['Payload'].read())`.
    6.  Save: `s3.put_object(Bucket=os.environ['KG_BUCKET'], Key=f'temp_kg/{hash}/entities.json', Body=json.dumps(llm_output))`.
    7.  Return `{'status': 'success'}`.

**3. `l10-l14` (KG Agents) (15 mins)**

  * [x] **Copy-paste** the `l9` logic into `l10`, `l11`, `l12`, `l13`, `l14`.
  * [x] **Change only** the `stage`, `prompt_name`, and `output_path` for each.
      * `l10_extract_kriya`: `stage: 'D2a_Kriya'`, `prompt_name: 'kriya_concept_prompt.txt'`, `output_path: '.../kriya.json'`.
      * ...and so on for all 6 agents.

**4. `l17_retrieve_from_embedding` (10 mins)**

  * [x] Open `.../rag/l17_retrieve_from_embedding/lambda_function.py`.
  * [x] **Logic:**
    1.  `query = event['query']`, `doc_ids = event['doc_ids']`.
    2.  Invoke `l8_embedding_call` to get query vector.
    3.  **MVP HACK:** Load all `.npy` vectors from `kg-bucket/embeddings/`. (FAISS is too slow to build).
    4.  Calculate cosine similarity, find Top 30 hashes.
    5.  **Filter:** Loop Top 30, `GetItem` from `SentencesTable`. Check if `item['documents']` list contains any `doc_ids`. Keep Top 3.
    6.  Return `['hash1', 'hash2', 'hash3']`.

**5. `l18_synthesize_answer` (`POST /query`) (10 mins)**

  * [x] Open `.../rag/l18_synthesize_answer/lambda_function.py`.
  * [x] **Logic:**
    1.  `body = json.loads(event['body'])`, `query = body['query']`, `doc_ids = body['doc_ids']`.
    2.  Invoke `l17`: `response = lambda.invoke(l17, ...)` -\> `['hash1', 'hash2']`.
    3.  **Build Context:** Loop hashes. `GetItem` from `SentencesTable` (for text). `s3.get_object` from `temp_kg/{hash}/entities.json` + `.../events.json`. (Prune here\!)
    4.  **Format Prompt:** Use `answer_synthesizer_prompt.txt` (from `prompts/`).
    5.  **Invoke `l7_llm_call`** with the full context.
    6.  Format the final 200 OK API response with `answer` and `references`.

-----

### P4: OBSERVABILITY (Est: 30 Mins) - **⚠️ PARTIALLY COMPLETED**

  * [ ] **`l19_get_processing_chain` (`GET /docs/{job_id}/chain`)** - **STUB ONLY**
      * `job_id = event['pathParameters']['doc_id']`.
      * `Query` `LLMCallLog` GSI `ByJobId`, sort by `timestamp`.
      * Return 200 OK with `{"data": response['Items']}`.
  * [ ] **`l20_get_sentence_chain` (`GET /sentences/{hash}/chain`)** - **STUB ONLY**
      * `hash = event['pathParameters']['sentence_hash']`.
      * `Query` `LLMCallLog` GSI `BySentenceHash`, sort by `timestamp`.
      * Return 200 OK with `{"data": response['Items']}`.