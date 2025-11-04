#!/bin/bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
STACK_NAME=${STACK_NAME:-agentic-ai-local}
REGION=${AWS_REGION:-us-east-1}
SAM_TEMPLATE=${SAM_TEMPLATE:-template.yaml}

if ! command -v sam >/dev/null 2>&1; then
  echo "ERROR: AWS SAM CLI is required (pip install aws-sam-cli)" >&2
  exit 1
fi

export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-test}
export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-test}
export AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN:-test}
export AWS_REGION=$REGION
export AWS_ENDPOINT_URL=${AWS_ENDPOINT_URL:-http://localhost:4566}
export SAM_CLI_TELEMETRY=0
export SAM_CLI_PERSIST_AWS_CREDENTIALS=1
export AWS_S3_USE_ARN_REGION=true

if ! curl -s "${AWS_ENDPOINT_URL}/health" >/dev/null 2>&1; then
  echo "ERROR: LocalStack is not reachable at ${AWS_ENDPOINT_URL}. Start it with scripts/start-localstack.sh" >&2
  exit 1
fi

cd "$ROOT_DIR"

echo "Building SAM application..."
sam build --use-container

echo "Deploying stack '${STACK_NAME}' to LocalStack..."
sam deploy \
  --stack-name "$STACK_NAME" \
  --template-file "$SAM_TEMPLATE" \
  --resolve-s3 \
  --s3-prefix "$STACK_NAME" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  "$@"

echo "Stack deployment request submitted. Retrieve outputs with:\n  AWS_ENDPOINT_URL=${AWS_ENDPOINT_URL} aws cloudformation describe-stacks --stack-name ${STACK_NAME}"
