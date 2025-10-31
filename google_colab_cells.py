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
# CELL 6: Entity Resolution
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
# CELL 7: Kāraka Knowledge Graph
# ============================================================================
class KarakaGraph:
    def __init__(self, embedding_model, embedding_tokenizer):
        self.graph = nx.MultiDiGraph()
        self.entity_resolver = EntityResolver(embedding_model, embedding_tokenizer)
        self.documents = {}
        self.kriyas = {}
        self.kriya_index = defaultdict(list)
        self.entity_index = defaultdict(list)
    
    def load_from_file(self, filepath: str):
        if not os.path.exists(filepath):
            print(f"ℹ️  No existing graph found at {filepath}. Starting fresh.")
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.documents = data.get('documents', {})
        self.kriyas = data.get('kriyas', {})
        self.kriya_index = defaultdict(list, data.get('kriya_index', {}))
        self.entity_index = defaultdict(list, data.get('entity_index', {}))
        self.entity_resolver.entity_map = data.get('entity_map', {})
        
        for kriya_id, kriya_data in self.kriyas.items():
            self.graph.add_node(kriya_id, 
                                node_type='kriya',
                                verb=kriya_data['verb'],
                                doc_id=kriya_data['doc_id'],
                                line_number=kriya_data['line_number'])
            for karaka_type, entity in kriya_data['karakas'].items():
                if entity not in self.graph:
                    self.graph.add_node(entity, node_type='entity')
                self.graph.add_edge(kriya_id, entity, 
                                    relation=karaka_type,
                                    doc_id=kriya_data['doc_id'],
                                    line_number=kriya_data['line_number'])
        
        print(f"✅ Loaded graph: {len(self.kriyas)} kriyas, {len(self.entity_resolver.entity_map)} entities")
    
    def save_to_file(self, filepath: str):
        data = {
            'documents': self.documents,
            'kriyas': self.kriyas,
            'kriya_index': dict(self.kriya_index),
            'entity_index': dict(self.entity_index),
            'entity_map': self.entity_resolver.entity_map,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_kriyas': len(self.kriyas),
                'total_entities': len([n for n in self.graph.nodes() if self.graph.nodes[n].get('node_type') == 'entity']),
                'total_documents': len(self.documents)
            }
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Graph saved to {filepath}")
    
    def export_visualization(self, filepath: str):
        nx.write_gexf(self.graph, filepath)
        print(f"✅ Graph exported to {filepath}")
    
    def add_document(self, doc_id: str, metadata: Dict):
        if doc_id in self.documents:
            print(f"ℹ️  Document {doc_id} already exists. Appending new content.")
        else:
            self.documents[doc_id] = metadata
    
    def add_kriya(self, verb: str, karakas: Dict[str, str], doc_id: str, line_number: int, original_text: str) -> str:
        resolved_karakas = {
            k_type: self.entity_resolver.resolve_entity(entity)
            for k_type, entity in karakas.items()
            if entity and entity.strip()
        }
        
        for existing_id, existing_kriya in self.kriyas.items():
            if (existing_kriya['verb'] == verb and
                existing_kriya['karakas'] == resolved_karakas and
                existing_kriya['doc_id'] == doc_id and
                existing_kriya['line_number'] == line_number):
                print(f"    ↻ Duplicate kriya detected. Reusing: {existing_id}")
                return existing_id
        
        kriya_id = f"{doc_id}_L{line_number}_K{len(self.kriyas)}"
        kriya_data = {
            'verb': verb,
            'karakas': resolved_karakas,
            'doc_id': doc_id,
            'line_number': line_number,
            'original_text': original_text
        }
        self.kriyas[kriya_id] = kriya_data
        self.kriya_index[verb].append(kriya_id)
        
        self.graph.add_node(kriya_id,
                            node_type='kriya',
                            verb=verb,
                            doc_id=doc_id,
                            line_number=line_number)
        
        for karaka_type, entity in resolved_karakas.items():
            if entity not in self.graph:
                self.graph.add_node(entity, node_type='entity')
            self.graph.add_edge(kriya_id, entity,
                                relation=karaka_type,
                                doc_id=doc_id,
                                line_number=line_number)
            self.entity_index[entity].append(kriya_id)
        
        return kriya_id
    
    def find_kriyas(self, verb: Optional[str] = None, **karaka_constraints) -> List[str]:
        if verb:
            candidate_ids = self.kriya_index.get(verb, [])
        else:
            candidate_ids = list(self.kriyas.keys())
        
        results = []
        for kriya_id in candidate_ids:
            kriya = self.kriyas[kriya_id]
            match = True
            for karaka_type, required_entity in karaka_constraints.items():
                if required_entity is None:
                    continue
                resolved_query = self.entity_resolver.resolve_entity(required_entity)
                kriya_entity = kriya['karakas'].get(karaka_type)
                if kriya_entity != resolved_query:
                    match = False
                    break
            if match:
                results.append(kriya_id)
        return results
    
    def get_citation(self, kriya_id: str) -> Optional[Citation]:
        kriya = self.kriyas.get(kriya_id)
        if not kriya:
            return None
        return Citation(
            document_id=kriya['doc_id'],
            line_number=kriya['line_number'],
            original_text=kriya['original_text']
        )
    
    def get_stats(self) -> Dict:
        entity_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n].get('node_type') == 'entity']
        kriya_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n].get('node_type') == 'kriya']
        return {
            'total_documents': len(self.documents),
            'total_kriyas': len(kriya_nodes),
            'total_entities': len(entity_nodes),
            'total_edges': self.graph.number_of_edges(),
            'unique_verbs': len(self.kriya_index),
            'avg_karakas_per_kriya': self.graph.number_of_edges() / len(kriya_nodes) if kriya_nodes else 0
        }

print("✅ Graph class loaded")


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
