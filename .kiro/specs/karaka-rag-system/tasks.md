# Implementation Plan

## Phase 1: Project Setup

- [ ] 1. Initialize Project Structure
  - Create directory structure: `src/{ingestion,query,graph,utils}`, `lambda/`, `infrastructure/`, `data/`
  - Create `requirements.txt` with dependencies: spacy, neo4j, boto3, python-dotenv
  - Create `.env.example` with AWS, SageMaker, Neo4j configuration templates
  - Create `.gitignore` for Python and AWS artifacts
  - _Requirements: 11.1_

- [ ] 2. Create Configuration Module
  - Create `src/config.py` with Config class
  - Load environment variables for AWS region, S3 bucket, SageMaker endpoints, Neo4j credentials
  - Define Kāraka types list and confidence thresholds
  - _Requirements: 1.1, 1.2, 1.3, 1.5_

---

## Phase 2: Core Processing Components

- [ ] 3. Implement NIM Client
  - Create `src/utils/nim_client.py`
  - Implement `call_nemotron()` using boto3 sagemaker-runtime for text generation
  - Implement `get_embedding()` using boto3 sagemaker-runtime for embeddings
  - Add retry logic with exponential backoff for throttling
  - _Requirements: 9.2, 9.3, 9.4_

- [ ] 4. Implement Neo4j Client
  - Create `src/graph/neo4j_client.py`
  - Implement `create_entity(canonical_name, aliases, document_ids)` with MERGE
  - Implement `create_action(action_id, verb, sentence, sentence_id, document_id)`
  - Implement `create_karaka_relationship(entity, karaka_type, action, confidence, document_id)`
  - Implement `execute_query(cypher, params)` for arbitrary queries
  - Implement `get_graph_for_visualization()` returning nodes and edges
  - _Requirements: 3.7, 3.8, 7.1, 7.2, 8.2, 8.3, 8.4, 9.5_

- [ ] 5. Implement SRL Parser
  - Create `src/ingestion/srl_parser.py`
  - Load spaCy model `en_core_web_sm`
  - Implement `parse_sentence(sentence)` returning (verb, {role: entity})
  - Extract main verb from ROOT dependency
  - Extract semantic roles: nsubj, obj, iobj, obl (with preposition variants)
  - Implement `_get_noun_phrase()` to extract full noun phrases with modifiers
  - _Requirements: 3.4_

- [ ] 6. Implement Kāraka Mapper
  - Create `src/ingestion/karaka_mapper.py`
  - Define SRL_TO_KARAKA mapping dict: nsubj→KARTA, obj→KARMA, iobj→SAMPRADANA, obl:with→KARANA, obl:loc→ADHIKARANA, obl:from→APADANA
  - Implement `map_to_karakas(srl_roles)` converting SRL to Kāraka roles
  - _Requirements: 3.5_

- [ ] 7. Implement Entity Resolver
  - Create `src/ingestion/entity_resolver.py`
  - Implement `resolve_entity(entity_mention, document_id)` returning canonical name
  - Check entity cache for existing entities and aliases
  - Call NIM client to get embedding for new mentions
  - Calculate cosine similarity with existing entity embeddings
  - Merge entities if similarity > 0.85, otherwise create new entity
  - Track document IDs for each entity
  - _Requirements: 3.6, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 8.2, 8.8_

- [ ] 8. Implement Graph Builder
  - Create `src/ingestion/graph_builder.py`
  - Implement `process_sentence(sentence, sentence_id, document_id)` orchestrating full pipeline
  - Call SRL parser to extract verb and roles
  - Call Kāraka mapper to convert roles
  - Call entity resolver for each entity mention
  - Create action node in Neo4j with document_id
  - Create entity nodes with document_id tracking
  - Create Kāraka relationships with confidence and document_id
  - Return status dict with extracted Kārakas
  - Implement `process_document(sentences, document_id)` processing all sentences
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 8.1, 8.2, 8.3, 8.4_

---

## Phase 3: Query Pipeline

- [ ] 9. Implement Query Decomposer
  - Create `src/query/decomposer.py`
  - Implement `decompose(question)` using Nemotron NIM
  - Build prompt template for query analysis identifying target Kāraka, constraints, and verb
  - Parse LLM response to extract target_karaka, constraints dict, and verb
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 10. Implement Cypher Generator
  - Create `src/query/cypher_generator.py`
  - Implement `generate(decomposition, min_confidence, document_filter)` returning Cypher query
  - Build MATCH pattern for target Kāraka relationship
  - Add WHERE clauses for confidence threshold, verb matching, document filtering
  - Add constraint MATCH patterns for other Kārakas mentioned in query
  - Return entity, sentence, confidence, document_id
  - _Requirements: 6.3, 6.4, 6.8, 8.5, 8.6_

- [ ] 11. Implement Answer Synthesizer
  - Create `src/query/answer_synthesizer.py`
  - Implement `synthesize(question, graph_results, decomposition)` using Nemotron NIM
  - Build prompt template with question, graph results, and Kāraka roles
  - Generate natural language answer with Kāraka role annotations
  - Format sources with sentence text, confidence, document_id, document_name
  - Return answer dict with answer text, sources list, karakas, confidence
  - _Requirements: 6.6, 6.7, 8.5_

---

## Phase 4: Lambda Functions and API

- [ ] 12. Implement Ingestion Lambda Handler
  - Create `lambda/ingestion_handler.py`
  - Parse API Gateway event for document_name and content (base64)
  - Generate unique job_id and document_id
  - Split document into sentences
  - Initialize job status in S3 with total_sentences
  - Process sentences using graph_builder.process_document()
  - Update S3 progress every 10 sentences
  - Mark job as completed in S3 with statistics
  - Handle errors and update S3 status
  - Return job_id and status
  - _Requirements: 3.1, 3.2, 4.1, 4.2, 4.3, 4.4, 4.5, 9.1, 9.2, 9.5, 9.6, 9.7, 10.2_

- [ ] 13. Implement Query Lambda Handler
  - Create `lambda/query_handler.py`
  - Parse API Gateway event for question, min_confidence, document_filter
  - Call query decomposer to analyze question
  - Call Cypher generator to build query
  - Execute Cypher query against Neo4j
  - Call answer synthesizer to generate response
  - Return answer with sources and Kāraka annotations
  - Handle errors and return appropriate error responses
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 9.1, 9.3, 9.4, 9.5, 9.7_

- [ ] 14. Implement Status and Graph Lambda Handlers
  - Create `lambda/status_handler.py` to retrieve job status from S3
  - Parse job_id from API Gateway path parameters
  - Read job status JSON from S3
  - Return progress percentage and statistics
  - Create `lambda/graph_handler.py` to retrieve visualization data
  - Call neo4j_client.get_graph_for_visualization()
  - Return nodes and edges with document annotations
  - _Requirements: 4.3, 7.1, 7.2, 7.3, 7.6, 8.7, 9.1, 9.5, 9.6, 9.7_

---

## Phase 5: Infrastructure Deployment

- [ ] 15. Create Lambda Packaging Script
  - Create `infrastructure/package_lambda.sh`
  - Install requirements.txt to package/ directory
  - Copy src/ modules to package/
  - Create lambda.zip with all dependencies and handlers
  - _Requirements: 10.2_

- [ ] 16. Create SageMaker Deployment Script
  - Create `infrastructure/deploy_sagemaker.py`
  - Use boto3 to create SageMaker model for Nemotron NIM (llama-3.1-nemotron-nano-8b-v1)
  - Use boto3 to create SageMaker model for Embedding NIM (nvidia-retrieval-embedding)
  - Create endpoint configs with ml.g5.xlarge instance type
  - Create endpoints and wait for InService status
  - Output endpoint names for .env configuration
  - _Requirements: 1.2, 1.3, 1.4, 10.1_

- [ ] 17. Create API Gateway Deployment Script
  - Create `infrastructure/deploy_api_gateway.py`
  - Use boto3 to create REST API named 'karaka-rag-api'
  - Create resources and methods: POST /ingest, GET /ingest/status/{job_id}, POST /query, GET /graph
  - Enable CORS for all endpoints with appropriate headers
  - Integrate each endpoint with corresponding Lambda function
  - Deploy to 'prod' stage
  - Output API Gateway URL
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 10.3, 10.7_

- [ ] 18. Create Deployment Orchestration Script
  - Create `infrastructure/deploy.sh` bash script
  - Check for .env file and load environment variables
  - Create S3 bucket for job tracking
  - Run deploy_sagemaker.py and wait for endpoints
  - Package Lambda functions using package_lambda.sh
  - Deploy Lambda functions with environment variables and IAM roles
  - Run deploy_api_gateway.py to create API
  - Output deployment summary with API URL and endpoint names
  - _Requirements: 1.1, 1.5, 10.1, 10.2, 10.3, 10.7, 10.8_

---

## Phase 6: Frontend

- [ ] 19. Setup React Frontend Project
  - Create `frontend/` directory with Vite + React
  - Create `frontend/package.json` with dependencies: react, react-dom, axios, vis-network, lucide-react
  - Create `frontend/vite.config.js` with proxy configuration
  - Create `frontend/src/utils/api.js` with axios client and API methods
  - Configure API_GATEWAY_URL from environment
  - _Requirements: 11.1_

- [ ] 20. Build Document Upload Component
  - Create `frontend/src/components/DocumentUpload.jsx`
  - File input for text document selection
  - Upload button calling POST /ingest API
  - Display upload status and job_id
  - Show error messages if upload fails
  - _Requirements: 3.1, 4.2_

- [ ] 21. Build Progress Tracker Component
  - Create `frontend/src/components/ProgressTracker.jsx`
  - Poll GET /ingest/status/{job_id} every 2 seconds
  - Display progress bar with percentage
  - Show statistics: success, skipped, errors
  - Stop polling when status is completed or failed
  - _Requirements: 4.2, 4.3_

- [ ] 22. Build Query Interface Component
  - Create `frontend/src/components/QueryInterface.jsx`
  - Text input for natural language question
  - Submit button calling POST /query API
  - Display answer with Kāraka role annotations
  - Display sources with sentence text, confidence, document name
  - Show loading state during query processing
  - _Requirements: 6.1, 6.7_

- [ ] 23. Build Graph Visualization Component
  - Create `frontend/src/components/GraphVisualization.jsx`
  - Use vis-network library to render graph
  - Fetch data from GET /graph API
  - Display Entity nodes as circles, Action nodes as boxes
  - Color-code edges by Kāraka type: KARTA (red), KARMA (blue), SAMPRADANA (green), KARANA (yellow), ADHIKARANA (purple), APADANA (orange)
  - Show document source on node hover
  - Add Kāraka legend explaining colors
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.7_

- [ ] 24. Build Main App Component
  - Create `frontend/src/App.jsx`
  - Layout: left panel with upload, progress, query; right panel with graph
  - Integrate DocumentUpload, ProgressTracker, QueryInterface, GraphVisualization
  - Add header with project title and description
  - Add Kāraka information section explaining semantic roles
  - Refresh graph visualization after document upload completes
  - _Requirements: 11.1_

---

## Phase 7: Testing and Data

- [ ] 25. Create Test Data Files
  - Create `data/ramayana_sample.txt` with 20-30 sentences from Ramayana
  - Create `data/mahabharata_sample.txt` with 20-30 sentences from Mahabharata
  - Create `data/test_queries.json` with sample queries for each Kāraka type
  - _Requirements: 11.3_

- [ ] 26. End-to-End Testing
  - Upload ramayana_sample.txt and verify graph grows with entities and actions
  - Upload mahabharata_sample.txt and verify graph expands with new entities
  - Test entity resolution: verify same entities across documents are merged
  - Test queries from test_queries.json and verify correct answers
  - Test document filtering: query with document_filter parameter
  - Verify Kāraka relationships are correctly labeled and color-coded
  - Check CloudWatch logs for errors
  - _Requirements: 11.5, 11.6_

---

## Summary

**Total Tasks**: 26 tasks
**Focus**: Minimal viable implementation with core Kāraka RAG functionality

**Implementation Order**:
1. Project setup and configuration (Tasks 1-2)
2. Core processing components (Tasks 3-8)
3. Query pipeline (Tasks 9-11)
4. Lambda functions (Tasks 12-14)
5. Infrastructure deployment (Tasks 15-18)
6. Frontend (Tasks 19-24)
7. Testing (Tasks 25-26)

**Key Features**:
- ✅ Document ingestion with Kāraka extraction
- ✅ Multi-document entity resolution with embeddings
- ✅ Query decomposition and Cypher generation
- ✅ Graph visualization with color-coded Kāraka relationships
- ✅ Document tracking and filtering
- ✅ AWS deployment with SageMaker NIMs

**Out of Scope** (per steering rules):
- Documentation files (README, architecture docs)
- Demo video recording
- DevPost submission materials
