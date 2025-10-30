#!/usr/bin/env python3
"""
Lightweight API Server for Kāraka RAG System
FastAPI server that wraps Lambda handlers for local development
"""

import os
import sys
import json
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

# Add src to path
sys.path.append('src')
sys.path.append('lambda')

# Import Lambda handlers
import importlib.util
import sys

def import_lambda_handler(handler_name):
    """Import lambda handler from file"""
    spec = importlib.util.spec_from_file_location(
        handler_name, f"lambda/{handler_name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.lambda_handler

health_handler = import_lambda_handler("health_handler")
ingestion_handler = import_lambda_handler("ingestion_handler")
status_handler = import_lambda_handler("status_handler")
query_handler = import_lambda_handler("query_handler")
graph_handler = import_lambda_handler("graph_handler")

app = FastAPI(
    title="Kāraka RAG System API",
    description="Local development API for the Kāraka semantic knowledge graph system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class QueryRequest(BaseModel):
    query: str
    limit: Optional[int] = 10

class IngestRequest(BaseModel):
    text: str
    filename: Optional[str] = "uploaded_text.txt"

def create_lambda_context():
    """Create a mock Lambda context for local testing"""
    class MockContext:
        def __init__(self):
            self.function_name = "local-development"
            self.function_version = "1.0"
            self.invoked_function_arn = "arn:aws:lambda:local:123456789012:function:local-development"
            self.memory_limit_in_mb = 512
            self.remaining_time_in_millis = lambda: 30000
            self.log_group_name = "/aws/lambda/local-development"
            self.log_stream_name = "local-stream"
            self.aws_request_id = "local-request-id"
    
    return MockContext()

def lambda_response_to_fastapi(lambda_response: Dict[str, Any]):
    """Convert Lambda response format to FastAPI response"""
    status_code = lambda_response.get('statusCode', 200)
    body = lambda_response.get('body', '{}')
    
    # Parse body if it's a string
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            body = {"message": body}
    
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=body)
    
    return JSONResponse(content=body, status_code=status_code)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    event = {"httpMethod": "GET", "path": "/health"}
    context = create_lambda_context()
    
    response = health_handler(event, context)
    return lambda_response_to_fastapi(response)

@app.post("/ingest")
async def ingest_text(request: IngestRequest):
    """Ingest text for processing"""
    event = {
        "httpMethod": "POST",
        "path": "/ingest",
        "body": json.dumps({
            "text": request.text,
            "filename": request.filename
        })
    }
    context = create_lambda_context()
    
    response = ingestion_handler(event, context)
    return lambda_response_to_fastapi(response)

@app.post("/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    """Ingest uploaded file"""
    try:
        content = await file.read()
        text = content.decode('utf-8')
        
        event = {
            "httpMethod": "POST",
            "path": "/ingest",
            "body": json.dumps({
                "text": text,
                "filename": file.filename
            })
        }
        context = create_lambda_context()
        
        response = ingestion_handler(event, context)
        return lambda_response_to_fastapi(response)
    
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/ingest/status/{job_id}")
async def get_ingestion_status(job_id: str):
    """Get ingestion job status"""
    event = {
        "httpMethod": "GET",
        "path": f"/ingest/status/{job_id}",
        "pathParameters": {"job_id": job_id}
    }
    context = create_lambda_context()
    
    response = status_handler(event, context)
    return lambda_response_to_fastapi(response)

@app.post("/query")
async def query_graph(request: QueryRequest):
    """Query the knowledge graph"""
    event = {
        "httpMethod": "POST",
        "path": "/query",
        "body": json.dumps({
            "query": request.query,
            "limit": request.limit
        })
    }
    context = create_lambda_context()
    
    response = query_handler(event, context)
    return lambda_response_to_fastapi(response)

@app.get("/graph")
async def get_graph_data():
    """Get graph visualization data"""
    event = {"httpMethod": "GET", "path": "/graph"}
    context = create_lambda_context()
    
    response = graph_handler(event, context)
    return lambda_response_to_fastapi(response)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Kāraka RAG System API",
        "version": "1.0.0",
        "mode": "lightweight",
        "endpoints": {
            "health": "GET /health",
            "ingest_text": "POST /ingest",
            "ingest_file": "POST /ingest/file",
            "status": "GET /ingest/status/{job_id}",
            "query": "POST /query",
            "graph": "GET /graph",
            "docs": "GET /docs"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Kāraka RAG System API Server")
    print("📚 API Documentation: http://localhost:8090/docs")
    print("🔍 Interactive API: http://localhost:8090/redoc")
    print("💡 Health Check: http://localhost:8090/health")
    print("\n⚠️  First run will download models (~500MB)")
    print("🛑 Press Ctrl+C to stop\n")
    
    uvicorn.run(
        "lightweight_api:app",
        host="0.0.0.0",
        port=8090,
        reload=True,
        log_level="info"
    )