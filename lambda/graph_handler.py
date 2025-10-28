"""Lambda handler for graph visualization data."""

import json
from src.config import Config
from src.graph.neo4j_client import Neo4jClient


config = Config()
neo4j_client = Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password)


def lambda_handler(event, context):
    """
    Retrieve graph visualization data.
    
    Optional query parameters:
    - document_filter: Filter by document_id
    - limit: Max nodes to return (default 100)
    """
    try:
        # Parse query parameters
        params = event.get('queryStringParameters', {}) or {}
        document_filter = params.get('document_filter')
        limit = int(params.get('limit', 100))
        
        # Get graph data
        graph_data = neo4j_client.get_graph_for_visualization(
            document_filter=document_filter,
            limit=limit
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(graph_data)
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": str(e)
            })
        }
