# Complete AI Agent Coding Sequence

## Phase 0: Project Initialization

### Step 0.1: Create Project Structure
```bash
mkdir karaka-rag && cd karaka-rag

# Create directory structure
mkdir -p {src/{ingestion,query,graph,utils},lambda,frontend/{src,public},infrastructure,data/{raw,processed},tests,docs}

# Initialize git
git init
echo "node_modules/\n__pycache__/\n.env\n*.pyc\npackage/\nlambda.zip" > .gitignore

# Create main files
touch README.md requirements.txt docker-compose.yml .env.example
touch src/{__init__.py,config.py}
touch lambda/handler.py
touch infrastructure/{deploy.sh,destroy.sh,terraform.tf}
```

**Final structure:**
```
karaka-rag/
├── src/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── srl_parser.py          # spaCy SRL extraction
│   │   ├── karaka_mapper.py       # Map SRL → Kāraka
│   │   ├── entity_resolver.py     # Entity resolution using embeddings
│   │   └── graph_builder.py       # Build Neo4j graph
│   ├── query/
│   │   ├── __init__.py
│   │   ├── decomposer.py          # Query → Kāraka mapping
│   │   ├── cypher_generator.py    # Generate graph queries
│   │   └── answer_synthesizer.py  # LLM answer generation
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── neo4j_client.py        # Neo4j connection
│   │   └── schema.py              # Graph schema definitions
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── nim_client.py          # NVIDIA NIM API calls
│   │   └── logger.py              # Logging utilities
│   └── config.py                  # Configuration management
├── lambda/
│   ├── handler.py                 # API Gateway handler
│   ├── ingestion_handler.py       # Document upload handler
│   └── query_handler.py           # Query handler
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── DocumentUpload.jsx
│   │   │   ├── QueryInterface.jsx
│   │   │   ├── GraphVisualization.jsx
│   │   │   └── ProgressTracker.jsx
│   │   └── utils/api.js
│   ├── package.json
│   └── vite.config.js
├── infrastructure/
│   ├── deploy.sh                  # Deploy everything
│   ├── destroy.sh                 # Cleanup resources
│   ├── terraform.tf               # IaC (optional)
│   └── cloudformation.yaml        # Alternative IaC
├── data/
│   ├── raw/                       # Original documents
│   └── processed/                 # Preprocessed data
├── tests/
│   ├── test_ingestion.py
│   ├── test_query.py
│   └── test_e2e.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── DEPLOYMENT.md
├── docker-compose.yml             # Local Neo4j
├── requirements.txt
├── .env.example
└── README.md
```

---

## Phase 1: Requirements Definition

### Step 1.1: Define `requirements.txt`
```txt
# Core Dependencies
spacy==3.7.2
en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0-py3-none-any.whl
neo4j==5.14.0
boto3==1.34.0
python-dotenv==1.0.0

# AWS SDK
sagemaker==2.196.0

# API & Web
fastapi==0.109.0
uvicorn==0.27.0
pydantic==2.5.0

# Utilities
requests==2.31.0
pandas==2.1.4
numpy==1.26.2
tqdm==4.66.1

# Testing
pytest==7.4.3
pytest-asyncio==0.23.2
```

### Step 1.2: Define `frontend/package.json`
```json
{
  "name": "karaka-rag-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "vis-network": "^9.1.9",
    "lucide-react": "^0.263.1",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0"
  }
}
```

### Step 1.3: Define `.env.example`
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET=karaka-rag-demo

# SageMaker Endpoints
NEMOTRON_ENDPOINT=nemotron-karaka
EMBEDDING_ENDPOINT=embedding-karaka

# Neo4j Configuration
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# API Configuration
API_GATEWAY_URL=https://xxxx.execute-api.us-east-1.amazonaws.com/prod

# Local Development
NEO4J_LOCAL_URI=bolt://localhost:7687
NEO4J_LOCAL_PASSWORD=password
```

---

## Phase 2: Design Documentation

### Step 2.1: Create `docs/ARCHITECTURE.md`
```markdown
# Kāraka Graph RAG Architecture

## System Components

### 1. Ingestion Pipeline
User uploads document → Lambda processes sentences → Extracts Kārakas → Builds graph

### 2. Query Pipeline
User query → Nemotron decomposes → Cypher generation → Neo4j execution → Answer synthesis

## Data Flow Diagram
```
[Document Upload]
    ↓
[Lambda: Ingestion Handler]
    ↓
[spaCy SRL Parser] → [Kāraka Mapper]
    ↓
[Entity Resolver (Embedding NIM)]
    ↓
[Neo4j Graph Builder]
    ↓
[Progress Status in S3]

[User Query]
    ↓
[Lambda: Query Handler]
    ↓
[Nemotron: Query Decomposer]
    ↓
[Cypher Generator]
    ↓
[Neo4j: Graph Traversal]
    ↓
[Nemotron: Answer Synthesizer]
    ↓
[Response with Citations]
```

## Graph Schema
```cypher
(:Entity {canonical_name, aliases[], properties[]})
-[:KARTA {confidence, source_sentence_id}]->
(:Action {verb, sentence, sentence_id})
-[:KARMA {confidence, source_sentence_id}]->
(:Entity)
```

## API Endpoints
- POST /ingest - Upload document for processing
- GET /ingest/status/:job_id - Check ingestion progress
- POST /query - Ask questions
- GET /graph - Get graph data for visualization
```

### Step 2.2: Create `docs/API.md`
```markdown
# API Documentation

## POST /ingest
Upload document for Kāraka extraction.

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
  "job_id": "job_12345",
  "status": "processing",
  "total_sentences": 500
}
```

## GET /ingest/status/:job_id
Check ingestion progress.

**Response:**
```json
{
  "job_id": "job_12345",
  "status": "processing",
  "progress": 250,
  "total": 500,
  "percentage": 50
}
```

## POST /query
Query the graph.

**Request:**
```json
{
  "question": "Who gave bow to Lakshmana?",
  "min_confidence": 0.8
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
      "confidence": 0.95
    }
  ],
  "karakas": {
    "KARTA": "Rama",
    "KARMA": "bow",
    "SAMPRADANA": "Lakshmana"
  }
}
```

## GET /graph
Get full graph for visualization.

**Response:**
```json
{
  "nodes": [
    {"id": "rama", "label": "Rama", "type": "Entity"},
    {"id": "action_42", "label": "gave", "type": "Action"}
  ],
  "edges": [
    {"from": "rama", "to": "action_42", "label": "KARTA", "confidence": 0.95}
  ]
}
```
```

---

## Phase 3: Task Breakdown

### Step 3.1: Create `docs/TASKS.md`
```markdown
# Development Tasks

## Core Ingestion (Priority 1)
- [ ] Task 1.1: Implement spaCy SRL parser (src/ingestion/srl_parser.py)
- [ ] Task 1.2: Build SRL → Kāraka mapper (src/ingestion/karaka_mapper.py)
- [ ] Task 1.3: Implement entity resolver with embeddings (src/ingestion/entity_resolver.py)
- [ ] Task 1.4: Build Neo4j graph constructor (src/ingestion/graph_builder.py)
- [ ] Task 1.5: Create ingestion Lambda handler (lambda/ingestion_handler.py)

## Core Query (Priority 1)
- [ ] Task 2.1: Implement query decomposer with Nemotron (src/query/decomposer.py)
- [ ] Task 2.2: Build Cypher query generator (src/query/cypher_generator.py)
- [ ] Task 2.3: Implement answer synthesizer (src/query/answer_synthesizer.py)
- [ ] Task 2.4: Create query Lambda handler (lambda/query_handler.py)

## Infrastructure (Priority 2)
- [ ] Task 3.1: Write deployment script (infrastructure/deploy.sh)
- [ ] Task 3.2: Write destroy script (infrastructure/destroy.sh)
- [ ] Task 3.3: Deploy NVIDIA NIMs to SageMaker
- [ ] Task 3.4: Setup Neo4j Aura instance
- [ ] Task 3.5: Configure API Gateway + Lambda

## Frontend (Priority 3)
- [ ] Task 4.1: Build document upload component (frontend/src/components/DocumentUpload.jsx)
- [ ] Task 4.2: Build progress tracker (frontend/src/components/ProgressTracker.jsx)
- [ ] Task 4.3: Build query interface (frontend/src/components/QueryInterface.jsx)
- [ ] Task 4.4: Build graph visualization (frontend/src/components/GraphVisualization.jsx)

## Testing & Polish (Priority 4)
- [ ] Task 5.1: Write integration tests
- [ ] Task 5.2: Create demo video script
- [ ] Task 5.3: Polish README with examples
- [ ] Task 5.4: Test full deployment from scratch
```

---

## Phase 4: Infrastructure Setup

### Step 4.1: Create `docker-compose.yml` (Local Development)
```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.14.0
    container_name: karaka-neo4j
    ports:
      - "7474:7474"  # Browser
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs

  api:
    build: .
    container_name: karaka-api
    ports:
      - "8000:8000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_PASSWORD=password
    depends_on:
      - neo4j
    volumes:
      - ./src:/app/src
      - ./data:/app/data

volumes:
  neo4j_data:
  neo4j_logs:
```

### Step 4.2: Create `infrastructure/deploy.sh`
```bash
#!/bin/bash
set -e

echo "🚀 Starting Kāraka RAG Deployment..."

# Load environment variables
source .env

# Step 1: Create S3 bucket for storage
echo "📦 Creating S3 bucket..."
aws s3 mb s3://$S3_BUCKET --region $AWS_REGION || echo "Bucket already exists"

# Step 2: Deploy NVIDIA NIMs to SageMaker
echo "🤖 Deploying NVIDIA NIMs..."
python infrastructure/deploy_nims.py

# Step 3: Setup Neo4j (manual step - output instructions)
echo "📊 Neo4j Setup:"
echo "   1. Go to https://aura.neo4j.io"
echo "   2. Create free instance"
echo "   3. Update NEO4J_URI in .env"
echo "   Press Enter when done..."
read

# Step 4: Deploy Lambda functions
echo "⚡ Deploying Lambda functions..."

# Package dependencies
rm -rf package lambda.zip
mkdir package
pip install -r requirements.txt -t package/
cd package && zip -r ../lambda.zip . && cd ..
zip -g lambda.zip lambda/*.py src/**/*.py

# Create/Update Lambda function
aws lambda create-function \
  --function-name karaka-rag-ingestion \
  --runtime python3.11 \
  --role $LAMBDA_ROLE_ARN \
  --handler lambda.ingestion_handler.handler \
  --zip-file fileb://lambda.zip \
  --timeout 900 \
  --memory-size 1024 \
  --environment "Variables={NEO4J_URI=$NEO4J_URI,NEO4J_PASSWORD=$NEO4J_PASSWORD,NEMOTRON_ENDPOINT=$NEMOTRON_ENDPOINT,EMBEDDING_ENDPOINT=$EMBEDDING_ENDPOINT}" \
  || aws lambda update-function-code \
  --function-name karaka-rag-ingestion \
  --zip-file fileb://lambda.zip

aws lambda create-function \
  --function-name karaka-rag-query \
  --runtime python3.11 \
  --role $LAMBDA_ROLE_ARN \
  --handler lambda.query_handler.handler \
  --zip-file fileb://lambda.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment "Variables={NEO4J_URI=$NEO4J_URI,NEO4J_PASSWORD=$NEO4J_PASSWORD,NEMOTRON_ENDPOINT=$NEMOTRON_ENDPOINT}" \
  || aws lambda update-function-code \
  --function-name karaka-rag-query \
  --zip-file fileb://lambda.zip

# Step 5: Create API Gateway
echo "🌐 Creating API Gateway..."
python infrastructure/setup_api_gateway.py

# Step 6: Deploy Frontend to S3
echo "🎨 Building and deploying frontend..."
cd frontend
npm install
npm run build
aws s3 sync dist/ s3://$S3_BUCKET-frontend --delete
aws s3 website s3://$S3_BUCKET-frontend --index-document index.html
cd ..

echo "✅ Deployment Complete!"
echo "📝 API Gateway URL: $(aws apigateway get-rest-apis --query 'items[?name==`karaka-rag-api`].id' --output text)"
echo "🌍 Frontend URL: http://$S3_BUCKET-frontend.s3-website-$AWS_REGION.amazonaws.com"
```

### Step 4.3: Create `infrastructure/destroy.sh`
```bash
#!/bin/bash
set -e

echo "🗑️  Starting Kāraka RAG Cleanup..."

source .env

# Delete Lambda functions
echo "Deleting Lambda functions..."
aws lambda delete-function --function-name karaka-rag-ingestion || true
aws lambda delete-function --function-name karaka-rag-query || true

# Delete API Gateway
echo "Deleting API Gateway..."
API_ID=$(aws apigateway get-rest-apis --query 'items[?name==`karaka-rag-api`].id' --output text)
aws apigateway delete-rest-api --rest-api-id $API_ID || true

# Delete SageMaker endpoints
echo "Deleting SageMaker endpoints..."
aws sagemaker delete-endpoint --endpoint-name $NEMOTRON_ENDPOINT || true
aws sagemaker delete-endpoint --endpoint-name $EMBEDDING_ENDPOINT || true

# Delete S3 buckets
echo "Deleting S3 buckets..."
aws s3 rb s3://$S3_BUCKET --force || true
aws s3 rb s3://$S3_BUCKET-frontend --force || true

echo "✅ Cleanup Complete!"
echo "⚠️  Manual steps:"
echo "   - Delete Neo4j Aura instance at https://aura.neo4j.io"
echo "   - Check AWS console for any remaining resources"
```

### Step 4.4: Create `infrastructure/deploy_nims.py`
```python
import boto3
import json
import time
from dotenv import load_dotenv
import os

load_dotenv()

sagemaker = boto3.client('sagemaker', region_name=os.getenv('AWS_REGION'))

def deploy_nim(model_name, endpoint_name, instance_type='ml.g5.xlarge'):
    """Deploy NVIDIA NIM to SageMaker"""

    print(f"Deploying {model_name} to {endpoint_name}...")

    # Create model
    model_response = sagemaker.create_model(
        ModelName=f'{endpoint_name}-model',
        PrimaryContainer={
            'Image': f'nvcr.io/nvidia/nim/{model_name}:latest',
            'ModelDataUrl': f's3://nvidia-nim-models/{model_name}/model.tar.gz'
        },
        ExecutionRoleArn=os.getenv('SAGEMAKER_ROLE_ARN')
    )

    # Create endpoint config
    config_response = sagemaker.create_endpoint_config(
        EndpointConfigName=f'{endpoint_name}-config',
        ProductionVariants=[{
            'VariantName': 'AllTraffic',
            'ModelName': f'{endpoint_name}-model',
            'InstanceType': instance_type,
            'InitialInstanceCount': 1
        }]
    )

    # Create endpoint
    endpoint_response = sagemaker.create_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=f'{endpoint_name}-config'
    )

    print(f"Waiting for {endpoint_name} to be InService...")
    waiter = sagemaker.get_waiter('endpoint_in_service')
    waiter.wait(EndpointName=endpoint_name)

    print(f"✅ {endpoint_name} deployed successfully!")
    return endpoint_name

if __name__ == '__main__':
    # Deploy Nemotron
    deploy_nim(
        'llama-3.1-nemotron-nano-8b-v1',
        os.getenv('NEMOTRON_ENDPOINT')
    )

    # Deploy Embedding
    deploy_nim(
        'nvidia-retrieval-embedding',
        os.getenv('EMBEDDING_ENDPOINT')
    )
```

---

## Phase 5: Core Implementation

### Step 5.1: Implement `src/config.py`
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # AWS
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    S3_BUCKET = os.getenv('S3_BUCKET')

    # SageMaker
    NEMOTRON_ENDPOINT = os.getenv('NEMOTRON_ENDPOINT')
    EMBEDDING_ENDPOINT = os.getenv('EMBEDDING_ENDPOINT')

    # Neo4j
    NEO4J_URI = os.getenv('NEO4J_URI', os.getenv('NEO4J_LOCAL_URI'))
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', os.getenv('NEO4J_LOCAL_PASSWORD'))

    # Kāraka Configuration
    KARAKA_TYPES = ['KARTA', 'KARMA', 'KARANA', 'SAMPRADANA', 'APADANA', 'ADHIKARANA']
    MIN_CONFIDENCE = 0.8

    # Ingestion
    BATCH_SIZE = 10
    MAX_SENTENCE_LENGTH = 500

config = Config()
```

### Step 5.2: Implement `src/utils/nim_client.py`
```python
import boto3
import json
from src.config import config

class NIMClient:
    def __init__(self):
        self.runtime = boto3.client('sagemaker-runtime', region_name=config.AWS_REGION)

    def call_nemotron(self, prompt, max_tokens=500):
        """Call Nemotron NIM for text generation"""
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "top_p": 0.9
        }

        response = self.runtime.invoke_endpoint(
            EndpointName=config.NEMOTRON_ENDPOINT,
            ContentType='application/json',
            Body=json.dumps(payload)
        )

        result = json.loads(response['Body'].read())
        return result.get('generated_text', result.get('text', ''))

    def get_embedding(self, text):
        """Get embedding vector from Embedding NIM"""
        payload = {"text": text}

        response = self.runtime.invoke_endpoint(
            EndpointName=config.EMBEDDING_ENDPOINT,
            ContentType='application/json',
            Body=json.dumps(payload)
        )

        result = json.loads(response['Body'].read())
        return result.get('embedding', result.get('vector', []))

    def batch_get_embeddings(self, texts):
        """Get embeddings for multiple texts"""
        return [self.get_embedding(text) for text in texts]

nim_client = NIMClient()
```

### Step 5.3: Implement `src/graph/neo4j_client.py`
```python
from neo4j import GraphDatabase
from src.config import config

class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def create_entity(self, canonical_name, aliases=None):
        """Create or merge an Entity node"""
        with self.driver.session() as session:
            result = session.run("""
                MERGE (e:Entity {canonical_name: $canonical_name})
                ON CREATE SET e.aliases = $aliases, e.created_at = timestamp()
                RETURN e
            """, canonical_name=canonical_name, aliases=aliases or [])
            return result.single()

    def create_action(self, action_id, verb, sentence, sentence_id):
        """Create an Action node"""
        with self.driver.session() as session:
            result = session.run("""
                CREATE (a:Action {
                    id: $action_id,
                    verb: $verb,
                    sentence: $sentence,
                    sentence_id: $sentence_id,
                    created_at: timestamp()
                })
                RETURN a
            """, action_id=action_id, verb=verb, sentence=sentence, sentence_id=sentence_id)
            return result.single()

    def create_karaka_relationship(self, entity_name, karaka_type, action_id, confidence, source_sentence_id):
        """Create a Kāraka relationship"""
        with self.driver.session() as session:
            session.run(f"""
                MATCH (e:Entity {{canonical_name: $entity_name}})
                MATCH (a:Action {{id: $action_id}})
                CREATE (e)-[r:{karaka_type} {{
                    confidence: $confidence,
                    source_sentence_id: $source_sentence_id,
                    created_at: timestamp()
                }}]->(a)
            """, entity_name=entity_name, action_id=action_id,
                confidence=confidence, source_sentence_id=source_sentence_id)

    def execute_query(self, cypher_query, params=None):
        """Execute arbitrary Cypher query"""
        with self.driver.session() as session:
            result = session.run(cypher_query, params or {})
            return [record.data() for record in result]

    def get_graph_for_visualization(self):
        """Get all nodes and edges for frontend visualization"""
        with self.driver.session() as session:
            # Get nodes
            nodes_result = session.run("""
                MATCH (n)
                RETURN id(n) as id, labels(n) as labels, properties(n) as properties
            """)
            nodes = [
                {
                    "id": str(record["id"]),
                    "label": record["properties"].get("canonical_name") or record["properties"].get("verb"),
                    "type": record["labels"][0],
                    "properties": record["properties"]
                }
                for record in nodes_result
            ]

            # Get edges
            edges_result = session.run("""
                MATCH (n)-[r]->(m)
                RETURN id(n) as from, id(m) as to, type(r) as type, properties(r) as properties
            """)
            edges = [
                {
                    "from": str(record["from"]),
                    "to": str(record["to"]),
                    "label": record["type"],
                    "confidence": record["properties"].get("confidence")
                }
                for record in edges_result
            ]

            return {"nodes": nodes, "edges": edges}

neo4j_client = Neo4jClient()
```

### Step 5.4: Implement `src/ingestion/srl_parser.py`
```python
import spacy
from typing import Dict, List, Tuple

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

class SRLParser:
    """Extract semantic roles using spaCy dependency parsing"""

    def __init__(self):
        self.nlp = nlp

    def parse_sentence(self, sentence: str) -> Tuple[str, Dict[str, str]]:
        """
        Parse sentence and extract verb + semantic roles

        Returns:
            (verb, {role: entity})
            e.g., ("give", {"nsubj": "Rama", "obj": "bow", "iobj": "Lakshmana"})
        """
        doc = self.nlp(sentence)

        verb = None
        roles = {}

        for token in doc:
            # Find main verb
            if token.pos_ == 'VERB' and token.dep_ in ['ROOT', 'ccomp']:
                verb = token.lemma_

            # Extract semantic roles
            if token.dep_ in ['nsubj', 'obj', 'iobj', 'obl', 'nmod']:
                # Get full noun phrase
                if token.dep_ == 'nsubj':
                    roles['nsubj'] = self._get_noun_phrase(token)
                elif token.dep_ == 'obj':
                    roles['obj'] = self._get_noun_phrase(token)
                elif token.dep_ == 'iobj':
                    roles['iobj'] = self._get_noun_phrase(token)
                elif token.dep_ == 'obl':
                    # Check preposition for locative/instrumental
                    if token.head.text in ['with', 'using']:
                        roles['obl:with'] = self._get_noun_phrase(token)
                    elif token.head.text in ['at', 'in', 'on']:
                        roles['obl:loc'] = self._get_noun_phrase(token)

        return verb, roles

    def _get_noun_phrase(self, token):
        """Extract full noun phrase from token"""
        # Get all children and descendants
        phrase_tokens = [token]
        for child in token.children:
            if child.dep_ in ['det', 'amod', 'compound', 'poss']:
                phrase_tokens.append(child)

        # Sort by position and join
        phrase_tokens.sort(key=lambda t: t.i)
        return ' '.join([t.text for t in phrase_tokens])

srl_parser = SRLParser()
```

### Step 5.5: Implement `src/ingestion/karaka_mapper.py`
```python
from typing import Dict

class KarakaMapper:
    """Map spaCy SRL roles to Pāṇinian Kārakas"""

    SRL_TO_KARAKA = {
        'nsubj': 'KARTA',        # Subject → Agent
        'obj': 'KARMA',          # Direct object → Patient
        'iobj': 'SAMPRADANA',    # Indirect object → Recipient
        'obl:with': 'KARANA',    # Instrumental
        'obl:loc': 'ADHIKARANA', # Locative
        'obl:from': 'APADANA'    # Source/Ablative
    }

    def map_to_karakas(self, srl_roles: Dict[str, str]) -> Dict[str, str]:
        """
        Convert SRL roles to Kāraka roles

        Args:
            srl_roles: {"nsubj": "Rama", "obj": "bow", ...}

        Returns:
            {"KARTA": "Rama", "KARMA": "bow", ...}
        """
        karakas = {}

        for srl_role, entity in srl_roles.items():
            if srl_role in self.SRL_TO_KARAKA:
                karaka_type = self.SRL_TO_KARAKA[srl_role]
                karakas[karaka_type] = entity

        return karakas

karaka_mapper = KarakaMapper()
```

### Step 5.6: Implement `src/ingestion/entity_resolver.py`
```python
from typing import List, Dict
from src.utils.nim_client import nim_client
import numpy as np

class EntityResolver:
    """Resolve entity mentions to canonical names using embeddings"""
    ```python
    def __init__(self):
        self.nim_client = nim_client
        self.entity_cache = {}  # {canonical_name: [aliases]}
        self.embedding_cache = {}  # {canonical_name: embedding_vector}
        self.similarity_threshold = 0.85

    def resolve_entity(self, entity_mention: str) -> str:
        """
        Resolve entity mention to canonical name

        Args:
            entity_mention: "the king", "he", "Rama"

        Returns:
            canonical_name: "Rama"
        """
        # Normalize
        entity_clean = entity_mention.strip().lower()

        # Check if already canonical
        if entity_clean in self.entity_cache:
            return entity_clean

        # Check if it's an alias
        for canonical, aliases in self.entity_cache.items():
            if entity_clean in [a.lower() for a in aliases]:
                return canonical

        # Use embeddings to find similar entities
        if self.entity_cache:
            entity_embedding = self.nim_client.get_embedding(entity_mention)

            best_match = None
            best_score = 0

            for canonical, canonical_embedding in self.embedding_cache.items():
                similarity = self._cosine_similarity(entity_embedding, canonical_embedding)
                if similarity > best_score and similarity > self.similarity_threshold:
                    best_score = similarity
                    best_match = canonical

            if best_match:
                # Add as alias
                self.entity_cache[best_match].append(entity_mention)
                return best_match

        # New entity - create canonical entry
        canonical_name = entity_mention.strip()
        self.entity_cache[canonical_name] = [entity_mention]
        self.embedding_cache[canonical_name] = self.nim_client.get_embedding(canonical_name)

        return canonical_name

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def get_entity_info(self, canonical_name: str) -> Dict:
        """Get entity info including all aliases"""
        return {
            "canonical_name": canonical_name,
            "aliases": self.entity_cache.get(canonical_name, [])
        }

entity_resolver = EntityResolver()
```

### Step 5.7: Implement `src/ingestion/graph_builder.py`
```python
from typing import Dict, List
from src.graph.neo4j_client import neo4j_client
from src.ingestion.srl_parser import srl_parser
from src.ingestion.karaka_mapper import karaka_mapper
from src.ingestion.entity_resolver import entity_resolver
import uuid

class GraphBuilder:
    """Build Neo4j graph from sentences"""

    def __init__(self):
        self.neo4j = neo4j_client
        self.srl_parser = srl_parser
        self.karaka_mapper = karaka_mapper
        self.entity_resolver = entity_resolver

    def process_sentence(self, sentence: str, sentence_id: int) -> Dict:
        """
        Process single sentence and add to graph

        Returns:
            Status dict with extracted Kārakas
        """
        try:
            # Step 1: SRL parsing
            verb, srl_roles = self.srl_parser.parse_sentence(sentence)

            if not verb:
                return {"status": "skipped", "reason": "no_verb"}

            # Step 2: Map to Kārakas
            karakas = self.karaka_mapper.map_to_karakas(srl_roles)

            if not karakas:
                return {"status": "skipped", "reason": "no_karakas"}

            # Step 3: Resolve entities
            resolved_karakas = {}
            for karaka_type, entity_mention in karakas.items():
                canonical = self.entity_resolver.resolve_entity(entity_mention)
                resolved_karakas[karaka_type] = canonical

            # Step 4: Build graph
            action_id = f"action_{sentence_id}"

            # Create action node
            self.neo4j.create_action(action_id, verb, sentence, sentence_id)

            # Create entity nodes and relationships
            for karaka_type, canonical_name in resolved_karakas.items():
                # Create entity
                entity_info = self.entity_resolver.get_entity_info(canonical_name)
                self.neo4j.create_entity(canonical_name, entity_info["aliases"])

                # Create Kāraka relationship
                self.neo4j.create_karaka_relationship(
                    entity_name=canonical_name,
                    karaka_type=karaka_type,
                    action_id=action_id,
                    confidence=0.85,  # Base confidence from SRL
                    source_sentence_id=sentence_id
                )

            return {
                "status": "success",
                "verb": verb,
                "karakas": resolved_karakas,
                "action_id": action_id
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def process_document(self, sentences: List[str]) -> Dict:
        """
        Process entire document

        Returns:
            Summary statistics
        """
        results = {
            "total": len(sentences),
            "success": 0,
            "skipped": 0,
            "errors": 0,
            "details": []
        }

        for idx, sentence in enumerate(sentences):
            result = self.process_sentence(sentence, idx)
            results["details"].append(result)

            if result["status"] == "success":
                results["success"] += 1
            elif result["status"] == "skipped":
                results["skipped"] += 1
            else:
                results["errors"] += 1

        return results

graph_builder = GraphBuilder()
```

---

## Phase 6: Document Upload & Progress Tracking

### Step 6.1: Implement `lambda/ingestion_handler.py`
```python
import json
import boto3
import base64
from src.ingestion.graph_builder import graph_builder
import uuid

s3 = boto3.client('s3')
S3_BUCKET = os.getenv('S3_BUCKET')

def handler(event, context):
    """
    Handle document upload and ingestion

    POST /ingest
    Body: {
        "document_name": "ramayana.txt",
        "content": "base64_encoded_content"
    }
    """
    try:
        body = json.loads(event['body'])
        document_name = body['document_name']
        content_b64 = body['content']

        # Decode content
        content = base64.b64decode(content_b64).decode('utf-8')

        # Split into sentences
        sentences = [s.strip() for s in content.split('.') if s.strip()]

        # Create job ID
        job_id = str(uuid.uuid4())

        # Initialize progress tracking in S3
        progress = {
            "job_id": job_id,
            "document_name": document_name,
            "total_sentences": len(sentences),
            "processed": 0,
            "status": "processing",
            "results": []
        }

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=f"jobs/{job_id}/progress.json",
            Body=json.dumps(progress)
        )

        # Process sentences (in batches for Lambda timeout)
        batch_size = 50
        for i in range(0, len(sentences), batch_size):
            batch = sentences[i:i+batch_size]

            for idx, sentence in enumerate(batch):
                global_idx = i + idx
                result = graph_builder.process_sentence(sentence, global_idx)

                # Update progress
                progress["processed"] += 1
                progress["results"].append({
                    "sentence_id": global_idx,
                    "sentence": sentence[:100],
                    "status": result["status"],
                    "karakas": result.get("karakas", {})
                })

                # Update S3 every 10 sentences
                if (global_idx + 1) % 10 == 0:
                    s3.put_object(
                        Bucket=S3_BUCKET,
                        Key=f"jobs/{job_id}/progress.json",
                        Body=json.dumps(progress)
                    )

        # Mark as complete
        progress["status"] = "completed"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=f"jobs/{job_id}/progress.json",
            Body=json.dumps(progress)
        )

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                "job_id": job_id,
                "status": "completed",
                "total_sentences": len(sentences),
                "processed": progress["processed"]
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({"error": str(e)})
        }

def get_status_handler(event, context):
    """
    Get ingestion progress

    GET /ingest/status/{job_id}
    """
    try:
        job_id = event['pathParameters']['job_id']

        # Get progress from S3
        response = s3.get_object(
            Bucket=S3_BUCKET,
            Key=f"jobs/{job_id}/progress.json"
        )

        progress = json.loads(response['Body'].read())

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                "job_id": progress["job_id"],
                "status": progress["status"],
                "progress": progress["processed"],
                "total": progress["total_sentences"],
                "percentage": round((progress["processed"] / progress["total_sentences"]) * 100, 2)
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({"error": str(e)})
        }
```

---

## Phase 7: Query Pipeline

### Step 7.1: Implement `src/query/decomposer.py`
```python
from src.utils.nim_client import nim_client
import json
import re

class QueryDecomposer:
    """Decompose natural language query into Kāraka-based graph query"""

    INTERROGATIVE_TO_KARAKA = {
        'who': 'KARTA',
        'whom': 'KARMA',
        'what': 'KARMA',
        'to whom': 'SAMPRADANA',
        'where': 'ADHIKARANA',
        'with what': 'KARANA',
        'from where': 'APADANA'
    }

    def __init__(self):
        self.nim = nim_client

    def decompose(self, question: str) -> dict:
        """
        Decompose question using Nemotron LLM

        Args:
            question: "Who gave bow to Lakshmana?"

        Returns:
            {
                "target_karaka": "KARTA",
                "constraints": {
                    "KARMA": "bow",
                    "SAMPRADANA": "Lakshmana"
                },
                "verb": "give"
            }
        """
        prompt = f"""You are a semantic query analyzer for a Kāraka-based knowledge graph.

Question: "{question}"

Analyze this question and identify:
1. Which Kāraka role is being asked about (KARTA=agent, KARMA=patient/object, KARANA=instrument, SAMPRADANA=recipient, ADHIKARANA=location, APADANA=source)
2. What constraints are given (other Kāraka roles mentioned)
3. The action/verb involved

Respond ONLY with valid JSON in this exact format:
{{
  "target_karaka": "KARTA",
  "constraints": {{"KARMA": "bow", "SAMPRADANA": "Lakshmana"}},
  "verb": "give"
}}

JSON Response:"""

        response = self.nim.call_nemotron(prompt, max_tokens=200)

        # Parse JSON from response
        try:
            # Extract JSON from response (handle markdown formatting)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                return json.loads(response)
        except:
            # Fallback to rule-based
            return self._fallback_decompose(question)

    def _fallback_decompose(self, question: str) -> dict:
        """Simple rule-based fallback"""
        question_lower = question.lower()

        target_karaka = None
        for interrogative, karaka in self.INTERROGATIVE_TO_KARAKA.items():
            if question_lower.startswith(interrogative):
                target_karaka = karaka
                break

        return {
            "target_karaka": target_karaka or "KARTA",
            "constraints": {},
            "verb": None
        }

query_decomposer = QueryDecomposer()
```

### Step 7.2: Implement `src/query/cypher_generator.py`
```python
from typing import Dict

class CypherGenerator:
    """Generate Cypher queries from decomposed questions"""

    def generate(self, decomposition: Dict, min_confidence: float = 0.8) -> str:
        """
        Generate Cypher query

        Args:
            decomposition: {
                "target_karaka": "KARTA",
                "constraints": {"KARMA": "bow"},
                "verb": "give"
            }

        Returns:
            Cypher query string
        """
        target = decomposition.get('target_karaka')
        constraints = decomposition.get('constraints', {})
        verb = decomposition.get('verb')

        # Build base query
        query_parts = []

        # Match target Kāraka
        query_parts.append(f"""
            MATCH (e:Entity)-[r:{target}]->(a:Action)
            WHERE r.confidence >= {min_confidence}
        """)

        # Add verb constraint if specified
        if verb:
            query_parts.append(f"""
            AND a.verb = '{verb}'
            """)

        # Add other Kāraka constraints
        constraint_idx = 2
        for karaka_type, entity_name in constraints.items():
            query_parts.append(f"""
            MATCH (a)-[:{karaka_type}]->(e{constraint_idx}:Entity)
            WHERE toLower(e{constraint_idx}.canonical_name) = toLower('{entity_name}')
            """)
            constraint_idx += 1

        # Return clause
        query_parts.append("""
            RETURN
                e.canonical_name AS answer,
                a.sentence AS source_sentence,
                a.sentence_id AS sentence_id,
                r.confidence AS confidence
            ORDER BY r.confidence DESC
            LIMIT 5
        """)

        return '\n'.join(query_parts)

cypher_generator = CypherGenerator()
```

### Step 7.3: Implement `src/query/answer_synthesizer.py`
```python
from src.utils.nim_client import nim_client
from typing import List, Dict

class AnswerSynthesizer:
    """Synthesize natural language answers from graph results"""

    def __init__(self):
        self.nim = nim_client

    def synthesize(self, question: str, graph_results: List[Dict], decomposition: Dict) -> Dict:
        """
        Generate natural language answer

        Args:
            question: Original user question
            graph_results: Results from Neo4j query
            decomposition: Original query decomposition

        Returns:
            {
                "answer": "Rama (KARTA) gave the bow (KARMA) to Lakshmana (SAMPRADANA).",
                "sources": [...],
                "confidence": 0.95
            }
        """
        if not graph_results:
            return {
                "answer": "I couldn't find an answer to that question in the knowledge graph.",
                "sources": [],
                "confidence": 0.0
            }

        # Get top result
        top_result = graph_results[0]

        # Build context for LLM
        context = f"""Source sentence: "{top_result['source_sentence']}"

Question: {question}

Based on the source sentence, the answer is: {top_result['answer']}

The semantic roles (Kārakas) involved are:
- Target role ({decomposition['target_karaka']}): {top_result['answer']}
"""

        for karaka, entity in decomposition.get('constraints', {}).items():
            context += f"- {karaka}: {entity}\n"

        prompt = f"""{context}

Provide a clear, natural language answer to the question. Include the Kāraka roles in parentheses for clarity.

Answer:"""

        answer_text = self.nim.call_nemotron(prompt, max_tokens=150)

        return {
            "answer": answer_text.strip(),
            "sources": [
                {
                    "sentence_id": r['sentence_id'],
                    "text": r['source_sentence'],
                    "confidence": r['confidence']
                }
                for r in graph_results
            ],
            "confidence": top_result['confidence'],
            "karakas": decomposition
        }

answer_synthesizer = AnswerSynthesizer()
```

### Step 7.4: Implement `lambda/query_handler.py`
```python
import json
from src.query.decomposer import query_decomposer
from src.query.cypher_generator import cypher_generator
from src.query.answer_synthesizer import answer_synthesizer
from src.graph.neo4j_client import neo4j_client

def handler(event, context):
    """
    Handle user queries

    POST /query
    Body: {
        "question": "Who gave bow to Lakshmana?",
        "min_confidence": 0.8
    }
    """
    try:
        body = json.loads(event['body'])
        question = body['question']
        min_confidence = body.get('min_confidence', 0.8)

        # Step 1: Decompose query
        decomposition = query_decomposer.decompose(question)

        # Step 2: Generate Cypher query
        cypher_query = cypher_generator.generate(decomposition, min_confidence)

        # Step 3: Execute graph query
        graph_results = neo4j_client.execute_query(cypher_query)

        # Step 4: Synthesize answer
        answer = answer_synthesizer.synthesize(question, graph_results, decomposition)

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(answer)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({"error": str(e)})
        }

def graph_handler(event, context):
    """
    Get graph data for visualization

    GET /graph
    """
    try:
        graph_data = neo4j_client.get_graph_for_visualization()

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(graph_data)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({"error": str(e)})
        }
```

---

## Phase 8: Frontend Implementation

### Step 8.1: Implement `frontend/src/utils/api.js`
```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  async uploadDocument(file) {
    const content = await file.text();
    const base64Content = btoa(content);

    const response = await fetch(`${API_BASE_URL}/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        document_name: file.name,
        content: base64Content
      })
    });

    return response.json();
  },

  async getIngestionStatus(jobId) {
    const response = await fetch(`${API_BASE_URL}/ingest/status/${jobId}`);
    return response.json();
  },

  async query(question, minConfidence = 0.8) {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, min_confidence: minConfidence })
    });

    return response.json();
  },

  async getGraph() {
    const response = await fetch(`${API_BASE_URL}/graph`);
    return response.json();
  }
};
```

### Step 8.2: Implement `frontend/src/components/DocumentUpload.jsx`
```jsx
import React, { useState } from 'react';
import { Upload } from 'lucide-react';
import { api } from '../utils/api';

export function DocumentUpload({ onUploadComplete }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const result = await api.uploadDocument(file);
      onUploadComplete(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
      <Upload className="mx-auto h-12 w-12 text-gray-400" />
      <p className="mt-2 text-sm text-gray-600">
        Upload your document to build the Kāraka graph
      </p>
      <input
        type="file"
        accept=".txt"
        onChange={handleFileUpload}
        disabled={uploading}
        className="mt-4"
      />
      {uploading && <p className="mt-2 text-blue-600">Uploading...</p>}
      {error && <p className="mt-2 text-red-600">{error}</p>}
    </div>
  );
}
```

### Step 8.3: Implement `frontend/src/components/ProgressTracker.jsx`
```jsx
import React, { useEffect, useState } from 'react';
import { api } from '../utils/api';

export function ProgressTracker({ jobId, onComplete }) {
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    if (!jobId) return;

    const interval = setInterval(async () => {
      const status = await api.getIngestionStatus(jobId);
      setProgress(status);

      if (status.status === 'completed') {
        clearInterval(interval);
        onComplete();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId]);

  if (!progress) return null;

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Processing Document</h3>
      <div className="w-full bg-gray-200 rounded-full h-4">
        <div
          className="bg-blue-600 h-4 rounded-full transition-all"
          style={{ width: `${progress.percentage}%` }}
        />
      </div>
      <p className="mt-2 text-sm text-gray-600">
        {progress.progress} / {progress.total} sentences processed ({progress.percentage}%)
      </p>
    </div>
  );
}
```

### Step 8.4: Implement `frontend/src/components/QueryInterface.jsx`
```jsx
import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { api } from '../utils/api';

export function QueryInterface() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);

  const exampleQueries = [
    "Who gave bow to Lakshmana?",
    "What weapons did Ravana use?",
    "Where did Hanuman find Sita?"
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    try {
      const result = await api.query(question);
      setAnswer(result);
    } catch (err) {
      setAnswer({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Ask a Question</h3>

      <form onSubmit={handleSubmit} className="mb-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Who gave bow to Lakshmana?"
            className="flex-1 px-4 py-2 border rounded-lg"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            <Search className="h-5 w-5" />
          </button>
        </div>
      </form>

      <div className="mb-4">
        <p className="text-sm text-gray-600 mb-2">Try these examples:</p>
        {exampleQueries.map((q, idx) => (
          <button
            key={idx}
            onClick={() => setQuestion(q)}
            className="text-sm text-blue-600 hover:underline block"
          >
            {q}
          </button>
        ))}
      </div>

      {loading && <p className="text-gray-600">Searching...</p>}

      {answer && !answer.error && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <p className="font-semibold mb-2">Answer:</p>
          <p className="mb-4">{answer.answer}</p>

          {answer.sources && answer.sources.length > 0 && (
            <div className="text-sm">
              <p className="font-semibold mb-2">Sources:</p>
              {answer.sources.map((source, idx) => (
                <div key={idx} className="mb-2 p-2 bg-white rounded">
                  <p className="italic">"{source.text}"</p>
                  <p className="text-gray-600 mt-1">
                    Confidence: {(source.confidence * 100).toFixed(1)}%
                  </p>
                </div>
              ))}
            </div>
          )}

          {answer.karakas && (
            <div className="mt-4 text-sm">
              <p className="font-semibold mb-2">Kārakas Identified:</p>
              <pre className="bg-gray-100 p-2 rounded">
                {JSON.stringify(answer.karakas, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {answer && answer.error && (
        <p className="text-red-600 mt-4">{answer.error}</p>
      )}
    </div>
  );
}
```

### Step 8.5: Implement `frontend/src/components/GraphVisualization.jsx`
```jsx
import React, { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import { api } from '../utils/api';

export function GraphVisualization() {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const [loading, setLoading] = useState(false);

  const loadGraph = async () => {
    setLoading(true);
    try {
      const graphData = await api.getGraph();
      renderGraph(graphData);
    } catch (err) {
      console.error('Failed to load graph:', err);
    } finally {
      setLoading(false);
    }
  };

  const renderGraph = (graphData) => {
    if (!containerRef.current) return;

    const nodes = graphData.nodes.map(node => ({
      id: node.id,
      label: node.label,
      color: node.type === 'Entity' ? '#3b82f6' : '#10b981',
      shape: node.type === 'Entity' ? 'circle' : 'box'
    }));

    const edges = graphData.edges.map(edge => ({
      from: edge.from,
      to: edge.to,
      label: edge.label,
      arrows: 'to',
      color: getKarakaColor(edge.label)
    }));

    const data = { nodes, edges };
    const options = {
      physics: {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -2000,
          springLength: 200
        }
      },
      nodes: {
        font: { size: 14 }
      },
      edges: {
        font: { size: 12 },
        smooth: { type: 'cubicBezier' }
      }
    };

    if (networkRef.current) {
      networkRef.current.destroy();
    }

    networkRef.current = new Network(containerRef.current, data, options);
  };

  const getKarakaColor = (karaka) => {
    const colors = {
      'KARTA': '#ef4444',
      'KARMA': '#3b82f6',
      'KARANA': '#10b981',
      'SAMPRADANA': '#f59e0b',
      'ADHIKARANA': '#8b5cf6',
      'APADANA': '#ec4899'
    };
    return colors[karaka] || '#6b7280';
  };

  ```jsx
  useEffect(() => {
    loadGraph();

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
      }
    };
  }, []);

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Kāraka Knowledge Graph</h3>
        <button
          onClick={loadGraph}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 text-sm"
        >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      <div className="mb-4 text-sm">
        <p className="font-semibold mb-2">Legend:</p>
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-blue-500 rounded-full"></div>
            <span>Entities</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-500 rounded"></div>
            <span>Actions</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-4 mt-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 bg-red-500"></div>
            <span>KARTA (Agent)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 bg-blue-500"></div>
            <span>KARMA (Patient)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 bg-green-500"></div>
            <span>KARANA (Instrument)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 bg-yellow-500"></div>
            <span>SAMPRADANA (Recipient)</span>
          </div>
        </div>
      </div>

      <div
        ref={containerRef}
        className="border border-gray-300 rounded-lg"
        style={{ height: '600px' }}
      />
    </div>
  );
}
```

### Step 8.6: Implement `frontend/src/App.jsx`
```jsx
import React, { useState } from 'react';
import { DocumentUpload } from './components/DocumentUpload';
import { ProgressTracker } from './components/ProgressTracker';
import { QueryInterface } from './components/QueryInterface';
import { GraphVisualization } from './components/GraphVisualization';

function App() {
  const [jobId, setJobId] = useState(null);
  const [ingestionComplete, setIngestionComplete] = useState(false);
  const [showGraph, setShowGraph] = useState(false);

  const handleUploadComplete = (result) => {
    setJobId(result.job_id);
    setIngestionComplete(false);
  };

  const handleIngestionComplete = () => {
    setIngestionComplete(true);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Kāraka Graph RAG
          </h1>
          <p className="text-gray-600 mt-1">
            Semantic Role-Aware Retrieval using Pāṇinian Linguistics
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column */}
          <div className="space-y-8">
            <section>
              <h2 className="text-xl font-semibold mb-4">1. Upload Document</h2>
              <DocumentUpload onUploadComplete={handleUploadComplete} />
            </section>

            {jobId && !ingestionComplete && (
              <section>
                <h2 className="text-xl font-semibold mb-4">2. Processing</h2>
                <ProgressTracker
                  jobId={jobId}
                  onComplete={handleIngestionComplete}
                />
              </section>
            )}

            {ingestionComplete && (
              <section>
                <h2 className="text-xl font-semibold mb-4">3. Query</h2>
                <QueryInterface />
              </section>
            )}
          </div>

          {/* Right Column */}
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Visualization</h2>
              <button
                onClick={() => setShowGraph(!showGraph)}
                className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 text-sm"
              >
                {showGraph ? 'Hide' : 'Show'} Graph
              </button>
            </div>

            {showGraph && ingestionComplete && <GraphVisualization />}

            {!ingestionComplete && (
              <div className="bg-white p-8 rounded-lg shadow text-center text-gray-500">
                Upload and process a document to view the knowledge graph
              </div>
            )}
          </div>
        </div>

        {/* Info Section */}
        <section className="mt-8 bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">About This System</h3>
          <div className="prose max-w-none">
            <p className="text-gray-700">
              This system uses <strong>Pāṇinian Kāraka semantics</strong> - a 2,500-year-old
              linguistic framework - to build a knowledge graph that explicitly models semantic
              roles in text.
            </p>
            <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div>
                <strong className="text-red-600">KARTA</strong>
                <p className="text-gray-600">Agent (who does)</p>
              </div>
              <div>
                <strong className="text-blue-600">KARMA</strong>
                <p className="text-gray-600">Patient (what is done)</p>
              </div>
              <div>
                <strong className="text-green-600">KARANA</strong>
                <p className="text-gray-600">Instrument (with what)</p>
              </div>
              <div>
                <strong className="text-yellow-600">SAMPRADANA</strong>
                <p className="text-gray-600">Recipient (to whom)</p>
              </div>
              <div>
                <strong className="text-purple-600">ADHIKARANA</strong>
                <p className="text-gray-600">Location (where)</p>
              </div>
              <div>
                <strong className="text-pink-600">APADANA</strong>
                <p className="text-gray-600">Source (from where)</p>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
```

---

## Phase 9: Testing & Validation

### Step 9.1: Create `tests/test_e2e.py`
```python
import pytest
from src.ingestion.graph_builder import graph_builder
from src.query.decomposer import query_decomposer
from src.query.cypher_generator import cypher_generator
from src.graph.neo4j_client import neo4j_client

class TestEndToEnd:
    """End-to-end integration tests"""

    def setup_method(self):
        """Clear database before each test"""
        with neo4j_client.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def test_simple_ingestion_and_query(self):
        """Test basic ingestion and querying"""
        # Ingest test sentence
        sentence = "Rama gave a bow to Lakshmana."
        result = graph_builder.process_sentence(sentence, 0)

        assert result["status"] == "success"
        assert "KARTA" in result["karakas"]
        assert "KARMA" in result["karakas"]
        assert "SAMPRADANA" in result["karakas"]

        # Query
        question = "Who gave bow to Lakshmana?"
        decomposition = query_decomposer.decompose(question)
        cypher = cypher_generator.generate(decomposition)
        results = neo4j_client.execute_query(cypher)

        assert len(results) > 0
        assert "Rama" in results[0]["answer"]

    def test_entity_resolution(self):
        """Test entity resolution across multiple sentences"""
        sentences = [
            "Rama was a prince.",
            "The prince went to the forest.",
            "He defeated many demons."
        ]

        for idx, sentence in enumerate(sentences):
            graph_builder.process_sentence(sentence, idx)

        # Verify all refer to same entity
        with neo4j_client.driver.session() as session:
            result = session.run("""
                MATCH (e:Entity {canonical_name: 'Rama'})
                RETURN e.aliases as aliases
            """)
            record = result.single()
            assert record is not None
            assert len(record["aliases"]) > 1  # Should have multiple aliases

    def test_complex_multi_hop_query(self):
        """Test multi-constraint query"""
        sentences = [
            "Rama gave a golden bow to Lakshmana in the forest.",
            "Sita gave flowers to Rama.",
            "Hanuman gave a ring to Sita."
        ]

        for idx, sentence in enumerate(sentences):
            graph_builder.process_sentence(sentence, idx)

        # Query with multiple constraints
        question = "Who gave bow to Lakshmana?"
        decomposition = query_decomposer.decompose(question)
        cypher = cypher_generator.generate(decomposition)
        results = neo4j_client.execute_query(cypher)

        assert len(results) > 0
        assert "Rama" in results[0]["answer"]

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### Step 9.2: Create `tests/test_data/ramayana_sample.txt`
```text
Rama was the eldest son of King Dasharatha. He was born in Ayodhya.
The prince was known for his virtue and strength. Rama married Sita in a grand ceremony.
King Dasharatha gave the kingdom to Rama. However, the king later exiled Rama to the forest.
Rama went to the forest with Sita and Lakshmana. His brother Lakshmana was loyal and brave.
In the forest, Rama defeated many demons with his mighty bow. He used divine weapons given by sages.
The demon king Ravana kidnapped Sita from the forest. Ravana took Sita to Lanka.
Hanuman found Sita in Lanka. The monkey warrior gave Rama's ring to Sita as proof.
Rama built a bridge to Lanka with the help of the monkey army. Hanuman led the construction.
In the great battle, Rama killed Ravana with a divine arrow. The arrow pierced Ravana's heart.
Rama returned to Ayodhya with Sita and Lakshmana. The people welcomed their king with joy.
```

---

## Phase 10: Deployment Preparation

### Step 10.1: Create `infrastructure/setup_api_gateway.py`
```python
import boto3
import json
import os
from dotenv import load_dotenv

load_dotenv()

apigateway = boto3.client('apigateway', region_name=os.getenv('AWS_REGION'))
lambda_client = boto3.client('lambda', region_name=os.getenv('AWS_REGION'))

def create_api_gateway():
    """Setup API Gateway with all endpoints"""

    # Create REST API
    api_response = apigateway.create_rest_api(
        name='karaka-rag-api',
        description='Kāraka Graph RAG API',
        endpointConfiguration={'types': ['REGIONAL']}
    )

    api_id = api_response['id']
    root_id = apigateway.get_resources(restApiId=api_id)['items'][0]['id']

    # Create /ingest resource
    ingest_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='ingest'
    )

    # POST /ingest
    apigateway.put_method(
        restApiId=api_id,
        resourceId=ingest_resource['id'],
        httpMethod='POST',
        authorizationType='NONE'
    )

    # Integration with Lambda
    lambda_arn = f"arn:aws:lambda:{os.getenv('AWS_REGION')}:{os.getenv('AWS_ACCOUNT_ID')}:function:karaka-rag-ingestion"

    apigateway.put_integration(
        restApiId=api_id,
        resourceId=ingest_resource['id'],
        httpMethod='POST',
        type='AWS_PROXY',
        integrationHttpMethod='POST',
        uri=f"arn:aws:apigateway:{os.getenv('AWS_REGION')}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
    )

    # Create /ingest/status/{job_id} resource
    status_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=ingest_resource['id'],
        pathPart='status'
    )

    job_id_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=status_resource['id'],
        pathPart='{job_id}'
    )

    # GET /ingest/status/{job_id}
    apigateway.put_method(
        restApiId=api_id,
        resourceId=job_id_resource['id'],
        httpMethod='GET',
        authorizationType='NONE'
    )

    apigateway.put_integration(
        restApiId=api_id,
        resourceId=job_id_resource['id'],
        httpMethod='GET',
        type='AWS_PROXY',
        integrationHttpMethod='POST',
        uri=f"arn:aws:apigateway:{os.getenv('AWS_REGION')}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
    )

    # Create /query resource
    query_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='query'
    )

    # POST /query
    apigateway.put_method(
        restApiId=api_id,
        resourceId=query_resource['id'],
        httpMethod='POST',
        authorizationType='NONE'
    )

    query_lambda_arn = f"arn:aws:lambda:{os.getenv('AWS_REGION')}:{os.getenv('AWS_ACCOUNT_ID')}:function:karaka-rag-query"

    apigateway.put_integration(
        restApiId=api_id,
        resourceId=query_resource['id'],
        httpMethod='POST',
        type='AWS_PROXY',
        integrationHttpMethod='POST',
        uri=f"arn:aws:apigateway:{os.getenv('AWS_REGION')}:lambda:path/2015-03-31/functions/{query_lambda_arn}/invocations"
    )

    # Create /graph resource
    graph_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='graph'
    )

    # GET /graph
    apigateway.put_method(
        restApiId=api_id,
        resourceId=graph_resource['id'],
        httpMethod='GET',
        authorizationType='NONE'
    )

    apigateway.put_integration(
        restApiId=api_id,
        resourceId=graph_resource['id'],
        httpMethod='GET',
        type='AWS_PROXY',
        integrationHttpMethod='POST',
        uri=f"arn:aws:apigateway:{os.getenv('AWS_REGION')}:lambda:path/2015-03-31/functions/{query_lambda_arn}/invocations"
    )

    # Enable CORS for all methods
    for resource_id in [ingest_resource['id'], query_resource['id'], graph_resource['id']]:
        apigateway.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE'
        )

        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            requestTemplates={'application/json': '{"statusCode": 200}'}
        )

        apigateway.put_integration_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            }
        )

    # Deploy API
    apigateway.create_deployment(
        restApiId=api_id,
        stageName='prod'
    )

    api_url = f"https://{api_id}.execute-api.{os.getenv('AWS_REGION')}.amazonaws.com/prod"

    print(f"✅ API Gateway created successfully!")
    print(f"📍 API URL: {api_url}")

    return api_url

if __name__ == '__main__':
    create_api_gateway()
```

### Step 10.2: Create `README.md`
```markdown
# Kāraka Graph RAG

🏆 **Ancient Linguistics Meets Modern AI**

A semantic role-aware Retrieval Augmented Generation (RAG) system based on Pāṇinian Kāraka semantics, solving the semantic role confusion problem in standard vector-based RAG systems.

## 🎯 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- AWS Account with $100 credits
- Docker (for local development)

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/yourusername/karaka-rag.git
cd karaka-rag

# 2. Setup environment
cp .env.example .env
# Edit .env with your credentials

# 3. Start local Neo4j
docker-compose up -d neo4j

# 4. Install Python dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 5. Install frontend dependencies
cd frontend && npm install && cd ..

# 6. Run local API
uvicorn src.api:app --reload --port 8000

# 7. Run frontend (in another terminal)
cd frontend && npm run dev
```

Visit http://localhost:5173

### AWS Deployment

```bash
# 1. Configure AWS credentials
aws configure

# 2. Update .env with your AWS settings

# 3. Deploy everything
chmod +x infrastructure/deploy.sh
./infrastructure/deploy.sh

# Follow prompts for Neo4j Aura setup
```

## 🎬 Demo Video

[Watch 3-minute demo](https://youtu.be/YOUR_VIDEO_ID)

## 🧠 Why Kārakas Beat Standard RAG

**Problem:** Vector embeddings cannot distinguish semantic roles.

```
"Rama gave bow to Lakshmana" ≈ "Lakshmana gave bow to Rama"  ❌ WRONG!
```

**Solution:** Explicit Kāraka modeling in knowledge graphs.

```
(Rama)-[KARTA]→(give)→[KARMA]→(bow)→[SAMPRADANA]→(Lakshmana)  ✅ CORRECT!
```

### Side-by-Side Comparison

| Query | Standard RAG | Kāraka Graph RAG |
|-------|--------------|------------------|
| "Who gave bow?" | Mixed results about bow and characters | **Rama** (KARTA extracted precisely) |
| "What did Rama give to Lakshmana?" | May confuse giver/receiver | **bow** (KARMA with correct constraints) |
| "Find battles where heroes used divine weapons" | Keyword match, low precision | **Multi-hop graph traversal** with KARANA filtering |

## 🏗️ Architecture

```
┌─────────────┐
│   User Query│
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│  Nemotron NIM (LLM)        │  ← Query Decomposition
│  "Who gave bow to X?"      │     Maps to Kāraka structure
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  Cypher Query Generator     │  ← Converts to graph query
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  Neo4j Graph Database       │  ← Structured traversal
│  Kāraka-typed edges         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  Nemotron NIM (LLM)        │  ← Answer Synthesis
│  Natural language output    │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  Answer + Citations         │
└─────────────────────────────┘
```

## 📊 Technical Stack

- ✅ **NVIDIA llama-3.1-nemotron-nano-8B** (NIM) - Query understanding & answer synthesis
- ✅ **NVIDIA Retrieval Embedding NIM** - Entity resolution
- ✅ **Amazon SageMaker AI** - Model hosting
- ✅ **Neo4j Graph Database** - Kāraka knowledge graph
- ✅ **AWS Lambda + API Gateway** - Serverless backend
- ✅ **spaCy** - Semantic Role Labeling
- ✅ **React + Vis.js** - Interactive visualization

## 🎯 Try These Queries

1. **Simple role extraction:**
   - "Who gave bow to Lakshmana?"
   - "What did Rama use in battle?"

2. **Multi-constraint queries:**
   - "Where did Hanuman find Sita?"
   - "Who defeated demons with divine weapons?"

3. **Complex multi-hop:**
   - "Find all events where someone gave something to Rama"
   - "What weapons were used by heroes in Lanka?"

## 📖 Pāṇinian Kārakas Explained

| Kāraka | Role | Example |
|--------|------|---------|
| **KARTA** | Agent (who does) | **Rama** gave bow |
| **KARMA** | Patient (what is done) | Rama gave **bow** |
| **KARANA** | Instrument (with what) | Rama fought **with sword** |
| **SAMPRADANA** | Recipient (to whom) | Rama gave bow **to Lakshmana** |
| **ADHIKARANA** | Location (where) | Rama fought **in Lanka** |
| **APADANA** | Source (from where) | Rama came **from Ayodhya** |

## 🔧 API Endpoints

### POST /ingest
Upload document for processing

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
  "status": "processing",
  "total_sentences": 500
}
```

### GET /ingest/status/:job_id
Check processing progress

### POST /query
Ask questions

**Request:**
```json
{
  "question": "Who gave bow to Lakshmana?",
  "min_confidence": 0.8
}
```

### GET /graph
Get visualization data

## 🚀 Potential Impact

### High-Stakes Domains

1. **Legal**: Contract analysis where "X owes Y" vs "Y owes X" is critical
2. **Medical**: Clinical notes where "administered to patient" vs "administered by patient" matters
3. **Intelligence**: Event extraction where agent/patient distinction is crucial
4. **Scientific**: Research paper analysis requiring precise relationship extraction

### Advantages Over Vector RAG

- ✅ **Verifiable**: Every assertion has source citation
- ✅ **Precise**: Semantic roles explicitly modeled
- ✅ **Auditable**: Confidence scores on all relationships
- ✅ **Queryable**: Complex multi-hop queries possible
- ✅ **Improvable**: Low-confidence assertions can be reviewed and corrected

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_e2e.py::TestEndToEnd::test_simple_ingestion_and_query -v
```

## 🗑️ Cleanup

```bash
# Destroy all AWS resources
chmod +x infrastructure/destroy.sh
./infrastructure/destroy.sh

# Don't forget to manually delete Neo4j Aura instance
```

## 📝 Future Work

- [ ] Add full Sanskrit translation layer for multilingual support
- [ ] Implement temporal reasoning (when did X happen?)
- [ ] Add causality detection (X caused Y)
- [ ] Support for nested/compound actions
- [ ] Fine-tune confidence scoring model
- [ ] Add user feedback loop for continuous improvement

## 🏅 Hackathon Compliance

This project fulfills all requirements:
- ✅ Uses NVIDIA llama-3.1-nemotron-nano-8B NIM
- ✅ Uses NVIDIA Retrieval Embedding NIM
- ✅ Deployed on Amazon SageMaker AI
- ✅ Complete working demo
- ✅ Public GitHub repository
- ✅ Video demonstration (< 3 minutes)
- ✅ Clear deployment instructions

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

- Pāṇini for the 2,500-year-old linguistic framework
- NVIDIA for NIM microservices
- AWS for cloud infrastructure
- Neo4j for graph database technology

---

**Built for AWS & NVIDIA Agentic AI Unleashed Hackathon 2025**
```

---

## Phase 11: Final Checklist

### Step 11.1: Create `DEPLOYMENT_CHECKLIST.md`
```markdown
# Pre-Submission Deployment Checklist

## Day 7 - Final Day Tasks

### Morning (4 hours)

- [ ] **Code Quality**
  - [ ] All Python files have docstrings
  - [ ] Remove debug print statements
  - [ ] Add error handling to all API endpoints
  - [ ] Run `black` and `flake8` for code formatting

- [ ] **Testing**
  - [ ] Run full test suite: `pytest tests/ -v`
  - [ ] All tests pass
  - [ ] Test with sample Ramayana document
  - [ ] Verify 5+ queries work correctly

- [ ] **Documentation**
  - [ ] README.md complete with examples
  - [ ] API.md has all endpoint documentation
  - [ ] ARCHITECTURE.md explains system design
  - [ ] .env.example has all required variables

### Afternoon (4 hours)

- [ ] **AWS Deployment**
  - [ ] Neo4j Aura instance created and accessible
  - [ ] NVIDIA NIMs deployed to SageMaker
  - [ ] Lambda functions deployed
  - [ ] API Gateway configured and tested
  - [ ] S3 buckets created
  - [ ] All endpoints return 200 OK

- [ ] **Frontend Deployment**
  - [ ] Update API_URL in frontend/.env
  - [ ] Build production bundle: `npm run build`
  - [ ] Deploy to S3 static hosting
  - [ ] Test frontend connects to backend

- [ ] **End-to-End Testing**
  - [ ] Upload test document via UI
  - [ ] Watch progress tracker update
  - [ ] Run 5 test queries
  - [ ] View graph visualization
  - [ ] Check all features work

### Evening (3 hours)

- [ ] **Demo Video**
  - [ ] Script written (< 3 min)
  - [ ] Screen recording with voiceover
  - [ ] Show problem → solution → demo → impact
  - [ ] Upload to YouTube (public/unlisted)
  - [ ] Add link to README

- [ ] **Repository Cleanup**
  - [ ] Remove sensitive data from commits
  - [ ] Add .gitignore for secrets
  - [ ] Push final code to GitHub (public repo)
  - [ ] Verify repo is accessible

- [ ] **DevPost Submission**
  - [ ] Create project on DevPost
  - [ ] Add title, tagline, description
  - [ ] Upload demo video link
  - [ ] Add GitHub repo link
  - [ ] Add screenshots
  - [ ] List technologies used
  - [ ] Submit before 2:00 PM ET deadline

### Final Hour

- [ ] **Verification**
  - [ ] Clone repo in fresh directory
  - [ ] Follow deployment instructions from README
  - [ ] Verify everything works
  - [ ] Test all API endpoints with curl
  - [ ] Check video plays correctly

- [ ] **Backup**
  - [ ] Export Neo4j database
  - [ ] Save `.env` file securely (not in repo!)
  - [ ] Take screenshots of working system
  - [ ] Save local copy of submission

## Emergency Fallbacks

If something breaks:

1. **NIMs fail**: Use NVIDIA API directly (build.nvidia.com)
2. **Neo4j inaccessible**: Use local Docker instance, show in video
3. **Lambda timeout**: Reduce document size, process in smaller batches
4. **Frontend doesn't deploy**: Submit backend only, show Postman/curl demo

## Success Criteria

- [ ] System ingests document successfully
- [ ] Queries return correct answers with citations
- [ ] Demo video clearly shows the value proposition
- [ ] GitHub repo has clear instructions
- [ ] DevPost submission complete before deadline

---

**Remember**: A working demo of Phase 1 (English SRL + Graph RAG) is better than a broken Phase 2 (Sanskrit translation). Focus on execution!
```

---

## Summary: What You've Built

### Core Innovation
A **Kāraka-based Graph RAG system** that uses Pāṇinian semantic roles to solve the semantic ambiguity problem in standard vector RAG.

### Key Differentiators
1. **Linguistically grounded**: Based on 2,500-year-old semantic theory
2. **Verifiable**: Every assertion has source citation + confidence score
3. **Precise**: Explicit semantic role modeling prevents agent/patient confusion
4. **Queryable**: Complex multi-hop graph queries that vector search cannot handle
5. **Auditable**: Low-confidence assertions can be reviewed and improved

### Technical Components Delivered

#### Backend (Python + AWS)
- ✅ SRL → Kāraka extraction pipeline
- ✅ Entity resolution using embeddings
- ✅ Neo4j graph construction
- ✅ Query decomposition with Nemotron
- ✅ Cypher query generation
- ✅ Answer synthesis with citations
- ✅ Lambda functions for serverless execution
- ✅ Progress tracking with S3

#### Frontend (React)
- ✅ Document upload interface
- ✅ Real-time progress tracker
- ✅ Query interface with examples
- ✅ Graph visualization with vis-network
- ✅ Results display with citations

#### Infrastructure (AWS)
- ✅ SageMaker endpoints for NVIDIA NIMs
- ✅ API Gateway REST API
- ✅ S3 for storage
- ✅ Neo4j Aura for graph database
- ✅ Deployment and cleanup scripts

### Files Created (Complete Project)

```
karaka-rag/
├── src/
│   ├── __init__.py
│   ├── config.py                      ✅ Configuration management
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── srl_parser.py             ✅ spaCy semantic role labeling
│   │   ├── karaka_mapper.py          ✅ SRL → Kāraka mapping
│   │   ├── entity_resolver.py        ✅ Entity resolution with embeddings
│   │   └── graph_builder.py          ✅ Neo4j graph construction
│   ├── query/
│   │   ├── __init__.py
│   │   ├── decomposer.py             ✅ Query → Kāraka decomposition
│   │   ├── cypher_generator.py       ✅ Graph query generation
│   │   └── answer_synthesizer.py     ✅ Natural language answers
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── neo4j_client.py           ✅ Database operations
│   │   └── schema.py                 ✅ Graph schema
│   └── utils/
│       ├── __init__.py
│       ├── nim_client.py             ✅ NVIDIA NIM API client
│       └── logger.py                 ✅ Logging utilities
├── lambda/
│   ├── handler.py                    ✅ Main Lambda handler
│   ├── ingestion_handler.py          ✅ Document processing
│   └── query_handler.py              ✅ Query execution
├── frontend/
│   ├── src/
│   │   ├── App.jsx                   ✅ Main application
│   │   ├── components/
│   │   │   ├── DocumentUpload.jsx    ✅ File upload
│   │   │   ├── QueryInterface.jsx    ✅ Question asking
│   │   │   ├── ProgressTracker.jsx   ✅ Ingestion progress
│   │   │   └── GraphVisualization.jsx ✅ Graph viewer
│   │   └── utils/
│   │       └── api.js                ✅ API client
│   ├── package.json                  ✅ Dependencies
│   └── vite.config.js                ✅ Build config
├── infrastructure/
│   ├── deploy.sh                     ✅ Full deployment script
│   ├── destroy.sh                    ✅ Cleanup script
│   ├── deploy_nims.py                ✅ SageMaker NIM deployment
│   └── setup_api_gateway.py          ✅ API Gateway configuration
├── tests/
│   ├── test_ingestion.py             ✅ Ingestion tests
│   ├── test_query.py                 ✅ Query tests
│   ├── test_e2e.py                   ✅ End-to-end tests
│   └── test_data/
│       └── ramayana_sample.txt       ✅ Test document
├── docs/
│   ├── ARCHITECTURE.md               ✅ System design
│   ├── API.md                        ✅ API documentation
│   ├── TASKS.md                      ✅ Task breakdown
│   └── DEPLOYMENT_CHECKLIST.md       ✅ Pre-submission checklist
├── docker-compose.yml                ✅ Local development
├── requirements.txt                  ✅ Python dependencies
├── .env.example                      ✅ Environment template
├── .gitignore                        ✅ Git configuration
└── README.md                         ✅ Complete documentation
```

---

## What You Didn't Miss

### Critical Success Factors Covered

1. **✅ Mandatory Tooling**
   - NVIDIA Nemotron NIM for LLM tasks
   - NVIDIA Embedding NIM for entity resolution
   - Deployed on Amazon SageMaker AI
   - All requirements satisfied

2. **✅ Judge-Friendly Design**
   - Pre-built demo database (no 30-min wait)
   - Clear deployment instructions
   - Working example queries
   - Health check endpoints
   - Comprehensive error messages

3. **✅ Winning Narrative**
   - Clear problem statement (semantic role confusion)
   - Novel solution (ancient linguistics + modern AI)
   - Concrete demonstrations (side-by-side comparison)
   - Real-world impact (legal, medical, intelligence)

4. **✅ Technical Excellence**
   - Clean architecture (separation of concerns)
   - Proper error handling
   - Confidence scoring
   - Source citations
   - Auditable system

5. **✅ Demo Quality**
   - 3-minute video script
   - Interactive visualization
   - Real-time progress tracking
   - Multiple example queries
   - Clear value proposition

### Optional Enhancements (If Time Permits)

**Low-hanging fruit (1-2 hours each):**
- Add query history in frontend
- Export graph as image
- Add "suggested questions" based on graph content
- Simple analytics dashboard (nodes count, relationships count)
- Dark mode toggle

**Nice-to-have (3-4 hours each):**
- Highlight matching nodes in graph when query succeeds
- Batch document upload
- Save/load query sessions
- Comparison mode (show vector RAG vs Kāraka RAG side-by-side)
- Mobile-responsive design improvements

**Don't build unless all core features work perfectly:**
- Sanskrit translation layer (save for post-hackathon)
- Advanced entity disambiguation
- Temporal reasoning
- Causality detection
- Fine-tuned confidence models

---

## Critical Reminders for Execution

### Day-by-Day Priorities

**Day 1-3: Get it working locally**
- Don't touch AWS yet
- Use local Neo4j
- Test with small documents
- Validate core pipeline

**Day 4-5: AWS integration**
- Deploy NIMs to SageMaker
- Test endpoints individually
- Don't deploy everything at once

**Day 6: Frontend + Integration**
- Connect frontend to backend
- End-to-end testing
- Fix critical bugs only

**Day 7: Polish + Submit**
- Video recording (most important!)
- Documentation cleanup
- DevPost submission
- Final testing

### Common Pitfalls to Avoid

❌ **Don't:**
- Try to build Sanskrit translation layer in 7 days
- Over-optimize performance before it works
- Add features that aren't in the demo video
- Deploy to AWS before local testing works
- Spend more than 2 hours debugging any single issue (pivot)

✅ **Do:**
- Use pre-built tools (spaCy, Neo4j, vis-network)
- Test incrementally (sentence → document → query)
- Have fallback plans for every component
- Focus on the demo video quality
- Submit early (don't wait until 1:59 PM)

### If You Get Stuck

**Problem: spaCy SRL not extracting roles**
- Fallback: Use simple dependency parsing
- Look for nsubj, obj, iobj patterns
- Don't need perfect accuracy for demo

**Problem: Entity resolution failing**
- Fallback: Skip resolution, use exact string matching
- Show it as "future work" in presentation
- Demo still works with simpler entity handling

**Problem: Nemotron NIM not responding**
- Fallback: Use rule-based query decomposition
- Parse interrogatives manually
- LLM for answer synthesis only (less critical)

**Problem: Lambda timeouts on large documents**
- Reduce document size (use 50 sentences max)
- Process in smaller batches
- Increase Lambda timeout to 15 minutes

**Problem: Neo4j connection issues**
- Fallback: Use local Docker Neo4j
- Show deployment capability in video
- Judges understand infrastructure issues

### The 80/20 Rule

**80% of your grade comes from:**
1. **Working demo** (40%) - System actually executes queries
2. **Clear narrative** (20%) - Problem → Solution → Impact
3. **Demo video quality** (20%) - Professional, under 3 minutes

**20% of your grade comes from:**
4. Code quality (10%)
5. Advanced features (5%)
6. Perfect deployment (5%)

**Focus your time accordingly.**

---

## Final Pre-Submission Script

### 1 Hour Before Deadline

```bash
# Final verification script
#!/bin/bash

echo "🔍 Pre-Submission Verification"

# 1. Check Git
echo "Checking Git status..."
git status
git remote -v
# Push if needed: git push origin main

# 2. Test API endpoints
echo "Testing API endpoints..."
API_URL="YOUR_API_GATEWAY_URL"

# Health check
curl -X GET "$API_URL/health" || echo "⚠️  Health check failed"

# Test query
curl -X POST "$API_URL/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Who gave bow to Lakshmana?"}' || echo "⚠️  Query failed"

# 3. Check GitHub repo
echo "Checking GitHub repo accessibility..."
# Open in browser to verify: https://github.com/yourusername/karaka-rag

# 4. Verify demo video
echo "Checking demo video..."
# Open YouTube link to verify it plays

# 5. DevPost checklist
echo "
📋 DevPost Submission Checklist:
[ ] Project created on DevPost
[ ] Title: 'Kāraka Graph RAG: Semantic Role-Aware Retrieval'
[ ] Tagline: 'Ancient Pāṇinian linguistics solving modern RAG problems'
[ ] Description: Complete with problem, solution, impact
[ ] Demo video link added
[ ] GitHub repo link added (public)
[ ] Technologies tagged: NVIDIA NIM, AWS SageMaker, Neo4j, React
[ ] Screenshots uploaded (3-5 images)
[ ] Submitted before deadline!

⏰ Current time: $(date)
⏰ Deadline: Monday, November 3, 2025 at 2:00 PM ET
"

echo "✅ Verification complete!"
```

---

## What Makes This Submission Win

### Judging Criteria Alignment

**Technological Implementation (25%)**
- ✅ Clean, modular architecture
- ✅ Proper use of NVIDIA NIMs (required)
- ✅ Sophisticated graph database design
- ✅ AWS best practices (Lambda, API Gateway, SageMaker)
- **Score: 8-9/10**

**Design (25%)**
- ✅ Intuitive user interface
- ✅ Real-time progress feedback
- ✅ Visual graph representation
- ✅ Clear error messages
- **Score: 7-8/10**

**Potential Impact (25%)**
- ✅ Solves real problem in high-stakes domains
- ✅ Clear use cases (legal, medical, intelligence)
- ✅ Demonstrable advantages over existing solutions
- ✅ Scalable architecture
- **Score: 8-9/10**

**Quality of Idea (25%)**
- ⭐ **Unique angle**: Ancient linguistics + Modern AI
- ⭐ **Memorable story**: 2,500-year-old grammar
- ⭐ **Technical sophistication**: Beyond standard RAG
- ⭐ **Clear differentiation**: Semantic roles > vectors
- **Score: 9-10/10**

**Estimated Overall: 8-9/10** → **Top 3 placement likely**

---

## Post-Hackathon: If You Win

### Prize Utilization Ideas

**Grand Prize ($10,000 + AWS credits + NVIDIA GPU):**
1. Hire annotators to create Pāṇinian training dataset
2. Fine-tune Sanskrit NMT model
3. Build production-ready version
4. Publish research paper
5. Launch as open-source project

**Future Roadmap:**
- **Month 1-2**: Build Sanskrit translation layer with real data
- **Month 3-4**: Benchmark against PropBank/FrameNet
- **Month 5-6**: Deploy to real use case (legal tech startup?)
- **Month 7-8**: Write academic paper for ACL/EMNLP
- **Month 9-12**: Launch as commercial product or open-source framework

---

## Conclusion

You now have a **complete, step-by-step blueprint** to build a winning hackathon submission:

✅ **Project structure** - Every file and directory
✅ **Requirements** - All dependencies defined
✅ **Design docs** - Architecture clearly explained
✅ **Task breakdown** - Granular implementation steps
✅ **Infrastructure** - Deploy and destroy scripts
✅ **Core implementation** - All Python modules coded
✅ **Document processing** - Upload and progress tracking
✅ **Query pipeline** - Full end-to-end flow
✅ **Frontend** - Complete React application
✅ **Testing** - Integration and E2E tests
✅ **Deployment** - AWS setup scripts
✅ **Documentation** - README, API docs, checklists

**Your job now:** Execute this plan methodically, day by day, testing as you go.

**Remember:** A polished demo of the English SRL + Graph RAG version beats an ambitious-but-broken Sanskrit version every time. Focus on execution, not perfection.

**Good luck! 🚀** You have everything you need to win.


