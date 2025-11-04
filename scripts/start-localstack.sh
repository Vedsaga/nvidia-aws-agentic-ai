#!/bin/bash
set -euo pipefail

CONTAINER_NAME=${LOCALSTACK_CONTAINER_NAME:-localstack-gssr}
IMAGE=${LOCALSTACK_IMAGE:-localstack/localstack:latest}
SERVICES=${LOCALSTACK_SERVICES:-apigateway,cloudformation,cloudwatch,dynamodb,iam,lambda,logs,s3,sns,sqs,stepfunctions,sts}

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is required to run LocalStack" >&2
  exit 1
fi

action=${1:-start}
if [[ "$action" != "start" ]]; then
  echo "Usage: $0 [start]" >&2
  exit 1
fi

if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "LocalStack already running in container '${CONTAINER_NAME}'"
  exit 0
fi

if docker ps -aq --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "Removing stale LocalStack container '${CONTAINER_NAME}'"
  docker rm -f "${CONTAINER_NAME}" >/dev/null
fi

echo "Starting LocalStack container '${CONTAINER_NAME}'..."
docker run -d \
  --name "${CONTAINER_NAME}" \
  -p 4566:4566 \
  -p 4510-4559:4510-4559 \
  -e SERVICES="${SERVICES}" \
  -e LOCALSTACK_AUTH_TOKEN="${LOCALSTACK_AUTH_TOKEN:-}" \
  -e DEBUG=${LOCALSTACK_DEBUG:-0} \
  "${IMAGE}" >/dev/null

echo "Waiting for LocalStack edge service to respond..."
for _ in {1..30}; do
  if curl -s "http://localhost:4566/health" >/dev/null 2>&1; then
    echo "LocalStack is ready on http://localhost:4566"
    exit 0
  fi
  sleep 1
done

echo "ERROR: LocalStack did not become ready within 30 seconds" >&2
exit 1
