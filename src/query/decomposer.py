"""
Query Decomposer for analyzing natural language questions.
Uses Nemotron NIM to identify target Kāraka roles, constraints, and verbs.
"""
import json
import logging
from typing import Dict, Any, Optional

from src.utils.nim_client import NIMClient

logger = logging.getLogger(__name__)


class QueryDecomposer:
    """Decomposes natural language queries into Kāraka-based graph queries."""
    
    # Valid Kāraka types
    KARAKA_TYPES = [
        'KARTA',        # Agent - Who performs the action?
        'KARMA',        # Patient/Object - What is acted upon?
        'KARANA',       # Instrument - By what means?
        'SAMPRADANA',   # Recipient - For whom? To whom?
        'ADHIKARANA',   # Location - Where?
        'APADANA'       # Source - From where? From whom?
    ]
    
    def __init__(self, nim_client: NIMClient):
        """
        Initialize Query Decomposer.
        
        Args:
            nim_client: NIM client for calling Nemotron
        """
        self.nim_client = nim_client
        logger.info("Initialized Query Decomposer")
    
    def decompose(self, question: str) -> Dict[str, Any]:
        """
        Decompose a natural language question into Kāraka components.
        
        Args:
            question: Natural language question
            
        Returns:
            Dict containing:
                - target_karaka: The Kāraka role being queried
                - constraints: Dict of other Kāraka roles mentioned
                - verb: The action/verb involved (optional)
                
        Example:
            Input: "Who gave bow to Lakshmana?"
            Output: {
                "target_karaka": "KARTA",
                "constraints": {"KARMA": "bow", "SAMPRADANA": "Lakshmana"},
                "verb": "give"
            }
        """
        logger.info(f"Decomposing query: {question}")
        
        # Build prompt for Nemotron
        prompt = self._build_decomposition_prompt(question)
        
        # Call Nemotron NIM
        try:
            response = self.nim_client.call_nemotron(
                prompt=prompt,
                max_tokens=256,
                temperature=0.3  # Lower temperature for more deterministic output
            )
            
            # Parse response
            decomposition = self._parse_response(response)
            
            logger.info(f"Decomposed query: {decomposition}")
            return decomposition
            
        except Exception as e:
            logger.error(f"Error decomposing query: {str(e)}")
            raise
    
    def _build_decomposition_prompt(self, question: str) -> str:
        """
        Build prompt template for query decomposition.
        
        Args:
            question: Natural language question
            
        Returns:
            str: Formatted prompt for Nemotron
        """
        prompt = f"""You are a semantic query analyzer for a Kāraka-based knowledge graph system.

Kāraka roles are semantic relationships from Pāṇinian linguistics:
- KARTA: Agent (who performs the action?)
- KARMA: Patient/Object (what is acted upon?)
- KARANA: Instrument (by what means?)
- SAMPRADANA: Recipient (for whom? to whom?)
- ADHIKARANA: Location (where?)
- APADANA: Source (from where? from whom?)

Analyze this question and identify:
1. Which Kāraka role is being asked about (the target)
2. What constraints are given (other Kāraka roles mentioned in the question)
3. The action/verb involved (if any)

Question: "{question}"

Respond ONLY with valid JSON in this exact format:
{{
  "target_karaka": "KARTA",
  "constraints": {{"KARMA": "entity_name", "SAMPRADANA": "entity_name"}},
  "verb": "action_verb"
}}

Examples:

Question: "Who gave bow to Lakshmana?"
{{
  "target_karaka": "KARTA",
  "constraints": {{"KARMA": "bow", "SAMPRADANA": "Lakshmana"}},
  "verb": "give"
}}

Question: "What did Rama give to Lakshmana?"
{{
  "target_karaka": "KARMA",
  "constraints": {{"KARTA": "Rama", "SAMPRADANA": "Lakshmana"}},
  "verb": "give"
}}

Question: "To whom did Rama give the bow?"
{{
  "target_karaka": "SAMPRADANA",
  "constraints": {{"KARTA": "Rama", "KARMA": "bow"}},
  "verb": "give"
}}

Question: "What did Rama use to kill Ravana?"
{{
  "target_karaka": "KARANA",
  "constraints": {{"KARTA": "Rama", "KARMA": "Ravana"}},
  "verb": "kill"
}}

Question: "Where did Rama meet Sita?"
{{
  "target_karaka": "ADHIKARANA",
  "constraints": {{"KARTA": "Rama"}},
  "verb": "meet"
}}

Now analyze the question and respond with JSON only:"""
        
        return prompt
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response to extract decomposition components.
        
        Args:
            response: Raw response from Nemotron
            
        Returns:
            Dict with target_karaka, constraints, and verb
        """
        try:
            # Try to find JSON in response
            response = response.strip()
            
            # Handle case where response might have extra text
            if '{' in response:
                start_idx = response.index('{')
                end_idx = response.rindex('}') + 1
                json_str = response[start_idx:end_idx]
            else:
                json_str = response
            
            # Parse JSON
            parsed = json.loads(json_str)
            
            # Validate and normalize
            decomposition = {
                'target_karaka': parsed.get('target_karaka', '').upper(),
                'constraints': parsed.get('constraints', {}),
                'verb': parsed.get('verb', '').lower() if parsed.get('verb') else None
            }
            
            # Validate target_karaka
            if decomposition['target_karaka'] not in self.KARAKA_TYPES:
                logger.warning(
                    f"Invalid target_karaka: {decomposition['target_karaka']}. "
                    f"Defaulting to KARTA"
                )
                decomposition['target_karaka'] = 'KARTA'
            
            # Normalize constraint keys
            normalized_constraints = {}
            for key, value in decomposition['constraints'].items():
                key_upper = key.upper()
                if key_upper in self.KARAKA_TYPES:
                    normalized_constraints[key_upper] = value
                else:
                    logger.warning(f"Ignoring invalid constraint Kāraka: {key}")
            
            decomposition['constraints'] = normalized_constraints
            
            return decomposition
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response}")
            logger.error(f"JSON error: {str(e)}")
            
            # Fallback: try to extract information heuristically
            return self._fallback_parse(response)
        
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            raise
    
    def _fallback_parse(self, response: str) -> Dict[str, Any]:
        """
        Fallback parser when JSON parsing fails.
        Uses heuristics to extract information.
        
        Args:
            response: Raw response text
            
        Returns:
            Dict with best-effort decomposition
        """
        logger.warning("Using fallback parser for query decomposition")
        
        # Default to KARTA (most common query type)
        decomposition = {
            'target_karaka': 'KARTA',
            'constraints': {},
            'verb': None
        }
        
        # Try to find Kāraka types in response
        response_upper = response.upper()
        for karaka in self.KARAKA_TYPES:
            if karaka in response_upper:
                decomposition['target_karaka'] = karaka
                break
        
        return decomposition
