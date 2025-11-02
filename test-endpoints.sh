#!/bin/bash
set -e # Stop on error

# 1. Load the frontend .env file to get URLs
if [ ! -f frontend/.env ]; then
    echo "ERROR: frontend/.env file not found. Have you deployed the models yet?"
    exit 1
fi
source frontend/.env

if [ -z "$APP_GENERATE_ENDPOINT_URL" ] || [ -z "$APP_EMBED_ENDPOINT_URL" ]; then
    echo "ERROR: Endpoint URLs not found in frontend/.env."
    exit 1
fi

echo "--- Testing Generator Endpoint ---"
echo "URL: $APP_GENERATE_ENDPOINT_URL"
curl -X 'POST' \
  "$APP_GENERATE_ENDPOINT_URL/v1/chat/completions" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "meta/llama-3.1-nemotron-nano-8b-v1",
    "messages": [
      {
        "role": "user",
        "content": "What is the capital of France?"
      }
    ],
    "max_tokens": 128
  }'

echo -e "\n\n--- Testing Embedder Endpoint ---"
echo "URL: $APP_EMBED_ENDPOINT_URL"
curl -X 'POST' \
  "$APP_EMBED_ENDPOINT_URL/v1/embeddings" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "nvidia/llama-3.2-nv-embedqa-1b-v2",
    "input": [
      "This is a test sentence."
    ]
  }'

echo -e "\n\n--- Test complete. ---"
