#!/bin/bash
set -e

echo "=== Karaka RAG System Deployment ==="

# Check .env file
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Copy .env.example to .env and configure it"
    exit 1
fi

# Load environment variables
source .env

# Check required variables
if [ -z "$AWS_REGION" ] || [ -z "$S3_BUCKET" ] || [ -z "$NEO4J_URI" ]; then
    echo "Error: Required environment variables not set"
    echo "Check AWS_REGION, S3_BUCKET, NEO4J_URI in .env"
    exit 1
fi

echo "AWS Region: $AWS_REGION"
echo "S3 Bucket: $S3_BUCKET"

# Create S3 bucket if it doesn't exist
echo ""
echo "=== Creating S3 Bucket ==="
if aws s3 ls "s3://$S3_BUCKET" 2>/dev/null; then
    echo "Bucket $S3_BUCKET already exists"
else
    aws s3 mb "s3://$S3_BUCKET" --region "$AWS_REGION"
    echo "Created bucket: $S3_BUCKET"
fi

# Deploy SageMaker endpoints (optional - comment out if already deployed)
# echo ""
# echo "=== Deploying SageMaker Endpoints ==="
# python3 infrastructure/deploy_sagemaker.py
# echo "Update .env with endpoint names from above"

# Package Lambda functions
echo ""
echo "=== Packaging Lambda Functions ==="
./infrastructure/package_lambda.sh

# Deploy Lambda functions
echo ""
echo "=== Deploying Lambda Functions ==="

LAMBDA_ROLE_ARN="${LAMBDA_ROLE_ARN:-}"
if [ -z "$LAMBDA_ROLE_ARN" ]; then
    echo "Error: LAMBDA_ROLE_ARN not set in .env"
    echo "Create an IAM role with Lambda, S3, SageMaker, and Neo4j permissions"
    exit 1
fi

# Deploy ingestion lambda
INGESTION_ARN=$(aws lambda create-function \
    --function-name karaka-rag-ingestion \
    --runtime python3.11 \
    --role "$LAMBDA_ROLE_ARN" \
    --handler lambda.ingestion_handler.lambda_handler \
    --zip-file fileb://lambda.zip \
    --timeout 900 \
    --memory-size 1024 \
    --environment "Variables={AWS_REGION=$AWS_REGION,S3_BUCKET=$S3_BUCKET,NEO4J_URI=$NEO4J_URI,NEO4J_USER=$NEO4J_USER,NEO4J_PASSWORD=$NEO4J_PASSWORD,NEMOTRON_ENDPOINT=$NEMOTRON_ENDPOINT,EMBEDDING_ENDPOINT=$EMBEDDING_ENDPOINT}" \
    --query 'FunctionArn' --output text 2>/dev/null || \
    aws lambda update-function-code \
    --function-name karaka-rag-ingestion \
    --zip-file fileb://lambda.zip --query 'FunctionArn' --output text)

echo "Ingestion Lambda: $INGESTION_ARN"

# Deploy query lambda
QUERY_ARN=$(aws lambda create-function \
    --function-name karaka-rag-query \
    --runtime python3.11 \
    --role "$LAMBDA_ROLE_ARN" \
    --handler lambda.query_handler.lambda_handler \
    --zip-file fileb://lambda.zip \
    --timeout 300 \
    --memory-size 512 \
    --environment "Variables={AWS_REGION=$AWS_REGION,S3_BUCKET=$S3_BUCKET,NEO4J_URI=$NEO4J_URI,NEO4J_USER=$NEO4J_USER,NEO4J_PASSWORD=$NEO4J_PASSWORD,NEMOTRON_ENDPOINT=$NEMOTRON_ENDPOINT,EMBEDDING_ENDPOINT=$EMBEDDING_ENDPOINT}" \
    --query 'FunctionArn' --output text 2>/dev/null || \
    aws lambda update-function-code \
    --function-name karaka-rag-query \
    --zip-file fileb://lambda.zip --query 'FunctionArn' --output text)

echo "Query Lambda: $QUERY_ARN"

# Deploy status lambda
STATUS_ARN=$(aws lambda create-function \
    --function-name karaka-rag-status \
    --runtime python3.11 \
    --role "$LAMBDA_ROLE_ARN" \
    --handler lambda.status_handler.lambda_handler \
    --zip-file fileb://lambda.zip \
    --timeout 30 \
    --memory-size 256 \
    --environment "Variables={AWS_REGION=$AWS_REGION,S3_BUCKET=$S3_BUCKET}" \
    --query 'FunctionArn' --output text 2>/dev/null || \
    aws lambda update-function-code \
    --function-name karaka-rag-status \
    --zip-file fileb://lambda.zip --query 'FunctionArn' --output text)

echo "Status Lambda: $STATUS_ARN"

# Deploy graph lambda
GRAPH_ARN=$(aws lambda create-function \
    --function-name karaka-rag-graph \
    --runtime python3.11 \
    --role "$LAMBDA_ROLE_ARN" \
    --handler lambda.graph_handler.lambda_handler \
    --zip-file fileb://lambda.zip \
    --timeout 60 \
    --memory-size 256 \
    --environment "Variables={AWS_REGION=$AWS_REGION,NEO4J_URI=$NEO4J_URI,NEO4J_USER=$NEO4J_USER,NEO4J_PASSWORD=$NEO4J_PASSWORD}" \
    --query 'FunctionArn' --output text 2>/dev/null || \
    aws lambda update-function-code \
    --function-name karaka-rag-graph \
    --zip-file fileb://lambda.zip --query 'FunctionArn' --output text)

echo "Graph Lambda: $GRAPH_ARN"

# Deploy API Gateway
echo ""
echo "=== Deploying API Gateway ==="
python3 infrastructure/deploy_api_gateway.py "$INGESTION_ARN" "$QUERY_ARN" "$STATUS_ARN" "$GRAPH_ARN"

echo ""
echo "=== Deployment Complete ==="
echo "Update your .env file with the API_GATEWAY_URL from above"
