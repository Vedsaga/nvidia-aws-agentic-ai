"""Cypher query generation from decomposed queries."""

from typing import Dict, Any, List, Optional
from src.graph.neo4j_client import Neo4jClient
import boto3


class CypherGenerator:
    """Generates Cypher queries from decomposed questions."""
    
    def __init__(self, neo4j_client: Neo4jClient, s3_bucket: str):
        self.neo4j = neo4j_client
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3')
    
    def generate(
        self,
        decomposition: Dict[str, Any],
        min_confidence: float = 0.5,
        document_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate and execute Cypher query.
        
        Args:
            decomposition: Decomposed query from QueryDecomposer
            min_confidence: Minimum confidence threshold
            document_filter: Optional document_id to filter results
            
        Returns:
            List of results with entity, line_number, confidence, document_id
        """
        cypher = self._build_cypher(decomposition, min_confidence, document_filter)
        params = self._build_params(decomposition, min_confidence, document_filter)
        
        results = self.neo4j.execute_query(cypher, params)
        
        # Enrich results with line text from S3
        enriched_results = []
        for result in results:
            line_text = self.retrieve_line_text(result["document_id"], result["line_number"])
            enriched_results.append({
                **result,
                "line_text": line_text
            })
        
        return enriched_results
    
    def _build_cypher(
        self,
        decomposition: Dict[str, Any],
        min_confidence: float,
        document_filter: Optional[str]
    ) -> str:
        """Build Cypher query string."""
        target_karaka = decomposition["target_karaka"]
        verb = decomposition.get("verb")
        constraints = decomposition.get("constraints", {})
        
        # Base pattern: Action -> Target Entity
        cypher_parts = [
            f"MATCH (a:Action)-[r:{target_karaka}]->(e:Entity)"
        ]
        
        # Add constraint patterns for other Karakas
        constraint_idx = 0
        for karaka_type, entity_mention in constraints.items():
            constraint_idx += 1
            cypher_parts.append(
                f"MATCH (a)-[r{constraint_idx}:{karaka_type}]->(e{constraint_idx}:Entity)"
            )
        
        # WHERE clauses
        where_clauses = [f"r.confidence >= $min_confidence"]
        
        if verb:
            where_clauses.append("toLower(a.verb) = toLower($verb)")
        
        if document_filter:
            where_clauses.append("a.document_id = $document_filter")
        
        # Add constraint entity matching
        for idx, (karaka_type, entity_mention) in enumerate(constraints.items(), start=1):
            where_clauses.append(
                f"(toLower(e{idx}.canonical_name) = toLower($constraint_{idx}) OR "
                f"toLower($constraint_{idx}) IN [x IN e{idx}.aliases | toLower(x)])"
            )
        
        if where_clauses:
            cypher_parts.append("WHERE " + " AND ".join(where_clauses))
        
        # RETURN clause
        cypher_parts.append(
            "RETURN DISTINCT e.canonical_name as entity, "
            "r.line_number as line_number, "
            "r.confidence as confidence, "
            "r.document_id as document_id, "
            "a.verb as verb "
            "ORDER BY r.confidence DESC, r.line_number ASC "
            "LIMIT 20"
        )
        
        return "\n".join(cypher_parts)
    
    def _build_params(
        self,
        decomposition: Dict[str, Any],
        min_confidence: float,
        document_filter: Optional[str]
    ) -> Dict[str, Any]:
        """Build query parameters."""
        params = {
            "min_confidence": min_confidence
        }
        
        if decomposition.get("verb"):
            params["verb"] = decomposition["verb"]
        
        if document_filter:
            params["document_filter"] = document_filter
        
        # Add constraint parameters
        for idx, (karaka_type, entity_mention) in enumerate(decomposition.get("constraints", {}).items(), start=1):
            params[f"constraint_{idx}"] = entity_mention
        
        return params
    
    def retrieve_line_text(self, document_id: str, line_number: int) -> str:
        """
        Retrieve specific line text from S3.
        
        Args:
            document_id: Document identifier
            line_number: Line number (1-indexed)
            
        Returns:
            Line text
        """
        key = f"documents/{document_id}/content.txt"
        
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            lines = content.split('\n')
            
            if 1 <= line_number <= len(lines):
                return lines[line_number - 1]
            else:
                return ""
        except Exception as e:
            return f"Error: {str(e)}"
