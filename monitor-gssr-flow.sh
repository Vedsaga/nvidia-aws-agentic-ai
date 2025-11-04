#!/bin/bash

# Monitor GSSR Flow in Real-Time
# Shows CloudWatch logs from all extraction Lambdas

echo "=========================================="
echo "GSSR Flow Monitor"
echo "=========================================="
echo ""
echo "This will tail logs from:"
echo "  - ExtractEntities (D1)"
echo "  - ExtractKriya (D2a)"
echo "  - BuildEvents (D2b)"
echo "  - ScoreExtractions (Scorer)"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Function to get log group name
get_log_group() {
    local lambda_name=$1
    echo "/aws/lambda/${lambda_name}"
}

# Function to tail logs with label
tail_logs() {
    local lambda_name=$1
    local label=$2
    local log_group=$(get_log_group "$lambda_name")
    
    echo "Starting monitor for $label..."
    
    aws logs tail "$log_group" --follow --format short --filter-pattern "Phase" 2>/dev/null | while read line; do
        echo "[$label] $line"
    done &
}

# Start tailing all relevant logs
tail_logs "ServerlessStack-ExtractEntities" "D1-ENTITIES"
tail_logs "ServerlessStack-ExtractKriya" "D2a-KRIYA"
tail_logs "ServerlessStack-BuildEvents" "D2b-EVENTS"
tail_logs "ServerlessStack-ScoreExtractions" "SCORER"

# Wait for all background processes
wait
