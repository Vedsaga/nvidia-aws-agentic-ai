#!/bin/bash
set -e # Exit immediately if a command fails

LAMBDA_SRC_DIR="src/lambda_src"

# --- TEMPLATES ---
# Use single quotes to avoid issues with the heredoc delimiter
DEFAULT_TEMPLATE='import json
import os
import boto3

# Boto3 clients
# s3_client = boto3.client("s3")
# dynamodb = boto3.resource("dynamodb")

# Environment variables
# TABLE_NAME = os.environ["TABLE_NAME"]
# BUCKET_NAME = os.environ["BUCKET_NAME"]

def lambda_handler(event, context):
    """
    TODO: IMPLEMENT LOGIC
    """
    print(json.dumps(event, indent=2))

    # Example: Propagate the input to the next SFN step
    # Or return a response for an API Gateway
    return event'

L1_UPLOAD_HANDLER_LOGIC='import json
import os
import uuid
import boto3
import time
from botocore.exceptions import ClientError

# Boto3 clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Environment variables
JOBS_TABLE_NAME = os.environ["JOBS_TABLE"]
RAW_BUCKET_NAME = os.environ["RAW_BUCKET"]
jobs_table = dynamodb.Table(JOBS_TABLE_NAME)


def lambda_handler(event, context):
    """
    Handles the initial API request to upload a file.
    Generates a job_id and a pre-signed URL for the client to upload to S3.
    """
    try:
        # 1. Parse request body
        body = json.loads(event.get("body", "{}"))
        filename = body.get("filename")
        if not filename:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing '\''filename'\'' in request body"}),
            }

        # 2. Generate a unique job_id
        job_id = str(uuid.uuid4())
        # S3 object key will be job_id/filename to keep it organized
        object_key = f"{job_id}/{filename}"

        # 3. Create pre-signed URL
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": RAW_BUCKET_NAME, "Key": object_key},
            ExpiresIn=3600,  # URL expires in 1 hour
        )

        # 4. Create an entry in DocumentJobs table
        timestamp = int(time.time())
        jobs_table.put_item(
            Item={
                "job_id": job_id,
                "filename": filename,
                "status": "PENDING_UPLOAD", # Client has URL, waiting for file
                "s3_raw_key": object_key,
                "received_at": timestamp,
            }
        )

        # 5. Return the URL and job_id to the client
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Pre-signed URL generated successfully.",
                    "job_id": job_id,
                    "pre_signed_url": presigned_url,
                    "s3_key": object_key
                }
            ),
        }

    except ClientError as e:
        print(f"Boto3 error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "AWS service error"})}
    except Exception as e:
        print(f"Handler error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}'

# --- SCRIPT ---

# 1. Safety Check
if [ ! -d "$LAMBDA_SRC_DIR" ]; then
    echo "Directory $LAMBDA_SRC_DIR does not exist. Creating it."
else
    echo "WARNING: This script will permanently delete the entire directory:"
    echo "$LAMBDA_SRC_DIR"
    echo "This will reset all your Lambda function source code."
    read -p "Are you sure you want to continue? (y/n) " -n 1 -r
    echo "" # move to a new line
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operation cancelled."
        exit 1
    fi
    echo "Removing old directory..."
    rm -rf "$LAMBDA_SRC_DIR"
fi

# 2. Helper function to create a lambda
create_lambda() {
    local path=$1
    local content=$2
    local full_path="$LAMBDA_SRC_DIR/$path"

    mkdir -p "$full_path"
    echo "$content" > "$full_path/lambda_function.py"
    echo "Created $full_path/lambda_function.py"
}

# 3. Recreate all 20 functions based on the serverless_stack.py
echo "Rebuilding Lambda source tree..."

# Job Management
create_lambda "job_mgmt/l1_upload_handler"       "$L1_UPLOAD_HANDLER_LOGIC"
create_lambda "job_mgmt/l2_validate_doc"         "$DEFAULT_TEMPLATE"
create_lambda "job_mgmt/l3_sanitize_doc"         "$DEFAULT_TEMPLATE"
create_lambda "job_mgmt/l3_update_doc_status"    "$DEFAULT_TEMPLATE"
create_lambda "job_mgmt/l4_list_all_docs"        "$DEFAULT_TEMPLATE"
create_lambda "job_mgmt/l8_get_sentences_from_s3" "$DEFAULT_TEMPLATE"

# LLM Gateway
create_lambda "llm_gateway/l7_llm_call"      "$DEFAULT_TEMPLATE"
create_lambda "llm_gateway/l8_embedding_call" "$DEFAULT_TEMPLATE"

# KG Agents
create_lambda "kg_agents/l9_extract_entities"    "$DEFAULT_TEMPLATE"
create_lambda "kg_agents/l10_extract_kriya"      "$DEFAULT_TEMPLATE"
create_lambda "kg_agents/l11_build_events"       "$DEFAULT_TEMPLATE"
create_lambda "kg_agents/l12_audit_events"       "$DEFAULT_TEMPLATE"
create_lambda "kg_agents/l13_extract_relations"  "$DEFAULT_TEMPLATE"
create_lambda "kg_agents/l14_extract_attributes" "$DEFAULT_TEMPLATE"

# Graph Ops
create_lambda "graph_ops/l15_graph_node_ops" "$DEFAULT_TEMPLATE"
create_lambda "graph_ops/l16_graph_edge_ops" "$DEFAULT_TEMPLATE"

# RAG
create_lambda "rag/l17_retrieve_from_embedding" "$DEFAULT_TEMPLATE"
create_lambda "rag/l18_synthesize_answer"       "$DEFAULT_TEMPLATE"

# API Tools
create_lambda "api_tools/l19_get_processing_chain" "$DEFAULT_TEMPLATE"
create_lambda "api_tools/l20_get_sentence_chain"   "$DEFAULT_TEMPLATE"

# 4. Final confirmation
echo ""
echo "------------------------------------------"
echo "✅ Lambda source tree rebuilt successfully."
echo "Total functions created: 20"
echo "------------------------------------------"
echo "New tree structure:"
if command -v tree &> /dev/null; then
    tree src/
else
    find src/ -type f -name "*.py" | head -25
fi

echo ""
echo "NEXT STEPS:"
echo "1. Your logic for 'l1_upload_handler' is in place."
echo "2. You must now copy your old logic from backups into the new template files for the other 19 functions."
