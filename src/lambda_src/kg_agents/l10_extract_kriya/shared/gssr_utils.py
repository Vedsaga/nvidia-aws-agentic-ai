"""
GSSR utility functions for consensus checking and JSON parsing
"""
import json
import re


def check_consensus(json1, json2, json3):
    """
    Check if all 3 JSONs are identical using sorted string comparison
    Returns: bool
    """
    try:
        str1 = json.dumps(json1, sort_keys=True)
        str2 = json.dumps(json2, sort_keys=True)
        str3 = json.dumps(json3, sort_keys=True)
        
        return str1 == str2 == str3
    except Exception:
        return False


def parse_llm_json_response(raw_response):
    """
    Extract JSON from LLM response
    Handles various formats:
    - Pure JSON
    - JSON wrapped in markdown code blocks
    - JSON with reasoning text before/after
    
    Returns: parsed JSON dict or None
    """
    if isinstance(raw_response, dict):
        # Already parsed
        return raw_response
    
    if not isinstance(raw_response, str):
        return None
    
    text = raw_response.strip()
    
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract from markdown code blocks
    code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    if matches:
        try:
            return json.loads(matches[0])
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in text
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    for match in matches:
        try:
            parsed = json.loads(match)
            # Verify it looks like our expected structure
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    
    return None


def extract_reasoning_block(raw_response):
    """
    Extract reasoning/explanation text from LLM response
    Returns: string or empty string
    """
    if not isinstance(raw_response, str):
        return ""
    
    text = raw_response.strip()
    
    # Look for reasoning markers
    reasoning_patterns = [
        r'(?:Reasoning|Explanation|Analysis):\s*(.+?)(?:\n\n|\{)',
        r'<reasoning>(.*?)</reasoning>',
        r'(?:^|\n)(.+?)(?:\n\{|\n```)',
    ]
    
    for pattern in reasoning_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # If no specific pattern, return text before first JSON
    json_start = text.find('{')
    if json_start > 0:
        return text[:json_start].strip()
    
    return ""


def parse_scorer_response(raw_response):
    """
    Parse scorer LLM response to extract 3 scores
    Expected format: Score 1: X, Score 2: Y, Score 3: Z
    Returns: [score1, score2, score3] or [0, 0, 0] if parsing fails
    """
    if isinstance(raw_response, dict) and 'scores' in raw_response:
        return raw_response['scores']
    
    if not isinstance(raw_response, str):
        return [0, 0, 0]
    
    text = raw_response.strip()
    
    # Try to find score patterns
    score_pattern = r'Score\s*(\d+)\s*:\s*(\d+(?:\.\d+)?)'
    matches = re.findall(score_pattern, text, re.IGNORECASE)
    
    if len(matches) >= 3:
        scores = [0, 0, 0]
        for idx_str, score_str in matches[:3]:
            idx = int(idx_str) - 1  # Convert to 0-based
            if 0 <= idx < 3:
                scores[idx] = float(score_str)
        return scores
    
    # Try alternative format: [score1, score2, score3]
    array_pattern = r'\[(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\]'
    match = re.search(array_pattern, text)
    if match:
        return [float(match.group(1)), float(match.group(2)), float(match.group(3))]
    
    return [0, 0, 0]
