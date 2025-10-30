# Design Document

## Overview

The GSV-Retry Colab System transforms the existing Karaka RAG implementation into a production-grade knowledge graph system with robust validation mechanisms. The architecture follows a three-phase approach:

1. **Phase 0: System Setup** - Model loading, graph initialization, and prompt management
2. **Phase 1: Ingestion Pipeline** - Document embedding, GSV-Retry extraction, graph writing, and post-processing
3. **Phase 2: Query Pipeline** - Query decomposition, graph traversal, and grounded answer generation

The core innovation is the **GSV-Retry Loop**: a multi-candidate generation system where each extraction undergoes independent scoring (ensemble of 3 calls), blind verification (against Pāṇinian rules), and cross-validation before acceptance. Mismatches trigger feedback loops for self-correction.

**Hackathon Constraint:** Clean text/PDF input only via existing `load_and_refine_documents` function.

## Architecture

### High-Level System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        PHASE 0: SETUP                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Load Models  │  │ Init Graph & │  │Load Prompts  │         │
│  │ (Llama 3.1   │  │ FAISS Vector │  │(prompts.json)│         │
│  │  + EmbedQA)  │  │    Store     │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 1: INGESTION PIPELINE                   │
│                                                                 │
│  Step 1: Load & Embed Documents                                │
│  ┌────────────────────────────────────────────────────┐        │
│  │ load_and_refine_documents() → list_of_lines        │        │
│  │ For each line:                                     │        │
│  │   • Embed with EmbedQA → Store in FAISS           │        │
│  │   • Create Document node in NetworkX               │        │
│  └────────────────────────────────────────────────────┘        │
│                              ↓                                  │
│  Step 2: GSV-Retry Kriyā Extraction                            │
│  ┌────────────────────────────────────────────────────┐        │
│  │ For each line (max_retries=3):                    │        │
│  │   GENERATE: 3 candidates (isolated LLM calls)     │        │
│  │   SCORE: 9 calls (3 per candidate) → avg score   │        │
│  │   VERIFY: 1 blind call → best candidate ID       │        │
│  │   CROSS-VALIDATE:                                 │        │
│  │     ✓ Match → Golden Candidate → Break           │        │
│  │     ✗ Mismatch → Feedback → Retry                │        │
│  └────────────────────────────────────────────────────┘        │
│                              ↓                                  │
│  Step 3: Write to Graph                                        │
│  ┌────────────────────────────────────────────────────┐        │
│  │ Golden Candidate → NetworkX nodes & edges         │        │
│  │ Schema: Kriyā, Entity, Document nodes             │        │
│  │ Relations: IS_KARTĀ_OF, HAS_KARMA, CITED_IN, etc.│        │
│  └────────────────────────────────────────────────────┘        │
│                              ↓                                  │
│  Step 4: Post-Processing                                       │
│  ┌────────────────────────────────────────────────────┐        │
│  │ • Coreference resolution (pronouns → entities)    │        │
│  │ • Metaphorical linking (RAG + GSV-Retry)          │        │
│  │ • Entity type enrichment                          │        │
│  │ • Causal relationship detection                   │        │
│  └────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 2: QUERY PIPELINE                      │
│                                                                 │
│  Step 1: Decompose Query (GSV-Retry)                           │
│  ┌────────────────────────────────────────────────────┐        │
│  │ User Query → GSV-Retry Loop:                      │        │
│  │   GENERATE: 3 query plans                         │        │
│  │   SCORE: 9 calls → avg scores                     │        │
│  │   VERIFY: 1 blind call → best plan               │        │
│  │   CROSS-VALIDATE → Golden Plan                    │        │
│  └────────────────────────────────────────────────────┘        │
│                              ↓                                  │
│  Step 2: Execute Graph Traversal                               │
│  ┌────────────────────────────────────────────────────┐        │
│  │ Golden Plan → NetworkX traversal operations       │        │
│  │ Follow edges: IS_KARTĀ_OF, CAUSES, IS_SAME_AS    │        │
│  │ Multi-hop: Collect all Kriyā nodes in path       │        │
│  │ Follow CITED_IN → Document nodes                  │        │
│  │ Extract text attributes → Ground truth sentences  │        │
│  └────────────────────────────────────────────────────┘        │
│                              ↓                                  │
│  Step 3: Generate Grounded Answer                              │
│  ┌────────────────────────────────────────────────────┐        │
│  │ 1 isolated LLM call:                              │        │
│  │   Prompt: "Using only this context..."           │        │
│  │   Context: All ground truth sentences             │        │
│  │   Question: User's original query                 │        │
│  │ → Answer + Citations                              │        │
│  └────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Model Management Component

**Responsibility:** Load and manage LLM and embedding models with Colab optimization.

**Key Classes/Functions:**
- `load_models()` - Loads Llama 3.1 Nemotron Nano 8B V1 (4-bit quantized) and Llama-3.2-NV-EmbedQA-1B-v2
- `call_llm_isolated(system_prompt, user_prompt, max_tokens)` - Stateless LLM call (no conversation history)

**Interface:**
```python
def call_llm_isolated(
    system_prompt: str,
    user_prompt: str,
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    max_tokens: int = 300
) -> str:
    """Returns raw LLM response text"""
```

**Design Decisions:**
- 4-bit quantization for memory efficiency in Colab (12-16GB RAM)
- Global model caching to avoid reloading on cell re-runs
- Isolated calls prevent context contamination between extractions

### 2. Prompt Management Component

**Responsibility:** Centralize all system prompts in external configuration.

**Key Classes/Functions:**
- `load_prompts(filepath)` - Loads prompts from JSON file
- `get_prompt(key)` - Retrieves specific prompt by key

**Prompt Structure (prompts.json):**
```json
{
  "kriya_extraction_prompt": "You are a semantic role labeling expert...",
  "kriya_extraction_feedback_prompt": "Previous attempt failed because: {feedback}...",
  "kriya_scoring_prompt": "Score this extraction 1-100. Return JSON: {\"reasoning\": \"...\", \"score\": 85}",
  "kriya_verification_prompt": "Apply Pāṇinian rules: [embedded sūtras]. Select best candidate or return ALL_INVALID.",
  "query_decomposition_prompt": "Decompose query into multi-hop graph traversal plan...",
  "query_scoring_prompt": "Score this query plan 1-100...",
  "query_verification_prompt": "Verify query plan executability..."
}
```

**Design Decisions:**
- Pāṇinian Sūtra rules embedded directly in verification prompt (no external rule engine)
- Scoring prompts enforce JSON output with "reasoning" and "score" fields
- Feedback prompts use template strings for dynamic error injection

### 3. Graph Database Component

**Responsibility:** Manage NetworkX graph with strict schema enforcement.

**Key Classes:**
```python
class KarakaGraphV2:
    def __init__(self, embedding_model):
        self.graph = nx.MultiDiGraph()
        self.vector_store = FAISSVectorStore()
        self.entity_resolver = EntityResolver(embedding_model)
        self.schema = GraphSchema()  # NEW: Schema validator
    
    # Core operations
    def add_document_node(self, doc_id, line_number, text) -> str
    def add_kriya_node(self, verb, doc_id, line_number) -> str
    def add_entity_node(self, canonical_name) -> str
    def add_edge(self, source, target, relation, **attrs) -> None
    
    # Query operations
    def traverse(self, start_node, edge_filter, max_hops) -> List[str]
    def get_cited_documents(self, kriya_ids) -> List[Dict]
```

**Schema Definition:**
```python
class GraphSchema:
    NODE_TYPES = {"Kriya", "Entity", "Document"}
    EDGE_RELATIONS = {
        # All kāraka relations flow FROM Kriyā TO Entity (Pāṇinian standard)
        "HAS_KARTĀ", "HAS_KARMA", "USES_KARANA",
        "TARGETS_SAMPRADĀNA", "FROM_APĀDĀNA", 
        "LOCATED_IN",  # Spatial location (adhikarana - space)
        "OCCURS_AT",   # Temporal location (adhikarana - time)
        "IS_SAME_AS", "CAUSES", "CITED_IN"
    }
    
    def validate_node(self, node_id, attrs) -> bool
    def validate_edge(self, source, target, relation) -> bool
```

**Design Decisions:**
- MultiDiGraph allows multiple edges between nodes (e.g., multiple kāraka roles)
- Schema validation at write-time prevents malformed graph
- FAISS vector store integrated for RAG operations
- Entity resolver uses embedding similarity for coreference

### 4. GSV-Retry Engine Component

**Responsibility:** Implement the core Generate-Score-Verify-Retry loop with cross-validation.

**Key Classes/Functions:**
```python
class GSVRetryEngine:
    def __init__(self, model, tokenizer, prompts, max_retries=5):
        self.model = model
        self.tokenizer = tokenizer
        self.prompts = prompts
        self.max_retries = max_retries
    
    def extract_with_retry(self, text: str, extraction_type: str, line_ref: str = "") -> Optional[Dict]:
        """Main GSV-Retry loop for any extraction task"""
        feedback_prompt = ""
        failure_log = []
        
        for attempt in range(self.max_retries):
            # GENERATE: 3 candidates
            candidates = self._generate_candidates(text, feedback_prompt)
            
            # SCORE: Robust ensemble scoring
            scores = [self._get_robust_score(c) for c in candidates]
            
            # VERIFY: Blind verification
            verifier_choice = self._get_blind_verification(candidates)
            
            # CROSS-VALIDATE
            highest_idx = scores.index(max(scores))
            if candidates[highest_idx]["id"] == verifier_choice:
                return candidates[highest_idx]  # Golden Candidate
            
            # FEEDBACK for retry
            feedback_prompt = self._generate_feedback(
                candidates, scores, verifier_choice
            )
            failure_log.append({
                "attempt": attempt + 1,
                "candidates": [c["id"] for c in candidates],
                "scores": scores,
                "verifier_choice": verifier_choice,
                "feedback": feedback_prompt
            })
        
        # Failed after max_retries - log detailed failure
        error_msg = f"GSV-Retry exhausted at {line_ref}. Attempts: {self.max_retries}"
        self._log_failure(text, failure_log, error_msg)
        return None  # Failed after max_retries
    
    def _generate_candidates(self, text, feedback) -> List[Dict]:
        """3 isolated LLM calls"""
        candidates = []
        for i in range(3):
            prompt = self.prompts["base"] + feedback
            response = call_llm_isolated(prompt, text, self.model, self.tokenizer)
            candidates.append({"id": f"Candidate_{chr(65+i)}", "data": parse_json(response)})
        return candidates
    
    def _get_robust_score(self, candidate: Dict) -> float:
        """Ensemble of 3 scoring calls with validation"""
        scores = []
        for _ in range(3):
            response = call_llm_isolated(
                self.prompts["scoring"],
                json.dumps(candidate["data"]),
                self.model, self.tokenizer
            )
            score_data = parse_json(response)
            score = self._validate_score(score_data.get("score"))
            scores.append(score)
        return sum(scores) / len(scores)
    
    def _validate_score(self, score) -> int:
        """Retry until valid 1-100 score"""
        # Implementation with retry logic
        pass
    
    def _get_blind_verification(self, candidates: List[Dict]) -> str:
        """Single blind call with Pāṇinian rules"""
        prompt = self.prompts["verification"]
        context = json.dumps([c["data"] for c in candidates])
        response = call_llm_isolated(prompt, context, self.model, self.tokenizer)
        return parse_json(response).get("choice", "ALL_INVALID")
    
    def _generate_feedback(self, candidates, scores, verifier_choice) -> str:
        """Generate feedback for next iteration"""
        if verifier_choice == "ALL_INVALID":
            return "Retry: All candidates invalid. Verifier reasoning: ..."
        else:
            return "Retry: Score and verifier disagreed. Re-evaluate..."
```

**Fast-Path Optimization:**
```python
def extract_with_retry(self, text: str, extraction_type: str, line_ref: str = "") -> Optional[Dict]:
    """Main GSV-Retry loop with fast-path optimization"""
    feedback_prompt = ""
    failure_log = []
    
    for attempt in range(self.max_retries):
        # GENERATE: 3 candidates
        candidates = self._generate_candidates(text, feedback_prompt)
        
        # FAST-PATH: Score only first candidate initially
        first_score = self._get_robust_score(candidates[0])
        
        if first_score >= 95:
            # High confidence - verify immediately
            verifier_choice = self._get_blind_verification([candidates[0]])
            if verifier_choice == candidates[0]["id"]:
                return candidates[0]  # Fast-path success (4 LLM calls)
        
        # FULL-PATH: Score all candidates
        scores = [first_score] + [self._get_robust_score(c) for c in candidates[1:]]
        
        # VERIFY: Blind verification
        verifier_choice = self._get_blind_verification(candidates)
        
        # CROSS-VALIDATE
        highest_idx = scores.index(max(scores))
        if candidates[highest_idx]["id"] == verifier_choice:
            return candidates[highest_idx]  # Golden Candidate
        
        # FEEDBACK for retry
        feedback_prompt = self._generate_feedback(candidates, scores, verifier_choice)
        failure_log.append({"attempt": attempt + 1, "candidates": [c["id"] for c in candidates], 
                           "scores": scores, "verifier_choice": verifier_choice, "feedback": feedback_prompt})
    
    # Failed after max_retries
    self._log_failure(text, failure_log, f"GSV-Retry exhausted at {line_ref}")
    return None
```

**Design Decisions:**
- Fast-path optimization: High-confidence extractions (score ≥95) skip redundant scoring (4 calls vs 13)
- Generic engine works for both Kriyā extraction and query decomposition
- Feedback loop allows model to self-correct based on validation failures
- Blind verification prevents score bias in rule-based validation
- Max 5 retries balances quality vs. performance (45 LLM calls worst case per line, 4 calls best case)

### 5. Ingestion Pipeline Component

**Responsibility:** Orchestrate document loading, embedding, extraction, and post-processing.

**Key Classes/Functions:**
```python
class IngestionPipeline:
    def __init__(self, graph, gsv_engine, embedding_model):
        self.graph = graph
        self.gsv_engine = gsv_engine
        self.embedding_model = embedding_model
    
    def ingest_documents(self, docs_folder: str):
        """Main ingestion orchestrator"""
        # Step 1: Load and embed
        refined_docs = load_and_refine_documents(docs_folder)
        self._embed_and_store(refined_docs)
        
        # Step 2: Extract Kriyās with GSV-Retry
        for doc_id, lines in refined_docs.items():
            for line_num, text in enumerate(lines, 1):
                golden_candidate = self.gsv_engine.extract_with_retry(
                    text, extraction_type="kriya"
                )
                if golden_candidate:
                    self._write_to_graph(golden_candidate, doc_id, line_num, text)
        
        # Step 3: Post-processing
        self._resolve_coreferences()
        self._link_metaphorical_entities()
        self._enrich_entity_types()
        self._detect_causal_relationships()
    
    def _embed_and_store(self, refined_docs):
        """Create Document nodes and FAISS embeddings"""
        for doc_id, lines in refined_docs.items():
            for line_num, text in enumerate(lines, 1):
                # Create Document node
                doc_node_id = self.graph.add_document_node(doc_id, line_num, text)
                
                # Embed and store in FAISS
                embedding = self.embedding_model.encode(text)
                self.graph.vector_store.add(doc_node_id, embedding)
    
    def _write_to_graph(self, golden_candidate, doc_id, line_num, text):
        """Write verified Kriyā to graph with schema compliance"""
        verb = golden_candidate["data"]["verb"]
        karakas = golden_candidate["data"]["karakas"]
        coreferences = golden_candidate["data"].get("coreferences", [])
        
        # Create Kriyā node
        kriya_id = self.graph.add_kriya_node(verb, doc_id, line_num)
        
        # Create Entity nodes and kāraka edges (ALL edges flow FROM Kriyā)
        for karaka_type, entity_mention in karakas.items():
            canonical_entity = self.graph.entity_resolver.resolve(entity_mention)
            entity_id = self.graph.add_entity_node(canonical_entity)
            
            # Map kāraka type to edge relation
            relation = self._map_karaka_to_relation(karaka_type)
            # Kriyā is ALWAYS the source
            self.graph.add_edge(kriya_id, entity_id, relation)
        
        # Store coreference hints for post-processing
        for coref in coreferences:
            self.graph.nodes[self.graph.add_entity_node(coref["pronoun"])]["coref_context"] = coref["context"]
        
        # Add citation edge (also FROM Kriyā)
        doc_node_id = f"{doc_id}_L{line_num}"
        self.graph.add_edge(kriya_id, doc_node_id, "CITED_IN")
    
    def _map_karaka_to_relation(self, karaka_type: str) -> str:
        """Map Pāṇinian kāraka to graph relation (all flow FROM Kriyā)"""
        mapping = {
            "KARTA": "HAS_KARTĀ",
            "KARMA": "HAS_KARMA",
            "KARANA": "USES_KARANA",
            "SAMPRADANA": "TARGETS_SAMPRADĀNA",
            "APADANA": "FROM_APĀDĀNA",
            "ADHIKARANA_SPATIAL": "LOCATED_IN",
            "ADHIKARANA_TEMPORAL": "OCCURS_AT"
        }
        return mapping.get(karaka_type, "UNKNOWN")
```

**Post-Processing Methods:**
```python
def _resolve_coreferences(self):
    """Link pronouns to entities using RAG and extraction-time hints"""
    # Expanded pronoun list
    pronouns = ["he", "she", "it", "they", "him", "her", "his", "hers", "its", "their", 
                "theirs", "which", "that", "who", "whom"]
    
    pronoun_nodes = [n for n in self.graph.nodes() 
                     if self.graph.nodes[n].get("type") == "Entity" 
                     and self.graph.nodes[n].get("canonical_name", "").lower() in pronouns]
    
    for pronoun_id in pronoun_nodes:
        # Check if extraction provided coreference hint
        coref_context = self.graph.nodes[pronoun_id].get("coref_context")
        
        # Get context via incoming HAS_KARTĀ edges (note direction change)
        kriya_nodes = [e[0] for e in self.graph.in_edges(pronoun_id, data=True) 
                      if e[2].get("relation") in ["HAS_KARTĀ", "HAS_KARMA"]]
        doc_nodes = [e[1] for k in kriya_nodes for e in self.graph.out_edges(k, data=True) 
                    if e[2].get("relation") == "CITED_IN"]
        
        # Query FAISS for nearby context
        if doc_nodes:
            context_docs = self.graph.vector_store.query_nearby(doc_nodes[0], k=5)
            
            # Use verifier LLM to confirm link
            target_entity = self._verify_coreference(pronoun_id, context_docs, coref_context)
            if target_entity:
                self.graph.add_edge(pronoun_id, target_entity, "IS_SAME_AS")
```

**Design Decisions:**
- Reuses existing `load_and_refine_documents` for hackathon speed
- GSV-Retry engine handles all validation complexity
- Post-processing as separate pass allows graph-wide analysis
- Entity resolver uses embedding similarity (threshold 0.85) for fuzzy matching

### 6. Query Pipeline Component

**Responsibility:** Decompose queries, execute graph traversals, and generate grounded answers.

**Key Classes/Functions:**
```python
class QueryPipeline:
    def __init__(self, graph, gsv_engine, model, tokenizer):
        self.graph = graph
        self.gsv_engine = gsv_engine
        self.model = model
        self.tokenizer = tokenizer
    
    def answer_query(self, question: str) -> Dict:
        """Main query orchestrator"""
        # Step 1: Decompose with GSV-Retry
        golden_plan = self.gsv_engine.extract_with_retry(
            question, extraction_type="query"
        )
        
        if not golden_plan:
            return {"answer": "Failed to decompose query", "status": "ERROR"}
        
        # Step 2: Execute graph traversal
        ground_truth_docs = self._execute_traversal(golden_plan["data"])
        
        if not ground_truth_docs:
            return {"answer": "No answer found in knowledge graph", "status": "NO_MATCH"}
        
        # Step 3: Generate grounded answer
        return self._generate_answer(question, ground_truth_docs)
    
    def _execute_traversal(self, query_plan: Dict) -> List[Dict]:
        """Translate plan to NetworkX operations and execute"""
        all_doc_nodes = []
        
        for step in query_plan["steps"]:
            # Find matching Kriyā nodes
            kriya_nodes = self._find_kriyas(
                verb=step.get("verb"),
                karaka_constraints=step.get("karakas", {})
            )
            
            # Multi-hop: Follow CAUSES, IS_SAME_AS chains
            if step.get("follow_causes"):
                kriya_nodes = self._expand_causal_chain(kriya_nodes)
            
            # Get cited documents
            for kriya_id in kriya_nodes:
                doc_nodes = self.graph.get_neighbors(kriya_id, relation="CITED_IN")
                all_doc_nodes.extend(doc_nodes)
        
        # Retrieve text from unique Document nodes
        unique_docs = list(set(all_doc_nodes))
        return [
            {
                "doc_id": self.graph.nodes[d]["doc_id"],
                "line_number": self.graph.nodes[d]["line_number"],
                "text": self.graph.nodes[d]["text"]
            }
            for d in unique_docs
        ]
    
    def _find_kriyas(self, verb: Optional[str], karaka_constraints: Dict) -> List[str]:
        """Find Kriyā nodes matching verb and kāraka constraints (optimized traversal)"""
        # Start from entity if KARTA constraint exists (most selective)
        if "KARTA" in karaka_constraints and karaka_constraints["KARTA"]:
            canonical = self.graph.entity_resolver.resolve(karaka_constraints["KARTA"])
            # Get all Kriyā nodes where this entity is KARTĀ (traverse FROM entity)
            candidates = [e[0] for e in self.graph.in_edges(canonical, data=True) 
                         if e[2].get("relation") == "HAS_KARTĀ"]
        elif verb:
            # Fallback to verb filter
            candidates = [n for n in self.graph.nodes() 
                         if self.graph.nodes[n].get("type") == "Kriya" 
                         and self.graph.nodes[n].get("verb") == verb]
        else:
            # Last resort: all Kriyā nodes
            candidates = [n for n in self.graph.nodes() 
                         if self.graph.nodes[n].get("type") == "Kriya"]
        
        # Apply remaining kāraka constraints
        results = []
        for kriya_id in candidates:
            match = True
            
            # Check verb if not already filtered
            if verb and self.graph.nodes[kriya_id].get("verb") != verb:
                continue
            
            # Check other kāraka constraints
            for karaka_type, required_entity in karaka_constraints.items():
                if not required_entity or karaka_type == "KARTA":  # Already filtered
                    continue
                
                # Resolve entity and check edge (FROM Kriyā TO Entity)
                canonical = self.graph.entity_resolver.resolve(required_entity)
                relation = self._map_karaka_to_relation(karaka_type)
                
                # Check if edge exists (outgoing from Kriyā)
                edges = [e for e in self.graph.out_edges(kriya_id, data=True) 
                        if e[1] == canonical and e[2].get("relation") == relation]
                if not edges:
                    match = False
                    break
            
            if match:
                results.append(kriya_id)
        
        return results
    
    def _expand_causal_chain(self, kriya_nodes: List[str]) -> List[str]:
        """Follow CAUSES edges to get full causal chain"""
        expanded = set(kriya_nodes)
        
        for kriya_id in kriya_nodes:
            # Follow CAUSES edges (both directions)
            caused_by = self.graph.get_neighbors(kriya_id, relation="CAUSES", direction="in")
            causes = self.graph.get_neighbors(kriya_id, relation="CAUSES", direction="out")
            expanded.update(caused_by)
            expanded.update(causes)
        
        return list(expanded)
    
    def _generate_answer(self, question: str, ground_truth_docs: List[Dict]) -> Dict:
        """Final LLM call with grounded context"""
        # Sort by doc_id and line_number for narrative coherence
        sorted_docs = sorted(ground_truth_docs, key=lambda d: (d["doc_id"], d["line_number"]))
        
        # Build context
        context = "\n".join([
            f"[{d['doc_id']}, Line {d['line_number']}]: {d['text']}"
            for d in sorted_docs
        ])
        
        # Single isolated LLM call
        system_prompt = """You are a precise answer generator. Form a natural answer using ONLY the provided context.
Rules:
- Use only information from the context
- Keep it concise
- Cite sources"""
        
        user_prompt = f"""Question: {question}

Context:
{context}

Natural Answer:"""
        
        answer = call_llm_isolated(system_prompt, user_prompt, self.model, self.tokenizer, max_tokens=200)
        
        return {
            "question": question,
            "answer": answer,
            "citations": sorted_docs,
            "status": "GROUNDED"
        }
```

**Design Decisions:**
- Query plan includes multi-hop instructions (follow_causes, follow_same_as)
- Graph traversal collects ALL relevant documents along reasoning path
- Documents sorted by (doc_id, line_number) to maintain narrative flow
- Final LLM acts as summarizer only, not reasoner
- Citations include full provenance (doc_id, line_number, original text)

## Data Models

### Graph Node Types

```python
@dataclass
class DocumentNode:
    node_id: str  # Format: {doc_id}_L{line_number}
    type: Literal["Document"] = "Document"
    doc_id: str
    line_number: int
    text: str

@dataclass
class KriyaNode:
    node_id: str  # Format: {doc_id}_L{line_number}_K{sequence}
    type: Literal["Kriya"] = "Kriya"
    verb: str
    doc_id: str
    line_number: int

@dataclass
class EntityNode:
    node_id: str  # Canonical name
    type: Literal["Entity"] = "Entity"
    canonical_name: str
    entity_type: Optional[str] = None  # "AI", "Person", "Location", etc.
```

### Graph Edge Types

```python
@dataclass
class GraphEdge:
    source: str
    target: str
    relation: Literal[
        "HAS_KARTĀ",        # Kriyā → Entity (agent) - DIRECTION CHANGED
        "HAS_KARMA",        # Kriyā → Entity (patient)
        "USES_KARANA",      # Kriyā → Entity (instrument)
        "TARGETS_SAMPRADĀNA", # Kriyā → Entity (recipient)
        "FROM_APĀDĀNA",     # Kriyā → Entity (source)
        "LOCATED_IN",       # Kriyā → Entity (spatial location - adhikarana space)
        "OCCURS_AT",        # Kriyā → Entity (temporal location - adhikarana time)
        "IS_SAME_AS",       # Entity → Entity (coreference)
        "CAUSES",           # Kriyā → Kriyā (causality)
        "CITED_IN"          # Kriyā → Document (provenance)
    ]
    doc_id: Optional[str] = None
    line_number: Optional[int] = None
```

### GSV-Retry Data Structures

```python
@dataclass
class Candidate:
    id: str  # "Candidate_A", "Candidate_B", "Candidate_C"
    data: Dict  # Extracted JSON (verb, karakas, etc.)
    raw_response: str

@dataclass
class ScoringResult:
    candidate_id: str
    scores: List[int]  # 3 scores from ensemble
    avg_score: float
    reasoning: List[str]  # Reasoning from each scoring call

@dataclass
class VerificationResult:
    choice: str  # Candidate ID or "ALL_INVALID"
    reasoning: str
    paninian_violations: List[str]

@dataclass
class GSVResult:
    golden_candidate: Optional[Candidate]
    attempts: int
    all_candidates: List[Candidate]
    all_scores: List[ScoringResult]
    verification: VerificationResult
    feedback_history: List[str]
```

### Query Plan Structure

```python
@dataclass
class QueryStep:
    goal: str  # Human-readable description
    verb: Optional[str]
    karakas: Dict[str, Optional[str]]  # {"KARTA": "Rama", "KARMA": None, ...}
    extract: str  # Which kāraka role contains the answer
    follow_causes: bool = False  # Whether to expand causal chain
    follow_same_as: bool = False  # Whether to follow coreference links

@dataclass
class QueryPlan:
    steps: List[QueryStep]
    reasoning: str

@dataclass
class QueryResult:
    question: str
    answer: str
    citations: List[Dict]  # [{doc_id, line_number, text}, ...]
    reasoning_trace: List[str]  # Graph traversal steps
    status: Literal["GROUNDED", "NO_MATCH", "ERROR"]
```

## Error Handling

### Error Categories

1. **Model Errors**
   - LLM timeout/failure → Retry with exponential backoff (max 3 attempts)
   - Invalid JSON response → Attempt parsing recovery, log raw response
   - Out of memory → Clear cache, reduce batch size

2. **Validation Errors**
   - Invalid score (not 1-100) → Retry scoring call until valid
   - Schema violation → Reject operation, log details
   - GSV-Retry exhaustion → Skip line, log all attempts

3. **Graph Errors**
   - Node not found → Return empty result
   - Circular traversal → Implement visited set, max depth limit
   - Malformed query plan → Return error to user

### Error Logging Strategy

```python
@dataclass
class ErrorLog:
    timestamp: datetime
    error_type: str
    component: str
    context: Dict
    stack_trace: Optional[str]

class ErrorHandler:
    def log_gsv_failure(self, text, all_candidates, scores, verifier_result):
        """Log complete GSV-Retry failure for debugging"""
        
    def log_schema_violation(self, operation, node_or_edge, violation):
        """Log schema enforcement failures"""
        
    def log_llm_failure(self, prompt, response, attempt_num):
        """Log LLM call failures with context"""
```

### Recovery Strategies

- **LLM Failures:** Exponential backoff (1s, 2s, 4s), then skip
- **JSON Parse Failures:** Regex recovery, then manual parsing, then skip
- **Schema Violations:** Reject write, continue processing
- **GSV-Retry Exhaustion (5 attempts):** 
  - Log detailed diagnostics with all candidates, scores, and verifier responses
  - Include exact line reference (doc_id, line_number, text)
  - Print failure message with cause
  - Skip line and continue processing
  - Accumulate failure statistics for final report
- **Graph Traversal Failures:** Return partial results with warning

## Testing Strategy

### Unit Testing

**Target Components:**
1. `parse_json_response()` - Test with malformed JSON, edge cases
2. `GraphSchema.validate_node()` - Test all node types and invalid cases
3. `GraphSchema.validate_edge()` - Test all relations and invalid cases
4. `EntityResolver.resolve()` - Test fuzzy matching, threshold behavior
5. `_map_karaka_to_relation()` - Test all kāraka types

**Test Data:**
- Malformed JSON strings (missing brackets, trailing commas)
- Invalid node types ("InvalidType")
- Invalid edge relations ("INVALID_RELATION")
- Entity variations ("Dr. Aris", "Aris", "Dr Aris")

### Integration Testing

**Test Scenarios:**

1. **GSV-Retry Loop:**
   - All candidates valid, scorer and verifier agree → Accept first try
   - Scorer and verifier disagree → Retry with feedback
   - All candidates invalid → Retry with feedback
   - Max retries exhausted → Return None

2. **Ingestion Pipeline:**
   - Single document, single line → Verify Document node, Kriyā node, edges
   - Multiple documents → Verify entity resolution across documents
   - Pronoun resolution → Verify IS_SAME_AS edges created

3. **Query Pipeline:**
   - Simple query (single hop) → Verify correct traversal
   - Multi-hop query with CAUSES → Verify causal chain expansion
   - Query with no match → Verify NO_MATCH status

**Test Documents:**
```
test_doc_1.txt:
"Rama gave the bow to Lakshmana."
"He used it to kill Ravana."

Expected Graph:
- Document nodes: test_doc_1_L1, test_doc_1_L2
- Kriyā nodes: test_doc_1_L1_K1 (give), test_doc_1_L2_K1 (use), test_doc_1_L2_K2 (kill)
- Entity nodes: Rama, Lakshmana, bow, Ravana, He, it
- IS_SAME_AS edges: He → Rama, it → bow
```

### Performance Testing

**Metrics to Track:**
- LLM calls per line (target: 13 avg, 27 max with retries)
- Ingestion time per line (target: <5s avg)
- Query response time (target: <10s for 3-hop queries)
- Memory usage (target: <12GB for 1000-line corpus)

**Optimization Targets:**
- Batch FAISS queries where possible
- Cache entity resolutions
- Limit graph traversal depth (max 5 hops)

### Colab-Specific Testing

**Cell Execution Tests:**
1. Run all cells in sequence → Verify no errors
2. Re-run Cell 7 (extraction) → Verify no duplicate nodes
3. Re-run Cell 12 (queries) → Verify consistent results
4. Restart runtime, run all → Verify model reloading works

**Memory Tests:**
- Monitor RAM usage during ingestion
- Test with 100, 500, 1000 line documents
- Verify FAISS index size stays reasonable

## Colab Cell Structure

### Cell Organization

```
CELL 1: Setup & Dependencies
- pip install commands
- Import statements
- Constants (ENTITY_SIMILARITY_THRESHOLD, etc.)
- Dataclass definitions

CELL 2: Load Models
- Load Llama 3.1 Nemotron Nano 8B V1 (4-bit)
- Load Llama-3.2-NV-EmbedQA-1B-v2
- Global caching check

CELL 3: Graph & Vector Store
- Initialize NetworkX MultiDiGraph
- Define GraphSchema class
- Initialize FAISS vector store
- Initialize EntityResolver

CELL 4: Load Prompts
- Load prompts.json
- Define load_prompts() function
- Print loaded prompt keys

CELL 5: Core Functions
- call_llm_isolated()
- parse_json_response()
- Helper utilities

CELL 6: GSV-Retry Engine
- GSVRetryEngine class
- All GSV-Retry methods

CELL 7: Graph Database
- KarakaGraphV2 class
- Schema validation
- Graph operations

CELL 8: Ingestion Pipeline - Step 1
- load_and_refine_documents()
- _embed_and_store()
- Execute: Load documents and create Document nodes

CELL 9: Ingestion Pipeline - Step 2
- GSV-Retry extraction loop
- _write_to_graph()
- Execute: Extract and write Kriyās

CELL 10: Ingestion Pipeline - Step 3
- Post-processing methods
- _resolve_coreferences()
- _link_metaphorical_entities()
- _enrich_entity_types()
- _detect_causal_relationships()
- Execute: Run all post-processing

CELL 11: Query Pipeline
- QueryPipeline class
- _execute_traversal()
- _generate_answer()

CELL 12: Run Queries
- Define test queries
- Execute query pipeline
- Print results with citations
- Save to query_results.json
```

### Progress Indicators

Each cell should print clear progress:
```python
print("✅ Dependencies installed")
print("⚠️  Warning: Model already loaded")
print("❌ ERROR: Failed to parse JSON")
print("📄 Processing: document.txt")
print("   ✓ Loaded 50 lines")
print("      ↻ Duplicate kriya detected")
```

## Design Rationale

### Why GSV-Retry?

**Problem:** Single-pass LLM extraction is unreliable. Models hallucinate, miss entities, or violate linguistic rules.

**Solution:** Multi-candidate generation with independent validation:
1. **Generate 3 candidates** - Increases chance of at least one good extraction
2. **Robust scoring** - Ensemble of 3 calls reduces variance
3. **Blind verification** - Rule-based check prevents score bias
4. **Cross-validation** - Only accept when scorer and verifier agree
5. **Feedback loop** - Model learns from failures and self-corrects

**Trade-off:** More LLM calls (13 avg, 27 max) vs. higher quality. For hackathon, quality > speed.

### Why NetworkX + FAISS?

**Alternatives Considered:**
- Neo4j: Requires server, overkill for hackathon
- SQLite: Poor graph traversal performance
- Pure FAISS: No structured relationships

**Decision:** NetworkX for graph operations, FAISS for semantic search
- Lightweight (no server)
- Fast graph traversal (in-memory)
- Colab-friendly (12-16GB RAM sufficient)
- Easy to visualize (GEXF export)

### Why Strict Schema?

**Problem:** Unstructured graphs become unmaintainable. Query logic breaks with inconsistent edge types.

**Solution:** Enforce schema at write-time
- Prevents "IS_KARTA_OF" vs "IS_KARTĀ_OF" inconsistencies
- Enables reliable query translation
- Makes debugging easier (violations logged immediately)

### Why Isolated LLM Calls?

**Problem:** Conversation history causes context contamination. Model "remembers" previous extractions and biases new ones.

**Solution:** Each call is stateless
- Prevents cross-contamination between lines
- Makes scoring truly independent
- Enables parallel processing (future optimization)

## Future Enhancements (Post-Hackathon)

1. **Parallel Processing:** Batch LLM calls with asyncio
2. **Incremental Updates:** Add new documents without full re-ingestion
3. **Query Optimization:** Cache common traversal patterns
4. **Advanced RAG:** Use FAISS for query expansion
5. **Visualization:** Interactive graph explorer in Colab
6. **Metrics Dashboard:** Track GSV-Retry success rates, common failures
7. **Prompt Tuning:** A/B test different Pāṇinian rule formulations
8. **Entity Linking:** Link to external knowledge bases (Wikidata)


## Critical Design Improvements (Based on Architectural Review)

### 1. Batched Validation Strategy (Alternative to Per-Line GSV-Retry)

For hackathon efficiency, consider this phased approach:

**Phase 1a: Single-Pass Generation**
- Run all lines through single-candidate generation (1 LLM call per line)
- Store all candidates in memory

**Phase 1b: Batch Validation**
- Run validator LLM over all candidates (simplified verification prompt)
- Identify failed extractions

**Phase 1c: Focused GSV-Retry**
- Apply full GSV-Retry loop only to failed extractions (~20% of lines)
- This reduces average LLM calls from 13 to ~4 per line

**Trade-off:** Slightly lower quality on easy lines, but 3x faster ingestion overall.

### 2. Simplified Verification Prompt

**Original Approach:** Embed full Pāṇinian Sūtra rules in verification prompt

**Problem:** LLM may not apply linguistic theory correctly without training

**Improved Verification Prompt:**
```
You are a verification agent. Given a sentence and JSON extraction, check for:

1. HALLUCINATION: Is any entity in the JSON not present in the sentence?
2. OMISSION: Is there a clear agent, object, or instrument missing from the JSON?
3. ROLE MISMATCH: Is the KARTA (agent) clearly the KARMA (object) or vice-versa?

Return the most accurate candidate ID or 'ALL_INVALID' with reasoning.
```

**Why:** Tests concrete, verifiable errors rather than abstract grammar theory.

### 3. Extraction-Time Coreference Hints

**Enhancement to Extraction Prompt:**
```json
{
  "verb": "kill",
  "karakas": {"KARTA": "He", "KARMA": "Ravana"},
  "coreferences": [
    {"pronoun": "He", "context": "Previous sentence mentioned Rama"}
  ]
}
```

**Why:** Captures coreference information when context is richest (during extraction), reducing post-processing complexity.

### 4. LLM-Based ADHIKARANA Classification

**Instead of keyword heuristics, enhance extraction prompt:**
```
For ADHIKARANA kāraka, specify type:
- ADHIKARANA_SPATIAL: "at the temple", "in the forest"
- ADHIKARANA_TEMPORAL: "at 3 PM", "on Tuesday", "yesterday"
```

**Why:** LLM is more reliable than keyword matching for temporal/spatial distinction.

### 5. Edge Direction Standardization

**Critical Change:** ALL kāraka relations flow FROM Kriyā TO Entity

**Before:**
- IS_KARTĀ_OF: Entity → Kriyā
- HAS_KARMA: Kriyā → Entity (inconsistent)

**After:**
- HAS_KARTĀ: Kriyā → Entity
- HAS_KARMA: Kriyā → Entity (consistent)

**Impact on Query Traversal:**
```python
# Find all actions performed by Rama
entity_id = "Rama"
# Get incoming edges to Rama with relation HAS_KARTĀ
kriya_nodes = [e[0] for e in graph.in_edges(entity_id, data=True) 
               if e[2]["relation"] == "HAS_KARTĀ"]
```

**Why:** Consistent direction enables O(k) traversal instead of O(N) node scanning.

### 6. Expanded Pronoun Coverage

**Original:** ["He", "She", "It", "They"]

**Enhanced:** ["he", "she", "it", "they", "him", "her", "his", "hers", "its", "their", "theirs", "which", "that", "who", "whom"]

**Why:** Catches possessive pronouns and relative pronouns critical for coreference resolution.
