# Sentence Split Flow

## Overview

Document sentence splitting flow with chunking strategy and async LLM processing. Breaks validated documents into manageable chunks, then processes each chunk via LLM for intelligent sentence splitting.

## Flow Description

### Phase 1: Document Preparation

1. **Client Request**: `POST /documents/{doc_id}/start-splitting`
2. **Document Validation**: Verify `upload_status = "UPLOAD_COMPLETE"`
3. **Document Analysis**: Calculate total bytes, initialize splitting job
4. **Response**: Return splitting job ID for progressive chunking

### Phase 2: Progressive Chunking

1. **Client Request**: `POST /documents/{doc_id}/create-chunk`
2. **Chunk Creation**: Create next chunk with optimal boundaries
3. **LLM Submission**: Submit chunk to LLM queue immediately
4. **Response**: Return chunk ID and progress metrics

### Phase 3: Iterative Chunk Processing

1. **Client Polling**: `GET /chunks/{chunk_id}/status`
2. **LLM Response Check**: Check latest LLM request status
3. **Fidelity Validation**: Validate extracted sentences against chunk text
4. **Adaptive Processing**:
   - If fidelity passes → Mark chunk complete
   - If fidelity fails → Adjust chunk boundaries and retry
   - If partial success → Process validated sentences, adjust for remainder

### Phase 4: Final Sentence Assembly

1. **Completion Check**: All chunks validated and complete
2. **Sentence Deduplication**: Handle overlapping chunk sentences
3. **Global Ordering**: Assign final document sequence numbers
4. **Status Update**: Mark document splitting as complete

## Database Schema

```sql
-- Document-level splitting tracking
CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY,
    doc_hash_256 TEXT UNIQUE NOT NULL,
    original_filename TEXT NOT NULL,
    file_size_bytes INTEGER,
    s3_key TEXT,
    upload_status TEXT NOT NULL,
    s3_url_generated_at INTEGER,
    s3_url_expires_at INTEGER,
    
    -- Splitting specific fields
    splitting_job_id TEXT,
    splitting_status TEXT DEFAULT 'not_started',
    document_size_bytes INTEGER DEFAULT 0,
    processed_bytes INTEGER DEFAULT 0,        -- NEEDED: Progress tracking
    total_chunks_created INTEGER DEFAULT 0,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Individual chunks with versioning and overlap support
CREATE TABLE document_chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    splitting_job_id TEXT NOT NULL,
    
    -- Chunk positioning (can overlap)
    start_byte_offset INTEGER NOT NULL,
    end_byte_offset INTEGER NOT NULL,
    chunk_size_bytes INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    
    -- Versioning for iterative refinement
    version INTEGER DEFAULT 1,
    parent_chunk_id TEXT,              -- If this is a refinement of another chunk
    
    -- Status tracking
    status TEXT NOT NULL,              -- splitting_pending, splitting_in_progress, 
                                      -- splitting_complete, splitting_failed, 
                                      -- fidelity_failed, needs_adjustment
    
    -- LLM processing tracking
    current_llm_request_id TEXT,       -- Latest LLM request for this chunk
    successful_sentences_count INTEGER DEFAULT 0,
    
    -- Adjustment tracking
    adjustment_reason TEXT,            -- Why chunk boundaries were adjusted
    context_expansion_left INTEGER DEFAULT 0,   -- Bytes added to left
    context_expansion_right INTEGER DEFAULT 0,  -- Bytes added to right
    
    failure_reason TEXT,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id),
    FOREIGN KEY (parent_chunk_id) REFERENCES document_chunks(chunk_id)
);

-- Track all LLM requests per chunk (multiple calls possible)
CREATE TABLE chunk_llm_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id TEXT NOT NULL,
    llm_request_id TEXT NOT NULL,
    request_sequence INTEGER NOT NULL, -- 1st, 2nd, 3rd attempt for this chunk
    request_type TEXT NOT NULL,        -- initial, fidelity_retry, context_expansion
    
    -- Fidelity results (based on current implementation)
    fidelity_passed BOOLEAN,
    fidelity_similarity_score REAL,    -- 0.0 to 1.0 (current uses >0.95)
    sentences_extracted INTEGER DEFAULT 0,
    sentences_validated INTEGER DEFAULT 0,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (chunk_id) REFERENCES document_chunks(chunk_id),
    FOREIGN KEY (llm_request_id) REFERENCES llm_requests(request_id)
);

-- Temporary sentence candidates (before final validation)
CREATE TABLE sentence_candidates (
    candidate_id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL,
    llm_request_id TEXT NOT NULL,
    
    sentence_text TEXT NOT NULL,
    sentence_hash TEXT NOT NULL,       -- SHA-256 like current implementation
    chunk_sequence INTEGER NOT NULL,   -- Position within chunk
    
    -- Validation status
    fidelity_status TEXT NOT NULL,     -- pending, passed, failed
    fidelity_error TEXT,
    
    -- Text positioning for fidelity check
    start_char_offset INTEGER,
    end_char_offset INTEGER,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (chunk_id) REFERENCES document_chunks(chunk_id),
    FOREIGN KEY (llm_request_id) REFERENCES llm_requests(request_id)
);

-- Global sentence content (reusable across documents)
CREATE TABLE sentences (
    sentence_hash TEXT PRIMARY KEY,    -- SHA-256 hash of normalized sentence text
    text TEXT NOT NULL,                -- Actual sentence content (normalized)
    text_length_chars INTEGER NOT NULL, -- Character count
    text_length_bytes INTEGER NOT NULL, -- Byte count (UTF-8)
    
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Document-sentence linking table (many-to-many relationship)
CREATE TABLE document_sentences (
    link_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    sentence_hash TEXT NOT NULL,       -- Links to sentences table
    
    -- Position within document
    start_byte_offset INTEGER NOT NULL,
    end_byte_offset INTEGER NOT NULL,
    document_sequence INTEGER NOT NULL, -- Order in document (0, 1, 2...)
    
    -- Source tracking
    chunk_id TEXT NOT NULL,            -- Which chunk produced this sentence
    source_llm_request_id TEXT,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id),
    FOREIGN KEY (sentence_hash) REFERENCES sentences(sentence_hash),
    FOREIGN KEY (chunk_id) REFERENCES document_chunks(chunk_id),
    FOREIGN KEY (source_llm_request_id) REFERENCES llm_requests(request_id)
    
    -- No UNIQUE constraint - same sentence can appear multiple times in same document
);
```

## Implementation

### Phase 1 Implementation: Document Preparation

```python
def handle_start_splitting_request(doc_id):
    """Initialize document for progressive chunking"""
    trace_id = start_trace("start_splitting", doc_id=doc_id)
    
    try:
        # 1. Validate document status
        doc = db.query("SELECT * FROM documents WHERE doc_id=?", doc_id)
        if not doc or doc.upload_status != "UPLOAD_COMPLETE":
            return error_response("Document not ready for splitting", trace_id)
        
        # 2. Check if already processing
        if doc.splitting_status == "splitting_in_progress":
            return existing_splitting_status(doc, trace_id)
        
        # 3. Get document size from S3
        document_size = get_s3_object_size(doc.s3_key)
        splitting_job_id = generate_uuid()
        
        # 4. Initialize document splitting
        db.update("documents", {
            "splitting_job_id": splitting_job_id,
            "splitting_status": "splitting_in_progress",
            "document_size_bytes": document_size,
            "processed_bytes": 0,
            "total_chunks_created": 0,
            "completed_chunks": 0,
            "updated_at": int(time.time())
        }, {"doc_id": doc_id})
        
        complete_trace(trace_id, "SUCCESS", {
            "action": "splitting_initialized",
            "document_size_bytes": document_size,
            "splitting_job_id": splitting_job_id
        })
        
        return {
            "doc_id": doc_id,
            "splitting_job_id": splitting_job_id,
            "status": "splitting_in_progress",
            "document_size_bytes": document_size,
            "processed_bytes": 0,
            "progress_percentage": 0.0,
            "trace_id": trace_id
        }
        
    except Exception as e:
        log_error_with_trace(trace_id, "SYSTEM_ERROR", str(e), "start_splitting")
        return error_response("Failed to initialize splitting", trace_id)

def handle_create_chunk_request(doc_id):
    """Create next chunk and submit to LLM"""
    trace_id = start_trace("create_chunk", doc_id=doc_id)
    
    try:
        doc = db.query("SELECT * FROM documents WHERE doc_id=?", doc_id)
        
        # 0. Precheck: Document must be in splitting_in_progress status
        if not doc or doc.splitting_status != "splitting_in_progress":
            log_error_with_trace(trace_id, "INVALID_DOC_STATUS", 
                               f"Document not in splitting_in_progress status: {doc.splitting_status if doc else 'NOT_FOUND'}", 
                               "create_chunk")
            return error_response("Document not ready for chunk creation", trace_id)
        
        # 1. Calculate next chunk boundaries
        next_chunk_info = calculate_next_chunk_boundaries(doc)
        if not next_chunk_info:
            return {"message": "All chunks created", "doc_id": doc_id}
        
        # 2. Read chunk content from S3
        chunk_text = read_s3_byte_range(
            doc.s3_key, 
            next_chunk_info["start_byte"], 
            next_chunk_info["end_byte"]
        )
        
        # 3. Create chunk record
        chunk_id = generate_uuid()
        db.insert("document_chunks", {
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "splitting_job_id": doc.splitting_job_id,
            "start_byte_offset": next_chunk_info["start_byte"],
            "end_byte_offset": next_chunk_info["end_byte"],
            "chunk_size_bytes": len(chunk_text.encode('utf-8')),
            "chunk_text": chunk_text,
            "status": "splitting_pending"
        })
        
        # 4. Submit to LLM immediately
        llm_request_id = submit_llm_request(
            prompt_template="sentence_split_prompt.txt",
            inputs={"CHUNK_TEXT": chunk_text},
            operation="sentence_split",
            context={
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "chunk_version": 1
            },
            parent_trace_id=trace_id
        )
        
        # 5. Track LLM request
        db.insert("chunk_llm_requests", {
            "chunk_id": chunk_id,
            "llm_request_id": llm_request_id,
            "request_sequence": 1,
            "request_type": "initial"
        })
        
        # 6. Update chunk with LLM request
        db.update("document_chunks", {
            "status": "splitting_in_progress",
            "current_llm_request_id": llm_request_id,
            "updated_at": int(time.time())
        }, {"chunk_id": chunk_id})
        
        # 7. Update document progress
        new_processed_bytes = next_chunk_info["end_byte"]
        progress_percentage = (new_processed_bytes / doc.document_size_bytes) * 100
        
        db.update("documents", {
            "processed_bytes": new_processed_bytes,
            "total_chunks_created": doc.total_chunks_created + 1,
            "updated_at": int(time.time())
        }, {"doc_id": doc_id})
        
        complete_trace(trace_id, "SUCCESS", {
            "action": "chunk_created_and_submitted",
            "chunk_id": chunk_id,
            "llm_request_id": llm_request_id
        })
        
        return {
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "status": "splitting_in_progress",
            "chunk_size_bytes": len(chunk_text.encode('utf-8')),
            "progress_percentage": round(progress_percentage, 2),
            "processed_bytes": new_processed_bytes,
            "total_bytes": doc.document_size_bytes,
            "trace_id": trace_id
        }
        
    except Exception as e:
        log_error_with_trace(trace_id, "SYSTEM_ERROR", str(e), "create_chunk")
        return error_response("Failed to create chunk", trace_id)

def calculate_next_chunk_boundaries(doc):
    """Calculate optimal boundaries for next chunk"""
    # Get last processed byte
    last_chunk = db.query("""
        SELECT MAX(end_byte_offset) as last_byte 
        FROM document_chunks 
        WHERE doc_id = ?
    """, doc.doc_id)
    
    start_byte = last_chunk[0].last_byte if last_chunk[0].last_byte else 0
    
    if start_byte >= doc.document_size_bytes:
        return None  # All chunks created
    
    # Calculate chunk size (4000 chars ≈ 4000-8000 bytes depending on encoding)
    target_chunk_size = 6000  # bytes
    end_byte = min(start_byte + target_chunk_size, doc.document_size_bytes)
    
    # Adjust to word boundaries to avoid splitting words
    end_byte = adjust_to_word_boundary(doc.s3_key, start_byte, end_byte)
    
    return {
        "start_byte": start_byte,
        "end_byte": end_byte
    }
```

### Phase 3: Iterative Chunk Processing & Completion Detection

```python
def handle_chunk_status_request(chunk_id):
    """Check chunk status and process LLM responses"""
    trace_id = start_trace("chunk_status_check", chunk_id=chunk_id)
    
    try:
        # 1. Get chunk and latest LLM request
        chunk_info = db.query("""
            SELECT dc.*, clr.llm_request_id, clr.request_sequence, clr.request_type,
                   lr.status as llm_status, lr.response_data, lr.parsed_response
            FROM document_chunks dc
            JOIN chunk_llm_requests clr ON dc.chunk_id = clr.chunk_id
            JOIN llm_requests lr ON clr.llm_request_id = lr.request_id
            WHERE dc.chunk_id = ? AND clr.llm_request_id = dc.current_llm_request_id
        """, chunk_id)
        
        if not chunk_info:
            return error_response("Chunk not found", trace_id)
        
        chunk = chunk_info[0]
        
        # 2. Check if LLM response is ready
        if chunk.llm_status == "completed":
            result = process_chunk_llm_response(chunk, trace_id)
            
            # 3. Check if document splitting is complete after processing this chunk
            check_document_completion(chunk.doc_id, trace_id)
            
            return result
        elif chunk.llm_status == "failed":
            return handle_chunk_llm_failure(chunk, trace_id)
        else:
            # Still processing
            return {
                "chunk_id": chunk_id,
                "status": "splitting_in_progress",
                "llm_status": chunk.llm_status,
                "request_sequence": chunk.request_sequence,
                "trace_id": trace_id
            }
        
    except Exception as e:
        log_error_with_trace(trace_id, "SYSTEM_ERROR", str(e), "chunk_status_check")
        return error_response("Chunk status check failed", trace_id)

def check_document_completion(doc_id, parent_trace_id):
    """
    Check if document splitting is complete.
    
    Simple completion criteria:
    1. processed_bytes >= document_size_bytes (all bytes processed)
    2. All created chunks have status 'splitting_complete' or 'splitting_failed'
    3. No regex fallback - if LLM fails, document fails
    """
    try:
        doc = db.query("SELECT * FROM documents WHERE doc_id=?", doc_id)
        if not doc:
            return
        
        doc = doc[0]
        
        # Check if all bytes processed
        if doc.processed_bytes < doc.document_size_bytes:
            return  # Still creating chunks
        
        # Check if all chunks are in final state
        pending_chunks = db.query("""
            SELECT COUNT(*) as count
            FROM document_chunks 
            WHERE doc_id = ? AND status NOT IN ('splitting_complete', 'splitting_failed')
        """, doc_id)
        
        if pending_chunks[0].count > 0:
            return  # Still processing chunks
        
        # All chunks processed - finalize document
        finalize_document_splitting(doc_id, parent_trace_id)
        
    except Exception as e:
        log_error_with_trace(parent_trace_id, "COMPLETION_CHECK_ERROR", str(e), "check_document_completion")

def finalize_document_splitting(doc_id, parent_trace_id):
    """
    Finalize document splitting by creating final sentence records and updating status
    """
    try:
        # 1. Get all validated sentence candidates from completed chunks
        validated_candidates = db.query("""
            SELECT sc.*, dc.start_byte_offset, dc.end_byte_offset
            FROM sentence_candidates sc
            JOIN document_chunks dc ON sc.chunk_id = dc.chunk_id
            WHERE dc.doc_id = ? AND sc.fidelity_status = 'passed' AND dc.status = 'splitting_complete'
            ORDER BY dc.start_byte_offset, sc.chunk_sequence
        """, doc_id)
        
        # 2. Keep all sentences (no deduplication - same sentence can appear multiple times)
        all_sentences = validated_candidates
        unique_sentence_hashes = set(candidate.sentence_hash for candidate in all_sentences)
        
        # 3. Create global sentence records if they don't exist
        for sentence_hash in unique_sentence_hashes:
            # Find any candidate with this hash to get the text
            candidate = next(c for c in all_sentences if c.sentence_hash == sentence_hash)
            normalized_text = normalize_sentence_text(candidate.sentence_text)
            
            # Insert into global sentences table (ignore if exists)
            try:
                db.insert("sentences", {
                    "sentence_hash": sentence_hash,
                    "text": normalized_text,
                    "text_length_chars": len(normalized_text),
                    "text_length_bytes": len(normalized_text.encode('utf-8'))
                })
            except:
                pass  # Sentence already exists globally
        
        # 4. Create document-sentence links for ALL sentences (including duplicates)
        document_sequence = 0
        for candidate in all_sentences:
            link_id = generate_uuid()
            
            # Calculate approximate byte positions
            estimated_start = candidate.start_byte_offset + (candidate.start_char_offset or 0)
            estimated_end = candidate.start_byte_offset + (candidate.end_char_offset or len(candidate.sentence_text))
            
            db.insert("document_sentences", {
                "link_id": link_id,
                "doc_id": doc_id,
                "sentence_hash": candidate.sentence_hash,
                "start_byte_offset": estimated_start,
                "end_byte_offset": estimated_end,
                "document_sequence": document_sequence,
                "chunk_id": candidate.chunk_id,
                "source_llm_request_id": candidate.llm_request_id
            })
            
            document_sequence += 1
        
        # 5. Update document status
        db.update("documents", {
            "splitting_status": "splitting_complete",
            "updated_at": int(time.time())
        }, {"doc_id": doc_id})
        
        # 6. Log completion
        complete_trace(parent_trace_id, "SUCCESS", {
            "action": "document_splitting_complete",
            "total_sentences": len(all_sentences),
            "unique_sentences": len(unique_sentence_hashes),
            "doc_id": doc_id
        })
        
        print(f"Document {doc_id} splitting completed with {len(all_sentences)} total sentences ({len(unique_sentence_hashes)} unique)")
        
    except Exception as e:
        log_error_with_trace(parent_trace_id, "FINALIZATION_ERROR", str(e), "finalize_document_splitting")
        
        # Mark document as failed
        db.update("documents", {
            "splitting_status": "splitting_failed",
            "updated_at": int(time.time())
        }, {"doc_id": doc_id})

def normalize_sentence_text(text):
    """
    Normalize sentence text for consistent hashing.
    Only relax spacing and quotes, nothing else.
    """
    # Normalize whitespace (multiple spaces/tabs/newlines to single space)
    normalized = re.sub(r'\s+', ' ', text.strip())
    
    # Normalize quotes (convert smart quotes to regular quotes)
    normalized = normalized.replace('"', '"').replace('"', '"')
    normalized = normalized.replace(''', "'").replace(''', "'")
    
    return normalized

def process_chunk_llm_response(chunk, parent_trace_id):
    """Process LLM response with fidelity validation"""
    try:
        # 1. Parse LLM response to get sentence candidates
        sentences_data = json.loads(chunk.parsed_response)
        sentence_candidates = sentences_data.get("sentences", [])
        
        # 2. Create sentence candidates for fidelity checking
        candidate_ids = []
        for i, sentence_text in enumerate(sentence_candidates):
            candidate_id = generate_uuid()
            sentence_hash = hashlib.sha256(sentence_text.encode()).hexdigest()
            
            db.insert("sentence_candidates", {
                "candidate_id": candidate_id,
                "chunk_id": chunk.chunk_id,
                "llm_request_id": chunk.llm_request_id,
                "sentence_text": sentence_text,
                "sentence_hash": sentence_hash,
                "chunk_sequence": i,  # Position within chunk: 0=first sentence, 1=second, etc.
                "fidelity_status": "pending"
            })
            candidate_ids.append(candidate_id)
        
        # 3. Perform fidelity validation
        fidelity_results = validate_sentence_fidelity(chunk.chunk_text, sentence_candidates)
        
        # 4. Update candidate statuses based on fidelity
        passed_count = 0
        failed_count = 0
        
        for i, (candidate_id, fidelity_result) in enumerate(zip(candidate_ids, fidelity_results)):
            if fidelity_result["passed"]:
                db.update("sentence_candidates", {
                    "fidelity_status": "passed",
                    "confidence_score": fidelity_result["confidence"],
                    "start_char_offset": fidelity_result.get("start_offset"),
                    "end_char_offset": fidelity_result.get("end_offset")
                }, {"candidate_id": candidate_id})
                passed_count += 1
            else:
                db.update("sentence_candidates", {
                    "fidelity_status": "failed",
                    "fidelity_error": fidelity_result["error"]
                }, {"candidate_id": candidate_id})
                failed_count += 1
        
        # 5. Update chunk LLM request results
        db.update("chunk_llm_requests", {
            "fidelity_passed": failed_count == 0,
            "fidelity_score": passed_count / len(sentence_candidates) if sentence_candidates else 0,
            "sentences_extracted": len(sentence_candidates),
            "sentences_validated": passed_count
        }, {"chunk_id": chunk.chunk_id, "llm_request_id": chunk.llm_request_id})
        
        # 6. Decide next action based on fidelity results
        if failed_count == 0:
            # All sentences passed - chunk is complete
            return complete_chunk_processing(chunk, passed_count)
        elif passed_count > 0:
            # Partial success - process validated sentences and adjust chunk
            return handle_partial_fidelity_success(chunk, passed_count, failed_count, parent_trace_id)
        else:
            # Complete failure - adjust chunk boundaries and retry
            return handle_complete_fidelity_failure(chunk, parent_trace_id)
        
    except Exception as e:
        log_error_with_trace(parent_trace_id, "FIDELITY_ERROR", str(e), "process_chunk_response")
        return error_response("Fidelity validation failed", parent_trace_id)

def validate_sentence_fidelity(chunk_text, sentences):
    """
    Strict fidelity validation - only relax spacing and quotes.
    Programmatically align sentences with original text.
    """
    if not sentences:
        return {
            "overall_passed": False,
            "similarity_score": 0.0,
            "error": "No sentences extracted"
        }
    
    # Normalize both texts (only spacing and quotes)
    original_normalized = normalize_sentence_text(chunk_text)
    
    # Normalize and join all sentences
    normalized_sentences = [normalize_sentence_text(s) for s in sentences]
    joined_normalized = ''.join(normalized_sentences)
    
    # Strict comparison - must be identical after normalization
    if original_normalized == joined_normalized:
        return {
            "overall_passed": True,
            "similarity_score": 1.0,
            "length_difference": 0,
            "error": None
        }
    
    # If not identical, try to align sentences programmatically
    alignment_result = align_sentences_with_original(original_normalized, normalized_sentences)
    
    if alignment_result["success"]:
        return {
            "overall_passed": True,
            "similarity_score": alignment_result["coverage_ratio"],
            "length_difference": alignment_result["length_diff"],
            "error": None,
            "alignment_info": alignment_result["alignment_info"]
        }
    
    return {
        "overall_passed": False,
        "similarity_score": alignment_result["coverage_ratio"],
        "length_difference": alignment_result["length_diff"],
        "error": f"Alignment failed: {alignment_result['error']}"
    }

def align_sentences_with_original(original_text, sentences):
    """
    Programmatically align sentences with original text.
    Find where each sentence appears in the original.
    """
    try:
        total_original_length = len(original_text)
        covered_chars = set()
        alignment_info = []
        
        for i, sentence in enumerate(sentences):
            # Find sentence in original text
            start_pos = original_text.find(sentence)
            
            if start_pos != -1:
                end_pos = start_pos + len(sentence)
                
                # Track covered characters
                for pos in range(start_pos, end_pos):
                    covered_chars.add(pos)
                
                alignment_info.append({
                    "sentence_index": i,
                    "start_pos": start_pos,
                    "end_pos": end_pos,
                    "matched": True
                })
            else:
                # Try fuzzy matching for partial sentences
                best_match = find_best_substring_match(original_text, sentence)
                if best_match["score"] > 0.95:  # 95% match threshold
                    for pos in range(best_match["start"], best_match["end"]):
                        covered_chars.add(pos)
                    
                    alignment_info.append({
                        "sentence_index": i,
                        "start_pos": best_match["start"],
                        "end_pos": best_match["end"],
                        "matched": True,
                        "fuzzy_score": best_match["score"]
                    })
                else:
                    alignment_info.append({
                        "sentence_index": i,
                        "matched": False,
                        "error": "No suitable match found"
                    })
        
        # Calculate coverage
        coverage_ratio = len(covered_chars) / total_original_length if total_original_length > 0 else 0
        
        # Calculate length difference
        total_sentence_length = sum(len(s) for s in sentences)
        length_diff = abs(total_original_length - total_sentence_length)
        
        # Success criteria: >95% coverage and <10 char difference
        success = coverage_ratio > 0.95 and length_diff < 10
        
        return {
            "success": success,
            "coverage_ratio": coverage_ratio,
            "length_diff": length_diff,
            "alignment_info": alignment_info,
            "error": None if success else f"Coverage: {coverage_ratio:.3f}, Length diff: {length_diff}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "coverage_ratio": 0.0,
            "length_diff": float('inf'),
            "alignment_info": [],
            "error": f"Alignment error: {str(e)}"
        }

def find_best_substring_match(text, pattern):
    """
    Find best substring match using sliding window.
    Returns position and similarity score.
    """
    best_score = 0.0
    best_start = -1
    best_end = -1
    
    pattern_len = len(pattern)
    
    # Try different window sizes around pattern length
    for window_size in range(max(1, pattern_len - 10), pattern_len + 11):
        for start in range(len(text) - window_size + 1):
            end = start + window_size
            substring = text[start:end]
            
            # Calculate similarity (simple character overlap)
            if len(substring) > 0 and len(pattern) > 0:
                overlap = len(set(substring) & set(pattern))
                union = len(set(substring) | set(pattern))
                score = overlap / union if union > 0 else 0
                
                if score > best_score:
                    best_score = score
                    best_start = start
                    best_end = end
    
    return {
        "score": best_score,
        "start": best_start,
        "end": best_end
    }

def handle_partial_fidelity_success(chunk, passed_count, failed_count, parent_trace_id):
    """Handle case where some sentences passed fidelity, some failed"""
    
    # 1. Create final sentences for passed candidates
    create_final_sentences_from_candidates(chunk.chunk_id, "passed")
    
    # 2. Analyze failed sentences to determine chunk adjustment
    failed_sentences = get_failed_sentence_candidates(chunk.chunk_id)
    adjustment_strategy = analyze_fidelity_failures(failed_sentences, chunk.chunk_text)
    
    # 3. Create adjusted chunk if needed
    if adjustment_strategy["needs_adjustment"]:
        adjusted_chunk_id = create_adjusted_chunk(
            chunk, 
            adjustment_strategy,
            parent_trace_id
        )
        
        return {
            "chunk_id": chunk.chunk_id,
            "status": "partially_complete",
            "passed_sentences": passed_count,
            "failed_sentences": failed_count,
            "adjustment_created": True,
            "adjusted_chunk_id": adjusted_chunk_id,
            "adjustment_reason": adjustment_strategy["reason"]
        }
    else:
        # Mark chunk as complete with partial success
        db.update("document_chunks", {
            "status": "splitting_complete",
            "successful_sentences_count": passed_count,
            "failed_fidelity_count": failed_count,
            "updated_at": int(time.time())
        }, {"chunk_id": chunk.chunk_id})
        
        return {
            "chunk_id": chunk.chunk_id,
            "status": "splitting_complete",
            "passed_sentences": passed_count,
            "failed_sentences": failed_count,
            "adjustment_created": False
        }

def create_adjusted_chunk(original_chunk, adjustment_strategy, parent_trace_id):
    """Create new chunk with adjusted boundaries based on fidelity failures"""
    
    # Calculate new boundaries
    context_left = adjustment_strategy.get("expand_left_bytes", 0)
    context_right = adjustment_strategy.get("expand_right_bytes", 0)
    
    new_start = max(0, original_chunk.start_byte_offset - context_left)
    new_end = min(
        get_document_size(original_chunk.doc_id),
        original_chunk.end_byte_offset + context_right
    )
    
    # Read adjusted chunk content
    adjusted_text = read_s3_byte_range(
        get_document_s3_key(original_chunk.doc_id),
        new_start,
        new_end
    )
    
    # Create new chunk record
    adjusted_chunk_id = generate_uuid()
    db.insert("document_chunks", {
        "chunk_id": adjusted_chunk_id,
        "doc_id": original_chunk.doc_id,
        "splitting_job_id": original_chunk.splitting_job_id,
        "start_byte_offset": new_start,
        "end_byte_offset": new_end,
        "chunk_size_bytes": len(adjusted_text.encode('utf-8')),
        "chunk_text": adjusted_text,
        "version": original_chunk.version + 1,
        "parent_chunk_id": original_chunk.chunk_id,
        "status": "splitting_pending",
        "adjustment_reason": adjustment_strategy["reason"],
        "context_expansion_left": context_left,
        "context_expansion_right": context_right
    })
    
    # Submit to LLM
    llm_request_id = submit_llm_request(
        prompt_template="sentence_split_prompt.txt",
        inputs={"CHUNK_TEXT": adjusted_text},
        operation="sentence_split",
        context={
            "doc_id": original_chunk.doc_id,
            "chunk_id": adjusted_chunk_id,
            "chunk_version": original_chunk.version + 1,
            "parent_chunk_id": original_chunk.chunk_id,
            "adjustment_reason": adjustment_strategy["reason"]
        },
        parent_trace_id=parent_trace_id
    )
    
    # Track new LLM request
    db.insert("chunk_llm_requests", {
        "chunk_id": adjusted_chunk_id,
        "llm_request_id": llm_request_id,
        "request_sequence": 1,
        "request_type": "context_expansion"
    })
    
    # Update adjusted chunk with LLM request
    db.update("document_chunks", {
        "status": "splitting_in_progress",
        "current_llm_request_id": llm_request_id,
        "updated_at": int(time.time())
    }, {"chunk_id": adjusted_chunk_id})
    
    return adjusted_chunk_id
```

## Key Features

### 1. **Progressive Chunking (Based on Current Implementation)**

- One chunk created per API call for fine-grained control
- Paragraph-based chunking with 4000 char limit (like current)
- Byte-level progress tracking (processed_bytes / total_bytes)
- Overlapping chunks allowed for context preservation

### 2. **Fidelity Validation (Current Implementation Logic)**

- Join all sentences from LLM and compare to original chunk
- 95% similarity threshold using character set intersection
- Length difference must be < 10 characters
- **No regex fallback** - if LLM fails, chunk fails (as requested)

### 3. **Buffer-Based Completion Detection**

- Document considered complete when all chunks before buffer zone (last 10%) are done
- Handles the chicken-egg problem of not knowing when all chunks are created
- 5-minute stability check for buffer zone chunks
- Allows for chunk boundary adjustments without premature completion

### 4. **Multi-Request Chunk Processing**

- Multiple LLM calls per chunk tracked in `chunk_llm_requests`
- Request sequence tracking (1st attempt, 2nd retry, etc.)
- Different request types: initial, fidelity_retry, context_expansion

### 5. **Separate Sentence Storage (As Requested)**

- `sentences` table: Global sentence content (reusable across documents)
- `sentence_positions` table: Document-specific positioning and sequence
- Same sentence hash can appear in multiple documents
- Deduplication of overlapping chunk results

### 6. **Adaptive Chunk Boundaries**

- Chunks can overlap for better context
- Version tracking for chunk refinements
- Parent-child relationships between chunk versions
- Context expansion tracking (bytes added left/right)

### 7. **Status Granularity**

```
Document: not_started → splitting_in_progress → splitting_complete
                                             ↘ splitting_failed

Chunk: splitting_pending → splitting_in_progress → splitting_complete
                        ↘ fidelity_failed → needs_adjustment → splitting_pending
                        ↘ splitting_failed
```

### 8. **No Confidence Scores (As Requested)**

- Removed confidence scoring - binary pass/fail based on fidelity
- Focus on similarity score from current implementation
- Simplified validation logic

## API Design

```
# Document-level operations
POST /documents/{doc_id}/start-splitting   - Initialize progressive chunking
GET /documents/{doc_id}/splitting-progress - Get overall progress

# Progressive chunking
POST /documents/{doc_id}/create-chunk      - Create next chunk and submit to LLM
GET /documents/{doc_id}/chunks             - List all chunks with status

# Chunk-level operations  
GET /chunks/{chunk_id}/status              - Poll individual chunk processing
GET /chunks/{chunk_id}/candidates          - Get sentence candidates (for debugging)
POST /chunks/{chunk_id}/retry              - Retry failed chunk processing

# Final results
GET /documents/{doc_id}/sentences          - Get validated sentences (when complete)
```

## Dependencies

- **LLM Call Flow** - For async LLM processing
- **Error Handling** - For trace correlation and error logging

## Next Steps

1. Design LLM prompt for sentence splitting
2. Implement chunk processing logic
3. Create sentence validation and fidelity checks
4. Add retry logic for failed chunks
5. Implement sentence reassembly and deduplication#

# Concept Explanations

### **Context Expansion Process**

When fidelity validation fails, the system automatically adjusts chunk boundaries:

```python
def create_adjusted_chunk(original_chunk, adjustment_strategy, parent_trace_id):
    """
    Context expansion example:
    
    Original chunk: bytes 1000-2000 (1000 bytes)
    LLM returns sentences that don't match chunk text
    
    Adjustment strategy:
    - expand_left_bytes: 50   (add 50 bytes to the left)
    - expand_right_bytes: 100 (add 100 bytes to the right)
    
    New chunk: bytes 950-2100 (1150 bytes)
    More context might help LLM generate better sentences
    """
    context_left = adjustment_strategy.get("expand_left_bytes", 0)
    context_right = adjustment_strategy.get("expand_right_bytes", 0)
    
    new_start = max(0, original_chunk.start_byte_offset - context_left)
    new_end = min(document_size, original_chunk.end_byte_offset + context_right)
    
    # Create new chunk with expanded boundaries
    # This gets submitted to LLM as a new request
```

### **Sentences Extracted vs Validated**

```python
# Example LLM response parsing:
llm_response = ["Hello world.", "This is good.", "Random text.", "Goodbye."]

sentences_extracted = 4  # LLM returned 4 sentences

# Fidelity check against chunk text:
chunk_text = "Hello world. This is good. Goodbye."

# Results:
# "Hello world." ✅ Found in chunk
# "This is good." ✅ Found in chunk  
# "Random text." ❌ NOT found in chunk (LLM hallucination)
# "Goodbye." ✅ Found in chunk

sentences_validated = 3  # Only 3 sentences passed fidelity check
```

### **Chunk Sequence**

```python
# LLM returns sentences for a chunk:
sentences = [
    "This is the first sentence.",    # chunk_sequence = 0
    "This is the second sentence.",   # chunk_sequence = 1  
    "This is the third sentence."     # chunk_sequence = 2
]

# Each sentence gets its position within the chunk
# This helps maintain order when reassembling the document
```

### **Request Types in chunk_llm_requests**

```python
request_types = {
    "initial": "First attempt to split this chunk",
    "fidelity_retry": "Retry after fidelity validation failed", 
    "context_expansion": "Retry with expanded chunk boundaries (more context)"
}

# Example flow:
# 1. initial request → fidelity fails
# 2. fidelity_retry request → still fails  
# 3. context_expansion request → expand chunk boundaries and try again
```

### **Why We Track These Metrics**

- **sentences_extracted**: Know if LLM is responding properly
- **sentences_validated**: Know if LLM output matches source text
- **Low validation rate**: Indicates LLM hallucination or poor chunk boundaries
- **Context expansion**: Automatic recovery mechanism when fidelity fails
