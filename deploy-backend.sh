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
source scripts/load_env.sh
load_env
print_success "Environment variables loaded"

# 2. Bootstrap the environment (force to ensure resources exist)
print_step "Bootstrapping AWS environment for CDK..."
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION \
    --context nvidia_api_key=$NVIDIA_BUILD_API_KEY \
    --context nvidia_email=$NVIDIA_ACCOUNT_EMAIL \
    --force
print_success "Bootstrap complete"

# 3. Check if there are changes to deploy
print_step "Checking for changes in EventDrivenStack..."
DIFF_OUTPUT=$(cdk diff EventDrivenStack 2>&1 || true)

if echo "$DIFF_OUTPUT" | grep -q "There were no differences"; then
    print_info "No changes detected in EventDrivenStack - skipping deployment"
    SKIP_DEPLOY=true
else
    print_info "Changes detected - proceeding with deployment"
    SKIP_DEPLOY=false
fi

# 4. Deploy the event-driven stack (only if changes detected or forced)
if [ "$SKIP_DEPLOY" = false ] || [ "$1" == "--force" ]; then
    print_step "Deploying EventDrivenStack (Event Bus, Lambdas, DynamoDB...)"
    cdk deploy EventDrivenStack \
        --outputs-file ./cdk-outputs-backend.json \
        --require-approval never
    print_success "Deployment complete"
    
    # 5. Update the frontend .env file
    print_step "Updating frontend environment..."
    python scripts/parse_outputs.py cdk-outputs-backend.json
    print_success "Frontend .env updated"
else
    print_info "Use './deploy-backend.sh --force' to force redeployment"
fi

echo ""
print_success "Event-driven architecture deployment complete!"
echo ""
echo "Summary:"
echo "  • Event Bus: karaka-events"
echo "  • Lambda Handlers: Check AWS Console"
echo "  • Outputs: cdk-outputs-backend.json"
echo ""