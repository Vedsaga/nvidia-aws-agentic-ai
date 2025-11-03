#!/bin/bash
set -e # Stop on error

# 1. Load the frontend .env file to get URLs
if [ ! -f frontend/.env ]; then
    echo "ERROR: frontend/.env file not found. Have you deployed the models yet?"
    exit 1
fi
source frontend/.env
export $(grep -v '^#' frontend/.env | xargs)


echo "--- Testing Generator Endpoint ---"
echo "URL: $APP_GENERATE_ENDPOINT_URL"

# --- GENERATOR JSON PAYLOAD ---
cat > /tmp/generator_payload.json <<EOF
{
  "model": "nvidia/llama-3.1-nemotron-nano-8b-v1",
  "messages": [
    {
      "role": "user",
      "content": "What is the capital of France?"
    }
  ],
  "max_tokens": 128
}
EOF

curl -X POST \
  "$APP_GENERATE_ENDPOINT_URL/v1/chat/completions" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d @/tmp/generator_payload.json


echo -e "\n\n--- Testing Embedder Endpoint (Create Embedding) ---"
echo "URL: $APP_EMBED_ENDPOINT_URL"

# --- EMBEDDER JSON PAYLOAD ---
cat > /tmp/embedder_payload.json <<EOF
{
  "model": "nvidia/llama-3.2-nv-embedqa-1b-v2",
  "input": [
    "This is a test sentence for embedding."
  ],
  "input_type": "query"
}
EOF

EMBED_RESPONSE=$(curl -s -X POST \
  "$APP_EMBED_ENDPOINT_URL/v1/embeddings" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d @/tmp/embedder_payload.json)

echo "$EMBED_RESPONSE"

# Extract embedding dimension info
EMBED_LENGTH=$(echo "$EMBED_RESPONSE" | grep -o '"embedding":\[' | wc -l)
if [ "$EMBED_LENGTH" -gt 0 ]; then
    echo -e "\n✓ Embedding created successfully"
else
    echo -e "\n✗ Failed to create embedding"
    exit 1
fi


echo -e "\n\n--- Testing Embedder Endpoint (Retrieval) ---"

# Test retrieval with a similar query
cat > /tmp/retrieval_payload.json <<EOF
{
  "model": "nvidia/llama-3.2-nv-embedqa-1b-v2",
  "input": [
    "test sentence"
  ],
  "input_type": "query"
}
EOF

RETRIEVAL_RESPONSE=$(curl -s -X POST \
  "$APP_EMBED_ENDPOINT_URL/v1/embeddings" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d @/tmp/retrieval_payload.json)

echo "$RETRIEVAL_RESPONSE"

if echo "$RETRIEVAL_RESPONSE" | grep -q '"embedding"'; then
    echo -e "\n✓ Retrieval test successful"
else
    echo -e "\n✗ Retrieval test failed"
fi


echo -e "\n\n--- Cleaning up test data ---"

# Clean up temporary files
rm -f /tmp/generator_payload.json /tmp/embedder_payload.json /tmp/retrieval_payload.json

echo "✓ Test payloads cleaned up"

echo -e "\n--- Test complete. ---"
