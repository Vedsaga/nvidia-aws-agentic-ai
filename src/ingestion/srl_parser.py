"""
SRL Parser using LLM (Nemotron) for semantic role extraction.

This module extracts semantic roles from sentences using LLM-based analysis.
It handles multiple verbs per line and extracts semantic roles without spaCy.
"""

from typing import List, Tuple, Dict
import json
import re


class SRLParser:
    """
    Semantic Role Labeling parser using LLM (Nemotron).
    
    Extracts semantic roles (nsubj, obj, iobj, obl) for all verbs in a line.
    """
    
    def __init__(self, nim_client=None):
        """Initialize with NIM client for LLM calls."""
        self.nim_client = nim_client
    
    def parse_line(self, line: str) -> List[Tuple[str, Dict[str, str]]]:
        """
        Parse a line and extract semantic roles for all verbs using LLM.
        
        Args:
            line: Input text line
            
        Returns:
            List of (verb, {role: entity}) tuples for each verb in the line
            Example: [("called", {"nsubj": "she", "obj": "team"}), 
                     ("scheduled", {"nsubj": "she", "obj": "meeting"})]
        """
        if not line or not line.strip():
            return []
        
        if not self.nim_client:
            raise RuntimeError("NIM client not initialized")
        
        # Build prompt for LLM to extract semantic roles
        prompt = f"""Extract semantic roles from the following sentence. For each verb, identify:
- nsubj: the subject/agent performing the action
- obj: the direct object/patient receiving the action
- iobj: the indirect object/recipient
- obl:with: instrument (with what)
- obl:loc: location (where)
- obl:from: source (from where)
- obl:to: destination (to where)

Sentence: {line}

Return ONLY a JSON array with this exact format:
[{{"verb": "verb1", "roles": {{"nsubj": "entity1", "obj": "entity2"}}}}, ...]

JSON:"""

        try:
            response = self.nim_client.call_nemotron(prompt, max_tokens=500, temperature=0.1)
            return self._parse_llm_response(response)
        except Exception as e:
            print(f"Error parsing line with LLM: {e}")
            return []
    
    def _parse_llm_response(self, response: str) -> List[Tuple[str, Dict[str, str]]]:
        """
        Parse LLM response to extract verb-role pairs.
        
        Args:
            response: LLM response text
            
        Returns:
            List of (verb, roles_dict) tuples
        """
        try:
            # Extract JSON from response (may have extra text)
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if not json_match:
                return []
            
            json_str = json_match.group(0)
            data = json.loads(json_str)
            
            results = []
            for item in data:
                if isinstance(item, dict) and "verb" in item and "roles" in item:
                    verb = item["verb"]
                    roles = item["roles"]
                    if isinstance(roles, dict) and roles:
                        results.append((verb, roles))
            
            return results
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing LLM JSON response: {e}")
            return []
