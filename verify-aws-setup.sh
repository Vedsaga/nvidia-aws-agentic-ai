#!/bin/bash

# Load environment variables from .env file
set -a
source .env
set +a

echo "=========================================="
echo "AWS Setup Verification Script"
echo "=========================================="
echo ""

# Check if AWS CLI is installed
echo "1. Checking AWS CLI installation..."
if command -v aws &> /dev/null; then
    echo "   ✓ AWS CLI is installed"
    aws --version
else
    echo "   ✗ AWS CLI is NOT installed"
    echo "   Install with: sudo apt-get install awscli -y"
    exit 1
fi
echo ""

# Check environment variables
echo "2. Checking environment variables..."
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "   ✗ AWS_ACCESS_KEY_ID is not set"
    exit 1
else
    echo "   ✓ AWS_ACCESS_KEY_ID is set (${AWS_ACCESS_KEY_ID:0:10}...)"
fi

if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "   ✗ AWS_SECRET_ACCESS_KEY is not set"
    exit 1
else
    echo "   ✓ AWS_SECRET_ACCESS_KEY is set (${AWS_SECRET_ACCESS_KEY:0:10}...)"
fi

if [ -z "$AWS_SESSION_TOKEN" ]; then
    echo "   ✗ AWS_SESSION_TOKEN is not set"
    exit 1
else
    echo "   ✓ AWS_SESSION_TOKEN is set (${AWS_SESSION_TOKEN:0:20}...)"
fi

if [ -z "$AWS_DEFAULT_REGION" ]; then
    echo "   ⚠ AWS_DEFAULT_REGION is not set, using us-east-1"
    export AWS_DEFAULT_REGION=us-east-1
else
    echo "   ✓ AWS_DEFAULT_REGION is set to $AWS_DEFAULT_REGION"
fi
echo ""

# Test AWS connection
echo "3. Testing AWS connection..."
echo "   Getting caller identity..."
if aws sts get-caller-identity 2>&1; then
    echo "   ✓ Successfully connected to AWS!"
else
    echo "   ✗ Failed to connect to AWS"
    echo "   Your session may have expired. Get fresh credentials from Vocareum."
    exit 1
fi
echo ""

# List available regions
echo "4. Listing available AWS regions..."
aws ec2 describe-regions --query 'Regions[].RegionName' --output table
echo ""

# Check S3 access
echo "5. Testing S3 access..."
if aws s3 ls 2>&1 | head -5; then
    echo "   ✓ S3 access confirmed"
else
    echo "   ⚠ S3 access may be limited or no buckets exist"
fi
echo ""

# Check SSH key file
echo "6. Checking SSH key file..."
if [ -f "$SSH_KEY_PEM" ]; then
    echo "   ✓ SSH key found at $SSH_KEY_PEM"
    ls -lh "$SSH_KEY_PEM"
    
    # Check permissions
    PERMS=$(stat -c "%a" "$SSH_KEY_PEM")
    if [ "$PERMS" = "400" ] || [ "$PERMS" = "600" ]; then
        echo "   ✓ SSH key has correct permissions ($PERMS)"
    else
        echo "   ⚠ SSH key permissions are $PERMS (should be 400 or 600)"
        echo "   Run: chmod 400 $SSH_KEY_PEM"
    fi
else
    echo "   ⚠ SSH key not found at $SSH_KEY_PEM"
    echo "   Download it from Vocareum 'Cloud access' section"
fi
echo ""

echo "=========================================="
echo "Setup verification complete!"
echo "=========================================="
