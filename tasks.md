## Updated GSSR Flow:
```
Phase 1: Generation (3x JSONs at temp=0.6)
         ↓
Phase 2: Fidelity Check (programmatic)
         ↓
Phase 2a: Consensus Check (all 3 identical?)
         ↓ (if not identical)
Phase 3: Scorer (temp=0.0) → gives 3 scores
         ↓
    All scores < 70? → Retry from Phase 1 (max 5 attempts)
    At least one ≥ 70? → Go to Phase 4
         ↓
Phase 4: Second Scorer (temp=0.3) → verification
         ↓
    All scores < 70? → Retry from Phase 1 or fallback
         ↓
Phase 5: Select best JSON (average of pass1 + pass2 scores)
```

# Updated Task List: KG Pipeline and UI Enhancements (Final for Submission)

---

* `[x]` **Prompt Engineering (First Iteration - COMPLETE):**

    * `[x]` **Entity Extraction Prompt (D1):**
        * `[x]` Complete worked example showing reasoning + JSON output
        * `[x]` Emphasis on using `<reasoning>` block for step-by-step thinking
        * `[x]` Entity boundary rules (titles with names, appositives as separate, compounds as single)
        * `[x]` File: `D1_entity_extraction.txt`

    * `[x]` **Kriya Concept Prompt (D2a):**
        * `[x]` Voice Detection Checklist with concrete indicators
        * `[x]` Tricky case examples for passive voice
        * `[x]` Emphasis on thorough reasoning before classification
        * `[x]` File: `D2a_kriya_extraction.txt`

    * `[x]` **Event Instance + Kāraka Prompt (D2b):**
        * `[x]` Locus Decision Tree for classification (3-step process)
        * `[x]` Concrete examples applying the decision tree
        * `[x]` Explicit handling for passive without agent
        * `[x]` Reinforcement that entity references must match INPUT ENTITIES exactly
        * `[x]` File: `D2b_event_karaka_extraction.txt`

    * `[x]` **Scorer Prompt (Critical for GSSR):**
        * `[x]` Structured scoring rubric (100-point scale):
            * Completeness (40 points): All entities? All verbs? All kāraka roles?
            * Accuracy (40 points): Entity types? Voice? Kāraka semantics? Locus types?
            * Fidelity (20 points): Exact text match? No invented spans?
        * `[x]` Output format: JSON array with score + detailed reasoning for each of 3 input JSONs
        * `[x]` Strengths/weaknesses breakdown
        * `[x]` Designed for temperature = 0.0 (deterministic scoring)
        * `[x]` File: `scorer.txt`

    * `[x]` **Correction Prompt:**
        * `[x]` Template for providing specific error feedback to LLM
        * `[x]` Used when fidelity check fails or Locus errors detected
        * `[x]` File: `correction_prompt.txt`

---

* `[ ]` **KG Pipeline Architecture: GSSR Implementation:** *(Code implemented, testing pending)*

    * `[x]` **Define Sentence Table & Caching Strategy:**
        * `[x]` Define a central "Sentence Table" with the following columns:
            * `sentence_hash` (Primary Key)
            * `original_sentence` (To store the raw sentence text)
            * `document_ids` (A list/array to track all source documents containing the sentence)
            * `status` (Enum: e.g., `KG_PENDING`, `KG_IN_PROGRESS`, `KG_COMPLETE`, `KG_FAILED`, `NEEDS_REVIEW`)
            * `best_score` (To be updated with the final winning score *after* the GSSR process)
            * `failure_reason` (To track why GSSR failed if max attempts reached)
            * `needs_review` (Boolean flag for human review queue)
            * `attempts_count` (Track how many GSSR iterations were needed)
        * `[x]` When a new document is ingested, sentences are hashed and added to this table with the `KG_PENDING` status.
        * `[x]` The KG processing queue/worker should query this table and select only sentences with the `status = KG_PENDING` for processing.
        * `[x]` Before processing, a check should confirm the sentence isn't already `KG_COMPLETE` (as a redundant check for the queue logic).

    * `[ ]` **Implement Comprehensive Logging Strategy:**
        * `[ ]` Create a central `LLMCallLog` table to store all raw LLM requests and responses *as-is* (no cleanup) for complete debugging traceability.
        * `[ ]` Each log entry must include a unique request ID and contextual metadata (e.g., `pipeline_stage`, `document_id`, `sentence_hash`, `attempt_number`, `generation_index`).
        * `[ ]` Store the *extracted* JSON and `reasoning` sections in a separate processing table, linked to the `sentence_hash` and `LLMCallLog` ID.

    * `[ ]` **Develop Multi-Phase "Generate, Score, Select, Repeat" (GSSR) Pipeline:**
        * GSSR applies to three extraction phases: **(1) Entity Extraction (D1), (2) Kriya Extraction (D2a), (3) Event Instance + Kāraka Extraction (D2b)**
        * **Maximum 5 attempts** per sentence to prevent infinite loops
        * **Temperature strategy:** Generation = 0.6, Scoring Pass 1 = 0.0, Scoring Pass 2 = 0.3

    * `[ ]` **Phase 1: Generation (3x Independent Calls)**
        * `[ ]` For each extraction stage (D1, D2a, D2b), make **3 independent LLM calls** to generate 3 distinct JSON variations.
        * `[ ]` Use **temperature = 0.6** for focused but slightly diverse generations.
        * `[ ]` Require the LLM to provide its `reasoning` in `<reasoning>` tags for each generated JSON structure.
        * `[ ]` Log all 3 raw responses to `LLMCallLog` table with metadata.

    * `[ ]` **Phase 2: Unidirectional Fidelity Check**
        * `[ ]` Programmatically verify that all extracted text spans in the JSON exist verbatim in the `original_sentence`.
        * `[ ]` **Direction: JSON ⊂ Sentence** (not bidirectional - the sentence can have extra words).
        * `[ ]` Check: Every value in JSON (entity text, surface_text, entity in kāraka_links) must be a substring of `original_sentence`.
        * `[ ]` Allow for case-insensitive matching with a warning if case differs.
        * `[ ]` **Fidelity Failure Loop:**
            * `[ ]` If a check fails for any of the 3 JSONs, identify the *exact* span that failed.
            * `[ ]` Re-call the LLM with a correction prompt (use `correction_prompt.txt`) providing specific error feedback.
            * `[ ]` Attempt correction once per failed JSON.
            * `[ ]` If correction still fails, use the best available JSON and continue to scoring.

    * `[ ]` **Phase 2a: Consensus Check (Optimization)**
        * `[ ]` After all 3 JSONs pass the fidelity check, perform a semantic comparison.
        * `[ ]` **If all 3 JSONs are identical** (serialize with `json.dumps(sort_keys=True)` and compare):
            * `[ ]` **Skip** the entire scoring process (Phase 3 and Phase 4).
            * `[ ]` Select this single consensus JSON with score = 100.
            * `[ ]` Proceed directly to Phase 5.
        * `[ ]` **If JSONs are different:**
            * `[ ]` Proceed to Phase 3 for scoring.

    * `[ ]` **Phase 3: LLM Scoring (Pass 1 - Primary Evaluation)**
        * `[ ]` *(Triggered if consensus check in Phase 2a fails).*
        * `[ ]` Send all 3 verified JSON objects to the Scorer LLM in a **single call** (use `scorer.txt` prompt).
        * `[ ]` Use **temperature = 0.0** for maximum scoring consistency.
        * `[ ]` Parse the Scorer's response to extract:
            * Score (1-100) for *each* of the 3 JSONs
            * Detailed reasoning breakdown (completeness, accuracy, fidelity)
            * Strengths and weaknesses for each JSON
        * `[ ]` **Scoring Failure Handling:**
            * `[ ]` If *all 3* variations score below 70:
                * Check if `attempts_count < 5`
                * If yes: Increment `attempts_count`, trigger Generation step (Phase 1) again (optionally include scorer feedback in generation prompt)
                * If no (attempts_count == 5): Go to fallback selection

    * `[ ]` **Phase 4: LLM Scoring (Pass 2 - Verification)**
        * `[ ]` *(Triggered if at least one JSON scored ≥ 70 in Pass 1).*
        * `[ ]` Initiate a **second, independent** scoring call to the Scorer LLM (same `scorer.txt` prompt).
        * `[ ]` Use **temperature = 0.3** for slight variance to detect scorer bias.
        * `[ ]` Parse scores for all 3 JSONs.
        * `[ ]` If this second pass also fails to produce a score ≥ 70 for any variation:
            * Check if `attempts_count < 5`
            * If yes: Increment `attempts_count`, trigger Generation step (Phase 1) again
            * If no (attempts_count == 5): Go to fallback selection

    * `[ ]` **Phase 5: Final Selection and Graph Construction**
        * `[ ]` Combine scores from Pass 1 and Pass 2: `combined_score = (score_pass1 + score_pass2) / 2`
        * `[ ]` Select the JSON with the highest combined score.
        * `[ ]` **Update Sentence Table:**
            * Set `best_score` = selected JSON's combined score
            * Set `status = KG_COMPLETE`
            * Set `attempts_count` = current attempt number
            * Set `needs_review = FALSE`
        * `[ ]` Use the final selected JSON to create entities, events, and kāraka links in NetworkX:
            * Create entity nodes with properties: `{text, type, sentence_hash}`
            * Create event instance nodes with properties: `{instance_id, kriyā_concept, surface_text, prayoga, sentence_hash}`
            * Create kāraka edges between event instances and entities with properties: `{role, reasoning, sentence_hash}`
        * `[ ]` Create an embedding for the `original_sentence` using `llama-3.2-nv-embedqa-1b-v2` and store it in the vector database with `sentence_hash` as the key.

    * `[ ]` **Fallback Selection (When Max Attempts Reached):**
        * `[ ]` If after 5 attempts no JSON scores ≥ 70:
            * Select the JSON with the highest score from the last attempt
            * **Update Sentence Table:**
                * Set `status = KG_COMPLETE`
                * Set `needs_review = TRUE`
                * Set `failure_reason` = "MAX_ATTEMPTS_REACHED" or "LOW_QUALITY_SCORES"
                * Set `best_score` = the fallback score
                * Set `attempts_count = 5`
            * Log warning for manual review queue
            * Still create graph nodes/edges using the best available JSON

    * `[ ]` **Data Storage Requirement:**
        * `[ ]` Ensure that full sentences are *not* stored directly within the NetworkX graph nodes.
        * `[ ]` Instead, store `sentence_hash` in NetworkX node/edge properties that link back to the `Sentence Table` and the vector database.
        * `[ ]` Graph queries can join with Sentence Table using `sentence_hash` to retrieve original text when needed.

---

* `[ ]` **UI:**
    * `[ ]` Update the UI design based on the reference from `stitch.withgoogle`.

---

* `[ ]` **Code Maintenance & Documentation:**
    * `[ ]` Clean the project codebase: Refactor and remove all unnecessary files, and delete any deprecated or unused scripts.
    * `[ ]` Document known limitations for first iteration:
        * No coreference resolution (pronouns not linked to referents across sentences)
        * Single-sentence processing (no cross-sentence context)
        * No external NLP tools (pure LLM-based pipeline using prompt engineering only)
        * Relations (Sambandha) and Attributes (Modifiers) deferred to future iterations
        * Character range extraction skipped (ambiguous for duplicate entities in same sentence)
    * `[ ]` Document the GSSR pipeline flow with diagrams
    * `[ ]` Add code comments explaining temperature choices and retry logic
    * `[ ]` Create a human review queue interface/script for sentences marked with `needs_review = TRUE`

--- 

