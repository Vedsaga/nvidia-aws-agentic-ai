# Kāraka RAG System - Deployment Guide

## Quick Start

### Full Deployment (SageMaker + Infrastructure)
```bash
./deploy.sh --env personal
```

### SageMaker Endpoints Only
```bash
./deploy.sh --env personal --sagemaker-only
```

### Skip SageMaker (Use existing endpoints)
```bash
./deploy.sh --env personal --skip-sagemaker
```

### Deploy and Test
```bash
./deploy.sh --env personal --test
```

### Cleanup All Resources
```bash
./deploy.sh --cleanup
```

## Prerequisites

1. **AWS Marketplace Subscriptions** (Required for SageMaker):
   - [Llama 3.1 Nemotron Nano 8B](https://aws.amazon.com/marketplace/ai/procurement?productId=prod-dqa44sfw3zyfm)
   - [NV-EmbedQA 1B v2](https://aws.amazon.com/marketplace/ai/procurement?productId=f2e6a2fd-2aec-4344-8efb-9d46172f4468)

2. **Environment File**: Create `.env.personal` with:
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
EXECUTION_ROLE_ARN=arn:aws:iam::ACCOUNT_ID:role/KarakaRAGSageMakerRole
```

## Deployment Steps

The unified script handles:
1. ✅ SageMaker NVIDIA NIM endpoints (Nemotron + EmbedQA)
2. ✅ S3 bucket creation
3. ✅ IAM roles
4. ✅ Lambda functions (4)
5. ✅ API Gateway
6. ✅ Neo4j EC2 instance

## Important Notes

- **Instance Type**: Uses `ml.g6e.2xlarge` (NVIDIA NIM requirement)
- **Deployment Time**: 30-50 minutes (20-40 min for SageMaker)
- **Cost**: Monitor SageMaker endpoint costs

## Endpoints

After deployment:
- **API Gateway**: Check `.env.personal` for `API_GATEWAY_URL`
- **Neo4j**: `bolt://PUBLIC_IP:7687`
- **SageMaker**: `nemotron-karaka-endpoint`, `embedding-karaka-endpoint`
