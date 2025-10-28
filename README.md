# Diagrams Index

## Essential Diagrams (7 files)

### 1. system-architecture.md
High-level system overview showing AWS components, data flow, and deployment architecture.

### 2. neo4j-schema.md ⭐ CRITICAL
**Core graph structure with all architectural principles:**
- Kriya-centric design (Kriya → Pada)
- Pada node reuse (one node, multiple Kāraka relationships)
- No direct pada connections
- Multi-hop reasoning examples
- Cypher query patterns with Sanskrit terminology
- Correct vs wrong patterns

### 3. ingestion-flow.md
Document processing pipeline:
- Sentence splitting
- SRL parsing
- Kāraka mapping
- Entity resolution
- Graph creation

### 4. query-flow.md
Query processing pipeline:
- Query decomposition
- Cypher generation
- Neo4j execution
- Answer synthesis
- No-answer handling (NULL when no match)

### 5. entity-resolution.md
Entity resolution algorithm:
- Check existing entities
- Embedding similarity
- Merge vs create new
- Alias tracking

### 6. srl-to-karaka-mapping.md
SRL to Kāraka role mapping:
- nsubj → KARTA
- obj → KARMA
- iobj → SAMPRADANA
- obl:with → KARANA
- etc.

### 7. complex-example-graph.md ⭐ COMPLETE EXAMPLE
**Full end-to-end example with 8 sentences:**
- Shows entity reuse (Rama: 1 node, 6 relationships)
- Demonstrates multi-hop reasoning
- Example queries with Cypher
- No-answer scenario
- Temporal ordering



## Quick Reference

**Graph Direction:** `(Kriya)-[KARAKA]->(Pada)` ✅  
**Pada Creation:** Once per unique entity, then reuse  
**No Direct Links:** Padas only connect through Kriyas  
**No Hallucination:** Return NULL when no answer exists  
**Source Tracking:** line_number, action_sequence, document_id  
**Sentence Text:** NOT stored in graph, retrieved from document when needed

**Sanskrit Terms:**
- Kriya (क्रिया) = Verb/Action (center of graph)
- Pada (पद) = Entity
- Karta (कर्ता) = Agent
- Karma (कर्म) = Patient/Object
- Karana (करण) = Instrument
- Sampradana (सम्प्रदान) = Recipient
- Adhikarana (अधिकरण) = Location
- Apadana (अपादान) = Source  

## Implementation Priority

1. Read **neo4j-schema.md** first (critical architecture)
2. Read **complex-example-graph.md** (complete example)
3. Read **ingestion-flow.md** and **query-flow.md** (pipelines)
4. Reference others as needed
