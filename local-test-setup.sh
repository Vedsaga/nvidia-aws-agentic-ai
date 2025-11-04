#!/bin/bash
set -e

echo "=== Local Lambda Testing Setup ==="
echo ""

# Check prerequisites
echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "Docker not found. Install Docker first."; exit 1; }
command -v sam >/dev/null 2>&1 || { echo "AWS SAM CLI not found. Install with: pip install aws-sam-cli"; exit 1; }
command -v localstack >/dev/null 2>&1 || { echo "LocalStack not found. Install with: pip install localstack"; exit 1; }

echo "✓ All prerequisites found"
echo ""

# Build Lambda layer with dependencies
echo "Building Lambda layer with requests and networkx..."
mkdir -p lambda_layer/python
pip install requests networkx -t lambda_layer/python/ --upgrade
echo "✓ Lambda layer built"
echo ""

# Build SAM application
echo "Building SAM application..."
sam build
echo "✓ SAM build complete"
echo ""

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Start LocalStack: localstack start -d"
echo "2. Create DynamoDB tables: ./create-local-tables.sh"
echo "3. Test Lambda functions: ./test-lambda-local.sh <function-name>"
echo ""
