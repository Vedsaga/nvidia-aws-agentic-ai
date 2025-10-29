#!/bin/bash
################################################################################
# Pre-flight Check for Personal AWS Deployment
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_check() { echo -e "${BLUE}[CHECK]${NC} $1"; }
print_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
print_fail() { echo -e "${RED}[FAIL]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

echo "=================================="
echo "Pre-flight Deployment Check"
echo "=================================="
echo ""

# Check 1: .env.personal exists
print_check "Checking .env.personal file..."
if [ -f .env.personal ]; then
    print_pass ".env.personal exists"
else
    print_fail ".env.personal not found"
    exit 1
fi

# Check 2: AWS credentials
print_check "Checking AWS credentials..."
export AWS_ACCESS_KEY_ID=$(grep aws_access_key_id .env.personal | cut -d= -f2)
export AWS_SECRET_ACCESS_KEY=$(grep aws_secret_access_key .env.personal | cut -d= -f2)
export AWS_REGION=us-east-1

if aws sts get-caller-identity > /dev/null 2>&1; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    print_pass "AWS credentials valid (Account: $ACCOUNT_ID)"
else
    print_fail "AWS credentials invalid"
    exit 1
fi

# Check 3: Python version
print_check "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_pass "Python $PYTHON_VERSION installed"
else
    print_fail "Python 3 not found"
    exit 1
fi

# Check 4: AWS CLI
print_check "Checking AWS CLI..."
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version | cut -d' ' -f1 | cut -d'/' -f2)
    print_pass "AWS CLI $AWS_VERSION installed"
else
    print_fail "AWS CLI not found"
    exit 1
fi

# Check 5: Required files
print_check "Checking required files..."
REQUIRED_FILES=(
    "infrastructure/package_lambda.sh"
    "infrastructure/deploy_api_gateway.py"
    "infrastructure/deploy_neo4j.sh"
    "lambda/ingestion_handler.py"
    "lambda/query_handler.py"
    "lambda/status_handler.py"
    "lambda/graph_handler.py"
)

ALL_FOUND=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        print_fail "Missing: $file"
        ALL_FOUND=false
    fi
done

if [ "$ALL_FOUND" = true ]; then
    print_pass "All required files present"
fi

# Check 6: Virtual environment
print_check "Checking virtual environment..."
if [ -d "venv" ]; then
    print_pass "Virtual environment exists"
else
    print_warn "Virtual environment not found (will be created)"
fi

# Check 7: Existing resources
print_check "Checking existing AWS resources..."

# Check for existing Lambda functions
EXISTING_LAMBDAS=$(aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'karaka-')].FunctionName" --output text 2>/dev/null || echo "")
if [ -n "$EXISTING_LAMBDAS" ]; then
    print_warn "Existing Lambda functions found (will be updated):"
    echo "    $EXISTING_LAMBDAS"
else
    print_pass "No existing Lambda functions"
fi

# Check for existing API Gateway
EXISTING_API=$(aws apigateway get-rest-apis --query "items[?name=='karaka-rag-api'].id" --output text 2>/dev/null || echo "")
if [ -n "$EXISTING_API" ] && [ "$EXISTING_API" != "None" ]; then
    print_warn "Existing API Gateway found (will be updated): $EXISTING_API"
else
    print_pass "No existing API Gateway"
fi

# Check 8: AWS Service Limits
print_check "Checking AWS service limits..."
LAMBDA_COUNT=$(aws lambda list-functions --query "length(Functions)" --output text 2>/dev/null || echo "0")
print_pass "Current Lambda functions: $LAMBDA_COUNT"

# Check 9: Disk space
print_check "Checking disk space..."
AVAILABLE_SPACE=$(df -h . | awk 'NR==2 {print $4}')
print_pass "Available disk space: $AVAILABLE_SPACE"

# Check 10: Network connectivity
print_check "Checking network connectivity..."
if curl -s --max-time 5 https://aws.amazon.com > /dev/null 2>&1; then
    print_pass "Network connectivity OK"
else
    print_warn "Network connectivity issues detected"
fi

echo ""
echo "=================================="
echo "Pre-flight Check Complete"
echo "=================================="
echo ""
echo "Ready to deploy! Run:"
echo "  ./deploy_personal.sh"
echo ""
