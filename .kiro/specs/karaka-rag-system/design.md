# Design Document

## Overview

The Kāraka Graph RAG System uses Pāṇinian semantic role theory to build a knowledge graph that explicitly models agent-patient relationships and other semantic roles. This design document outlines the technical architecture, component interactions, data models, and implementation approach for deploying the system on AWS infrastructure.

## Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│                    (React Frontend - S3/Local)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Amazon API Gateway                          │
│  POST /ingest  │  GET /ingest/status/:id  │  POST /query  │     │
│                      GET /graph                                  │
└──────┬──────────────────────┬──────────────────┬────────────────┘
       │                      │                  │
       ▼                      ▼                  ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Lambda:         │  │  Lambda:         │  │  Lambda:         │
│  Ingestion       │  │  Status          │  │  Query           │
│  Handler         │  │  Handler         │  │  Handler         │
└────┬─────────────┘  └────┬─────────────┘  └────┬─────────────┘
     │                     │                      │
     │ boto3               │ boto3                │ boto3
     ▼                     ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              Amazon SageMaker Endpoints                          │
│  ┌──────────────────────────┐  ┌──────────────────────────┐    │
│  │ Nemotron NIM             │  │ Embedding NIM            │    │
│  │ (llama-3.1-nemotron)     │  │ (nvidia-retrieval)       │    │
│  │ ml.g5.xlarge             │  │ ml.g5.xlarge             │    │
│  └──────────────────────────┘  └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
     │                                    │
     │ Query decomposition                │ Entity embeddings
     │ Answer synthesis                   │ Entity resolution
     ▼                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Core Processing Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ SRL Parser   │  │ Kāraka       │  │ Entity       │          │
│  │ (spaCy)      │  │ Mapper       │  │ Resolver     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Query        │  │ Cypher       │  │ Answer       │          │
│  │ Decomposer   │  │ Generator    │  │ Synthesizer  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
     │                                    │
     │ Graph operations                   │ Job status
     ▼                                    ▼
┌──────────────────────┐          ┌──────────────────────┐
│   Neo4j Aura         │          │   Amazon S3          │
│   (Graph Database)   │          │   (Job Tracking)     │
│                      │          │                      │
│  - Entity nodes      │          │  - Progress files    │
│  - Action nodes      │          │  - Document uploads  │
│  - Kāraka edges      │          │  - Job metadata      │
└──────────────────────┘          └──────────────────────┘
```

### Component Responsibilities

#### 1. Frontend (React)
- Document upload interface
- Real-time progress tracking
- Query input and result display
- Graph visualization using vis-network
- Hosted on S3 static website or run locally

#### 2. API Gateway
- REST API endpoints for all operations
- CORS configuration for cross-origin requests
- Request validation and routing
- Integration with Lambda functions

#### 3. Lambda Functions
- **Ingestion Handler**: Processes uploaded documents, orchestrates SRL extraction, calls SageMaker endpoints
- **Status Handler**: Retrieves job progress from S3
- **Query Handler**: Decomposes queries, generates Cypher, synthesizes answers
- **Graph Handler**: Retrieves visualization data from Neo4j

#### 4. SageMaker Endpoints
- **Nemotron NIM**: Query decomposition and answer synthesis
- **Embedding NIM**: Entity embedding generation for resolution

#### 5. Core Processing Modules
- **SRL Parser**: Extracts semantic roles using spaCy
- **Kāraka Mapper**: Maps SRL roles to Pāṇinian Kārakas
- **Entity Resolver**: Resolves entity mentions using embeddings
- **Query Decomposer**: Analyzes queries to identify target Kārakas
- **Cypher Generator**: Generates Neo4j queries
- **Answer Synthesizer**: Creates natural language responses

#### 6. Data Storage
- **Neo4j Aura**: Stores knowledge graph
- **Amazon S3**: Stores job status and documents

## Data Models

### Neo4j Graph Schema

```cypher
// Entity Node
(:Entity {
  canonical_name: String,           // "Rama"
  aliases: [String],                // ["the prince", "he", "Rama"]
  document_ids: [String],           // ["doc_123", "doc_456"]
  embedding: [Float],               // 768-dimensional vector
  created_at: Timestamp
})

// Action Node (Kriya) - THE CENTER OF THE GRAPH
(:Action {
  id: String,                       // "action_42"
  verb: String,                     // "give"
  sentence: String,                 // Full source sentence
  sentence_id: Integer,             // Position in document
  document_id: String,              // Source document
  created_at: Timestamp
})

// Kāraka Relationships - ALL POINT FROM ACTION TO ENTITY
// The Kriya (Action) is the binding force that connects entities through Kāraka roles

(Action)-[:KARTA {                  // Agent - Who performs the action?
  confidence: Float,                // 0.0 - 1.0
  source_sentence_id: Integer,
  document_id: String,
  created_at: Timestamp
}]->(Entity)

(Action)-[:KARMA {                  // Patient/Object - What is acted upon?
  confidence: Float,
  source_sentence_id: Integer,
  document_id: String,
  created_at: Timestamp
}]->(Entity)

(Action)-[:KARANA {                 // Instrument - By what means?
  confidence: Float,
  source_sentence_id: Integer,
  document_id: String,
  created_at: Timestamp
}]->(Entity)

(Action)-[:SAMPRADANA {             // Recipient - For whom? To whom?
  confidence: Float,
  source_sentence_id: Integer,
  document_id: String,
  created_at: Timestamp
}]->(Entity)

(Action)-[:ADHIKARANA {             // Location - Where?
  confidence: Float,
  source_sentence_id: Integer,
  document_id: String,
  created_at: Timestamp
}]->(Entity)

(Action)-[:APADANA {                // Source - From where? From whom?
  confidence: Float,
  source_sentence_id: Integer,
  document_id: String,
  created_at: Timestamp
}]->(Entity)

// CRITICAL: Entities are NOT directly connected to each other
// They are only connected through the Kriya (Action) that binds them
// This enables multi-hop reasoning by traversing through actions
```

### S3 Job Status Schema

```json
{
  "job_id": "uuid-string",
  "document_id": "doc_123",
  "document_name": "ramayana.txt",
  "status": "processing|completed|failed",
  "total_sentences": 500,
  "processed": 250,
  "percentage": 50.0,
  "started_at": "2025-10-28T10:00:00Z",
  "updated_at": "2025-10-28T10:05:00Z",
  "completed_at": null,
  "results": [
    {
      "sentence_id": 0,
      "sentence": "Rama gave bow to Lakshmana.",
      "status": "success|skipped|error",
      "karakas": {
        "KARTA": "Rama",
        "KARMA": "bow",
        "SAMPRADANA": "Lakshmana"
      },
      "action_id": "action_0",
      "error": null
    }
  ],
  "statistics": {
    "success": 240,
    "skipped": 8,
    "errors": 2
  }
}
```

### API Request/Response Schemas

#### POST /ingest
**Request:**
```json
{
  "document_name": "ramayana.txt",
  "content": "base64_encoded_content"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "document_id": "doc_123",
  "status": "processing",
  "total_sentences": 500
}
```

#### GET /ingest/status/:job_id
**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "progress": 250,
  "total": 500,
  "percentage": 50.0,
  "statistics": {
    "success": 240,
    "skipped": 8,
    "errors": 2
  }
}
```

#### POST /query
**Request:**
```json
{
  "question": "Who gave bow to Lakshmana?",
  "min_confidence": 0.8,
  "document_filter": "doc_123"  // Optional
}
```

**Response:**
```json
{
  "answer": "Rama (KARTA) gave the bow (KARMA) to Lakshmana (SAMPRADANA).",
  "sources": [
    {
      "sentence_id": 42,
      "text": "Rama handed the mighty bow to his brother Lakshmana.",
      "confidence": 0.95,
      "document_id": "doc_123",
      "document_name": "ramayana.txt"
    }
  ],
  "karakas": {
    "target": "KARTA",
    "constraints": {
      "KARMA": "bow",
      "SAMPRADANA": "Lakshmana"
    }
  },
  "confidence": 0.95
}
```

#### GET /graph
**Response:**
```json
{
  "nodes": [
    {
      "id": "entity_rama",
      "label": "Rama",
      "type": "Entity",
      "document_ids": ["doc_123"],
      "aliases": ["the prince", "he"]
    },
    {
      "id": "action_42",
      "label": "gave",
      "type": "Action",
      "document_id": "doc_123"
    }
  ],
  "edges": [
    {
      "from": "entity_rama",
      "to": "action_42",
      "label": "KARTA",
      "confidence": 0.95,
      "document_id": "doc_123"
    }
  ]
}
```

## Component Design

### 1. SRL Parser (spaCy-based)

**Purpose**: Extract semantic roles from sentences using dependency parsing

**Implementation**:
```python
class SRLParser:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
    
    def parse_sentence(self, sentence: str) -> Tuple[str, Dict[str, str]]:
        """
        Returns: (verb, {role: entity})
        Example: ("give", {"nsubj": "Rama", "obj": "bow", "iobj": "Lakshmana"})
        """
        doc = self.nlp(sentence)
        verb = self._extract_main_verb(doc)
        roles = self._extract_semantic_roles(doc)
        return verb, roles
```

**Key Methods**:
- `_extract_main_verb()`: Finds ROOT verb in dependency tree
- `_extract_semantic_roles()`: Maps dependency labels (nsubj, obj, iobj, obl) to entities
- `_get_noun_phrase()`: Extracts full noun phrases including modifiers

### 2. Kāraka Mapper

**Purpose**: Map spaCy SRL roles to Pāṇinian Kārakas

**Mapping Rules**:
```python
SRL_TO_KARAKA = {
    'nsubj': 'KARTA',        # Subject → Agent
    'obj': 'KARMA',          # Direct object → Patient
    'iobj': 'SAMPRADANA',    # Indirect object → Recipient
    'obl:with': 'KARANA',    # Instrumental
    'obl:loc': 'ADHIKARANA', # Locative
    'obl:from': 'APADANA'    # Source
}
```

**Implementation**:
```python
class KarakaMapper:
    def map_to_karakas(self, srl_roles: Dict[str, str]) -> Dict[str, str]:
        """
        Converts SRL roles to Kāraka roles
        Input: {"nsubj": "Rama", "obj": "bow"}
        Output: {"KARTA": "Rama", "KARMA": "bow"}
        """
```

### 3. Entity Resolver

**Purpose**: Resolve entity mentions to canonical names using embedding similarity

**Algorithm**:
1. Check if entity exists in Neo4j
2. If not found, call SageMaker Embedding NIM to get vector
3. Compare with existing entity embeddings using cosine similarity
4. If similarity > 0.85, resolve to existing entity
5. Otherwise, create new canonical entity

**Implementation**:
```python
class EntityResolver:
    def __init__(self, sagemaker_client, neo4j_client):
        self.sagemaker = sagemaker_client
        self.neo4j = neo4j_client
        self.similarity_threshold = 0.85
    
    def resolve_entity(self, entity_mention: str, document_id: str) -> str:
        """
        Returns canonical entity name
        """
        # Check Neo4j for existing entities
        existing = self.neo4j.find_similar_entities(entity_mention)
        
        if not existing:
            # New entity
            embedding = self._get_embedding(entity_mention)
            return self._create_entity(entity_mention, embedding, document_id)
        
        # Compare embeddings
        mention_embedding = self._get_embedding(entity_mention)
        best_match = self._find_best_match(mention_embedding, existing)
        
        if best_match['similarity'] > self.similarity_threshold:
            return best_match['canonical_name']
        else:
            # Different entity with same name
            return self._create_entity(entity_mention, mention_embedding, document_id)
```

### 4. Query Decomposer

**Purpose**: Analyze natural language queries to identify target Kāraka and constraints

**Implementation**:
```python
class QueryDecomposer:
    def __init__(self, sagemaker_client):
        self.sagemaker = sagemaker_client
    
    def decompose(self, question: str) -> Dict:
        """
        Uses Nemotron NIM to decompose query
        Input: "Who gave bow to Lakshmana?"
        Output: {
            "target_karaka": "KARTA",
            "constraints": {"KARMA": "bow", "SAMPRADANA": "Lakshmana"},
            "verb": "give"
        }
        """
        prompt = self._build_decomposition_prompt(question)
        response = self._call_nemotron(prompt)
        return self._parse_response(response)
```

**Prompt Template**:
```
You are a semantic query analyzer for a Kāraka-based knowledge graph.

Question: "{question}"

Identify:
1. Which Kāraka role is being asked about (KARTA, KARMA, KARANA, SAMPRADANA, ADHIKARANA, APADANA)
2. What constraints are given (other Kāraka roles mentioned)
3. The action/verb involved

Respond with JSON:
{
  "target_karaka": "KARTA",
  "constraints": {"KARMA": "bow", "SAMPRADANA": "Lakshmana"},
  "verb": "give"
}
```

### 5. Cypher Generator

**Purpose**: Generate Neo4j Cypher queries from decomposed questions

**Implementation**:
```python
class CypherGenerator:
    def generate(self, decomposition: Dict, min_confidence: float, document_filter: str = None) -> str:
        """
        Generates Cypher query with CORRECT direction: Action -> Entity
        The Kriya (Action) is the center, Kārakas point FROM action TO entities
        """
        target = decomposition['target_karaka']
        constraints = decomposition.get('constraints', {})
        verb = decomposition.get('verb')
        
        # CORRECTED: Action points TO Entity via Kāraka relationship
        query = f"""
        MATCH (a:Action)-[r:{target}]->(e:Entity)
        WHERE r.confidence >= {min_confidence}
        """
        
        if verb:
            query += f"\nAND a.verb = '{verb}'"
        
        if document_filter:
            query += f"\nAND a.document_id = '{document_filter}'"
        
        # Add constraint matches - Action points TO constraint entities
        for i, (karaka, entity) in enumerate(constraints.items()):
            query += f"""
            MATCH (a)-[:{karaka}]->(e{i}:Entity)
            WHERE toLower(e{i}.canonical_name) = toLower('{entity}')
            """
        
        query += """
        RETURN e.canonical_name AS answer,
               a.sentence AS source_sentence,
               a.sentence_id AS sentence_id,
               a.document_id AS document_id,
               r.confidence AS confidence
        ORDER BY r.confidence DESC
        LIMIT 5
        """
        
        return query
```

### 6. Answer Synthesizer

**Purpose**: Generate natural language answers from graph results

**Implementation**:
```python
class AnswerSynthesizer:
    def __init__(self, sagemaker_client):
        self.sagemaker = sagemaker_client
    
    def synthesize(self, question: str, graph_results: List[Dict], decomposition: Dict) -> Dict:
        """
        Uses Nemotron NIM to create natural language answer
        """
        if not graph_results:
            return {
                "answer": "I couldn't find an answer in the knowledge graph.",
                "sources": [],
                "confidence": 0.0
            }
        
        top_result = graph_results[0]
        prompt = self._build_synthesis_prompt(question, top_result, decomposition)
        answer_text = self._call_nemotron(prompt)
        
        return {
            "answer": answer_text,
            "sources": self._format_sources(graph_results),
            "karakas": decomposition,
            "confidence": top_result['confidence']
        }
```

## Deployment Strategy

### Phase 1: Infrastructure Setup

**Scripts to create**:
1. `deploy_sagemaker.py` - Deploy NIM endpoints
2. `setup_neo4j.sh` - Create Neo4j Aura instance (manual step with instructions)
3. `create_s3_bucket.sh` - Create S3 bucket for job tracking

**SageMaker Deployment**:
```python
import boto3

sagemaker = boto3.client('sagemaker')

# Deploy Nemotron NIM
sagemaker.create_model(
    ModelName='nemotron-karaka',
    PrimaryContainer={
        'Image': 'nvcr.io/nvidia/nim/llama-3.1-nemotron-nano-8b:latest',
        'ModelDataUrl': 's3://nvidia-nim-models/nemotron/model.tar.gz'
    },
    ExecutionRoleArn='arn:aws:iam::ACCOUNT:role/SageMakerRole'
)

sagemaker.create_endpoint_config(
    EndpointConfigName='nemotron-config',
    ProductionVariants=[{
        'VariantName': 'AllTraffic',
        'ModelName': 'nemotron-karaka',
        'InstanceType': 'ml.g5.xlarge',
        'InitialInstanceCount': 1
    }]
)

sagemaker.create_endpoint(
    EndpointName='nemotron-karaka-endpoint',
    EndpointConfigName='nemotron-config'
)
```

### Phase 2: Lambda Deployment

**Scripts to create**:
1. `package_lambda.sh` - Package dependencies
2. `deploy_lambda.sh` - Deploy all Lambda functions

**Lambda Packaging**:
```bash
#!/bin/bash
# package_lambda.sh

# Create package directory
rm -rf package lambda.zip
mkdir package

# Install dependencies
pip install -r requirements.txt -t package/

# Add source code
cp -r src/ package/

# Create zip
cd package && zip -r ../lambda.zip . && cd ..

# Add Lambda handlers
zip -g lambda.zip lambda/*.py
```

### Phase 3: API Gateway Setup

**Script**: `deploy_api_gateway.py`

Creates REST API with endpoints and Lambda integrations

### Phase 4: Frontend Deployment

**Options**:
1. S3 static website hosting
2. Run locally during development

## Error Handling

### Lambda Function Error Handling

```python
def lambda_handler(event, context):
    try:
        # Process request
        result = process_request(event)
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(result)
        }
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Invalid request', 'details': str(e)})
        }
    except SageMakerError as e:
        logger.error(f"SageMaker error: {str(e)}")
        return {
            'statusCode': 503,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'AI service unavailable', 'details': str(e)})
        }
    except Neo4jError as e:
        logger.error(f"Neo4j error: {str(e)}")
        return {
            'statusCode': 503,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Database unavailable', 'details': str(e)})
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Internal server error'})
        }
```

### Retry Logic for SageMaker Calls

```python
import time
import random

def call_sagemaker_with_retry(endpoint_name, payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = sagemaker_runtime.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            return json.loads(response['Body'].read())
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
                else:
                    raise
            else:
                raise
```

## Testing Strategy

### Unit Tests
- Test SRL parser with sample sentences
- Test Kāraka mapper with various SRL outputs
- Test Cypher generator with different query types
- Test entity resolver with similar/different entities

### Integration Tests
- Test full ingestion pipeline with sample document
- Test query pipeline end-to-end
- Test multi-document entity resolution

### AWS Integration Tests
- Verify SageMaker endpoints respond correctly
- Verify Lambda functions can call SageMaker
- Verify Neo4j connectivity from Lambda
- Verify S3 read/write operations

### End-to-End Tests
- Upload document → Verify graph creation
- Submit query → Verify correct answer
- Test with multiple documents → Verify document filtering

## Performance Considerations

### Lambda Optimization
- Keep deployment packages small (< 50MB)
- Use Lambda layers for common dependencies
- Initialize clients outside handler function
- Set appropriate timeout (300s for ingestion, 30s for queries)
- Set appropriate memory (1024MB for ingestion, 512MB for queries)

### SageMaker Optimization
- Use ml.g5.xlarge for cost-performance balance
- Implement request batching where possible
- Cache frequent queries (future enhancement)

### Neo4j Optimization
- Create indexes on canonical_name and document_id
- Use parameterized queries to leverage query cache
- Limit result sets (LIMIT 5 for queries)

### Cost Management
- Stop SageMaker endpoints when not in use
- Use S3 lifecycle policies for old job data
- Monitor CloudWatch metrics for usage patterns

## Security Considerations

### IAM Roles
- Lambda execution role with minimal permissions
- SageMaker execution role for model access
- S3 bucket policies for Lambda access only

### API Gateway
- Enable CORS with specific origins (production)
- Consider API keys for production deployment
- Rate limiting to prevent abuse

### Neo4j
- Use strong passwords
- Enable encryption in transit
- Restrict network access to Lambda security group

### Data Privacy
- No PII in logs
- Sanitize error messages
- Consider encryption at rest for S3

## Monitoring and Logging

### CloudWatch Metrics
- Lambda invocation count and duration
- SageMaker endpoint invocations and latency
- API Gateway request count and errors
- S3 storage usage

### CloudWatch Logs
- Lambda function logs with structured logging
- SageMaker endpoint logs
- API Gateway access logs

### Alarms
- Lambda error rate > 5%
- SageMaker endpoint latency > 5s
- API Gateway 5xx errors > 10/minute

## Multi-Hop Reasoning Through Kriya-Centric Graph

### Core Principle
**The Kriya (Action) is the binding force.** Entities are NOT directly connected. They are only related through the actions that bind them via Kāraka relationships.

### Example: Tracing Object Movement

**Sentences:**
1. "Vishwamitra gave bow to Rama."
2. "Rama gave bow to Lakshmana."
3. "Rama killed Ravana using the bow."

**Graph Structure:**
```
(gave_1)-[KARTA]->(Vishwamitra)
(gave_1)-[KARMA]->(bow)
(gave_1)-[SAMPRADANA]->(Rama)

(gave_2)-[KARTA]->(Rama)
(gave_2)-[KARMA]->(bow)
(gave_2)-[SAMPRADANA]->(Lakshmana)

(killed)-[KARTA]->(Rama)
(killed)-[KARMA]->(Ravana)
(killed)-[KARANA]->(bow)
```

**Query: "From where did Rama get the bow?"**

Multi-hop traversal:
```cypher
// Find action where Rama is SAMPRADANA (recipient) and bow is KARMA
MATCH (a1:Action)-[:SAMPRADANA]->(rama:Entity)
WHERE toLower(rama.canonical_name) = 'rama'

MATCH (a1)-[:KARMA]->(bow:Entity)
WHERE toLower(bow.canonical_name) = 'bow'

// Find who was KARTA (giver) in that action
MATCH (a1)-[:KARTA]->(giver:Entity)

RETURN giver.canonical_name AS answer,
       a1.sentence AS source_sentence
```

**Result:** "Vishwamitra" from sentence 1

**Query: "Who has the bow now?"**

Temporal reasoning (requires sentence_id ordering):
```cypher
// Find the most recent action involving the bow
MATCH (a:Action)-[:KARMA]->(bow:Entity)
WHERE toLower(bow.canonical_name) = 'bow'

// Check if bow was given away (SAMPRADANA exists)
OPTIONAL MATCH (a)-[:SAMPRADANA]->(recipient:Entity)

// Check if bow was used as instrument (KARANA)
OPTIONAL MATCH (a_use:Action)-[:KARANA]->(bow)
MATCH (a_use)-[:KARTA]->(user:Entity)

RETURN COALESCE(recipient.canonical_name, user.canonical_name) AS current_holder,
       a.sentence_id AS last_action_id
ORDER BY a.sentence_id DESC
LIMIT 1
```

**Result:** "Rama" (last used it in sentence 3, never gave it away after that)

### Enabling Complex Queries

**Query: "What did Rama do with the bow?"**
```cypher
// Find all actions where Rama is KARTA and bow is involved
MATCH (a:Action)-[:KARTA]->(rama:Entity)
WHERE toLower(rama.canonical_name) = 'rama'

MATCH (a)-[r]->(bow:Entity)
WHERE toLower(bow.canonical_name) = 'bow'

RETURN a.verb AS action,
       type(r) AS karaka_role,
       a.sentence AS sentence
ORDER BY a.sentence_id
```

**Results:**
1. "gave" (bow as KARMA) - "Rama gave bow to Lakshmana"
2. "killed" (bow as KARANA) - "Rama killed Ravana using the bow"

**Query: "Who did Rama give things to?"**
```cypher
MATCH (a:Action)-[:KARTA]->(rama:Entity)
WHERE toLower(rama.canonical_name) = 'rama'
AND a.verb = 'gave'

MATCH (a)-[:SAMPRADANA]->(recipient:Entity)
MATCH (a)-[:KARMA]->(object:Entity)

RETURN recipient.canonical_name AS recipient,
       object.canonical_name AS object,
       a.sentence AS sentence
```

**Result:** "Lakshmana" (received "bow")

### Causality and Temporal Chains

**Query: "What happened to the bow?"**

Trace the bow through all actions chronologically:
```cypher
MATCH (a:Action)-[r]->(bow:Entity)
WHERE toLower(bow.canonical_name) = 'bow'

MATCH (a)-[:KARTA]->(agent:Entity)

RETURN a.sentence_id AS order,
       agent.canonical_name AS agent,
       a.verb AS action,
       type(r) AS role,
       a.sentence AS sentence
ORDER BY a.sentence_id
```

**Results (chronological):**
1. Vishwamitra gave (KARMA) → to Rama
2. Rama gave (KARMA) → to Lakshmana  
3. Rama used (KARANA) → to kill Ravana

This shows the bow's journey through different Kāraka roles across multiple actions.

## Future Enhancements

### Phase 2 Features (Post-Hackathon)
1. Sanskrit translation layer
2. Temporal reasoning with sentence_id ordering (partially enabled above)
3. Causality detection (X caused Y) - track action chains
4. Multi-hop reasoning (chains of actions) - **ENABLED by Kriya-centric design**
5. User feedback loop for confidence improvement
6. Query history and saved queries
7. Batch document upload
8. Export graph as image
9. Advanced visualization filters
10. Inverse relationship queries ("Who received from Rama?" vs "Who gave to Rama?")

### Scalability Improvements
1. DynamoDB for job status (instead of S3)
2. SQS for async document processing
3. Step Functions for long-running workflows
4. ElastiCache for query caching
5. Multi-region deployment

## Critical Implementation Notes

### ⚠️ RELATIONSHIP DIRECTION IS CRITICAL

**CORRECT:** `(Action)-[KARAKA]->(Entity)`
**WRONG:** `(Entity)-[KARAKA]->(Action)`

All code that creates relationships in Neo4j must follow this pattern:

```python
# CORRECT - Action is the source, Entity is the target
session.run("""
    MATCH (a:Action {id: $action_id})
    MATCH (e:Entity {canonical_name: $entity_name})
    CREATE (a)-[:KARTA {confidence: $confidence, document_id: $doc_id}]->(e)
""", action_id=action_id, entity_name=entity_name, confidence=0.95, doc_id=doc_id)

# WRONG - Do not do this!
# CREATE (e)-[:KARTA]->(a)
```

All Cypher queries must traverse FROM Action TO Entity:

```python
# CORRECT - Start from Action, point to Entity
MATCH (a:Action)-[r:KARTA]->(e:Entity)

# WRONG - Do not do this!
# MATCH (e:Entity)-[r:KARTA]->(a:Action)
```

### Why This Matters

1. **Kriya-Centric Design**: The action is the center that binds entities
2. **Multi-Hop Reasoning**: Enables traversing through action chains
3. **Temporal Reasoning**: Actions have sentence_id for chronological ordering
4. **No Direct Entity Links**: Entities are only related through actions
5. **Correct Semantics**: "The action 'gave' has an agent (KARTA) Rama" not "Rama performs action gave"

## Development Workflow

### Local Development
1. Run Neo4j with Docker Compose
2. Use FastAPI to simulate Lambda locally
3. Use NVIDIA API (build.nvidia.com) for NIM calls
4. Test with sample documents
5. **Verify relationship direction in Neo4j browser**

### AWS Development
1. Deploy SageMaker endpoints
2. Deploy Lambda functions
3. Test with Postman or curl
4. Deploy frontend
5. **Verify graph structure with sample queries**

### Testing Workflow
1. Unit tests → Integration tests → AWS tests → E2E tests
2. Test locally first, then deploy to AWS
3. Use small documents for testing (< 50 sentences)
4. Verify each component independently
5. **Test multi-hop queries to ensure correct traversal**

## Conclusion

This design provides a comprehensive blueprint for building the Kāraka Graph RAG system on AWS infrastructure. The architecture is modular, scalable, and follows AWS best practices. The system leverages NVIDIA NIMs on SageMaker for AI capabilities while maintaining cost efficiency through proper resource management.

Key design decisions:
- ✅ Serverless architecture (Lambda) for cost efficiency
- ✅ SageMaker for NVIDIA NIM hosting (hackathon requirement)
- ✅ Neo4j for graph database (optimal for relationship queries)
- ✅ S3 for job tracking (simple and cost-effective)
- ✅ Modular components for independent testing
- ✅ Clear error handling and logging
- ✅ Deployment automation scripts
- ✅ Local development support

The design is ready for implementation following the task breakdown in tasks.md.
