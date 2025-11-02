### **Phase 0: Setup & Prerequisites (Your Starting Point)**

* **1. AWS Setup:**
    * [ ] Get your AWS Access Key and Secret Key for an IAM User.
    * [ ] **Crucial:** Configure your AWS CLI with these keys (`aws configure`). Grant this IAM User permissions for S3, DynamoDB, Lambda, EKS, ECR, API Gateway, and Step Functions.
* **2. NVIDIA Setup:**
    * [ ] Get the NVIDIA API key for accessing `nvcr.io`.
* **3. Local Environment Setup:**
    * [ ] Create a project folder and a Python virtual environment (`python -m venv venv`).
    * [ ] Install necessary tools: AWS CLI, `kubectl`, `eksctl`, Docker.
    * [ ] Install necessary Python libraries: `boto3`, `requests`, `networkx`, `flask` (or `fastapi`).
* **4. Code Repository:**
    * [ ] Create a Git repository (e.g., on GitHub) to manage your code.

### **Phase 1: Backend - Core AWS Infrastructure (The "Foundation")**

* **1. S3 Bucket:**
    * [ ] Create one S3 bucket (e.g., `your-hackathon-bucket`).
    * [ ] Create folders inside it: `uploads/`, `results/`, `llm_responses/`.
* **2. DynamoDB Table 1: `DocumentJobs`**
    * [ ] Create a DynamoDB table named `DocumentJobs`.
    * [ ] **Primary Key:** `doc_id` (String).
    * [ ] **Attributes:** `status`, `hash`, `filename`, `s3_location`, `error_message`.
    * [ ] **Global Secondary Index (GSI):** Create a GSI named `hash-index` with the partition key `hash` (String). This is critical for the duplicate file check.
* **3. DynamoDB Table 2: `SentenceCache`**
    * [ ] Create a DynamoDB table named `SentenceCache`.
    * [ ] **Primary Key:** `sentence_hash` (String).
    * [ ] **Attributes:** `kg_fragment` (String, you will store JSON here), `llm_output`.
* **4. IAM Roles (Essential for AWS services to talk to each other):**
    * [ ] Create `LambdaExecutionRole` with permissions to:
        * Read/Write to both DynamoDB tables.
        * Read/Write to your S3 bucket.
        * Write to CloudWatch Logs.
    * [ ] Create `StepFunctionRole` with permission to:
        * Invoke your Lambda functions.

### **Phase 2: Backend - The LLM Service (EKS)**

* **1. Containerize Your Model:**
    * [ ] Write a simple Python web server (e.g., using **FastAPI**) with a `/reason` endpoint.
    * [ ] This server should load the model (using your NVIDIA key) and process input JSON.
    * [ ] Write a `Dockerfile` to package this server.
* **2. Deploy Container to ECR (Elastic Container Registry):**
    * [ ] Create an ECR repository.
    * [ ] Build your Docker image and push it to this ECR repository.
* **3. Provision EKS Cluster:**
    * [ ] Use `eksctl` to create a basic EKS cluster, making sure to request **GPU-enabled nodes** (e.g., `g4dn.xlarge`).
* **4. Deploy to EKS:**
    * [ ] Write a Kubernetes `deployment.yaml` to run your ECR image on the cluster.
    * [ ] Write a Kubernetes `service.yaml` of type `LoadBalancer`. This creates a public AWS Load Balancer.
    * [ ] Apply both YAML files (`kubectl apply -f .`).
* **5. Get Endpoint:**
    * [ ] Run `kubectl get services`. Wait for the `LoadBalancer` to get an "EXTERNAL-IP".
    * [ ] This URL is your `EKS_LLM_ENDPOINT`. Test it with Postman or `curl`.

### **Phase 3: Backend - The Asynchronous Workflow (Lambdas & Step Functions)**

* **1. Create Lambda Functions (Modular Logic):**
    * [ ] **`L1_CreateUploadJob`:**
        * Input: `{"filename": "...", "hash": "..."}`.
        * Logic: Checks DynamoDB `hash-index`.
        * If hash exists: Returns `{ "status": "PROCEEDED", "doc_id": "..." }` (Cache Hit).
        * If hash is new: Generates a `doc_id` (UUID), saves to `DocumentJobs` (status: `PENDING_UPLOAD`), generates an S3 pre-signed `upload_url`, and returns `{ "doc_id": "...", "upload_url": "..." }`.
    * [ ] **`L2_StartStepFunction`:**
        * **Trigger:** S3 Event Notification (for `ObjectCreated` in the `uploads/` folder).
        * Logic: Gets `doc_id` from the S3 file path and starts the Step Function execution.
    * [ ] **`L3_UpdateStatus`:**
        * A generic function. Input: `{"doc_id": "...", "new_status": "..."}`.
        * Logic: Updates the `status` for that `doc_id` in the `DocumentJobs` table.
    * [ ] **`L4_RunVerification`:**
        * Logic: Downloads file from S3, calls `EKS_LLM_ENDPOINT`, saves raw response to S3, returns `{ "verification_status": "OK" }` or `{ "verification_status": "FAILED" }`.
    * [ ] **`L5_RunProcessing` (The Core "KG" Builder):**
        * Logic:
            1.  Downloads file.
            2.  Splits into sentences.
            3.  For each sentence:
            4.  Computes `sentence_hash`.
            5.  Checks `SentenceCache` table.
            6.  **Cache Miss:** Runs the 10-20 LLM calls (to `EKS_LLM_ENDPOINT`), saves result to `SentenceCache`.
            7.  **Cache Hit:** Pulls from `SentenceCache`.
            8.  Adds nodes/edges to an in-memory `networkx` graph, including `APPEARS_IN` edges.
            9.  Saves the final graph file (e.g., `graph.json`) to the `results/` folder in S3.
    * [ ] **`L6_GetStatus`:**
        * Input: `doc_id` (from API Gateway path).
        * Logic: Queries `DocumentJobs` table, returns the `status`.
    * [ ] **`L7_ListDocs`:**
        * Logic: Scans `DocumentJobs` table, returns all items (fine for a hackathon).
* **2. Package Lambdas:**
    * [ ] Create a folder for each Lambda.
    * [ ] **Important:** Put your `prompts.yaml` file *inside* the ZIP package for `L4_RunVerification` and `L5_RunProcessing` so it can be read locally.
    * [ ] Upload all Lambda functions to AWS.
* **3. Define the Step Function:**
    * [ ] In the AWS console, create a new State Machine.
    * [ ] Visually drag or write JSON to define the workflow:
        * `Start` -> `UpdateStatusToVerifying` (calls `L3_UpdateStatus`)
        * -> `RunVerification` (calls `L4_RunVerification`). **Add a `Retry` block and a `Catch` block here.**
        * -> `Choice (IsVerified?)`
            * `OK` -> `UpdateStatusToProcessing` (calls `L3_UpdateStatus`) -> `RunProcessing` (calls `L5_RunProcessing`). **Also add `Retry/Catch` here.** -> `UpdateStatusToSucceeded` (calls `L3_UpdateStatus`) -> `End`
            * `FAILED` -> `UpdateStatusToUnsupported` (calls `L3_UpdateStatus`) -> `End`
        * **Error Path:** The `Catch` blocks should all go to a final `UpdateStatusToFailed` (calls `L3_UpdateStatus`) -> `End`


### **Phase 4: Backend - The API Layer (API Gateway)**

* **1. Create a new REST API:**
    * [ ] `POST /documents`:
        * Integration: `L1_CreateUploadJob` (Lambda Proxy).
    * [ ] `GET /documents/{doc_id}/status`:
        * Integration: `L6_GetStatus` (Lambda Proxy).
    * [ ] `GET /documents`:
        * Integration: `L7_ListDocs` (Lambda Proxy).
* **2. Enable CORS:**
    * [ ] On your API Gateway, enable CORS for all methods. This is *essential* for your web frontend to be able to call it.
* **3. Deploy API:**
    * [ ] Deploy your API to a stage (e.g., `v1`).
    * [ ] You will now have a public **Invoke URL**. This is your main API endpoint.

### **Phase 5: Frontend - Client Application (The UI)**

* **1. Setup:**
    * [ ] Create `index.html`, `style.css`, `app.js`.
    * [ ] Include a JavaScript MD5 library (like `spark-md5.min.js`).
* **2. On Page Load (`app.js`):**
    * [ ] Call `GET {Your_Invoke_URL}/documents`.
    * [ ] Render the list of existing documents and their statuses.
* **3. File Upload Flow (`app.js`):**
    * [ ] Add an event listener to your `<input type="file">`.
    * [ ] **When a file is selected:**
        1.  Show a "Checking file..." spinner.
        2.  Read the file *in the browser* and use the JS library to **compute its MD5 hash**.
        3.  Call `POST {Your_Invoke_URL}/documents` with the `filename` and `hash`.
        4.  **Handle Response:**
            * **If `status` is returned:** Cache hit. Show "File already processed." Stop.
            * **If `upload_url` is returned:** New file. Proceed.
        5.  Show "Uploading file...".
        6.  Use `fetch()` to send a `PUT` request **to the `upload_url`** (this is the direct-to-S3 part) with the file as the body.
        7.  **On `PUT` Success:** Show "Processing started." and add the doc to your UI list with status "PENDING".
        8.  Begin polling.
* **4. Status Polling (`app.js`):**
    * [ ] Create a function `startPolling(doc_id)`.
    * [ ] Use `setInterval()` to call `GET {Your_Invoke_URL}/documents/{doc_id}/status` every 10 seconds.
    * [ ] Update the status in the UI.
    * [ ] Stop the interval when status is `PROCEEDED`, `FAILED`, or `UNSUPPORTED`.

### **Phase 6: Integration & Testing**

* [ ] Test the `EKS_LLM_ENDPOINT` independently.
* [ ] Test each Lambda independently in the AWS console.
* [ ] Test the full, end-to-end flow from the frontend.
    * Upload a small file.
    * Upload a duplicate file (test the hash check).
    * Upload a file with similar sentences (test the sentence cache).
* [ ] Prepare your demo!