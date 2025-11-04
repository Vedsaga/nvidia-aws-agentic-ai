#!/bin/bash

# Test GSSR Phase 1 Implementation
# This script uploads a test document and monitors the GSSR process

set -e

echo "=== GSSR Phase 1 Test ==="
echo ""

# Load environment
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)

API_URL=$(grep APP_API_GATEWAY_URL frontend/.env | cut -d '=' -f2)

echo "▶ Uploading test document..."
UPLOAD_RESPONSE=$(curl -s -X POST "${API_URL}/upload" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test_gssr_phase1.txt"}')

echo "$UPLOAD_RESPONSE" | jq '.'

JOB_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.job_id')
PRESIGNED_URL=$(echo "$UPLOAD_RESPONSE" | jq -r '.pre_signed_url')

echo ""
echo "▶ Job ID: $JOB_ID"
echo ""

echo "▶ Uploading file content..."
curl -s -X PUT "$PRESIGNED_URL" \
  -H "Content-Type: text/plain" \
  --data-binary @test_kg.txt

echo ""
echo "✓ File uploaded"
echo ""

echo "▶ Triggering processing..."
curl -s -X POST "${API_URL}/trigger/${JOB_ID}" | jq '.'

echo ""
echo "▶ Waiting 5 seconds for processing to start..."
sleep 5

echo ""
echo "▶ Checking job status..."
curl -s "${API_URL}/status/${JOB_ID}" | jq '.'

echo ""
echo "▶ Checking LLM call logs (last 10 calls)..."
aws dynamodb scan \
  --table-name LLMCallLog \
  --filter-expression "job_id = :jid" \
  --expression-attribute-values "{\":jid\":{\"S\":\"$JOB_ID\"}}" \
  --max-items 10 \
  --output json | jq '.Items[] | {
    stage: .pipeline_stage.S,
    temperature: .temperature.N,
    attempt: .attempt_number.N,
    generation: .generation_index.N,
    status: .status.S
  }'

echo ""
echo "▶ Checking Sentences table for GSSR metadata..."
SENTENCE_HASH=$(aws dynamodb scan \
  --table-name Sentences \
  --filter-expression "job_id = :jid" \
  --expression-attribute-values "{\":jid\":{\"S\":\"$JOB_ID\"}}" \
  --max-items 1 \
  --output json | jq -r '.Items[0].sentence_hash.S')

if [ "$SENTENCE_HASH" != "null" ] && [ -n "$SENTENCE_HASH" ]; then
  echo "Sentence Hash: $SENTENCE_HASH"
  aws dynamodb get-item \
    --table-name Sentences \
    --key "{\"sentence_hash\":{\"S\":\"$SENTENCE_HASH\"}}" \
    --output json | jq '.Item | {
      text: .text.S,
      d1_attempts: .d1_attempts.N,
      d2a_attempts: .d2a_attempts.N,
      d2b_attempts: .d2b_attempts.N,
      best_score: .best_score.N,
      needs_review: .needs_review.BOOL,
      status: .status.S
    }'
fi

echo ""
echo "=== Test Complete ==="
