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
  -d @/tmp/generator_payload.json # Reads payload from file


echo -e "\n\n--- Testing Embedder Endpoint ---"
echo "URL: $APP_EMBED_ENDPOINT_URL"

# --- EMBEDDER JSON PAYLOAD ---
cat > /tmp/embedder_payload.json <<EOF
{
  "model": "nvidia/nv-embedqa-e5-v5",
  "input": [
    "This is a test sentence."
  ],
  "input_type": "query"
}
EOF

curl -X POST \
  "$APP_EMBED_ENDPOINT_URL/v1/embeddings" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d @/tmp/embedder_payload.json # Reads payload from file

echo -e "\n\n--- Test complete. ---"