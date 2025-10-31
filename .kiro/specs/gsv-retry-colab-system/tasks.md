# Implementation Plan

- [x] 1. Update dependencies and model configuration
  - Add faiss-cpu to pip install command in CELL 1
  - Update model_id to "meta-llama/Llama-3.1-Nemotron-Nano-8B-Instruct-v1" in CELL 2
  - Update embedding_model to "nvidia/Llama-3.2-NV-EmbedQA-1B-v2" in CELL 2
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Create prompts.json configuration file
  - Create prompts.json with all required prompt keys
  - Use simplified verification prompt (hallucination, omission, role mismatch checks)
  - Enhance extraction prompt to include coreferences field and ADHIKARANA_SPATIAL/TEMPORAL distinction
  - Ensure scoring prompts enforce JSON output with "reasoning" and "score" (1-100)
  - _Requirements: 3.2, 3.3, 3.4_

- [x] 3. Implement GraphSchema class with strict validation
  - Define NODE_TYPES constant: {"Kriya", "Entity", "Document"}
  - Define EDGE_RELATIONS constant with 10 relations: HAS_KARTĀ (changed from IS_KARTĀ_OF), HAS_KARMA, USES_KARANA, TARGETS_SAMPRADĀNA, FROM_APĀDĀNA, LOCATED_IN, OCCURS_AT, IS_SAME_AS, CAUSES, CITED_IN
  - Implement validate_node() method
  - Implement validate_edge() method
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 4. Implement FAISSVectorStore wrapper class
  - Initialize FAISS index in __init__
  - Implement add(doc_id, embedding) method
  - Implement query_nearby(doc_id, k) method
  - Integrate with KarakaGraphV2
  - _Requirements: 1.5, 4.3_

- [x] 5. Implement GSVRetryEngine core class
  - Create GSVRetryEngine class with max_retries=5
  - Implement extract_with_retry() main loop with fast-path optimization (score ≥95 → immediate verify)
  - Implement _generate_candidates() for 3 isolated LLM calls
  - Implement _get_robust_score() with 3-call ensemble and validation
  - Implement _validate_score() with retry logic for 1-100 range
  - Implement _get_blind_verification() with simplified verification prompt
  - Implement _generate_feedback() for retry prompts
  - Implement _log_failure() with detailed diagnostics
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11, 5.12, 5.13, 5.14, 5.15, 5.16_

- [x] 6. Update KarakaGraphV2 with schema enforcement
  - Add GraphSchema instance to __init__
  - Add FAISSVectorStore instance to __init__
  - Implement add_document_node() with schema validation
  - Implement add_kriya_node() with schema validation
  - Implement add_entity_node() with schema validation
  - Override add_edge() with schema validation
  - Implement traverse() for multi-hop graph queries
  - Implement get_cited_documents() to retrieve Document node texts
  - _Requirements: 2.4, 2.5, 2.6, 4.4, 4.5, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [ ] 7. Implement IngestionPipeline class
  - Create IngestionPipeline class with graph, gsv_engine, embedding_model
  - Implement ingest_documents() orchestrator method
  - Implement _embed_and_store() for Document nodes and FAISS embeddings
  - Implement _write_to_graph() with Golden Candidate processing and coreference hints storage
  - Implement _map_karaka_to_relation() mapping ADHIKARANA_SPATIAL/TEMPORAL to LOCATED_IN/OCCURS_AT
  - Ensure ALL edges flow FROM Kriyā TO Entity (HAS_KARTĀ not IS_KARTĀ_OF)
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [ ] 8. Implement post-processing methods in IngestionPipeline
  - Implement _resolve_coreferences() with expanded pronoun list and extraction-time hints
  - Use in_edges() to traverse FROM Entity (pronoun) via HAS_KARTĀ relation
  - Implement _link_metaphorical_entities() using GSV-Retry
  - Implement _enrich_entity_types() using RAG and verifier LLM
  - Implement _detect_causal_relationships() using verifier LLM
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11, 7.12, 7.13_

- [ ] 9. Implement QueryPipeline class
  - Create QueryPipeline class with graph, gsv_engine, model, tokenizer
  - Implement answer_query() orchestrator method
  - Implement _execute_traversal() to translate plan to NetworkX operations
  - Implement _find_kriyas() with optimized entity-first traversal using in_edges()
  - Start from KARTA entity if available, traverse via HAS_KARTĀ relation (O(k) not O(N))
  - Implement _expand_causal_chain() to follow CAUSES edges
  - Implement _generate_answer() with grounded context and citations
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [ ] 10. Restructure Colab cells with new architecture
  - Update CELL 3 to initialize NetworkX, GraphSchema, and FAISS
  - Create CELL 4 for load_prompts() function
  - Update CELL 6 to use GSVRetryEngine class
  - Update CELL 7 to use KarakaGraphV2 class
  - Create CELL 8 for IngestionPipeline Step 1 (embed and store)
  - Create CELL 9 for IngestionPipeline Step 2 (GSV-Retry extraction)
  - Create CELL 10 for IngestionPipeline Step 3 (post-processing)
  - Create CELL 11 for QueryPipeline class
  - Update CELL 12 to use QueryPipeline.answer_query()
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

- [ ] 11. Add comprehensive progress indicators and error handling
  - Add ✅ success indicators after each major operation
  - Add ⚠️ warning indicators for retries and skipped lines
  - Add ❌ error indicators for failures
  - Add 📄 document processing indicators
  - Implement failure statistics accumulation
  - Print final ingestion report with success/failure counts
  - _Requirements: 11.2, 11.3, 11.4, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_

- [ ] 12. Wire everything together and test end-to-end
  - Execute CELL 1-5 to initialize system
  - Execute CELL 8-10 to ingest test documents
  - Verify graph statistics (nodes, edges, entity resolution)
  - Execute CELL 11-12 to run test queries
  - Verify grounded answers with citations
  - Verify multi-hop reasoning with CAUSES chain expansion
  - Test failure scenarios (invalid JSON, schema violations, GSV-Retry exhaustion)
  - _Requirements: All requirements integration testing_
