"""
Eventive Sentence Filter for Kāraka Frame Graph POC.
Filters out stative sentences, keeps only eventive (action) sentences.
"""

import json
from llm_client import call_llm

# Keywords that often indicate stative sentences
STATIVE_PATTERNS = [
    r'\bis\s+a\b',       # "is a"
    r'\bare\s+the\b',    # "are the"
    r'\bwas\s+a\b',      # "was a"
    r'\bwere\s+the\b',   # "were the"
    r'\bis\s+an\b',      # "is an"
    r'\bhas\s+been\b',   # "has been" (sometimes stative)
]

# Verbs that are typically stative (no action)
STATIVE_VERBS = {
    'is', 'are', 'was', 'were', 'am', 'be', 'been', 'being',
    'seems', 'appears', 'looks', 'sounds', 'feels', 'smells', 'tastes',
    'belongs', 'contains', 'consists', 'equals', 'resembles',
    'knows', 'believes', 'thinks', 'understands', 'remembers',
    'loves', 'hates', 'likes', 'dislikes', 'prefers', 'wants', 'needs',
    'owns', 'possesses', 'has', 'have', 'had'  # when possessive, not action
}


def quick_eventive_check(sentence: str) -> bool | None:
    """
    Quick heuristic check. Returns:
    - True: Likely eventive
    - False: Likely stative
    - None: Uncertain, needs LLM
    """
    import re
    
    text_lower = sentence.lower().strip()
    
    # Check for clear stative patterns
    for pattern in STATIVE_PATTERNS:
        if re.search(pattern, text_lower):
            # But check if there's also an action verb
            words = text_lower.split()
            action_verbs = {'ate', 'ran', 'went', 'said', 'made', 'gave', 
                           'took', 'came', 'saw', 'got', 'put', 'found',
                           'told', 'asked', 'used', 'tried', 'left', 'called'}
            if any(w in action_verbs for w in words):
                return None  # Mixed, needs LLM
            return False  # Likely stative
    
    return None  # Uncertain


async def is_eventive(sentence: str) -> tuple[bool, str]:
    """
    Determine if a sentence is eventive (action) or stative (state/property).
    
    Returns:
        (is_eventive: bool, reason: str)
    """
    # Quick check first
    quick_result = quick_eventive_check(sentence)
    if quick_result is False:
        return False, "Stative pattern detected"
    
    # Use LLM for uncertain cases
    prompt = """Classify this sentence as EVENTIVE or STATIVE.

EVENTIVE: Describes an action, change, or happening
- "Ram ate the mango" → EVENTIVE (eating is an action)
- "The company hired 50 employees" → EVENTIVE (hiring is an action)
- "She walked to the store" → EVENTIVE (walking is an action)

STATIVE: Describes a state, property, or relationship (no action)
- "Ram is tall" → STATIVE (property, no action)
- "Paris is the capital of France" → STATIVE (definition, no action)
- "She has blue eyes" → STATIVE (property, no action)

Respond with JSON: {"type": "EVENTIVE" or "STATIVE", "reason": "brief explanation"}
"""

    try:
        response = await call_llm(prompt, f"Sentence: {sentence}", json_mode=True)
        data = json.loads(response)
        
        is_event = data.get("type", "").upper() == "EVENTIVE"
        reason = data.get("reason", "LLM classification")
        
        return is_event, reason
    
    except Exception as e:
        # Default to eventive on error (don't lose data)
        return True, f"Classification error, defaulting to eventive: {e}"


async def filter_eventive(sentences: list[str]) -> list[dict]:
    """
    Filter a list of sentences, keeping only eventive ones.
    
    Returns:
        List of dicts with sentence and metadata
    """
    results = []
    
    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            continue
            
        is_event, reason = await is_eventive(sentence)
        
        results.append({
            "sentence_id": i,
            "text": sentence.strip(),
            "is_eventive": is_event,
            "reason": reason
        })
        
        status = "✅ EVENTIVE" if is_event else "⏭️ STATIVE (skipped)"
        print(f"  [{i}] {status}: {sentence[:50]}...")
    
    eventive_count = sum(1 for r in results if r["is_eventive"])
    print(f"\n📊 {eventive_count}/{len(results)} sentences are eventive")
    
    return results
