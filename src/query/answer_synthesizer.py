"""Answer synthesis using Nemotron NIM."""

from typing import Dict, Any, List
from src.utils.nim_client import NIMClient


class AnswerSynthesizer:
    """Synthesizes natural language answers from graph query results."""
    
    def __init__(self, nim_client: NIMClient):
        self.nim = nim_client
    
    def synthesize(
        self,
        question: str,
        graph_results: List[Dict[str, Any]],
        decomposition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate natural language answer from graph results.
        
        Args:
            question: Original question
            graph_results: Results from Cypher query (with line_text)
            decomposition: Query decomposition
            
        Returns:
            Dict with answer, sources, karakas, confidence
        """
        if not graph_results:
            return {
                "answer": "I couldn't find any information to answer that question in the knowledge graph.",
                "sources": [],
                "karakas": {},
                "confidence": 0.0
            }
        
        prompt = self._build_prompt(question, graph_results, decomposition)
        answer_text = self.nim.call_nemotron(prompt, max_tokens=300, temperature=0.3)
        
        # Format sources
        sources = self._format_sources(graph_results)
        
        # Extract Karakas from results
        karakas = self._extract_karakas(graph_results, decomposition)
        
        # Calculate average confidence
        avg_confidence = sum(r["confidence"] for r in graph_results) / len(graph_results)
        
        return {
            "answer": answer_text.strip(),
            "sources": sources,
            "karakas": karakas,
            "confidence": round(avg_confidence, 2)
        }
    
    def _build_prompt(
        self,
        question: str,
        graph_results: List[Dict[str, Any]],
        decomposition: Dict[str, Any]
    ) -> str:
        """Build prompt for answer generation."""
        target_karaka = decomposition.get("target_karaka", "")
        
        # Format evidence
        evidence_lines = []
        for idx, result in enumerate(graph_results[:5], start=1):  # Top 5 results
            evidence_lines.append(
                f"{idx}. \"{result['line_text']}\" "
                f"(Entity: {result['entity']}, Confidence: {result['confidence']:.2f})"
            )
        evidence = "\n".join(evidence_lines)
        
        return f"""You are answering questions about text using a semantic knowledge graph based on Sanskrit Kāraka theory.

Question: {question}

Target Semantic Role (Kāraka): {target_karaka}

Evidence from Knowledge Graph:
{evidence}

Instructions:
1. Answer the question directly and concisely
2. Use information from the evidence above
3. Mention the semantic role (Kāraka) when relevant
4. If multiple entities match, list them
5. Keep the answer natural and readable

Answer:"""
    
    def _format_sources(self, graph_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format sources for response."""
        sources = []
        for result in graph_results:
            sources.append({
                "line_text": result["line_text"],
                "line_number": result["line_number"],
                "entity": result["entity"],
                "confidence": round(result["confidence"], 2),
                "document_id": result["document_id"],
                "verb": result.get("verb", "")
            })
        return sources
    
    def _extract_karakas(
        self,
        graph_results: List[Dict[str, Any]],
        decomposition: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Extract Kāraka roles from results."""
        target_karaka = decomposition.get("target_karaka", "")
        
        karakas = {
            target_karaka: list(set(r["entity"] for r in graph_results))
        }
        
        # Add constraint Karakas
        for karaka_type, entity_mention in decomposition.get("constraints", {}).items():
            karakas[karaka_type] = [entity_mention]
        
        return karakas
