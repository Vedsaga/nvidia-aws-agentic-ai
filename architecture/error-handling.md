# Error Handling & Tracing System

## Overview

Application-wide error tracking and distributed tracing system that provides complete visibility across all microservices and user flows.

## Database Schema

### Error Tracking Tables

```sql
-- Application-wide error tracking
CREATE TABLE error_logs (
    error_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,            -- Links to request_traces
    operation TEXT NOT NULL,           -- upload_request, validate_doc, extract_entities, etc.
    error_code TEXT,                   -- Structured codes: INVALID_HASH, S3_ERROR, LLM_TIMEOUT
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    context_data TEXT,                 -- JSON blob with operation-specific data
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (trace_id) REFERENCES request_traces(trace_id)
);

-- Application-wide request tracing
CREATE TABLE request_traces (
    trace_id TEXT PRIMARY KEY,         -- UUID for entire request flow
    parent_trace_id TEXT,              -- For nested operations (sentence processing)
    operation TEXT NOT NULL,           -- Operation name across all microservices
    doc_id TEXT,                       -- Associated document (if applicable)
    sentence_hash TEXT,                -- Associated sentence (if applicable)  
    status TEXT NOT NULL,              -- SUCCESS/FAILED/IN_PROGRESS
    start_time INTEGER DEFAULT (strftime('%s', 'now')),
    end_time INTEGER,
    duration_ms INTEGER,
    metadata TEXT,                     -- JSON blob with operation details
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
);
```

## Error Code Standardization

```python
class ErrorCodes:
    # Input validation
    INVALID_HASH = "INVALID_HASH"
    INVALID_FILE_SIZE = "INVALID_FILE_SIZE"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Infrastructure
    S3_ERROR = "S3_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    
    # Business logic
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    SENTENCE_PROCESSING_FAILED = "SENTENCE_PROCESSING_FAILED"
    GSSR_MAX_ATTEMPTS = "GSSR_MAX_ATTEMPTS"
    
    # System
    SYSTEM_ERROR = "SYSTEM_ERROR"
    TIMEOUT = "TIMEOUT"
```

## Helper Functions (Used by All Flows)

```python
def start_trace(operation, doc_id=None, sentence_hash=None, parent_trace_id=None):
    """Start a new trace for an operation"""
    trace_id = generate_uuid()
    db.insert("request_traces", {
        "trace_id": trace_id,
        "parent_trace_id": parent_trace_id,
        "operation": operation,
        "doc_id": doc_id,
        "sentence_hash": sentence_hash,
        "status": "IN_PROGRESS",
        "start_time": int(time.time())
    })
    return trace_id

def complete_trace(trace_id, status, metadata=None):
    """Complete a trace with success or failure status"""
    end_time = int(time.time())
    start_time = db.query("SELECT start_time FROM request_traces WHERE trace_id=?", trace_id)[0].start_time
    duration_ms = (end_time - start_time) * 1000
    
    db.update("request_traces", {
        "status": status,
        "end_time": end_time,
        "duration_ms": duration_ms,
        "metadata": json.dumps(metadata) if metadata else None
    }, {"trace_id": trace_id})

def log_error_with_trace(trace_id, error_code, message, operation, stack_trace=None):
    """Log an error with trace correlation"""
    db.insert("error_logs", {
        "error_id": generate_uuid(),
        "trace_id": trace_id,
        "operation": operation,
        "error_code": error_code,
        "error_message": message,
        "stack_trace": stack_trace,
        "context_data": json.dumps({"trace_id": trace_id})
    })
```

## Usage Examples Across Flows

```python
# Upload flow
trace_id = start_trace("upload_request", doc_id=doc_id)

# Document processing  
trace_id = start_trace("validate_document", doc_id=doc_id, parent_trace_id=upload_trace_id)
trace_id = start_trace("split_sentences", doc_id=doc_id, parent_trace_id=upload_trace_id)

# Sentence processing (parallel)
for sentence in sentences:
    sentence_trace_id = start_trace("extract_entities", 
                                   doc_id=doc_id, 
                                   sentence_hash=sentence.hash,
                                   parent_trace_id=split_trace_id)
```

## Industry Standard Practices

### 1. Distributed Tracing
- Each request gets unique `trace_id` (UUID)
- All operations within request use same `trace_id`
- Nested operations get `parent_trace_id` for hierarchy
- Standard: OpenTelemetry, Jaeger, Zipkin

### 2. Structured Logging
```python
# Every log entry includes trace context
logger.info("Document validation started", extra={
    "trace_id": trace_id,
    "doc_id": doc_id,
    "operation": "validate_document"
})
```

### 3. Request Correlation
- Client includes `X-Request-ID` header
- Server generates `trace_id` if not provided
- All downstream calls propagate trace context

## Debugging & Monitoring Queries

### Find All Operations for a Document
```sql
SELECT rt.operation, rt.status, rt.duration_ms, el.error_code
FROM request_traces rt
LEFT JOIN error_logs el ON rt.trace_id = el.trace_id  
WHERE rt.doc_id = ?
ORDER BY rt.start_time;
```

### Find Failed Sentence Processing
```sql
SELECT rt.sentence_hash, rt.operation, el.error_message
FROM request_traces rt
JOIN error_logs el ON rt.trace_id = el.trace_id
WHERE rt.operation LIKE '%extract_%' AND rt.status = 'FAILED';
```

### Performance Analysis
```sql
SELECT operation, 
       AVG(duration_ms) as avg_duration,
       COUNT(*) as total_calls,
       SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failures
FROM request_traces 
GROUP BY operation;
```

### End-to-End Request Flow
```sql
SELECT operation, status, duration_ms, start_time
FROM request_traces 
WHERE trace_id = ? 
ORDER BY start_time;
```

### Track Operation Patterns
```sql
-- Track URL regeneration patterns  
SELECT doc_hash_256, COUNT(*) as regeneration_count
FROM request_traces rt
JOIN documents d ON rt.doc_id = d.doc_id
WHERE rt.operation = 'upload_request' AND rt.metadata LIKE '%url_regenerated%'
GROUP BY doc_hash_256;
```

## Benefits

- **Complete Visibility** - Track requests end-to-end across all microservices
- **Error Correlation** - Link failures to specific operations and contexts
- **Performance Monitoring** - Measure duration and identify bottlenecks
- **Audit Trail** - Full history for debugging and compliance
- **Structured Debugging** - Standardized error codes and messages