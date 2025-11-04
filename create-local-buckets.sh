#!/bin/bash
set -e

ENDPOINT="http://localhost:4566"

echo "Creating S3 buckets in LocalStack..."

aws s3 mb s3://raw-documents-local --endpoint-url $ENDPOINT --region us-east-1 2>/dev/null || echo "raw-documents-local already exists"
aws s3 mb s3://verified-documents-local --endpoint-url $ENDPOINT --region us-east-1 2>/dev/null || echo "verified-documents-local already exists"
aws s3 mb s3://knowledge-graph-local --endpoint-url $ENDPOINT --region us-east-1 2>/dev/null || echo "knowledge-graph-local already exists"

echo ""
echo "✓ All buckets created"
echo ""
echo "Verify buckets:"
echo "aws s3 ls --endpoint-url $ENDPOINT --region us-east-1"
