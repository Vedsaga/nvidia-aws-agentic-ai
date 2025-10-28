"""
Neo4j Client for Kāraka Graph RAG System

CRITICAL: All Kāraka relationships point FROM Action TO Entity
The Kriya (Action) is the binding force that connects entities through semantic roles.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from neo4j import GraphDatabase, Session
from neo4j.exceptions import Neo4jError

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Client for interacting with Neo4j graph database.
    
    Core Principle: Kriya-Centric Graph
    - Actions are the center of the graph
    - Entities are connected ONLY through actions
    - All Kāraka relationships: (Action)-[KARAKA]->(Entity)
    """
    
    def __init__(self, uri: str = None, username: str = None, password: str = None):
        """
        Initialize Neo4j client with connection parameters.
        
        Args:
            uri: Neo4j connection URI (default from env NEO4J_URI)
            username: Neo4j username (default from env NEO4J_USERNAME)
            password: Neo4j password (default from env NEO4J_PASSWORD)
        """
        self.uri = uri or os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.username = username or os.getenv('NEO4J_USERNAME', 'neo4j')
        self.password = password or os.getenv('NEO4J_PASSWORD', 'password')
        
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
            
            # Create indexes for performance
            self._create_indexes()
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def _create_indexes(self):
        """Create indexes on frequently queried properties."""
        with self.driver.session() as session:
            try:
                # Index on Entity canonical_name for fast lookups
                session.run(
                    "CREATE INDEX entity_canonical_name IF NOT EXISTS "
                    "FOR (e:Entity) ON (e.canonical_name)"
                )
                
                # Index on Action id for fast lookups
                session.run(
                    "CREATE INDEX action_id IF NOT EXISTS "
                    "FOR (a:Action) ON (a.id)"
                )
                
                # Index on Action document_id for filtering
                session.run(
                    "CREATE INDEX action_document_id IF NOT EXISTS "
                    "FOR (a:Action) ON (a.document_id)"
                )
                
                logger.info("Neo4j indexes created successfully")
            except Neo4jError as e:
                logger.warning(f"Index creation warning: {str(e)}")
    
    def create_entity(
        self,
        canonical_name: str,
        aliases: List[str],
        document_ids: List[str],
        embedding: List[float] = None
    ) -> Dict[str, Any]:
        """
        Create an entity node in Neo4j using MERGE (creates ONCE, idempotent).
        
        Args:
            canonical_name: The canonical name for the entity
            aliases: List of alias names for this entity
            document_ids: List of document IDs where this entity appears
            embedding: Optional embedding vector for similarity matching
        
        Returns:
            Dict with entity details
        """
        with self.driver.session() as session:
            try:
                result = session.run(
                    """
                    MERGE (e:Entity {canonical_name: $canonical_name})
                    ON CREATE SET
                        e.aliases = $aliases,
                        e.document_ids = $document_ids,
                        e.embedding = $embedding,
                        e.created_at = datetime()
                    ON MATCH SET
                        e.aliases = e.aliases + [x IN $aliases WHERE NOT x IN e.aliases],
                        e.document_ids = e.document_ids + [x IN $document_ids WHERE NOT x IN e.document_ids]
                    RETURN e.canonical_name AS canonical_name,
                           e.aliases AS aliases,
                           e.document_ids AS document_ids
                    """,
                    canonical_name=canonical_name,
                    aliases=aliases,
                    document_ids=document_ids,
                    embedding=embedding
                )
                
                record = result.single()
                if record:
                    logger.debug(f"Entity created/updated: {canonical_name}")
                    return {
                        'canonical_name': record['canonical_name'],
                        'aliases': record['aliases'],
                        'document_ids': record['document_ids']
                    }
                else:
                    raise Neo4jError("Failed to create entity")
                    
            except Neo4jError as e:
                logger.error(f"Error creating entity {canonical_name}: {str(e)}")
                raise
    
    def add_entity_alias(
        self,
        canonical_name: str,
        alias: str,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Add an alias to an existing entity (does NOT create duplicate).
        
        Args:
            canonical_name: The canonical name of the entity
            alias: New alias to add
            document_id: Document ID where this alias appears
        
        Returns:
            Dict with updated entity details
        """
        with self.driver.session() as session:
            try:
                result = session.run(
                    """
                    MATCH (e:Entity {canonical_name: $canonical_name})
                    SET e.aliases = CASE
                        WHEN $alias IN e.aliases THEN e.aliases
                        ELSE e.aliases + [$alias]
                    END,
                    e.document_ids = CASE
                        WHEN $document_id IN e.document_ids THEN e.document_ids
                        ELSE e.document_ids + [$document_id]
                    END
                    RETURN e.canonical_name AS canonical_name,
                           e.aliases AS aliases,
                           e.document_ids AS document_ids
                    """,
                    canonical_name=canonical_name,
                    alias=alias,
                    document_id=document_id
                )
                
                record = result.single()
                if record:
                    logger.debug(f"Alias '{alias}' added to entity: {canonical_name}")
                    return {
                        'canonical_name': record['canonical_name'],
                        'aliases': record['aliases'],
                        'document_ids': record['document_ids']
                    }
                else:
                    raise Neo4jError(f"Entity not found: {canonical_name}")
                    
            except Neo4jError as e:
                logger.error(f"Error adding alias to entity {canonical_name}: {str(e)}")
                raise
    
    def create_action(
        self,
        action_id: str,
        verb: str,
        line_number: int,
        action_sequence: int,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Create an action node in Neo4j (NO sentence text stored).
        
        Args:
            action_id: Unique action identifier (e.g., "action_5_0")
            verb: The verb/action (e.g., "gave")
            line_number: Line number in document
            action_sequence: Order within line if multiple verbs (0, 1, 2...)
            document_id: Source document identifier
        
        Returns:
            Dict with action details
        """
        with self.driver.session() as session:
            try:
                result = session.run(
                    """
                    CREATE (a:Action {
                        id: $action_id,
                        verb: $verb,
                        line_number: $line_number,
                        action_sequence: $action_sequence,
                        document_id: $document_id,
                        created_at: datetime()
                    })
                    RETURN a.id AS id,
                           a.verb AS verb,
                           a.line_number AS line_number,
                           a.action_sequence AS action_sequence,
                           a.document_id AS document_id
                    """,
                    action_id=action_id,
                    verb=verb,
                    line_number=line_number,
                    action_sequence=action_sequence,
                    document_id=document_id
                )
                
                record = result.single()
                if record:
                    logger.debug(f"Action created: {action_id} ({verb})")
                    return {
                        'id': record['id'],
                        'verb': record['verb'],
                        'line_number': record['line_number'],
                        'action_sequence': record['action_sequence'],
                        'document_id': record['document_id']
                    }
                else:
                    raise Neo4jError("Failed to create action")
                    
            except Neo4jError as e:
                logger.error(f"Error creating action {action_id}: {str(e)}")
                raise
    
    def create_karaka_relationship(
        self,
        action_id: str,
        karaka_type: str,
        entity_name: str,
        confidence: float,
        line_number: int,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Create a Kāraka relationship with CORRECT direction: Action -> Entity.
        
        CRITICAL: The Kriya (Action) is the binding force.
        Relationships MUST point FROM Action TO Entity.
        
        Args:
            action_id: Action node identifier
            karaka_type: Kāraka role (KARTA, KARMA, KARANA, SAMPRADANA, ADHIKARANA, APADANA)
            entity_name: Entity canonical name
            confidence: Confidence score (0.0 - 1.0)
            line_number: Source line number
            document_id: Source document identifier
        
        Returns:
            Dict with relationship details
        """
        valid_karakas = ['KARTA', 'KARMA', 'KARANA', 'SAMPRADANA', 'ADHIKARANA', 'APADANA']
        if karaka_type not in valid_karakas:
            raise ValueError(f"Invalid Kāraka type: {karaka_type}. Must be one of {valid_karakas}")
        
        with self.driver.session() as session:
            try:
                # CORRECT: (Action)-[KARAKA]->(Entity)
                result = session.run(
                    f"""
                    MATCH (a:Action {{id: $action_id}})
                    MATCH (e:Entity {{canonical_name: $entity_name}})
                    CREATE (a)-[r:{karaka_type} {{
                        confidence: $confidence,
                        line_number: $line_number,
                        document_id: $document_id,
                        created_at: datetime()
                    }}]->(e)
                    RETURN type(r) AS karaka_type,
                           r.confidence AS confidence,
                           r.line_number AS line_number,
                           r.document_id AS document_id
                    """,
                    action_id=action_id,
                    entity_name=entity_name,
                    confidence=confidence,
                    line_number=line_number,
                    document_id=document_id
                )
                
                record = result.single()
                if record:
                    logger.debug(
                        f"Kāraka relationship created: {action_id} -[{karaka_type}]-> {entity_name}"
                    )
                    return {
                        'action_id': action_id,
                        'karaka_type': record['karaka_type'],
                        'entity_name': entity_name,
                        'confidence': record['confidence'],
                        'line_number': record['line_number'],
                        'document_id': record['document_id']
                    }
                else:
                    raise Neo4jError("Failed to create Kāraka relationship")
                    
            except Neo4jError as e:
                logger.error(
                    f"Error creating Kāraka relationship {action_id} -[{karaka_type}]-> {entity_name}: {str(e)}"
                )
                raise
    
    def execute_query(self, cypher: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute an arbitrary Cypher query.
        
        Args:
            cypher: Cypher query string
            params: Query parameters
        
        Returns:
            List of result records as dictionaries
        """
        with self.driver.session() as session:
            try:
                result = session.run(cypher, params or {})
                records = [dict(record) for record in result]
                logger.debug(f"Query executed: {len(records)} results")
                return records
            except Neo4jError as e:
                logger.error(f"Error executing query: {str(e)}")
                raise
    
    def get_graph_for_visualization(
        self,
        document_filter: str = None,
        limit: int = 100
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve graph data for visualization.
        
        Args:
            document_filter: Optional document ID to filter results
            limit: Maximum number of nodes to return
        
        Returns:
            Dict with 'nodes' and 'edges' lists
        """
        with self.driver.session() as session:
            try:
                # Build query with optional document filter
                where_clause = "WHERE a.document_id = $document_id" if document_filter else ""
                
                # Get all actions and entities with their relationships
                query = f"""
                MATCH (a:Action)-[r]->(e:Entity)
                {where_clause}
                WITH a, e, r
                LIMIT $limit
                RETURN 
                    collect(DISTINCT {{
                        id: 'action_' + a.id,
                        label: a.verb,
                        type: 'Action',
                        document_id: a.document_id,
                        line_number: a.line_number,
                        action_sequence: a.action_sequence
                    }}) AS actions,
                    collect(DISTINCT {{
                        id: 'entity_' + e.canonical_name,
                        label: e.canonical_name,
                        type: 'Entity',
                        document_ids: e.document_ids,
                        aliases: e.aliases
                    }}) AS entities,
                    collect({{
                        from: 'action_' + a.id,
                        to: 'entity_' + e.canonical_name,
                        label: type(r),
                        confidence: r.confidence,
                        document_id: r.document_id,
                        line_number: r.line_number
                    }}) AS relationships
                """
                
                params = {'limit': limit}
                if document_filter:
                    params['document_id'] = document_filter
                
                result = session.run(query, params)
                record = result.single()
                
                if record:
                    nodes = record['actions'] + record['entities']
                    edges = record['relationships']
                    
                    logger.debug(f"Graph retrieved: {len(nodes)} nodes, {len(edges)} edges")
                    return {
                        'nodes': nodes,
                        'edges': edges
                    }
                else:
                    return {'nodes': [], 'edges': []}
                    
            except Neo4jError as e:
                logger.error(f"Error retrieving graph: {str(e)}")
                raise
    
    def find_entity_by_name_or_alias(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find an entity by canonical name or alias.
        
        Args:
            name: Entity name or alias to search for
        
        Returns:
            Entity dict if found, None otherwise
        """
        with self.driver.session() as session:
            try:
                result = session.run(
                    """
                    MATCH (e:Entity)
                    WHERE e.canonical_name = $name OR $name IN e.aliases
                    RETURN e.canonical_name AS canonical_name,
                           e.aliases AS aliases,
                           e.document_ids AS document_ids,
                           e.embedding AS embedding
                    LIMIT 1
                    """,
                    name=name
                )
                
                record = result.single()
                if record:
                    return {
                        'canonical_name': record['canonical_name'],
                        'aliases': record['aliases'],
                        'document_ids': record['document_ids'],
                        'embedding': record['embedding']
                    }
                return None
                
            except Neo4jError as e:
                logger.error(f"Error finding entity {name}: {str(e)}")
                raise
    
    def get_all_entities_with_embeddings(self) -> List[Dict[str, Any]]:
        """
        Retrieve all entities that have embeddings for similarity comparison.
        
        Returns:
            List of entity dicts with embeddings
        """
        with self.driver.session() as session:
            try:
                result = session.run(
                    """
                    MATCH (e:Entity)
                    WHERE e.embedding IS NOT NULL
                    RETURN e.canonical_name AS canonical_name,
                           e.aliases AS aliases,
                           e.document_ids AS document_ids,
                           e.embedding AS embedding
                    """
                )
                
                entities = [dict(record) for record in result]
                logger.debug(f"Retrieved {len(entities)} entities with embeddings")
                return entities
                
            except Neo4jError as e:
                logger.error(f"Error retrieving entities: {str(e)}")
                raise
    
    def clear_database(self):
        """
        Clear all nodes and relationships from the database.
        WARNING: This is destructive and should only be used for testing.
        """
        with self.driver.session() as session:
            try:
                session.run("MATCH (n) DETACH DELETE n")
                logger.warning("Database cleared - all nodes and relationships deleted")
            except Neo4jError as e:
                logger.error(f"Error clearing database: {str(e)}")
                raise
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
