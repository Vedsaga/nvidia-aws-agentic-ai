"""Lambda handler for document ingestion."""

import json
import base64
import os
import uuid
from datetime import datetime
import boto3
from src.config import Config
from src.graph.neo4j_client import Neo4jClient
from src.utils.nim_client import NIMClient
from src.ingestion.graph_builder import GraphBuilder


s3_client = boto3.client('s3')
config = Config()
neo4j_client = Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password)
nim_client = NIMClient(config.aws_region, config.nemotron_endpoint, config.embedding_endpoint)
graph_builder = GraphBuilder(neo4j_client, nim_client, config.s3_bucket)


def lambda_handler(event, context):
    """
    Handle document ingestion requests.
    
    Event format:
    {
        "document_name": "filename.txt",
        "content": "base64_encoded_content" or "plain_text"
    }
    """
    try:
        # Parse request
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event
        
        document_name = body.get('document_name', 'unknown.txt')
        content = body.get('content', '')
        
        # Decode if base64
        try:
            content = base64.b64decode(content).decode('utf-8')
        except:
            pass  # Already plain text
        
        # Generate IDs
        job_id = str(uuid.uuid4())
        document_id = f"{document_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Split into lines
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # Initialize job status
        job_status = {
            "job_id": job_id,
            "document_id": document_id,
            "document_name": document_name,
            "status": "processing",
            "total_lines": len(lines),
            "processed_lines": 0,
            "progress_percentage": 0,
            "stats": {
                "success": 0,
                "skipped": 0,
                "errors": 0,
                "actions_created": 0
            },
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        _update_job_status(job_id, job_status)
        
        # Process document
        result = graph_builder.process_document(lines, document_id)
        
        # Update final status
        job_status.update({
            "status": "completed",
            "processed_lines": len(lines),
            "progress_percentage": 100,
            "stats": result["stats"],
            "completed_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
        
        _update_job_status(job_id, job_status)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "job_id": job_id,
                "document_id": document_id,
                "status": "completed",
                "stats": result["stats"]
            })
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Update job status if job_id exists
        if 'job_id' in locals():
            job_status["status"] = "failed"
            job_status["error"] = error_msg
            job_status["updated_at"] = datetime.now().isoformat()
            _update_job_status(job_id, job_status)
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": error_msg
            })
        }


def _update_job_status(job_id: str, status: dict):
    """Update job status in S3."""
    key = f"jobs/{job_id}/status.json"
    s3_client.put_object(
        Bucket=config.s3_bucket,
        Key=key,
        Body=json.dumps(status, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
