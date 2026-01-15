"""
QA Engine for Kāraka Frame Graph POC.
Implements a 2-Phase RAG Pipeline:
1. Query Planning: NLP -> Search Filters
2. Answer Synthesis: Filtered Frames -> Answer
"""

import json
from typing import Optional, List, Dict, Any
from llm_client import call_llm
from frame_store import FrameStore, get_store
from frame_extractor import Frame

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: QUERY PLANNING PROMPT
# ═══════════════════════════════════════════════════════════════════════════════
QUERY_PLANNER_PROMPT = """You are a Search Query Generator for a Kāraka Frame Database.
Your job is to convert a natural language question into key terms to search the database.

Database Info:
- Contains event frames (actions)
- Fields: Kriyā (verb), Kartā (agent), Karma (object), etc.

Refining Rules:
1. Identify the core action (Kriyā) in the question. Include the root and synonyms.
2. Identify any specific entities (names, places, dates) mentioned.
3. Ignore stop words (the, a, is).

Example 1:
Question: "Who discovered a protein in Mumbai?"
Output:
{
  "kriya_keywords": ["discover", "find", "locate"],
  "entity_keywords": ["protein", "Mumbai"],
  "reasoning": "Searching for discovery events involving protein or Mumbai"
}

Example 2:
Question: "What did the ERC fund?"
Output:
{
  "kriya_keywords": ["fund", "grant", "support"],
  "entity_keywords": ["ERC", "European Research Council"],
  "reasoning": "Searching for funding actions by ERC"
}

Respond ONLY with JSON.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: ANSWER SYNTHESIS PROMPT (Schema-Aware)
# ═══════════════════════════════════════════════════════════════════════════════
ANSWER_SYNTHESIS_PROMPT = """You are a Question-Answering system for a Kāraka Frame Graph database.

## PĀṆINIAN SEMANTICS & INTERROGATIVES
Systematically map the question to Kāraka roles:

| Question | Role to Find |
|---|---|
| Who? (Agent) | **Kartā** |
| Whom/What? (Object) | **Karma** |
| By what? (Instrument) | **Karaṇa** |
| To whom? (Recipient) | **Sampradāna** |
| From where? | **Apādāna** |
| Where? | **Locus_Space** |
| When? | **Locus_Time** |

## FRAME STRUCTURE
Each frame is an EVENT.
- Passive voice: Grammatical subject = Karma. Agent = Kartā (or NULL).
- NULL Kartā means "Agent unstated".

## YOUR TASK
1. Read the user question.
2. Analyze the RELEVANT FRAMES provided (these were retrieved by a search engine).
3. Extract the answer based on the role mapping.

## OUTPUT FORMAT
```json
{
  "interrogative_type": "who/what/where/when...",
  "mapped_karaka": "Kartā/Karma...",
  "reasoning": "Chain of thought...",
  "matched_frame_ids": ["F0"],
  "answer": "Natural language answer...",
  "confidence": "high/medium/low"
}
```
"""

async def plan_query(question: str) -> Dict[str, Any]:
    """Phase 1: Generate search filters from question."""
    prompt = f"{QUERY_PLANNER_PROMPT}\n\nQuestion: \"{question}\"\n"
    
    try:
        response = await call_llm(prompt, "Generte JSON query plan", temperature=0.1, json_mode=True)
        # Parse JSON
        start = response.find("{")
        end = response.rfind("}") + 1
        data = json.loads(response[start:end])
        return data
    except Exception as e:
        print(f"⚠️ Query planning failed: {e}")
        # Fallback: simple keyword search on the question itself
        return {
            "kriya_keywords": [],
            "entity_keywords": [w for w in question.split() if len(w) > 3],
            "reasoning": "Fallback keyword search"
        }

def search_frames(store: FrameStore, plan: Dict[str, Any]) -> List[Frame]:
    """Phase 2: Filter frames based on plan + Graph Expansion."""
    all_frames = store.get_all_frames()
    
    kriyas = [k.lower() for k in plan.get("kriya_keywords", [])]
    entities = [e.lower() for e in plan.get("entity_keywords", [])]
    
    if not kriyas and not entities:
        return all_frames # Return all if no specific filter
        
    # 1. Direct Search (Keyword/Vector phase)
    hits = []
    
    for f in all_frames:
        score = 0
        
        # Check Kriyā (Verb)
        if f.kriya and any(k in f.kriya.lower() for k in kriyas):
            score += 3
        if f.kriya_surface and any(k in f.kriya_surface.lower() for k in kriyas):
            score += 3
            
        # Check Content (Entities)
        frame_text = f.sentence_text.lower()
        # Also check specific roles values
        role_values = " ".join([
            str(v) for k, v in f.__dict__.items() 
            if k in ['karta', 'karma', 'locus_space', 'locus_time', 'sampradana'] and v
        ]).lower()
        
        for entity in entities:
            if entity in frame_text or entity in role_values:
                score += 2
                
        if score > 0:
            hits.append((score, f))
            
    # Sort by score and take top matches
    hits.sort(key=lambda x: x[0], reverse=True)
    direct_matches = [h[1] for h in hits] # Take top 10 or threshold
    
    # 2. Graph Expansion (The "Hop")
    # Retrieve neighbors connected via causal_links to bridge reasoning gaps
    expanded_pool = {f.frame_id: f for f in direct_matches}
    
    for frame in direct_matches:
        if not frame.causal_links:
            continue
            
        for link in frame.causal_links:
            # Check for cause_frame (parent) and effect_frame (child)
            # We expand in BOTH directions to find context
            neighbor_ids = []
            if link.get("cause_frame"): neighbor_ids.append(link.get("cause_frame"))
            if link.get("effect_frame"): neighbor_ids.append(link.get("effect_frame"))
            
            for nid in neighbor_ids:
                if nid and nid not in expanded_pool:
                    neighbor = store.get_frame(nid)
                    if neighbor:
                        expanded_pool[nid] = neighbor
                        print(f"     🔗 Graph Hop: Expanded from {frame.frame_id} to {nid}")

    return list(expanded_pool.values())

async def ask(question: str, store: Optional[FrameStore] = None) -> dict:
    """
    Main Q&A Entry Point: 2-Phase Pipeline.
    """
    store = store or get_store()
    all_frames = store.get_all_frames()
    
    print(f"\n❓ Question: {question}")
    print(f"  📊 Total DB: {len(all_frames)} frames")
    
    if not all_frames:
        return _empty_response(question)

    import time
    start_total = time.perf_counter()

    # ─────────────────────────────────────────────────────
    # PHASE 1: PLAN QUERY
    # ─────────────────────────────────────────────────────
    t0 = time.perf_counter()
    print("  🧠 Phase 1: Planning Query...")
    plan = await plan_query(question)
    t1 = time.perf_counter()
    print(f"     ⏱️ Planning took {t1-t0:.2f}s")
    print(f"     Target Kriya: {plan.get('kriya_keywords')}")
    print(f"     Target Entities: {plan.get('entity_keywords')}")
    
    # ─────────────────────────────────────────────────────
    # PHASE 2: SEARCH / RETRIEVE
    # ─────────────────────────────────────────────────────
    t2 = time.perf_counter()
    print("  🔍 Phase 2: Searching Graph...")
    relevant_frames = search_frames(store, plan)
    t3 = time.perf_counter()
    print(f"     ⏱️ Search took {t3-t2:.4f}s")
    print(f"     Found {len(relevant_frames)} relevant frames.")
    
    if not relevant_frames:
        print("     ⚠️ No direct matches found. Using all frames as fallback.")
        relevant_frames = all_frames
    
    # ─────────────────────────────────────────────────────
    # PHASE 3: SYNTHESIZE ANSWER
    # ─────────────────────────────────────────────────────
    t4 = time.perf_counter()
    print("  🤖 Phase 3: Synthesizing Answer...")
    
    # Prepare Context (Only Relevant Frames)
    frame_descriptions = []
    for f in relevant_frames:
        frame_dict = f.to_display()
        # Add original sentence for context
        frame_dict["original_sentence"] = f.sentence_text 
        frame_descriptions.append(frame_dict)
        
    context = f"""## USER QUESTION
{question}

## RETRIEVED FRAMES (Search Results)
{json.dumps(frame_descriptions, indent=2)}

## INSTRUCTIONS
Answer the question using ONLY the Retrieved Frames. 
If the answer is found, map it to the Pāṇinian role.
"""

    try:
        response = await call_llm(
            ANSWER_SYNTHESIS_PROMPT,
            context,
            temperature=0.1
        )
        t5 = time.perf_counter()
        print(f"     ⏱️ Synthesis took {t5-t4:.2f}s")
        print(f"     ⏱️ TOTAL Q&A Latency: {t5-start_total:.2f}s")
        
        # Parse Response (Reuse existing clean logic)
        data = _parse_llm_json(response)
        
        return {
            "question": question,
            "answer": data.get("answer", response),
            "reasoning": data.get("reasoning", ""),
            "matched_frames": data.get("matched_frame_ids", []),
            "mapped_karaka": data.get("mapped_karaka", ""),
            "interrogative_type": data.get("interrogative_type", ""),
            "confidence": data.get("confidence", "medium"),
            "sources": [f.to_display() for f in relevant_frames if f.frame_id in data.get("matched_frame_ids", [])],
            "frame_count": len(all_frames)
        }
        
    except Exception as e:
        print(f"  ❌ QA Error: {e}")
        return _error_response(question, str(e))

def _parse_llm_json(text):
    try:
        if "{" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            return json.loads(text[start:end])
        return {"answer": text}
    except:
        return {"answer": text}

def _empty_response(q):
    return {
        "question": q, 
        "answer": "No frames loaded.", 
        "sources": [], 
        "frame_count": 0
    }

def _error_response(q, err):
    return {
        "question": q, 
        "answer": f"Error: {err}", 
        "sources": [], 
        "frame_count": 0
    }
