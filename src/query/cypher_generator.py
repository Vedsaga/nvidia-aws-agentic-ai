"""
Cypher Generator for building Neo4j queries from decomposed questions.
Generates queries with CORRECT direction: (Action)-[KARAKA]->(Entity)
"""
import json
import logging
import os
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class CypherGenerator:
    """Generates Neo4j Cypher queries from decomposed questions."""
    
    def __init__(self, s3_bucket: Optional[str] = None, aws_region: Optional[str] = None):
        """
        Initialize Cypher Generator.
        
        Args:
            s3_bucket: S3 bucket name for document storage
            aws_region: AWS region for S3 client
        """
        self.s3_bucket = s3_bucket or os.getenv('S3_BUCKET', 'karaka-rag-jobs')
        self.aws_region = aws_region or os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize S3 client
        self.s3_client = boto3.client('s3', region_name=self.aws_region)
    
    def generate(
        self,
        decomposition: Dict[str, Any],
        min_confidence: float = 0.8,
        document_filter: Optional[str] = None
    ) -> str:
        """
        Generate Cypher query from decomposed question.
        
        CRITICAL: Uses CORRECT direction: (Action)-[KARAKA]->(Entity)
        The Kriya (Action) is the center that binds entities through Kāraka roles.
        
        Args:
            decomposition: Dict with target_karaka, constraints, verb
            min_confidence: Minimum confidence threshold for relationships
            document_filter: Optional document ID to filter results
            
        Returns:
            str: Cypher query
            
        Example:
            Input: {
                "target_karaka": "KARTA",
                "constraints": {"KARMA": "bow", "SAMPRADANA": "Lakshmana"},
                "verb": "give"
            }
            
            Output: Cypher query that finds who (KARTA) gave bow to Lakshmana
        """
        target_karaka = decomposition.get('target_karaka', 'KARTA')
        constraints = decomposition.get('constraints', {})
        verb = decomposition.get('verb')
        
        logger.info(
            f"Generating Cypher query: target={target_karaka}, "
            f"constraints={constraints}, verb={verb}, "
            f"min_confidence={min_confidence}, document_filter={document_filter}"
        )
        
        # Build MATCH pattern with CORRECT direction: Action -> Entity
        query_parts = []
        
        # Main MATCH: Find action with target Kāraka relationship
        query_parts.append(
            f"MATCH (a:Action)-[r:{target_karaka}]->(e:Entity)"
        )
        
        # WHERE clauses
        where_clauses = []
        
        # Confidence threshold
        where_clauses.append(f"r.confidence >= {min_confidence}")
        
        # Verb matching
        if verb:
            # Normalize verb for matching
            verb_normalized = verb.lower().strip()
            where_clauses.append(f"toLower(a.verb) = '{verb_normalized}'")
        
        # Document filtering
        if document_filter:
            where_clauses.append(f"a.document_id = '{document_filter}'")
        
        # Add WHERE clause if we have conditions
        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))
        
        # Add constraint MATCH patterns for other Kārakas
        # These ensure the action also has the specified constraint entities
        constraint_matches = []
        for i, (karaka_type, entity_name) in enumerate(constraints.items()):
            # Each constraint gets its own entity variable
            entity_var = f"e{i}"
            constraint_matches.append(
                f"MATCH (a)-[:{karaka_type}]->({entity_var}:Entity)"
            )
            constraint_matches.append(
                f"WHERE toLower({entity_var}.canonical_name) = toLower('{entity_name}')"
            )
        
        # Add constraint matches
        query_parts.extend(constraint_matches)
        
        # RETURN clause
        # Return entity name, line_number, document_id, confidence
        # NO sentence text from graph - retrieve separately from S3
        query_parts.append("""
RETURN e.canonical_name AS answer,
       a.line_number AS line_number,
       a.document_id AS document_id,
       r.confidence AS confidence
ORDER BY r.confidence DESC
LIMIT 5
""")
        
        query = "\n".join(query_parts)
        
        logger.debug(f"Generated Cypher query:\n{query}")
        
        return query
    
    def retrieve_line_text(self, document_id: str, line_number: int) -> Optional[str]:
        """
        Retrieve sentence text from S3 document storage.
        
        The graph stores only line_number and document_id, not the actual text.
        This method fetches the text from the job status file in S3.
        
        Args:
            document_id: Document identifier
            line_number: Line number in the document
            
        Returns:
            str: Line text, or None if not found
        """
        try:
            # Construct S3 key for job status file
            s3_key = f"jobs/{document_id}.json"
            
            logger.debug(f"Retrieving line text from S3: {s3_key}, line {line_number}")
            
            # Get job status file from S3
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=s3_key
            )
            
            # Parse JSON
            job_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Find the line in results
            results = job_data.get('results', [])
            for result in results:
                if result.get('line_number') == line_number:
                    line_text = result.get('line_text', '')
                    logger.debug(f"Found line text: {line_text}")
                    return line_text
            
            logger.warning(
                f"Line {line_number} not found in document {document_id}"
            )
            return None
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.error(
                    f"Document not found in S3: {document_id}"
                )
            else:
                logger.error(
                    f"S3 error retrieving line text: {str(e)}"
                )
            return None
            
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse job data for document {document_id}: {str(e)}"
            )
            return None
            
        except Exception as e:
            logger.error(
                f"Error retrieving line text: {str(e)}"
            )
            return None
    
    def retrieve_multiple_line_texts(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve line texts for multiple query results.
        
        Optimizes S3 calls by grouping results by document_id.
        
        Args:
            results: List of query results with document_id and line_number
            
        Returns:
            List of results enriched with line_text field
        """
        # Group results by document_id to minimize S3 calls
        docs_cache = {}
        enriched_results = []
        
        for result in results:
            document_id = result.get('document_id')
            line_number = result.get('line_number')
            
            if not document_id or line_number is None:
                logger.warning(f"Missing document_id or line_number in result: {result}")
                enriched_results.append({**result, 'line_text': None})
                continue
            
            # Load document data if not cached
            if document_id not in docs_cache:
                try:
                    s3_key = f"jobs/{document_id}.json"
                    response = self.s3_client.get_object(
                        Bucket=self.s3_bucket,
                        Key=s3_key
                    )
                    job_data = json.loads(response['Body'].read().decode('utf-8'))
                    docs_cache[document_id] = job_data.get('results', [])
                except Exception as e:
                    logger.error(f"Error loading document {document_id}: {str(e)}")
                    docs_cache[document_id] = []
            
            # Find line text in cached document
            line_text = None
            for doc_result in docs_cache[document_id]:
                if doc_result.get('line_number') == line_number:
                    line_text = doc_result.get('line_text', '')
                    break
            
            enriched_results.append({
                **result,
                'line_text': line_text
            })
        
        return enriched_results
