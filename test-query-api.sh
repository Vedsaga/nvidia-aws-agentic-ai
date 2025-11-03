#!/bin/bash

API_URL="https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod"

echo "=== Testing Query API ==="
echo ""
echo "1. Submitting question: Who eats the mango?"
RESPONSE=$(curl -s -X POST "$API_URL/query/submit" \
  -H "Content-Type: application/json" \
  -d '{"question": "Who eats the mango?"}')

echo "$RESPONSE" | jq .
QUERY_ID=$(echo "$RESPONSE" | jq -r '.query_id')

echo ""
echo "2. Query ID: $QUERY_ID"
echo ""
echo "3. Polling for answer (checking every 3 seconds)..."

for i in {1..20}; do
  echo "   Attempt $i..."
  STATUS_RESPONSE=$(curl -s "$API_URL/query/status/$QUERY_ID")
  STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
  
  if [ "$STATUS" == "completed" ]; then
    echo ""
    echo "=== ANSWER READY ==="
    echo "$STATUS_RESPONSE" | jq .
    exit 0
  elif [ "$STATUS" == "error" ]; then
    echo ""
    echo "=== ERROR ==="
    echo "$STATUS_RESPONSE" | jq .
    exit 1
  fi
  
  sleep 3
done

echo ""
echo "Timeout waiting for answer"
