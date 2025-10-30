"""
Query Processor for Kāraka RAG System
Handles query processing and answer generation
"""
from typing import Dict, Any
from .decomposer import QueryDecomposer
from .cypher_generator import CypherGenerator
from .answer_synthesizer import AnswerSynthesizer

class QueryProcessor:
    """Main query processor"""
    
    def __init__(self):
        self.decomposer = QueryDecomposer()
        self.cypher_generator = CypherGenerator()
        self.answer_synthesizer = AnswerSynthesizer()
    
    def process_query(self, question: str, min_confidence: float = 0.7) -> Dict[str, Any]:
        """
        Process a query and generate an answer
        
        Args:
            question: User question
            min_confidence: Minimum confidence threshold
            
        Returns:
            Dict with answer and metadata
        """
        # Decompose query
        decomposed = self.decomposer.decompose(question)
        
        # Generate Cypher queries
        cypher_queries = self.cypher_generator.generate(decomposed)
        
        # Execute and synthesize answer
        result = self.answer_synthesizer.synthesize(
            question=question,
            cypher_queries=cypher_queries,
            min_confidence=min_confidence
        )
        
        return result
