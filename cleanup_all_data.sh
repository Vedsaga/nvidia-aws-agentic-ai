#!/bin/bash
set -e

export $(grep -v '^#' .env | xargs)
source .venv/bin/activate

echo "=== Cleaning All Data ==="

# 1. Clear DynamoDB tables
echo "1. Clearing Sentences table..."
aws dynamodb scan --table-name Sentences --attributes-to-get sentence_hash --output json | \
  jq -r '.Items[].sentence_hash.S' | \
  while read hash; do
    aws dynamodb delete-item --table-name Sentences --key "{\"sentence_hash\":{\"S\":\"$hash\"}}"
  done

echo "2. Clearing Jobs table..."
aws dynamodb scan --table-name Jobs --attributes-to-get job_id --output json | \
  jq -r '.Items[].job_id.S' | \
  while read job; do
    aws dynamodb delete-item --table-name Jobs --key "{\"job_id\":{\"S\":\"$job\"}}"
  done

echo "3. Clearing Queries table..."
aws dynamodb scan --table-name Queries --attributes-to-get query_id --output json | \
  jq -r '.Items[].query_id.S' | \
  while read qid; do
    aws dynamodb delete-item --table-name Queries --key "{\"query_id\":{\"S\":\"$qid\"}}"
  done

# 2. Clear S3 buckets (graphs and embeddings)
echo "4. Clearing S3 graphs..."
aws s3 rm s3://knowledge-graph-151534200269-us-east-1/graphs/ --recursive 2>/dev/null || true

echo "5. Clearing S3 embeddings..."
aws s3 rm s3://knowledge-graph-151534200269-us-east-1/embeddings/ --recursive 2>/dev/null || true

echo "6. Clearing S3 temp_kg..."
aws s3 rm s3://knowledge-graph-151534200269-us-east-1/temp_kg/ --recursive 2>/dev/null || true

echo ""
echo "=== Cleanup Complete ==="
echo ""
echo "Now test with fresh upload:"
echo "  ./test-fresh-upload.sh"
