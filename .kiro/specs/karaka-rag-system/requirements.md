# Requirements Document

## Introduction

The Kāraka Graph RAG System is a semantic role-aware Retrieval Augmented Generation (RAG) system that uses Pāṇinian Kāraka semantics to build knowledge graphs with explicit semantic role modeling. This system solves the semantic role confusion problem in standard vector-based RAG systems by explicitly modeling agent-patient relationships and other semantic roles.

## Deployment Architecture

The system will be deployed on AWS infrastructure as required by the hackathon:

1. **NVIDIA NIMs on AWS SageMaker**: Deploy llama-3.1-nemotron-nano-8B-v1 and Retrieval Embedding NIM as SageMaker real-time inference endpoints
2. **AWS Lambda**: Serverless functions for ingestion and query processing that call SageMaker endpoints
3. **Amazon API Gateway**: REST API for frontend communication
4. **Neo4j Aura**: Managed graph database (cloud-hosted Neo4j)
5. **Amazon S3**: Storage for job status and document uploads
6. **React Frontend**: Hosted on S3 static website or locally

## System Execution Flow

1. User uploads document via frontend → API Gateway → Lambda (Ingestion)
2. Lambda processes document → Calls SageMaker NIM endpoints → Builds Neo4j graph
3. User submits query via frontend → API Gateway → Lambda (Query)
4. Lambda decomposes query using SageMaker Nemotron endpoint → Generates Cypher → Queries Neo4j
5. Lambda synthesizes answer using SageMaker Nemotron endpoint → Returns to frontend

## Glossary

- **System**: The Kāraka Graph RAG System
- **User**: A person interacting with the system through the web interface or API
- **Document**: A text file uploaded by the User for processing
- **Sentence**: A single sentence extracted from a Document
- **Kāraka**: A semantic role from Pāṇinian linguistics (KARTA, KARMA, KARANA, SAMPRADANA, ADHIKARANA, APADANA)
- **Entity**: A noun or noun phrase representing a person, place, or thing
- **Action** (Kriya): A verb representing an event or activity - **THE CENTER OF THE GRAPH**
- **Graph**: The Neo4j knowledge graph storing entities, actions, and their Kāraka relationships
- **Query**: A natural language question posed by the User
- **NIM**: NVIDIA Inference Microservice for LLM and embedding operations
- **SRL**: Semantic Role Labeling using spaCy dependency parsing
- **Confidence Score**: A numerical value between 0 and 1 indicating the reliability of an extracted relationship

## Core Architectural Principle: Kriya-Centric Graph

### ⚠️ CRITICAL: Relationship Direction

**The Kriya (Action/Verb) is the binding force that connects entities through Kāraka relationships.**

**CORRECT Graph Structure:**
```
(Action)-[KARTA]->(Entity)
(Action)-[KARMA]->(Entity)
(Action)-[KARANA]->(Entity)
(Action)-[SAMPRADANA]->(Entity)
(Action)-[APADANA]->(Entity)
(Action)-[ADHIKARANA]->(Entity)
```

**WRONG (Do NOT implement this way):**
```
(Entity)-[KARTA]->(Action)  ❌
```

### Why This Matters

1. **Linguistic Foundation**: In Pāṇinian grammar, the Kriya binds entities through their semantic roles
2. **No Direct Entity Links**: Entities are NEVER directly connected - only through actions
3. **Multi-Hop Reasoning**: Enables tracing relationships across multiple actions
4. **Temporal Reasoning**: Actions have sentence_id for chronological ordering
5. **Correct Semantics**: "The action 'gave' has agent Rama" not "Rama performs action gave"

### Example

**Sentence:** "Rama gave bow to Lakshmana"

**Graph Structure:**
```
(gave:Action)-[KARTA]->(Rama:Entity)
(gave:Action)-[KARMA]->(bow:Entity)
(gave:Action)-[SAMPRADANA]->(Lakshmana:Entity)
```

**Key Insight:** Rama and Lakshmana are NOT directly connected. They are only related through the action "gave" that binds them via their Kāraka roles.

### Multi-Hop Query Example

**Sentences:**
1. "Vishwamitra gave bow to Rama"
2. "Rama killed Ravana using the bow"

**Query:** "From where did Rama get the bow?"

**Traversal:**
```cypher
// Find action where Rama is SAMPRADANA (recipient) and bow is KARMA
MATCH (a:Action)-[:SAMPRADANA]->(rama:Entity {canonical_name: 'Rama'})
MATCH (a)-[:KARMA]->(bow:Entity {canonical_name: 'bow'})
// Get the KARTA (giver) of that action
MATCH (a)-[:KARTA]->(giver:Entity)
RETURN giver.canonical_name
```

**Answer:** "Vishwamitra"

This multi-hop reasoning is only possible because the Kriya is the center that binds entities.

## Requirements

*Requirements are organized in the order of system execution flow*

### Requirement 1: Infrastructure Setup

**User Story:** As a DevOps Engineer, I want to set up the AWS infrastructure so that the system has all necessary cloud resources before development begins.

#### Acceptance Criteria

1. WHEN the infrastructure setup begins, THE System SHALL create an S3 bucket for document storage and job tracking
2. WHEN setting up compute resources, THE System SHALL deploy llama-3.1-nemotron-nano-8B-v1 NIM to a SageMaker real-time inference endpoint
3. WHEN setting up embedding resources, THE System SHALL deploy NVIDIA Retrieval Embedding NIM to a SageMaker real-time inference endpoint
4. WHEN creating SageMaker endpoints, THE System SHALL use ml.g5.medium instance type
5. WHEN setting up the graph database, THE System SHALL create a Neo4j Aura instance with appropriate credentials
6. WHEN infrastructure setup completes, THE System SHALL output all endpoint URLs and connection strings for configuration

### Requirement 2: API Endpoints

**User Story:** As a Developer, I want well-defined API endpoints so that the frontend can communicate with the backend services.

#### Acceptance Criteria

1. WHEN the API Gateway is configured, THE System SHALL create a POST /ingest endpoint that accepts document uploads
2. WHEN the API Gateway is configured, THE System SHALL create a GET /ingest/status/:job_id endpoint for progress tracking
3. WHEN the API Gateway is configured, THE System SHALL create a POST /query endpoint for natural language questions
4. WHEN the API Gateway is configured, THE System SHALL create a GET /graph endpoint for visualization data
5. WHEN the API Gateway is configured, THE System SHALL enable CORS headers for cross-origin requests
6. WHEN API endpoints are created, THE System SHALL integrate each endpoint with corresponding Lambda functions
7. WHEN the System responds to API requests, THE System SHALL return appropriate HTTP status codes and error messages

### Requirement 3: Document Ingestion

**User Story:** As a User, I want to upload text documents so that the System can extract semantic relationships and build a knowledge graph.

#### Acceptance Criteria

1. WHEN the User uploads a Document, THE System SHALL accept text files in plain text format
2. WHEN the System receives a Document, THE System SHALL assign a unique document identifier
3. WHEN the System receives a Document, THE System SHALL split the Document into individual Sentences
4. WHEN the System processes Sentences, THE System SHALL extract semantic roles using spaCy SRL
5. WHEN the System extracts semantic roles, THE System SHALL map SRL roles to Kāraka types
6. WHEN the System identifies Entities, THE System SHALL call the SageMaker Embedding NIM endpoint to get embedding vectors
7. WHEN the System resolves Entities, THE System SHALL create Entity nodes in Neo4j with document source tracking
8. WHEN the System creates Graph nodes, THE System SHALL create Kāraka-typed relationships with Confidence Scores and document IDs

### Requirement 4: Progress Tracking

**User Story:** As a User, I want to see real-time progress of document processing so that I know when the system is ready for queries.

#### Acceptance Criteria

1. WHEN the System begins processing a Document, THE System SHALL generate a unique job identifier
2. WHEN the System processes Sentences, THE System SHALL update progress status in S3 after every 10 Sentences
3. WHEN the User requests job status via API, THE System SHALL retrieve status from S3 and return progress percentage
4. WHEN the System completes Document processing, THE System SHALL mark the job status as completed in S3
5. WHEN the System encounters processing errors, THE System SHALL record error details in the job status

### Requirement 5: Entity Resolution with Document Tracking

**User Story:** As a User, I want the system to recognize that "Rama", "the prince", and "he" refer to the same entity across multiple documents, and I want to disambiguate entities when the same name appears in different documents with different meanings.

#### Acceptance Criteria

1. WHEN the System encounters an Entity mention, THE System SHALL check if the Entity exists in Neo4j
2. WHEN the Entity is not found, THE System SHALL call the SageMaker Embedding NIM endpoint to compute an embedding vector
3. WHEN the System computes an embedding, THE System SHALL compare the embedding to existing canonical Entity embeddings in Neo4j
4. WHEN the similarity score exceeds the threshold of 0.85, THE System SHALL resolve the mention to the canonical Entity
5. WHEN the similarity score is below the threshold, THE System SHALL create a new canonical Entity entry in Neo4j
6. WHEN the System resolves an Entity, THE System SHALL add the mention as an alias and store the source document ID
7. WHEN the System creates Entity nodes, THE System SHALL store a list of document identifiers where that Entity appears
8. WHEN multiple documents contain the same Entity name with different contexts, THE System SHALL create separate Entity nodes with document-specific disambiguation

### Requirement 6: Query Processing

**User Story:** As a User, I want to ask natural language questions so that I can retrieve information from the knowledge graph with semantic role awareness.

#### Acceptance Criteria

1. WHEN the User submits a Query, THE System SHALL call the SageMaker Nemotron NIM endpoint to decompose the Query into target Kāraka and constraints
2. WHEN the System decomposes a Query, THE System SHALL identify which Kāraka role is being requested (KARTA, KARMA, etc.)
3. WHEN the System identifies Query constraints, THE System SHALL generate a Cypher query for Neo4j Graph traversal
4. WHEN the System generates a Cypher query, THE System SHALL filter results by minimum Confidence Score
5. WHEN the System executes the Cypher query against Neo4j, THE System SHALL retrieve matching Entities, Actions, and source Sentences
6. WHEN the System retrieves Graph results, THE System SHALL call the SageMaker Nemotron NIM endpoint to synthesize a natural language answer
7. WHEN the System generates an answer, THE System SHALL include source citations with Confidence Scores and document sources
8. WHERE the User specifies a document filter, THE System SHALL restrict query results to the specified document

### Requirement 7: Graph Visualization

**User Story:** As a User, I want to visualize the knowledge graph so that I can understand the semantic relationships extracted from documents.

#### Acceptance Criteria

1. WHEN the User requests Graph visualization, THE System SHALL query Neo4j to retrieve all Entity nodes and Action nodes
2. WHEN the System retrieves Graph nodes, THE System SHALL retrieve all Kāraka relationships between nodes from Neo4j
3. WHEN the System returns visualization data, THE System SHALL include node types, relationship labels, and document sources
4. WHEN the User views the Graph, THE System SHALL display Entities as circles and Actions as boxes
5. WHEN the User views relationships, THE System SHALL color-code edges by Kāraka type
6. WHEN the User views nodes, THE System SHALL display which documents contributed to each node

### Requirement 8: Multi-Document Management

**User Story:** As a User, I want to upload multiple documents and track which entities and relationships come from which documents, so that I can disambiguate entities with the same name across different stories or contexts.

#### Acceptance Criteria

1. WHEN the User uploads a Document, THE System SHALL assign a unique document identifier and store it in S3
2. WHEN the System creates Entity nodes in Neo4j, THE System SHALL store a list of document identifiers where that Entity appears
3. WHEN the System creates Action nodes in Neo4j, THE System SHALL store the source document identifier with the Action
4. WHEN the System creates Kāraka relationships in Neo4j, THE System SHALL store the source document identifier with the relationship
5. WHEN the User queries without document filter, THE System SHALL return results from all documents with document source annotations
6. WHERE the User specifies a document name filter in the query, THE System SHALL add Cypher WHERE clauses to filter by document ID
7. WHEN the User views the Graph, THE System SHALL display which documents contributed to each node and edge
8. WHEN multiple documents contain the same Entity name with different contexts, THE System SHALL create separate Entity nodes with document-specific disambiguation
9. WHEN the User asks "which documents mention Entity X", THE System SHALL query Neo4j for all document IDs associated with that Entity

### Requirement 9: Lambda Function Implementation

**User Story:** As a Developer, I want Lambda functions that orchestrate the ingestion and query workflows by calling SageMaker endpoints and Neo4j.

#### Acceptance Criteria

1. WHEN the ingestion Lambda function is invoked, THE System SHALL receive document data from API Gateway
2. WHEN processing documents, THE Lambda function SHALL call the SageMaker Embedding NIM endpoint using boto3 sagemaker-runtime client
3. WHEN decomposing queries, THE Lambda function SHALL call the SageMaker Nemotron NIM endpoint using boto3 sagemaker-runtime client
4. WHEN synthesizing answers, THE Lambda function SHALL call the SageMaker Nemotron NIM endpoint using boto3 sagemaker-runtime client
5. WHEN Lambda functions interact with Neo4j, THE System SHALL use the neo4j-driver Python library to execute Cypher queries
6. WHEN Lambda functions store job status, THE System SHALL write JSON files to S3 using boto3 s3 client
7. WHEN Lambda functions encounter errors, THE System SHALL log errors to CloudWatch and return appropriate error responses

### Requirement 10: Deployment Automation Scripts

**User Story:** As a DevOps Engineer, I want automated deployment scripts so that I can deploy and manage AWS infrastructure efficiently and provide clear deployment instructions for hackathon judges.

#### Acceptance Criteria

1. WHEN the deployment script for SageMaker runs, THE System SHALL create SageMaker endpoints for both Nemotron and Embedding NIMs
2. WHEN the deployment script for Lambda runs, THE System SHALL package Python dependencies and deploy Lambda functions with environment variables
3. WHEN the deployment script for API Gateway runs, THE System SHALL create REST API with all required endpoints and CORS configuration
4. WHEN the start script runs, THE System SHALL start stopped SageMaker endpoints to resume development
5. WHEN the stop script runs, THE System SHALL stop SageMaker endpoints without deleting them to save costs
6. WHEN the cleanup script runs, THE System SHALL delete all AWS resources including SageMaker endpoints, Lambda functions, API Gateway, and S3 buckets
7. WHEN deployment completes, THE System SHALL output API Gateway URL and SageMaker endpoint names for configuration
8. WHEN the deployment scripts are provided, THE System SHALL include a README with step-by-step deployment instructions for judges

### Requirement 11: Development Workflow and Testing

**User Story:** As a Developer, I want a clear development workflow so that I can build and test the system incrementally before deploying to AWS.

#### Acceptance Criteria

1. WHEN the Developer begins development, THE System SHALL provide a project structure with separate directories for source code, Lambda functions, infrastructure scripts, and frontend
2. WHEN the Developer implements core functionality, THE System SHALL allow testing of SRL parsing, Kāraka mapping, and entity resolution independently
3. WHEN the Developer tests ingestion pipeline, THE System SHALL process sample documents and verify graph creation in local Neo4j
4. WHEN the Developer tests query pipeline, THE System SHALL decompose queries and generate Cypher without requiring AWS deployment
5. WHEN the Developer completes local testing, THE System SHALL provide integration tests that verify end-to-end workflows
6. WHEN the Developer deploys to AWS, THE System SHALL provide smoke tests to verify SageMaker endpoints, Lambda functions, and API Gateway are working
7. WHEN the Developer encounters errors, THE System SHALL log detailed error messages to CloudWatch for debugging

### Requirement 12: Local Development Environment

**User Story:** As a Developer, I want to run the system locally so that I can develop and test without incurring AWS costs.

#### Acceptance Criteria

1. WHEN the Developer starts local development, THE System SHALL use Docker Compose to run Neo4j locally on port 7687
2. WHEN the Developer runs the API locally, THE System SHALL use FastAPI or Flask to simulate Lambda functions
3. WHEN testing locally without SageMaker, THE System SHALL use NVIDIA API (build.nvidia.com) as a fallback for NIM calls
4. WHEN the Developer runs the frontend locally, THE System SHALL connect to the local API endpoint on localhost:8000
5. WHEN the Developer tests locally, THE System SHALL use environment variables to switch between local and AWS configurations
6. WHEN the Developer installs dependencies, THE System SHALL provide requirements.txt for Python and package.json for frontend
