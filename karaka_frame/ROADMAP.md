# POC Robustness Roadmap

**Objective**: Make the Kāraka Frame Graph POC demo-ready while minimizing LLM calls.

---

## Immediate Priorities (Before Demo)

### ✅ DONE: Demo Mode
- Pre-extracted frames in `demo_frames.json`
- "Load Demo" button bypasses live extraction
- Works even with 0 API credits

### ✅ DONE: Context-Aware Q&A
- All frames passed to LLM for semantic matching
- Fallback keyword matching when LLM unavailable

### ✅ DONE: Improved Extraction Prompt
- Added reasoning blocks, voice checklist, locus decision tree

---

## Phase 1: Token-Conservative LLM Strategy (1-2 hours)

### 1.1 Add Reasoning Mode Toggle
```python
# In .env
LLM_REASONING_ENABLED=false  # Start conservative
```

Benefits:
- Can toggle on for complex sentences
- Save tokens for simple cases

### 1.2 Implement Token Budget
Track token usage per session:
```python
class TokenBudget:
    def __init__(self, max_tokens=10000):
        self.max_tokens = max_tokens
        self.used_tokens = 0
    
    def can_proceed(self, estimated_tokens=500):
        return self.used_tokens + estimated_tokens < self.max_tokens
    
    def record_usage(self, tokens):
        self.used_tokens += tokens
```

### 1.3 Caching Layer
Cache LLM responses by input hash:
```python
import hashlib
import json

CACHE = {}

def get_cached_or_call(prompt):
    key = hashlib.md5(prompt.encode()).hexdigest()
    if key in CACHE:
        return CACHE[key]
    
    result = await call_llm(prompt)
    CACHE[key] = result
    return result
```

---

## Phase 2: Multi-Phase Extraction (2-3 hours)

### 2.1 Implement D2a → D2b Split

Current: One mega-prompt does everything
Target: Two focused prompts

**Step 1: D2a - Kriyā Extraction Only**
```
Input: "The study was conducted in Copenhagen."
Output: {
  "kriyās": [
    {"canonical_form": "conduct", "surface_text": "was conducted", "prayoga": "passive"}
  ]
}
```

**Step 2: D2b - Kāraka Binding**
```
Input: sentence + kriyas from D2a
Output: {
  "events": [
    {
      "kriya": "conduct",
      "karma": "The study",      // Subject of passive = Object
      "karta": null,             // No "by" phrase = no agent
      "locus_space": "Copenhagen"
    }
  ]
}
```

**Benefits:**
- Each prompt is simpler → better accuracy
- Can cache D2a results
- Retry only the failed phase

### 2.2 Add Fidelity Validation

After extraction, verify:
```python
def validate_fidelity(frame, source_sentence):
    """Check that extracted values exist in source text."""
    errors = []
    source_lower = source_sentence.lower()
    
    for field in ['karta', 'karma', 'locus_space', 'locus_time']:
        value = getattr(frame, field)
        if value and value.lower() not in source_lower:
            errors.append(f"'{value}' not found in source")
    
    return len(errors) == 0, errors
```

---

## Phase 3: Rate Limit Resilience (1-2 hours)

### 3.1 Exponential Backoff
```python
async def call_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await call_llm(prompt)
        except RateLimitError:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            await asyncio.sleep(wait_time)
    
    return None  # Trigger fallback
```

### 3.2 Request Throttling
```python
import asyncio
from datetime import datetime

class RateLimiter:
    def __init__(self, requests_per_minute=10):
        self.rpm = requests_per_minute
        self.request_times = []
    
    async def acquire(self):
        now = datetime.now()
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times 
                             if (now - t).seconds < 60]
        
        if len(self.request_times) >= self.rpm:
            # Wait until a slot opens
            wait_time = 60 - (now - self.request_times[0]).seconds
            await asyncio.sleep(wait_time)
        
        self.request_times.append(now)
```

### 3.3 Graceful Degradation Modes
```python
class DegradationLevel(Enum):
    FULL = "full"           # All LLM features enabled
    REDUCED = "reduced"     # No reasoning, shorter prompts
    CACHED_ONLY = "cached"  # Only use cached responses
    OFFLINE = "offline"     # Demo mode, no LLM calls
```

---

## Phase 4: Q&A Improvements (1-2 hours)

### 4.1 Question Classification (No LLM)
```python
def classify_question(question):
    """Classify question type without LLM."""
    q = question.lower()
    
    if q.startswith("who") or "agent" in q:
        return "agent_query"  # Looking for Kartā
    elif q.startswith("what") and ("happen" in q or "did" in q):
        return "event_query"  # Looking for Kriyā
    elif q.startswith("where"):
        return "location_query"  # Looking for Locus_Space
    elif q.startswith("when"):
        return "time_query"  # Looking for Locus_Time
    elif q.startswith("how"):
        return "instrument_query"  # Looking for Karaṇa
    else:
        return "general_query"  # Use LLM

# Use classification to build targeted, token-efficient queries
```

### 4.2 Pre-computed Answer Templates
For demo, pre-compute answers for expected questions:
```python
DEMO_QA = {
    "who funded the study": "The European Research Council funded the study.",
    "where was the study conducted": "The study was conducted in Copenhagen.",
    "who led the research": "Dr. Chen led the research.",
    "what did the team publish": "The team published the results in Nature."
}

def get_demo_answer(question):
    q = question.lower().strip().rstrip("?")
    return DEMO_QA.get(q)
```

---

## Phase 5: Future Production Features

### 5.1 GSSR Implementation (Post-Demo)
- Generate 3 variations
- Fidelity check each
- Consensus detection
- Scorer tie-breaking

### 5.2 D1 Entity Pre-Extraction (Post-Demo)
- Extract entities first
- Force D2b to use only D1 entities
- Prevents hallucination

### 5.3 OpenRouter SDK Integration (Optional)
For reasoning token tracking:
```python
# Track reasoning tokens separately
if response.usage and response.usage.reasoning_tokens:
    log(f"Reasoning tokens: {response.usage.reasoning_tokens}")
```

---

## Token Budget Estimation

| Operation | Est. Tokens | With Reasoning |
|-----------|-------------|----------------|
| Sentence split | ~200 | ~400 |
| D2a (Kriyā only) | ~300 | ~600 |
| D2b (Kāraka binding) | ~500 | ~1000 |
| Q&A answer | ~400 | ~800 |
| **Per sentence total** | ~1000 | ~2000 |

**Free tier strategy:**
- 50 requests/day × ~500 tokens/request = ~25K tokens/day
- Demo mode: 0 extraction tokens, only Q&A tokens
- With caching: ~50% reduction

---

## Implementation Order

| Priority | Task | Time | Impact |
|----------|------|------|--------|
| 1 | Token budget tracking | 30 min | Know when to stop |
| 2 | Response caching | 30 min | 50% token reduction |
| 3 | Pre-computed demo Q&A | 30 min | Demo works offline |
| 4 | D2a/D2b split | 2 hours | Better accuracy |
| 5 | Fidelity validation | 1 hour | Catch errors |
| 6 | Rate limiter | 30 min | Prevent 429s |

---

## Quick Wins (Can Do Now)

1. **Add pre-computed Q&A for demo** - Zero tokens for expected questions
2. **Add request caching** - Same question = cached answer
3. **Track token usage** - Know before we hit limits

Would you like me to implement any of these now?
