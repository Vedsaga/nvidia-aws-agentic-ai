#!/bin/bash

API_URL="https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod"

echo "Testing Query API with doc_ids"
echo "==============================="
echo ""

# Get the job_id from our test
JOB_ID="d298ea26-ea73-4540-bafb-899a09d5bafa"

echo "Sending query: Who teaches Arjuna?"
echo "With doc_ids: [$JOB_ID]"
echo ""

RESPONSE=$(curl -s -X POST "$API_URL/query" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"Who teaches Arjuna?\", \"doc_ids\": [\"$JOB_ID\"]}")

echo "$RESPONSE" | jq .
echo ""

# Also test the sentence directly
echo "Checking sentence in DynamoDB..."
aws dynamodb scan --table-name Sentences \
  --filter-expression "job_id = :jid" \
  --expression-attribute-values "{\":jid\":{\"S\":\"$JOB_ID\"}}" \
  --query 'Items[0].{hash:sentence_hash.S,text:sentence_text.S,status:kg_status.S}' \
  --output json | jq .
