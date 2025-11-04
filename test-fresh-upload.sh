#!/bin/bash
set -e

source .venv/bin/activate
export $(grep -v '^#' .env | xargs)

API_URL="${APP_API_GATEWAY_URL}"

echo "=== Fresh Upload Test ==="
echo ""

# 1. Create test file
echo "Rama eats mango." > test-fresh.txt
echo "Created test file: test-fresh.txt"
echo ""

# 2. Request upload URL
echo "1. Requesting upload URL..."
RESPONSE=$(curl -s -X POST "$API_URL/upload" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test-fresh.txt"}')

echo "$RESPONSE" | jq .
JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
UPLOAD_URL=$(echo "$RESPONSE" | jq -r '.pre_signed_url')

echo ""
echo "Job ID: $JOB_ID"
echo ""

# 3. Upload file
echo "2. Uploading file..."
curl -X PUT --upload-file test-fresh.txt "$UPLOAD_URL"
echo ""
echo "File uploaded"
echo ""

# 4. Poll status
echo "3. Polling status (checking every 5 seconds)..."
for i in {1..60}; do
  echo "   Check $i..."
  STATUS_RESPONSE=$(curl -s "$API_URL/status/$JOB_ID")
  STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
  PROGRESS=$(echo "$STATUS_RESPONSE" | jq -r '.progress_percentage')
  
  echo "   Status: $STATUS, Progress: $PROGRESS%"
  
  if [ "$STATUS" == "completed" ]; then
    echo ""
    echo "=== Processing Complete ==="
    echo "$STATUS_RESPONSE" | jq .
    
    # Verify GSSR execution
    echo ""
    echo "=== GSSR Verification ==="
    SENTENCE_HASH=$(echo -n "Rama eats mango. " | sha256sum | cut -d' ' -f1)
    echo "Sentence hash: $SENTENCE_HASH"
    
    # Check Sentences table for GSSR data
    echo ""
    echo "1. Checking Sentences table..."
    aws dynamodb get-item --table-name Sentences --key "{\"sentence_hash\":{\"S\":\"$SENTENCE_HASH\"}}" | jq '.Item | {
      d1_attempts: .d1_attempts.N,
      d2a_attempts: .d2a_attempts.N,
      d2b_attempts: .d2b_attempts.N,
      best_score: .best_score.N,
      needs_review: .needs_review.BOOL,
      status: .status.S
    }'
    
    # Check LLM logs count
    echo ""
    echo "2. Checking LLM call logs..."
    LLM_COUNT=$(aws dynamodb query --table-name LLMCallLog --index-name BySentenceHash \
      --key-condition-expression 'sentence_hash = :sh' \
      --expression-attribute-values "{\":sh\":{\"S\":\"$SENTENCE_HASH\"}}" \
      --select COUNT | jq -r '.Count')
    echo "Total LLM calls: $LLM_COUNT"
    
    # Show breakdown by stage
    echo ""
    echo "3. LLM calls by stage:"
    aws dynamodb query --table-name LLMCallLog --index-name BySentenceHash \
      --key-condition-expression 'sentence_hash = :sh' \
      --expression-attribute-values "{\":sh\":{\"S\":\"$SENTENCE_HASH\"}}" \
      --limit 50 | jq -r '.Items[] | [.pipeline_stage.S, .temperature.N, .generation_index.N // "N/A"] | @tsv' | \
      awk '{stages[$1]++} END {for (s in stages) print s ": " stages[s]}'
    
    # Now test query
    echo ""
    echo "4. Testing query: Who eats mango?"
    QUERY_RESPONSE=$(curl -s -X POST "$API_URL/query/submit" \
      -H "Content-Type: application/json" \
      -d '{"question": "Who eats mango?"}')
    
    echo "$QUERY_RESPONSE" | jq .
    QUERY_ID=$(echo "$QUERY_RESPONSE" | jq -r '.query_id')
    
    echo ""
    echo "5. Polling query answer..."
    for j in {1..20}; do
      echo "   Check $j..."
      ANSWER_RESPONSE=$(curl -s "$API_URL/query/status/$QUERY_ID")
      ANSWER_STATUS=$(echo "$ANSWER_RESPONSE" | jq -r '.status')
      
      if [ "$ANSWER_STATUS" == "completed" ]; then
        echo ""
        echo "=== ANSWER READY ==="
        echo "$ANSWER_RESPONSE" | jq .
        exit 0
      fi
      
      sleep 3
    done
    
    echo "Query timeout"
    exit 1
  elif [ "$STATUS" == "error" ]; then
    echo ""
    echo "=== ERROR ==="
    echo "$STATUS_RESPONSE" | jq .
    exit 1
  fi
  
  sleep 5
done

echo ""
echo "Processing timeout"
