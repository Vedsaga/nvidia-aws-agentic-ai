#!/bin/bash

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ $1${NC}"; }

# Load environment variables
source scripts/load_env.sh
load_env

echo -e "\n${BLUE}=== Model Endpoint Testing ===${NC}\n"

# Check EKS endpoints
HAS_EKS_GENERATE=false
HAS_EKS_EMBED=false
if [ -n "$APP_GENERATE_ENDPOINT_URL" ] && [ "$APP_GENERATE_ENDPOINT_URL" != "https://integrate.api.nvidia.com" ]; then
    HAS_EKS_GENERATE=true
fi
if [ -n "$APP_EMBED_ENDPOINT_URL" ] && [ "$APP_EMBED_ENDPOINT_URL" != "https://integrate.api.nvidia.com" ]; then
    HAS_EKS_EMBED=true
fi

# Check NVIDIA API keys
HAS_NVIDIA_GENERATE=false
HAS_NVIDIA_EMBED=false
if [ -n "$NVIDIA_MODEL_GENERATE" ]; then
    HAS_NVIDIA_GENERATE=true
fi
if [ -n "$NVIDIA_MODEL_EMBADDING" ]; then
    HAS_NVIDIA_EMBED=true
fi

# Test EKS Generator
if [ "$HAS_EKS_GENERATE" = true ]; then
    echo -e "${BLUE}--- Testing EKS Generator Endpoint ---${NC}"
    echo "URL: $APP_GENERATE_ENDPOINT_URL"
    
    cat > /tmp/generator_payload.json <<EOF
{
  "model": "nvidia/llama-3.1-nemotron-nano-8b-v1",
  "messages": [{"role": "user", "content": "What is the capital of France?"}],
  "max_tokens": 128
}
EOF
    
    RESPONSE=$(curl -s -X POST "$APP_GENERATE_ENDPOINT_URL/v1/chat/completions" \
        -H 'Content-Type: application/json' \
        -d @/tmp/generator_payload.json)
    
    echo "$RESPONSE"
    
    if echo "$RESPONSE" | grep -q '"choices"'; then
        print_success "EKS Generator endpoint working"
    else
        print_error "EKS Generator endpoint failed"
    fi
    echo ""
else
    print_warning "EKS Generator endpoint not configured - skipping"
    echo ""
fi

# Test NVIDIA Cloud Generator
if [ "$HAS_NVIDIA_GENERATE" = true ]; then
    echo -e "${BLUE}--- Testing NVIDIA Cloud Generator ---${NC}"
    echo "URL: https://integrate.api.nvidia.com"
    
    cat > /tmp/nvidia_gen_payload.json <<EOF
{
  "model": "nvidia/llama-3.1-nemotron-nano-8b-v1",
  "messages": [{"role": "user", "content": "What is the capital of France?"}],
  "max_tokens": 128
}
EOF
    
    RESPONSE=$(curl -s -X POST "https://integrate.api.nvidia.com/v1/chat/completions" \
        -H "Authorization: Bearer $NVIDIA_MODEL_GENERATE" \
        -H 'Content-Type: application/json' \
        -d @/tmp/nvidia_gen_payload.json)
    
    echo "$RESPONSE"
    
    if echo "$RESPONSE" | grep -q '"choices"'; then
        print_success "NVIDIA Cloud Generator working"
    else
        print_error "NVIDIA Cloud Generator failed"
    fi
    echo ""
else
    print_warning "NVIDIA_MODEL_GENERATE not set - skipping NVIDIA Cloud Generator test"
    echo ""
fi

# Test EKS Embedder
if [ "$HAS_EKS_EMBED" = true ]; then
    echo -e "${BLUE}--- Testing EKS Embedder Endpoint ---${NC}"
    echo "URL: $APP_EMBED_ENDPOINT_URL"
    
    cat > /tmp/embedder_payload.json <<EOF
{
  "model": "nvidia/llama-3.2-nv-embedqa-1b-v2",
  "input": ["This is a test sentence for embedding."],
  "input_type": "query"
}
EOF
    
    RESPONSE=$(curl -s -X POST "$APP_EMBED_ENDPOINT_URL/v1/embeddings" \
        -H 'Content-Type: application/json' \
        -d @/tmp/embedder_payload.json)
    
    echo "$RESPONSE"
    
    if echo "$RESPONSE" | grep -q '"embedding"'; then
        print_success "EKS Embedder endpoint working"
    else
        print_error "EKS Embedder endpoint failed"
    fi
    echo ""
else
    print_warning "EKS Embedder endpoint not configured - skipping"
    echo ""
fi

# Test NVIDIA Cloud Embedder
if [ "$HAS_NVIDIA_EMBED" = true ]; then
    echo -e "${BLUE}--- Testing NVIDIA Cloud Embedder ---${NC}"
    echo "URL: https://integrate.api.nvidia.com"
    
    cat > /tmp/nvidia_embed_payload.json <<EOF
{
  "model": "nvidia/llama-3.2-nv-embedqa-1b-v2",
  "input": ["This is a test sentence for embedding."],
  "input_type": "query"
}
EOF
    
    RESPONSE=$(curl -s -X POST "https://integrate.api.nvidia.com/v1/embeddings" \
        -H "Authorization: Bearer $NVIDIA_MODEL_EMBADDING" \
        -H 'Content-Type: application/json' \
        -d @/tmp/nvidia_embed_payload.json)
    
    echo "$RESPONSE"
    
    if echo "$RESPONSE" | grep -q '"embedding"'; then
        print_success "NVIDIA Cloud Embedder working"
    else
        print_error "NVIDIA Cloud Embedder failed"
    fi
    echo ""
else
    print_warning "NVIDIA_MODEL_EMBADDING not set - skipping NVIDIA Cloud Embedder test"
    echo ""
fi

# Cleanup
rm -f /tmp/generator_payload.json /tmp/nvidia_gen_payload.json /tmp/embedder_payload.json /tmp/nvidia_embed_payload.json /tmp/retrieval_payload.json

echo -e "${BLUE}=== Test Complete ===${NC}\n"
