"""Simple in-memory cache for embeddings to reduce SageMaker calls."""

import hashlib
import time
from typing import Optional, List


class EmbeddingCache:
    """LRU cache for embedding vectors with TTL."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}  # {hash: (embedding, timestamp)}
        self.access_order = []  # LRU tracking
    
    def _hash_text(self, text: str) -> str:
        """Generate hash key for text."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding if exists and not expired."""
        key = self._hash_text(text)
        
        if key not in self.cache:
            return None
        
        embedding, timestamp = self.cache[key]
        
        # Check TTL
        if time.time() - timestamp > self.ttl_seconds:
            del self.cache[key]
            self.access_order.remove(key)
            return None
        
        # Update LRU
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
        
        return embedding
    
    def put(self, text: str, embedding: List[float]):
        """Store embedding in cache."""
        key = self._hash_text(text)
        
        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        
        self.cache[key] = (embedding, time.time())
        
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
    
    def clear(self):
        """Clear all cached embeddings."""
        self.cache.clear()
        self.access_order.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)


# Global cache instance
embedding_cache = EmbeddingCache(max_size=1000, ttl_seconds=3600)
