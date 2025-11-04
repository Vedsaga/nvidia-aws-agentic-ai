#!/bin/bash
set -e

echo "=== Integration Test: Full Document Processing Flow ==="
echo ""

# Ensure LocalStack is running
if ! curl -s http://localhost:4566/_localstack/health > /dev/null; then
    echo "LocalStack not running. Start it with: ./start-local-env.sh"
    exit 1
fi

JOB_ID="test-job-$(date +%s)"
SENTENCE_HASH="hash-$(date +%s)"

echo "Test Job ID: $JOB_ID"
echo "Test Sentence Hash: $SENTENCE_HASH"
echo ""

# Step 1: Create job in DynamoDB
echo "1. Creating job in DynamoDB..."
aws dynamodb put-item \
    --endpoint-url http://localhost:4566 \
    --table-name DocumentJobs \
    --item "{
        \"job_id\": {\"S\": \"$JOB_ID\"},
        \"status\": {\"S\": \"pending\"},
        \"filename\": {\"S\": \"test-doc.txt\"},
        \"created_at\": {\"N\": \"$(date +%s)\"}
    }" \
    --region us-east-1

echo "✓ Job created"
echo ""

# Step 2: Upload test document to S3
echo "2. Uploading test document to S3..."
echo "John works at Microsoft in Seattle. He is a software engineer." > /tmp/test-doc.txt
aws s3 cp /tmp/test-doc.txt s3://raw-documents-local/$JOB_ID.txt \
    --endpoint-url http://localhost:4566 \
    --region us-east-1

echo "✓ Document uploaded"
echo ""

# Step 3: Test LLM Call
echo "3. Testing LLM Call (Entity Extraction)..."
cat > /tmp/llm-test-event.json << EOF
{
  "job_id": "$JOB_ID",
  "sentence_hash": "$SENTENCE_HASH",
  "stage": "D1",
  "prompt_name": "entity_extraction",
  "inputs": {
    "text": "John works at Microsoft in Seattle.",
    "sentence": "John works at Microsoft in Seattle."
  },
  "temperature": 0.6,
  "attempt_number": 1,
  "generation_index": 1
}
EOF

./test-lambda-local.sh LLMCall /tmp/llm-test-event.json

echo "✓ LLM Call tested"
echo ""

# Step 4: Test Entity Extraction
echo "4. Testing Entity Extraction..."
cat > /tmp/entity-test-event.json << EOF
{
  "job_id": "$JOB_ID",
  "hash": "$SENTENCE_HASH",
  "text": "John works at Microsoft in Seattle.",
  "index": 0
}
EOF

./test-lambda-local.sh ExtractEntities /tmp/entity-test-event.json

echo "✓ Entity Extraction tested"
echo ""

# Step 5: Verify data in DynamoDB
echo "5. Verifying data in DynamoDB..."
aws dynamodb get-item \
    --endpoint-url http://localhost:4566 \
    --table-name DocumentJobs \
    --key "{\"job_id\": {\"S\": \"$JOB_ID\"}}" \
    --region us-east-1

echo ""
echo "=== Integration Test Complete ==="
echo ""
echo "Cleanup:"
echo "  aws dynamodb delete-item --endpoint-url http://localhost:4566 --table-name DocumentJobs --key '{\"job_id\": {\"S\": \"$JOB_ID\"}}' --region us-east-1"
echo "  aws s3 rm s3://raw-documents-local/$JOB_ID.txt --endpoint-url http://localhost:4566 --region us-east-1"
