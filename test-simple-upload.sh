#!/bin/bash

# Simple upload test with detailed diagnostics

set -e

echo "=========================================="
echo "Simple Upload Test with Diagnostics"
echo "=========================================="
echo ""

# Load environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

API_URL="${APP_API_GATEWAY_URL}"

# Create test file
TEST_FILE="test-simple.txt"
echo "Rama eats mango." > $TEST_FILE

echo "✓ Created test file"
echo ""

# Step 1: Request upload URL
echo "Step 1: Requesting upload URL..."
UPLOAD_RESPONSE=$(curl -s -X POST "${API_URL}upload" \
  -H "Content-Type: application/json" \
  -d "{\"filename\": \"$TEST_FILE\"}")

echo "$UPLOAD_RESPONSE" | jq '.'

JOB_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.job_id')
PRE_SIGNED_URL=$(echo "$UPLOAD_RESPONSE" | jq -r '.pre_signed_url')
S3_KEY=$(echo "$UPLOAD_RESPONSE" | jq -r '.s3_key')

echo ""
echo "Job ID: $JOB_ID"
echo "S3 Key: $S3_KEY"
echo ""

# Step 2: Upload file
echo "Step 2: Uploading file to S3..."
UPLOAD_RESULT=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X PUT "$PRE_SIGNED_URL" \
  -H "Content-Type: text/plain" \
  --data-binary "@$TEST_FILE")

HTTP_CODE=$(echo "$UPLOAD_RESULT" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$HTTP_CODE" == "200" ]; then
    echo "✓ File uploaded successfully (HTTP 200)"
else
    echo "❌ Upload failed with HTTP code: $HTTP_CODE"
    echo "$UPLOAD_RESULT"
    exit 1
fi
echo ""

# Step 3: Verify file in S3
echo "Step 3: Verifying file in S3..."
sleep 2
aws s3 ls "s3://raw-documents-151534200269-us-east-1/$S3_KEY" && echo "✓ File exists in S3" || echo "❌ File not found in S3"
echo ""

# Step 4: Check job status
echo "Step 4: Checking job status..."
for i in {1..5}; do
    sleep 3
    STATUS_RESPONSE=$(curl -s "${API_URL}status/${JOB_ID}")
    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
    echo "Check $i: Status=$STATUS"
    
    if [ "$STATUS" != "PENDING_UPLOAD" ]; then
        echo "✓ Status changed from PENDING_UPLOAD"
        break
    fi
done
echo ""

# Step 5: Check Lambda logs
echo "Step 5: Checking ValidateDoc Lambda logs..."
echo "Waiting 5 seconds for logs to appear..."
sleep 5

aws logs filter-log-events \
    --log-group-name /aws/lambda/ServerlessStack-ValidateDoc \
    --start-time $(($(date +%s) - 120))000 \
    --filter-pattern "$JOB_ID" \
    --query 'events[].message' \
    --output text | head -20 || echo "No logs found for this job_id"
echo ""

# Step 6: Check S3 notification config
echo "Step 6: Checking S3 notification configuration..."
aws s3api get-bucket-notification-configuration \
    --bucket raw-documents-151534200269-us-east-1 | jq '.LambdaFunctionConfigurations[] | {Id, LambdaFunctionArn, Events, Filter}'
echo ""

# Cleanup
rm -f $TEST_FILE

echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "If status is still PENDING_UPLOAD, check:"
echo "1. S3 notification configuration (above)"
echo "2. ValidateDoc Lambda permissions"
echo "3. ValidateDoc Lambda logs for errors"
