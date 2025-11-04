#!/bin/bash
set -e

ENDPOINT="http://localhost:4566"

echo "Creating DynamoDB tables in LocalStack..."

# DocumentJobs table
aws dynamodb create-table \
    --endpoint-url $ENDPOINT \
    --table-name DocumentJobs \
    --attribute-definitions AttributeName=job_id,AttributeType=S \
    --key-schema AttributeName=job_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1 2>/dev/null || echo "DocumentJobs table already exists"

# Sentences table with GSI
aws dynamodb create-table \
    --endpoint-url $ENDPOINT \
    --table-name Sentences \
    --attribute-definitions \
        AttributeName=sentence_hash,AttributeType=S \
        AttributeName=job_id,AttributeType=S \
    --key-schema AttributeName=sentence_hash,KeyType=HASH \
    --global-secondary-indexes \
        "IndexName=ByJobId,KeySchema=[{AttributeName=job_id,KeyType=HASH},{AttributeName=sentence_hash,KeyType=RANGE}],Projection={ProjectionType=ALL}" \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1 2>/dev/null || echo "Sentences table already exists"

# LLMCallLog table with GSIs
aws dynamodb create-table \
    --endpoint-url $ENDPOINT \
    --table-name LLMCallLog \
    --attribute-definitions \
        AttributeName=call_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=N \
        AttributeName=job_id,AttributeType=S \
        AttributeName=sentence_hash,AttributeType=S \
    --key-schema \
        AttributeName=call_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --global-secondary-indexes \
        "IndexName=ByJobId,KeySchema=[{AttributeName=job_id,KeyType=HASH}],Projection={ProjectionType=ALL}" \
        "IndexName=BySentenceHash,KeySchema=[{AttributeName=sentence_hash,KeyType=HASH},{AttributeName=timestamp,KeyType=RANGE}],Projection={ProjectionType=ALL}" \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1 2>/dev/null || echo "LLMCallLog table already exists"

# Queries table
aws dynamodb create-table \
    --endpoint-url $ENDPOINT \
    --table-name Queries \
    --attribute-definitions AttributeName=query_id,AttributeType=S \
    --key-schema AttributeName=query_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1 2>/dev/null || echo "Queries table already exists"

echo ""
echo "✓ All tables created"
echo ""
echo "Verify tables:"
echo "aws dynamodb list-tables --endpoint-url $ENDPOINT --region us-east-1"
