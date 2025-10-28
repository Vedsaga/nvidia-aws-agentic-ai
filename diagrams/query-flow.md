# Query Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API Gateway
    participant Lambda
    participant Query Decomposer
    participant Nemotron NIM
    participant Cypher Generator
    participant Neo4j
    participant Answer Synthesizer

    User->>Frontend: Enter question
    Frontend->>API Gateway: POST /query
    API Gateway->>Lambda: Invoke query handler
    
    Lambda->>Query Decomposer: Decompose question
    Query Decomposer->>Nemotron NIM: Analyze query
    Note over Nemotron NIM: Identify target Kāraka<br/>Extract constraints<br/>Find verb
    Nemotron NIM-->>Query Decomposer: {target_karaka, constraints, verb}
    Query Decomposer-->>Lambda: Decomposition

    Lambda->>Cypher Generator: Generate query
    Note over Cypher Generator: Build MATCH pattern<br/>Add WHERE clauses<br/>Filter by confidence
    Cypher Generator-->>Lambda: Cypher query

    Lambda->>Neo4j: Execute Cypher
    Note over Neo4j: Traverse graph<br/>Match Kāraka patterns<br/>Filter by document
    Neo4j-->>Lambda: Graph results

    Lambda->>Answer Synthesizer: Synthesize answer
    Answer Synthesizer->>Nemotron NIM: Generate NL answer
    Note over Nemotron NIM: Create natural language<br/>Include Kāraka roles<br/>Add citations
    Nemotron NIM-->>Answer Synthesizer: Answer text
    Answer Synthesizer-->>Lambda: {answer, sources, confidence}

    Lambda-->>Frontend: Response
    Frontend-->>User: Display answer with sources
```


## No Answer Handling

### When No Matching Relationship Exists

```mermaid
flowchart TD
    Q[User Query:<br/>Did Rama use Pinaka to kill Ravana?]
    Q --> D[Query Decomposer]
    D --> C[Cypher Generator]
    C --> CYP[MATCH action-KARANA-Pinaka<br/>WHERE verb=kill, KARTA=Rama]
    CYP --> N[Neo4j Execute]
    N --> CHK{Results<br/>empty?}
    
    CHK -->|Yes| NULL[Return NULL]
    NULL --> MSG[Message: No matching relationship found]
    MSG --> REL[Find Related Info:<br/>- Rama used Kodanda not Pinaka<br/>- Rama gave Pinaka to Lakshmana]
    REL --> RESP[Response with suggestions]
    
    CHK -->|No| ANS[Synthesize Answer]
    ANS --> RESP2[Response with sources]
    
    style Q fill:#e8f5e9
    style NULL fill:#ffebee
    style MSG fill:#ffebee
    style ANS fill:#c8e6c9
    style RESP fill:#fff9c4
    style RESP2 fill:#c8e6c9
```

### Response Format

**With Answer:**
```json
{
  "answer": "Rama used Kodanda to kill Ravana",
  "sources": [{
    "sentence_id": 7,
    "line_number": 8,
    "text": "Rama used the Kodanda to kill Ravana",
    "confidence": 0.95
  }],
  "confidence": 0.95
}
```

**No Answer:**
```json
{
  "answer": null,
  "message": "No matching relationship found",
  "related_findings": [{
    "text": "Rama used Kodanda (not Pinaka)",
    "sentence_id": 7,
    "line_number": 8
  }],
  "confidence": 0.0
}
```

**Key: Never hallucinate. Return NULL when no answer exists.**
