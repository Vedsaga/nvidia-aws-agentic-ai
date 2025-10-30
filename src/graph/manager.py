"""
Graph Manager for Kāraka RAG System
Handles graph operations and queries
"""
from typing import Dict, Any, List
from .neo4j_client import Neo4jClient

class GraphManager:
    """Manages graph database operations"""
    
    def __init__(self):
        self.client = Neo4jClient()
        self.driver = self.client.driver
    
    def get_graph_data(self, limit: int = 100) -> Dict[str, Any]:
        """Get graph data for visualization"""
        query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT $limit
        """
        
        result = self.client.execute_query(query, {"limit": limit})
        
        nodes = []
        edges = []
        node_ids = set()
        
        for record in result:
            # Add source node
            if record["n"] and record["n"].id not in node_ids:
                nodes.append({
                    "id": record["n"].id,
                    "label": list(record["n"].labels)[0] if record["n"].labels else "Unknown",
                    "properties": dict(record["n"])
                })
                node_ids.add(record["n"].id)
            
            # Add relationship and target node
            if record["r"] and record["m"]:
                if record["m"].id not in node_ids:
                    nodes.append({
                        "id": record["m"].id,
                        "label": list(record["m"].labels)[0] if record["m"].labels else "Unknown",
                        "properties": dict(record["m"])
                    })
                    node_ids.add(record["m"].id)
                
                edges.append({
                    "source": record["n"].id,
                    "target": record["m"].id,
                    "type": record["r"].type,
                    "properties": dict(record["r"])
                })
        
        # Get stats
        stats = self.get_stats()
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": stats
        }
    
    def get_entity_subgraph(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        """Get subgraph for a specific entity"""
        query = """
        MATCH path = (e:Entity {name: $entity_name})-[*1..$depth]-(connected)
        RETURN path
        """
        
        result = self.client.execute_query(query, {
            "entity_name": entity_name,
            "depth": depth
        })
        
        nodes = []
        edges = []
        node_ids = set()
        
        for record in result:
            path = record["path"]
            for node in path.nodes:
                if node.id not in node_ids:
                    nodes.append({
                        "id": node.id,
                        "label": list(node.labels)[0] if node.labels else "Unknown",
                        "properties": dict(node)
                    })
                    node_ids.add(node.id)
            
            for rel in path.relationships:
                edges.append({
                    "source": rel.start_node.id,
                    "target": rel.end_node.id,
                    "type": rel.type,
                    "properties": dict(rel)
                })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def get_stats(self) -> Dict[str, int]:
        """Get graph statistics"""
        stats_query = """
        MATCH (e:Entity) WITH count(e) as entities
        MATCH (a:Action) WITH entities, count(a) as actions
        MATCH ()-[r]->() WHERE type(r) IN ['KARTA', 'KARMA', 'KARANA', 'SAMPRADANA', 'ADHIKARANA', 'APADANA']
        RETURN entities, actions, count(r) as relationships
        """
        
        result = self.client.execute_query(stats_query)
        
        if result:
            record = result[0]
            return {
                "entities": record.get("entities", 0),
                "actions": record.get("actions", 0),
                "relationships": record.get("relationships", 0)
            }
        
        return {"entities": 0, "actions": 0, "relationships": 0}
    
    def clear_graph(self):
        """Clear all data from the graph"""
        query = "MATCH (n) DETACH DELETE n"
        self.client.execute_query(query)
