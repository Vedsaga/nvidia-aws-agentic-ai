"""
Cascading Sentence Splitter for Kāraka Frame Graph POC.
Layers: Regex → Spacy → LLM (fallback)
Guarantees: Lossless (input == output when joined)
"""

import re
import json

# Lazy load spacy to avoid startup cost
_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("📥 Downloading spaCy model...")
            from spacy.cli import download
            download("en_core_web_sm")
            _nlp = spacy.load("en_core_web_sm")
    return _nlp


def verify_fidelity(original: str, segments: list[str]) -> bool:
    """The Iron Law: Input MUST equal Output exactly."""
    return "".join(segments) == original


def split_regex(text: str) -> list[str]:
    """
    Layer 1: Fast Regex Split
    Handles: Simple sentences ending with . ? !
    """
    # Pattern captures the delimiter with trailing whitespace
    pattern = r'(?<=[.!?])\s+'
    parts = re.split(pattern, text)
    
    # Reconstruct with whitespace preserved
    result = []
    current_pos = 0
    
    for part in parts:
        # Find where this part starts in original
        start = text.find(part, current_pos)
        if start > current_pos:
            # There was whitespace before this part
            result[-1] = result[-1] if result else ""
            result[-1] += text[current_pos:start]
        result.append(part)
        current_pos = start + len(part)
    
    # Handle trailing content
    if current_pos < len(text):
        if result:
            result[-1] += text[current_pos:]
        else:
            result.append(text[current_pos:])
    
    return result if result else [text]


def split_spacy(text: str) -> list[str]:
    """
    Layer 2: Spacy Dependency Parse
    Handles: Complex sentences, abbreviations, etc.
    """
    nlp = _get_nlp()
    doc = nlp(text)
    return [sent.text_with_ws for sent in doc.sents]


async def split_llm(text: str) -> list[str]:
    """
    Layer 3: LLM Fallback
    Handles: Edge cases that Regex and Spacy miss
    """
    from llm_client import call_llm
    
    prompt = """Split this text into sentences.
CRITICAL RULES:
1. Preserve ALL original characters including spaces and punctuation
2. When joined, the sentences must EXACTLY equal the original text
3. Return a JSON array of strings

Example:
Input: "Hello world. How are you? "
Output: ["Hello world. ", "How are you? "]

Return only the JSON array, nothing else."""

    response = await call_llm(prompt, text, json_mode=True)
    
    try:
        data = json.loads(response)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "sentences" in data:
            return data["sentences"]
        if isinstance(data, dict):
            return list(data.values())[0]
    except json.JSONDecodeError:
        pass
    
    return [text]


async def smart_split(text: str) -> list[str]:
    """
    Main entry point: Cascading sentence splitter.
    Tries each layer in order until one succeeds with perfect fidelity.
    """
    if not text or not text.strip():
        return []
    
    # Layer 1: Regex (instant, free)
    candidates = split_regex(text)
    if verify_fidelity(text, candidates) and len(candidates) > 1:
        print(f"✅ Regex split: {len(candidates)} sentences")
        return candidates
    
    # Layer 2: Spacy (fast, free)
    candidates = split_spacy(text)
    if verify_fidelity(text, candidates):
        print(f"✅ Spacy split: {len(candidates)} sentences")
        return candidates
    
    # Layer 3: LLM (slow, costly)
    print("⚠️ Local methods failed, using LLM fallback...")
    candidates = await split_llm(text)
    
    if verify_fidelity(text, candidates):
        print(f"✅ LLM split: {len(candidates)} sentences")
        return candidates
    
    # Safety net: Return unsplit
    print("❌ All methods failed, returning unsplit text")
    return [text]
