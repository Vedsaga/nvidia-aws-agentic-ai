#!/bin/bash

API_URL="https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod"

echo "Testing Query API"
echo "================="
echo ""

# Test query
echo "Sending query: Who teaches Arjuna?"
RESPONSE=$(curl -s -X POST "$API_URL/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Who teaches Arjuna?"}')

echo "$RESPONSE" | jq .
echo ""
echo "✅ Query API Test Complete!"
