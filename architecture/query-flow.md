# Query Flow

## Overview

Asynchronous query processing flow using RAG (Retrieval-Augmented Generation) for answering user questions based on processed knowledge graphs.

## Status

🔄 **TODO** - This flow is not yet designed.

## Planned Features

- Async query submission and polling
- Vector similarity search
- Graph-based retrieval
- LLM-powered answer synthesis
- Reference tracking and citations
- Query result caching

## Database Schema

```sql
-- TODO: Define query processing tables
CREATE TABLE queries (
    query_id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    status TEXT NOT NULL,              -- processing, completed, failed
    answer TEXT,
    references TEXT,                   -- JSON array of source references
    processing_method TEXT,            -- vector, graph, hybrid
    confidence_score REAL,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    completed_at INTEGER,
    error_message TEXT
);

CREATE TABLE query_retrievals (
    retrieval_id TEXT PRIMARY KEY,
    query_id TEXT NOT NULL,
    sentence_hash TEXT NOT NULL,
    relevance_score REAL NOT NULL,
    retrieval_method TEXT NOT NULL,    -- vector, graph, keyword
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (query_id) REFERENCES queries(query_id)
);
```

## Implementation Plan

### 1. Query Submission
```python
POST /queries
{
    "question": "What are the main events in the document?"
}

Response:
{
    "query_id": "uuid",
    "status": "processing", 
    "estimated_completion": "2024-01-01T12:00:00Z"
}
```

### 2. Retrieval Pipeline
- **Vector Search**: Embedding-based similarity
- **Graph Search**: Entity and relation matching
- **Hybrid Approach**: Combine multiple methods
- **Ranking**: Score and rank retrieved sentences

### 3. Answer Generation
- **Context Assembly**: Combine retrieved sentences
- **LLM Synthesis**: Generate coherent answer
- **Citation Tracking**: Link answer to sources
- **Quality Validation**: Verify answer quality

### 4. Status Polling
```python
GET /queries/{query_id}/status

Response:
{
    "query_id": "uuid",
    "status": "completed",
    "answer": "The main events include...",
    "references": [
        {
            "sentence_hash": "abc123",
            "text": "Original sentence text",
            "relevance_score": 0.95
        }
    ],
    "confidence_score": 0.87
}
```

## API Design

```
POST /queries                          - Submit new query
GET /queries/{query_id}/status         - Poll query status
GET /queries/{query_id}/references     - Get detailed references
POST /queries/{query_id}/feedback      - Provide feedback on answer
```

## Processing States

```
QUERY_SUBMITTED → QUERY_PROCESSING → QUERY_COMPLETED
               ↘ QUERY_FAILED
```

## Error Scenarios

- No relevant content found
- LLM generation failures
- Embedding service unavailable
- Graph query timeouts
- Answer quality too low

## Performance Considerations

- Query result caching
- Parallel retrieval methods
- Streaming answer generation
- Background processing queues
- Rate limiting per user

## Next Steps

1. Design retrieval algorithms (vector + graph)
2. Implement answer synthesis pipeline
3. Create reference tracking system
4. Add query caching mechanisms
5. Build feedback collection system
6. Implement performance monitoring