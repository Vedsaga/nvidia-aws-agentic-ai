# Global Status Enum

## Overview

Centralized status definitions used across all microservices and user flows.

## Status Definitions

```python
class JobStatus(Enum):
    # Upload Flow
    UPLOAD_PENDING = "upload_pending"
    UPLOAD_COMPLETE = "upload_complete" 
    UPLOAD_FAILED = "upload_failed"
    
    # Document Processing
    DOC_VALIDATION_PENDING = "doc_validation_pending"
    DOC_VALIDATION_COMPLETE = "doc_validation_complete"
    DOC_VALIDATION_FAILED = "doc_validation_failed"
    
    DOC_SANITIZE_PENDING = "doc_sanitize_pending"
    DOC_SANITIZE_COMPLETE = "doc_sanitize_complete"
    DOC_SANITIZE_FAILED = "doc_sanitize_failed"
    
    SENTENCE_SPLIT_PENDING = "sentence_split_pending"
    SENTENCE_SPLIT_COMPLETE = "sentence_split_complete"
    SENTENCE_SPLIT_FAILED = "sentence_split_failed"
    
    # KG Processing (per sentence)
    ENTITIES_PENDING = "entities_pending"
    ENTITIES_COMPLETE = "entities_complete"
    ENTITIES_FAILED = "entities_failed"
    
    KRIYA_PENDING = "kriya_pending"
    KRIYA_COMPLETE = "kriya_complete"
    KRIYA_FAILED = "kriya_failed"
    
    EVENTS_PENDING = "events_pending"
    EVENTS_COMPLETE = "events_complete"
    EVENTS_FAILED = "events_failed"
    
    RELATIONS_PENDING = "relations_pending"
    RELATIONS_COMPLETE = "relations_complete"
    RELATIONS_FAILED = "relations_failed"
    
    GRAPH_PENDING = "graph_pending"
    GRAPH_COMPLETE = "graph_complete"
    GRAPH_FAILED = "graph_failed"
    
    # Overall Job Status
    JOB_COMPLETE = "job_complete"
    JOB_FAILED = "job_failed"
```

## Status Flow Patterns

### Standard Three-State Pattern
Most operations follow this pattern:
- `{OPERATION}_PENDING` - Operation queued/ready to start
- `{OPERATION}_COMPLETE` - Operation finished successfully  
- `{OPERATION}_FAILED` - Operation failed with error details

### Usage Guidelines

1. **Atomic Updates** - Each API call updates exactly one status
2. **No Intermediate States** - Avoid states like "processing" or "in_progress"
3. **Clear Failure Reasons** - Always store failure_reason when status is FAILED
4. **Idempotent Operations** - Same input should produce same status outcome

### Status Transitions

```
PENDING → COMPLETE (success path)
PENDING → FAILED (error path)
FAILED → PENDING (retry - client triggered)
```

Note: COMPLETE states are terminal - no transitions allowed from them.


### LLM Call Arch

```
Business Layer (sentence-split-flow)
    ↓ (decides provider, model, reasoning)
Prompt Layer (prompt-processor) 
    ↓ (builds final prompts)
LLM Layer (llm-call-flow)
    ↓ (pure execution)
LLM API
```
