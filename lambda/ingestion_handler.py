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
from src.ingestion.srl_parser import SRLParser
from src.ingestion.karaka_mapper import KarakaMapper
from src.ingestion.entity_resolver import EntityResolver
from src.ingestion.graph_builder import GraphBuilder


s3_client = boto3.client('s3')
config = Config()
neo4j_client = Neo4jClient(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
nim_client = NIMClient(config.AWS_REGION, config.SAGEMAKER_NEMOTRON_ENDPOINT, config.SAGEMAKER_EMBEDDING_ENDPOINT)

# Initialize pipeline components
srl_parser = SRLParser(nim_client=nim_client)
karaka_mapper = KarakaMapper()
entity_resolver = EntityResolver(nim_client, neo4j_client, config.ENTITY_SIMILARITY_THRESHOLD)
graph_builder = GraphBuilder(
    srl_parser=srl_parser,
    karaka_mapper=karaka_mapper,
    entity_resolver=entity_resolver,
    neo4j_client=neo4j_client,
    s3_client=s3_client,
    s3_bucket=config.S3_BUCKET
)


def lambda_handler(event, context):
    """
    Handle document ingestion requests.
    
    Event format:
    {
        "document_name": "filename.txt",
        "content": "base64_encoded_content" or "plain_text"
    }
    """
    job_id = None
    
    try:
        # Parse request
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event
        
        document_name = body.get('document_name', 'unknown.txt').strip()
        content = body.get('content', '')
        
        # Input validation
        if not content:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*')
                },
                "body": json.dumps({
                    "error": "Document content is required"
                })
            }
        
        # Validate document name (prevent path traversal)
        if '..' in document_name or '/' in document_name:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*')
                },
                "body": json.dumps({
                    "error": "Invalid document name"
                })
            }
        
        # Decode if base64
        try:
            content = base64.b64decode(content).decode('utf-8')
        except:
            pass  # Already plain text
        
        # Validate content size (10MB limit for Lambda)
        if len(content) > 10 * 1024 * 1024:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*')
                },
                "body": json.dumps({
                    "error": "Document too large (max 10MB)"
                })
            }
        
        # Generate IDs
        job_id = str(uuid.uuid4())
        document_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Split into lines (not sentences)
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # Initialize job status with document_content
        job_status = {
            "job_id": job_id,
            "document_id": document_id,
            "document_name": document_name,
            "document_content": content,  # Store for later line text retrieval
            "status": "processing",
            "total_lines": len(lines),
            "processed": 0,
            "percentage": 0.0,
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_at": None,
            "results": [],
            "statistics": {
                "success": 0,
                "skipped": 0,
                "errors": 0
            }
        }
        
        _update_job_status(job_id, job_status)
        
        # Process lines with progress updates every 10 lines
        entity_resolver.clear_cache()  # Clear cache for new document
        
        for line_number, line_text in enumerate(lines, start=1):
            try:
                # Process single line
                line_result = graph_builder.process_line(
                    line_text=line_text,
                    line_number=line_number,
                    document_id=document_id
                )
                
                # Add to results
                job_status["results"].append(line_result)
                
                # Update statistics
                status = line_result['status']
                if status == 'success':
                    job_status["statistics"]["success"] += 1
                elif status == 'skipped':
                    job_status["statistics"]["skipped"] += 1
                elif status == 'error':
                    job_status["statistics"]["errors"] += 1
                
                job_status["processed"] = line_number
                job_status["percentage"] = round((line_number / len(lines)) * 100, 2)
                job_status["updated_at"] = datetime.now().isoformat()
                
                # Update S3 progress every 10 lines
                if line_number % 10 == 0 or line_number == len(lines):
                    _update_job_status(job_id, job_status)
                
            except Exception as e:
                # Log error but continue processing
                error_result = {
                    'status': 'error',
                    'line_number': line_number,
                    'line_text': line_text,
                    'actions': [],
                    'error': str(e)
                }
                job_status["results"].append(error_result)
                job_status["statistics"]["errors"] += 1
        
        # Store document in S3 for later line text retrieval
        _store_document_in_s3(document_id, document_name, lines, job_status["results"])
        
        # Mark job as completed
        job_status.update({
            "status": "completed",
            "processed": len(lines),
            "percentage": 100.0,
            "completed_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
        
        _update_job_status(job_id, job_status)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*'),
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "X-Content-Type-Options": "nosniff"
            },
            "body": json.dumps({
                "job_id": job_id,
                "document_id": document_id,
                "status": "completed",
                "total_lines": len(lines),
                "statistics": job_status["statistics"]
            })
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Update job status if job_id exists
        if job_id:
            try:
                job_status["status"] = "failed"
                job_status["error"] = error_msg
                job_status["updated_at"] = datetime.now().isoformat()
                _update_job_status(job_id, job_status)
            except:
                pass  # Ignore errors updating status
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*')
            },
            "body": json.dumps({
                "error": "Failed to process document",
                "message": "An error occurred during document ingestion"
            })
        }


def _update_job_status(job_id: str, status: dict):
    """Update job status in S3."""
    key = f"jobs/{job_id}/status.json"
    s3_client.put_object(
        Bucket=config.S3_BUCKET,
        Key=key,
        Body=json.dumps(status, indent=2).encode('utf-8'),
        ContentType='application/json'
    )


def _store_document_in_s3(document_id: str, document_name: str, lines: list, results: list):
    """Store document content in S3 for later line text retrieval."""
    document_data = {
        'document_id': document_id,
        'document_name': document_name,
        'total_lines': len(lines),
        'lines': lines,
        'results': results
    }
    
    key = f"documents/{document_id}.json"
    s3_client.put_object(
        Bucket=config.S3_BUCKET,
        Key=key,
        Body=json.dumps(document_data, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
