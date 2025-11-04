#!/bin/bash

# Inspect GSSR Results in DynamoDB
# Shows sentences table with GSSR metrics

echo "=========================================="
echo "GSSR Results Inspector"
echo "=========================================="
echo ""

if [ -z "$1" ]; then
    echo "Usage: $0 <job_id>"
    echo ""
    echo "This will show:"
    echo "  - Sentences processed"
    echo "  - GSSR attempts per stage (d1_attempts, d2a_attempts, d2b_attempts)"
    echo "  - Best scores achieved"
    echo "  - Sentences needing review"
    echo ""
    exit 1
fi

JOB_ID=$1

echo "Job ID: $JOB_ID"
echo ""

# Query Sentences table by job_id
echo "=========================================="
echo "Sentences Processed"
echo "=========================================="
echo ""

SENTENCES=$(aws dynamodb query \
    --table-name Sentences \
    --index-name ByJobId \
    --key-condition-expression "job_id = :jid" \
    --expression-attribute-values "{\":jid\":{\"S\":\"$JOB_ID\"}}" \
    --output json)

SENTENCE_COUNT=$(echo "$SENTENCES" | jq '.Items | length')

echo "Total sentences: $SENTENCE_COUNT"
echo ""

if [ "$SENTENCE_COUNT" -eq 0 ]; then
    echo "No sentences found for this job_id"
    exit 0
fi

# Display each sentence with GSSR metrics
echo "$SENTENCES" | jq -r '.Items[] | 
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" +
    "Sentence: \(.original_sentence.S // .text.S)\n" +
    "Hash: \(.sentence_hash.S)\n" +
    "Status: \(.status.S)\n" +
    "Best Score: \(.best_score.N // "N/A")\n" +
    "Needs Review: \(.needs_review.BOOL // false)\n" +
    "D1 Attempts: \(.d1_attempts.N // "0")\n" +
    "D2a Attempts: \(.d2a_attempts.N // "0")\n" +
    "D2b Attempts: \(.d2b_attempts.N // "0")\n" +
    (if .failure_reason then "Failure Reason: \(.failure_reason.S)\n" else "" end) +
    ""'

echo ""

# Summary statistics
echo "=========================================="
echo "GSSR Statistics"
echo "=========================================="
echo ""

# Average attempts per stage
AVG_D1=$(echo "$SENTENCES" | jq '[.Items[].d1_attempts.N | tonumber] | add / length')
AVG_D2A=$(echo "$SENTENCES" | jq '[.Items[].d2a_attempts.N | tonumber] | add / length')
AVG_D2B=$(echo "$SENTENCES" | jq '[.Items[].d2b_attempts.N | tonumber] | add / length')

echo "Average attempts:"
echo "  D1 (Entities): $AVG_D1"
echo "  D2a (Kriya): $AVG_D2A"
echo "  D2b (Events): $AVG_D2B"
echo ""

# Average best score
AVG_SCORE=$(echo "$SENTENCES" | jq '[.Items[].best_score.N | tonumber] | add / length')
echo "Average best score: $AVG_SCORE"
echo ""

# Count needing review
NEEDS_REVIEW=$(echo "$SENTENCES" | jq '[.Items[] | select(.needs_review.BOOL == true)] | length')
echo "Sentences needing review: $NEEDS_REVIEW / $SENTENCE_COUNT"
echo ""

# Count by status
echo "Status breakdown:"
echo "$SENTENCES" | jq -r '.Items[].status.S' | sort | uniq -c
echo ""

# Show LLM call statistics
echo "=========================================="
echo "LLM Call Statistics"
echo "=========================================="
echo ""

# Get first sentence hash to show detailed LLM calls
FIRST_HASH=$(echo "$SENTENCES" | jq -r '.Items[0].sentence_hash.S')

if [ ! -z "$FIRST_HASH" ]; then
    echo "Detailed LLM calls for first sentence ($FIRST_HASH):"
    echo ""
    
    LLM_CALLS=$(aws dynamodb query \
        --table-name LLMCallLog \
        --index-name BySentenceHash \
        --key-condition-expression "sentence_hash = :hash" \
        --expression-attribute-values "{\":hash\":{\"S\":\"$FIRST_HASH\"}}" \
        --output json)
    
    CALL_COUNT=$(echo "$LLM_CALLS" | jq '.Items | length')
    echo "Total LLM calls: $CALL_COUNT"
    echo ""
    
    echo "Calls by stage:"
    echo "$LLM_CALLS" | jq -r '.Items[].pipeline_stage.S' | sort | uniq -c
    echo ""
    
    echo "Calls by temperature:"
    echo "$LLM_CALLS" | jq -r '.Items[].temperature.N' | sort | uniq -c
    echo ""
    
    echo "Recent calls:"
    echo "$LLM_CALLS" | jq -r '.Items[] | 
        "\(.pipeline_stage.S) - Attempt \(.attempt_number.N), Gen \(.generation_index.N), Temp \(.temperature.N), Status: \(.status.S)"' | head -20
fi

echo ""
echo "=========================================="
echo "✓ Inspection Complete"
echo "=========================================="
