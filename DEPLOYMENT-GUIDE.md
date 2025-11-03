# Deployment Guide for Judges

## Prerequisites

### 1. Required Tools & Versions
```bash
# AWS CLI
aws --version  # Tested: 2.31.16 (v2.x required)

# Node.js & npm
node --version  # Tested: v24.9.0 (v18+ required)
npm --version   # Tested: 11.6.2 (v9+ required)

# Python
python3 --version  # Tested: 3.13.7 (v3.9+ required)

# AWS CDK
npm install -g aws-cdk
cdk --version  # Tested: 2.1031.1 (v2.x required)
```

### 2. AWS Credentials Setup
Configure your AWS credentials (from Vocareum or your AWS account):
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_SESSION_TOKEN="your-session-token"  # If using temporary credentials
```

### 3. Get NVIDIA API Key
1. Visit https://build.nvidia.com
2. Sign up/login
3. Generate API key from your account settings

## Setup Steps

### Step 1: Clone Repository
```bash
git clone <your-repo-url>
cd aws-ai-agent
```

### Step 2: Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials:
nano .env  # or use any text editor
```

Required `.env` values:
```bash
AWS_ACCESS_KEY_ID="your-key"
AWS_SECRET_ACCESS_KEY="your-secret"
AWS_SESSION_TOKEN="your-token"
AWS_ACCOUNT_ID="123456789012"
AWS_REGION="us-east-1"
NVIDIA_BUILD_API_KEY="nvapi-xxx"
NVIDIA_ACCOUNT_EMAIL="your@email.com"
```

### Step 3: Install Dependencies

#### Python Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### Node Dependencies
```bash
npm install
```

#### Lambda Layer Dependencies (for packaging)
The Lambda functions use a pre-built layer with these packages:
- requests (HTTP calls to NVIDIA NIM)
- networkx (graph operations)
- numpy (numerical operations)

**Already included** in `lambda_layer/python/` - no additional installation needed.

## Deployment

### Deploy Model Stack (EKS + GPU Nodes)
**Time: ~20-25 minutes**

```bash
chmod +x deploy-model.sh
./deploy-model.sh
```

This deploys:
- EKS Cluster
- GPU Node Groups (g5.xlarge instances)
- NVIDIA NIM models (Generator + Embedder)
- Model endpoints

**Note:** This step builds Docker containers and provisions GPU infrastructure. Grab coffee ☕

### Deploy Backend Stack (Serverless)
**Time: ~5-10 minutes**

```bash
chmod +x deploy-backend.sh
./deploy-backend.sh
```

This deploys:
- Lambda functions
- DynamoDB tables
- API Gateway
- S3 buckets
- Step Functions

## Verification

### 1. Check Model Status
```bash
# Make script executable
chmod +x monitor-pods.sh

# Check if models are running
./monitor-pods.sh
```

Expected output: Both pods should show `Running` status

### 2. Test Model Endpoints
```bash
chmod +x test-model-endpoints.sh
./test-model-endpoints.sh
```

This tests:
- Generator endpoint (LLM responses)
- Embedder endpoint (vector embeddings)

### 3. Test End-to-End Flow
```bash
# Upload a test document
chmod +x test-fresh-upload.sh
./test-fresh-upload.sh

# Check processing status
python check-sentence-status.py
```

### 4. Test Query API
```bash
chmod +x test-query-api.sh
./test-query-api.sh
```

## Frontend Setup

**Note:** Frontend documentation is being finalized by the team.

For now, you can test the backend APIs directly using the scripts above. The frontend will connect to:
- Model endpoints (from `frontend/.env`)
- API Gateway (from `cdk-outputs-backend.json`)

## Troubleshooting

### Model pods not starting
```bash
# Check pod logs
kubectl get pods -n default
kubectl logs <pod-name> -n default
```

### Deployment fails
```bash
# Check CDK bootstrap
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION

# Verify credentials
aws sts get-caller-identity
```

### API Gateway errors
```bash
# Check Lambda logs in CloudWatch
aws logs tail /aws/lambda/<function-name> --follow
```

## Cleanup

To avoid charges, destroy all resources:
```bash
cdk destroy ServerlessStack
cdk destroy EksStack
```

## Architecture Overview

```
┌─────────────────┐
│   Frontend      │
│   (React)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│  API Gateway    │────▶│   Lambda     │
│                 │     │  Functions   │
└─────────────────┘     └──────┬───────┘
                               │
         ┌─────────────────────┼─────────────────┐
         ▼                     ▼                 ▼
┌─────────────────┐   ┌──────────────┐  ┌──────────────┐
│   DynamoDB      │   │  S3 Buckets  │  │ EKS Cluster  │
│   (Metadata)    │   │  (Documents) │  │ (GPU Models) │
└─────────────────┘   └──────────────┘  └──────────────┘
```

## Support

For issues during deployment:
- Check CloudWatch logs
- Verify AWS credentials are valid
- Ensure NVIDIA API key is correct
- Check AWS service quotas (especially for GPU instances)
