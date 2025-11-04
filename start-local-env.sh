#!/bin/bash
set -e

echo "=== Starting Local Testing Environment ==="
echo ""

# Start LocalStack
echo "Starting LocalStack..."
docker-compose up -d

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
sleep 10

# Check if LocalStack is running
if ! curl -s http://localhost:4566/_localstack/health | grep -q "running"; then
    echo "LocalStack failed to start properly"
    exit 1
fi

echo "✓ LocalStack is running"
echo ""

# Create DynamoDB tables
echo "Creating DynamoDB tables..."
./create-local-tables.sh

# Create S3 buckets
echo "Creating S3 buckets..."
./create-local-buckets.sh

echo ""
echo "=== Local Environment Ready ==="
echo ""
echo "LocalStack Dashboard: http://localhost:4566"
echo ""
echo "Test a Lambda function:"
echo "  ./test-lambda-local.sh ListAllDocs"
echo ""
echo "Stop environment:"
echo "  docker-compose down"
