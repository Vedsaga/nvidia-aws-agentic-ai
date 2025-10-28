"""
Answer Synthesizer for generating natural language answers from graph results.
Uses Nemotron NIM to create answers with Kāraka role annotations.
"""
import json
import logging
from typing import Dict, Any, List, Optional

from src.utils.nim_client import NIMClient
from src.query.cypher_generator import CypherGenerator

logger = logging.getLogger(__name__)


class AnswerSynthesizer:
    """Synthesizes natural language answers from graph query results."""
    
    def __init__(
        self,
        nim_client: Optional[NIMClient] = None,
        cypher_generator: Optional[CypherGenerator] = None
    ):
        """
        Initialize Answer Synthesizer.
        
        Args:
            nim_client: NIM client for calling Nemotron
            cypher_generator: Cypher generator for retrieving line texts from S3
        """
        self.nim_client = nim_client or NIMClient()
        self.cypher_gen = cypher_generator or CypherGenerator()
        
        logger.info("Initialized Answer Synthesizer")
    
    def synthesize(
        self,
        question: str,
        graph_results: List[Dict[str, Any]],
        decomposition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate natural language answer from graph results.
        
        Retrieves sentence text from S3 for each result, then uses Nemotron NIM
        to synthesize a natural language answer with Kāraka role annotations.
        
        Args:
            question: Original natural language question
            graph_results: List of results from Neo4j query
                Each result has: answer, line_number, document_id, confidence
            decomposition: Query decomposition with target_karaka, constraints, verb
            
        Returns:
            Dict with:
                - answer: Natural language answer text
                - sources: List of source citations with line_text, line_number, etc.
                - karakas: Kāraka roles from decomposition
                - confidence: Overall confidence score
                
        Example:
            Input:
                question: "Who gave bow to Lakshmana?"
                graph_results: [
                    {
                        "answer": "Rama",
                        "line_number": 42,
                        "document_id": "doc_123",
                        "confidence": 0.95
                    }
                ]
                decomposition: {
                    "target_karaka": "KARTA",
                    "constraints": {"KARMA": "bow", "SAMPRADANA": "Lakshmana"},
                    "verb": "give"
                }
            
            Output:
                {
                    "answer": "Rama (KARTA) gave the bow (KARMA) to Lakshmana (SAMPRADANA).",
                    "sources": [...],
                    "karakas": {...},
                    "confidence": 0.95
                }
        """
        logger.info(f"Synthesizing answer for question: {question}")
        
        # Handle empty results
        if not graph_results:
            logger.warning("No graph results to synthesize answer from")
            return {
                "answer": "I couldn't find an answer in the knowledge graph.",
                "sources": [],
                "karakas": decomposition,
                "confidence": 0.0
            }
        
        # Retrieve sentence text from S3 for each result
        logger.debug(f"Enriching {len(graph_results)} results with line text from S3")
        enriched_results = self.cypher_gen.retrieve_multiple_line_texts(graph_results)
        
        # Filter out results without line text
        valid_results = [r for r in enriched_results if r.get('line_text')]
        
        if not valid_results:
            logger.warning("No valid results with line text found")
            return {
                "answer": "I found potential answers but couldn't retrieve the source text.",
                "sources": [],
                "karakas": decomposition,
                "confidence": 0.0
            }
        
        # Use top result for answer generation
        top_result = valid_results[0]
        
        # Build prompt for Nemotron
        prompt = self._build_synthesis_prompt(question, top_result, decomposition)
        
        # Call Nemotron NIM to generate answer
        logger.debug("Calling Nemotron NIM for answer synthesis")
        try:
            answer_text = self.nim_client.call_nemotron(
                prompt=prompt,
                max_tokens=256,
                temperature=0.3  # Lower temperature for more focused answers
            )
        except Exception as e:
            logger.error(f"Error calling Nemotron NIM: {str(e)}")
            # Fallback to simple answer
            answer_text = self._generate_fallback_answer(top_result, decomposition)
        
        # Format sources
        sources = self._format_sources(valid_results)
        
        # Return complete answer dict
        return {
            "answer": answer_text.strip(),
            "sources": sources,
            "karakas": decomposition,
            "confidence": top_result.get('confidence', 0.0)
        }
    
    def _build_synthesis_prompt(
        self,
        question: str,
        result: Dict[str, Any],
        decomposition: Dict[str, Any]
    ) -> str:
        """
        Build prompt for Nemotron to synthesize natural language answer.
        
        Args:
            question: Original question
            result: Top result with answer, line_text, confidence
            decomposition: Query decomposition with Kāraka roles
            
        Returns:
            str: Formatted prompt
        """
        target_karaka = decomposition.get('target_karaka', 'KARTA')
        constraints = decomposition.get('constraints', {})
        verb = decomposition.get('verb', '')
        
        # Build constraint description
        constraint_desc = ""
        if constraints:
            constraint_parts = []
            for karaka, entity in constraints.items():
                constraint_parts.append(f"{entity} ({karaka})")
            constraint_desc = " with " + ", ".join(constraint_parts)
        
        prompt = f"""You are a semantic role-aware question answering system using Pāṇinian Kāraka theory.

Question: {question}

Context from knowledge graph:
- Answer: {result.get('answer', 'Unknown')}
- Role: {target_karaka} (the semantic role being asked about)
- Source text: "{result.get('line_text', '')}"
- Confidence: {result.get('confidence', 0.0):.2f}

Semantic roles (Kārakas):
- KARTA: Agent (who performs the action)
- KARMA: Patient/Object (what is acted upon)
- KARANA: Instrument (by what means)
- SAMPRADANA: Recipient (for whom, to whom)
- ADHIKARANA: Location (where)
- APADANA: Source (from where, from whom)

Task: Generate a natural language answer that:
1. Directly answers the question
2. Includes the Kāraka role annotation for the answer (e.g., "Rama (KARTA)")
3. Mentions other relevant Kāraka roles from the context{constraint_desc}
4. Is concise and clear (1-2 sentences)

Answer:"""
        
        return prompt
    
    def _generate_fallback_answer(
        self,
        result: Dict[str, Any],
        decomposition: Dict[str, Any]
    ) -> str:
        """
        Generate simple fallback answer if NIM call fails.
        
        Args:
            result: Top result with answer and confidence
            decomposition: Query decomposition
            
        Returns:
            str: Simple answer text
        """
        answer = result.get('answer', 'Unknown')
        target_karaka = decomposition.get('target_karaka', 'KARTA')
        
        return f"{answer} ({target_karaka})"
    
    def _format_sources(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Format source citations for response.
        
        Args:
            results: Enriched results with line_text
            
        Returns:
            List of formatted source dicts
        """
        sources = []
        
        for result in results:
            # Get document name from document_id (extract from path if needed)
            document_id = result.get('document_id', 'unknown')
            document_name = self._extract_document_name(document_id)
            
            source = {
                'line_number': result.get('line_number'),
                'text': result.get('line_text', ''),
                'confidence': result.get('confidence', 0.0),
                'document_id': document_id,
                'document_name': document_name
            }
            
            sources.append(source)
        
        return sources
    
    def _extract_document_name(self, document_id: str) -> str:
        """
        Extract human-readable document name from document ID.
        
        Args:
            document_id: Document identifier (e.g., "doc_123" or "ramayana_20250128")
            
        Returns:
            str: Document name
        """
        # If document_id contains underscore, try to extract meaningful name
        if '_' in document_id:
            parts = document_id.split('_')
            # Return first part as name (e.g., "ramayana" from "ramayana_20250128")
            return parts[0]
        
        return document_id
    
    def synthesize_batch(
        self,
        questions: List[str],
        graph_results_list: List[List[Dict[str, Any]]],
        decompositions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Synthesize answers for multiple questions.
        
        Args:
            questions: List of questions
            graph_results_list: List of graph results for each question
            decompositions: List of decompositions for each question
            
        Returns:
            List of answer dicts
        """
        answers = []
        
        for question, graph_results, decomposition in zip(
            questions, graph_results_list, decompositions
        ):
            answer = self.synthesize(question, graph_results, decomposition)
            answers.append(answer)
        
        return answers
