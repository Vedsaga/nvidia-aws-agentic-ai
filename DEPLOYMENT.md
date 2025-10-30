# Deployment Guide for Judges

## Important Notice

**You do NOT need to use our deployed infrastructure.** According to the [official contest rules](https://nvidia-aws.devpost.com/rules), judges will deploy and test the project using their own AWS credentials and SageMaker/EKS endpoints.

This guide provides complete instructions for judges to:
1. Configure the project with their own AWS credentials
2. Deploy NVIDIA NIM models to their own SageMaker or EKS endpoints
3. Test the complete system
4. Clean up resources to avoid charges

## Prerequisites

### Required
- AWS Account with appropriate permissions
- Python 3.8 or higher
- AWS CLI (recommended but optional)

### AWS Permissions Required
- SageMaker: Create/manage endpoints and models
- Lambda: Create/manage functions
- API Gateway: Create/manage REST APIs
- EC2: Launch instances (for Neo4j)
- S3: Create/manage buckets
- IAM: Create/manage roles (if not pre-configured)

### Recommended for Testing
- Docker Desktop (for local testing before AWS deployment)
- 8GB+ RAM, 20GB+ disk space

## Deployment Options

### Option A: Quick Local Testing (Recommended First)

Test the system locally before deploying to AWS. This helps verify functionality without incurring AWS costs.

#### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd <repository-name>
```

#### Step 2: Local Deployment (Lightweight Mode)
```bash
# No Docker required - uses local Python models
python deploy_local.py --lightweight
```

This will:
- Check system requirements
- Create Python virtual environment
- Install dependencies
- Configure local environment

#### Step 3: Test Locally
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run end-to-end tests
python test_e2e.py --mode local
```

#### Step 4: Cleanup Local Environment
```bash
python deploy_local.py --destroy
```

---

### Option B: AWS Deployment with Your Credentials

Deploy the complete system to AWS using your own credentials and endpoints.

## AWS Deployment Steps

### Step 1: Configure AWS Credentials

Create a `.env.personal` file in the project root:

```bash
# AWS Credentials (Required)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=your_session_token_if_using_temporary_credentials
AWS_REGION=us-east-1

# Account Information
ACCOUNT_ID=123456789012

# SageMaker Configuration
SAGEMAKER_NEMOTRON_ENDPOINT=your-nemotron-endpoint-name
SAGEMAKER_EMBEDDING_ENDPOINT=your-embedding-endpoint-name
SAGEMAKER_INSTANCE_TYPE=ml.g5.xlarge

# Neo4j Configuration (will be auto-configured during deployment)
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_secure_password_here
NEO4J_DATABASE=neo4j

# S3 Configuration (will be auto-created if not specified)
S3_BUCKET=your-unique-bucket-name-optional
```

**Important Notes:**
- Replace all example values with your actual AWS credentials
- For Vocareum labs, use `.env.vocareum` instead of `.env.personal`
- Session tokens are required for temporary credentials (like Vocareum)
- Choose a unique S3 bucket name or leave blank for auto-generation

### Step 2: Validate Configuration

Before deploying, validate your AWS credentials and configuration:

```bash
python deploy_server.py --env personal --validate-only
```

This will check:
- ✓ AWS credentials are valid and not expired
- ✓ Account access is working
- ✓ Required permissions are available
- ✓ Configuration is complete
- ✓ Any existing resources in your account

**Expected Output:**
```
Configuration Validation
============================================================

▶ Loading configuration from .env.personal
✓ Configuration loaded from .env.personal

▶ Validating AWS credentials...
✓ AWS credentials valid
  Account ID: 123456789012
  ARN: arn:aws:iam::123456789012:user/your-user

▶ Checking model configuration...
✓ Nemotron endpoint: your-nemotron-endpoint-name
✓ Embedding endpoint: your-embedding-endpoint-name
✓ Instance type: ml.g5.xlarge

▶ Checking existing AWS resources...
✓ No existing SageMaker endpoints
✓ No existing Lambda functions

✓ All validations passed!
```

### Step 3: Deploy NVIDIA NIM Models to SageMaker

The deployment script will automatically deploy NVIDIA NIM models to your SageMaker endpoints.

**Models Used:**
1. **Llama 3.1 Nemotron Nano 8B V1** - For text generation and reasoning
2. **NVIDIA Retrieval Embedding NIM** - For semantic embeddings

**Deploy to AWS:**
```bash
python deploy_server.py --env personal
```

**Deployment Process (15-20 minutes):**

1. **S3 Bucket Setup** (~30 seconds)
   - Creates S3 bucket for data storage
   - Configures bucket policies

2. **Lambda Functions** (~2 minutes)
   - Packages Lambda code with dependencies
   - Uploads to S3
   - Creates 4 Lambda functions:
     - `karaka-ingestion-handler` - Document processing
     - `karaka-query-handler` - Query processing
     - `karaka-graph-handler` - Graph visualization
     - `karaka-status-handler` - Job status tracking

3. **API Gateway** (~1 minute)
   - Creates REST API
   - Configures endpoints and integrations
   - Sets up CORS

4. **Neo4j Database** (~3 minutes)
   - Launches EC2 instance (t3.micro)
   - Installs and configures Neo4j
   - Sets up security groups

5. **SageMaker Endpoints** (~15 minutes)
   - Creates endpoint configurations
   - Deploys Nemotron model (ml.g5.xlarge)
   - Deploys Embedding model (ml.g5.xlarge)
   - Waits for endpoints to be InService

**Expected Output:**
```
Kāraka RAG System - AWS Deployment
============================================================

Environment: .env.personal
AWS Account: 123456789012
Region: us-east-1

Step 1: Deploy S3 Bucket
============================================================
▶ Checking S3 bucket: karaka-rag-1234567890
✓ S3 bucket created: karaka-rag-1234567890

Step 2: Deploy Lambda Functions
============================================================
▶ Packaging Lambda functions...
✓ Lambda functions packaged
▶ Uploading Lambda package to S3...
✓ Lambda package uploaded

Step 3: Deploy API Gateway
============================================================
▶ Deploying API Gateway...
✓ API Gateway deployed

Step 4: Deploy Neo4j Database
============================================================
▶ Deploying Neo4j on EC2...
✓ Neo4j deployed

Step 5: Deploy SageMaker Endpoints
============================================================
▶ Deploying SageMaker endpoints...
⚠ This will take 15-20 minutes...
✓ SageMaker endpoints deployed

Deployment Complete!
============================================================

Resources Deployed:
  ✓ S3 Bucket: karaka-rag-1234567890
  ✓ API Gateway: https://abc123.execute-api.us-east-1.amazonaws.com/prod
  ✓ Neo4j: bolt://ec2-xx-xx-xx-xx.compute-1.amazonaws.com:7687
  ✓ SageMaker Endpoints:
    - Nemotron: your-nemotron-endpoint-name
    - Embedding: your-embedding-endpoint-name

Configuration saved to:
  .env.personal

API Endpoints:
  POST https://abc123.execute-api.us-east-1.amazonaws.com/prod/ingest
  GET  https://abc123.execute-api.us-east-1.amazonaws.com/prod/ingest/status/{job_id}
  POST https://abc123.execute-api.us-east-1.amazonaws.com/prod/query
  GET  https://abc123.execute-api.us-east-1.amazonaws.com/prod/graph
  GET  https://abc123.execute-api.us-east-1.amazonaws.com/prod/health

Next Steps:
  1. Test the deployment:
     curl https://abc123.execute-api.us-east-1.amazonaws.com/prod/health

  2. Update frontend .env with API_GATEWAY_URL

  3. For judges: All endpoints and credentials are in .env file
```

### Step 4: Test the Deployment

#### Quick Health Check
```bash
# Get API URL from deployment output or .env file
API_URL=$(grep API_GATEWAY_URL .env.personal | cut -d= -f2)

# Test health endpoint
curl $API_URL/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-10-30T12:00:00Z",
  "services": {
    "neo4j": "connected",
    "sagemaker": "available"
  }
}
```

#### Run End-to-End Tests
```bash
python test_e2e.py --mode server
```

**Test Coverage:**
- Document upload and ingestion
- Job status tracking
- Graph structure verification
- Query processing with Kāraka analysis
- API endpoint functionality

**Expected Output:**
```
============================================================
Kāraka RAG System - End-to-End Tests
============================================================

API URL: https://abc123.execute-api.us-east-1.amazonaws.com/prod
Mode: server

Test 1: Upload Documents
============================================================
ℹ Uploading ramayana_sample.txt...
✓ Uploaded: ramayana_sample.txt
ℹ Waiting for job abc-123...
✓ Job completed

Test 2: Verify Graph
============================================================
ℹ Verifying graph...
✓ Found 45 entities
✓ Found 67 actions
✓ Found 89 Karaka relationships

Test 3: Upload Second Document
============================================================
ℹ Uploading mahabharata_sample.txt...
✓ Uploaded: mahabharata_sample.txt
✓ Job completed

Test 4: Test Queries
============================================================
ℹ Query: Who gave bow to Rama?
✓ Answer: According to the text, Vishwamitra gave the bow to Rama...
✓ Found 3 sources

============================================================
Test Summary
============================================================

Total: 12
Passed: 12
Failed: 0
```

### Step 5: Access the System

#### API Gateway Endpoints

All endpoints are available at: `https://<api-id>.execute-api.<region>.amazonaws.com/prod`

**1. Ingest Document**
```bash
curl -X POST $API_URL/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "document_name": "test.txt",
    "content": "base64_encoded_content_here"
  }'
```

**2. Check Ingestion Status**
```bash
curl $API_URL/ingest/status/{job_id}
```

**3. Query the System**
```bash
curl -X POST $API_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Who gave the bow to Rama?",
    "min_confidence": 0.7
  }'
```

**4. Get Graph Visualization**
```bash
curl $API_URL/graph
```

#### Neo4j Browser

Access Neo4j Browser at: `http://<ec2-public-ip>:7474`

**Credentials:**
- Username: `neo4j`
- Password: (from your `.env.personal` file)

**Sample Queries:**
```cypher
// View all entities
MATCH (e:Entity) RETURN e LIMIT 25

// View all actions
MATCH (a:Action) RETURN a LIMIT 25

// View Kāraka relationships
MATCH (a:Action)-[r]->(e:Entity)
WHERE type(r) IN ['KARTA', 'KARMA', 'KARANA']
RETURN a, r, e LIMIT 50
```

### Step 6: Cleanup Resources

**IMPORTANT:** Always cleanup when done to avoid ongoing AWS charges!

```bash
python deploy_server.py --env personal --destroy
```

**Confirmation Required:**
```
Resource Cleanup
============================================================

This will DELETE all deployed resources:
  - SageMaker Endpoints (2)
  - Lambda Functions (4)
  - API Gateway
  - Neo4j EC2 Instance
  - S3 Bucket (and all data)

Type 'DELETE' to confirm: DELETE
```

**Cleanup Process:**
1. Deletes SageMaker endpoints
2. Removes Lambda functions
3. Deletes API Gateway
4. Terminates EC2 instance
5. Empties and deletes S3 bucket
6. Removes IAM roles (if created)

**Expected Output:**
```
▶ Stopping SageMaker endpoints...
✓ SageMaker endpoints deleted

▶ Removing Lambda functions...
✓ Lambda functions deleted

▶ Deleting API Gateway...
✓ API Gateway deleted

▶ Terminating Neo4j EC2 instance...
✓ EC2 instance terminated

▶ Cleaning up S3 bucket...
✓ S3 bucket deleted

✓ All resources cleaned up
```

## Alternative: Using Existing SageMaker Endpoints

If you already have NVIDIA NIM models deployed to SageMaker endpoints, you can configure the project to use them.

### Step 1: Update Configuration

Edit `.env.personal` with your existing endpoint names:

```bash
# Use your existing SageMaker endpoints
SAGEMAKER_NEMOTRON_ENDPOINT=your-existing-nemotron-endpoint
SAGEMAKER_EMBEDDING_ENDPOINT=your-existing-embedding-endpoint

# Skip SageMaker deployment
SKIP_SAGEMAKER_DEPLOYMENT=true
```

### Step 2: Deploy Other Components

```bash
# This will skip SageMaker endpoint creation
python deploy_server.py --env personal
```

The script will:
- ✓ Use your existing SageMaker endpoints
- ✓ Deploy Lambda, API Gateway, Neo4j, S3
- ✓ Configure Lambda functions to use your endpoints

## Using EKS Instead of SageMaker

If you prefer to deploy NVIDIA NIM models on EKS:

### Step 1: Deploy Models to EKS

Follow NVIDIA's EKS deployment guide to deploy:
1. Llama 3.1 Nemotron Nano 8B V1
2. NVIDIA Retrieval Embedding NIM

### Step 2: Configure Endpoints

Update `.env.personal` with your EKS service endpoints:

```bash
# EKS Configuration
USE_EKS=true
NVIDIA_API_BASE_URL=http://your-nemotron-service.eks.amazonaws.com/v1
NVIDIA_EMBEDDING_URL=http://your-embedding-service.eks.amazonaws.com/v1
NVIDIA_API_KEY=your_api_key_if_required

# Skip SageMaker deployment
SKIP_SAGEMAKER_DEPLOYMENT=true
```

### Step 3: Deploy

```bash
python deploy_server.py --env personal
```

The Lambda functions will automatically use your EKS endpoints instead of SageMaker.

## Cost Estimation

### AWS Deployment Costs (per hour)

| Service | Configuration | Cost/Hour |
|---------|--------------|-----------|
| SageMaker (Nemotron) | ml.g5.xlarge | ~$0.75 |
| SageMaker (Embedding) | ml.g5.xlarge | ~$0.75 |
| EC2 (Neo4j) | t3.micro | ~$0.01 |
| Lambda | Pay per request | ~$0.20/1M requests |
| API Gateway | Pay per request | ~$3.50/1M requests |
| S3 | Storage + requests | ~$0.023/GB |

**Total Estimated Cost:**
- **Testing (2-3 hours):** $5-10
- **Development (8 hours):** $15-20
- **Per day (if left running):** $40-50

**Cost Saving Tips:**
1. Use local testing first (free)
2. Deploy to AWS only when ready
3. Always cleanup after testing
4. Use spot instances for EC2 (if available)
5. Stop SageMaker endpoints when not in use

## Troubleshooting

### AWS Credentials Issues

**Problem:** "ExpiredToken" error
```
✗ AWS credentials invalid: ExpiredToken
```

**Solution:**
- For Vocareum: Get fresh credentials from "Cloud access" section
- For IAM users: Verify credentials haven't been rotated
- Update `.env.personal` with new credentials
- Run validation again: `python deploy_server.py --env personal --validate-only`

### SageMaker Deployment Fails

**Problem:** "ResourceLimitExceeded" or endpoint creation fails

**Solution:**
1. Check service quotas:
```bash
aws service-quotas list-service-quotas \
  --service-code sagemaker \
  --query 'Quotas[?QuotaName==`ml.g5.xlarge for endpoint usage`]'
```

2. Request quota increase if needed
3. Try different instance type: `SAGEMAKER_INSTANCE_TYPE=ml.g5.2xlarge`
4. Try different region: `AWS_REGION=us-west-2`

### Lambda Package Too Large

**Problem:** "InvalidParameterValueException: Unzipped size must be smaller than..."

**Solution:** The script automatically handles this by uploading to S3. If issues persist:
1. Check S3 bucket permissions
2. Verify Lambda has access to S3
3. Check CloudWatch logs for detailed errors

### Neo4j Connection Issues

**Problem:** Cannot connect to Neo4j

**Solution:**
1. Wait 2-3 minutes after deployment for Neo4j to fully start
2. Check security group allows your IP:
```bash
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=neo4j-sg"
```
3. Verify instance is running:
```bash
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=karaka-neo4j"
```
4. Check instance logs for errors

### API Gateway 403 Errors

**Problem:** "Missing Authentication Token" or 403 errors

**Solution:**
1. Verify API Gateway deployment:
```bash
aws apigateway get-rest-apis
```
2. Check Lambda permissions
3. Verify CORS configuration
4. Check CloudWatch logs for Lambda errors

## Verification Checklist

Before submitting or demonstrating:

- [ ] Local testing completed successfully
- [ ] AWS credentials validated
- [ ] All AWS resources deployed
- [ ] Health check endpoint returns 200
- [ ] Document ingestion works
- [ ] Query processing works
- [ ] Graph visualization works
- [ ] End-to-end tests pass
- [ ] Video demonstration recorded
- [ ] Resources cleaned up (if not needed)

## Support and Resources

### Documentation
- **NVIDIA NIM Documentation:** https://docs.nvidia.com/nim/
- **AWS SageMaker:** https://docs.aws.amazon.com/sagemaker/
- **Neo4j:** https://neo4j.com/docs/

### Logs and Debugging
- **Lambda Logs:** CloudWatch Logs → `/aws/lambda/karaka-*`
- **SageMaker Logs:** CloudWatch Logs → `/aws/sagemaker/Endpoints/*`
- **API Gateway Logs:** CloudWatch Logs → API Gateway execution logs

### Common Commands
```bash
# View Lambda logs
aws logs tail /aws/lambda/karaka-query-handler --follow

# Check SageMaker endpoint status
aws sagemaker describe-endpoint --endpoint-name your-nemotron-endpoint

# List all deployed resources
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Project,Values=karaka-rag
```

## Submission Requirements

According to the [official contest rules](https://nvidia-aws.devpost.com/rules), your submission must include:

1. **Text Description** - Project overview and features
2. **Video Demonstration** - Functioning project walkthrough
3. **Public Code Repository** - Complete source code
4. **Deployment Instructions** - This document

**You do NOT need to:**
- Keep the app deployed during judging
- Provide access to your AWS account
- Share your AWS credentials
- Maintain running infrastructure

Judges will deploy using their own AWS credentials following this guide.

---

**Questions or Issues?**

If you encounter any problems during deployment:
1. Check the troubleshooting section above
2. Review CloudWatch logs for detailed errors
3. Verify all prerequisites are met
4. Ensure AWS credentials have required permissions

**Note:** This deployment guide is designed for judges to independently deploy and test the system. All scripts are self-contained and require no external dependencies beyond AWS credentials and Python.
