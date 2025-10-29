#!/bin/bash

source set_vocareum_env.sh

echo "============================================================"
echo "SageMaker NVIDIA NIM Requirements Check"
echo "============================================================"
echo ""

# Check account
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo "✓ AWS Account: $ACCOUNT"
echo ""

# Check if we can describe the model package
echo "Checking NVIDIA NIM model package access..."
NEMOTRON_ARN="arn:aws:sagemaker:us-east-1:151534200269:model-package/llama3-1-nemotron-nano-8b-v1-n-710c29bc58f0303aac54c77c70fc229a"

if aws sagemaker describe-model-package --model-package-name "$NEMOTRON_ARN" --region us-east-1 > /tmp/model_check.json 2>&1; then
    echo "✓ Can access model package metadata"
    
    # Check supported instances
    echo ""
    echo "Supported instance types:"
    cat /tmp/model_check.json | grep -A 20 "SupportedRealtimeInferenceInstanceTypes" | grep "ml\." | sed 's/[",]//g' | sed 's/^[ \t]*/  /'
    
    echo ""
    echo "⚠ PROBLEM: Hackathon allows ml.g5.xlarge, but NVIDIA NIM requires:"
    echo "  - Minimum: ml.g6e.2xlarge OR ml.g5.12xlarge"
    echo ""
    
    # Try to create a test model to check subscription
    echo "Checking marketplace subscription..."
    TEST_MODEL_NAME="test-subscription-check-$$"
    
    if aws sagemaker create-model \
        --model-name "$TEST_MODEL_NAME" \
        --execution-role-arn "arn:aws:iam::${ACCOUNT}:role/KarakaRAGSageMakerRole" \
        --primary-container ModelPackageName="$NEMOTRON_ARN" \
        --region us-east-1 > /dev/null 2>&1; then
        
        echo "✓ Marketplace subscription is active!"
        aws sagemaker delete-model --model-name "$TEST_MODEL_NAME" --region us-east-1 > /dev/null 2>&1
        
        echo ""
        echo "============================================================"
        echo "NEXT STEPS:"
        echo "============================================================"
        echo "1. Contact hackathon organizers to request:"
        echo "   - Allow ml.g6e.2xlarge instance type"
        echo "   OR"
        echo "   - Allow ml.g5.12xlarge instance type"
        echo ""
        echo "2. Current constraint: ml.g5.xlarge (too small for NVIDIA NIM)"
        echo ""
        echo "3. Once approved, run:"
        echo "   ./deploy.sh --env vocareum --sagemaker-only"
        
    else
        ERROR=$(aws sagemaker create-model \
            --model-name "$TEST_MODEL_NAME" \
            --execution-role-arn "arn:aws:iam::${ACCOUNT}:role/KarakaRAGSageMakerRole" \
            --primary-container ModelPackageName="$NEMOTRON_ARN" \
            --region us-east-1 2>&1)
        
        if echo "$ERROR" | grep -q "not subscribed"; then
            echo "✗ NOT SUBSCRIBED to marketplace offering"
            echo ""
            echo "============================================================"
            echo "ACTION REQUIRED:"
            echo "============================================================"
            echo "1. Subscribe to NVIDIA NIM models:"
            echo "   https://aws.amazon.com/marketplace/pp/prodview-dqa44sfw3zyfm"
            echo ""
            echo "2. OR ask hackathon organizers to subscribe your account to:"
            echo "   - Llama 3.1 Nemotron Nano 8B"
            echo "   - NV-EmbedQA 1B v2"
            echo ""
            echo "3. Also request instance type approval:"
            echo "   - ml.g6e.2xlarge (minimum for NVIDIA NIM)"
        else
            echo "✗ Error: $ERROR"
        fi
    fi
else
    echo "✗ Cannot access model package"
    echo "This might be a permissions issue."
fi

rm -f /tmp/model_check.json
