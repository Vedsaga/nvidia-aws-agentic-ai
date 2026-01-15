"""
QA Engine for Kāraka Frame Graph POC.

This module implements a schema-aware Q&A system that translates natural language
questions into frame traversal operations. The LLM is taught the Kāraka semantic
framework and can reason about event frames to answer questions.

Key Insight: We don't do keyword matching or traditional RAG. Instead, we teach
the LLM our semantic schema and let it reason about structured event data.
"""

import json
from dataclasses import dataclass
from typing import Optional, List
from llm_client import call_llm
from frame_store import FrameStore, get_store
from frame_extractor import Frame


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA-AWARE Q&A PROMPT
# ═══════════════════════════════════════════════════════════════════════════════
# This prompt teaches the LLM:
# 1. What Kāraka roles mean (Pāṇinian semantics)
# 2. How our frame database is structured
# 3. How to translate questions into frame traversal logic
# 4. How to generate accurate answers from frames

SCHEMA_AWARE_QA_PROMPT = """You are a Question-Answering system for a Kāraka Frame Graph database.

## THE PĀṆINIAN INSIGHT

You are using a 2500-year-old Sanskrit grammar system that SYSTEMATICALLY maps ALL question types 
to semantic roles. This is not pattern matching - it's a complete theory of interrogatives.

## INTERROGATIVE → KĀRAKA MAPPING (Vibhakti System)

Every question word in any language maps to a specific Kāraka role:

| Question Word | Case (Vibhakti) | Kāraka Role | What to Find |
|---------------|-----------------|-------------|--------------|
| **Who?** (subject) | प्रथमा (Nominative) | **Kartā** | The agent who performed the action |
| **Whom?** (object) | द्वितीया (Accusative) | **Karma** | The thing acted upon |
| **What?** (subject) | प्रथमा | **Kartā** | Inanimate agent |
| **What?** (object) | द्वितीया | **Karma** | The thing acted upon |
| **What did X do?** | - | **Kriyā + Karma** | The action and its object |
| **By what? How?** | तृतीया (Instrumental) | **Karaṇa** | The instrument/means used |
| **To/For whom?** | चतुर्थी (Dative) | **Sampradāna** | The recipient/beneficiary |
| **From where?** | पञ्चमी (Ablative) | **Apādāna** | The source/origin |
| **Whose?** | षष्ठी (Genitive) | *(possession)* | Owner/possessor |
| **Where?** | सप्तमी (Locative) | **Locus_Space** | Physical location |
| **When?** | सप्तमी (Locative) | **Locus_Time** | Temporal location |
| **About what?** | सप्तमी (Locative) | **Locus_Topic** | Subject matter |

## WHAT IS A KĀRAKA FRAME?

Each frame represents ONE EVENT (action/verb) with its semantic participants:

```
FRAME: {
  frame_id: "F0",
  kriya: "fund",              // The action/verb
  Kartā: "ERC",               // WHO did it (agent)
  Karma: "the study",         // WHAT was acted upon (object)
  Karaṇa: null,               // BY WHAT means (instrument)
  Sampradāna: null,           // TO WHOM (recipient)
  Apādāna: null,              // FROM WHERE (source)
  Locus_Space: null,          // WHERE it happened
  Locus_Time: "2022",         // WHEN it happened
  Locus_Topic: null           // ABOUT WHAT topic
}
```

## PASSIVE VOICE: CRITICAL INSIGHT

In passive voice ("The study was conducted"):
- The **grammatical subject** ("The study") is the **Karma** (object), NOT Kartā
- The **agent** may be in a "by" phrase, OR may be **NULL** (unstated)
- A **NULL Kartā is valid** - it means "done by unspecified agent"

Example:
- "The study was conducted in Copenhagen"
- Kriyā = "conduct", Karma = "The study", Kartā = NULL, Locus_Space = "Copenhagen"
- Question: "Who conducted the study?" → Answer: "The agent is not explicitly stated (passive voice)"

## YOUR REASONING PROCESS

When answering a question:

1. **IDENTIFY THE INTERROGATIVE TYPE**
   - What question word is used? (who/what/where/when/how/why)
   - Map it to the corresponding Kāraka role using the table above

2. **IDENTIFY CONSTRAINTS**
   - What entity or action is mentioned that helps locate the right frame?
   - Example: "funded the study" → find frame with Kriyā containing "fund"

3. **LOCATE THE FRAME**
   - Find the frame(s) that match the constraints

4. **EXTRACT THE ANSWER**
   - Return the value of the mapped Kāraka role from that frame
   - If the role is NULL, explain why (often passive voice)

## OUTPUT FORMAT

Respond with JSON:
```json
{
  "interrogative_type": "who/what/where/when/how/why",
  "mapped_karaka": "The Kāraka role you're looking for",
  "reasoning": "How you identified the frame and extracted the answer",
  "matched_frame_ids": ["F0"],
  "answer": "Natural language answer using ONLY frame data",
  "confidence": "high/medium/low"
}
```

## CRITICAL RULES

1. ONLY use information from the provided frames
2. If a role is NULL, say so explicitly and explain (passive voice, unstated, etc.)
3. If no frame matches, say "This information is not in the extracted events"
4. Always cite which frame(s) you used
"""


async def ask(question: str, store: Optional[FrameStore] = None) -> dict:
    """
    Main Q&A entry point - Schema-Aware Approach.
    
    This function:
    1. Retrieves all frames from the store
    2. Sends a comprehensive prompt teaching the LLM our Kāraka schema
    3. Lets the LLM reason about the question and frames
    4. Returns a structured answer
    
    Args:
        question: User's natural language question
        store: Optional frame store (uses global if not provided)
    
    Returns:
        {
            "question": original question,
            "answer": generated answer,
            "reasoning": LLM's reasoning about the query,
            "matched_frames": frame IDs used,
            "sources": full frame data,
            "frame_count": number of total frames,
            "confidence": answer confidence level
        }
    """
    store = store or get_store()
    all_frames = store.get_all_frames()
    
    print(f"\n❓ Question: {question}")
    print(f"  📊 Frame store contains {len(all_frames)} frames")
    
    if not all_frames:
        return {
            "question": question,
            "answer": "No events have been extracted yet. Please process a document first by entering text and clicking 'Process Text', or click 'Load Demo' to load pre-extracted frames.",
            "reasoning": "No frames in database",
            "matched_frames": [],
            "sources": [],
            "frame_count": 0,
            "confidence": "none"
        }
    
    # ─────────────────────────────────────────────────────
    # Build frame context for the LLM
    # ─────────────────────────────────────────────────────
    frame_descriptions = []
    for f in all_frames:
        frame_dict = {
            "frame_id": f.frame_id,
            "kriya": f.kriya,
            "original_sentence": f.sentence_text,
            "roles": {}
        }
        
        if f.karta: frame_dict["roles"]["Kartā (Agent)"] = f.karta
        if f.karma: frame_dict["roles"]["Karma (Object)"] = f.karma
        if f.karana: frame_dict["roles"]["Karaṇa (Instrument)"] = f.karana
        if f.sampradana: frame_dict["roles"]["Sampradāna (Recipient)"] = f.sampradana
        if f.apadana: frame_dict["roles"]["Apādāna (Source)"] = f.apadana
        if f.locus_time: frame_dict["roles"]["Locus_Time"] = f.locus_time
        if f.locus_space: frame_dict["roles"]["Locus_Space"] = f.locus_space
        if f.locus_topic: frame_dict["roles"]["Locus_Topic"] = f.locus_topic
        
        # Note if any expected roles are null (helpful for passive voice)
        if not f.karta:
            frame_dict["roles"]["Kartā (Agent)"] = "NULL (not explicitly stated - likely passive voice)"
        
        frame_descriptions.append(frame_dict)
    
    # Build the full context
    context = f"""## USER QUESTION
{question}

## AVAILABLE FRAMES (from extracted events)
{json.dumps(frame_descriptions, indent=2)}

## YOUR TASK
Analyze the question, find relevant frames, and provide an answer using ONLY the frame data above."""

    try:
        # Call LLM with schema-aware prompt
        response = await call_llm(
            SCHEMA_AWARE_QA_PROMPT,
            context,
            temperature=0.1  # Low temperature for factual accuracy
        )
        
        # Parse JSON response
        response_text = response.strip()
        
        # Try to extract JSON from response
        try:
            # Look for JSON block
            if "{" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
            else:
                # No JSON found, treat entire response as answer
                data = {
                    "reasoning": "Direct answer",
                    "matched_frames": [],
                    "answer": response_text,
                    "confidence": "medium"
                }
        except json.JSONDecodeError:
            data = {
                "reasoning": "Response parsing",
                "matched_frames": [],
                "answer": response_text,
                "confidence": "medium"
            }
        
        answer = data.get("answer", response_text)
        reasoning = data.get("reasoning", "")
        # Handle both field names for compatibility
        matched_frames = data.get("matched_frame_ids", data.get("matched_frames", []))
        confidence = data.get("confidence", "medium")
        interrogative_type = data.get("interrogative_type", "")
        mapped_karaka = data.get("mapped_karaka", "")
        
        print(f"  🔍 Interrogative: {interrogative_type} → Kāraka: {mapped_karaka}")
        print(f"  💭 Reasoning: {reasoning}")
        print(f"  📎 Matched frames: {matched_frames}")
        print(f"  ✅ Answer: {answer}")
        
        # Get source frames for the matched IDs
        sources = []
        for frame in all_frames:
            if frame.frame_id in matched_frames:
                sources.append(frame.to_display())
        
        # If no specific frames matched, include all as context
        if not sources:
            sources = [f.to_display() for f in all_frames]
        
        return {
            "question": question,
            "answer": answer,
            "reasoning": reasoning,
            "matched_frames": matched_frames,
            "sources": sources,
            "frame_count": len(all_frames),
            "confidence": confidence
        }
        
    except Exception as e:
        print(f"  ⚠️ LLM Q&A failed: {e}")
        
        # Graceful fallback - list what we have
        frame_summary = []
        for f in all_frames:
            if f.karta:
                frame_summary.append(f"• {f.karta} → {f.kriya}" + (f" → {f.karma}" if f.karma else ""))
            else:
                frame_summary.append(f"• {f.kriya} (passive)" + (f" on {f.karma}" if f.karma else ""))
        
        fallback_answer = f"I have {len(all_frames)} extracted events:\n" + "\n".join(frame_summary) + f"\n\nPlease rephrase your question. (Error: {str(e)[:50]})"
        
        return {
            "question": question,
            "answer": fallback_answer,
            "reasoning": f"LLM call failed: {e}",
            "matched_frames": [],
            "sources": [f.to_display() for f in all_frames],
            "frame_count": len(all_frames),
            "confidence": "low"
        }
