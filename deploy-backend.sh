#!/bin/bash
set -e # Exit immediately if a command fails

# 1. Load the manual .env file
if [ ! -f .env ]; then
    echo "ERROR: .env file not found."
    exit 1
fi
export $(grep -v '^#' .env | xargs)

# 2. Bootstrap the environment
echo "Bootstrapping AWS environment for CDK..."
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION \
    --context nvidia_api_key=$NVIDIA_BUILD_API_KEY # <-- ADD THIS LINE

# 3. Deploy the serverless stack
echo "Deploying ServerlessStack (Lambdas, DynamoDB, API GW...)"
cdk deploy ServerlessStack \
    --outputs-file ./cdk-outputs-backend.json \
    --require-approval never

# 4. Update the frontend .env file
echo "Updating frontend environment..."
python scripts/parse_outputs.py cdk-outputs-backend.json

echo "Backend deployment complete. API Gateway URL is in frontend/.env"
