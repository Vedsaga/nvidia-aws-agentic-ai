#!/bin/bash

# Deployment Orchestration Script for Kāraka RAG System
# This script orchestrates the complete AWS deployment process

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo
}

print_step() {
    echo -e "${GREEN}▶ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Check if .env file exists
check_env_file() {
    print_step "Checking for .env file..."
    
    if [ ! -f .env ]; then
        print_error ".env file not found!"
        echo
        echo "Please create a .env file with the following variables:"
        echo "  - AWS_REGION"
        echo "  - AWS_ACCESS_KEY_ID"
        echo "  - AWS_SECRET_ACCESS_KEY"
        echo "  - S3_BUCKET"
        echo "  - NEO4J_URI"
        echo "  - NEO4J_USERNAME"
        echo "  - NEO4J_PASSWORD"
        echo
        echo "You can copy .env.example and fill in your values:"
        echo "  cp .env.example .env"
        echo
        exit 1
    fi
    
    print_success ".env file found"
    echo
}

# Load environment variables
load_env_vars() {
    print_step "Loading environment variables..."
    
    # Export variables from .env file
    set -a
    source .env
    set +a
    
    # Validate required variables
    REQUIRED_VARS=(
        "AWS_REGION"
        "S3_BUCKET"
        "NEO4J_URI"
        "NEO4J_USERNAME"
        "NEO4J_PASSWORD"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            print_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    print_success "Environment variables loaded"
    echo "  AWS Region: $AWS_REGION"
    echo "  S3 Bucket: $S3_BUCKET"
    echo "  Neo4j URI: $NEO4J_URI"
    echo
}

# Create S3 bucket for job tracking
create_s3_bucket() {
    print_step "Creating S3 bucket for job tracking..."
    
    # Check if bucket exists
    if aws s3 ls "s3://$S3_BUCKET" 2>/dev/null; then
        print_success "S3 bucket $S3_BUCKET already exists"
    else
        # Create bucket
        if [ "$AWS_REGION" = "us-east-1" ]; then
            aws s3 mb "s3://$S3_BUCKET" --region "$AWS_REGION"
        else
            aws s3 mb "s3://$S3_BUCKET" --region "$AWS_REGION" --create-bucket-configuration LocationConstraint="$AWS_REGION"
        fi
        print_success "Created S3 bucket: $S3_BUCKET"
    fi
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "$S3_BUCKET" \
        --versioning-configuration Status=Enabled
    
    print_success "S3 bucket configured"
    echo
}

# Deploy SageMaker endpoints
deploy_sagemaker() {
    print_step "Deploying SageMaker endpoints..."
    echo
    
    python3 infrastructure/deploy_sagemaker.py
    
    if [ $? -ne 0 ]; then
        print_error "SageMaker deployment failed"
        exit 1
    fi
    
    print_success "SageMaker endpoints deployed"
    echo
}

# Package Lambda functions
package_lambda() {
    print_step "Packaging Lambda functions..."
    echo
    
    bash infrastructure/package_lambda.sh
    
    if [ $? -ne 0 ]; then
        print_error "Lambda packaging failed"
        exit 1
    fi
    
    print_success "Lambda functions packaged"
    echo
}

# Get or create Lambda execution role
get_lambda_role() {
    print_step "Setting up Lambda execution role..."
    
    ROLE_NAME="KarakaRAGLambdaRole"
    
    # Check if role exists
    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text 2>/dev/null || echo "")
    
    if [ -z "$ROLE_ARN" ]; then
        print_step "Creating Lambda execution role..."
        
        # Create trust policy
        cat > /tmp/lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
        
        # Create role
        ROLE_ARN=$(aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
            --description "Execution role for Kāraka RAG Lambda functions" \
            --query 'Role.Arn' \
            --output text)
        
        # Attach policies
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/AmazonS3FullAccess"
        
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
        
        # Clean up temp file
        rm /tmp/lambda-trust-policy.json
        
        print_success "Created Lambda execution role"
        print_warning "Waiting 10 seconds for role propagation..."
        sleep 10
    else
        print_success "Using existing Lambda execution role"
    fi
    
    echo "  Role ARN: $ROLE_ARN"
    echo
    
    echo "$ROLE_ARN"
}

# Deploy Lambda function
deploy_lambda_function() {
    local FUNCTION_NAME=$1
    local HANDLER=$2
    local ROLE_ARN=$3
    
    print_step "Deploying Lambda function: $FUNCTION_NAME..."
    
    # Check if function exists
    if aws lambda get-function --function-name "$FUNCTION_NAME" 2>/dev/null; then
        # Update existing function
        aws lambda update-function-code \
            --function-name "$FUNCTION_NAME" \
            --zip-file fileb://lambda.zip \
            --no-cli-pager > /dev/null
        
        # Update configuration
        aws lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --handler "$HANDLER" \
            --runtime python3.11 \
            --timeout 300 \
            --memory-size 1024 \
            --environment "Variables={
                AWS_REGION=$AWS_REGION,
                S3_BUCKET=$S3_BUCKET,
                SAGEMAKER_NEMOTRON_ENDPOINT=$SAGEMAKER_NEMOTRON_ENDPOINT,
                SAGEMAKER_EMBEDDING_ENDPOINT=$SAGEMAKER_EMBEDDING_ENDPOINT,
                NEO4J_URI=$NEO4J_URI,
                NEO4J_USERNAME=$NEO4J_USERNAME,
                NEO4J_PASSWORD=$NEO4J_PASSWORD,
                CONFIDENCE_THRESHOLD=${CONFIDENCE_THRESHOLD:-0.8},
                ENTITY_SIMILARITY_THRESHOLD=${ENTITY_SIMILARITY_THRESHOLD:-0.85}
            }" \
            --no-cli-pager > /dev/null
        
        print_success "Updated Lambda function: $FUNCTION_NAME"
    else
        # Create new function
        aws lambda create-function \
            --function-name "$FUNCTION_NAME" \
            --runtime python3.11 \
            --role "$ROLE_ARN" \
            --handler "$HANDLER" \
            --zip-file fileb://lambda.zip \
            --timeout 300 \
            --memory-size 1024 \
            --environment "Variables={
                AWS_REGION=$AWS_REGION,
                S3_BUCKET=$S3_BUCKET,
                SAGEMAKER_NEMOTRON_ENDPOINT=$SAGEMAKER_NEMOTRON_ENDPOINT,
                SAGEMAKER_EMBEDDING_ENDPOINT=$SAGEMAKER_EMBEDDING_ENDPOINT,
                NEO4J_URI=$NEO4J_URI,
                NEO4J_USERNAME=$NEO4J_USERNAME,
                NEO4J_PASSWORD=$NEO4J_PASSWORD,
                CONFIDENCE_THRESHOLD=${CONFIDENCE_THRESHOLD:-0.8},
                ENTITY_SIMILARITY_THRESHOLD=${ENTITY_SIMILARITY_THRESHOLD:-0.85}
            }" \
            --no-cli-pager > /dev/null
        
        print_success "Created Lambda function: $FUNCTION_NAME"
    fi
}

# Deploy all Lambda functions
deploy_lambda_functions() {
    print_step "Deploying Lambda functions..."
    echo
    
    # Get Lambda execution role
    LAMBDA_ROLE_ARN=$(get_lambda_role)
    
    # Deploy each Lambda function
    deploy_lambda_function "karaka-ingestion-handler" "ingestion_handler.lambda_handler" "$LAMBDA_ROLE_ARN"
    deploy_lambda_function "karaka-status-handler" "status_handler.lambda_handler" "$LAMBDA_ROLE_ARN"
    deploy_lambda_function "karaka-query-handler" "query_handler.lambda_handler" "$LAMBDA_ROLE_ARN"
    deploy_lambda_function "karaka-graph-handler" "graph_handler.lambda_handler" "$LAMBDA_ROLE_ARN"
    
    print_success "All Lambda functions deployed"
    echo
}

# Deploy API Gateway
deploy_api_gateway() {
    print_step "Deploying API Gateway..."
    echo
    
    python3 infrastructure/deploy_api_gateway.py
    
    if [ $? -ne 0 ]; then
        print_error "API Gateway deployment failed"
        exit 1
    fi
    
    print_success "API Gateway deployed"
    echo
}

# Output deployment summary
output_summary() {
    print_header "Deployment Summary"
    
    # Get API Gateway URL
    API_ID=$(aws apigateway get-rest-apis --query "items[?name=='karaka-rag-api'].id" --output text)
    API_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"
    
    echo "AWS Resources:"
    echo "  Region: $AWS_REGION"
    echo "  S3 Bucket: $S3_BUCKET"
    echo
    echo "SageMaker Endpoints:"
    echo "  Nemotron: $SAGEMAKER_NEMOTRON_ENDPOINT"
    echo "  Embedding: $SAGEMAKER_EMBEDDING_ENDPOINT"
    echo
    echo "Lambda Functions:"
    echo "  karaka-ingestion-handler"
    echo "  karaka-status-handler"
    echo "  karaka-query-handler"
    echo "  karaka-graph-handler"
    echo
    echo "API Gateway:"
    echo "  API URL: $API_URL"
    echo
    echo "Endpoints:"
    echo "  POST   $API_URL/ingest"
    echo "  GET    $API_URL/ingest/status/{job_id}"
    echo "  POST   $API_URL/query"
    echo "  GET    $API_URL/graph"
    echo
    echo "Neo4j:"
    echo "  URI: $NEO4J_URI"
    echo
    print_success "Deployment completed successfully!"
    echo
    echo "Next steps:"
    echo "  1. Test the ingestion endpoint with a sample document"
    echo "  2. Monitor CloudWatch logs for any errors"
    echo "  3. Query the graph using the query endpoint"
    echo
}

# Main deployment flow
main() {
    print_header "Kāraka RAG System - AWS Deployment"
    
    # Step 1: Check and load environment
    check_env_file
    load_env_vars
    
    # Step 2: Create S3 bucket
    print_header "Step 1: S3 Bucket Setup"
    create_s3_bucket
    
    # Step 3: Deploy SageMaker endpoints
    print_header "Step 2: SageMaker Deployment"
    deploy_sagemaker
    
    # Step 4: Package Lambda functions
    print_header "Step 3: Lambda Packaging"
    package_lambda
    
    # Step 5: Deploy Lambda functions
    print_header "Step 4: Lambda Deployment"
    deploy_lambda_functions
    
    # Step 6: Deploy API Gateway
    print_header "Step 5: API Gateway Deployment"
    deploy_api_gateway
    
    # Step 7: Output summary
    output_summary
}

# Run main function
main

