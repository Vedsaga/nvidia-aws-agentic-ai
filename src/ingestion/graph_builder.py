"""
Graph Builder for Kāraka Graph RAG System

Orchestrates the full ingestion pipeline:
1. Parse lines with SRL to extract verbs and semantic roles
2. Map SRL roles to Kāraka types
3. Resolve entities to canonical names
4. Create action nodes in Neo4j
5. Create Kāraka relationships FROM Action TO Entity

Handles multiple verbs per line and ensures entities are created ONCE.
"""

import logging
import json
import boto3
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError

from src.ingestion.srl_parser import SRLParser
from src.ingestion.karaka_mapper import KarakaMapper
from src.ingestion.entity_resolver import EntityResolver
from src.graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class GraphBuilder:
    """
    Orchestrates the full pipeline for building the Kāraka knowledge graph.
    
    Key Features:
    - Processes lines (not sentences) to handle multiple verbs per line
    - Creates action nodes with line_number and action_sequence
    - Ensures entities are created ONCE and reused across actions
    - Creates Kāraka relationships with CORRECT direction: Action -> Entity
    - Stores document content in S3 for later line text retrieval
    """
    
    def __init__(
        self,
        srl_parser: SRLParser,
        karaka_mapper: KarakaMapper,
        entity_resolver: EntityResolver,
        neo4j_client: Neo4jClient,
        s3_client=None,
        s3_bucket: str = None,
        default_confidence: float = 0.9
    ):
        """
        Initialize Graph Builder with required components.
        
        Args:
            srl_parser: SRL parser for extracting semantic roles
            karaka_mapper: Mapper for converting SRL to Kāraka roles
            entity_resolver: Resolver for entity mentions
            neo4j_client: Neo4j client for graph operations
            s3_client: Boto3 S3 client for document storage
            s3_bucket: S3 bucket name for document storage
            default_confidence: Default confidence score for relationships (0.0-1.0)
        """
        self.srl_parser = srl_parser
        self.karaka_mapper = karaka_mapper
        self.entity_resolver = entity_resolver
        self.neo4j_client = neo4j_client
        self.s3_client = s3_client or boto3.client('s3')
        self.s3_bucket = s3_bucket
        self.default_confidence = default_confidence
        
        logger.info("GraphBuilder initialized")
    
    def process_line(
        self,
        line_text: str,
        line_number: int,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Process a single line and create graph nodes/relationships.
        
        Algorithm:
        1. Parse line with SRL to extract ALL verbs and their roles
        2. For each verb:
           a. Map SRL roles to Kāraka types
           b. Resolve each entity mention to canonical name
           c. Create action node in Neo4j
           d. Create Kāraka relationships FROM Action TO Entity
        
        Args:
            line_text: The text of the line to process
            line_number: Line number in the document (1-indexed)
            document_id: Document identifier
        
        Returns:
            Dict with processing status and extracted actions
            {
                'status': 'success|skipped|error',
                'line_number': int,
                'line_text': str,
                'actions': [
                    {
                        'action_id': str,
                        'verb': str,
                        'action_sequence': int,
                        'karakas': {karaka_type: entity_name}
                    }
                ],
                'error': str or None
            }
        """
        result = {
            'status': 'success',
            'line_number': line_number,
            'line_text': line_text,
            'actions': [],
            'error': None
        }
        
        try:
            # Skip empty lines
            if not line_text or not line_text.strip():
                result['status'] = 'skipped'
                logger.debug(f"Line {line_number}: Empty, skipped")
                return result
            
            # Parse line to extract ALL verbs and their semantic roles
            verb_roles_list = self.srl_parser.parse_line(line_text)
            
            if not verb_roles_list:
                result['status'] = 'skipped'
                logger.debug(f"Line {line_number}: No verbs found, skipped")
                return result
            
            # Process each verb in the line
            for action_sequence, (verb, srl_roles) in enumerate(verb_roles_list):
                try:
                    action_data = self._process_verb(
                        verb=verb,
                        srl_roles=srl_roles,
                        line_number=line_number,
                        action_sequence=action_sequence,
                        document_id=document_id
                    )
                    
                    result['actions'].append(action_data)
                    logger.debug(
                        f"Line {line_number}, action {action_sequence}: "
                        f"Processed verb '{verb}' with {len(action_data['karakas'])} Kārakas"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Line {line_number}, action {action_sequence}: "
                        f"Error processing verb '{verb}': {str(e)}"
                    )
                    # Continue processing other verbs in the line
                    continue
            
            if not result['actions']:
                result['status'] = 'skipped'
                logger.debug(f"Line {line_number}: No actions created")
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            logger.error(f"Line {line_number}: Processing error: {str(e)}")
        
        return result
    
    def _process_verb(
        self,
        verb: str,
        srl_roles: Dict[str, str],
        line_number: int,
        action_sequence: int,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Process a single verb and create action node with Kāraka relationships.
        
        Args:
            verb: The verb text
            srl_roles: SRL roles dict {role: entity_mention}
            line_number: Line number in document
            action_sequence: Order within line (0, 1, 2...)
            document_id: Document identifier
        
        Returns:
            Dict with action details and Kāraka mappings
        """
        # Map SRL roles to Kāraka types
        karaka_roles = self.karaka_mapper.map_to_karakas(srl_roles)
        
        if not karaka_roles:
            raise ValueError(f"No Kāraka roles mapped for verb '{verb}'")
        
        # Create action ID: action_{line_number}_{action_sequence}
        action_id = f"action_{line_number}_{action_sequence}"
        
        # Create action node in Neo4j (NO sentence text)
        self.neo4j_client.create_action(
            action_id=action_id,
            verb=verb,
            line_number=line_number,
            action_sequence=action_sequence,
            document_id=document_id
        )
        
        # Resolve entities and create Kāraka relationships
        resolved_karakas = {}
        
        for karaka_type, entity_mention in karaka_roles.items():
            try:
                # Resolve entity mention to canonical name
                # Entity nodes are created ONCE by resolver and reused
                canonical_name = self.entity_resolver.resolve_entity(
                    entity_mention=entity_mention,
                    document_id=document_id
                )
                
                # Create Kāraka relationship: Action -> Entity
                self.neo4j_client.create_karaka_relationship(
                    action_id=action_id,
                    karaka_type=karaka_type,
                    entity_name=canonical_name,
                    confidence=self.default_confidence,
                    line_number=line_number,
                    document_id=document_id
                )
                
                resolved_karakas[karaka_type] = canonical_name
                
                logger.debug(
                    f"Created relationship: {action_id} -[{karaka_type}]-> {canonical_name}"
                )
                
            except Exception as e:
                logger.error(
                    f"Error processing Kāraka {karaka_type} for entity '{entity_mention}': {str(e)}"
                )
                # Continue with other Kārakas
                continue
        
        return {
            'action_id': action_id,
            'verb': verb,
            'action_sequence': action_sequence,
            'karakas': resolved_karakas
        }
    
    def process_document(
        self,
        lines: List[str],
        document_id: str,
        document_name: str = None
    ) -> Dict[str, Any]:
        """
        Process all lines in a document and build the knowledge graph.
        
        Args:
            lines: List of text lines from the document
            document_id: Unique document identifier
            document_name: Optional document name for metadata
        
        Returns:
            Dict with processing statistics and results
            {
                'document_id': str,
                'document_name': str,
                'total_lines': int,
                'processed': int,
                'results': [line_result_dicts],
                'statistics': {
                    'success': int,
                    'skipped': int,
                    'errors': int
                }
            }
        """
        logger.info(
            f"Processing document {document_id} ({document_name}): {len(lines)} lines"
        )
        
        # Clear entity cache for new document
        self.entity_resolver.clear_cache()
        
        results = []
        stats = {
            'success': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Process each line
        for line_number, line_text in enumerate(lines, start=1):
            line_result = self.process_line(
                line_text=line_text,
                line_number=line_number,
                document_id=document_id
            )
            
            results.append(line_result)
            
            # Update statistics
            status = line_result['status']
            if status == 'success':
                stats['success'] += 1
            elif status == 'skipped':
                stats['skipped'] += 1
            elif status == 'error':
                stats['errors'] += 1
        
        # Store document content in S3 for later retrieval
        if self.s3_bucket:
            try:
                self._store_document_in_s3(
                    document_id=document_id,
                    document_name=document_name,
                    lines=lines,
                    results=results
                )
            except Exception as e:
                logger.error(f"Failed to store document in S3: {str(e)}")
        
        logger.info(
            f"Document {document_id} processed: "
            f"{stats['success']} success, {stats['skipped']} skipped, {stats['errors']} errors"
        )
        
        return {
            'document_id': document_id,
            'document_name': document_name or document_id,
            'total_lines': len(lines),
            'processed': len(results),
            'results': results,
            'statistics': stats
        }
    
    def _store_document_in_s3(
        self,
        document_id: str,
        document_name: str,
        lines: List[str],
        results: List[Dict[str, Any]]
    ):
        """
        Store document content and processing results in S3.
        
        This enables later retrieval of line text using document_id + line_number.
        
        Args:
            document_id: Document identifier
            document_name: Document name
            lines: Original document lines
            results: Processing results for each line
        """
        document_data = {
            'document_id': document_id,
            'document_name': document_name,
            'total_lines': len(lines),
            'lines': lines,
            'results': results
        }
        
        try:
            key = f"documents/{document_id}.json"
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=json.dumps(document_data, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"Document stored in S3: s3://{self.s3_bucket}/{key}")
            
        except ClientError as e:
            logger.error(f"S3 storage error: {str(e)}")
            raise
    
    def retrieve_line_text(
        self,
        document_id: str,
        line_number: int
    ) -> Optional[str]:
        """
        Retrieve line text from S3 document storage.
        
        Args:
            document_id: Document identifier
            line_number: Line number (1-indexed)
        
        Returns:
            Line text if found, None otherwise
        """
        if not self.s3_bucket:
            logger.warning("S3 bucket not configured, cannot retrieve line text")
            return None
        
        try:
            key = f"documents/{document_id}.json"
            
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=key
            )
            
            document_data = json.loads(response['Body'].read())
            
            # Lines are 1-indexed, list is 0-indexed
            if 1 <= line_number <= len(document_data['lines']):
                return document_data['lines'][line_number - 1]
            else:
                logger.warning(
                    f"Line number {line_number} out of range for document {document_id}"
                )
                return None
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Document not found in S3: {document_id}")
            else:
                logger.error(f"S3 retrieval error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving line text: {str(e)}")
            return None
