# Local Lambda Testing with SAM + LocalStack

Production-like local testing environment for all Lambda functions without mocks.

## Architecture

- **AWS SAM CLI**: Builds and invokes Lambda functions in Docker containers with exact AWS runtime
- **LocalStack**: Emulates DynamoDB, S3, and other AWS services locally
- **NetworkX**: Installed in Lambda layer, available to all functions
- **Docker**: Runs both SAM containers and LocalStack

## Prerequisites

```bash
# Install Docker
# https://docs.docker.com/get-docker/

# Install AWS SAM CLI
pip install aws-sam-cli

# Install LocalStack
pip install localstack

# Install AWS CLI (for LocalStack interaction)
pip install awscli
```

## Quick Start

### 1. Setup Environment

```bash
# Make scripts executable
chmod +x *.sh

# Build Lambda functions and layer
./local-test-setup.sh
```

This will:
- Build Lambda layer with `requests` and `networkx`
- Build all Lambda functions using SAM
- Package everything for local testing

### 2. Start LocalStack

```bash
# Start LocalStack with DynamoDB and S3
./start-local-env.sh
```

This will:
- Start LocalStack in Docker
- Create all DynamoDB tables (DocumentJobs, Sentences, LLMCallLog, Queries)
- Create all S3 buckets (raw-documents-local, verified-documents-local, knowledge-graph-local)

### 3. Test Lambda Functions

```bash
# Test a specific function
./test-lambda-local.sh ListAllDocs

# Test with custom event
./test-lambda-local.sh LLMCall test-events/llm-call-event.json

# Test entity extraction
./test-lambda-local.sh ExtractEntities test-events/extract-entities-event.json
```

### 4. Stop Environment

```bash
./stop-local-env.sh
```

## Available Lambda Functions

### Job Management
- `UploadHandler` - Generate S3 presigned URLs
- `ValidateDoc` - Validate uploaded documents
- `SanitizeDoc` - Sanitize and split into sentences
- `ListAllDocs` - List all documents
- `ManualTrigger` - Manually trigger processing
- `UpdateDocStatus` - Get document status
- `CheckDedup` - Check sentence deduplication
- `GetSentencesFromS3` - Retrieve sentences

### LLM Gateway
- `LLMCall` - Call LLM with prompt
- `EmbeddingCall` - Generate embeddings

### KG Agents
- `ExtractEntities` - Extract entities (D1)
- `ExtractKriya` - Extract kriya (D2a)
- `BuildEvents` - Build events (D2b)
- `AuditEvents` - Audit events
- `ExtractRelations` - Extract relations
- `ExtractAttributes` - Extract attributes
- `ScoreExtractions` - GSSR scoring

### Graph Operations
- `GraphNodeOps` - NetworkX node operations
- `GraphEdgeOps` - NetworkX edge operations

### RAG
- `RetrieveFromEmbedding` - Embedding search
- `SynthesizeAnswer` - Generate answers
- `QueryProcessor` - Process queries

### API Tools
- `QuerySubmit` - Submit query
- `QueryStatus` - Get query status
- `GetProcessingChain` - Get processing chain
- `GetSentenceChain` - Get sentence chain

## Testing Workflow

### Test Individual Lambda

```bash
# 1. Create test event
cat > test-events/my-test.json << EOF
{
  "job_id": "test-123",
  "text": "Test sentence"
}
EOF

# 2. Run test
./test-lambda-local.sh ExtractEntities test-events/my-test.json
```

### Test with LocalStack Data

```bash
# 1. Add test data to DynamoDB
aws dynamodb put-item \
  --endpoint-url http://localhost:4566 \
  --table-name DocumentJobs \
  --item '{"job_id": {"S": "test-123"}, "status": {"S": "pending"}}'

# 2. Add test file to S3
echo "Test content" > test.txt
aws s3 cp test.txt s3://raw-documents-local/ \
  --endpoint-url http://localhost:4566

# 3. Test Lambda that reads this data
./test-lambda-local.sh ValidateDoc test-events/validate-event.json
```

### Test Lambda Invocation Chain

```bash
# Test L7 (LLM Call) directly
./test-lambda-local.sh LLMCall test-events/llm-call-event.json

# Test L9 (Extract Entities) which invokes L7
./test-lambda-local.sh ExtractEntities test-events/extract-entities-event.json
```

## How It Works

### SAM Build Process

```bash
sam build
```

1. Creates `.aws-sam/build/` directory
2. For each Lambda:
   - Pulls official AWS Lambda Python 3.12 Docker image
   - Copies function code
   - Installs dependencies from requirements.txt (if exists)
   - Attaches Lambda layer (requests, networkx)
3. Result: Exact replica of AWS Lambda environment

### Local Invocation

```bash
sam local invoke FunctionName --event event.json
```

1. Starts Docker container with Lambda runtime
2. Mounts function code and layer
3. Sets environment variables from `local-env.json`
4. Executes handler
5. Returns response

### LocalStack Integration

Lambda functions check `AWS_SAM_LOCAL` environment variable:

```python
import os
import boto3

if os.environ.get('AWS_SAM_LOCAL'):
    # Local testing - use LocalStack
    s3_client = boto3.client('s3', endpoint_url='http://host.docker.internal:4566')
else:
    # Production - use real AWS
    s3_client = boto3.client('s3')
```

## Updating Lambda Functions for Local Testing

To make Lambda functions work with LocalStack, update boto3 client initialization:

```python
# Before
import boto3
s3_client = boto3.client('s3')

# After
from shared.local_aws_clients import s3_client, dynamodb_client, lambda_client
```

The shared module handles endpoint switching automatically.

## Troubleshooting

### LocalStack not starting
```bash
# Check Docker
docker ps

# Check LocalStack logs
docker logs localstack-lambda-test

# Restart
docker-compose down && docker-compose up -d
```

### Lambda can't connect to LocalStack
- Use `host.docker.internal:4566` not `localhost:4566`
- Ensure `--docker-network host` in sam invoke
- Check `local-env.json` has correct endpoints

### NetworkX not found
```bash
# Rebuild layer
rm -rf lambda_layer/python
mkdir -p lambda_layer/python
pip install networkx requests -t lambda_layer/python/

# Rebuild SAM
sam build
```

### Function timeout
- Increase timeout in `template.yaml`
- Check if LLM endpoints are accessible
- Verify LocalStack is running

## Environment Variables

All functions have access to:
- `AWS_SAM_LOCAL=true` - Indicates local testing
- `JOBS_TABLE=DocumentJobs`
- `SENTENCES_TABLE=Sentences`
- `LLM_CALL_LOG_TABLE=LLMCallLog`
- `RAW_BUCKET=raw-documents-local`
- `VERIFIED_BUCKET=verified-documents-local`
- `KG_BUCKET=knowledge-graph-local`
- `GENERATE_ENDPOINT=http://host.docker.internal:8000`
- `EMBED_ENDPOINT=http://host.docker.internal:8001`

## Next Steps

1. Update Lambda functions to use `shared/local_aws_clients.py`
2. Create comprehensive test events for each function
3. Add integration tests that chain multiple Lambdas
4. Set up CI/CD to run local tests before deployment
