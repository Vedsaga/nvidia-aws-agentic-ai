#!/bin/bash

################################################################################
# Kāraka RAG System - Unified Deployment Script
# Usage:
#   ./deploy.sh --env personal                    # Deploy full system
#   ./deploy.sh --env personal --sagemaker-only   # Deploy only SageMaker endpoints
#   ./deploy.sh --env personal --skip-sagemaker   # Skip SageMaker deployment
#   ./deploy.sh --env personal --test             # Deploy and test
#   ./deploy.sh --cleanup                         # Remove all resources
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Print functions
print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

print_step() { echo -e "${GREEN}▶ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }

error_exit() {
    print_error "$1"
    exit 1
}

# Parse arguments
ENV_TYPE=""
RUN_TEST=false
CLEANUP=false
SAGEMAKER_ONLY=false
SKIP_SAGEMAKER=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENV_TYPE="$2"
            shift 2
            ;;
        --test)
            RUN_TEST=true
            shift
            ;;
        --cleanup)
            CLEANUP=true
            shift
            ;;
        --sagemaker-only)
            SAGEMAKER_ONLY=true
            shift
            ;;
        --skip-sagemaker)
            SKIP_SAGEMAKER=true
            shift
            ;;
        *)
            echo "Usage: $0 --env [personal|vocareum] [--sagemaker-only] [--skip-sagemaker] [--test] [--cleanup]"
            exit 1
            ;;
    esac
done

################################################################################
# SageMaker NIM Deployment Function
################################################################################
deploy_sagemaker_nim() {
    print_header "SageMaker NVIDIA NIM Deployment"
    
    REGION="us-east-1"
    # NVIDIA NIM requires ml.g6e.2xlarge minimum (ml.g5.xlarge is too small)
    HACKATHON_INSTANCE_TYPE="ml.g6e.2xlarge"
    
    # Model Package ARNs from AWS Marketplace (shared account get ACCOUNT_ID from env)
    NEMOTRON_MODEL_PACKAGE_ARN="arn:aws:sagemaker:us-east-1:${AWS_ACCOUNT_ID}:model-package/llama3-1-nemotron-nano-8b-v1-n-710c29bc58f0303aac54c77c70fc229a"
    EMBED_MODEL_PACKAGE_ARN="arn:aws:sagemaker:us-east-1:${AWS_ACCOUNT_ID}:model-package/llama-3-2-nv-embedqa-1b-v2-nim-790d4634e92a3e39a57f47cf420fb687"
    
    # Resource names
    NEMOTRON_MODEL_NAME="nemotron-karaka-model"
    NEMOTRON_ENDPOINT_CONFIG_NAME="nemotron-karaka-config"
    NEMOTRON_ENDPOINT_NAME="nemotron-karaka-endpoint"
    
    EMBED_MODEL_NAME="embedding-karaka-model"
    EMBED_ENDPOINT_CONFIG_NAME="embedding-karaka-config"
    EMBED_ENDPOINT_NAME="embedding-karaka-endpoint"
    
    print_warning "Account: ${CURRENT_ACCOUNT_ID}"
    print_warning "Instance type: ${HACKATHON_INSTANCE_TYPE}"
    print_warning "Note: Using hackathon-approved NVIDIA NIM models"
    echo ""
    
    # Deploy Nemotron Nano 8B
    print_step "Deploying Nemotron Nano 8B (Reasoning Model)..."
    
    if aws sagemaker describe-model --model-name ${NEMOTRON_MODEL_NAME} --region ${REGION} 2>/dev/null; then
        print_warning "Model exists, deleting..."
        aws sagemaker delete-model --model-name ${NEMOTRON_MODEL_NAME} --region ${REGION}
        sleep 2
    fi
    
    aws sagemaker create-model \
        --model-name ${NEMOTRON_MODEL_NAME} \
        --execution-role-arn ${EXECUTION_ROLE_ARN} \
        --primary-container ModelPackageName=${NEMOTRON_MODEL_PACKAGE_ARN} \
        --enable-network-isolation \
        --region ${REGION} > /dev/null
    
    if aws sagemaker describe-endpoint-config --endpoint-config-name ${NEMOTRON_ENDPOINT_CONFIG_NAME} --region ${REGION} 2>/dev/null; then
        aws sagemaker delete-endpoint-config --endpoint-config-name ${NEMOTRON_ENDPOINT_CONFIG_NAME} --region ${REGION}
        sleep 2
    fi
    
    aws sagemaker create-endpoint-config \
        --endpoint-config-name ${NEMOTRON_ENDPOINT_CONFIG_NAME} \
        --production-variants VariantName=variant-1,ModelName=${NEMOTRON_MODEL_NAME},InstanceType=${HACKATHON_INSTANCE_TYPE},InitialInstanceCount=1,ModelDataDownloadTimeoutInSeconds=3600 \
        --region ${REGION} > /dev/null
    
    if aws sagemaker describe-endpoint --endpoint-name ${NEMOTRON_ENDPOINT_NAME} --region ${REGION} 2>/dev/null; then
        ENDPOINT_STATUS=$(aws sagemaker describe-endpoint --endpoint-name ${NEMOTRON_ENDPOINT_NAME} --region ${REGION} --query 'EndpointStatus' --output text)
        if [ "$ENDPOINT_STATUS" == "InService" ]; then
            print_success "Nemotron endpoint already InService"
        else
            print_warning "Endpoint status: ${ENDPOINT_STATUS}, recreating..."
            aws sagemaker delete-endpoint --endpoint-name ${NEMOTRON_ENDPOINT_NAME} --region ${REGION}
            sleep 5
            aws sagemaker create-endpoint \
                --endpoint-name ${NEMOTRON_ENDPOINT_NAME} \
                --endpoint-config-name ${NEMOTRON_ENDPOINT_CONFIG_NAME} \
                --region ${REGION} > /dev/null
        fi
    else
        aws sagemaker create-endpoint \
            --endpoint-name ${NEMOTRON_ENDPOINT_NAME} \
            --endpoint-config-name ${NEMOTRON_ENDPOINT_CONFIG_NAME} \
            --region ${REGION} > /dev/null
    fi
    
    print_step "Waiting for Nemotron endpoint (10-20 min)..."
    aws sagemaker wait endpoint-in-service --endpoint-name ${NEMOTRON_ENDPOINT_NAME} --region ${REGION}
    print_success "Nemotron endpoint InService"
    
    # Deploy EmbedQA
    print_step "Deploying EmbedQA (Embedding Model)..."
    
    if aws sagemaker describe-model --model-name ${EMBED_MODEL_NAME} --region ${REGION} 2>/dev/null; then
        aws sagemaker delete-model --model-name ${EMBED_MODEL_NAME} --region ${REGION}
        sleep 2
    fi
    
    aws sagemaker create-model \
        --model-name ${EMBED_MODEL_NAME} \
        --execution-role-arn ${EXECUTION_ROLE_ARN} \
        --primary-container ModelPackageName=${EMBED_MODEL_PACKAGE_ARN} \
        --enable-network-isolation \
        --region ${REGION} > /dev/null
    
    if aws sagemaker describe-endpoint-config --endpoint-config-name ${EMBED_ENDPOINT_CONFIG_NAME} --region ${REGION} 2>/dev/null; then
        aws sagemaker delete-endpoint-config --endpoint-config-name ${EMBED_ENDPOINT_CONFIG_NAME} --region ${REGION}
        sleep 2
    fi
    
    aws sagemaker create-endpoint-config \
        --endpoint-config-name ${EMBED_ENDPOINT_CONFIG_NAME} \
        --production-variants VariantName=variant-1,ModelName=${EMBED_MODEL_NAME},InstanceType=${HACKATHON_INSTANCE_TYPE},InitialInstanceCount=1,ModelDataDownloadTimeoutInSeconds=3600 \
        --region ${REGION} > /dev/null
    
    if aws sagemaker describe-endpoint --endpoint-name ${EMBED_ENDPOINT_NAME} --region ${REGION} 2>/dev/null; then
        ENDPOINT_STATUS=$(aws sagemaker describe-endpoint --endpoint-name ${EMBED_ENDPOINT_NAME} --region ${REGION} --query 'EndpointStatus' --output text)
        if [ "$ENDPOINT_STATUS" == "InService" ]; then
            print_success "Embedding endpoint already InService"
        else
            aws sagemaker delete-endpoint --endpoint-name ${EMBED_ENDPOINT_NAME} --region ${REGION}
            sleep 5
            aws sagemaker create-endpoint \
                --endpoint-name ${EMBED_ENDPOINT_NAME} \
                --endpoint-config-name ${EMBED_ENDPOINT_CONFIG_NAME} \
                --region ${REGION} > /dev/null
        fi
    else
        aws sagemaker create-endpoint \
            --endpoint-name ${EMBED_ENDPOINT_NAME} \
            --endpoint-config-name ${EMBED_ENDPOINT_CONFIG_NAME} \
            --region ${REGION} > /dev/null
    fi
    
    print_step "Waiting for Embedding endpoint (10-20 min)..."
    aws sagemaker wait endpoint-in-service --endpoint-name ${EMBED_ENDPOINT_NAME} --region ${REGION}
    print_success "Embedding endpoint InService"
}

################################################################################
# Cleanup Function
################################################################################
cleanup_all() {
    print_header "Cleanup - Remove All Resources"
    
    echo "This will DELETE all deployed resources:"
    echo "  - SageMaker Endpoints (2)"
    echo "  - Lambda Functions (4)"
    echo "  - API Gateway"
    echo "  - Neo4j EC2 Instance"
    echo "  - Security Groups"
    echo "  - S3 Bucket (and all data)"
    echo "  - IAM Roles"
    echo ""
    read -p "Are you sure? Type 'DELETE' to confirm: " confirm
    
    if [ "$confirm" != "DELETE" ]; then
        print_warning "Cleanup cancelled"
        exit 0
    fi
    
    if [ -f .env ]; then
        set -a
        source .env
        set +a
    fi
    
    print_step "Starting cleanup..."
    
    # Delete SageMaker endpoints
    print_step "Deleting SageMaker endpoints..."
    for endpoint in nemotron-karaka-endpoint embedding-karaka-endpoint; do
        if aws sagemaker delete-endpoint --endpoint-name "$endpoint" 2>/dev/null; then
            print_success "Deleted endpoint $endpoint"
        fi
    done
    
    # Delete endpoint configs
    for config in nemotron-karaka-config embedding-karaka-config; do
        aws sagemaker delete-endpoint-config --endpoint-config-name "$config" 2>/dev/null || true
    done
    
    # Delete models
    for model in nemotron-karaka-model embedding-karaka-model; do
        aws sagemaker delete-model --model-name "$model" 2>/dev/null || true
    done
    
    # Delete Lambda functions
    print_step "Deleting Lambda functions..."
    for func in karaka-ingestion-handler karaka-status-handler karaka-query-handler karaka-graph-handler; do
        if aws lambda delete-function --function-name "$func" 2>/dev/null; then
            print_success "Deleted $func"
        fi
    done
    
    # Delete API Gateway
    print_step "Deleting API Gateway..."
    API_ID=$(aws apigateway get-rest-apis --query "items[?name=='karaka-rag-api'].id" --output text 2>/dev/null)
    if [ -n "$API_ID" ] && [ "$API_ID" != "None" ]; then
        aws apigateway delete-rest-api --rest-api-id "$API_ID"
        print_success "Deleted API Gateway"
    fi
    
    # Terminate Neo4j instance
    print_step "Terminating Neo4j instance..."
    INSTANCE_ID=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=karaka-neo4j" "Name=instance-state-name,Values=running,stopped" \
        --query 'Reservations[0].Instances[0].InstanceId' \
        --output text 2>/dev/null)
    if [ -n "$INSTANCE_ID" ] && [ "$INSTANCE_ID" != "None" ]; then
        aws ec2 terminate-instances --instance-ids "$INSTANCE_ID" > /dev/null
        print_success "Terminating $INSTANCE_ID"
    fi
    
    # Delete security group
    sleep 30
    SG_ID=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=karaka-neo4j-sg" \
        --query "SecurityGroups[0].GroupId" \
        --output text 2>/dev/null)
    if [ -n "$SG_ID" ] && [ "$SG_ID" != "None" ]; then
        aws ec2 delete-security-group --group-id "$SG_ID" 2>/dev/null || true
    fi
    
    # Delete S3 bucket
    if [ -n "$S3_BUCKET" ]; then
        aws s3 rm "s3://$S3_BUCKET" --recursive 2>/dev/null || true
        aws s3 rb "s3://$S3_BUCKET" 2>/dev/null || true
    fi
    
    print_success "Cleanup complete!"
    exit 0
}

# Handle cleanup
if [ "$CLEANUP" = true ]; then
    cleanup_all
fi

# Validate environment type
if [ -z "$ENV_TYPE" ]; then
    error_exit "Environment type required. Use: --env personal or --env vocareum"
fi

if [ "$ENV_TYPE" != "personal" ] && [ "$ENV_TYPE" != "vocareum" ]; then
    error_exit "Invalid environment. Use: personal or vocareum"
fi

################################################################################
# Load Environment
################################################################################
print_header "Kāraka RAG System - Deployment"

ENV_FILE=".env.${ENV_TYPE}"
if [ ! -f "$ENV_FILE" ]; then
    error_exit "Environment file not found: $ENV_FILE"
fi

print_step "Loading environment: $ENV_TYPE"
cp "$ENV_FILE" .env
set -a
source .env
set +a
print_success "Environment loaded from $ENV_FILE"

# Activate virtual environment
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
    print_success "Virtual environment activated"
fi

# Verify AWS credentials
print_step "Verifying AWS credentials..."
if aws sts get-caller-identity > /dev/null 2>&1; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    print_success "AWS credentials valid (Account: $ACCOUNT_ID)"
else
    error_exit "AWS credentials are invalid or expired"
fi

export AWS_REGION=${AWS_REGION:-us-east-1}
export S3_BUCKET=${S3_BUCKET:-karaka-rag-${ENV_TYPE}-$(date +%s)}

################################################################################
# Deploy SageMaker NIM Endpoints
################################################################################
if [ "$SKIP_SAGEMAKER" != true ]; then
    if [ -z "${EXECUTION_ROLE_ARN}" ]; then
        print_warning "EXECUTION_ROLE_ARN not set, skipping SageMaker deployment"
        print_warning "Add EXECUTION_ROLE_ARN to $ENV_FILE to deploy SageMaker endpoints"
    else
        deploy_sagemaker_nim
        
        # Update env file with endpoint names
        if ! grep -q "SAGEMAKER_NEMOTRON_ENDPOINT=nemotron-karaka-endpoint" "$ENV_FILE"; then
            echo "" >> "$ENV_FILE"
            echo "# SageMaker Endpoints (deployed)" >> "$ENV_FILE"
            echo "SAGEMAKER_NEMOTRON_ENDPOINT=nemotron-karaka-endpoint" >> "$ENV_FILE"
            echo "SAGEMAKER_EMBEDDING_ENDPOINT=embedding-karaka-endpoint" >> "$ENV_FILE"
        fi
        
        # Reload environment
        set -a
        source .env
        set +a
    fi
fi

# Exit if SageMaker-only deployment
if [ "$SAGEMAKER_ONLY" = true ]; then
    print_success "SageMaker deployment complete!"
    exit 0
fi

################################################################################
# S3 Bucket Setup
################################################################################
print_header "Step 1: S3 Bucket Setup"

print_step "Checking S3 bucket: $S3_BUCKET"
if aws s3 ls "s3://$S3_BUCKET" > /dev/null 2>&1; then
    print_success "S3 bucket already exists"
else
    print_step "Creating S3 bucket..."
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3 mb "s3://$S3_BUCKET" --region "$AWS_REGION"
    else
        aws s3 mb "s3://$S3_BUCKET" --region "$AWS_REGION" \
            --create-bucket-configuration LocationConstraint="$AWS_REGION"
    fi
    print_success "Created S3 bucket: $S3_BUCKET"
fi

aws s3api put-bucket-versioning \
    --bucket "$S3_BUCKET" \
    --versioning-configuration Status=Enabled 2>/dev/null || true

################################################################################
# IAM Role Setup
################################################################################
print_header "Step 2: IAM Role Setup"

ROLE_NAME="KarakaRAGLambdaRole"
print_step "Checking IAM role: $ROLE_NAME"

if aws iam get-role --role-name "$ROLE_NAME" > /dev/null 2>&1; then
    LAMBDA_ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
    print_success "IAM role already exists"
else
    print_step "Creating IAM role..."
    
    cat > /tmp/lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
    
    LAMBDA_ROLE_ARN=$(aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
        --description "Execution role for Karaka RAG Lambda functions" \
        --query 'Role.Arn' \
        --output text)
    
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/AmazonS3FullAccess"
    
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
    
    rm /tmp/lambda-trust-policy.json
    print_success "Created IAM role"
    print_warning "Waiting 10 seconds for IAM propagation..."
    sleep 10
fi

echo "  Role ARN: $LAMBDA_ROLE_ARN"

################################################################################
# Package Lambda Functions
################################################################################
print_header "Step 3: Package Lambda Functions"

print_step "Running package script..."
bash infrastructure/package_lambda.sh

if [ ! -f lambda.zip ]; then
    error_exit "Lambda package not created"
fi

print_step "Uploading Lambda package to S3..."
aws s3 cp lambda.zip "s3://$S3_BUCKET/lambda/lambda.zip"
print_success "Lambda package uploaded"

################################################################################
# Deploy Lambda Functions
################################################################################
print_header "Step 4: Deploy Lambda Functions"

declare -A FUNCTIONS=(
    ["karaka-ingestion-handler"]="ingestion_handler.lambda_handler"
    ["karaka-status-handler"]="status_handler.lambda_handler"
    ["karaka-query-handler"]="query_handler.lambda_handler"
    ["karaka-graph-handler"]="graph_handler.lambda_handler"
    ["karaka-health-handler"]="health_handler.lambda_handler"
)

for FUNC_NAME in "${!FUNCTIONS[@]}"; do
    HANDLER="${FUNCTIONS[$FUNC_NAME]}"
    print_step "Deploying $FUNC_NAME..."
    
    if aws lambda get-function --function-name "$FUNC_NAME" > /dev/null 2>&1; then
        for i in {1..30}; do
            STATE=$(aws lambda get-function --function-name "$FUNC_NAME" --query 'Configuration.State' --output text 2>/dev/null || echo "Pending")
            if [ "$STATE" = "Active" ]; then
                break
            fi
            sleep 2
        done
        
        aws lambda update-function-code \
            --function-name "$FUNC_NAME" \
            --s3-bucket "$S3_BUCKET" \
            --s3-key "lambda/lambda.zip" > /dev/null 2>&1 || true
        
        sleep 3
        
        aws lambda update-function-configuration \
            --function-name "$FUNC_NAME" \
            --handler "$HANDLER" \
            --runtime python3.11 \
            --timeout 300 \
            --memory-size 1024 \
            --environment "Variables={
                S3_BUCKET=$S3_BUCKET,
                SAGEMAKER_NEMOTRON_ENDPOINT=${SAGEMAKER_NEMOTRON_ENDPOINT:-},
                SAGEMAKER_EMBEDDING_ENDPOINT=${SAGEMAKER_EMBEDDING_ENDPOINT:-},
                NEO4J_URI=${NEO4J_URI:-bolt://localhost:7687},
                NEO4J_USERNAME=${NEO4J_USERNAME:-neo4j},
                NEO4J_PASSWORD=${NEO4J_PASSWORD:-},
                CONFIDENCE_THRESHOLD=${CONFIDENCE_THRESHOLD:-0.8},
                ENTITY_SIMILARITY_THRESHOLD=${ENTITY_SIMILARITY_THRESHOLD:-0.85}
            }" > /dev/null 2>&1 || true
        
        print_success "Updated $FUNC_NAME"
    else
        aws lambda create-function \
            --function-name "$FUNC_NAME" \
            --runtime python3.11 \
            --role "$LAMBDA_ROLE_ARN" \
            --handler "$HANDLER" \
            --code S3Bucket="$S3_BUCKET",S3Key="lambda/lambda.zip" \
            --timeout 300 \
            --memory-size 1024 \
            --environment "Variables={
                S3_BUCKET=$S3_BUCKET,
                SAGEMAKER_NEMOTRON_ENDPOINT=${SAGEMAKER_NEMOTRON_ENDPOINT:-},
                SAGEMAKER_EMBEDDING_ENDPOINT=${SAGEMAKER_EMBEDDING_ENDPOINT:-},
                NEO4J_URI=${NEO4J_URI:-bolt://localhost:7687},
                NEO4J_USERNAME=${NEO4J_USERNAME:-neo4j},
                NEO4J_PASSWORD=${NEO4J_PASSWORD:-},
                CONFIDENCE_THRESHOLD=${CONFIDENCE_THRESHOLD:-0.8},
                ENTITY_SIMILARITY_THRESHOLD=${ENTITY_SIMILARITY_THRESHOLD:-0.85}
            }" > /dev/null
        
        print_success "Created $FUNC_NAME"
    fi
    sleep 2
done

################################################################################
# Deploy API Gateway
################################################################################
print_header "Step 5: Deploy API Gateway"

print_step "Running API Gateway deployment..."
python3 infrastructure/deploy_api_gateway.py

API_ID=$(aws apigateway get-rest-apis --query "items[?name=='karaka-rag-api'].id" --output text)
API_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"

print_success "API Gateway deployed"
echo "  API URL: $API_URL"

################################################################################
# Deploy Neo4j
################################################################################
print_header "Step 6: Deploy Neo4j Community Edition"

bash infrastructure/deploy_neo4j.sh

NEO4J_INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=karaka-neo4j" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text 2>/dev/null || echo "")

if [ -n "$NEO4J_INSTANCE_ID" ] && [ "$NEO4J_INSTANCE_ID" != "None" ]; then
    NEO4J_PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids "$NEO4J_INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)
    
    NEO4J_URI="bolt://$NEO4J_PUBLIC_IP:7687"
    
    if grep -q "^NEO4J_URI=" .env; then
        sed -i "s|^NEO4J_URI=.*|NEO4J_URI=$NEO4J_URI|" .env
    else
        echo "NEO4J_URI=$NEO4J_URI" >> .env
    fi
    
    set -a
    source .env
    set +a
fi

################################################################################
# Update Lambda with Neo4j URI
################################################################################
print_header "Step 7: Update Lambda Functions"

print_step "Updating Lambda environment variables..."

for FUNC_NAME in "${!FUNCTIONS[@]}"; do
    aws lambda update-function-configuration \
        --function-name "$FUNC_NAME" \
        --environment "Variables={
            S3_BUCKET=$S3_BUCKET,
            SAGEMAKER_NEMOTRON_ENDPOINT=${SAGEMAKER_NEMOTRON_ENDPOINT:-},
            SAGEMAKER_EMBEDDING_ENDPOINT=${SAGEMAKER_EMBEDDING_ENDPOINT:-},
            NEO4J_URI=${NEO4J_URI:-bolt://localhost:7687},
            NEO4J_USERNAME=${NEO4J_USERNAME:-neo4j},
            NEO4J_PASSWORD=${NEO4J_PASSWORD:-},
            CONFIDENCE_THRESHOLD=${CONFIDENCE_THRESHOLD:-0.8},
            ENTITY_SIMILARITY_THRESHOLD=${ENTITY_SIMILARITY_THRESHOLD:-0.85}
        }" > /dev/null 2>&1 || true
    sleep 2
done

print_success "Lambda functions updated"

################################################################################
# Update Environment File
################################################################################
print_header "Step 8: Update Environment Configuration"

sed -i "s|^API_GATEWAY_URL=.*|API_GATEWAY_URL=$API_URL|" "$ENV_FILE" 2>/dev/null || echo "API_GATEWAY_URL=$API_URL" >> "$ENV_FILE"
sed -i "s|^S3_BUCKET=.*|S3_BUCKET=$S3_BUCKET|" "$ENV_FILE" 2>/dev/null || echo "S3_BUCKET=$S3_BUCKET" >> "$ENV_FILE"
sed -i "s|^NEO4J_URI=.*|NEO4J_URI=$NEO4J_URI|" "$ENV_FILE" 2>/dev/null || echo "NEO4J_URI=$NEO4J_URI" >> "$ENV_FILE"

cp "$ENV_FILE" .env

print_success "Environment configuration updated in $ENV_FILE"

################################################################################
# Deployment Summary
################################################################################
print_header "Deployment Summary"

echo "Environment: $ENV_TYPE"
echo "AWS Account: $ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo ""
echo "Resources:"
echo "  ✓ S3 Bucket: $S3_BUCKET"
echo "  ✓ IAM Role: $LAMBDA_ROLE_ARN"
echo "  ✓ Lambda Functions: 4 deployed"
echo "  ✓ API Gateway: $API_URL"
if [ -n "$NEO4J_INSTANCE_ID" ] && [ "$NEO4J_INSTANCE_ID" != "None" ]; then
    echo "  ✓ Neo4j: $NEO4J_URI (Instance: $NEO4J_INSTANCE_ID)"
fi
if [ -n "${SAGEMAKER_NEMOTRON_ENDPOINT}" ]; then
    echo "  ✓ SageMaker Nemotron: ${SAGEMAKER_NEMOTRON_ENDPOINT}"
    echo "  ✓ SageMaker Embedding: ${SAGEMAKER_EMBEDDING_ENDPOINT}"
fi
echo ""
echo "Endpoints:"
echo "  GET  $API_URL/graph"
echo "  POST $API_URL/query"
echo "  POST $API_URL/ingest"
echo "  GET  $API_URL/ingest/status/{job_id}"
echo ""

print_success "Deployment completed successfully!"

################################################################################
# Run Tests
################################################################################
if [ "$RUN_TEST" = true ]; then
    print_header "Running Tests"
    
    print_step "Testing /graph endpoint..."
    curl -s -X GET "$API_URL/graph" | python3 -m json.tool
    echo ""
    
    print_step "Testing /query endpoint..."
    curl -s -X POST "$API_URL/query" \
        -H "Content-Type: application/json" \
        -d '{"question": "Test query"}' | python3 -m json.tool
    echo ""
    
    print_success "Tests completed"
fi

echo ""
echo "To test the deployment:"
echo "  ./deploy.sh --env $ENV_TYPE --test"
echo ""
echo "To cleanup all resources:"
echo "  ./deploy.sh --cleanup"
