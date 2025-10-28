"""
Entity Resolver for Kāraka Graph RAG System

Resolves entity mentions to canonical names using embedding similarity.
Ensures each unique entity is created ONCE in Neo4j and reused across multiple actions.
"""

import logging
from typing import Dict, Optional, List
import numpy as np

logger = logging.getLogger(__name__)


class EntityResolver:
    """
    Resolves entity mentions to canonical entity names using embedding similarity.
    
    Key Features:
    - In-memory cache to ensure each entity is created ONCE per document processing
    - Checks Neo4j for existing entities by canonical_name or aliases
    - Uses embedding similarity (cosine) to match entity mentions
    - Adds aliases and document_ids to existing entities (no duplicates)
    - Creates new entities when similarity is below threshold
    """
    
    def __init__(self, nim_client, neo4j_client, similarity_threshold: float = 0.85):
        """
        Initialize Entity Resolver.
        
        Args:
            nim_client: NIM client for getting embeddings
            neo4j_client: Neo4j client for entity operations
            similarity_threshold: Minimum cosine similarity to consider entities the same (default 0.85)
        """
        self.nim_client = nim_client
        self.neo4j_client = neo4j_client
        self.similarity_threshold = similarity_threshold
        
        # In-memory cache: entity_mention -> canonical_name
        # Ensures each entity is created ONCE during document processing
        self.entity_cache: Dict[str, str] = {}
        
        logger.info(f"EntityResolver initialized with similarity threshold: {similarity_threshold}")
    
    def resolve_entity(self, entity_mention: str, document_id: str) -> str:
        """
        Resolve an entity mention to its canonical name.
        
        Algorithm:
        1. Check in-memory cache first
        2. Check Neo4j for existing entity by name or alias
        3. If not found, get embedding and compare with existing entities
        4. If similarity > threshold, add alias and document_id to existing entity
        5. Otherwise, create new entity with document_id
        
        Args:
            entity_mention: The entity text to resolve (e.g., "Rama", "the prince", "he")
            document_id: Document identifier where this mention appears
        
        Returns:
            str: Canonical entity name
        """
        # Normalize entity mention
        entity_mention = entity_mention.strip()
        
        if not entity_mention:
            raise ValueError("Entity mention cannot be empty")
        
        # Check cache first (fast path)
        if entity_mention in self.entity_cache:
            canonical_name = self.entity_cache[entity_mention]
            logger.debug(f"Entity '{entity_mention}' found in cache: {canonical_name}")
            return canonical_name
        
        # Check Neo4j for exact match by canonical_name or alias
        existing_entity = self.neo4j_client.find_entity_by_name_or_alias(entity_mention)
        
        if existing_entity:
            # Found exact match - add document_id if not already present
            canonical_name = existing_entity['canonical_name']
            
            if document_id not in existing_entity.get('document_ids', []):
                self.neo4j_client.add_entity_alias(canonical_name, entity_mention, document_id)
                logger.debug(
                    f"Entity '{entity_mention}' matched existing entity: {canonical_name}, "
                    f"added document_id: {document_id}"
                )
            else:
                logger.debug(f"Entity '{entity_mention}' already exists: {canonical_name}")
            
            # Cache the result
            self.entity_cache[entity_mention] = canonical_name
            return canonical_name
        
        # No exact match - use embedding similarity
        logger.debug(f"No exact match for '{entity_mention}', computing embedding similarity")
        
        # Get embedding for the mention
        mention_embedding = self._get_embedding(entity_mention)
        
        # Get all existing entities with embeddings
        existing_entities = self.neo4j_client.get_all_entities_with_embeddings()
        
        if not existing_entities:
            # No existing entities - create new one
            canonical_name = self._create_new_entity(entity_mention, mention_embedding, document_id)
            self.entity_cache[entity_mention] = canonical_name
            return canonical_name
        
        # Find best matching entity by cosine similarity
        best_match = self._find_best_match(mention_embedding, existing_entities)
        
        if best_match and best_match['similarity'] > self.similarity_threshold:
            # Similar entity found - add as alias
            canonical_name = best_match['canonical_name']
            self.neo4j_client.add_entity_alias(canonical_name, entity_mention, document_id)
            
            logger.info(
                f"Entity '{entity_mention}' resolved to existing entity '{canonical_name}' "
                f"(similarity: {best_match['similarity']:.3f})"
            )
            
            # Cache the result
            self.entity_cache[entity_mention] = canonical_name
            return canonical_name
        else:
            # No similar entity - create new one
            similarity_score = best_match['similarity'] if best_match else 0.0
            logger.info(
                f"Entity '{entity_mention}' is distinct (best similarity: {similarity_score:.3f}), "
                f"creating new entity"
            )
            
            canonical_name = self._create_new_entity(entity_mention, mention_embedding, document_id)
            self.entity_cache[entity_mention] = canonical_name
            return canonical_name
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for text using NIM client.
        
        Args:
            text: Text to embed
        
        Returns:
            List[float]: Embedding vector
        """
        try:
            embedding = self.nim_client.get_embedding(text)
            logger.debug(f"Generated embedding for '{text}' (dim: {len(embedding)})")
            return embedding
        except Exception as e:
            logger.error(f"Failed to get embedding for '{text}': {str(e)}")
            raise
    
    def _create_new_entity(
        self,
        entity_mention: str,
        embedding: List[float],
        document_id: str
    ) -> str:
        """
        Create a new entity in Neo4j.
        
        Args:
            entity_mention: Entity text (becomes canonical name)
            embedding: Embedding vector
            document_id: Document identifier
        
        Returns:
            str: Canonical entity name
        """
        canonical_name = entity_mention
        
        try:
            self.neo4j_client.create_entity(
                canonical_name=canonical_name,
                aliases=[entity_mention],
                document_ids=[document_id],
                embedding=embedding
            )
            
            logger.info(f"Created new entity: {canonical_name} (document: {document_id})")
            return canonical_name
            
        except Exception as e:
            logger.error(f"Failed to create entity '{canonical_name}': {str(e)}")
            raise
    
    def _find_best_match(
        self,
        mention_embedding: List[float],
        existing_entities: List[Dict]
    ) -> Optional[Dict]:
        """
        Find the best matching entity by cosine similarity.
        
        Args:
            mention_embedding: Embedding vector for the mention
            existing_entities: List of existing entities with embeddings
        
        Returns:
            Dict with 'canonical_name' and 'similarity' if found, None otherwise
        """
        if not existing_entities:
            return None
        
        best_match = None
        best_similarity = -1.0
        
        mention_vec = np.array(mention_embedding)
        
        for entity in existing_entities:
            entity_embedding = entity.get('embedding')
            
            if not entity_embedding:
                continue
            
            entity_vec = np.array(entity_embedding)
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(mention_vec, entity_vec)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = {
                    'canonical_name': entity['canonical_name'],
                    'similarity': similarity
                }
        
        if best_match:
            logger.debug(
                f"Best match: {best_match['canonical_name']} "
                f"(similarity: {best_match['similarity']:.3f})"
            )
        
        return best_match
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
        
        Returns:
            float: Cosine similarity (0.0 to 1.0)
        """
        # Normalize vectors
        vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-10)
        vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-10)
        
        # Compute dot product
        similarity = np.dot(vec1_norm, vec2_norm)
        
        # Clamp to [0, 1] range (handle floating point errors)
        return float(np.clip(similarity, 0.0, 1.0))
    
    def clear_cache(self):
        """
        Clear the in-memory entity cache.
        Should be called between document processing sessions.
        """
        self.entity_cache.clear()
        logger.debug("Entity cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get statistics about the entity cache.
        
        Returns:
            Dict with cache statistics
        """
        return {
            'cached_entities': len(self.entity_cache),
            'unique_mentions': len(set(self.entity_cache.values()))
        }
