import json
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.graph.neo4j_client import Neo4jClient
from src.config import Config

# Initialize clients outside handler for reuse
config = Config()
neo4j_client = None

def get_neo4j_client():
    """Lazy initialization of Neo4j client"""
    global neo4j_client
    if neo4j_client is None:
        neo4j_client = Neo4jClient(
            uri=config.neo4j_uri,
            username=config.neo4j_username,
            password=config.neo4j_password
        )
    return neo4j_client

def lambda_handler(event, context):
    """
    Lambda handler for retrieving graph visualization data
    GET /graph
    """
    try:
        # Get Neo4j client
        client = get_neo4j_client()
        
        # Parse optional query parameters for filtering
        query_params = event.get('queryStringParameters') or {}
        document_filter = query_params.get('document_id')
        limit = int(query_params.get('limit', 100))
        
        # Get graph data from Neo4j
        graph_data = client.get_graph_for_visualization(
            document_filter=document_filter,
            limit=limit
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(graph_data)
        }
        
    except Exception as e:
        print(f"Error retrieving graph data: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }
