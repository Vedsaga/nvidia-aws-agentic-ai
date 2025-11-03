#!/bin/bash
set -e

# Load environment variables
source .env

# Create a test document
TEST_DOC="test-trigger-$(date +%s).txt"
echo "This is a test document to verify S3 trigger functionality. Dr. Smith went to the store. He bought some items." > "$TEST_DOC"

echo "Uploading test document: $TEST_DOC"

# Upload to S3 raw bucket
aws s3 cp "$TEST_DOC" "s3://raw-documents-151534200269-us-east-1/$TEST_DOC"

echo "Document uploaded. Checking CloudWatch logs for Lambda execution..."

# Wait a moment for processing
sleep 5

# Check recent Lambda logs
echo "Checking ValidateDoc Lambda logs..."
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/ServerlessStack-ValidateDoc" --query 'logGroups[0].logGroupName' --output text | xargs -I {} aws logs describe-log-streams --log-group-name {} --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text | xargs -I {} aws logs get-log-events --log-group-name "/aws/lambda/ServerlessStack-ValidateDoc2962A8D4-UZL5IzMlb3B5" --log-stream-name {} --start-time $(date -d '5 minutes ago' +%s)000

# Clean up
rm "$TEST_DOC"