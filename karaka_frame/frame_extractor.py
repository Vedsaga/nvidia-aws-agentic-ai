"""
Frame Extractor for Kāraka Frame Graph POC.
Extracts Kriyā (verb root) and Kāraka (semantic roles) from eventive sentences.
"""

import json
from dataclasses import dataclass, asdict
from typing import Optional
from llm_client import call_llm


@dataclass
class Frame:
    """A single event frame with Kriyā and Kāraka roles."""
    frame_id: str
    sentence_id: int
    sentence_text: str
    kriya: str  # Normalized verb root
    kriya_surface: str  # Original verb form
    
    # Kāraka roles (null if not present)
    karta: Optional[str] = None       # Agent
    karma: Optional[str] = None       # Object  
    karana: Optional[str] = None      # Instrument
    sampradana: Optional[str] = None  # Recipient
    apadana: Optional[str] = None     # Source
    locus_time: Optional[str] = None  # Temporal locus
    locus_space: Optional[str] = None # Spatial locus
    locus_topic: Optional[str] = None # Topic locus
    causal_links: Optional[list[dict]] = None # Causal links to other frames
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_display(self) -> dict:
        """Convert to display format (only non-null roles)."""
        result = {
            "frame_id": self.frame_id,
            "kriya": self.kriya,
            "karakas": {}
        }
        
        role_map = {
            "Kartā (Agent)": self.karta,
            "Karma (Object)": self.karma,
            "Karaṇa (Instrument)": self.karana,
            "Sampradāna (Recipient)": self.sampradana,
            "Apādāna (Source)": self.apadana,
            "Locus_Time": self.locus_time,
            "Locus_Space": self.locus_space,
            "Locus_Topic": self.locus_topic,
        }
        
        for role, value in role_map.items():
            if value:
                result["karakas"][role] = value
        
        return result


EXTRACTION_PROMPT = """You are a Pāṇinian grammatical parser extracting event frames from sentences.

IMPORTANT: Take your time. Use the <reasoning> block to think step-by-step.
Quality > Speed. A thorough reasoning block leads to accurate JSON.

TASK:
1. Identify ALL verbs (kriyā) in the sentence
2. For EACH verb, determine if it's active or passive voice
3. Extract semantic roles (kārakas) for the main event

VOICE DETECTION CHECKLIST:
- Active voice: Subject DOES the action ("Dr. Chen developed...")
- Passive voice: Subject RECEIVES the action ("The study was conducted...")
  - Look for "was/were/been" + past participle
  - "by" phrase indicates agent in passive voice (but may be absent)

THE 8 KĀRAKA ROLES:
1. Kartā (Agent): Independent actor who initiates action
   - Active voice: subject of verb ("Dr. Chen developed...")
   - Passive voice: the "by" phrase ("was funded BY the ERC")
   - If passive and no "by" phrase → Agent is null (this is valid!)

2. Karma (Object): Primary target/patient of action
   - Active voice: direct object ("developed A SUPPLEMENT")  
   - Passive voice: subject ("THE STUDY was funded...")

3. Karaṇa (Instrument): Tool/means used
   - "typed WITH a keyboard", "analyzed USING statistical methods"

4. Sampradāna (Recipient): Beneficiary/destination
   - "gave TO the lab", "presented FOR the committee"

5. Apādāna (Source): Origin/separation point
   - "came FROM Berlin", "graduated FROM Stanford"

6. Locus_Space: Physical location (you can walk into it)
   - "conducted IN Copenhagen", "works AT the institute"

7. Locus_Time: Temporal location (date, duration, period)
   - "conducted IN 2024", "during six months"

8. Locus_Topic: Abstract subject matter (not physical)
   - "study ON neuroplasticity", "research examining gut-brain"

LOCUS DECISION TREE:
Step 1: Is it a date or time period? → Locus_Time
Step 2: Can you physically walk into this place? → Locus_Space  
Step 3: Is it an abstract concept or subject? → Locus_Topic

CRITICAL RULES:
1. Only extract roles EXPLICITLY mentioned in the sentence
2. NEVER invent or hallucinate entities not in the text
3. Use null for roles not mentioned
4. Passive voice without "by" phrase → Kartā is null (valid!)

REASONING PROCESS:
1. First, identify all verbs and their voice (active/passive)
2. For passive verbs, remember: subject = Karma, "by" phrase = Kartā
3. Apply the Locus Decision Tree for any location/time/topic
4. Double-check: does each extracted value appear verbatim in the sentence?

OUTPUT FORMAT:
First, show your reasoning in a <reasoning> block.
Then, provide ONLY valid JSON in a <json> block:

<json>
{
    "kriya": "verb root (e.g., fund, conduct, lead)",
    "kriya_surface": "original form as in sentence",
    "prayoga": "active or passive",
    "karta": "agent text or null",
    "karma": "object text or null",
    "karana": "instrument text or null",
    "sampradana": "recipient text or null",
    "apadana": "source text or null",
    "locus_time": "time text or null",
    "locus_space": "place text or null",
    "locus_topic": "topic text or null"
}
</json>"""


async def extract_frame(sentence_id: int, sentence: str) -> Frame:
    """
    Extract a single event frame from an eventive sentence.
    
    Args:
        sentence_id: Unique identifier for the sentence
        sentence: The eventive sentence text
    
    Returns:
        Frame object with extracted Kriyā and Kārakas
    """
    try:
        print(f"\n  🔍 Extracting frame for: '{sentence[:60]}...'")
        
        response = await call_llm(
            EXTRACTION_PROMPT,
            f"Sentence: {sentence}",
            json_mode=True
        )
        
        # Try to parse JSON
        try:
            data = json.loads(response)
        except json.JSONDecodeError as je:
            print(f"  ⚠️ JSON parse error: {je}")
            print(f"  ⚠️ Response was: {response[:300]}")
            raise
        
        frame = Frame(
            frame_id=f"F{sentence_id}",
            sentence_id=sentence_id,
            sentence_text=sentence,
            kriya=data.get("kriya", "UNKNOWN"),
            kriya_surface=data.get("kriya_surface", ""),
            karta=data.get("karta"),
            karma=data.get("karma"),
            karana=data.get("karana"),
            sampradana=data.get("sampradana"),
            apadana=data.get("apadana"),
            locus_time=data.get("locus_time"),
            locus_space=data.get("locus_space"),
            locus_topic=data.get("locus_topic"),
        )
        
        # Log extraction
        roles = [r for r, v in {
            "Kartā": frame.karta,
            "Karma": frame.karma,
            "Karaṇa": frame.karana,
            "Sampradāna": frame.sampradana,
            "Apādāna": frame.apadana,
            "Time": frame.locus_time,
            "Space": frame.locus_space,
            "Topic": frame.locus_topic,
        }.items() if v]
        
        print(f"  ✅ Frame {frame.frame_id}: {frame.kriya} ({', '.join(roles) if roles else 'no roles'})")
        
        return frame
    
    except Exception as e:
        import traceback
        print(f"  ❌ Extraction FAILED for sentence {sentence_id}")
        print(f"  ❌ Error type: {type(e).__name__}: {e}")
        traceback.print_exc()
        return Frame(
            frame_id=f"F{sentence_id}",
            sentence_id=sentence_id,
            sentence_text=sentence,
            kriya="EXTRACTION_FAILED",
            kriya_surface="",
        )


async def extract_frames(eventive_sentences: list[dict]) -> list[Frame]:
    """
    Extract frames from a list of eventive sentences.
    
    Args:
        eventive_sentences: List of dicts with sentence_id, text, is_eventive
    
    Returns:
        List of Frame objects
    """
    frames = []
    
    for item in eventive_sentences:
        if not item.get("is_eventive", False):
            continue
        
        frame = await extract_frame(
            sentence_id=item["sentence_id"],
            sentence=item["text"]
        )
        frames.append(frame)
    
    print(f"\n🎯 Extracted {len(frames)} frames")
    return frames
