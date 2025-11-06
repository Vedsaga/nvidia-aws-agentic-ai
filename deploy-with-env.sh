#!/bin/bash
set -e

# Source the frontend .env file
source scripts/load_env.sh
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    load_env
    echo "GENERATE_ENDPOINT: $APP_GENERATE_ENDPOINT_URL"
    echo "EMBED_ENDPOINT: $APP_EMBED_ENDPOINT_URL"
else
    echo "ERROR: .env not found"
    exit 1
fi

# Try to deploy the serverless stack
echo "Attempting to deploy ServerlessStack..."
cdk deploy ServerlessStack --require-approval never