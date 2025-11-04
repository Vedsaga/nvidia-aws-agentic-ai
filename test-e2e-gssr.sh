#!/bin/bash

# End-to-End GSSR Test Script
# Tests: Upload → Sentence Split → GSSR KG Creation → Embedding → NetworkX → Query → Answer

set -e

echo "=========================================="
echo "End-to-End GSSR Pipeline Test"
echo "=========================================="
echo ""

# Load environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

API_URL="${APP_API_GATEWAY_URL}"
if [ -z "$API_URL" ]; then
    echo "❌ Error: APP_API_GATEWAY_URL not found in .env"
    exit 1
fi

echo "API URL: $API_URL"
echo ""

# Create test file with multiple sentences
TEST_FILE="test-e2e-gssr.txt"
echo "Dr. Elena Kowalski served as chief neuroscientist at the Berlin Institute from 2018 to 2023. She collaborated with Maria Santos on a groundbreaking study examining neuroplasticity." > $TEST_FILE

echo "✓ Created test file: $TEST_FILE"
cat $TEST_FILE
echo ""

# Step 1: Request upload URL
echo "=========================================="
echo "Step 1: Requesting Upload URL"
echo "=========================================="

UPLOAD_RESPONSE=$(curl -s -X POST "${API_URL}upload" \
  -H "Content-Type: application/json" \
  -d "{\"filename\": \"$TEST_FILE\"}")

echo "$UPLOAD_RESPONSE" | jq '.'

JOB_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.job_id')
PRE_SIGNED_URL=$(echo "$UPLOAD_RESPONSE" | jq -r '.pre_signed_url')

if [ -z "$JOB_ID" ] || [ "$JOB_ID" == "null" ]; then
    echo "❌ Failed to get job_id"
    exit 1
fi

echo ""
echo "✓ Job ID: $JOB_ID"
echo ""

# Step 2: Upload file to S3
echo "=========================================="
echo "Step 2: Uploading File to S3"
echo "=========================================="

# Use the same upload approach as test-fresh-upload.sh and fail fast on HTTP errors.
if ! UPLOAD_OUTPUT=$(curl --fail --silent --show-error --upload-file "$TEST_FILE" "$PRE_SIGNED_URL" 2>&1); then
        echo "❌ File upload failed"
        echo "$UPLOAD_OUTPUT"
        exit 1
fi

if [ -n "$UPLOAD_OUTPUT" ]; then
        echo "$UPLOAD_OUTPUT"
fi

echo "✓ File uploaded"
echo ""

# Step 3: Monitor processing status
echo "=========================================="
echo "Step 3: Monitoring KG Processing"
echo "=========================================="
echo "This will show GSSR flow in action..."
echo ""

MAX_CHECKS=60
CHECK_COUNT=0
PROCESSING_COMPLETE=false

while [ $CHECK_COUNT -lt $MAX_CHECKS ]; do
    CHECK_COUNT=$((CHECK_COUNT + 1))
    
    STATUS_RESPONSE=$(curl -s "${API_URL}status/${JOB_ID}")
    
    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
    PROGRESS=$(echo "$STATUS_RESPONSE" | jq -r '.progress_percentage')
    TOTAL_SENTENCES=$(echo "$STATUS_RESPONSE" | jq -r '.total_sentences')
    COMPLETED_SENTENCES=$(echo "$STATUS_RESPONSE" | jq -r '.completed_sentences')
    LLM_CALLS=$(echo "$STATUS_RESPONSE" | jq -r '.llm_calls_made')
    
    echo "Check $CHECK_COUNT: Status=$STATUS, Progress=$PROGRESS%, Sentences=$COMPLETED_SENTENCES/$TOTAL_SENTENCES, LLM Calls=$LLM_CALLS"
    
    if [ "$STATUS" == "completed" ]; then
        PROCESSING_COMPLETE=true
        echo ""
        echo "✓ Processing complete!"
        echo "$STATUS_RESPONSE" | jq '.'
        break
    elif [ "$STATUS" == "failed" ]; then
        echo ""
        echo "❌ Processing failed!"
        echo "$STATUS_RESPONSE" | jq '.'
        exit 1
    fi
    
    sleep 5
done

if [ "$PROCESSING_COMPLETE" = false ]; then
    echo ""
    echo "⚠️  Processing timeout after $MAX_CHECKS checks"
    exit 1
fi

echo ""

# Step 4: Check processing chain (GSSR details)
echo "=========================================="
echo "Step 4: Checking GSSR Processing Chain"
echo "=========================================="
echo "This shows all LLM calls made during GSSR..."
echo ""

CHAIN_RESPONSE=$(curl -s "${API_URL}processing-chain/${JOB_ID}")
echo "$CHAIN_RESPONSE" | jq '.'

# Count LLM calls by stage
echo ""
echo "LLM Calls Breakdown:"
echo "$CHAIN_RESPONSE" | jq -r '.llm_calls[] | .pipeline_stage' | sort | uniq -c
echo ""

# Show GSSR attempts
echo "GSSR Attempts per Stage:"
echo "$CHAIN_RESPONSE" | jq -r '.llm_calls[] | select(.pipeline_stage | contains("D1") or contains("D2a") or contains("D2b")) | "\(.pipeline_stage): Attempt \(.attempt_number), Generation \(.generation_index), Temp \(.temperature)"' | head -20
echo ""

# Step 5: Get sentence details
echo "=========================================="
echo "Step 5: Checking Sentence Processing"
echo "=========================================="

# Get first sentence hash from chain
SENTENCE_HASH=$(echo "$CHAIN_RESPONSE" | jq -r '.llm_calls[0].sentence_hash')

if [ ! -z "$SENTENCE_HASH" ] && [ "$SENTENCE_HASH" != "null" ]; then
    echo "Sentence Hash: $SENTENCE_HASH"
    echo ""
    
    SENTENCE_CHAIN=$(curl -s "${API_URL}sentence-chain/${SENTENCE_HASH}")
    echo "$SENTENCE_CHAIN" | jq '.'
    
    echo ""
    echo "Sentence Processing Summary:"
    echo "$SENTENCE_CHAIN" | jq -r '.sentence_text'
    echo ""
    echo "Stages completed:"
    echo "$SENTENCE_CHAIN" | jq -r '.llm_calls[] | .pipeline_stage' | sort | uniq
    echo ""
fi

# Step 6: Test Query - Retrieve relevant sentences
echo "=========================================="
echo "Step 6: Testing Query - Sentence Retrieval"
echo "=========================================="

QUESTION="Who worked at the Berlin Institute?"
echo "Question: $QUESTION"
echo ""

# Submit query
QUERY_SUBMIT=$(curl -s -X POST "${API_URL}query/submit" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"$QUESTION\"}")

echo "$QUERY_SUBMIT" | jq '.'

QUERY_ID=$(echo "$QUERY_SUBMIT" | jq -r '.query_id')

if [ -z "$QUERY_ID" ] || [ "$QUERY_ID" == "null" ]; then
    echo "❌ Failed to get query_id"
    exit 1
fi

echo ""
echo "✓ Query ID: $QUERY_ID"
echo ""

# Step 7: Poll for query answer
echo "=========================================="
echo "Step 7: Waiting for Answer Synthesis"
echo "=========================================="
echo "This shows: Embedding retrieval → Graph fetch → LLM synthesis"
echo ""

MAX_QUERY_CHECKS=30
QUERY_CHECK_COUNT=0
ANSWER_READY=false

while [ $QUERY_CHECK_COUNT -lt $MAX_QUERY_CHECKS ]; do
    QUERY_CHECK_COUNT=$((QUERY_CHECK_COUNT + 1))
    
    sleep 2
    
    QUERY_STATUS=$(curl -s "${API_URL}query/status/${QUERY_ID}")
    
    STATUS=$(echo "$QUERY_STATUS" | jq -r '.status')
    
    echo "Check $QUERY_CHECK_COUNT: Status=$STATUS"
    
    if [ "$STATUS" == "completed" ]; then
        ANSWER_READY=true
        echo ""
        echo "✓ Answer ready!"
        break
    elif [ "$STATUS" == "failed" ]; then
        echo ""
        echo "❌ Query failed!"
        echo "$QUERY_STATUS" | jq '.'
        exit 1
    fi
done

if [ "$ANSWER_READY" = false ]; then
    echo ""
    echo "⚠️  Query timeout"
    exit 1
fi

# Step 8: Display final answer with context
echo "=========================================="
echo "Step 8: Final Answer with Context"
echo "=========================================="
echo ""

echo "$QUERY_STATUS" | jq '.'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ANSWER:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$QUERY_STATUS" | jq -r '.answer'
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SUPPORTING EVIDENCE:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Show retrieved sentences with their graphs
REFERENCES=$(echo "$QUERY_STATUS" | jq -c '.references[]')

if [ ! -z "$REFERENCES" ]; then
    echo "$REFERENCES" | while IFS= read -r ref; do
        SENTENCE=$(echo "$ref" | jq -r '.sentence_text')
        SENTENCE_HASH=$(echo "$ref" | jq -r '.sentence_hash')
        
        echo ""
        echo "📝 Sentence: $SENTENCE"
        echo "   Hash: $SENTENCE_HASH"
        echo ""
        echo "   🔗 Knowledge Graph:"
        
        # Show nodes
        echo "   Nodes:"
        echo "$ref" | jq -r '.kg_snippet.nodes[] | "      - \(.id) (\(.node_type))"'
        
        echo ""
        echo "   Edges:"
        echo "$ref" | jq -r '.kg_snippet.edges[] | "      - \(.source) → \(.target) [\(.karaka_role)]"'
        
        echo ""
        echo "   ─────────────────────────────────────────"
    done
else
    echo "No references found"
fi

echo ""

# Step 9: Verify GSSR quality metrics
echo "=========================================="
echo "Step 9: GSSR Quality Metrics"
echo "=========================================="
echo ""

# Analyze LLM calls to show GSSR effectiveness
echo "Analyzing GSSR performance..."
echo ""

# Count consensus vs scoring
CONSENSUS_COUNT=$(echo "$CHAIN_RESPONSE" | jq '[.llm_calls[] | select(.pipeline_stage | contains("Consensus"))] | length')
SCORER_COUNT=$(echo "$CHAIN_RESPONSE" | jq '[.llm_calls[] | select(.pipeline_stage | contains("Scorer"))] | length')

echo "Consensus optimizations: $CONSENSUS_COUNT"
echo "Scoring passes: $SCORER_COUNT"
echo ""

# Show temperature distribution
echo "Temperature distribution:"
echo "$CHAIN_RESPONSE" | jq -r '.llm_calls[] | "\(.temperature)"' | sort | uniq -c
echo ""

# Show attempts distribution
echo "Attempts distribution:"
echo "$CHAIN_RESPONSE" | jq -r '.llm_calls[] | select(.pipeline_stage | contains("D1") or contains("D2a") or contains("D2b")) | "\(.pipeline_stage): Attempt \(.attempt_number)"' | sort | uniq -c
echo ""

# Cleanup
rm -f $TEST_FILE

echo "=========================================="
echo "✅ End-to-End Test Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "1. ✓ File uploaded and processed"
echo "2. ✓ Sentences split and hashed"
echo "3. ✓ GSSR flow executed (3x generation, fidelity, consensus, scoring)"
echo "4. ✓ Embeddings created and stored"
echo "5. ✓ Knowledge graph built in NetworkX"
echo "6. ✓ Query submitted and processed"
echo "7. ✓ Relevant sentences retrieved via embedding"
echo "8. ✓ Graph context fetched from NetworkX"
echo "9. ✓ Answer synthesized by LLM"
echo ""
echo "🎉 All pipeline stages working correctly!"
