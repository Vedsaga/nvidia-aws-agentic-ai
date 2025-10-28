"""Query decomposition using Nemotron NIM."""

import json
import re
from typing import Dict, Any, Optional, List
from src.utils.nim_client import NIMClient


class QueryDecomposer:
    """Decomposes natural language queries into structured components."""
    
    def __init__(self, nim_client: NIMClient):
        self.nim = nim_client
        self.karaka_types = ["KARTA", "KARMA", "SAMPRADANA", "KARANA", "ADHIKARANA", "APADANA"]
    
    def decompose(self, question: str) -> Dict[str, Any]:
        """
        Decompose question into structured query components.
        
        Args:
            question: Natural language question
            
        Returns:
            Dict with target_karaka, constraints, verb
        """
        prompt = self._build_prompt(question)
        response = self.nim.call_nemotron(prompt, max_tokens=500, temperature=0.1)
        
        return self._parse_response(response, question)
    
    def _build_prompt(self, question: str) -> str:
        """Build prompt for query analysis."""
        return f"""You are a semantic role analyzer for Sanskrit Kāraka theory applied to English text.

Kāraka Types:
- KARTA: Agent/doer (who performs the action)
- KARMA: Patient/object (what is affected by the action)
- SAMPRADANA: Recipient (to whom/for whom)
- KARANA: Instrument (with what/by what means)
- ADHIKARANA: Location (where/when)
- APADANA: Source (from where/from whom)

Analyze this question and identify:
1. Target Kāraka: Which semantic role is being asked about?
2. Verb: What action is mentioned?
3. Constraints: Other Kārakas mentioned that constrain the query

Question: {question}

Respond in JSON format:
{{
  "target_karaka": "KARTA|KARMA|SAMPRADANA|KARANA|ADHIKARANA|APADANA",
  "verb": "action verb or null",
  "constraints": {{
    "KARAKA_TYPE": "entity mention"
  }}
}}

Examples:
Q: "Who killed Ravana?"
A: {{"target_karaka": "KARTA", "verb": "killed", "constraints": {{"KARMA": "Ravana"}}}}

Q: "What did Rama give to Sita?"
A: {{"target_karaka": "KARMA", "verb": "give", "constraints": {{"KARTA": "Rama", "SAMPRADANA": "Sita"}}}}

Q: "Where did the battle happen?"
A: {{"target_karaka": "ADHIKARANA", "verb": "happen", "constraints": {{"KARMA": "battle"}}}}

Now analyze the question above:"""
    
    def _parse_response(self, response: str, original_question: str) -> Dict[str, Any]:
        """Parse LLM response into structured format."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            # Validate and normalize
            target_karaka = data.get("target_karaka", "").upper()
            if target_karaka not in self.karaka_types:
                target_karaka = self._infer_target_karaka(original_question)
            
            verb = data.get("verb")
            if verb and verb.lower() == "null":
                verb = None
            
            constraints = data.get("constraints", {})
            # Normalize constraint keys
            normalized_constraints = {}
            for k, v in constraints.items():
                k_upper = k.upper()
                if k_upper in self.karaka_types and v:
                    normalized_constraints[k_upper] = v
            
            return {
                "target_karaka": target_karaka,
                "verb": verb,
                "constraints": normalized_constraints,
                "original_question": original_question
            }
            
        except Exception as e:
            # Fallback to simple heuristics
            return self._fallback_decomposition(original_question)
    
    def _infer_target_karaka(self, question: str) -> str:
        """Infer target Kāraka from question words."""
        q_lower = question.lower()
        
        if any(word in q_lower for word in ["who", "whom"]):
            if "to whom" in q_lower or "for whom" in q_lower:
                return "SAMPRADANA"
            elif "by whom" in q_lower or "with whom" in q_lower:
                return "KARANA"
            elif "from whom" in q_lower:
                return "APADANA"
            else:
                return "KARTA"
        elif any(word in q_lower for word in ["what", "which"]):
            return "KARMA"
        elif any(word in q_lower for word in ["where", "when"]):
            return "ADHIKARANA"
        elif any(word in q_lower for word in ["how", "with what", "by what"]):
            return "KARANA"
        elif "from where" in q_lower or "from what" in q_lower:
            return "APADANA"
        
        return "KARMA"  # Default
    
    def _fallback_decomposition(self, question: str) -> Dict[str, Any]:
        """Simple fallback decomposition."""
        return {
            "target_karaka": self._infer_target_karaka(question),
            "verb": None,
            "constraints": {},
            "original_question": question
        }
