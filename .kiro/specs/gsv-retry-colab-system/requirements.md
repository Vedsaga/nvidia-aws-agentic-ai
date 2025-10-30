# Requirements Document

## Introduction

This specification defines the transformation of the existing Karaka RAG system into a robust, production-grade system using the GSV-Retry (Generate-Score-Verify-Retry) methodology. The system will implement fail-safe mechanisms including ensemble scoring, blind verification, cross-validation, and feedback loops to ensure high-quality knowledge graph construction and query processing in a Google Colab environment.

The core innovation is replacing simple single-pass LLM extraction with a multi-candidate generation approach where each extraction is independently scored, blindly verified against Pāṇinian rules, and cross-validated before acceptance. Failed extractions trigger feedback loops for self-correction.

**Hackathon Scope Constraint:** This system assumes clean text/PDF data only. The existing `load_and_refine_documents` function provides a clean list of sentences/lines. No unstructured data pre-processing is required, simplifying the implementation for rapid hackathon development.

## Requirements

### Requirement 1: Enhanced Model Infrastructure

**User Story:** As a system architect, I want to use more powerful and specialized models, so that the system can handle complex reasoning and semantic matching tasks effectively.

#### Acceptance Criteria

1. WHEN the system initializes THEN it SHALL load Llama 3.1 Nemotron Nano 8B V1 as the primary LLM for all reasoning and verification tasks
2. WHEN the system initializes THEN it SHALL load Llama-3.2-NV-EmbedQA-1B-v2 as the embedding model for semantic matching
3. WHEN the system initializes THEN it SHALL add FAISS vector store library (faiss-cpu) to dependencies
4. WHEN the system initializes THEN it SHALL initialize a NetworkX MultiDiGraph as the primary graph database
5. WHEN the system initializes THEN it SHALL initialize a FAISS vector store instance for document embeddings

### Requirement 2: Strict Graph Schema Definition

**User Story:** As a knowledge engineer, I want a strictly enforced graph schema, so that the knowledge graph maintains semantic consistency and enables reliable traversal.

#### Acceptance Criteria

1. WHEN the graph is initialized THEN it SHALL define exactly three node types: Kriyā, Entity, and Document
2. WHEN the graph is initialized THEN it SHALL define exactly ten relationship types: IS_KARTĀ_OF, HAS_KARMA, USES_KARANA, TARGETS_SAMPRADĀNA, FROM_APĀDĀNA, LOCATED_IN, OCCURS_AT, IS_SAME_AS, CAUSES, CITED_IN
3. WHEN mapping ADHIKARANA kāraka THEN the system SHALL distinguish between spatial location (LOCATED_IN) and temporal location (OCCURS_AT) using entity value heuristics
4. WHEN a node is added THEN the system SHALL enforce that it has a valid type attribute
5. WHEN an edge is added THEN the system SHALL enforce that it has a valid relation attribute from the defined set
6. WHEN schema validation fails THEN the system SHALL reject the operation and log the violation

### Requirement 3: Centralized Prompt Management

**User Story:** As a prompt engineer, I want all system prompts stored in a centralized configuration file, so that I can iterate on prompts without modifying code.

#### Acceptance Criteria

1. WHEN the system initializes THEN it SHALL load all prompts from a prompts.json file
2. WHEN prompts.json is loaded THEN it SHALL contain keys for: kriya_extraction_prompt, kriya_extraction_feedback_prompt, kriya_scoring_prompt, kriya_verification_prompt, query_decomposition_prompt, query_scoring_prompt, query_verification_prompt
3. WHEN the kriya_verification_prompt is loaded THEN it SHALL embed Pāṇinian Sūtra rules directly in the prompt text
4. WHEN the kriya_scoring_prompt is loaded THEN it SHALL instruct the LLM to return JSON with "reasoning" (string) and "score" (integer 1-100)
5. IF prompts.json does not exist THEN the system SHALL create it with default prompts

### Requirement 4: Document Embedding and Storage

**User Story:** As a data engineer, I want each document line embedded and stored with its text, so that the system can perform semantic retrieval and maintain ground truth citations.

#### Acceptance Criteria

1. WHEN a document is ingested THEN the system SHALL use the existing load_and_refine_documents function to get clean list_of_lines
2. WHEN processing each line THEN the system SHALL create a vector embedding using Llama-3.2 EmbedQA model
3. WHEN an embedding is created THEN the system SHALL store it in FAISS mapped to (doc_id, line_number)
4. WHEN an embedding is created THEN the system SHALL create a Document node in NetworkX with attributes: type="Document", doc_id, line_number, text
5. WHEN a Document node is created THEN it SHALL have a unique ID in format: {doc_id}_L{line_number}
6. WHEN load_and_refine_documents executes THEN the system SHALL assume input is clean text/PDF with no unstructured data pre-processing required

### Requirement 5: GSV-Retry Loop for Kriyā Extraction

**User Story:** As a quality assurance engineer, I want Kriyā extraction to use a multi-candidate generation and validation loop, so that only verified, high-quality extractions are ingested into the knowledge graph.

#### Acceptance Criteria

1. WHEN extracting Kriyās from a line THEN the system SHALL initialize a retry loop with max_retries=5 and feedback_prompt=""
2. WHEN the Generate phase executes THEN the system SHALL make 3 isolated LLM calls with base_extraction_prompt + feedback_prompt to produce [Candidate_A, Candidate_B, Candidate_C]
3. WHEN the Score phase executes THEN the system SHALL call get_robust_score() for each candidate
4. WHEN get_robust_score() executes THEN it SHALL make 3 isolated scoring calls per candidate (9 total calls)
5. WHEN a scoring call returns THEN the system SHALL validate the score is an integer between 1-100
6. IF a score is invalid THEN the system SHALL retry that specific scoring call until valid
7. WHEN 3 valid scores are obtained THEN get_robust_score() SHALL return their average as final_score
8. WHEN the Verify phase executes THEN the system SHALL call get_blind_verification() with only the 3 candidates (no scores)
9. WHEN get_blind_verification() executes THEN it SHALL use kriya_verification_prompt with embedded Pāṇinian rules
10. WHEN get_blind_verification() returns THEN it SHALL return either a candidate ID (e.g., "Candidate_B") or "ALL_INVALID"
11. WHEN cross-validation executes AND highest_score_candidate == verifier_choice THEN the system SHALL accept this as the "Golden Candidate" and break the loop
12. WHEN cross-validation executes AND highest_score_candidate != verifier_choice THEN the system SHALL set feedback_prompt = "Retry: The quantitative score and qualitative verifier disagreed. Please re-evaluate." and continue loop
13. WHEN verifier returns "ALL_INVALID" THEN the system SHALL set feedback_prompt = "Retry: All previous candidates were invalid. Verifier noted: [verifier's reasoning]. Please generate new, valid options." and continue loop
14. WHEN max_retries is exhausted AND no Golden Candidate found THEN the system SHALL log detailed failure diagnostics including all candidates, scores, verifier responses, and exact line reference (doc_id, line_number, text)
15. WHEN max_retries is exhausted THEN the system SHALL print failure message with cause and skip the line
16. WHEN max_retries is exhausted THEN the system SHALL accumulate failure statistics for final report

### Requirement 6: Verified Kriyā Graph Writing

**User Story:** As a knowledge graph builder, I want only Golden Candidate Kriyās written to the graph with proper schema compliance, so that the graph contains only verified, high-quality knowledge.

#### Acceptance Criteria

1. WHEN a Golden Candidate is accepted THEN the system SHALL extract verb and kārakas from the JSON
2. WHEN writing a Kriyā node THEN the system SHALL create it with attributes: type="Kriya", verb, doc_id, line_number
3. WHEN writing a Kriyā node THEN it SHALL have a unique ID in format: {doc_id}_L{line_number}_K{sequence}
4. WHEN writing Entity nodes THEN the system SHALL create them with attributes: type="Entity", canonical_name
5. WHEN writing kāraka relationships THEN the system SHALL create edges with relation attribute matching schema (IS_KARTĀ_OF, HAS_KARMA, etc.)
6. WHEN writing citation relationships THEN the system SHALL create CITED_IN edges from Kriyā to Document nodes
7. WHEN all writes complete THEN the system SHALL validate all nodes and edges comply with the strict schema

### Requirement 7: Post-Processing Entity Linking

**User Story:** As a semantic analyst, I want the system to resolve coreferences and metaphorical references after initial ingestion, so that entities are properly linked across the knowledge graph.

#### Acceptance Criteria

1. WHEN post-processing executes THEN the system SHALL query NetworkX for all pronoun entities (e.g., "He", "She", "It")
2. WHEN a pronoun is found THEN the system SHALL follow CITED_IN to get the Document node
3. WHEN the Document node is retrieved THEN the system SHALL query FAISS for semantically similar lines within a context window
4. WHEN similar lines are found THEN the system SHALL use a verifier LLM call to confirm the coreference link
5. WHEN coreference is confirmed THEN the system SHALL add an IS_SAME_AS edge between entities
6. WHEN processing metaphorical references (e.g., "King of Kings") THEN the system SHALL use RAG and GSV-Retry to find the target entity
7. WHEN a metaphorical link is confirmed THEN the system SHALL add an IS_SAME_AS edge
8. WHEN enriching entity attributes THEN the system SHALL query for all canonical entities
9. WHEN an entity is found THEN the system SHALL use RAG and verifier LLM to determine entity type (AI, Person, Location, etc.)
10. WHEN entity type is determined THEN the system SHALL add it as a node attribute: G.nodes[entity_id]['entity_type']
11. WHEN finding causal relationships THEN the system SHALL query for adjacent Kriyā nodes
12. WHEN adjacent Kriyās are found THEN the system SHALL use verifier LLM to determine if one CAUSES the other
13. WHEN causality is confirmed THEN the system SHALL add a CAUSES edge between Kriyā nodes

### Requirement 8: GSV-Retry Loop for Query Decomposition

**User Story:** As a query processor, I want query decomposition to use the same GSV-Retry validation as ingestion, so that query plans are as reliable as the knowledge graph itself.

#### Acceptance Criteria

1. WHEN a user query is received THEN the system SHALL apply GSV-Retry loop with max_retries=5
2. WHEN the Generate phase executes THEN the system SHALL make 3 isolated LLM calls to produce 3 multi-hop query plans
3. WHEN the Score phase executes THEN the system SHALL use 9-call ensemble scoring (3 scores per plan) with 1-100 validation
4. WHEN the Verify phase executes THEN the system SHALL make 1 blind call to select the most logical and executable plan
5. WHEN cross-validation executes AND highest_score_plan == verifier_choice THEN the system SHALL accept this as the "Golden Plan"
6. WHEN cross-validation fails THEN the system SHALL retry with feedback as in Requirement 5
7. WHEN max_retries is exhausted AND no Golden Plan found THEN the system SHALL log detailed failure diagnostics and return an error message to the user with the cause of failure

### Requirement 9: Graph-Based Query Execution

**User Story:** As a query executor, I want queries executed as graph traversals rather than LLM reasoning, so that answers are grounded in the knowledge graph and not hallucinated.

#### Acceptance Criteria

1. WHEN a Golden Plan is accepted THEN the system SHALL translate it into NetworkX graph traversal operations
2. WHEN translating the plan THEN the system SHALL map each step to specific edge relation filters
3. WHEN executing traversal THEN the system SHALL follow edges based on relation attributes (IS_KARTĀ_OF, HAS_KARMA, etc.)
4. WHEN traversal reaches target Kriyā nodes THEN the system SHALL follow CITED_IN relationships to Document nodes
5. WHEN Document nodes are reached THEN the system SHALL retrieve the text attribute as ground truth
6. WHEN a query requires multi-hop reasoning THEN the system SHALL continue traversing through connected Kriyā nodes following CAUSES, IS_SAME_AS, and kāraka relationships
7. WHEN multi-hop traversal executes THEN the system SHALL collect all relevant Document nodes along the reasoning path
8. WHEN all relevant nodes are collected THEN the system SHALL retrieve text from all connected Document nodes to provide complete narrative context
9. WHEN no matching path is found THEN the system SHALL return "No answer found in knowledge graph"
10. WHEN traversal completes THEN the system SHALL return all ground truth sentences from the reasoning path (may be 2-20+ sentences for complex multi-hop queries)

### Requirement 10: Grounded Answer Generation

**User Story:** As an end user, I want answers generated only from retrieved ground truth text, so that I can trust the answers are factual and not hallucinated.

#### Acceptance Criteria

1. WHEN ground truth sentences are retrieved THEN the system SHALL make one final isolated LLM call
2. WHEN making the final call THEN the prompt SHALL be: "Using only the following context, please answer this question."
3. WHEN making the final call THEN the context SHALL be all ground truth sentences from the reasoning path (ordered by their appearance in the narrative)
4. WHEN the context contains multiple sentences THEN the system SHALL preserve document order and line numbers to maintain narrative coherence
5. WHEN making the final call THEN the question SHALL be the user's original question
6. WHEN the LLM responds THEN the system SHALL return the answer with citations to all source documents in the reasoning path
7. WHEN no ground truth is found THEN the system SHALL return "I cannot answer this question based on the available documents" without attempting to generate an answer

### Requirement 11: Colab Environment Optimization

**User Story:** As a Colab user, I want the system optimized for notebook execution with clear cell boundaries and progress tracking, so that I can run and debug the system interactively.

#### Acceptance Criteria

1. WHEN the system is structured THEN it SHALL be organized into 12 distinct Colab cells
2. WHEN each cell executes THEN it SHALL print clear progress indicators with ✅ and ⚠️ symbols
3. WHEN long operations execute THEN the system SHALL print incremental progress updates
4. WHEN errors occur THEN the system SHALL print clear error messages with ❌ symbols
5. WHEN the system uses memory THEN it SHALL be optimized for Colab's RAM limits (12-16GB)
6. WHEN models are loaded THEN the system SHALL check if already loaded to avoid reloading
7. WHEN cells are re-run THEN the system SHALL handle state gracefully without requiring full restart

### Requirement 12: Robust Error Handling and Logging

**User Story:** As a system operator, I want comprehensive error handling and logging, so that I can diagnose issues and understand system behavior.

#### Acceptance Criteria

1. WHEN any LLM call fails THEN the system SHALL log the error with context (prompt, model, attempt number)
2. WHEN JSON parsing fails THEN the system SHALL log the raw response and attempt recovery
3. WHEN schema validation fails THEN the system SHALL log the violation details
4. WHEN GSV-Retry exhausts retries THEN the system SHALL log all candidates, scores, and verifier responses
5. WHEN graph operations fail THEN the system SHALL log the operation type and node/edge details
6. WHEN the system completes ingestion THEN it SHALL print comprehensive statistics (nodes, edges, success rate)
7. WHEN the system completes a query THEN it SHALL print the reasoning trace showing all traversal steps
