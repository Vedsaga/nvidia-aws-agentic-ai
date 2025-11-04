#!/bin/bash

# Usage: ./test-lambda-local.sh <function-name> <event-file>

if [ -z "$1" ]; then
    echo "Usage: ./test-lambda-local.sh <function-name> [event-file]"
    echo ""
    echo "Available functions:"
    echo "  UploadHandler, ValidateDoc, SanitizeDoc, ListAllDocs"
    echo "  LLMCall, EmbeddingCall"
    echo "  ExtractEntities, ExtractKriya, BuildEvents, AuditEvents"
    echo "  ExtractRelations, ExtractAttributes, ScoreExtractions"
    echo "  GraphNodeOps, GraphEdgeOps"
    echo "  RetrieveFromEmbedding, SynthesizeAnswer, QueryProcessor"
    echo "  QuerySubmit, QueryStatus"
    echo "  GetProcessingChain, GetSentenceChain"
    echo ""
    echo "Example: ./test-lambda-local.sh LLMCall test-events/llm-call-event.json"
    exit 1
fi

FUNCTION_NAME=$1
EVENT_FILE=${2:-"test-events/${FUNCTION_NAME,,}-event.json"}

# Set environment to point to LocalStack
export AWS_SAM_LOCAL=true
export AWS_ENDPOINT_URL=http://localhost:4566

echo "Testing $FUNCTION_NAME with event: $EVENT_FILE"
echo ""

# Check if event file exists
if [ ! -f "$EVENT_FILE" ]; then
    echo "Event file not found: $EVENT_FILE"
    echo "Creating sample event file..."
    mkdir -p test-events
    echo '{}' > "$EVENT_FILE"
    echo "Created empty event at $EVENT_FILE - please edit it with your test data"
    exit 1
fi

# Invoke Lambda locally with LocalStack endpoints
sam local invoke $FUNCTION_NAME \
    --event "$EVENT_FILE" \
    --docker-network host \
    --env-vars local-env.json

echo ""
echo "Test complete"
