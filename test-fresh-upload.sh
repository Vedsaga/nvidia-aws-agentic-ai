#!/bin/bash
set -e

export $(grep -v '^#' .env | xargs)
source .venv/bin/activate

API_URL="https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod"

echo "=== Fresh Upload Test ==="
echo ""

# 1. Create test file
echo "Rama is a very good boy." > test-fresh.txt
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
    
    # Now test query
    echo ""
    echo "4. Testing query: How was RAM?"
    QUERY_RESPONSE=$(curl -s -X POST "$API_URL/query/submit" \
      -H "Content-Type: application/json" \
      -d '{"question": "How was RAM?"}')
    
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
