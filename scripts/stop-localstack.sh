#!/bin/bash
set -euo pipefail

CONTAINER_NAME=${LOCALSTACK_CONTAINER_NAME:-localstack-gssr}

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is required" >&2
  exit 1
fi

if ! docker ps -aq --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "LocalStack container '${CONTAINER_NAME}' is not present"
  exit 0
fi

echo "Stopping LocalStack container '${CONTAINER_NAME}'..."
docker stop "${CONTAINER_NAME}" >/dev/null || true

echo "Removing LocalStack container '${CONTAINER_NAME}'..."
docker rm "${CONTAINER_NAME}" >/dev/null || true

echo "LocalStack stopped"
