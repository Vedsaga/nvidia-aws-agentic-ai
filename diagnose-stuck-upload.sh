#!/bin/bash

# Diagnose why upload is stuck at PENDING_UPLOAD

if [ -z "$1" ]; then
    echo "Usage: $0 <job_id>"
    exit 1
fi

JOB_ID=$1

echo "=========================================="
echo "Diagnosing Job: $JOB_ID"
echo "=========================================="
echo ""

# Check job status in DynamoDB
echo "1. Checking DocumentJobs table..."
aws dynamodb get-item \
    --table-name DocumentJobs \
    --key "{\"job_id\":{\"S\":\"$JOB_ID\"}}" \
    --output json | jq '.Item'
echo ""

# Check if file exists in raw bucket
echo "2. Checking raw bucket for uploaded file..."
aws s3 ls s3://raw-documents-151534200269-us-east-1/$JOB_ID/ || echo "No files found"
echo ""

# Check Lambda function logs
echo "3. Checking ValidateDoc Lambda logs (last 10 minutes)..."
aws logs filter-log-events \
    --log-group-name /aws/lambda/ServerlessStack-ValidateDoc \
    --start-time $(($(date +%s) - 600))000 \
    --filter-pattern "$JOB_ID" \
    --query 'events[].message' \
    --output text || echo "No logs found"
echo ""

# Check SanitizeDoc Lambda logs
echo "4. Checking SanitizeDoc Lambda logs (last 10 minutes)..."
aws logs filter-log-events \
    --log-group-name /aws/lambda/ServerlessStack-SanitizeDoc \
    --start-time $(($(date +%s) - 600))000 \
    --filter-pattern "$JOB_ID" \
    --query 'events[].message' \
    --output text || echo "No logs found"
echo ""

# Check Step Functions executions
echo "5. Checking Step Functions executions..."
aws stepfunctions list-executions \
    --state-machine-arn arn:aws:states:us-east-1:151534200269:stateMachine:KarakaKGProcessing \
    --max-results 5 \
    --output json | jq '.executions[] | {name, status, startDate}'
echo ""

# Check S3 event notifications
echo "6. Checking S3 bucket notification configuration..."
aws s3api get-bucket-notification-configuration \
    --bucket raw-documents-151534200269-us-east-1 | jq '.'
echo ""

echo "=========================================="
echo "Diagnosis Complete"
echo "=========================================="
