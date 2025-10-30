"""
Ingestion Pipeline for Kāraka RAG System
Orchestrates document processing and graph building
"""
from typing import Dict, Any
from .srl_parser import SRLParser
from .karaka_mapper import KarakaMapper
from .entity_resolver import EntityResolver
from .graph_builder import GraphBuilder

class IngestionPipeline:
    """Main ingestion pipeline"""
    
    def __init__(self):
        self.srl_parser = SRLParser()
        self.karaka_mapper = KarakaMapper()
        self.entity_resolver = EntityResolver()
        self.graph_builder = GraphBuilder()
    
    def process_document(self, content: str, document_name: str) -> Dict[str, Any]:
        """
        Process a document through the ingestion pipeline
        
        Args:
            content: Document text content
            document_name: Name of the document
            
        Returns:
            Dict with processing statistics
        """
        # Parse SRL
        srl_results = self.srl_parser.parse(content)
        
        # Map to Kāraka
        karaka_results = self.karaka_mapper.map(srl_results)
        
        # Resolve entities
        resolved_entities = self.entity_resolver.resolve(karaka_results)
        
        # Build graph
        stats = self.graph_builder.build(resolved_entities, document_name)
        
        return stats
