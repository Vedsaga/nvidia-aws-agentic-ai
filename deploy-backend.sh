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
    --context nvidia_api_key=$NVIDIA_BUILD_API_KEY \
    --context nvidia_email=$NVIDIA_ACCOUNT_EMAIL

# 3. Deploy the serverless stack
echo "Deploying ServerlessStack (Lambdas, DynamoDB, API GW...)"
cdk deploy ServerlessStack \
    --outputs-file ./cdk-outputs-backend.json \
    --require-approval never

# 4. Update the frontend .env file
echo "Updating frontend environment..."
python scripts/parse_outputs.py cdk-outputs-backend.json

# 5. Get the KG Bucket name from the outputs
#    (This requires 'jq' to be installed: sudo apt-get install jq)
echo "Getting KnowledgeGraphBucket name from outputs..."
KG_BUCKET_NAME=$(jq -r '.ServerlessStack.KGBucket' ./cdk-outputs-backend.json)

if [ -z "$KG_BUCKET_NAME" ] || [ "$KG_BUCKET_NAME" == "null" ]; then
    echo "ERROR: Could not find KGBucket in cdk-outputs-backend.json"
    echo "Please ensure ServerlessStack exports 'KGBucket' as an output."
    exit 1
fi

# 6. Sync the prompts directory to the KG Bucket
echo "Syncing prompts/ directory to s3://$KG_BUCKET_NAME/prompts/..."
aws s3 sync ./prompts/ s3://$KG_BUCKET_NAME/prompts/ --delete

echo "Backend deployment complete."
echo "Prompts synced to s3://$KG_BUCKET_NAME/prompts/"
echo "API Gateway URL is in frontend/.env"
