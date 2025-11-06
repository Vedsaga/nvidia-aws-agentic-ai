# ============================================================================
# CELL 1: Setup & Dependencies
# ============================================================================
print("Installing required libraries...")
!pip install transformers torch accelerate networkx faiss-cpu pyyaml -q
print("✅ Dependencies installed.")

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModel
import json
import difflib
import re
import os
import sys
import networkx as nx
import faiss
import yaml
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import numpy as np
from collections import defaultdict
from typing import Dict, List, Optional

# Load configuration from config.yaml
def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

# Extract commonly used config values
ENTITY_SIMILARITY_THRESHOLD = CONFIG['entity_resolution']['similarity_threshold']
DB_FILE = CONFIG['file_paths']['db_file']
GRAPH_VIZ_FILE = CONFIG['file_paths']['graph_viz_file']

@dataclass
class Citation:
    document_id: str
    line_number: int
    original_text: str

@dataclass
class ReasoningStep:
    step_number: int
    description: str
    kriya_matched: str
    karakas_matched: Dict[str, str]
    citations: List[Citation]
    result: Any

print("✅ Setup complete")


# ============================================================================
# CELL 2: Load Models
# ============================================================================
print("\n" + "="*80)
print("LOADING MODELS")
print("="*80)

if 'llm_model' not in globals():
    print(f"Loading {CONFIG['models']['llm']['model_id']}...")
    model_id = CONFIG['models']['llm']['model_id']
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=CONFIG['models']['llm']['trust_remote_code'])
    tokenizer.pad_token_id = tokenizer.eos_token_id

    # Try primary dtype first, fallback to secondary if not supported
    try:
        dtype_primary = getattr(torch, CONFIG['models']['llm']['dtype_primary'])
        llm_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            dtype=dtype_primary,
            device_map=CONFIG['models']['llm']['device_map'],
            trust_remote_code=CONFIG['models']['llm']['trust_remote_code']
        )
    except Exception as e:
        print(f"⚠️  {CONFIG['models']['llm']['dtype_primary']} not supported, using {CONFIG['models']['llm']['dtype_fallback']}: {e}")
        dtype_fallback = getattr(torch, CONFIG['models']['llm']['dtype_fallback'])
        llm_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            dtype=dtype_fallback,
            device_map=CONFIG['models']['llm']['device_map'],
            trust_remote_code=CONFIG['models']['llm']['trust_remote_code']
        )
    print("✅ LLM loaded")
else:
    print("✅ Models already loaded — reusing.")

if 'embedding_model' not in globals():
    print(f"Loading {CONFIG['models']['embedding']['model_id']} for embeddings...")
    embedding_tokenizer = AutoTokenizer.from_pretrained(CONFIG['models']['embedding']['model_id'])
    embedding_model = AutoModel.from_pretrained(CONFIG['models']['embedding']['model_id'], trust_remote_code=CONFIG['models']['embedding']['trust_remote_code'])
    device = CONFIG['models']['embedding']['device'] if torch.cuda.is_available() else "cpu"
    embedding_model = embedding_model.to(device)
    embedding_model.eval()
    print("✅ Embedding model loaded")

def average_pool(last_hidden_states, attention_mask):
    """Average pooling with attention mask for NVIDIA embedding model."""
    last_hidden_states_masked = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    embedding = last_hidden_states_masked.sum(dim=1) / attention_mask.sum(dim=1)[..., None]
    embedding = F.normalize(embedding, dim=-1)
    return embedding


# ============================================================================
# CELL 3: Initialize NetworkX, GraphSchema, and FAISS
# ============================================================================
print("\n" + "="*80)
print("INITIALIZING GRAPH INFRASTRUCTURE")
print("="*80)

def call_llm_isolated(system_prompt: str, user_prompt: str, model, tokenizer, max_tokens: int = None, temperature: float = None, reasoning_mode: str = None, top_p: float = None) -> str:
    """Each call creates a fresh session - no conversation history

    Args:
        system_prompt: System instructions
        user_prompt: User query
        model: LLM model
        tokenizer: Tokenizer
        max_tokens: Max new tokens to generate
        temperature: Sampling temperature
        reasoning_mode: "on", "off", or None (auto-detect from config)
        top_p: Nucleus sampling parameter (default 0.95 for reasoning)

    Returns:
        Model response string
    """
    # Use config defaults if not specified
    if max_tokens is None:
        max_tokens = CONFIG['llm_call']['max_tokens']
    if temperature is None:
        temperature = CONFIG['llm_call']['temperature']
    if reasoning_mode is None:
        reasoning_mode = CONFIG.get('reasoning', {}).get('mode', 'on')
    if top_p is None:
        top_p = 0.95 if reasoning_mode == "on" else 1.0

    # Prepend reasoning mode directive to system prompt
    reasoning_directive = f"detailed thinking {reasoning_mode}"
    full_system_prompt = f"{reasoning_directive}\n\n{system_prompt}"

    messages = [
        {"role": "system", "content": full_system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    # Use sampling if temperature > 0
    do_sample = temperature > 0.0

    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=max_tokens,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=do_sample,
        temperature=temperature if do_sample else None,
        top_p=top_p if do_sample else None
    )

    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):]
    response = tokenizer.decode(output_ids, skip_special_tokens=True)

    return response.strip()

def parse_json_response(response: str) -> Any:
    response = re.sub(r"```(?:json)?", "", response)
    start = response.find('[') if '[' in response else response.find('{')
    end = response.rfind(']') if ']' in response else response.rfind('}')

    if start == -1 or end == -1:
        return None

    json_str = response[start:end+1]

    try:
        return json.loads(json_str)
    except:
        json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
        try:
            return json.loads(json_str)
        except:
            return None

# Initialize GraphSchema
class GraphSchema:
    """Strict schema enforcement for Karaka knowledge graph"""

    NODE_TYPES = set(CONFIG['graph_schema']['node_types'])

    EDGE_RELATIONS = set(CONFIG['graph_schema']['edge_relations'])

    def validate_node(self, node_id: str, attrs: dict) -> bool:
        """Validate node has required type attribute"""
        if not attrs:
            print(f"❌ Schema violation: Node {node_id} has no attributes")
            return False

        node_type = attrs.get("type") or attrs.get("node_type")
        if not node_type:
            print(f"❌ Schema violation: Node {node_id} missing 'type' attribute")
            return False

        if node_type not in self.NODE_TYPES:
            print(f"❌ Schema violation: Node {node_id} has invalid type '{node_type}'. Must be one of {self.NODE_TYPES}")
            return False

        return True

    def validate_edge(self, source: str, target: str, relation: str) -> bool:
        """Validate edge has valid relation attribute"""
        if not relation:
            print(f"❌ Schema violation: Edge {source} → {target} missing 'relation' attribute")
            return False

        if relation not in self.EDGE_RELATIONS:
            print(f"❌ Schema violation: Edge {source} → {target} has invalid relation '{relation}'. Must be one of {self.EDGE_RELATIONS}")
            return False

        return True

# Initialize FAISS Vector Store
class FAISSVectorStore:
    """Wrapper for FAISS index with document ID mapping"""

    def __init__(self, dimension: int = None):
        self.dimension = dimension or CONFIG['faiss']['dimension']
        self.index = faiss.IndexFlatL2(self.dimension)
        self.doc_id_map = []
        self.doc_id_to_idx = {}

    def add(self, doc_id: str, embedding: np.ndarray) -> None:
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        embedding = embedding.astype('float32')

        idx = len(self.doc_id_map)
        self.index.add(embedding)
        self.doc_id_map.append(doc_id)
        self.doc_id_to_idx[doc_id] = idx

    def query_nearby(self, doc_id: str, k: int = None) -> List[str]:
        if k is None:
            k = CONFIG['faiss']['nearby_k']
        if doc_id not in self.doc_id_to_idx:
            return []

        idx = self.doc_id_to_idx[doc_id]
        query_vector = self.index.reconstruct(idx).reshape(1, -1)
        distances, indices = self.index.search(query_vector, k + 1)

        nearby_doc_ids = []
        for i in indices[0]:
            if i < len(self.doc_id_map) and self.doc_id_map[i] != doc_id:
                nearby_doc_ids.append(self.doc_id_map[i])
                if len(nearby_doc_ids) >= k:
                    break

        return nearby_doc_ids

    def size(self) -> int:
        return self.index.ntotal

print("✅ NetworkX MultiDiGraph initialized")
print("✅ GraphSchema loaded")
print("✅ FAISSVectorStore initialized")


# ============================================================================
# CELL 4: Load Prompts from prompts.yaml
# ============================================================================

# Load prompts from YAML only
def load_yaml_prompts(filepath: str = None) -> dict:
    """Load all prompts from YAML file"""
    if filepath is None:
        filepath = CONFIG['file_paths'].get('prompts_yaml_file', 'prompts.yaml')
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            prompts = yaml.safe_load(f)
            # Filter out placeholder values
            return {k: v for k, v in prompts.items() if v != "LOAD_FROM_PROMPTS_JSON"}
    return {}

PROMPTS = load_yaml_prompts()
print(f"✅ Loaded {len(PROMPTS)} prompts from prompts.yaml")


# ============================================================================
# CELL 5: Entity Resolution
# ============================================================================
class EntityResolver:
    def __init__(self, embedding_model, embedding_tokenizer, threshold: float = None):
        self.model = embedding_model
        self.tokenizer = embedding_tokenizer
        self.threshold = threshold if threshold is not None else CONFIG['entity_resolution']['similarity_threshold']
        self.entity_registry = {}
        self.entity_map = {}

    def encode(self, text: str) -> np.ndarray:
        """Encode text using NVIDIA embedding model."""
        inputs = self.tokenizer([text], padding=True, truncation=True, return_tensors='pt')
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.model(**inputs)
        embedding = average_pool(outputs.last_hidden_state, inputs["attention_mask"])
        return embedding.cpu().numpy()[0]

    def resolve_entity(self, mention: str) -> str:
        mention = mention.strip()
        if mention in self.entity_map:
            return self.entity_map[mention]
        mention_lower = mention.lower()
        if mention_lower in self.entity_map:
            return self.entity_map[mention_lower]

        mention_embedding = self.encode(mention)
        best_match = None
        best_score = 0.0

        for canonical_name, canonical_embedding in self.entity_registry.items():
            similarity = np.dot(mention_embedding, canonical_embedding) / (
                np.linalg.norm(mention_embedding) * np.linalg.norm(canonical_embedding)
            )
            if similarity > best_score:
                best_score = similarity
                best_match = canonical_name

        if best_score >= self.threshold and best_match:
            self.entity_map[mention] = best_match
            return best_match

        canonical_name = mention
        self.entity_registry[canonical_name] = mention_embedding
        self.entity_map[mention] = canonical_name
        return canonical_name

print("✅ Entity resolver loaded")


# ============================================================================
# CELL 6: GSV-Retry Engine
# ============================================================================
class GSVRetryEngine:
    """Generate-Score-Verify-Retry engine for robust extraction with cross-validation"""

    def __init__(self, model, tokenizer, prompts: dict, max_retries: int = None, scoring_ensemble_size: int = None, logger=None):
        """Initialize GSV-Retry engine

        Args:
            model: LLM model for generation
            tokenizer: Tokenizer for the model
            prompts: Dictionary of prompts (extraction, scoring, verification, feedback)
            max_retries: Maximum retry attempts (default from config)
            scoring_ensemble_size: Number of scoring calls per candidate (default from config)
            logger: OptimizationLogger instance for tracking performance
        """
        self.model = model
        self.tokenizer = tokenizer
        self.prompts = prompts
        self.max_retries = max_retries if max_retries is not None else CONFIG['gsv_retry']['max_retries']
        self.scoring_ensemble_size = scoring_ensemble_size if scoring_ensemble_size is not None else CONFIG['gsv_retry']['scoring_ensemble_size']
        self.logger = logger
        self.failure_stats = {
            'total_attempts': 0,
            'total_failures': 0,
            'failure_reasons': defaultdict(int)
        }

    def extract_with_retry(self, text: str, extraction_type: str = "kriya", line_ref: str = "") -> Optional[Dict]:
        """Main GSV-Retry loop with fast-path optimization

        OPTIMIZATION: With reasoning mode enabled, this now does single-shot extraction
        with internal verification, reducing from 13+ calls to 1 call per extraction.

        Args:
            text: Input text to extract from
            extraction_type: Type of extraction ("kriya" or "query")
            line_ref: Reference for logging (e.g., "doc1_L5")

        Returns:
            Golden Candidate dict or None if all retries exhausted
        """
        import time
        start_time = time.time()

        # PHASE 3: Single-shot extraction with reasoning mode
        if CONFIG.get('reasoning', {}).get('enabled', False) and self.max_retries == 1:
            result = self._extract_single_shot_optimized(text, extraction_type, line_ref)

            # Log performance
            if self.logger:
                duration = time.time() - start_time
                self.logger.log_extraction(text, result, duration, llm_calls=1, mode="single_shot")

            return result

        # Legacy GSV-Retry path (fallback)
        self.failure_stats['total_attempts'] += 1
        feedback_prompt = ""
        failure_log = []
        llm_calls_made = 0

        # Select prompts based on extraction type
        if extraction_type == "kriya":
            base_prompt = self.prompts.get("kriya_extraction_prompt", "")
            feedback_template = self.prompts.get("kriya_extraction_feedback_prompt", "")
            scoring_prompt = self.prompts.get("kriya_scoring_prompt", "")
            verification_prompt = self.prompts.get("kriya_verification_prompt", "")
        else:  # query
            base_prompt = self.prompts.get("query_decomposition_prompt", "")
            feedback_template = self.prompts.get("query_decomposition_prompt", "")  # Reuse for now
            scoring_prompt = self.prompts.get("query_scoring_prompt", "")
            verification_prompt = self.prompts.get("query_verification_prompt", "")

        for attempt in range(self.max_retries):
            print(f"        🔄 Attempt {attempt + 1}/{self.max_retries}...", end=" ", flush=True)

            # GENERATE: 3 candidates (isolated LLM calls)
            print("Gen", end="", flush=True)
            candidates = self._generate_candidates(text, base_prompt, feedback_prompt)
            llm_calls_made += CONFIG['gsv_retry']['num_candidates']

            # DEBUG: Show all candidates on first attempt
            if attempt == 0 and candidates:
                print(f"\n          📋 All {len(candidates)} candidates:")
                for c in candidates:
                    print(f"            {c['id']}: {json.dumps(c['data'], ensure_ascii=False)}")
                print("          ", end="", flush=True)

            if not candidates:
                print(" ❌ No candidates")
                feedback_prompt = "Previous attempt produced no valid candidates. Please ensure JSON output is valid."
                failure_log.append({
                    "attempt": attempt + 1,
                    "error": "No valid candidates generated",
                    "feedback": feedback_prompt
                })
                continue

            print(f"({len(candidates)})", end=" ", flush=True)

            # FAST-PATH: Score only first candidate initially
            print("Score", end="", flush=True)
            first_score = self._get_robust_score(candidates[0], scoring_prompt)
            llm_calls_made += self.scoring_ensemble_size
            print(f"({first_score:.0f})", end=" ", flush=True)

            if first_score >= 95:
                # High confidence - verify immediately (fast path: 4 LLM calls total)
                print("FastVerify", end="", flush=True)
                verifier_choice = self._get_blind_verification([candidates[0]], verification_prompt, text)
                if verifier_choice == candidates[0]["id"]:
                    print(" ✅ Fast-path success!")
                    return candidates[0]  # Fast-path success
                print(f"({verifier_choice})", end=" ", flush=True)

            # FULL-PATH: Score all candidates
            scores = [first_score] + [self._get_robust_score(c, scoring_prompt) for c in candidates[1:]]
            llm_calls_made += (len(candidates) - 1) * self.scoring_ensemble_size
            print(f"AllScores{scores}", end=" ", flush=True)

            # VERIFY: Blind verification
            print("Verify", end="", flush=True)
            verifier_choice = self._get_blind_verification(candidates, verification_prompt, text)
            llm_calls_made += 1
            print(f"({verifier_choice})", end=" ", flush=True)

            # CROSS-VALIDATE
            highest_idx = scores.index(max(scores))
            highest_id = candidates[highest_idx]["id"]
            if highest_id == verifier_choice:
                print(f"✅ Match! {highest_id}")
                result = candidates[highest_idx]

                # Log performance
                if self.logger:
                    duration = time.time() - start_time
                    self.logger.log_extraction(text, result, duration, llm_calls=llm_calls_made, mode="gsv_retry")

                return result  # Golden Candidate found

            print(f"❌ Mismatch: Score→{highest_id} vs Verify→{verifier_choice}")

            # FEEDBACK for retry
            feedback_prompt = self._generate_feedback(
                candidates, scores, verifier_choice, feedback_template
            )
            failure_log.append({
                "attempt": attempt + 1,
                "candidates": [c["id"] for c in candidates],
                "scores": scores,
                "verifier_choice": verifier_choice,
                "feedback": feedback_prompt
            })

        # Failed after max_retries
        self._log_failure(text, failure_log, line_ref, extraction_type)
        self.failure_stats['total_failures'] += 1
        self.failure_stats['failure_reasons']['max_retries_exhausted'] += 1

        # Log failure
        if self.logger:
            duration = time.time() - start_time
            self.logger.log_extraction(text, None, duration, llm_calls=llm_calls_made, mode="gsv_retry")

        return None

    def _generate_candidates(self, text: str, base_prompt: str, feedback: str) -> List[Dict]:
        """Generate 3 candidates via isolated LLM calls

        Args:
            text: Input text
            base_prompt: Base extraction prompt
            feedback: Feedback from previous iteration

        Returns:
            List of candidate dicts with id, data, raw_response
        """
        candidates = []
        full_prompt = base_prompt + ("\n\n" + feedback if feedback else "")

        num_candidates = CONFIG['gsv_retry']['num_candidates']
        for i in range(num_candidates):
            print(".", end="", flush=True)
            try:
                response = call_llm_isolated(
                    system_prompt=full_prompt,
                    user_prompt=text,
                    model=self.model,
                    tokenizer=self.tokenizer,
                    temperature=CONFIG['gsv_retry']['generation_temperature']
                )

                # DEBUG: Show raw response if parsing fails
                parsed_data = parse_json_response(response)
                if not parsed_data and i == 0:
                    print(f"\n          ⚠️ Raw response: {response[:200]}", end="", flush=True)

                if parsed_data:
                    # Keep the full structure with extractions array
                    # Normalize to {"extractions": [...]} format
                    if isinstance(parsed_data, list):
                        # Direct list format
                        parsed_data = {"extractions": parsed_data}
                    elif isinstance(parsed_data, dict) and "verb" in parsed_data:
                        # Single extraction format - wrap in array
                        parsed_data = {"extractions": [parsed_data]}

                    # Validate we have extractions
                    if isinstance(parsed_data, dict) and "extractions" in parsed_data:
                        extractions = parsed_data["extractions"]
                        if isinstance(extractions, list) and len(extractions) > 0:
                            # Validate karakas values are strings, not arrays
                            valid = True
                            for ext in extractions:
                                if "karakas" in ext:
                                    for role, value in ext["karakas"].items():
                                        if isinstance(value, list):
                                            print(f"⚠️", end="", flush=True)
                                            valid = False
                                            break

                            if valid:
                                candidates.append({
                                    "id": f"Candidate_{chr(65+i)}",  # A, B, C
                                    "data": parsed_data,
                                    "raw_response": response
                                })
            except Exception as e:
                print(f"      ⚠️ Candidate {chr(65+i)} generation failed: {e}")
                continue

        return candidates

    def _get_robust_score(self, candidate: Dict, scoring_prompt: str) -> float:
        """Ensemble scoring with configurable calls and validation

        Args:
            candidate: Candidate dict to score
            scoring_prompt: Scoring prompt template

        Returns:
            Average score (1-100)
        """
        scores = []

        for attempt in range(self.scoring_ensemble_size):
            print(".", end="", flush=True)
            try:
                response = call_llm_isolated(
                    system_prompt=scoring_prompt,
                    user_prompt=json.dumps(candidate["data"], indent=2),
                    model=self.model,
                    tokenizer=self.tokenizer,
                    temperature=CONFIG['gsv_retry']['scoring_temperature']
                )

                score_data = parse_json_response(response)
                if score_data and isinstance(score_data, dict):
                    score = self._validate_score(score_data.get("score"))
                    if score is not None:
                        scores.append(score)
            except Exception as e:
                print(f"\n      ⚠️ Scoring attempt {attempt+1} failed: {e}")
                continue

        # Return average or default low score if all failed
        return sum(scores) / len(scores) if scores else 1.0

    def _validate_score(self, score) -> Optional[int]:
        """Validate score is integer 1-100

        Args:
            score: Score value to validate

        Returns:
            Valid score or None
        """
        try:
            score_int = int(score)
            if 1 <= score_int <= 100:
                return score_int
        except (TypeError, ValueError):
            pass
        return None

    def _get_blind_verification(self, candidates: List[Dict], verification_prompt: str, original_text: str) -> str:
        """Single blind verification call

        Args:
            candidates: List of candidates to verify
            verification_prompt: Verification prompt
            original_text: Original input text for hallucination checking

        Returns:
            Candidate ID (e.g., "Candidate_A") or "ALL_INVALID"
        """
        try:
            # Build context with original text and candidates
            # Extract the first extraction from each candidate's data
            context = {
                "original_text": original_text,
                "candidates": [
                    {
                        "id": c["id"],
                        "extraction": c["data"]["extractions"][0] if isinstance(c["data"], dict) and "extractions" in c["data"] and len(c["data"]["extractions"]) > 0 else c["data"]
                    }
                    for c in candidates
                ]
            }

            context_str = json.dumps(context, indent=2)

            # DEBUG: Show what we're sending to verifier (first time only)
            if CONFIG['display']['show_verifier_input'] and not hasattr(self, '_debug_shown'):
                print(f"\n          📤 Verifier input (full):")
                print(context_str)
                self._debug_shown = True

            response = call_llm_isolated(
                system_prompt=verification_prompt,
                user_prompt=context_str,
                model=self.model,
                tokenizer=self.tokenizer,
                temperature=CONFIG['gsv_retry']['verification_temperature']
            )

            # DEBUG: Show raw verifier response
            if CONFIG['display']['show_debug_output']:
                print(f"\n          🔍 Verifier raw: {response[:200]}...", end="", flush=True)

            result = parse_json_response(response)
            if result and isinstance(result, dict):
                choice = result.get("choice", "ALL_INVALID")
                reasoning = result.get("reasoning", "No reasoning")
                print(f"\n          🔍 Parsed choice: {choice}, reason: {reasoning[:80]}...", end="", flush=True)
                return choice
            else:
                print(f"\n          ⚠️ Verifier returned invalid JSON: {result}", end="", flush=True)
        except Exception as e:
            print(f"\n      ⚠️ Verification failed: {e}")

        return "ALL_INVALID"

    def _generate_feedback(self, candidates: List[Dict], scores: List[float],
                          verifier_choice: str, feedback_template: str) -> str:
        """Generate feedback for next retry iteration

        Args:
            candidates: List of candidates
            scores: List of scores
            verifier_choice: Verifier's choice
            feedback_template: Feedback prompt template

        Returns:
            Feedback string for next iteration
        """
        if verifier_choice == "ALL_INVALID":
            feedback = "Retry: All previous candidates were invalid. The verifier found issues with all extractions. Please generate new, valid options with correct structure and semantic roles."
        else:
            highest_idx = scores.index(max(scores))
            highest_candidate = candidates[highest_idx]["id"]
            feedback = f"Retry: The quantitative score favored {highest_candidate} (score: {scores[highest_idx]:.1f}), but the qualitative verifier chose {verifier_choice}. Please re-evaluate and ensure both semantic correctness and structural validity."

        # Use template if available
        if feedback_template and "{feedback}" in feedback_template:
            return feedback_template.format(feedback=feedback)

        return feedback

    def _extract_single_shot_optimized(self, text: str, extraction_type: str, line_ref: str) -> Optional[Dict]:
        """Single-shot extraction using reasoning mode (Phase 3 optimization)

        Args:
            text: Input text
            extraction_type: "kriya" or "query"
            line_ref: Line reference

        Returns:
            Extraction dict or None
        """
        print(f"        🎯 Single-shot ({extraction_type})...", end=" ", flush=True)

        # Select prompt
        if extraction_type == "kriya":
            system_prompt = self.prompts.get("kriya_extraction_single_shot_prompt",
                                            self.prompts.get("kriya_extraction_prompt", ""))
        else:
            system_prompt = self.prompts.get("query_decomposition_single_shot_prompt",
                                            self.prompts.get("query_decomposition_prompt", ""))

        try:
            if CONFIG['display'].get('show_extraction_details', False):
                print(f"\n          📤 Extracting from: {text[:100]}...")

            response = call_llm_isolated(
                system_prompt=system_prompt,
                user_prompt=text,
                model=self.model,
                tokenizer=self.tokenizer,
                reasoning_mode="on",
                temperature=0.6
            )

            if CONFIG['display'].get('show_extraction_details', False):
                print(f"\n          📥 Response ({len(response)} chars): {response[:200]}...")

            parsed = parse_json_response(response)

            if not parsed:
                print("❌ Parse failed")
                self.failure_stats['total_failures'] += 1
                self.failure_stats['failure_reasons']['parse_error'] += 1
                return None

            # Handle different response formats
            # Case 1: Direct list format (wrong but handle it)
            if isinstance(parsed, list):
                print("⚠️ Got list, wrapping...")
                parsed = {"extractions": parsed, "confidence": 0.7}

            # Case 2: Single extraction dict (wrap in array)
            if isinstance(parsed, dict) and "verb" in parsed and "extractions" not in parsed:
                print("⚠️ Single extraction, wrapping...")
                parsed = {"extractions": [parsed], "confidence": parsed.get("confidence", 0.7)}

            # Extract confidence
            confidence = parsed.get("confidence", 0.5)

            # Validate structure
            if extraction_type == "kriya":
                if "extractions" not in parsed or not isinstance(parsed["extractions"], list):
                    print(f"❌ Invalid structure: {type(parsed)}, keys: {parsed.keys() if isinstance(parsed, dict) else 'N/A'}")
                    self.failure_stats['total_failures'] += 1
                    self.failure_stats['failure_reasons']['invalid_structure'] += 1
                    return None

                if len(parsed["extractions"]) == 0:
                    print("⚠️ No extractions")
                    return None

            # Check confidence threshold
            threshold = CONFIG.get('reasoning', {}).get('confidence_threshold', 0.85)
            if confidence < threshold:
                print(f"⚠️ Low confidence ({confidence:.2f})")
                self.failure_stats['total_failures'] += 1
                self.failure_stats['failure_reasons']['low_confidence'] += 1
                return None

            print(f"✅ Conf: {confidence:.2f}")

            # Wrap in candidate format for compatibility
            return {
                "id": "SingleShot",
                "data": parsed,
                "raw_response": response
            }

        except Exception as e:
            print(f"❌ Error: {e}")
            self.failure_stats['total_failures'] += 1
            self.failure_stats['failure_reasons']['exception'] += 1
            return None

    def _log_failure(self, text: str, failure_log: List[Dict], line_ref: str, extraction_type: str):
        """Log detailed failure diagnostics

        Args:
            text: Original input text
            failure_log: List of failure attempt details
            line_ref: Line reference for context
            extraction_type: Type of extraction
        """
        max_preview = CONFIG['display']['max_text_preview_length']
        print(f"\n      ❌ GSV-Retry FAILED after {self.max_retries} attempts at {line_ref}")
        print(f"      Text: \"{text[:max_preview]}...\"" if len(text) > max_preview else f"      Text: \"{text}\"")
        print(f"      Type: {extraction_type}")
        print(f"      Failure log:")

        for entry in failure_log:
            print(f"        Attempt {entry['attempt']}:")
            if 'error' in entry:
                print(f"          Error: {entry['error']}")
            else:
                print(f"          Candidates: {entry.get('candidates', [])}")
                print(f"          Scores: {[f'{s:.1f}' for s in entry.get('scores', [])]}")
                print(f"          Verifier: {entry.get('verifier_choice', 'N/A')}")
            print(f"          Feedback: {entry.get('feedback', 'N/A')[:100]}...")

    def get_failure_stats(self) -> Dict:
        """Get failure statistics

        Returns:
            Dict with failure stats
        """
        return {
            'total_attempts': self.failure_stats['total_attempts'],
            'total_failures': self.failure_stats['total_failures'],
            'success_rate': (self.failure_stats['total_attempts'] - self.failure_stats['total_failures']) / self.failure_stats['total_attempts'] if self.failure_stats['total_attempts'] > 0 else 0,
            'failure_reasons': dict(self.failure_stats['failure_reasons'])
        }

print("✅ GSVRetryEngine class defined")


# ============================================================================
# CELL 7: Kāraka Knowledge Graph (with Schema Enforcement)
# ============================================================================
class KarakaGraphV2:
    """Enhanced Karaka Graph with strict schema validation and FAISS integration"""

    def __init__(self, embedding_model, embedding_tokenizer):
        """Initialize graph with schema enforcement and vector store

        Args:
            embedding_model: Model for entity resolution embeddings
            embedding_tokenizer: Tokenizer for embedding model
        """
        self.graph = nx.MultiDiGraph()
        self.schema = GraphSchema()
        self.vector_store = FAISSVectorStore(dimension=2048)
        self.entity_resolver = EntityResolver(embedding_model, embedding_tokenizer)

        # Indexes for fast lookup
        self.documents = {}
        self.kriyas = {}
        self.kriya_index = defaultdict(list)
        self.entity_index = defaultdict(list)

    def add_document_node(self, doc_id: str, line_number: int, text: str) -> str:
        """Add Document node with schema validation

        Args:
            doc_id: Document identifier
            line_number: Line number in document
            text: Original text content

        Returns:
            Node ID (format: {doc_id}_L{line_number})
        """
        node_id = f"{doc_id}_L{line_number}"
        attrs = {
            "type": "Document",
            "doc_id": doc_id,
            "line_number": line_number,
            "text": text
        }

        # Schema validation
        if not self.schema.validate_node(node_id, attrs):
            raise ValueError(f"Schema validation failed for Document node {node_id}")

        self.graph.add_node(node_id, **attrs)
        self.documents[node_id] = attrs

        return node_id

    def add_kriya_node(self, verb: str, doc_id: str, line_number: int) -> str:
        """Add Kriyā node with schema validation

        Args:
            verb: Verb/action
            doc_id: Source document ID
            line_number: Source line number

        Returns:
            Node ID (format: {doc_id}_L{line_number}_K{sequence})
        """
        sequence = len([k for k in self.kriyas.keys() if k.startswith(f"{doc_id}_L{line_number}_K")])
        node_id = f"{doc_id}_L{line_number}_K{sequence}"

        attrs = {
            "type": "Kriya",
            "verb": verb,
            "doc_id": doc_id,
            "line_number": line_number
        }

        # Schema validation
        if not self.schema.validate_node(node_id, attrs):
            raise ValueError(f"Schema validation failed for Kriya node {node_id}")

        self.graph.add_node(node_id, **attrs)
        self.kriyas[node_id] = attrs
        self.kriya_index[verb].append(node_id)

        return node_id

    def add_entity_node(self, canonical_name: str) -> str:
        """Add Entity node with schema validation (idempotent)

        Args:
            canonical_name: Canonical entity name (used as node ID)

        Returns:
            Node ID (canonical_name)
        """
        node_id = canonical_name

        # Check if already exists
        if node_id in self.graph:
            return node_id

        attrs = {
            "type": "Entity",
            "canonical_name": canonical_name
        }

        # Schema validation
        if not self.schema.validate_node(node_id, attrs):
            raise ValueError(f"Schema validation failed for Entity node {node_id}")

        self.graph.add_node(node_id, **attrs)

        return node_id

    def add_edge(self, source: str, target: str, relation: str, **attrs) -> None:
        """Add edge with schema validation

        Args:
            source: Source node ID
            target: Target node ID
            relation: Relation type (must be in schema)
            **attrs: Additional edge attributes
        """
        # Schema validation
        if not self.schema.validate_edge(source, target, relation):
            raise ValueError(f"Schema validation failed for edge {source} → {target} with relation {relation}")

        # Add relation to attrs
        attrs['relation'] = relation

        self.graph.add_edge(source, target, **attrs)

        # Update entity index if this is a kāraka relation
        if relation in ["HAS_KARTĀ", "HAS_KARMA", "USES_KARANA", "TARGETS_SAMPRADĀNA",
                       "FROM_APĀDĀNA", "LOCATED_IN", "OCCURS_AT"] and source in self.kriyas:
            self.entity_index[target].append(source)

    def traverse(self, start_node: str, edge_filter: Optional[List[str]] = None,
                max_hops: int = None, direction: str = None) -> List[str]:
        """Multi-hop graph traversal with edge filtering

        Args:
            start_node: Starting node ID
            edge_filter: List of relation types to follow (None = all)
            max_hops: Maximum traversal depth
            direction: "out" (outgoing), "in" (incoming), or "both"

        Returns:
            List of reachable node IDs
        """
        if max_hops is None:
            max_hops = CONFIG['graph_traversal']['max_hops']
        if direction is None:
            direction = CONFIG['graph_traversal']['default_direction']

        if start_node not in self.graph:
            return []

        visited = set()
        current_level = {start_node}

        for hop in range(max_hops):
            next_level = set()

            for node in current_level:
                if node in visited:
                    continue
                visited.add(node)

                # Get neighbors based on direction
                if direction in ["out", "both"]:
                    for _, target, data in self.graph.out_edges(node, data=True):
                        if edge_filter is None or data.get('relation') in edge_filter:
                            next_level.add(target)

                if direction in ["in", "both"]:
                    for source, _, data in self.graph.in_edges(node, data=True):
                        if edge_filter is None or data.get('relation') in edge_filter:
                            next_level.add(source)

            current_level = next_level

            if not current_level:
                break

        return list(visited)

    def get_cited_documents(self, kriya_ids: List[str]) -> List[Dict]:
        """Retrieve Document node texts for given Kriyā nodes

        Args:
            kriya_ids: List of Kriyā node IDs

        Returns:
            List of dicts with doc_id, line_number, text
        """
        documents = []

        for kriya_id in kriya_ids:
            if kriya_id not in self.graph:
                continue

            # Follow CITED_IN edges
            for _, target, data in self.graph.out_edges(kriya_id, data=True):
                if data.get('relation') == 'CITED_IN' and target in self.documents:
                    doc_attrs = self.graph.nodes[target]
                    documents.append({
                        'doc_id': doc_attrs['doc_id'],
                        'line_number': doc_attrs['line_number'],
                        'text': doc_attrs['text']
                    })

        return documents

    def get_neighbors(self, node_id: str, relation: Optional[str] = None,
                     direction: str = "out") -> List[str]:
        """Get neighbors of a node with optional relation filter

        Args:
            node_id: Node ID
            relation: Relation type filter (None = all)
            direction: "out", "in", or "both"

        Returns:
            List of neighbor node IDs
        """
        if node_id not in self.graph:
            return []

        neighbors = []

        if direction in ["out", "both"]:
            for _, target, data in self.graph.out_edges(node_id, data=True):
                if relation is None or data.get('relation') == relation:
                    neighbors.append(target)

        if direction in ["in", "both"]:
            for source, _, data in self.graph.in_edges(node_id, data=True):
                if relation is None or data.get('relation') == relation:
                    neighbors.append(source)

        return neighbors

    def find_kriyas(self, verb: Optional[str] = None, **karaka_constraints) -> List[str]:
        """Find Kriyā nodes matching verb and kāraka constraints

        Args:
            verb: Verb to match (None = any)
            **karaka_constraints: Kāraka constraints (e.g., KARTA="Rama")

        Returns:
            List of matching Kriyā node IDs
        """
        # Start with verb filter if provided
        if verb:
            candidate_ids = self.kriya_index.get(verb, [])
        else:
            candidate_ids = list(self.kriyas.keys())

        # Apply kāraka constraints
        results = []
        for kriya_id in candidate_ids:
            match = True

            for karaka_type, required_entity in karaka_constraints.items():
                if not required_entity:
                    continue

                # Resolve entity
                canonical = self.entity_resolver.resolve_entity(required_entity)

                # Map kāraka type to relation
                relation_map = CONFIG['karaka_relation_mapping']
                relation = relation_map.get(karaka_type, karaka_type)

                # Check if edge exists (FROM Kriyā TO Entity)
                edges = [e for e in self.graph.out_edges(kriya_id, data=True)
                        if e[1] == canonical and e[2].get('relation') == relation]

                if not edges:
                    match = False
                    break

            if match:
                results.append(kriya_id)

        return results

    def get_citation(self, kriya_id: str) -> Optional[Citation]:
        """Get citation for a Kriyā node

        Args:
            kriya_id: Kriyā node ID

        Returns:
            Citation object or None
        """
        if kriya_id not in self.kriyas:
            return None

        kriya_attrs = self.graph.nodes[kriya_id]

        # Find cited document
        doc_node_id = f"{kriya_attrs['doc_id']}_L{kriya_attrs['line_number']}"
        if doc_node_id in self.documents:
            doc_attrs = self.graph.nodes[doc_node_id]
            return Citation(
                document_id=doc_attrs['doc_id'],
                line_number=doc_attrs['line_number'],
                original_text=doc_attrs['text']
            )

        return None

    def save_to_file(self, filepath: str):
        """Save graph to JSON file"""
        data = {
            'documents': self.documents,
            'kriyas': self.kriyas,
            'kriya_index': dict(self.kriya_index),
            'entity_index': dict(self.entity_index),
            'entity_map': self.entity_resolver.entity_map,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_kriyas': len(self.kriyas),
                'total_entities': len([n for n in self.graph.nodes() if self.graph.nodes[n].get('type') == 'Entity']),
                'total_documents': len(self.documents)
            }
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Graph saved to {filepath}")

    def export_visualization(self, filepath: str):
        """Export graph to GEXF format for visualization"""
        nx.write_gexf(self.graph, filepath)
        print(f"✅ Graph exported to {filepath}")

print("✅ KarakaGraphV2 class defined")


# ============================================================================
# CELL 8: Ingestion Pipeline Class Definition
# ============================================================================
class IngestionPipeline:
    """Orchestrates document loading, embedding, extraction, and post-processing"""

    def __init__(self, graph: KarakaGraphV2, gsv_engine: GSVRetryEngine, embedding_model, embedding_tokenizer):
        """Initialize ingestion pipeline

        Args:
            graph: KarakaGraphV2 instance
            gsv_engine: GSVRetryEngine instance
            embedding_model: Model for document embeddings
            embedding_tokenizer: Tokenizer for embedding model
        """
        self.graph = graph
        self.gsv_engine = gsv_engine
        self.embedding_model = embedding_model
        self.embedding_tokenizer = embedding_tokenizer

        # Statistics
        self.stats = {
            'total_lines': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'total_kriyas': 0,
            'total_entities': 0,
            'total_edges': 0
        }

    def ingest_documents(self, docs_folder: str = "./test_documents", run_postprocessing: bool = True):
        """Main ingestion orchestrator

        Args:
            docs_folder: Path to folder containing documents
            run_postprocessing: Whether to run post-processing steps (default True)
        """
        print(f"\n{'='*80}")
        print(f"INGESTION PIPELINE")
        print(f"{'='*80}")

        # Step 1: Load and embed documents
        print(f"\n📄 Step 1: Loading and embedding documents...")
        refined_docs = self._load_documents(docs_folder)
        if not refined_docs:
            print("❌ No documents loaded. Aborting ingestion.")
            return

        self._embed_and_store(refined_docs)

        # Step 2: Extract Kriyās with GSV-Retry
        print(f"\n🔍 Step 2: Extracting Kriyās with GSV-Retry...")
        self._extract_kriyas(refined_docs)

        # Step 3: Post-processing (optional)
        if run_postprocessing:
            self.run_post_processing()

        # Print final statistics
        self._print_statistics()

    def _load_documents(self, docs_folder: str) -> Dict[str, List[str]]:
        """Load documents from folder and split into sentences using robust LLM pipeline

        Args:
            docs_folder: Path to folder containing documents

        Returns:
            Dict mapping doc_id to list of sentences
        """
        if not os.path.exists(docs_folder):
            print(f"❌ ERROR: Document folder '{docs_folder}' not found!")
            return {}

        text_files = list(Path(docs_folder).glob("*.txt")) + list(Path(docs_folder).glob("*.md"))
        if not text_files:
            print(f"❌ ERROR: No .txt or .md files found in '{docs_folder}'")
            return {}

        print(f"   Found {len(text_files)} document(s)")

        # Get processed folder from config
        processed_folder = Path(CONFIG['file_paths'].get('processed_folder', './data/processed'))
        processed_folder.mkdir(parents=True, exist_ok=True)

        refined_docs = {}

        for filepath in text_files:
            doc_path = Path(filepath)
            doc_id = doc_path.stem
            processed_file = processed_folder / f"{doc_id}_processed.txt"

            print(f"   📄 {doc_path.name}")

            # Check if processed file exists
            if processed_file.exists():
                print(f"      ✓ Loading from processed file: {processed_file.name}")
                with open(processed_file, 'r', encoding='utf-8') as f:
                    sentences = [line.strip() for line in f.readlines() if line.strip()]
            else:
                # Read original content
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                # Use pipeline from sentence_split_pipeline.md
                sentences = self._split_document_pipeline(content)

                # Save processed sentences (strip leading/trailing whitespace from each)
                with open(processed_file, 'w', encoding='utf-8') as f:
                    for sent in sentences:
                        # Strip only leading/trailing whitespace, preserve internal spacing
                        cleaned = sent.strip()
                        if cleaned:  # Skip empty lines
                            f.write(cleaned + '\n')
                print(f"      ✓ Saved to: {processed_file.name}")

            refined_docs[doc_id] = sentences
            print(f"      ✓ Loaded {len(sentences)} sentence(s)")

        return refined_docs

    # ========================================================================
    # SENTENCE SPLITTING PIPELINE (sentence_split_pipeline.md)
    # ========================================================================

    # Configuration loaded from config.yaml
    SENTENCE_SPLIT_CONFIG = CONFIG['sentence_split']

    def _count_tokens(self, text: str) -> int:
        """Get exact token count using the actual tokenizer"""
        if not text:
            return 0
        try:
            tokens = self.gsv_engine.tokenizer.encode(text, add_special_tokens=False)
            return len(tokens)
        except Exception as e:
            # Fallback to rough estimate if tokenizer fails
            print(f"[TokenizerError:{str(e)[:30]}]", end=" ")
            return len(text) // 4

    def _split_document_pipeline(self, document: str) -> List[str]:
        """Main pipeline: Split document → paragraphs → process with overlap

        Follows sentence_split_pipeline.md flowchart
        """
        print(f"\n      🔄 Pipeline: Splitting document...")

        # Step 1: Split into paragraphs
        paragraphs = document.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        print(f"      📦 Found {len(paragraphs)} paragraph(s)")

        all_sentences = []

        for p_idx, paragraph in enumerate(paragraphs, 1):
            token_count = self._count_tokens(paragraph)
            print(f"      📝 P{p_idx}/{len(paragraphs)} ({token_count} tokens)...", end=" ")

            # Step 2: Route based on length
            if token_count <= self.SENTENCE_SPLIT_CONFIG['max_paragraph_tokens']:
                print("(single)", end=" ")
                sentences = self._process_paragraph_single(paragraph, p_idx)
            else:
                print("(chunked)", end=" ")
                sentences = self._process_paragraph_chunked(paragraph, p_idx)

            if sentences:
                print(f"✅ {len(sentences)} sentences")
                all_sentences.extend(sentences)
            else:
                print("❌ Failed, using fallback")
                all_sentences.extend(self._fallback_sentence_split(paragraph))

        return all_sentences

    def _process_paragraph_single(self, paragraph: str, p_idx: int) -> List[str]:
        """Process paragraph in one LLM call with fidelity check & self-correction"""
        max_retries = self.SENTENCE_SPLIT_CONFIG['max_retries']
        feedback = None

        if CONFIG['display'].get('show_split_details', False):
            print(f"\n       📝 Processing paragraph {p_idx} ({len(paragraph)} chars)")
            print(f"          Text: {paragraph[:150]}...")

        for attempt in range(max_retries + 1):
            if attempt > 0:
                print(f"\n         🔄 Retry {attempt}/{max_retries}", end=" ")

            # LLM: Propose sentences
            proposed = self._llm_propose_sentences(paragraph, feedback)
            if not proposed:
                print(f"[P{p_idx}A{attempt}:NoProposal]", end=" ")
                continue

            print(f"[P{p_idx}A{attempt}:Proposed={len(proposed)}]", end=" ")

            # Align & Extract exact substrings
            aligned = self._align_and_reconstruct(paragraph, proposed)
            if not aligned:
                print(f"[P{p_idx}A{attempt}:AlignFail]", end=" ")
                # Generate feedback for retry
                feedback = self._generate_alignment_feedback(paragraph, proposed)
                continue

            print(f"[P{p_idx}A{attempt}:Aligned={len(aligned)}]", end=" ")

            # Fidelity check
            if self._verify_exact_fidelity(paragraph, aligned):
                print(f"[P{p_idx}A{attempt}:FidelityPass]", end=" ")
                return aligned

            print(f"[P{p_idx}A{attempt}:FidelityFail]", end=" ")

            # OPTIMIZATION: Check if we got SOME sentences correct
            # Find how many sentences from start are correct
            correct_sentences = []
            reconstructed_so_far = ""
            for sent in aligned:
                test_recon = reconstructed_so_far + sent
                if paragraph.startswith(test_recon):
                    correct_sentences.append(sent)
                    reconstructed_so_far = test_recon
                else:
                    break

            if correct_sentences and len(correct_sentences) < len(aligned):
                # We got some correct! Only retry the remaining part
                remaining_text = paragraph[len(reconstructed_so_far):]
                if CONFIG['display'].get('show_split_details', False):
                    print(f"\n          ✅ {len(correct_sentences)} sentences correct, retrying remaining {len(remaining_text)} chars")

                # Recursively process remaining part (strip leading space from retry)
                remaining_sentences = self._process_paragraph_single(remaining_text.lstrip(), f"{p_idx}R")
                return correct_sentences + remaining_sentences

            # Generate specific feedback for full retry
            feedback = self._generate_fidelity_feedback(paragraph, aligned)

            if CONFIG['display'].get('show_split_details', False):
                print(f"\n          📝 Feedback: {feedback}")

        # All retries exhausted - FAIL (don't use regex fallback)
        print(f"\n       ❌ CRITICAL: All {max_retries} LLM attempts failed for paragraph {p_idx}")
        print(f"          This will cause downstream Karaka extraction errors!")
        print(f"          Paragraph: {paragraph[:200]}...")

        # Return as single sentence to avoid catastrophic errors
        return [paragraph]

    def _process_paragraph_chunked(self, paragraph: str, p_idx: int) -> List[str]:
        """Process long paragraph using tokenizer-based chunking with overlap"""
        tokenizer = self.gsv_engine.tokenizer
        cfg = self.SENTENCE_SPLIT_CONFIG

        # Tokenize paragraph
        tokens = tokenizer.encode(paragraph, add_special_tokens=False)
        chunk_size = cfg['chunk_size_tokens']
        overlap = cfg['overlap_tokens']

        chunks = []
        for i in range(0, len(tokens), chunk_size - overlap):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = tokenizer.decode(chunk_tokens)
            chunks.append((i, chunk_text))
            if i + chunk_size >= len(tokens):
                break

        print(f"[P{p_idx}:Chunks={len(chunks)}]", end=" ")

        # Process each chunk
        all_chunk_sentences = []
        for chunk_idx, (offset, chunk_text) in enumerate(chunks):
            print(f"\n         C{chunk_idx+1}/{len(chunks)}", end=" ")
            chunk_sents = self._process_paragraph_single(chunk_text, f"{p_idx}.{chunk_idx+1}")
            if chunk_sents:
                all_chunk_sentences.append((offset, chunk_sents))

        # Merge overlapping outputs
        merged = self._merge_overlapping_chunks(all_chunk_sentences, paragraph)
        print(f"\n         [P{p_idx}:Merged={len(merged)}]", end=" ")
        return merged

    def _merge_overlapping_chunks(self, chunk_results: List[Tuple[int, List[str]]], original: str) -> List[str]:
        """
        Merge sentences from overlapping chunks while preserving order and avoiding duplicates.
        Uses cursor-based search to ensure repeated sentences (e.g. 'Thank you.') are preserved.
        """
        if not chunk_results:
            return []

        merged = []
        cursor = 0  # current search position in original text

        for offset, sentences in sorted(chunk_results, key=lambda x: x[0]):
            for sent in sentences:
                pos = original.find(sent, cursor)
                if pos == -1:
                    # If not found, try fuzzy search for robustness
                    window = original[cursor:cursor + len(sent) * 2]
                    match = difflib.SequenceMatcher(None, sent, window).find_longest_match(0, len(sent), 0, len(window))
                    if match.size > len(sent) * 0.8:
                        pos = cursor + match.b
                    else:
                        continue  # skip if can't align

                # Enforce increasing order
                if pos >= cursor:
                    merged.append(sent)
                    cursor = pos + len(sent)

        return merged

    def _llm_propose_sentences(self, text: str, feedback: Optional[str] = None) -> Optional[List[str]]:
        """Use LLM with reasoning mode to propose sentence splits

        CRITICAL: This must be accurate - errors cascade to Karaka extraction
        """
        system_prompt = self.gsv_engine.prompts.get("sentence_split_prompt")
        if not system_prompt:
            print(f"\n          ❌ No sentence_split_prompt found!")
            return None

        # Add feedback if provided
        if feedback:
            system_prompt = system_prompt + "\n\nFEEDBACK FROM PREVIOUS ATTEMPT:\n" + feedback

        # Use reasoning mode for better accuracy
        use_reasoning = self.SENTENCE_SPLIT_CONFIG.get('use_reasoning', True)
        output_tokens = self.SENTENCE_SPLIT_CONFIG['llm_max_output_tokens']

        if CONFIG['display'].get('show_split_details', False):
            print(f"\n          📤 LLM call: {len(text)} chars, reasoning={use_reasoning}")

        try:
            response = call_llm_isolated(
                system_prompt=system_prompt,
                user_prompt=text,
                model=self.gsv_engine.model,
                tokenizer=self.gsv_engine.tokenizer,
                max_tokens=output_tokens,
                temperature=0.0,
                reasoning_mode="on" if use_reasoning else "off"
            )

            if CONFIG['display'].get('show_split_details', False):
                print(f"\n          📥 Response: {len(response)} chars")
                # Show reasoning if present
                if "<think>" in response:
                    think_start = response.find("<think>")
                    think_end = response.find("</think>")
                    if think_end > think_start:
                        reasoning = response[think_start+7:think_end].strip()
                        print(f"\n          🧠 Reasoning: {reasoning[:300]}...")

            proposed = parse_json_response(response)

            if CONFIG['display'].get('show_split_details', False):
                print(f"\n          🔍 Parsed: {type(proposed)}")

            if not isinstance(proposed, list):
                print(f"\n          ❌ Not a list: {type(proposed)}")
                return None

            # Don't strip - preserve exact content
            sentences = [s for s in proposed if isinstance(s, str)]

            if CONFIG['display'].get('show_split_details', False):
                print(f"\n          ✅ Got {len(sentences)} sentences")
                for i, s in enumerate(sentences[:3], 1):
                    print(f"\n             {i}. [{len(s)} chars] {s[:100]}...")

            return sentences if sentences else None

        except Exception as e:
            print(f"[LLM_Error:{str(e)[:50]}]", end=" ")

        return None

    def _generate_alignment_feedback(self, original: str, proposed: List[str]) -> str:
        """Generate concise feedback when alignment fails (token-efficient)"""
        # Keep feedback under 100 tokens
        orig_preview = original[:150] + "..." if len(original) > 150 else original
        prop_count = len(proposed)

        return (
            f"ALIGNMENT FAILED: {prop_count} proposed sentences don't match original.\n"
            f"Original preview: {orig_preview}\n"
            f"Fix: Extract EXACT substrings, preserve all characters."
        )

    def _generate_fidelity_feedback(self, original: str, aligned: List[str]) -> str:
        """Generate specific feedback showing EXACTLY where the error is"""
        reconstructed = ''.join(aligned)

        # Find first character difference
        diff_pos = -1
        for i in range(min(len(original), len(reconstructed))):
            if original[i] != reconstructed[i]:
                diff_pos = i
                break

        if diff_pos == -1:
            # Length mismatch
            diff_pos = min(len(original), len(reconstructed))

        # Show context around error
        start = max(0, diff_pos - 30)
        end = min(len(original), diff_pos + 30)
        context = original[start:end]

        missing_chars = len(original) - len(reconstructed)

        # Specific instruction
        if missing_chars > 0:
            hint = "You're MISSING spaces after periods. Include them: 'sentence. ' not 'sentence.'"
        elif missing_chars < 0:
            hint = "You're ADDING extra characters. Remove them."
        else:
            hint = "Characters are wrong. Check punctuation and spacing."

        return (
            f"ERROR at position {diff_pos}: {hint}\n"
            f"Context: \"...{context}...\"\n"
            f"Missing {missing_chars} characters total."
        )

    # ========================================================================
    # HELPER METHODS (kept for backward compatibility)
    # ========================================================================

    def _get_safe_chunks(self, text: str, max_size: int = 1500) -> List[str]:
        """Recursively split text at safe boundaries (paragraphs > lines > sentence ends)"""
        if len(text) <= max_size:
            return [text]

        # 1. Paragraph break (\n\n)
        split_point = text.rfind('\n\n', 0, max_size)
        if split_point > 0:
            chunk1 = text[:split_point]
            chunk2 = text[split_point:].lstrip()
            return self._get_safe_chunks(chunk1, max_size) + self._get_safe_chunks(chunk2, max_size)

        # 2. Line break (\n)
        split_point = text.rfind('\n', 0, max_size)
        if split_point > 0:
            chunk1 = text[:split_point]
            chunk2 = text[split_point:].lstrip()
            return self._get_safe_chunks(chunk1, max_size) + self._get_safe_chunks(chunk2, max_size)

        # 3. Sentence boundary (.!? followed by space)
        last_end = -1
        for match in re.finditer(r'(?<=[.!?])\s+', text[:max_size]):
            last_end = match.end()
        if last_end > 0:
            chunk1 = text[:last_end]
            chunk2 = text[last_end:]
            return self._get_safe_chunks(chunk1, max_size) + self._get_safe_chunks(chunk2, max_size)

        # 4. Hard split (last resort)
        return [text[:max_size]] + self._get_safe_chunks(text[max_size:], max_size)


    def _fallback_sentence_split(self, text: str) -> List[str]:
        """Safe regex splitter without variable-length lookbehind."""
        parts = re.split(r'([.!?]+)\s+', text)

        ABBREVS = set(CONFIG['sentence_split']['abbreviations'])

        sentences = []
        i = 0
        while i < len(parts):
            current = parts[i].strip()
            if not current:
                i += 1
                continue

            if i + 1 < len(parts) and re.search(r'[.!?]$', current):
                punct = parts[i + 1] if i + 1 < len(parts) else ''
                next_part = parts[i + 2] if i + 2 < len(parts) else ''

                words = current.split()
                if words:
                    last_word = words[-1].rstrip('.!?').lower()
                    if last_word in ABBREVS:
                        merged = current + punct + (' ' + next_part if next_part else '')
                        parts[i] = merged
                        del parts[i+1:i+3]
                        continue

                sentences.append((current + punct).strip())
                i += 2
            else:
                sentences.append(current)
                i += 1

        return [s for s in sentences if s]


    def _align_and_reconstruct(self, original: str, proposed: List[str]) -> Optional[List[str]]:
        """Align LLM-proposed sentences to original text using fuzzy matching."""
        if not proposed:
            return None

        remaining = original
        aligned = []

        for sent in proposed:
            sent_clean = re.sub(r'\s+', ' ', sent.strip())
            if not sent_clean:
                continue

            window_size = min(len(remaining), len(sent_clean) * 3)
            window = remaining[:window_size]

            best_ratio = 0.0
            best_end = -1

            for end in range(max(1, len(sent_clean) - 10), len(window) + 10):
                if end <= 0 or end > len(window):
                    continue
                candidate = window[:end]
                cand_clean = re.sub(r'\s+', ' ', candidate.strip())
                if not cand_clean:
                    continue
                ratio = difflib.SequenceMatcher(None, sent_clean, cand_clean).ratio()
                if ratio > best_ratio and ratio >= 0.85:
                    best_ratio = ratio
                    best_end = end

            if best_end == -1:
                return None

            aligned.append(remaining[:best_end])
            remaining = remaining[best_end:].lstrip()

        if len(remaining.strip()) > 15:
            return None

        return aligned


    def _verify_exact_fidelity(self, original: str, sentences: List[str]) -> bool:
        """
        Verify near-exact fidelity while allowing harmless normalization differences.
        Ignores spacing, case, unicode variants, and minor punctuation formatting.
        """
        import unicodedata

        def normalize(s: str) -> str:
            # Normalize unicode and strip redundant whitespace
            s = unicodedata.normalize("NFKC", s)
            s = re.sub(r'\s+', ' ', s).strip().lower()
            return s

        original_norm = normalize(original)
        reconstructed_norm = normalize(''.join(sentences))

        # Compute similarity ratio
        ratio = difflib.SequenceMatcher(None, original_norm, reconstructed_norm).ratio()

        # Accept if threshold met (default 99%+ identical)
        threshold = self.SENTENCE_SPLIT_CONFIG.get('fidelity_threshold', 0.99)
        if ratio >= threshold:
            return True

        # Debug logging for failures
        print(f"[FidelityRatio={ratio:.4f}<{threshold}]", end=" ")

        if CONFIG['display'].get('show_debug_output', False):
            reconstructed = ''.join(sentences)
            print(f"\n          ⚠️ Fidelity check failed:")
            print(f"             Original: {len(original)} chars")
            print(f"             Reconstructed: {len(reconstructed)} chars")
            print(f"             Difference: {len(original) - len(reconstructed)} chars")
            print(f"             Similarity: {ratio:.2%}")

            # Show first difference
            for i in range(min(len(original), len(reconstructed))):
                if i >= len(original) or i >= len(reconstructed) or original[i] != reconstructed[i]:
                    print(f"\n          🔍 First diff at position {i}:")
                    print(f"             Original: ...{original[max(0,i-20):i+20]}...")
                    print(f"             Reconstructed: ...{reconstructed[max(0,i-20):i+20]}...")
                    break

        return False


    def _split_chunk_with_llm(self, text: str, max_retries: int = 3) -> List[str]:
        """Use LLM to propose sentences, then align to original for 100% fidelity."""
        system_prompt = self.gsv_engine.prompts.get("sentence_split_prompt")
        if not system_prompt:
            if CONFIG['display'].get('show_debug_output', False):
                print(f"\n          ⚠️ No sentence_split_prompt found")
            return self._fallback_sentence_split(text)

        for attempt in range(max_retries):
            try:
                response = call_llm_isolated(
                    system_prompt=system_prompt,
                    user_prompt=text,
                    model=self.gsv_engine.model,
                    tokenizer=self.gsv_engine.tokenizer,
                    max_tokens=800
                )

                proposed = parse_json_response(response)
                if not (isinstance(proposed, list) and all(isinstance(s, str) for s in proposed)):
                    print(f"⚠️ Invalid format", end=" ")
                    continue

                proposed = [s.strip() for s in proposed if s.strip()]
                if not proposed:
                    print(f"⚠️ Empty output", end=" ")
                    continue

                # Try alignment
                aligned = self._align_and_reconstruct(text, proposed)
                if aligned and self._verify_exact_fidelity(text, aligned):
                    return aligned

                # Self-correction on last attempt
                if attempt == max_retries - 2:
                    orig_norm = re.sub(r'\s+', '', text)
                    prop_norm = re.sub(r'\s+', '', ''.join(proposed))
                    min_len = min(len(orig_norm), len(prop_norm))
                    diff_pos = next((i for i in range(min_len) if orig_norm[i] != prop_norm[i]), min_len)
                    start_ctx = max(0, diff_pos - 50)
                    end_ctx = min(len(text), diff_pos + 50)
                    context_snippet = text[start_ctx:end_ctx]

                    system_prompt = PROMPTS.get("sentence_split_retry_prompt", "").format(
                        context_snippet=context_snippet
                    )
                    continue

                print(f"⚠️ Fidelity failed", end=" ")

            except Exception as e:
                print(f"⚠️ Exception: {e}", end=" ")
                continue

        # Final fallback: hybrid approach
        print(f"\n          ❌ All LLM retries failed → hybrid fallback")
        if CONFIG['display'].get('show_debug_output', False):
            print(f"\n          Text preview: {text[:200]}...")
        return self._hybrid_sentence_split(text)


    def _hybrid_sentence_split(self, text: str) -> List[str]:
        """Combine LLM (1 try) + rule-based + choose best via fidelity."""
        llm_proposal = None
        try:
            response = call_llm_isolated(
                system_prompt=PROMPTS.get("sentence_split_simple_prompt", "Split into sentences. Return JSON array only."),
                user_prompt=text,
                model=self.gsv_engine.model,
                tokenizer=self.gsv_engine.tokenizer,
                max_tokens=800,
                temperature=0.0
            )
            proposed = parse_json_response(response)
            if isinstance(proposed, list):
                llm_proposal = [s.strip() for s in proposed if s.strip()]
        except:
            pass

        rule_proposal = self._fallback_sentence_split(text)

        candidates = []
        if llm_proposal:
            aligned = self._align_and_reconstruct(text, llm_proposal)
            if aligned and self._verify_exact_fidelity(text, aligned):
                candidates.append(aligned)
        if rule_proposal and self._verify_exact_fidelity(text, rule_proposal):
            candidates.append(rule_proposal)

        if candidates:
            return candidates[0]

        return rule_proposal if rule_proposal else [text.strip()]
    # ========================================================================
    # END OF NEW SPLITTING PIPELINE
    # ========================================================================

    def _embed_and_store(self, refined_docs: Dict[str, List[str]]):
        """Create Document nodes and FAISS embeddings

        Args:
            refined_docs: Dict mapping doc_id to list of lines
        """
        total_docs = sum(len(lines) for lines in refined_docs.values())
        processed = 0
        failed = 0

        print(f"   📊 Total documents to embed: {total_docs}")

        for doc_id, lines in refined_docs.items():
            print(f"   📄 Embedding {doc_id}...", end=' ', flush=True)
            doc_success = 0
            doc_failed = 0

            for line_num, text in enumerate(lines, 1):
                try:
                    # Create Document node
                    doc_node_id = self.graph.add_document_node(doc_id, line_num, text)

                    # Generate embedding
                    embedding = self._encode_text(text)

                    # Store in FAISS
                    self.graph.vector_store.add(doc_node_id, embedding)

                    doc_success += 1
                    processed += 1
                except Exception as e:
                    print(f"\n      ⚠️ Failed to embed line {line_num}:")
                    print(f"         Error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    doc_failed += 1
                    failed += 1

                # Progress update every 10 lines
                if processed % 10 == 0 or processed == total_docs:
                    progress_pct = (processed / total_docs) * 100
                    print(f"\r      Progress: {processed}/{total_docs} ({progress_pct:.1f}%) embedded", end='', flush=True)

            print(f"\r   ✅ {doc_id}: {doc_success}/{len(lines)} lines embedded")

        print(f"\n   ✅ Embedding complete: {processed}/{total_docs} successful, {failed} failed")

    def _encode_text(self, text: str) -> np.ndarray:
        """Encode text using embedding model

        Args:
            text: Text to encode

        Returns:
            Embedding vector
        """
        # Assumes embedding_tokenizer and embedding_model are BERT-like
        inputs = self.embedding_tokenizer([text], padding=True, truncation=True, return_tensors='pt')
        inputs = {k: v.to(self.embedding_model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.embedding_model(**inputs)

        # Assumes average_pool is defined elsewhere
        embedding = average_pool(outputs.last_hidden_state, inputs["attention_mask"])
        return embedding.cpu().numpy()[0]

    def _extract_kriyas(self, refined_docs: Dict[str, List[str]]):
        """Extract Kriyās from all documents using GSV-Retry

        Args:
            refined_docs: Dict mapping doc_id to list of lines
        """
        self.stats['total_lines'] = sum(len(lines) for lines in refined_docs.values())
        processed = 0
        retry_count = 0

        print(f"\n   📊 Total lines to process: {self.stats['total_lines']}")

        for doc_id, lines in refined_docs.items():
            print(f"\n   📄 Processing document: {doc_id} ({len(lines)} lines)")

            for line_num, text in enumerate(lines, 1):
                processed += 1
                line_ref = f"{doc_id}_L{line_num}"

                # Show progress with percentage
                progress_pct = (processed / self.stats['total_lines']) * 100
                print(f"      [{processed}/{self.stats['total_lines']}] ({progress_pct:.1f}%) {line_ref}: ", end='', flush=True)

                # Extract with GSV-Retry
                golden_candidate = self.gsv_engine.extract_with_retry(
                    text=text,
                    extraction_type="kriya",
                    line_ref=line_ref
                )

                if golden_candidate:
                    try:
                        # Write to graph
                        self._write_to_graph(golden_candidate, doc_id, line_num, text)
                        print(f"✅")
                        self.stats['successful_extractions'] += 1
                    except Exception as e:
                        print(f"❌ Graph write failed: {str(e)[:50]}")
                        self.stats['failed_extractions'] += 1
                else:
                    print(f"❌ GSV-Retry exhausted")
                    self.stats['failed_extractions'] += 1

            # Document summary
            doc_success = sum(1 for line_num in range(1, len(lines)+1)
                            if f"{doc_id}_L{line_num}_K0" in self.graph.kriyas)
            print(f"   ✅ Document complete: {doc_success}/{len(lines)} lines extracted successfully")

    def _write_to_graph(self, golden_candidate: Dict, doc_id: str, line_number: int, text: str):
        """Write verified Kriyā to graph with schema compliance

        Args:
            golden_candidate: Golden candidate from GSV-Retry
            doc_id: Document ID
            line_number: Line number
            text: Original text
        """
        # Handle different result formats
        if not isinstance(golden_candidate, dict):
            print(f"⚠️ Invalid candidate type: {type(golden_candidate)}")
            return

        # Extract data from golden candidate
        data = golden_candidate.get("data", {})

        # Handle both single extraction and multiple extractions
        extractions = data.get("extractions", [])
        if not extractions:
            # Fallback: treat entire data as single extraction
            extractions = [data]

        for extraction in extractions:
            verb = extraction.get("verb")
            karakas = extraction.get("karakas", {})
            coreferences = extraction.get("coreferences", [])

            if not verb:
                continue

            # Create Kriyā node
            kriya_id = self.graph.add_kriya_node(verb, doc_id, line_number)
            self.stats['total_kriyas'] += 1

            # Create Entity nodes and kāraka edges (ALL edges flow FROM Kriyā)
            for karaka_type, entity_mention in karakas.items():
                if not entity_mention:
                    continue

                # Resolve entity to canonical form
                canonical_entity = self.graph.entity_resolver.resolve_entity(entity_mention)
                entity_id = self.graph.add_entity_node(canonical_entity)

                # Track unique entities
                if entity_id not in [n for n in self.graph.graph.nodes() if self.graph.graph.nodes[n].get('type') == 'Entity']:
                    self.stats['total_entities'] += 1

                # Map kāraka type to edge relation
                relation = self._map_karaka_to_relation(karaka_type)

                # Add edge FROM Kriyā TO Entity
                self.graph.add_edge(kriya_id, entity_id, relation)
                self.stats['total_edges'] += 1

            # Store coreference hints for post-processing
            for coref in coreferences:
                pronoun = coref.get("pronoun")
                likely_referent = coref.get("likely_referent")
                context = coref.get("context", "")

                if pronoun:
                    pronoun_entity_id = self.graph.add_entity_node(pronoun)
                    # Store hint as node attribute
                    self.graph.graph.nodes[pronoun_entity_id]["coref_context"] = context
                    if likely_referent:
                        self.graph.graph.nodes[pronoun_entity_id]["coref_hint"] = likely_referent

            # Add citation edge (FROM Kriyā TO Document)
            doc_node_id = f"{doc_id}_L{line_number}"
            self.graph.add_edge(kriya_id, doc_node_id, "CITED_IN")
            self.stats['total_edges'] += 1

    def _map_karaka_to_relation(self, karaka_type: str) -> str:
        """Map Pāṇinian kāraka to graph relation (all flow FROM Kriyā)

        Args:
            karaka_type: Kāraka type from extraction

        Returns:
            Graph relation name
        """
        mapping = CONFIG['karaka_relation_mapping']
        return mapping.get(karaka_type, "UNKNOWN")

    def _print_statistics(self):
        """Print final ingestion statistics"""
        print(f"\n{'='*80}")
        print(f"📊 INGESTION STATISTICS")
        print(f"{'='*80}")

        # Extraction statistics
        print(f"\n✅ Extraction Results:")
        print(f"   Total lines processed: {self.stats['total_lines']}")
        print(f"   Successful extractions: {self.stats['successful_extractions']}")
        print(f"   Failed extractions: {self.stats['failed_extractions']}")
        success_rate = (self.stats['successful_extractions']/self.stats['total_lines']*100) if self.stats['total_lines'] > 0 else 0
        print(f"   Success rate: {success_rate:.1f}%")

        # Graph statistics
        entity_count = len([n for n in self.graph.graph.nodes() if self.graph.graph.nodes[n].get('type') == 'Entity'])
        print(f"\n📈 Graph Statistics:")
        print(f"   Total Kriyās: {len(self.graph.kriyas)}")
        print(f"   Total Entities: {entity_count}")
        print(f"   Total Documents: {len(self.graph.documents)}")
        print(f"   Total Edges: {self.graph.graph.number_of_edges()}")
        print(f"   FAISS Index Size: {self.graph.vector_store.size()}")

        # Edge breakdown
        edge_types = defaultdict(int)
        for _, _, data in self.graph.graph.edges(data=True):
            relation = data.get('relation', 'UNKNOWN')
            edge_types[relation] += 1

        print(f"\n🔗 Edge Distribution:")
        for relation, count in sorted(edge_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {relation}: {count}")

        # GSV-Retry statistics
        gsv_stats = self.gsv_engine.get_failure_stats()
        print(f"\n🔄 GSV-Retry Statistics:")
        print(f"   Total attempts: {gsv_stats['total_attempts']}")
        print(f"   Successful: {gsv_stats['total_attempts'] - gsv_stats['total_failures']}")
        print(f"   Failed: {gsv_stats['total_failures']}")
        print(f"   Success rate: {gsv_stats['success_rate']*100:.1f}%")

        if gsv_stats['failure_reasons']:
            print(f"\n❌ Failure Breakdown:")
            for reason, count in gsv_stats['failure_reasons'].items():
                print(f"   {reason}: {count}")

        print(f"\n{'='*80}")

    # ========================================================================
    # POST-PROCESSING METHODS
    # ========================================================================

    def run_post_processing(self):
        """Run all post-processing steps"""
        print(f"\n{'='*80}")
        print(f"POST-PROCESSING")
        print(f"{'='*80}")

        print(f"\n🔗 Step 1: Resolving coreferences...")
        self._resolve_coreferences()

        print(f"\n🔗 Step 2: Linking metaphorical entities...")
        self._link_metaphorical_entities()

        print(f"\n🏷️  Step 3: Enriching entity types...")
        self._enrich_entity_types()

        print(f"\n⚡ Step 4: Detecting causal relationships...")
        self._detect_causal_relationships()

        print(f"\n✅ Post-processing complete")

    def _resolve_coreferences(self):
        """Link pronouns to entities using RAG and extraction-time hints"""
        # Expanded pronoun list
        pronouns = ["he", "she", "it", "they", "him", "her", "his", "hers", "its", "their",
                   "theirs", "which", "that", "who", "whom", "this", "these", "those"]

        # Find all pronoun entities
        pronoun_nodes = [
            n for n in self.graph.graph.nodes()
            if self.graph.graph.nodes[n].get("type") == "Entity"
            and self.graph.graph.nodes[n].get("canonical_name", "").lower() in pronouns
        ]

        print(f"   📊 Found {len(pronoun_nodes)} pronoun entities to resolve")
        resolved_count = 0
        skipped_count = 0
        failed_count = 0

        for idx, pronoun_id in enumerate(pronoun_nodes, 1):
            pronoun_name = self.graph.graph.nodes[pronoun_id].get("canonical_name", "")
            print(f"      [{idx}/{len(pronoun_nodes)}] Resolving '{pronoun_name}'...", end=' ', flush=True)

            try:
                # Check if extraction provided coreference hint
                coref_hint = self.graph.graph.nodes[pronoun_id].get("coref_hint")
                coref_context = self.graph.graph.nodes[pronoun_id].get("coref_context", "")

                # Get context via incoming edges (traverse FROM Entity via HAS_KARTĀ, HAS_KARMA, etc.)
                kriya_nodes = [
                    e[0] for e in self.graph.graph.in_edges(pronoun_id, data=True)
                    if e[2].get("relation") in ["HAS_KARTĀ", "HAS_KARMA", "USES_KARANA",
                                                "TARGETS_SAMPRADĀNA", "FROM_APĀDĀNA"]
                ]

                if not kriya_nodes:
                    print(f"⚠️ No context")
                    skipped_count += 1
                    continue

                # Get document nodes via CITED_IN edges
                doc_nodes = []
                for k in kriya_nodes:
                    doc_edges = [
                        e[1] for e in self.graph.graph.out_edges(k, data=True)
                        if e[2].get("relation") == "CITED_IN"
                    ]
                    doc_nodes.extend(doc_edges)

                if not doc_nodes:
                    print(f"⚠️ No documents")
                    skipped_count += 1
                    continue

                # Query FAISS for nearby context (5 nearest neighbors)
                context_docs = []
                for doc_node in doc_nodes[:1]:  # Use first doc as anchor
                    nearby = self.graph.vector_store.query_nearby(doc_node, k=5)
                    context_docs.extend(nearby)

                if not context_docs:
                    print(f"⚠️ No nearby docs")
                    skipped_count += 1
                    continue

                # Build context from nearby documents
                context_texts = []
                for doc_id in context_docs[:5]:
                    if doc_id in self.graph.graph:
                        text = self.graph.graph.nodes[doc_id].get("text", "")
                        if text:
                            context_texts.append(text)

                # Use verifier LLM to confirm coreference link
                target_entity = self._verify_coreference(
                    pronoun_name,
                    context_texts,
                    coref_hint,
                    coref_context
                )

                if target_entity:
                    # Resolve target entity to canonical form
                    canonical_target = self.graph.entity_resolver.resolve_entity(target_entity)

                    # Check if target entity exists in graph
                    if canonical_target in self.graph.graph:
                        # Add IS_SAME_AS edge
                        self.graph.add_edge(pronoun_id, canonical_target, "IS_SAME_AS")
                        resolved_count += 1
                        print(f"✅ → '{canonical_target}'")
                    else:
                        print(f"⚠️ Target not in graph")
                        skipped_count += 1
                else:
                    print(f"⚠️ No target found")
                    skipped_count += 1
            except Exception as e:
                print(f"❌ Error: {str(e)[:30]}")
                failed_count += 1

        print(f"\n   ✅ Coreference resolution complete:")
        print(f"      Resolved: {resolved_count}")
        print(f"      Skipped: {skipped_count}")
        print(f"      Failed: {failed_count}")

    def _verify_coreference(self, pronoun: str, context_texts: List[str],
                           hint: Optional[str], hint_context: str) -> Optional[str]:
        """Use LLM to verify coreference link

        Args:
            pronoun: Pronoun to resolve
            context_texts: Surrounding context texts
            hint: Extraction-time hint (likely referent)
            hint_context: Context from extraction

        Returns:
            Target entity name or None
        """
        if not context_texts:
            return hint  # Fallback to hint if no context

        system_prompt = self.gsv_engine.prompts.get("coreference_resolution_prompt", "")

        context_str = "\n".join([f"- {text}" for text in context_texts[:5]])
        hint_str = f"\nExtraction hint: '{pronoun}' likely refers to '{hint}' ({hint_context})" if hint else ""

        user_prompt = f"""Pronoun: "{pronoun}"

Context:
{context_str}{hint_str}

What entity does this pronoun refer to?"""

        try:
            response = call_llm_isolated(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.gsv_engine.model,
                tokenizer=self.gsv_engine.tokenizer,
                max_tokens=150
            )

            result = parse_json_response(response)
            if result and isinstance(result, dict):
                referent = result.get("referent")
                confidence = result.get("confidence", "low")

                # Only accept high or medium confidence
                if referent and confidence in ["high", "medium"]:
                    return referent
        except Exception as e:
            print(f"      ⚠️ Coreference verification failed: {e}")

        return None

    def _link_metaphorical_entities(self):
        """Link metaphorical references using GSV-Retry"""
        # Patterns that suggest metaphorical references
        metaphor_patterns = [
            r"king of \w+",
            r"lord of \w+",
            r"master of \w+",
            r"father of \w+",
            r"mother of \w+",
            r"son of \w+",
            r"daughter of \w+",
            r"\w+ the \w+",  # e.g., "Rama the brave"
        ]

        # Find entities matching metaphorical patterns
        metaphor_entities = []
        for node_id in self.graph.graph.nodes():
            if self.graph.graph.nodes[node_id].get("type") != "Entity":
                continue

            canonical_name = self.graph.graph.nodes[node_id].get("canonical_name", "")
            canonical_lower = canonical_name.lower()

            for pattern in metaphor_patterns:
                if re.search(pattern, canonical_lower):
                    metaphor_entities.append(node_id)
                    break

        print(f"   📊 Found {len(metaphor_entities)} potential metaphorical entities")
        linked_count = 0
        skipped_count = 0
        failed_count = 0

        for idx, metaphor_id in enumerate(metaphor_entities, 1):
            metaphor_name = self.graph.graph.nodes[metaphor_id].get("canonical_name", "")
            print(f"      [{idx}/{len(metaphor_entities)}] Linking '{metaphor_name}'...", end=' ', flush=True)

            try:
                # Get context via edges
                kriya_nodes = [
                    e[0] for e in self.graph.graph.in_edges(metaphor_id, data=True)
                ]

                if not kriya_nodes:
                    print(f"⚠️ No context")
                    skipped_count += 1
                    continue

                # Get document context
                doc_nodes = []
                for k in kriya_nodes[:3]:  # Limit to 3 kriyas
                    doc_edges = [
                        e[1] for e in self.graph.graph.out_edges(k, data=True)
                        if e[2].get("relation") == "CITED_IN"
                    ]
                    doc_nodes.extend(doc_edges)

                # Build context
                context_texts = []
                for doc_id in doc_nodes[:5]:
                    if doc_id in self.graph.graph:
                        text = self.graph.graph.nodes[doc_id].get("text", "")
                        if text:
                            context_texts.append(text)

                if not context_texts:
                    print(f"⚠️ No context texts")
                    skipped_count += 1
                    continue

                # Use LLM to find target entity
                target_entity = self._resolve_metaphor(metaphor_name, context_texts)

                if target_entity:
                    # Resolve to canonical form
                    canonical_target = self.graph.entity_resolver.resolve_entity(target_entity)

                    # Check if target exists and is different from metaphor
                    if canonical_target in self.graph.graph and canonical_target != metaphor_id:
                        # Add IS_SAME_AS edge
                        self.graph.add_edge(metaphor_id, canonical_target, "IS_SAME_AS")
                        linked_count += 1
                        print(f"✅ → '{canonical_target}'")
                    else:
                        print(f"⚠️ Target not valid")
                        skipped_count += 1
                else:
                    print(f"⚠️ No target found")
                    skipped_count += 1
            except Exception as e:
                print(f"❌ Error: {str(e)[:30]}")
                failed_count += 1

        print(f"\n   ✅ Metaphorical linking complete:")
        print(f"      Linked: {linked_count}")
        print(f"      Skipped: {skipped_count}")
        print(f"      Failed: {failed_count}")

    def _resolve_metaphor(self, metaphor: str, context_texts: List[str]) -> Optional[str]:
        """Use LLM to resolve metaphorical reference

        Args:
            metaphor: Metaphorical entity name
            context_texts: Context texts

        Returns:
            Target entity name or None
        """
        if not context_texts:
            return None

        system_prompt = PROMPTS.get("metaphor_resolution_prompt", "")

        context_str = "\n".join([f"- {text}" for text in context_texts[:5]])

        user_prompt = PROMPTS.get("metaphor_resolution_user_template", "").format(
            metaphor=metaphor,
            context=context_str
        )

        try:
            response = call_llm_isolated(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.gsv_engine.model,
                tokenizer=self.gsv_engine.tokenizer,
                max_tokens=150
            )

            result = parse_json_response(response)
            if result and isinstance(result, dict):
                entity = result.get("actual_entity")
                confidence = result.get("confidence", "low")

                if entity and confidence in ["high", "medium"]:
                    return entity
        except Exception as e:
            print(f"      ⚠️ Metaphor resolution failed: {e}")

        return None

    def _enrich_entity_types(self):
        """Enrich entity nodes with type information using RAG and verifier LLM"""
        # Get all canonical entities (non-pronoun)
        pronouns = ["he", "she", "it", "they", "him", "her", "his", "hers", "its", "their",
                   "theirs", "which", "that", "who", "whom", "this", "these", "those"]

        entity_nodes = [
            n for n in self.graph.graph.nodes()
            if self.graph.graph.nodes[n].get("type") == "Entity"
            and self.graph.graph.nodes[n].get("canonical_name", "").lower() not in pronouns
            and not self.graph.graph.nodes[n].get("entity_type")  # Not already typed
        ]

        print(f"   📊 Found {len(entity_nodes)} entities to type (limiting to 50)")
        typed_count = 0
        skipped_count = 0
        failed_count = 0

        for idx, entity_id in enumerate(entity_nodes[:50], 1):  # Limit to 50 for performance
            entity_name = self.graph.graph.nodes[entity_id].get("canonical_name", "")

            if idx % 5 == 0 or idx == 1:
                print(f"      [{idx}/50] Typing entities...", end='\r', flush=True)

            try:
                # Get context via edges
                kriya_nodes = [
                    e[0] for e in self.graph.graph.in_edges(entity_id, data=True)
                ]

                if not kriya_nodes:
                    skipped_count += 1
                    continue

                # Get document context
                doc_nodes = []
                for k in kriya_nodes[:3]:
                    doc_edges = [
                        e[1] for e in self.graph.graph.out_edges(k, data=True)
                        if e[2].get("relation") == "CITED_IN"
                    ]
                    doc_nodes.extend(doc_edges)

                # Build context
                context_texts = []
                for doc_id in doc_nodes[:5]:
                    if doc_id in self.graph.graph:
                        text = self.graph.graph.nodes[doc_id].get("text", "")
                        if text:
                            context_texts.append(text)

                if not context_texts:
                    skipped_count += 1
                    continue

                # Determine entity type
                entity_type = self._determine_entity_type(entity_name, context_texts)

                if entity_type:
                    # Add entity_type attribute
                    self.graph.graph.nodes[entity_id]["entity_type"] = entity_type
                    typed_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                failed_count += 1

        print(f"\n   ✅ Entity typing complete:")
        print(f"      Typed: {typed_count}")
        print(f"      Skipped: {skipped_count}")
        print(f"      Failed: {failed_count}")

    def _determine_entity_type(self, entity_name: str, context_texts: List[str]) -> Optional[str]:
        """Use LLM to determine entity type

        Args:
            entity_name: Entity name
            context_texts: Context texts

        Returns:
            Entity type or None
        """
        if not context_texts:
            return None

        system_prompt = PROMPTS.get("entity_type_classifier_prompt", "")

        context_str = "\n".join([f"- {text}" for text in context_texts[:3]])

        user_prompt = PROMPTS.get("entity_type_classifier_user_template", "").format(
            entity_name=entity_name,
            context=context_str
        )

        try:
            response = call_llm_isolated(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.gsv_engine.model,
                tokenizer=self.gsv_engine.tokenizer,
                max_tokens=100
            )

            result = parse_json_response(response)
            if result and isinstance(result, dict):
                entity_type = result.get("entity_type")
                confidence = result.get("confidence", "low")

                if entity_type and confidence in ["high", "medium"]:
                    return entity_type
        except Exception as e:
            pass  # Silent fail for performance

        return None

    def _detect_causal_relationships(self):
        """Detect causal relationships between adjacent Kriyā nodes"""
        # Get all Kriyā nodes
        kriya_nodes = [
            n for n in self.graph.graph.nodes()
            if self.graph.graph.nodes[n].get("type") == "Kriya"
        ]

        print(f"   📊 Analyzing {len(kriya_nodes)} Kriyā nodes for causality")
        causal_count = 0
        failed_count = 0

        # Group Kriyās by document for adjacency analysis
        doc_kriyas = defaultdict(list)
        for kriya_id in kriya_nodes:
            doc_id = self.graph.graph.nodes[kriya_id].get("doc_id")
            line_num = self.graph.graph.nodes[kriya_id].get("line_number")
            if doc_id and line_num:
                doc_kriyas[doc_id].append((line_num, kriya_id))

        # Sort by line number within each document
        for doc_id in doc_kriyas:
            doc_kriyas[doc_id].sort(key=lambda x: x[0])

        # Check adjacent Kriyās for causality
        checked = 0
        for doc_id, kriyas in doc_kriyas.items():
            for i in range(len(kriyas) - 1):
                line1, kriya1 = kriyas[i]
                line2, kriya2 = kriyas[i + 1]

                # Only check adjacent or nearby lines (within 3 lines)
                if line2 - line1 > 3:
                    continue

                # Get texts for both Kriyās
                doc_node1 = f"{doc_id}_L{line1}"
                doc_node2 = f"{doc_id}_L{line2}"

                text1 = self.graph.graph.nodes.get(doc_node1, {}).get("text", "")
                text2 = self.graph.graph.nodes.get(doc_node2, {}).get("text", "")

                if not text1 or not text2:
                    continue

                try:
                    # Check for causality
                    is_causal, direction = self._check_causality(
                        kriya1, kriya2, text1, text2
                    )

                    if is_causal:
                        if direction == "forward":
                            # kriya1 CAUSES kriya2
                            self.graph.add_edge(kriya1, kriya2, "CAUSES")
                            causal_count += 1
                        elif direction == "backward":
                            # kriya2 CAUSES kriya1
                            self.graph.add_edge(kriya2, kriya1, "CAUSES")
                            causal_count += 1
                except Exception as e:
                    failed_count += 1

                checked += 1
                if checked % 20 == 0:
                    progress_pct = (checked / sum(max(0, len(k)-1) for k in doc_kriyas.values())) * 100 if doc_kriyas else 0
                    print(f"      Progress: {checked} pairs checked ({progress_pct:.1f}%), {causal_count} causal links, {failed_count} failed", end='\r', flush=True)

        print(f"\n   ✅ Causal relationship detection complete:")
        print(f"      Found: {causal_count} causal links")
        print(f"      Checked: {checked} pairs")
        print(f"      Failed: {failed_count}")

    def _check_causality(self, kriya1_id: str, kriya2_id: str,
                        text1: str, text2: str) -> Tuple[bool, Optional[str]]:
        """Use LLM to check if two Kriyās have causal relationship

        Args:
            kriya1_id: First Kriyā node ID
            kriya2_id: Second Kriyā node ID
            text1: Text containing first Kriyā
            text2: Text containing second Kriyā

        Returns:
            Tuple of (is_causal, direction) where direction is "forward", "backward", or None
        """
        verb1 = self.graph.graph.nodes[kriya1_id].get("verb", "")
        verb2 = self.graph.graph.nodes[kriya2_id].get("verb", "")

        system_prompt = PROMPTS.get("causal_relationship_detector_prompt", "")

        user_prompt = PROMPTS.get("causal_relationship_user_template", "").format(
            verb1=verb1,
            text1=text1,
            verb2=verb2,
            text2=text2
        )

        try:
            response = call_llm_isolated(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.gsv_engine.model,
                tokenizer=self.gsv_engine.tokenizer,
                max_tokens=150
            )

            result = parse_json_response(response)
            if result and isinstance(result, dict):
                is_causal = result.get("is_causal", False)
                direction = result.get("direction")
                confidence = result.get("confidence", "low")

                if is_causal and confidence in ["high", "medium"] and direction:
                    return True, direction
        except Exception as e:
            pass  # Silent fail for performance

        return False, None

print("✅ IngestionPipeline class defined")


# ============================================================================
# CELL 9: Query Pipeline Class Definition
# ============================================================================
# NOTE: Re-run this cell after any changes to QueryPipeline code
class QueryPipeline:
    """Query pipeline with GSV-Retry decomposition and graph-based execution"""

    def __init__(self, graph: KarakaGraphV2, gsv_engine: GSVRetryEngine, model, tokenizer):
        """Initialize query pipeline

        Args:
            graph: KarakaGraphV2 instance
            gsv_engine: GSVRetryEngine for query decomposition
            model: LLM model
            tokenizer: Tokenizer
        """
        self.graph = graph
        self.gsv_engine = gsv_engine
        self.model = model
        self.tokenizer = tokenizer

    def answer_query(self, question: str) -> Dict:
        """Main query orchestrator

        Args:
            question: User question

        Returns:
            Dict with answer, citations, reasoning_trace, status
        """
        print(f"\n{'='*80}")
        print(f"🔍 QUERY: {question}")
        print(f"{'='*80}")

        reasoning_trace = []

        # Step 1: Decompose query (direct call - GSV too slow for queries)
        print("\n📋 [Step 1/3] Decomposing query (DIRECT CALL - NO GSV)...")
        print(f"   Query text: '{question}'")
        print(f"   🚀 Calling LLM directly...", end="", flush=True)
        try:
            response = call_llm_isolated(
                system_prompt=self.gsv_engine.prompts.get("query_decomposition_prompt"),
                user_prompt=question,
                model=self.gsv_engine.model,
                tokenizer=self.gsv_engine.tokenizer,
                temperature=0.5
            )
            print(" Done", flush=True)

            parsed_plan = parse_json_response(response)

            if not parsed_plan:
                print("   ❌ Failed to parse query plan")
                return {
                    "question": question,
                    "answer": "Failed to decompose query. Please try rephrasing your question.",
                    "citations": [],
                    "reasoning_trace": [],
                    "status": "ERROR"
                }

            # Normalize format: if it's a list, wrap it in {"steps": [...]}
            if isinstance(parsed_plan, list):
                parsed_plan = {"steps": parsed_plan}

            # Wrap in golden_plan format for compatibility
            golden_plan = {"data": parsed_plan, "raw_response": response}

            print(f"   ✅ Query plan generated")
            print(f"   📝 Plan: {json.dumps(golden_plan['data'], indent=2)[:200]}...")
        except Exception as e:
            print(f"   ❌ Error during decomposition: {str(e)[:50]}")
            return {
                "question": question,
                "answer": f"Error during query decomposition: {str(e)[:100]}",
                "citations": [],
                "reasoning_trace": [],
                "status": "ERROR"
            }

        # Step 2: Execute graph traversal with reasoning trace
        print("\n🔎 [Step 2/3] Executing graph traversal...")
        try:
            ground_truth_docs, reasoning_trace = self._execute_traversal(golden_plan["data"])

            if not ground_truth_docs:
                print("   ⚠️ No matching documents found")
                return {
                    "question": question,
                    "answer": "No answer found in the knowledge graph. The information may not be available in the ingested documents.",
                    "citations": [],
                    "reasoning_trace": reasoning_trace,
                    "status": "NO_MATCH"
                }

            print(f"   ✅ Found {len(ground_truth_docs)} relevant document(s)")

            # Print reasoning trace
            if reasoning_trace:
                print(f"\n   📊 Reasoning Trace:")
                for step in reasoning_trace:
                    print(f"      Step {step.step_number}: {step.description}")
                    print(f"         Kriyā: {step.kriya_matched}")
                    print(f"         Kārakas: {step.karakas_matched}")
                    print(f"         Citations: {len(step.citations)} document(s)")
        except Exception as e:
            print(f"   ❌ Error during traversal: {str(e)[:50]}")
            return {
                "question": question,
                "answer": f"Error during graph traversal: {str(e)[:100]}",
                "citations": [],
                "reasoning_trace": [],
                "status": "ERROR"
            }

        # Step 3: Generate grounded answer
        print("\n💬 [Step 3/3] Generating grounded answer...")
        try:
            result = self._generate_answer(question, ground_truth_docs)
            result["reasoning_trace"] = reasoning_trace
            print(f"   ✅ Answer generated successfully")
            return result
        except Exception as e:
            print(f"   ❌ Error during answer generation: {str(e)[:50]}")
            return {
                "question": question,
                "answer": f"Error generating answer: {str(e)[:100]}",
                "citations": ground_truth_docs,
                "reasoning_trace": reasoning_trace,
                "status": "ERROR"
            }

    def _execute_traversal(self, query_plan: Dict) -> Tuple[List[Dict], List[ReasoningStep]]:
        """Translate plan to NetworkX operations and execute

        Args:
            query_plan: Query plan from GSV-Retry (can be dict or list)

        Returns:
            Tuple of (document dicts, reasoning steps)
        """
        all_doc_nodes = []
        reasoning_trace = []

        # Handle both dict and list formats
        if isinstance(query_plan, list):
            steps = query_plan
        else:
            steps = query_plan.get("steps", [])

        if not steps:
            # Fallback: treat as single step
            steps = [query_plan]

        for step_num, step in enumerate(steps, 1):
            # Find matching Kriyā nodes
            kriya_nodes = self._find_kriyas(
                verb=step.get("verb"),
                karaka_constraints=step.get("karakas", {})
            )

            print(f"    Found {len(kriya_nodes)} matching Kriyā(s)")

            # Multi-hop: Follow CAUSES, IS_SAME_AS chains if requested
            if step.get("follow_causes"):
                kriya_nodes = self._expand_causal_chain(kriya_nodes)
                print(f"    Expanded to {len(kriya_nodes)} Kriyā(s) via causal chain")

            # Get cited documents for this step
            step_doc_nodes = []
            for kriya_id in kriya_nodes:
                doc_edges = [
                    e[1] for e in self.graph.graph.out_edges(kriya_id, data=True)
                    if e[2].get("relation") == "CITED_IN"
                ]
                step_doc_nodes.extend(doc_edges)
                all_doc_nodes.extend(doc_edges)

            # Create reasoning step
            if kriya_nodes:
                # Get first kriya for step tracking
                first_kriya = kriya_nodes[0]
                kriya_attrs = self.graph.graph.nodes[first_kriya]

                # Get karakas for this kriya
                karakas_matched = {}
                for edge in self.graph.graph.out_edges(first_kriya, data=True):
                    relation = edge[2].get("relation", "")
                    if relation.startswith("HAS_") or relation.startswith("USES_") or relation.startswith("TARGETS_") or relation.startswith("FROM_") or relation in ["LOCATED_IN", "OCCURS_AT"]:
                        target_node = edge[1]
                        if self.graph.graph.nodes[target_node].get("type") == "Entity":
                            karakas_matched[relation] = self.graph.graph.nodes[target_node].get("canonical_name", "")

                # Get citations for this step
                step_citations = []
                for doc_node in set(step_doc_nodes):
                    if doc_node in self.graph.graph and self.graph.graph.nodes[doc_node].get("type") == "Document":
                        doc_attrs = self.graph.graph.nodes[doc_node]
                        step_citations.append(Citation(
                            document_id=doc_attrs["doc_id"],
                            line_number=doc_attrs["line_number"],
                            original_text=doc_attrs["text"]
                        ))

                # Create reasoning step
                reasoning_step = ReasoningStep(
                    step_number=step_num,
                    description=f"Match Kriyā '{step.get('verb', 'any')}' with kārakas {step.get('karakas', {})}",
                    kriya_matched=kriya_attrs.get("verb", ""),
                    karakas_matched=karakas_matched,
                    citations=step_citations,
                    result=f"Found {len(kriya_nodes)} Kriyā(s), {len(step_citations)} citation(s)"
                )
                reasoning_trace.append(reasoning_step)

        # Retrieve text from unique Document nodes
        unique_docs = list(set(all_doc_nodes))
        doc_list = [
            {
                "doc_id": self.graph.graph.nodes[d]["doc_id"],
                "line_number": self.graph.graph.nodes[d]["line_number"],
                "text": self.graph.graph.nodes[d]["text"]
            }
            for d in unique_docs
            if d in self.graph.graph and self.graph.graph.nodes[d].get("type") == "Document"
        ]

        return doc_list, reasoning_trace

    def _find_kriyas(self, verb: Optional[str], karaka_constraints: Dict) -> List[str]:
        """Find Kriyā nodes with optimized entity-first traversal

        Args:
            verb: Verb to match (optional)
            karaka_constraints: Dict of kāraka constraints

        Returns:
            List of matching Kriyā node IDs
        """
        # OPTIMIZATION: Start from KARTA entity if available (O(k) not O(N))
        if "KARTA" in karaka_constraints and karaka_constraints["KARTA"]:
            karta_mention = karaka_constraints["KARTA"]
            canonical = self.graph.entity_resolver.resolve_entity(karta_mention)

            # Get all Kriyā nodes where this entity is KARTĀ (traverse FROM entity via incoming edges)
            if canonical in self.graph.graph:
                candidates = [
                    e[0] for e in self.graph.graph.in_edges(canonical, data=True)
                    if e[2].get("relation") == "HAS_KARTĀ"
                ]
            else:
                candidates = []
        elif verb:
            # Fallback: Filter by verb
            candidates = [
                n for n in self.graph.graph.nodes()
                if self.graph.graph.nodes[n].get("type") == "Kriya"
                and self.graph.graph.nodes[n].get("verb") == verb
            ]
        else:
            # Last resort: all Kriyā nodes
            candidates = [
                n for n in self.graph.graph.nodes()
                if self.graph.graph.nodes[n].get("type") == "Kriya"
            ]

        # Apply remaining kāraka constraints
        results = []
        for kriya_id in candidates:
            match = True

            # Check verb if not already filtered
            if verb and self.graph.graph.nodes[kriya_id].get("verb") != verb:
                continue

            # Check other kāraka constraints
            for karaka_type, required_entity in karaka_constraints.items():
                if not required_entity or karaka_type == "KARTA":  # Already filtered
                    continue

                # Resolve entity and check edge (FROM Kriyā TO Entity)
                canonical = self.graph.entity_resolver.resolve_entity(required_entity)
                relation = self._map_karaka_to_relation(karaka_type)

                # Check if edge exists (outgoing from Kriyā)
                edges = [
                    e for e in self.graph.graph.out_edges(kriya_id, data=True)
                    if e[1] == canonical and e[2].get("relation") == relation
                ]
                if not edges:
                    match = False
                    break

            if match:
                results.append(kriya_id)

        return results

    def _map_karaka_to_relation(self, karaka_type: str) -> str:
        """Map kāraka type to graph relation

        Args:
            karaka_type: Kāraka type

        Returns:
            Graph relation name
        """
        mapping = CONFIG['karaka_relation_mapping'].copy()
        mapping["ADHIKARANA"] = "LOCATED_IN"  # Default to spatial
        return mapping.get(karaka_type, "UNKNOWN")

    def _expand_causal_chain(self, kriya_nodes: List[str]) -> List[str]:
        """Follow CAUSES edges to get full causal chain

        Args:
            kriya_nodes: Initial Kriyā nodes

        Returns:
            Expanded list including causal chain
        """
        expanded = set(kriya_nodes)

        for kriya_id in kriya_nodes:
            # Follow CAUSES edges (both directions)
            # Caused by (incoming CAUSES edges)
            caused_by = [
                e[0] for e in self.graph.graph.in_edges(kriya_id, data=True)
                if e[2].get("relation") == "CAUSES"
            ]
            # Causes (outgoing CAUSES edges)
            causes = [
                e[1] for e in self.graph.graph.out_edges(kriya_id, data=True)
                if e[2].get("relation") == "CAUSES"
            ]
            expanded.update(caused_by)
            expanded.update(causes)

        return list(expanded)

    def _generate_answer(self, question: str, ground_truth_docs: List[Dict]) -> Dict:
        """Final LLM call with grounded context

        Args:
            question: User question
            ground_truth_docs: List of document dicts

        Returns:
            Dict with answer and citations
        """
        # Sort by doc_id and line_number for narrative coherence
        sorted_docs = sorted(ground_truth_docs, key=lambda d: (d["doc_id"], d["line_number"]))

        # Build context
        context = "\n".join([
            f"[{d['doc_id']}, Line {d['line_number']}]: {d['text']}"
            for d in sorted_docs
        ])

        # Single isolated LLM call
        system_prompt = PROMPTS.get("answer_generator_prompt", "")

        user_prompt = PROMPTS.get("answer_generator_user_template", "").format(
            question=question,
            context=context
        )

        try:
            answer = call_llm_isolated(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.model,
                tokenizer=self.tokenizer,
                max_tokens=200
            )

            return {
                "question": question,
                "answer": answer,
                "citations": sorted_docs,
                "status": "GROUNDED"
            }
        except Exception as e:
            print(f"  ❌ Answer generation failed: {e}")
            return {
                "question": question,
                "answer": f"Error generating answer: {e}",
                "citations": sorted_docs,
                "status": "ERROR"
            }

print("✅ QueryPipeline class defined")


# ============================================================================
# OPTIMIZATION LOGGER - Production-Ready Logging
# ============================================================================
class OptimizationLogger:
    """Track optimization performance and provide production-ready logs"""

    def __init__(self):
        self.logs = []
        self.start_time = None

    def start_document(self, doc_id: str):
        """Start timing a document"""
        self.start_time = datetime.now()

    def log_extraction(self, text: str, result: Optional[Dict], duration: float, llm_calls: int, mode: str):
        """Log a single extraction attempt

        Args:
            text: Input text
            result: Extraction result or None
            duration: Time in seconds
            llm_calls: Number of LLM calls made
            mode: "single_shot" or "gsv_retry"
        """
        # Handle both dict and None results
        confidence = 0.0
        if result:
            if isinstance(result, dict):
                confidence = result.get("data", {}).get("confidence", 0.0)
            elif isinstance(result, list):
                confidence = 0.0  # List format doesn't have confidence at top level

        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "text_preview": text[:100],
            "success": result is not None,
            "confidence": confidence,
            "duration_ms": duration * 1000,
            "llm_calls": llm_calls,
            "mode": mode
        })

    def get_stats(self) -> Dict:
        """Get aggregated statistics"""
        if not self.logs:
            return {}

        successful = [l for l in self.logs if l["success"]]

        return {
            "total_extractions": len(self.logs),
            "successful": len(successful),
            "failed": len(self.logs) - len(successful),
            "success_rate": len(successful) / len(self.logs) if self.logs else 0,
            "avg_confidence": sum(l["confidence"] for l in successful) / len(successful) if successful else 0,
            "avg_duration_ms": sum(l["duration_ms"] for l in self.logs) / len(self.logs),
            "total_llm_calls": sum(l["llm_calls"] for l in self.logs),
            "avg_llm_calls": sum(l["llm_calls"] for l in self.logs) / len(self.logs),
            "single_shot_count": sum(1 for l in self.logs if l["mode"] == "single_shot"),
            "gsv_retry_count": sum(1 for l in self.logs if l["mode"] == "gsv_retry")
        }

    def print_stats(self):
        """Print human-readable statistics"""
        stats = self.get_stats()
        if not stats:
            print("No extraction logs yet")
            return

        print("\n" + "="*80)
        print("OPTIMIZATION STATISTICS")
        print("="*80)
        print(f"Total Extractions: {stats['total_extractions']}")
        print(f"Success Rate: {stats['success_rate']*100:.1f}%")
        print(f"Avg Confidence: {stats['avg_confidence']:.2f}")
        print(f"Avg Duration: {stats['avg_duration_ms']:.1f}ms")
        print(f"Total LLM Calls: {stats['total_llm_calls']}")
        print(f"Avg LLM Calls/Extraction: {stats['avg_llm_calls']:.1f}")
        print(f"Single-Shot: {stats['single_shot_count']} ({stats['single_shot_count']/stats['total_extractions']*100:.1f}%)")
        print(f"GSV-Retry: {stats['gsv_retry_count']} ({stats['gsv_retry_count']/stats['total_extractions']*100:.1f}%)")

    def export_json(self, filepath: str = "optimization_logs.json"):
        """Export logs to JSON file for production analysis"""
        with open(filepath, 'w') as f:
            json.dump({
                "stats": self.get_stats(),
                "logs": self.logs
            }, f, indent=2)
        print(f"✅ Logs exported to {filepath}")

def extract_reasoning_trace(response: str) -> str:
    """Extract reasoning trace from <think></think> tags

    Args:
        response: LLM response

    Returns:
        Reasoning trace text or empty string
    """
    import re
    match = re.search(r'<think>(.*?)</think>', response, re.DOTALL)
    return match.group(1).strip() if match else ""

print("✅ OptimizationLogger class defined")



# ============================================================================
# CELL 10: Ingestion Pipeline Step 1 - Embed and Store Documents
# ============================================================================
print("\n" + "="*80)
print("CELL 10: INGESTION STEP 1 - EMBED AND STORE")
print("="*80)

# Always reload prompts (in case they were updated)
PROMPTS = load_yaml_prompts()

# ALWAYS recreate graph (fresh start on each run)
print("Initializing fresh KarakaGraphV2...")
karaka_graph = KarakaGraphV2(embedding_model, embedding_tokenizer)
print("✅ Graph initialized (clean slate)")

# Initialize optimization logger
print("Initializing OptimizationLogger...")
opt_logger = OptimizationLogger()
print("✅ Optimization Logger initialized")

# Always recreate GSV engine (to pick up prompt changes)
print("Initializing GSVRetryEngine...")
gsv_engine = GSVRetryEngine(
    model=llm_model,
    tokenizer=tokenizer,
    prompts=PROMPTS,
    max_retries=CONFIG['gsv_retry']['max_retries'],
    scoring_ensemble_size=CONFIG['gsv_retry']['scoring_ensemble_size'],
    logger=opt_logger
)
print("✅ GSV-Retry Engine initialized")
print(f"   Mode: {'Single-Shot' if CONFIG.get('reasoning', {}).get('enabled') and CONFIG['gsv_retry']['max_retries'] == 1 else 'GSV-Retry'}")
print(f"   Max Retries: {CONFIG['gsv_retry']['max_retries']}")
print(f"   Reasoning: {CONFIG.get('reasoning', {}).get('mode', 'off')}")
print(f"   Max Tokens: {CONFIG['llm_call']['max_tokens']}")

# Always recreate ingestion pipeline (to use new GSV engine)
print("Initializing IngestionPipeline...")
ingestion_pipeline = IngestionPipeline(
    graph=karaka_graph,
    gsv_engine=gsv_engine,
    embedding_model=embedding_model,
    embedding_tokenizer=embedding_tokenizer
)
print("✅ Ingestion Pipeline initialized")

# Load and embed documents (Step 1 only)
print("\n" + "="*80)
print("📄 STEP 1: LOADING AND EMBEDDING DOCUMENTS")
print("="*80)

docs_folder = CONFIG['file_paths']['docs_folder']
print(f"\n📂 Document folder: {docs_folder}")

refined_docs = ingestion_pipeline._load_documents(docs_folder)

if refined_docs:
    print(f"   ✅ Loaded {len(refined_docs)} document(s)")
    ingestion_pipeline._embed_and_store(refined_docs)
    print(f"\n✅ Step 1 complete: {karaka_graph.vector_store.size()} documents embedded in FAISS")
else:
    print("❌ No documents loaded - check folder path and file formats (.txt, .md)")


# ============================================================================
# CELL 11: Ingestion Pipeline Step 2 - GSV-Retry Extraction
# ============================================================================
print("\n" + "="*80)
print("CELL 11: INGESTION STEP 2 - GSV-RETRY EXTRACTION")
print("="*80)

# Extract Kriyās with GSV-Retry
if 'refined_docs' in globals() and refined_docs:
    print("\n🔍 STEP 2: EXTRACTING KRIYĀS WITH GSV-RETRY")
    print("="*80)
    ingestion_pipeline._extract_kriyas(refined_docs)

    entity_count = len([n for n in karaka_graph.graph.nodes() if karaka_graph.graph.nodes[n].get('type') == 'Entity'])

    print(f"\n✅ Step 2 complete - Extraction finished")
    print(f"\n📊 Current Graph State:")
    print(f"   Kriyās: {len(karaka_graph.kriyas)}")
    print(f"   Entities: {entity_count}")
    print(f"   Edges: {karaka_graph.graph.number_of_edges()}")
    print(f"   Success Rate: {ingestion_pipeline.stats['successful_extractions']}/{ingestion_pipeline.stats['total_lines']} ({ingestion_pipeline.stats['successful_extractions']/ingestion_pipeline.stats['total_lines']*100:.1f}%)")

    # Print optimization statistics
    if 'opt_logger' in globals():
        opt_logger.print_stats()
else:
    print("❌ No documents to process. Run CELL 8 first.")


# ============================================================================
# CELL 12: Ingestion Pipeline Step 3 - Post-Processing
# ============================================================================
print("\n" + "="*80)
print("CELL 12: INGESTION STEP 3 - POST-PROCESSING")
print("="*80)

# Run post-processing
if 'karaka_graph' in globals() and len(karaka_graph.kriyas) > 0:
    print("\n🔧 STEP 3: POST-PROCESSING")
    print("="*80)
    ingestion_pipeline.run_post_processing()

    # Print final statistics
    ingestion_pipeline._print_statistics()

    # Save graph
    print(f"\n💾 Saving graph to disk...")
    try:
        karaka_graph.save_to_file(DB_FILE)
        print(f"   ✅ Graph saved to {DB_FILE}")
        karaka_graph.export_visualization(GRAPH_VIZ_FILE)
        print(f"   ✅ Visualization exported to {GRAPH_VIZ_FILE}")
    except Exception as e:
        print(f"   ⚠️ Save failed: {str(e)[:50]}")

    print(f"\n{'='*80}")
    print(f"✅ INGESTION COMPLETE - All steps finished successfully!")
    print(f"{'='*80}")
else:
    print("❌ No graph to post-process. Run CELL 10 and 11 first.")


# ============================================================================
# CELL 13: Initialize Query Pipeline
# ============================================================================
print("\n" + "="*80)
print("CELL 13: INITIALIZE QUERY PIPELINE")
print("="*80)

# Initialize Query Pipeline
if 'query_pipeline' not in globals():
    if 'karaka_graph' in globals() and 'gsv_engine' in globals():
        print("Initializing QueryPipeline...")
        query_pipeline = QueryPipeline(
            graph=karaka_graph,
            gsv_engine=gsv_engine,
            model=llm_model,
            tokenizer=tokenizer
        )
        print("✅ Query Pipeline initialized")
    else:
        print("❌ Graph or GSV-Engine not initialized. Run CELL 10-12 first.")
else:
    print("✅ Query Pipeline already initialized")


# ============================================================================
# CELL 14: Execute Queries with QueryPipeline
# ============================================================================
print("\n" + "="*80)
print("CELL 14: EXECUTE QUERIES")
print("="*80)

# Test queries from config
test_queries = CONFIG['test_queries']

if 'query_pipeline' in globals():
    print("\n🔍 RUNNING TEST QUERIES")
    print("="*80)
    print(f"Total queries: {len(test_queries)}\n")

    query_results = []
    successful_queries = 0
    failed_queries = 0

    for i, question in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"📋 Query {i}/{len(test_queries)}")
        print(f"{'='*80}")

        try:
            result = query_pipeline.answer_query(question)
            query_results.append(result)

            print(f"\n📝 ANSWER:")
            print(f"{result['answer']}")

            if result['citations']:
                citation_limit = CONFIG['query_pipeline']['citation_limit']
                max_text_len = CONFIG['display']['max_citation_text_length']
                print(f"\n📚 CITATIONS ({len(result['citations'])}):")
                for idx, citation in enumerate(result['citations'][:citation_limit], 1):
                    print(f"  [{idx}] {citation['doc_id']}, Line {citation['line_number']}: {citation['text'][:max_text_len]}...")
                if len(result['citations']) > citation_limit:
                    print(f"  ... and {len(result['citations']) - citation_limit} more")

            if result['status'] in ['GROUNDED', 'NO_MATCH']:
                print(f"\n✅ Status: {result['status']}")
                successful_queries += 1
            else:
                print(f"\n⚠️ Status: {result['status']}")
                failed_queries += 1
        except Exception as e:
            print(f"\n❌ Query failed with error: {str(e)[:100]}")
            failed_queries += 1

    # Summary
    print(f"\n{'='*80}")
    print(f"📊 QUERY EXECUTION SUMMARY")
    print(f"{'='*80}")
    print(f"Total queries: {len(test_queries)}")
    print(f"Successful: {successful_queries}")
    print(f"Failed: {failed_queries}")
    print(f"Success rate: {successful_queries/len(test_queries)*100:.1f}%")
else:
    print("❌ Query Pipeline not initialized. Run CELL 13 first.")

print("\n" + "="*80)
print("ALL CELLS COMPLETE")
print("="*80)
