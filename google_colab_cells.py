# ============================================================================
# CELL 1: Setup & Dependencies
# ============================================================================
print("Installing required libraries...")
!pip install transformers torch accelerate networkx faiss-cpu -q
print("✅ Dependencies installed.")

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModel
import json
import re
import os
import sys
import networkx as nx
import faiss
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import numpy as np
from collections import defaultdict

ENTITY_SIMILARITY_THRESHOLD = 0.85
DB_FILE = "karaka_graph.json"
GRAPH_VIZ_FILE = "karaka_graph.gexf"

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
    print("Loading Llama-3.1-Nemotron-Nano-8B-v1...")
    model_id = "nvidia/Llama-3.1-Nemotron-Nano-8B-v1"
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    tokenizer.pad_token_id = tokenizer.eos_token_id
    
    # Try bfloat16 first, fallback to float16 if not supported
    try:
        llm_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True
        )
    except Exception as e:
        print(f"⚠️  bfloat16 not supported, using float16: {e}")
        llm_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )
    print("✅ LLM loaded")
else:
    print("✅ Models already loaded — reusing.")

if 'embedding_model' not in globals():
    print("Loading llama-3.2-nv-embedqa-1b-v2 for embeddings...")
    embedding_tokenizer = AutoTokenizer.from_pretrained("nvidia/llama-3.2-nv-embedqa-1b-v2")
    embedding_model = AutoModel.from_pretrained("nvidia/llama-3.2-nv-embedqa-1b-v2", trust_remote_code=True)
    embedding_model = embedding_model.to("cuda" if torch.cuda.is_available() else "cpu")
    embedding_model.eval()
    print("✅ Embedding model loaded")

def average_pool(last_hidden_states, attention_mask):
    """Average pooling with attention mask for NVIDIA embedding model."""
    last_hidden_states_masked = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    embedding = last_hidden_states_masked.sum(dim=1) / attention_mask.sum(dim=1)[..., None]
    embedding = F.normalize(embedding, dim=-1)
    return embedding


# ============================================================================
# CELL 3: Core Functions - Session-Isolated LLM Calls
# ============================================================================
def call_llm_isolated(system_prompt: str, user_prompt: str, model, tokenizer, max_tokens: int = 300) -> str:
    """Each call creates a fresh session - no conversation history"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=max_tokens,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=False,
        temperature=0.0
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

print("✅ Core functions loaded")


# ============================================================================
# CELL 4: FAISS Vector Store Implementation
# ============================================================================
class FAISSVectorStore:
    """Wrapper for FAISS index with document ID mapping"""
    
    def __init__(self, dimension: int = 768):
        """Initialize FAISS index
        
        Args:
            dimension: Embedding dimension (default 768 for Llama-3.2-NV-EmbedQA-1B-v2)
        """
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.doc_id_map = []  # Maps FAISS index position to doc_id
        self.doc_id_to_idx = {}  # Maps doc_id to FAISS index position
    
    def add(self, doc_id: str, embedding: np.ndarray) -> None:
        """Add document embedding to FAISS index
        
        Args:
            doc_id: Unique document identifier (e.g., "doc1_L5")
            embedding: Embedding vector (shape: (dimension,))
        """
        # Ensure embedding is 2D array for FAISS
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        
        # Ensure correct dtype
        embedding = embedding.astype('float32')
        
        # Add to index
        idx = len(self.doc_id_map)
        self.index.add(embedding)
        self.doc_id_map.append(doc_id)
        self.doc_id_to_idx[doc_id] = idx
    
    def query_nearby(self, doc_id: str, k: int = 5) -> List[str]:
        """Query k nearest neighbors of a document
        
        Args:
            doc_id: Document ID to query neighbors for
            k: Number of neighbors to return
        
        Returns:
            List of doc_ids of k nearest neighbors (excluding query doc itself)
        """
        if doc_id not in self.doc_id_to_idx:
            return []
        
        # Get embedding vector for this doc
        idx = self.doc_id_to_idx[doc_id]
        query_vector = self.index.reconstruct(idx).reshape(1, -1)
        
        # Query k+1 neighbors (to exclude self)
        distances, indices = self.index.search(query_vector, k + 1)
        
        # Filter out the query document itself and return doc_ids
        nearby_doc_ids = []
        for i in indices[0]:
            if i < len(self.doc_id_map) and self.doc_id_map[i] != doc_id:
                nearby_doc_ids.append(self.doc_id_map[i])
                if len(nearby_doc_ids) >= k:
                    break
        
        return nearby_doc_ids
    
    def size(self) -> int:
        """Return number of vectors in index"""
        return self.index.ntotal

print("✅ FAISSVectorStore class defined")


# ============================================================================
# CELL 5: Graph Schema Validation
# ============================================================================
class GraphSchema:
    """Strict schema enforcement for Karaka knowledge graph"""
    
    NODE_TYPES = {"Kriya", "Entity", "Document"}
    
    EDGE_RELATIONS = {
        "HAS_KARTĀ",           # Kriyā → Entity (agent)
        "HAS_KARMA",           # Kriyā → Entity (patient)
        "USES_KARANA",         # Kriyā → Entity (instrument)
        "TARGETS_SAMPRADĀNA",  # Kriyā → Entity (recipient)
        "FROM_APĀDĀNA",        # Kriyā → Entity (source)
        "LOCATED_IN",          # Kriyā → Entity (spatial location)
        "OCCURS_AT",           # Kriyā → Entity (temporal location)
        "IS_SAME_AS",          # Entity → Entity (coreference)
        "CAUSES",              # Kriyā → Kriyā (causality)
        "CITED_IN"             # Kriyā → Document (provenance)
    }
    
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

print("✅ Graph schema loaded")


# ============================================================================
# CELL 6: GSV-Retry Engine
# ============================================================================
class GSVRetryEngine:
    """Generate-Score-Verify-Retry engine for robust extraction with cross-validation"""
    
    def __init__(self, model, tokenizer, prompts: dict, max_retries: int = 5):
        """Initialize GSV-Retry engine
        
        Args:
            model: LLM model for generation
            tokenizer: Tokenizer for the model
            prompts: Dictionary of prompts (extraction, scoring, verification, feedback)
            max_retries: Maximum retry attempts (default 5)
        """
        self.model = model
        self.tokenizer = tokenizer
        self.prompts = prompts
        self.max_retries = max_retries
        self.failure_stats = {
            'total_attempts': 0,
            'total_failures': 0,
            'failure_reasons': defaultdict(int)
        }
    
    def extract_with_retry(self, text: str, extraction_type: str = "kriya", line_ref: str = "") -> Optional[Dict]:
        """Main GSV-Retry loop with fast-path optimization
        
        Args:
            text: Input text to extract from
            extraction_type: Type of extraction ("kriya" or "query")
            line_ref: Reference for logging (e.g., "doc1_L5")
        
        Returns:
            Golden Candidate dict or None if all retries exhausted
        """
        self.failure_stats['total_attempts'] += 1
        feedback_prompt = ""
        failure_log = []
        
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
            # GENERATE: 3 candidates (isolated LLM calls)
            candidates = self._generate_candidates(text, base_prompt, feedback_prompt)
            
            if not candidates:
                feedback_prompt = "Previous attempt produced no valid candidates. Please ensure JSON output is valid."
                failure_log.append({
                    "attempt": attempt + 1,
                    "error": "No valid candidates generated",
                    "feedback": feedback_prompt
                })
                continue
            
            # FAST-PATH: Score only first candidate initially
            first_score = self._get_robust_score(candidates[0], scoring_prompt)
            
            if first_score >= 95:
                # High confidence - verify immediately (fast path: 4 LLM calls total)
                verifier_choice = self._get_blind_verification([candidates[0]], verification_prompt)
                if verifier_choice == candidates[0]["id"]:
                    return candidates[0]  # Fast-path success
            
            # FULL-PATH: Score all candidates
            scores = [first_score] + [self._get_robust_score(c, scoring_prompt) for c in candidates[1:]]
            
            # VERIFY: Blind verification
            verifier_choice = self._get_blind_verification(candidates, verification_prompt)
            
            # CROSS-VALIDATE
            highest_idx = scores.index(max(scores))
            if candidates[highest_idx]["id"] == verifier_choice:
                return candidates[highest_idx]  # Golden Candidate found
            
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
        
        for i in range(3):
            try:
                response = call_llm_isolated(
                    system_prompt=full_prompt,
                    user_prompt=text,
                    model=self.model,
                    tokenizer=self.tokenizer,
                    max_tokens=400
                )
                
                parsed_data = parse_json_response(response)
                if parsed_data:
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
        """Ensemble scoring with 3 calls and validation
        
        Args:
            candidate: Candidate dict to score
            scoring_prompt: Scoring prompt template
        
        Returns:
            Average score (1-100)
        """
        scores = []
        
        for attempt in range(3):
            try:
                response = call_llm_isolated(
                    system_prompt=scoring_prompt,
                    user_prompt=json.dumps(candidate["data"], indent=2),
                    model=self.model,
                    tokenizer=self.tokenizer,
                    max_tokens=200
                )
                
                score_data = parse_json_response(response)
                if score_data and isinstance(score_data, dict):
                    score = self._validate_score(score_data.get("score"))
                    if score is not None:
                        scores.append(score)
            except Exception as e:
                print(f"      ⚠️ Scoring attempt {attempt+1} failed: {e}")
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
    
    def _get_blind_verification(self, candidates: List[Dict], verification_prompt: str) -> str:
        """Single blind verification call
        
        Args:
            candidates: List of candidates to verify
            verification_prompt: Verification prompt
        
        Returns:
            Candidate ID (e.g., "Candidate_A") or "ALL_INVALID"
        """
        try:
            # Build context with only candidate data (no scores)
            context = json.dumps([
                {"id": c["id"], "data": c["data"]} 
                for c in candidates
            ], indent=2)
            
            response = call_llm_isolated(
                system_prompt=verification_prompt,
                user_prompt=context,
                model=self.model,
                tokenizer=self.tokenizer,
                max_tokens=300
            )
            
            result = parse_json_response(response)
            if result and isinstance(result, dict):
                choice = result.get("choice", "ALL_INVALID")
                return choice
        except Exception as e:
            print(f"      ⚠️ Verification failed: {e}")
        
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
    
    def _log_failure(self, text: str, failure_log: List[Dict], line_ref: str, extraction_type: str):
        """Log detailed failure diagnostics
        
        Args:
            text: Original input text
            failure_log: List of failure attempt details
            line_ref: Line reference for context
            extraction_type: Type of extraction
        """
        print(f"\n      ❌ GSV-Retry FAILED after {self.max_retries} attempts at {line_ref}")
        print(f"      Text: \"{text[:100]}...\"" if len(text) > 100 else f"      Text: \"{text}\"")
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
# CELL 6.5: Entity Resolution
# ============================================================================
class EntityResolver:
    def __init__(self, embedding_model, embedding_tokenizer, threshold: float = ENTITY_SIMILARITY_THRESHOLD):
        self.model = embedding_model
        self.tokenizer = embedding_tokenizer
        self.threshold = threshold
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
        self.vector_store = FAISSVectorStore(dimension=768)
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
                max_hops: int = 3, direction: str = "out") -> List[str]:
        """Multi-hop graph traversal with edge filtering
        
        Args:
            start_node: Starting node ID
            edge_filter: List of relation types to follow (None = all)
            max_hops: Maximum traversal depth
            direction: "out" (outgoing), "in" (incoming), or "both"
        
        Returns:
            List of reachable node IDs
        """
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
                relation_map = {
                    "KARTA": "HAS_KARTĀ",
                    "KARMA": "HAS_KARMA",
                    "KARANA": "USES_KARANA",
                    "SAMPRADANA": "TARGETS_SAMPRADĀNA",
                    "APADANA": "FROM_APĀDĀNA",
                    "ADHIKARANA_SPATIAL": "LOCATED_IN",
                    "ADHIKARANA_TEMPORAL": "OCCURS_AT"
                }
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
# CELL 8: INGESTION STEP 1 - Load & Refine Documents
# ============================================================================
def load_and_refine_documents(docs_folder: str = "./test_documents") -> Dict[str, List[str]]:
    """
    Step 1: Load documents and split into sentences
    Returns: {doc_id: [sentence1, sentence2, ...]}
    """
    if not os.path.exists(docs_folder):
        print(f"❌ ERROR: Document folder '{docs_folder}' not found!")
        return {}
    
    text_files = list(Path(docs_folder).glob("*.txt")) + list(Path(docs_folder).glob("*.md"))
    if not text_files:
        print(f"❌ ERROR: No .txt or .md files found in '{docs_folder}'")
        return {}
    
    print(f"\n{'='*80}")
    print(f"INGESTION STEP 1: Loading & Refining Documents")
    print(f"{'='*80}")
    print(f"Found {len(text_files)} document(s)")
    
    refined_docs = {}
    
    for filepath in text_files:
        doc_path = Path(filepath)
        doc_id = doc_path.stem
        
        print(f"\n📄 Processing: {doc_path.name}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        refined_docs[doc_id] = lines
        print(f"   ✓ Loaded {len(lines)} line(s)")
    
    # Save refined documents
    with open("refined_documents.json", 'w') as f:
        json.dump(refined_docs, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Refined documents saved to: refined_documents.json")
    return refined_docs

# Execute Step 1
refined_docs = load_and_refine_documents()


# ============================================================================
# CELL 9: INGESTION STEP 2 - Extract Kārakas from Sentences
# ============================================================================
def extract_karakas_from_sentence(sentence: str, model, tokenizer) -> List[Dict]:
    """
    Isolated LLM call to extract Kārakas from a single sentence
    Each call is a fresh session
    """
    system_prompt = """You are a semantic role labeling expert using Pāṇinian Kāraka framework.
Extract ALL verbs and their semantic roles. Use ONLY these Kāraka types when applicable:

KARTA - Agent (who does)
KARMA - Patient (what is affected)
KARANA - Instrument (using what)
SAMPRADANA - Recipient (to whom)
APADANA - Source (from where/whom)
ADHIKARANA - Location/Time (where/when)

Return JSON array ONLY:
[{"verb": "base_form", "karakas": {"KARTA": "entity", ...}}]

Rules:
- Use base verb forms (give not gave)
- Extract entities exactly as mentioned
- Keep pronouns as-is
- Omit absent roles"""

    user_prompt = f"Sentence: {sentence}\nJSON:"
    
    response = call_llm_isolated(system_prompt, user_prompt, model, tokenizer, max_tokens=300)
    result = parse_json_response(response)
    
    return result if isinstance(result, list) else []

def ingest_karakas_to_graph(refined_docs: Dict[str, List[str]], graph: KarakaGraph, model, tokenizer):
    """
    Step 2: Extract Kārakas from each sentence and add to graph
    """
    print(f"\n{'='*80}")
    print(f"INGESTION STEP 2: Extracting Kārakas & Building Graph")
    print(f"{'='*80}")
    
    for doc_id, lines in refined_docs.items():
        print(f"\n{'─'*80}")
        print(f"📄 Document: {doc_id}")
        print(f"{'─'*80}")
        
        graph.add_document(doc_id, {
            'doc_id': doc_id,
            'total_lines': len(lines),
            'ingestion_time': datetime.now().isoformat()
        })
        
        for line_num, text in enumerate(lines, start=1):
            print(f"\n   Line {line_num}: \"{text}\"")
            
            # Isolated LLM call - fresh session
            kriyas_extracted = extract_karakas_from_sentence(text, model, tokenizer)
            
            if not kriyas_extracted:
                print(f"      ⚠️ No kriyas extracted")
                continue
            
            for kriya_data in kriyas_extracted:
                verb = kriya_data.get('verb', '').strip()
                karakas = kriya_data.get('karakas', {})
                if not verb:
                    continue
                
                kriya_id = graph.add_kriya(
                    verb=verb,
                    karakas=karakas,
                    doc_id=doc_id,
                    line_number=line_num,
                    original_text=text
                )
                print(f"      ✓ Kriya: {verb} | {karakas} → {kriya_id}")
    
    graph.save_to_file(DB_FILE)
    graph.export_visualization(GRAPH_VIZ_FILE)
    
    stats = graph.get_stats()
    print(f"\n{'='*80}")
    print(f"GRAPH STATISTICS")
    print(f"{'='*80}")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\n✅ Graph saved to: {DB_FILE}")
    print(f"✅ Visualization saved to: {GRAPH_VIZ_FILE}")

# Execute Step 2
karaka_graph = KarakaGraph(embedding_model, embedding_tokenizer)
karaka_graph.load_from_file(DB_FILE)
ingest_karakas_to_graph(refined_docs, karaka_graph, llm_model, tokenizer)


# ============================================================================
# CELL 10: QUERY STEP 1 - Decompose Query into Kārakas
# ============================================================================
def decompose_query_to_karakas(question: str, model, tokenizer) -> Optional[Dict]:
    """
    Isolated LLM call to break query into Kāraka search plan
    Fresh session - no history
    """
    system_prompt = """Analyze the question and create a Kāraka-based search plan.

Return JSON object with "steps" array:
{
  "steps": [
    {
      "goal": "description",
      "verb": "verb_to_find or null",
      "karakas": {"KARTA": "entity or null", "KARMA": "entity or null", ...},
      "extract": "which Kāraka role contains the answer"
    }
  ]
}

Example:
Q: "What weapon did Rama use to kill Ravana?"
A: {"steps": [{"goal": "Find killing action", "verb": "kill", "karakas": {"KARTA": "Rama", "KARMA": "Ravana", "KARANA": null}, "extract": "KARANA"}]}"""

    user_prompt = f"Question: {question}\nJSON:"
    
    response = call_llm_isolated(system_prompt, user_prompt, model, tokenizer, 400)
    result = parse_json_response(response)
    
    # Handle if LLM returns array instead of object
    if isinstance(result, list):
        return {"steps": result}
    return result

print("✅ Query decomposition function loaded")


# ============================================================================
# CELL 11: QUERY STEP 2 - Execute Search & Extract References
# ============================================================================
def execute_search_and_extract(search_plan: Dict, graph: KarakaGraph) -> Dict:
    """
    Step 2: Execute graph search and extract nodes with references
    Returns: answer, citations, reasoning steps
    """
    if not search_plan or not isinstance(search_plan, dict) or 'steps' not in search_plan:
        if isinstance(search_plan, list):
            search_plan = {"steps": search_plan}
        else:
            return {
                'answer': None,
                'reasoning': [],
                'citations': [],
                'status': 'FAILED_TO_PARSE_QUERY'
            }
    
    reasoning_steps = []
    steps = search_plan.get('steps', [])
    
    for i, step_info in enumerate(steps, 1):
        verb = step_info.get('verb')
        karakas = step_info.get('karakas', {})
        extract_role = step_info.get('extract')
        
        constraints = {k: v for k, v in karakas.items() if v}
        matching_kriyas = graph.find_kriyas(verb=verb, **constraints)
        
        print(f"  Step {i}: Found {len(matching_kriyas)} matching kriya(s)")
        
        if not matching_kriyas:
            continue
        
        for kriya_id in matching_kriyas:
            kriya = graph.kriyas[kriya_id]
            answer = kriya['karakas'].get(extract_role)
            
            if answer:
                citation = graph.get_citation(kriya_id)
                reasoning_steps.append(ReasoningStep(
                    step_number=i,
                    description=step_info.get('goal', ''),
                    kriya_matched=kriya_id,
                    karakas_matched=kriya['karakas'],
                    citations=[citation],
                    result=answer
                ))
                
                return {
                    'answer': answer,
                    'reasoning': [asdict(step) for step in reasoning_steps],
                    'citations': [asdict(citation)],
                    'status': 'GROUNDED'
                }
    
    return {
        'answer': None,
        'reasoning': [asdict(step) for step in reasoning_steps],
        'citations': [],
        'status': 'NO_MATCH'
    }

print("✅ Search execution function loaded")


# ============================================================================
# CELL 12: QUERY STEP 3 - Form Answer with Citations
# ============================================================================
def form_answer_with_citations(question: str, search_result: Dict, model, tokenizer) -> Dict:
    """
    Step 3: Use LLM to form natural answer with citations
    Isolated session - fresh call
    """
    if not search_result['answer']:
        return {
            'question': question,
            'answer': "I cannot find an answer in the knowledge graph.",
            'citations': [],
            'reasoning': search_result['reasoning'],
            'status': search_result['status']
        }
    
    # Build context from citations
    context_parts = []
    for cite in search_result['citations']:
        context_parts.append(f"[{cite['document_id']}, Line {cite['line_number']}]: \"{cite['original_text']}\"")
    
    context = "\n".join(context_parts)
    extracted_answer = search_result['answer']
    
    system_prompt = """You are a precise answer generator. Form a natural answer using ONLY the provided information.

Rules:
- Use the extracted answer and context
- Keep it concise
- Do not add information not in the context
- Cite the source"""

    user_prompt = f"""Question: {question}
Extracted Answer: {extracted_answer}
Context:
{context}

Natural Answer:"""
    
    response = call_llm_isolated(system_prompt, user_prompt, model, tokenizer, 200)
    
    return {
        'question': question,
        'answer': response,
        'raw_answer': extracted_answer,
        'citations': search_result['citations'],
        'reasoning': search_result['reasoning'],
        'status': search_result['status']
    }

print("✅ Answer formation function loaded")


# ============================================================================
# CELL 13: Complete Query Pipeline
# ============================================================================
def query_pipeline(question: str, graph: KarakaGraph, model, tokenizer) -> Dict:
    """
    Complete query pipeline with isolated LLM sessions
    """
    print(f"\n{'='*80}")
    print(f"QUERY: {question}")
    print(f"{'='*80}")
    
    # Step 1: Decompose query (isolated session)
    print("\n[Step 1] Decomposing query into Kārakas...")
    search_plan = decompose_query_to_karakas(question, model, tokenizer)
    
    if search_plan:
        print(f"  ✓ Search plan: {json.dumps(search_plan, indent=2)}")
    else:
        print(f"  ⚠️ Failed to parse query")
    
    # Step 2: Execute search
    print("\n[Step 2] Executing graph search...")
    search_result = execute_search_and_extract(search_plan, graph)
    
    # Step 3: Form answer (isolated session)
    print("\n[Step 3] Forming natural answer...")
    final_result = form_answer_with_citations(question, search_result, model, tokenizer)
    
    return final_result

print("✅ Query pipeline loaded")


# ============================================================================
# CELL 14: Run Queries
# ============================================================================
print(f"\n{'='*80}")
print(f"QUERY PHASE (Each LLM call is isolated)")
print(f"{'='*80}")

test_queries = [
    "Who gave what to whom?",
    "What weapon was used to kill Ravana?",
    "Who killed Ravana?",
    "What did Rama give to Lakshmana?"
]

all_results = []
for query in test_queries:
    result = query_pipeline(query, karaka_graph, llm_model, tokenizer)
    
    print(f"\n{'─'*80}")
    print(f"Question: {result['question']}")
    print(f"Answer: {result['answer']}")
    print(f"Status: {result['status']}")
    
    if result['citations']:
        print(f"\nCitations:")
        for cite in result['citations']:
            print(f"  📄 {cite['document_id']}, Line {cite['line_number']}: \"{cite['original_text']}\"")
    
    all_results.append(result)

# Save results
with open("query_results.json", 'w') as f:
    json.dump({'queries': all_results, 'timestamp': datetime.now().isoformat()}, f, indent=2)

print(f"\n{'='*80}")
print(f"✅ COMPLETE")
print(f"{'='*80}")
print(f"  Graph: {DB_FILE}")
print(f"  Visualization: {GRAPH_VIZ_FILE}")
print(f"  Results: query_results.json")
