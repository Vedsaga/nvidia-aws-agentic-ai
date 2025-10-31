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
# CELL 7.5: Ingestion Pipeline
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
        """Load documents from folder
        
        Args:
            docs_folder: Path to folder containing documents
        
        Returns:
            Dict mapping doc_id to list of lines
        """
        if not os.path.exists(docs_folder):
            print(f"❌ ERROR: Document folder '{docs_folder}' not found!")
            return {}
        
        text_files = list(Path(docs_folder).glob("*.txt")) + list(Path(docs_folder).glob("*.md"))
        if not text_files:
            print(f"❌ ERROR: No .txt or .md files found in '{docs_folder}'")
            return {}
        
        print(f"   Found {len(text_files)} document(s)")
        
        refined_docs = {}
        
        for filepath in text_files:
            doc_path = Path(filepath)
            doc_id = doc_path.stem
            
            print(f"   📄 {doc_path.name}")
            
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            refined_docs[doc_id] = lines
            print(f"      ✓ Loaded {len(lines)} line(s)")
        
        return refined_docs
    
    def _embed_and_store(self, refined_docs: Dict[str, List[str]]):
        """Create Document nodes and FAISS embeddings
        
        Args:
            refined_docs: Dict mapping doc_id to list of lines
        """
        print(f"   Creating Document nodes and embeddings...")
        
        total_docs = sum(len(lines) for lines in refined_docs.values())
        processed = 0
        
        for doc_id, lines in refined_docs.items():
            for line_num, text in enumerate(lines, 1):
                # Create Document node
                doc_node_id = self.graph.add_document_node(doc_id, line_num, text)
                
                # Generate embedding
                embedding = self._encode_text(text)
                
                # Store in FAISS
                self.graph.vector_store.add(doc_node_id, embedding)
                
                processed += 1
                if processed % 10 == 0 or processed == total_docs:
                    print(f"      Progress: {processed}/{total_docs} documents embedded", end='\r')
        
        print(f"\n   ✅ Embedded {total_docs} documents")
    
    def _encode_text(self, text: str) -> np.ndarray:
        """Encode text using embedding model
        
        Args:
            text: Text to encode
        
        Returns:
            Embedding vector
        """
        inputs = self.embedding_tokenizer([text], padding=True, truncation=True, return_tensors='pt')
        inputs = {k: v.to(self.embedding_model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.embedding_model(**inputs)
        
        embedding = average_pool(outputs.last_hidden_state, inputs["attention_mask"])
        return embedding.cpu().numpy()[0]
    
    def _extract_kriyas(self, refined_docs: Dict[str, List[str]]):
        """Extract Kriyās from all documents using GSV-Retry
        
        Args:
            refined_docs: Dict mapping doc_id to list of lines
        """
        self.stats['total_lines'] = sum(len(lines) for lines in refined_docs.values())
        processed = 0
        
        for doc_id, lines in refined_docs.items():
            print(f"\n   📄 Processing {doc_id}...")
            
            for line_num, text in enumerate(lines, 1):
                processed += 1
                line_ref = f"{doc_id}_L{line_num}"
                
                print(f"      [{processed}/{self.stats['total_lines']}] {line_ref}: ", end='')
                
                # Extract with GSV-Retry
                golden_candidate = self.gsv_engine.extract_with_retry(
                    text=text,
                    extraction_type="kriya",
                    line_ref=line_ref
                )
                
                if golden_candidate:
                    # Write to graph
                    self._write_to_graph(golden_candidate, doc_id, line_num, text)
                    print(f"✅")
                    self.stats['successful_extractions'] += 1
                else:
                    print(f"❌ Failed")
                    self.stats['failed_extractions'] += 1
    
    def _write_to_graph(self, golden_candidate: Dict, doc_id: str, line_number: int, text: str):
        """Write verified Kriyā to graph with schema compliance
        
        Args:
            golden_candidate: Golden candidate from GSV-Retry
            doc_id: Document ID
            line_number: Line number
            text: Original text
        """
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
    
    def _print_statistics(self):
        """Print final ingestion statistics"""
        print(f"\n{'='*80}")
        print(f"INGESTION COMPLETE")
        print(f"{'='*80}")
        print(f"Total lines processed: {self.stats['total_lines']}")
        print(f"Successful extractions: {self.stats['successful_extractions']}")
        print(f"Failed extractions: {self.stats['failed_extractions']}")
        print(f"Success rate: {self.stats['successful_extractions']/self.stats['total_lines']*100:.1f}%")
        print(f"\nGraph Statistics:")
        print(f"  Total Kriyās: {self.stats['total_kriyas']}")
        print(f"  Total Entities: {len([n for n in self.graph.graph.nodes() if self.graph.graph.nodes[n].get('type') == 'Entity'])}")
        print(f"  Total Documents: {len(self.graph.documents)}")
        print(f"  Total Edges: {self.graph.graph.number_of_edges()}")
        print(f"  FAISS Index Size: {self.graph.vector_store.size()}")
        
        # GSV-Retry statistics
        gsv_stats = self.gsv_engine.get_failure_stats()
        print(f"\nGSV-Retry Statistics:")
        print(f"  Total attempts: {gsv_stats['total_attempts']}")
        print(f"  Total failures: {gsv_stats['total_failures']}")
        print(f"  Success rate: {gsv_stats['success_rate']*100:.1f}%")
    
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
        
        print(f"   Found {len(pronoun_nodes)} pronoun entities")
        resolved_count = 0
        
        for pronoun_id in pronoun_nodes:
            pronoun_name = self.graph.graph.nodes[pronoun_id].get("canonical_name", "")
            
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
                continue
            
            # Query FAISS for nearby context (5 nearest neighbors)
            context_docs = []
            for doc_node in doc_nodes[:1]:  # Use first doc as anchor
                nearby = self.graph.vector_store.query_nearby(doc_node, k=5)
                context_docs.extend(nearby)
            
            if not context_docs:
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
                    print(f"      ✓ Resolved '{pronoun_name}' → '{canonical_target}'")
        
        print(f"   ✅ Resolved {resolved_count} coreferences")
    
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
        
        system_prompt = """You are a coreference resolution expert. Given a pronoun and surrounding context, identify what entity the pronoun refers to.

Return JSON with this structure:
{
  "referent": "<entity name or null if unclear>",
  "confidence": "<high|medium|low>",
  "reasoning": "<brief explanation>"
}

Only return a referent if you are confident. Return null if unclear."""
        
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
        
        print(f"   Found {len(metaphor_entities)} potential metaphorical entities")
        linked_count = 0
        
        for metaphor_id in metaphor_entities:
            metaphor_name = self.graph.graph.nodes[metaphor_id].get("canonical_name", "")
            
            # Get context via edges
            kriya_nodes = [
                e[0] for e in self.graph.graph.in_edges(metaphor_id, data=True)
            ]
            
            if not kriya_nodes:
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
                    print(f"      ✓ Linked '{metaphor_name}' → '{canonical_target}'")
        
        print(f"   ✅ Linked {linked_count} metaphorical entities")
    
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
        
        system_prompt = """You are an expert in resolving metaphorical and descriptive references to their actual entities.

Given a metaphorical or descriptive name and context, identify the actual entity being referred to.

Return JSON:
{
  "actual_entity": "<entity name or null>",
  "confidence": "<high|medium|low>",
  "reasoning": "<explanation>"
}

Only return an entity if confident."""
        
        context_str = "\n".join([f"- {text}" for text in context_texts[:5]])
        
        user_prompt = f"""Metaphorical reference: "{metaphor}"

Context:
{context_str}

What is the actual entity being referred to?"""
        
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
        
        print(f"   Found {len(entity_nodes)} entities to type")
        typed_count = 0
        
        for entity_id in entity_nodes[:50]:  # Limit to 50 for performance
            entity_name = self.graph.graph.nodes[entity_id].get("canonical_name", "")
            
            # Get context via edges
            kriya_nodes = [
                e[0] for e in self.graph.graph.in_edges(entity_id, data=True)
            ]
            
            if not kriya_nodes:
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
            
            # Determine entity type
            entity_type = self._determine_entity_type(entity_name, context_texts)
            
            if entity_type:
                # Add entity_type attribute
                self.graph.graph.nodes[entity_id]["entity_type"] = entity_type
                typed_count += 1
                
                if typed_count % 10 == 0:
                    print(f"      Progress: {typed_count} entities typed", end='\r')
        
        print(f"\n   ✅ Typed {typed_count} entities")
    
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
        
        system_prompt = """You are an entity type classifier. Given an entity name and context, classify it into ONE of these types:

- Person: Human individuals
- Deity: Gods, goddesses, divine beings
- Location: Places, cities, forests, mountains
- Organization: Groups, armies, kingdoms
- Object: Physical objects, weapons, artifacts
- Concept: Abstract concepts, emotions, qualities
- Animal: Animals, creatures
- Event: Named events, battles, ceremonies

Return JSON:
{
  "entity_type": "<type from list above>",
  "confidence": "<high|medium|low>",
  "reasoning": "<brief explanation>"
}"""
        
        context_str = "\n".join([f"- {text}" for text in context_texts[:3]])
        
        user_prompt = f"""Entity: "{entity_name}"

Context:
{context_str}

What type is this entity?"""
        
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
        
        print(f"   Analyzing {len(kriya_nodes)} Kriyā nodes for causality")
        causal_count = 0
        
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
                
                checked += 1
                if checked % 20 == 0:
                    print(f"      Progress: {checked} pairs checked, {causal_count} causal links found", end='\r')
        
        print(f"\n   ✅ Found {causal_count} causal relationships")
    
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
        
        system_prompt = """You are a causal relationship detector. Given two actions and their contexts, determine if one causes the other.

Return JSON:
{
  "is_causal": <true|false>,
  "direction": "<forward|backward|null>",
  "confidence": "<high|medium|low>",
  "reasoning": "<brief explanation>"
}

Direction:
- "forward": First action causes second action
- "backward": Second action causes first action
- null: No causal relationship"""
        
        user_prompt = f"""Action 1: "{verb1}"
Context 1: {text1}

Action 2: "{verb2}"
Context 2: {text2}

Is there a causal relationship between these actions?"""
        
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
# CELL 8.5: Query Pipeline Implementation
# ============================================================================
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
            Dict with answer, citations, status
        """
        print(f"\n{'='*80}")
        print(f"QUERY: {question}")
        print(f"{'='*80}")
        
        # Step 1: Decompose with GSV-Retry
        print("\n[Step 1] Decomposing query with GSV-Retry...")
        golden_plan = self.gsv_engine.extract_with_retry(
            text=question,
            extraction_type="query",
            line_ref="query"
        )
        
        if not golden_plan:
            return {
                "question": question,
                "answer": "Failed to decompose query after multiple attempts",
                "citations": [],
                "status": "ERROR"
            }
        
        print(f"  ✓ Golden Plan: {json.dumps(golden_plan['data'], indent=2)}")
        
        # Step 2: Execute graph traversal
        print("\n[Step 2] Executing graph traversal...")
        ground_truth_docs = self._execute_traversal(golden_plan["data"])
        
        if not ground_truth_docs:
            return {
                "question": question,
                "answer": "No answer found in knowledge graph",
                "citations": [],
                "status": "NO_MATCH"
            }
        
        print(f"  ✓ Found {len(ground_truth_docs)} relevant document(s)")
        
        # Step 3: Generate grounded answer
        print("\n[Step 3] Generating grounded answer...")
        return self._generate_answer(question, ground_truth_docs)
    
    def _execute_traversal(self, query_plan: Dict) -> List[Dict]:
        """Translate plan to NetworkX operations and execute
        
        Args:
            query_plan: Query plan from GSV-Retry
        
        Returns:
            List of document dicts with text and citations
        """
        all_doc_nodes = []
        steps = query_plan.get("steps", [])
        
        if not steps:
            # Fallback: treat as single step
            steps = [query_plan]
        
        for step in steps:
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
            
            # Get cited documents
            for kriya_id in kriya_nodes:
                doc_edges = [
                    e[1] for e in self.graph.graph.out_edges(kriya_id, data=True)
                    if e[2].get("relation") == "CITED_IN"
                ]
                all_doc_nodes.extend(doc_edges)
        
        # Retrieve text from unique Document nodes
        unique_docs = list(set(all_doc_nodes))
        return [
            {
                "doc_id": self.graph.graph.nodes[d]["doc_id"],
                "line_number": self.graph.graph.nodes[d]["line_number"],
                "text": self.graph.graph.nodes[d]["text"]
            }
            for d in unique_docs
            if d in self.graph.graph and self.graph.graph.nodes[d].get("type") == "Document"
        ]
    
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
        mapping = {
            "KARTA": "HAS_KARTĀ",
            "KARMA": "HAS_KARMA",
            "KARANA": "USES_KARANA",
            "SAMPRADANA": "TARGETS_SAMPRADĀNA",
            "APADANA": "FROM_APĀDĀNA",
            "ADHIKARANA": "LOCATED_IN",  # Default to spatial
            "ADHIKARANA_SPATIAL": "LOCATED_IN",
            "ADHIKARANA_TEMPORAL": "OCCURS_AT"
        }
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
        system_prompt = """You are a precise answer generator. Form a natural answer using ONLY the provided context.

Rules:
- Use only information from the context
- Keep it concise
- Cite sources
- Do not add information not in the context"""
        
        user_prompt = f"""Question: {question}

Context:
{context}

Natural Answer:"""
        
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

