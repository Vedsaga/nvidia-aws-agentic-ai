#!/bin/bash

echo "=== Verifying Local Testing Setup ==="
echo ""

# Check prerequisites
echo "Checking prerequisites..."
MISSING=0

if ! command -v docker &> /dev/null; then
    echo "✗ Docker not found"
    MISSING=1
else
    echo "✓ Docker installed: $(docker --version)"
fi

if ! command -v sam &> /dev/null; then
    echo "✗ AWS SAM CLI not found"
    echo "  Install: pip install aws-sam-cli"
    MISSING=1
else
    echo "✓ SAM CLI installed: $(sam --version)"
fi

if ! command -v localstack &> /dev/null; then
    echo "✗ LocalStack not found"
    echo "  Install: pip install localstack"
    MISSING=1
else
    echo "✓ LocalStack installed: $(localstack --version)"
fi

if ! command -v aws &> /dev/null; then
    echo "✗ AWS CLI not found"
    echo "  Install: pip install awscli"
    MISSING=1
else
    echo "✓ AWS CLI installed: $(aws --version)"
fi

echo ""

if [ $MISSING -eq 1 ]; then
    echo "Missing prerequisites. Install them and try again."
    exit 1
fi

# Check if template.yaml exists
if [ ! -f "template.yaml" ]; then
    echo "✗ template.yaml not found"
    exit 1
else
    echo "✓ template.yaml exists"
fi

# Check if lambda_layer exists
if [ ! -d "lambda_layer" ]; then
    echo "✗ lambda_layer directory not found"
    echo "  Run: ./local-test-setup.sh"
    exit 1
else
    echo "✓ lambda_layer directory exists"
fi

# Check if LocalStack is running
echo ""
echo "Checking LocalStack status..."
if curl -s http://localhost:4566/_localstack/health > /dev/null 2>&1; then
    echo "✓ LocalStack is running"
    
    # Check tables
    echo ""
    echo "Checking DynamoDB tables..."
    TABLES=$(aws dynamodb list-tables --endpoint-url http://localhost:4566 --region us-east-1 --output text 2>/dev/null | grep -c "TABLE")
    if [ "$TABLES" -ge 4 ]; then
        echo "✓ DynamoDB tables created ($TABLES tables)"
    else
        echo "⚠ Only $TABLES tables found (expected 4)"
        echo "  Run: ./create-local-tables.sh"
    fi
    
    # Check buckets
    echo ""
    echo "Checking S3 buckets..."
    BUCKETS=$(aws s3 ls --endpoint-url http://localhost:4566 --region us-east-1 2>/dev/null | wc -l)
    if [ "$BUCKETS" -ge 3 ]; then
        echo "✓ S3 buckets created ($BUCKETS buckets)"
    else
        echo "⚠ Only $BUCKETS buckets found (expected 3)"
        echo "  Run: ./create-local-buckets.sh"
    fi
else
    echo "✗ LocalStack not running"
    echo "  Start: ./start-local-env.sh"
fi

# Check if SAM build exists
echo ""
if [ -d ".aws-sam/build" ]; then
    echo "✓ SAM build directory exists"
    FUNCTIONS=$(find .aws-sam/build -name "lambda_function.py" | wc -l)
    echo "  Built functions: $FUNCTIONS"
else
    echo "✗ SAM build not found"
    echo "  Run: sam build"
fi

echo ""
echo "=== Verification Complete ==="
echo ""

if [ $MISSING -eq 0 ]; then
    echo "Ready to test! Try:"
    echo "  ./test-lambda-local.sh ListAllDocs"
fi
