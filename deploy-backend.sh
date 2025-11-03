#!/bin/bash
set -e # Exit immediately if a command fails

# Colors for better visibility
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# 1. Load the manual .env file
if [ ! -f .env ]; then
    echo "ERROR: .env file not found."
    exit 1
fi
export $(grep -v '^#' .env | xargs)
print_success "Environment variables loaded"

# 2. Bootstrap the environment (only if needed)
print_step "Checking CDK bootstrap status..."
BOOTSTRAP_VERSION=$(aws cloudformation describe-stacks \
    --stack-name CDKToolkit \
    --query "Stacks[0].Outputs[?OutputKey=='BootstrapVersion'].OutputValue" \
    --output text 2>/dev/null || echo "0")

if [ "$BOOTSTRAP_VERSION" == "0" ]; then
    print_step "Bootstrapping AWS environment for CDK..."
    cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION \
        --context nvidia_api_key=$NVIDIA_BUILD_API_KEY \
        --context nvidia_email=$NVIDIA_ACCOUNT_EMAIL
    print_success "Bootstrap complete"
else
    print_success "CDK already bootstrapped (version: $BOOTSTRAP_VERSION)"
fi

# 3. Check if there are changes to deploy
print_step "Checking for changes in ServerlessStack..."
DIFF_OUTPUT=$(cdk diff ServerlessStack \
    --context nvidia_api_key=$NVIDIA_BUILD_API_KEY \
    --context nvidia_email=$NVIDIA_ACCOUNT_EMAIL 2>&1 || true)

if echo "$DIFF_OUTPUT" | grep -q "There were no differences"; then
    print_info "No changes detected in ServerlessStack - skipping deployment"
    SKIP_DEPLOY=true
else
    print_info "Changes detected - proceeding with deployment"
    SKIP_DEPLOY=false
fi

# 4. Deploy the serverless stack (only if changes detected or forced)
if [ "$SKIP_DEPLOY" = false ] || [ "$1" == "--force" ]; then
    print_step "Deploying ServerlessStack (Lambdas, DynamoDB, API GW...)"
    cdk deploy ServerlessStack \
        --outputs-file ./cdk-outputs-backend.json \
        --require-approval never \
        --context nvidia_api_key=$NVIDIA_BUILD_API_KEY \
        --context nvidia_email=$NVIDIA_ACCOUNT_EMAIL
    print_success "Deployment complete"
else
    print_info "Use './deploy-backend.sh --force' to force redeployment"
fi

# 5. Update the frontend .env file
print_step "Updating frontend environment..."
python scripts/parse_outputs.py cdk-outputs-backend.json
print_success "Frontend .env updated"

# 6. Get the KG Bucket name from the outputs
print_step "Getting KnowledgeGraphBucket name from outputs..."
KG_BUCKET_NAME=$(jq -r '.ServerlessStack.KGBucket' ./cdk-outputs-backend.json)

if [ -z "$KG_BUCKET_NAME" ] || [ "$KG_BUCKET_NAME" == "null" ]; then
    echo "ERROR: Could not find KGBucket in cdk-outputs-backend.json"
    echo "Please ensure ServerlessStack exports 'KGBucket' as an output."
    exit 1
fi
print_success "Bucket name: $KG_BUCKET_NAME"

# 7. Sync the prompts directory to the KG Bucket (only changed files)
print_step "Syncing prompts/ directory to s3://$KG_BUCKET_NAME/prompts/..."
SYNC_OUTPUT=$(aws s3 sync ./prompts/ s3://$KG_BUCKET_NAME/prompts/ --delete 2>&1)

# Count uploaded files
UPLOADED=$(echo "$SYNC_OUTPUT" | grep -c "upload:" || echo "0")
DELETED=$(echo "$SYNC_OUTPUT" | grep -c "delete:" || echo "0")

if [ "$UPLOADED" -gt 0 ] || [ "$DELETED" -gt 0 ]; then
    print_success "Synced: $UPLOADED uploaded, $DELETED deleted"
else
    print_info "No changes in prompts/ directory"
fi

echo ""
print_success "Backend deployment complete!"
echo ""
echo "Summary:"
echo "  • Prompts: s3://$KG_BUCKET_NAME/prompts/"
echo "  • API Gateway URL: Check .env"
echo ""