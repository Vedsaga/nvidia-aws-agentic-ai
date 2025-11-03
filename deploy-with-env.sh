#!/bin/bash
set -e

# Source the frontend .env file
if [ -f frontend/.env ]; then
    echo "Loading environment variables from frontend/.env"
    export $(grep -v '^#' frontend/.env | xargs)
    echo "GENERATE_ENDPOINT: $APP_GENERATE_ENDPOINT_URL"
    echo "EMBED_ENDPOINT: $APP_EMBED_ENDPOINT_URL"
else
    echo "ERROR: frontend/.env not found"
    exit 1
fi

# Try to deploy the serverless stack
echo "Attempting to deploy ServerlessStack..."
cdk deploy ServerlessStack --require-approval never