# Knowledge Graph Processing Flow

## Overview

Asynchronous sentence-level knowledge graph processing using GSSR (Generate, Score, Select, Retry) methodology for entity extraction, kriya identification, and karaka (role) building. The system follows a client-controlled, status-driven architecture where each processing step requires explicit client requests.

## Status

✅ **DESIGNED** - Complete async architecture with GSSR implementation.

## Core Features

- **Sequential Sentence Processing**: Client-controlled sentence-by-sentence processing
- **Three-Phase GSSR**: Entity → Kriya → Karaka extraction phases
- **Async LLM Integration**: Full integration with existing LLM worker queue
- **Fidelity Validation**: Quality checks with automatic refinement (max 3 attempts)
- **Status Transparency**: Complete visibility into processing states
- **Extensible Architecture**: Support for additional phases beyond the initial three

## Database Schema

```sql
-- Extend documents table for KG processing
ALTER TABLE documents ADD COLUMN kg_extraction_status TEXT DEFAULT 'not_started';
ALTER TABLE documents ADD COLUMN kg_extraction_job_id TEXT;
ALTER TABLE documents ADD COLUMN kg_sentences_total INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN kg_sentences_completed INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN kg_sentences_failed INTEGER DEFAULT 0;

-- Configuration table for GSSR settings
CREATE TABLE kg_config (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    description TEXT,
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Insert default configuration
INSERT INTO kg_config VALUES 
    ('max_concurrent_sentences', '1', 'Maximum sentences processing concurrently globally'),
    ('variations_per_phase', '3', 'Number of variations to generate per phase'),
    ('max_refinement_attempts', '3', 'Maximum refinement attempts per variation'),
    ('scorer_score_threshold', '70', 'Minimum average score threshold for scorer validation'),
    ('fidelity_score_threshold', '0.8', 'Minimum fidelity score threshold'),
    ('max_regeneration_attempts', '3', 'Maximum regeneration attempts when scorer average < threshold');

-- Extend sentences table for KG processing (merge with existing table)
ALTER TABLE sentences ADD COLUMN kg_status TEXT DEFAULT 'kg_extraction_pending';
ALTER TABLE sentences ADD COLUMN current_phase TEXT DEFAULT 'entities';
ALTER TABLE sentences ADD COLUMN kg_started_at INTEGER;
ALTER TABLE sentences ADD COLUMN kg_completed_at INTEGER;
ALTER TABLE sentences ADD COLUMN kg_failure_reason TEXT;

-- Use existing document_sentences table (no new table needed)

-- Entity extraction phase (separate table for extensibility)
CREATE TABLE kg_entities (
    entity_id TEXT PRIMARY KEY,
    sentence_hash TEXT NOT NULL,
    variation_number INTEGER NOT NULL,     -- 1, 2, 3... (configurable variations per phase)
    
    -- Variation tracking
    variation_status TEXT DEFAULT 'pending',   -- pending, generating, completed, failed
    variation_type TEXT DEFAULT 'generation',  -- generation, fidelity_refinement
    llm_request_id TEXT,                       -- Links to llm_requests table
    parent_variation_id TEXT,                  -- Links to parent variation for refinements
    
    -- Validation results
    fidelity_status TEXT DEFAULT 'pending',    -- pending, passed, failed, skipped
    fidelity_score REAL DEFAULT 0.0,          -- 0.0 to 1.0
    scorer_status TEXT DEFAULT 'pending',      -- pending, passed, failed, skipped
    scorer_score_temp0 REAL DEFAULT 0.0,      -- 0-100 (temperature=0)
    scorer_score_temp06 REAL DEFAULT 0.0,     -- 0-100 (temperature=0.6)
    scorer_attempts INTEGER DEFAULT 0,        -- Number of scorer attempts
    
    -- Results
    extraction_result TEXT,                -- JSON blob with extracted entities
    final_score REAL DEFAULT 0.0,         -- Combined final score
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (sentence_hash) REFERENCES sentences(sentence_hash),
    FOREIGN KEY (llm_request_id) REFERENCES llm_requests(request_id),
    FOREIGN KEY (parent_variation_id) REFERENCES kg_entities(entity_id),
    UNIQUE(sentence_hash, variation_number)
);

-- Kriya extraction phase (separate table for extensibility)
CREATE TABLE kg_kriya (
    kriya_id TEXT PRIMARY KEY,
    sentence_hash TEXT NOT NULL,
    variation_number INTEGER NOT NULL,     -- 1, 2, 3... (configurable variations per phase)
    
    -- Variation tracking
    variation_status TEXT DEFAULT 'pending',   -- pending, generating, completed, failed
    variation_type TEXT DEFAULT 'generation',  -- generation, fidelity_refinement
    llm_request_id TEXT,                       -- Links to llm_requests table
    parent_variation_id TEXT,                  -- Links to parent variation for refinements
    
    -- Validation results
    fidelity_status TEXT DEFAULT 'pending',    -- pending, passed, failed, skipped
    fidelity_score REAL DEFAULT 0.0,          -- 0.0 to 1.0
    scorer_status TEXT DEFAULT 'pending',      -- pending, passed, failed, skipped
    scorer_score_temp0 REAL DEFAULT 0.0,      -- 0-100 (temperature=0)
    scorer_score_temp06 REAL DEFAULT 0.0,     -- 0-100 (temperature=0.6)
    scorer_attempts INTEGER DEFAULT 0,        -- Number of scorer attempts
    
    -- Results
    extraction_result TEXT,                -- JSON blob with extracted kriya
    final_score REAL DEFAULT 0.0,         -- Combined final score
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (sentence_hash) REFERENCES sentences(sentence_hash),
    FOREIGN KEY (llm_request_id) REFERENCES llm_requests(request_id),
    FOREIGN KEY (parent_variation_id) REFERENCES kg_kriya(kriya_id),
    UNIQUE(sentence_hash, variation_number)
);

-- Karaka extraction phase (separate table for extensibility)
CREATE TABLE kg_karaka (
    karaka_id TEXT PRIMARY KEY,
    sentence_hash TEXT NOT NULL,
    variation_number INTEGER NOT NULL,     -- 1, 2, 3... (configurable variations per phase)
    
    -- Variation tracking
    variation_status TEXT DEFAULT 'pending',   -- pending, generating, completed, failed
    variation_type TEXT DEFAULT 'generation',  -- generation, fidelity_refinement
    llm_request_id TEXT,                       -- Links to llm_requests table
    parent_variation_id TEXT,                  -- Links to parent variation for refinements
    
    -- Validation results
    fidelity_status TEXT DEFAULT 'pending',    -- pending, passed, failed, skipped
    fidelity_score REAL DEFAULT 0.0,          -- 0.0 to 1.0
    scorer_status TEXT DEFAULT 'pending',      -- pending, passed, failed, skipped
    scorer_score_temp0 REAL DEFAULT 0.0,      -- 0-100 (temperature=0)
    scorer_score_temp06 REAL DEFAULT 0.0,     -- 0-100 (temperature=0.6)
    scorer_attempts INTEGER DEFAULT 0,        -- Number of scorer attempts
    
    -- Results
    extraction_result TEXT,                -- JSON blob with extracted karaka
    final_score REAL DEFAULT 0.0,         -- Combined final score
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (sentence_hash) REFERENCES sentences(sentence_hash),
    FOREIGN KEY (llm_request_id) REFERENCES llm_requests(request_id),
    FOREIGN KEY (parent_variation_id) REFERENCES kg_karaka(karaka_id),
    UNIQUE(sentence_hash, variation_number)
);

-- Phase completion tracking (best stage selection per phase)
CREATE TABLE kg_phase_results (
    result_id TEXT PRIMARY KEY,
    sentence_hash TEXT NOT NULL,
    phase_name TEXT NOT NULL,              -- entities, kriya, karaka
    
    -- Phase completion status
    phase_status TEXT DEFAULT 'in_progress',  -- in_progress, completed, failed
    variations_generated INTEGER DEFAULT 0,   -- Count of completed variations (configurable)
    best_variation_id TEXT,                   -- ID of selected best variation (phase-specific)
    
    -- Consensus and scoring
    consensus_achieved BOOLEAN DEFAULT FALSE, -- All variations identical (skip scorer)
    average_fidelity_score REAL DEFAULT 0.0,
    average_scorer_score_temp0 REAL DEFAULT 0.0,
    average_scorer_score_temp06 REAL DEFAULT 0.0,
    final_scorer_average REAL DEFAULT 0.0,    -- Average of temp0 and temp06 scores
    total_llm_calls INTEGER DEFAULT 0,        -- Total number of LLM calls for this phase
    phase_completion_time INTEGER,
    
    -- Final extracted data (from best variation)
    final_extraction TEXT,                    -- JSON blob with final results
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (sentence_hash) REFERENCES sentences(sentence_hash),
    UNIQUE(sentence_hash, phase_name)
);
```

## Flow Description

Based on the Architecture Overview from README.md, we implement a **user-driven async architecture** where each junction point requires explicit client requests:

### Phase 1: Document KG Initialization
1. **Client Request**: `POST /documents/{doc_id}/start-kg-processing`
2. **Document Validation**: Verify `splitting_status = "splitting_complete"`
3. **Efficient Status Check**: Count existing sentence statuses without loading all sentences
4. **Status Update**: Mark document as `kg_extraction_in_progress` or `kg_extraction_complete`
5. **Response**: Return processing job ID and sentence counts

### Phase 2: User-Controlled Sentence Processing
1. **Client Request**: `POST /documents/{doc_id}/process-next-sentence`
2. **Concurrency Check**: Verify global concurrent sentence limit not exceeded
3. **Sentence Selection**: Find next sentence with `kg_extraction_pending` status
4. **Phase Initialization**: Start with entities phase, create stage tracking records
5. **Response**: Return sentence details and current phase information

### Phase 3: User-Driven Phase Progression (Following README Architecture)
Based on the README.md architecture diagram, each extraction step requires user trigger:

#### 3a. Entity Extraction Phase (L9: Extract Entities)
1. **Client Request**: `POST /sentences/{sentence_hash}/extract-entities`
2. **Pre-validation**: Ensure sentence is in correct state and phase
3. **Phase Initialization**: Create phase result record for entities
4. **Response**: Return phase status and variation generation readiness

#### 3b. Kriya Extraction Phase (L10: Extract Kriyā) 
1. **Client Request**: `POST /sentences/{sentence_hash}/extract-kriya`
2. **Pre-validation**: Ensure entities phase is complete
3. **Phase Initialization**: Create phase result record for kriya
4. **Response**: Return phase status and variation generation readiness

#### 3c. Karaka Extraction Phase (L11: Build Events)
1. **Client Request**: `POST /sentences/{sentence_hash}/extract-karaka`
2. **Pre-validation**: Ensure entities and kriya phases are complete
3. **Phase Initialization**: Create phase result record for karaka
4. **Response**: Return phase status and variation generation readiness

### Phase 4: User-Controlled GSSR Variation Generation
**Hierarchy**: Phase → Stage → Variations (V1, V2, V3, Vn...)

#### 4a. Variation Generation (User-Driven)
1. **Client Request**: `POST /sentences/{sentence_hash}/generate-variation/{phase}/{variation_number}`
2. **Pre-validation Checks**:
   - Ensure previous variation is complete (if not V1)
   - Verify phase is active and ready
   - Check variation doesn't already exist
3. **LLM Submission**: Submit variation request to LLM worker queue
4. **Response**: Return variation ID and generation status

#### 4b. Variation Status Monitoring
1. **Client Request**: `GET /variations/{variation_id}/status?phase={phase_name}`
2. **Table Lookup**: Use phase_name to determine correct table (kg_entities, kg_kriya, kg_karaka)
3. **LLM Response Check**: Process completed LLM responses
4. **Fidelity Validation**: Validate extraction against original sentence
5. **Refinement Logic**: If fidelity fails, allow refinement (max configurable attempts)
6. **Response**: Return variation status and next action available

#### 4c. Consensus Check and Scorer Phase
1. **Client Request**: `POST /sentences/{sentence_hash}/check-consensus/{phase}`
2. **Consensus Validation**: Compare all completed variations
3. **Scorer Decision**: If consensus achieved → skip scorer, else → run scorer
4. **Response**: Return consensus status and scorer requirement

#### 4d. Scorer Execution (If No Consensus)
1. **Client Request**: `POST /sentences/{sentence_hash}/run-scorer/{phase}`
2. **Scorer Phase 1**: Run scorer with temp=0 (1-100 score)
3. **Scorer Phase 2**: Run scorer with temp=0.6 (1-100 score)
4. **Average Calculation**: Calculate average of both scorer runs
5. **Threshold Check**: If average < 70 → regenerate (if limit not hit) or skip
6. **Response**: Return scorer results and next action needed

### Phase 5: User-Driven Phase Transitions
1. **Client Request**: `POST /sentences/{sentence_hash}/complete-phase/{phase}`
2. **Validation**: Ensure all required stages are complete
3. **Best Selection**: Choose stage with highest combined score
4. **Phase Transition**: User explicitly moves to next phase
5. **Completion**: User marks sentence as complete after all phases

## Implementation

### Document KG Initialization

```python
def handle_start_kg_processing_request(doc_id):
    """Initialize KG processing for a document (can only be called once) - Efficient version"""
    trace_id = start_trace("start_kg_processing", doc_id=doc_id)
    
    try:
        # 1. Validate document status
        doc = db.query("SELECT * FROM documents WHERE doc_id=?", doc_id)
        if not doc or doc.splitting_status != "splitting_complete":
            return error_response("Document not ready for KG processing", trace_id)
        
        # 2. Check if already initialized (can only be called once)
        if doc.kg_extraction_status != "not_started":
            return existing_kg_status(doc, trace_id)
        
        # 3. Efficient count-based approach using existing document_sentences table
        sentence_counts = db.query("""
            SELECT 
                COUNT(*) as total_sentences,
                COUNT(CASE WHEN s.kg_status = 'kg_extraction_complete' THEN 1 END) as completed_count,
                COUNT(CASE WHEN s.kg_status = 'kg_extraction_failed' THEN 1 END) as failed_count,
                COUNT(CASE WHEN s.kg_status = 'kg_extraction_pending' THEN 1 END) as pending_count,
                COUNT(CASE WHEN s.kg_status = 'kg_extraction_in_progress' THEN 1 END) as in_progress_count
            FROM document_sentences ds
            JOIN sentences s ON ds.sentence_hash = s.sentence_hash
            WHERE ds.doc_id = ?
        """, doc_id)
        
        if not sentence_counts or sentence_counts[0].total_sentences == 0:
            return error_response("No sentences found for document", trace_id)
        
        counts = sentence_counts[0]
        
        # 5. Initialize KG processing job
        kg_job_id = generate_uuid()
        
        # 6. Determine final status
        if counts.completed_count == counts.total_sentences:
            # All sentences already complete
            final_status = "kg_extraction_complete"
        else:
            final_status = "kg_extraction_in_progress"
        
        # 7. Update document status
        db.update("documents", {
            "kg_extraction_status": final_status,
            "kg_extraction_job_id": kg_job_id,
            "kg_sentences_total": counts.total_sentences,
            "kg_sentences_completed": counts.completed_count,
            "kg_sentences_failed": counts.failed_count,
            "updated_at": int(time.time())
        }, {"doc_id": doc_id})
        
        complete_trace(trace_id, "SUCCESS", {
            "action": "kg_processing_initialized",
            "kg_job_id": kg_job_id,
            "total_sentences": counts.total_sentences,
            "completed_sentences": counts.completed_count,
            "final_status": final_status
        })
        
        return {
            "doc_id": doc_id,
            "kg_job_id": kg_job_id,
            "status": final_status,
            "total_sentences": counts.total_sentences,
            "sentences_completed": counts.completed_count,
            "sentences_failed": counts.failed_count,
            "sentences_pending": counts.pending_count,
            "sentences_in_progress": counts.in_progress_count,
            "trace_id": trace_id
        }
        
    except Exception as e:
        log_error_with_trace(trace_id, "SYSTEM_ERROR", str(e), "start_kg_processing")
        return error_response("Failed to initialize KG processing", trace_id)

def handle_process_next_sentence_request(doc_id):
    """Process the next pending sentence for KG extraction (configurable concurrency)"""
    trace_id = start_trace("process_next_sentence", doc_id=doc_id)
    
    try:
        # 1. Validate document is in KG processing
        doc = db.query("SELECT * FROM documents WHERE doc_id=?", doc_id)
        if not doc or doc.kg_extraction_status != "kg_extraction_in_progress":
            return error_response("Document not in KG processing state", trace_id)
        
        # 2. Get configurable concurrent sentence limit
        max_concurrent = int(get_config_value('max_concurrent_sentences', '1'))
        
        # 3. Check global concurrent processing limit
        global_in_progress = db.query("""
            SELECT COUNT(*) as count FROM sentences 
            WHERE kg_status = 'kg_extraction_in_progress'
        """)
        
        if global_in_progress[0].count >= max_concurrent:
            return {
                "message": f"Maximum concurrent sentences ({max_concurrent}) already being processed globally",
                "status": "waiting",
                "global_in_progress": global_in_progress[0].count,
                "trace_id": trace_id
            }
        
        # 4. Find next pending sentence for this document using existing document_sentences table
        next_sentence = db.query("""
            SELECT ds.sentence_hash, ds.document_sequence, s.kg_status
            FROM document_sentences ds
            JOIN sentences s ON ds.sentence_hash = s.sentence_hash
            WHERE ds.doc_id = ? AND s.kg_status = 'kg_extraction_pending'
            ORDER BY ds.document_sequence ASC 
            LIMIT 1
        """, doc_id)
        
        if not next_sentence:
            # Check if all sentences are complete
            return check_document_kg_completion(doc_id, trace_id)
        
        sentence = next_sentence[0]
        
        # 5. Initialize sentence for processing (global status in sentences table)
        db.update("sentences", {
            "kg_status": "kg_extraction_in_progress",
            "current_phase": "entities",
            "kg_started_at": int(time.time())
        }, {"sentence_hash": sentence.sentence_hash})
        
        # 6. Create phase result record for entities
        db.insert("kg_phase_results", {
            "result_id": generate_uuid(),
            "sentence_hash": sentence.sentence_hash,
            "phase_name": "entities",
            "phase_status": "in_progress"
        })
        
        complete_trace(trace_id, "SUCCESS", {
            "action": "sentence_processing_started",
            "sentence_hash": sentence.sentence_hash,
            "sentence_sequence": sentence.sentence_sequence
        })
        
        # 7. Get configurable stages per phase
        stages_per_phase = int(get_config_value('variations_per_phase', '3'))
        
        return {
            "sentence_hash": sentence.sentence_hash,
            "sentence_sequence": sentence.document_sequence,
            "current_phase": "entities",
            "stages_needed": stages_per_phase,
            "stages_completed": 0,
            "trace_id": trace_id
        }
        
    except Exception as e:
        log_error_with_trace(trace_id, "SYSTEM_ERROR", str(e), "process_next_sentence")
        return error_response("Failed to process next sentence", trace_id)

def get_config_value(key, default_value):
    """Get configuration value with fallback to default"""
    try:
        result = db.query("SELECT config_value FROM kg_config WHERE config_key = ?", key)
        return result[0].config_value if result else default_value
    except:
        return default_value
```







## API Design (User-Driven Architecture)

Following the README.md architecture pattern where each junction requires user control:

```python
# Document-level KG processing
POST /documents/{doc_id}/start-kg-processing     # Initialize KG processing (efficient)
POST /documents/{doc_id}/process-next-sentence   # Process next pending sentence (configurable concurrency)
GET /documents/{doc_id}/kg-status                # Get overall KG progress

# Phase-specific extraction (matching README.md L9, L10, L11)
POST /sentences/{sentence_hash}/extract-entities # L9: Extract Entities phase (user-triggered)
POST /sentences/{sentence_hash}/extract-kriya    # L10: Extract Kriyā phase (user-triggered)
POST /sentences/{sentence_hash}/extract-karaka   # L11: Extract Karaka phase (user-triggered)

# GSSR variation management (user-controlled per variation)
POST /sentences/{sentence_hash}/generate-variation/{phase}/{variation_number}  # Generate specific variation (V1, V2, V3...)
GET /variations/{variation_id}/status            # Check variation status and process if complete
POST /variations/{variation_id}/refine           # User-triggered refinement (if fidelity failed)

# GSSR consensus and scoring (user-controlled)
POST /sentences/{sentence_hash}/check-consensus/{phase}  # Check if all variations match
POST /sentences/{sentence_hash}/run-scorer/{phase}       # Run scorer phase (temp=0, then temp=0.6)

# Phase completion (user-controlled)
POST /sentences/{sentence_hash}/complete-phase/{phase}   # User completes phase (select best variation)
POST /sentences/{sentence_hash}/move-to-next-phase      # User moves to next phase
POST /sentences/{sentence_hash}/complete-sentence       # User marks sentence complete

# Status and monitoring
GET /sentences/{sentence_hash}/kg-status                # Get sentence KG status
GET /sentences/{sentence_hash}/phase/{phase}/variations # Get all variations for a phase
GET /sentences/{sentence_hash}/phase/{phase}/status     # Get phase completion status
GET /sentences/{sentence_hash}/kg-results               # Get final extraction results

# Configuration management
GET /kg-config                                          # Get current GSSR configuration
PUT /kg-config/{key}                                   # Update configuration value
```

## GSSR Flow Clarification

**Hierarchy**: Phase → Stage → Variations

```
Phase: Entity
├── Stage: Generation (G)
│   ├── Variation 1 (V1) → Fidelity Check → [Pass/Fail → Refine if needed]
│   ├── Variation 2 (V2) → Fidelity Check → [Pass/Fail → Refine if needed]  
│   ├── Variation 3 (V3) → Fidelity Check → [Pass/Fail → Refine if needed]
│   └── Variation N (Vn) → [Configurable count]
├── Stage: Consensus Check
│   └── Compare all variations → [If identical → Skip Scorer]
├── Stage: Scorer (if no consensus)
│   ├── Scorer temp=0 → Score (1-100)
│   ├── Scorer temp=0.6 → Score (1-100)
│   └── Average < 70? → [Regenerate if limit not hit | Skip if limit hit]
└── Stage: Selection
    └── Select best variation based on combined scores
```

**User Control Points**:
1. Generate each variation (V1, V2, V3...)
2. Check variation status (triggers fidelity validation)
3. Refine variation (if fidelity failed)
4. Check consensus (compare all variations)
5. Run scorer (if no consensus achieved)
6. Complete phase (select best variation)

## Status Flow Patterns

### Document Level
```
not_started → kg_extraction_in_progress → kg_extraction_complete
           ↘ kg_extraction_failed
```

### Sentence Level
```
kg_extraction_pending → kg_extraction_in_progress → kg_extraction_complete
                     ↘ kg_extraction_failed
```

### Phase Level (per sentence)
```
not_started → in_progress → complete
           ↘ failed
```

### Variation Level (per phase)
```
pending → generating → completed
       ↘ failed
```

## Error Scenarios and Handling

### LLM Processing Errors
- **LLM timeout or rate limiting**: Automatic retry through existing LLM worker queue
- **JSON parsing failures**: Mark variation as failed, allow refinement attempts
- **Schema validation errors**: Provide structured feedback for refinement

### Fidelity Validation Errors
- **Entity not found in text**: Generate refinement with specific feedback
- **Low fidelity score**: Allow up to 3 refinement attempts before accepting best result
- **Complete fidelity failure**: Accept best available variation and continue

### System Errors
- **Database errors**: Full error logging with trace correlation
- **Processing interruption**: State preserved, resumable from last successful point
- **Concurrent processing**: Sequence-based locking prevents conflicts

## Key Benefits

- **Client-Controlled Flow**: Every processing step requires explicit client request
- **Complete Transparency**: Full visibility into processing states at all levels
- **Async Integration**: Seamless integration with existing LLM worker architecture
- **Quality Assurance**: GSSR methodology with fidelity validation ensures high-quality extractions
- **Extensible Design**: Easy to add new phases beyond the initial three
- **Error Recovery**: Comprehensive error handling with resumable processing
- **Sequential Processing**: Prevents resource conflicts while maintaining processing order
