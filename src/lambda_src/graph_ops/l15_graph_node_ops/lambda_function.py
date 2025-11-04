import json
import os
import boto3
import pickle
import networkx as nx

# Boto3 clients
s3_client = boto3.client("s3")
dynamodb = boto3.client("dynamodb")

# Environment variables
KG_BUCKET = os.environ["KG_BUCKET"]
SENTENCES_TABLE = os.environ.get("SENTENCES_TABLE", "Sentences")

def lambda_handler(event, context):
    """
    Build NetworkX graph nodes from entities
    Simple node creation for Karaka KG
    """
    
    try:
        sentence_hash = event['hash']
        job_id = event['job_id']
        
        print(f"Building graph nodes for {sentence_hash}")
        
        # Load entities from L9
        entities_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/entities.json'
        )
        entities_data = json.loads(entities_obj['Body'].read())
        
        # Create directed graph
        G = nx.DiGraph()
        
        # Parse sentence metadata for document references
        document_ids = []
        try:
            sentence_item = dynamodb.get_item(
                TableName=SENTENCES_TABLE,
                Key={'sentence_hash': {'S': sentence_hash}}
            ).get('Item', {})
            document_ids = sentence_item.get('document_ids', {}).get('SS', [])
            if not document_ids:
                legacy_docs = sentence_item.get('documents', {}).get('SS', [])
                document_ids = legacy_docs or []
        except Exception as meta_err:
            print(f"Warning: unable to load sentence metadata: {meta_err}")

        # Extract entities from stored JSON structure
        entities = entities_data.get('entities', []) if isinstance(entities_data, dict) else []
        
        # Add entity nodes
        for entity in entities:
            if isinstance(entity, dict):
                node_id = entity.get('text')
                entity_type = entity.get('type', '')
                entity_subtype = entity.get('subtype', '')
            else:
                node_id = str(entity)
                entity_type = ''
                entity_subtype = ''

            if not node_id:
                continue

            G.add_node(
                node_id,
                node_type='entity',
                entity_type=entity_type,
                entity_subtype=entity_subtype,
                sentence_hash=sentence_hash,
                job_id=job_id,
                document_ids=list(document_ids)
            )
        
        # Serialize graph
        graph_bytes = pickle.dumps(G)
        
        # Save to S3
        s3_client.put_object(
            Bucket=KG_BUCKET,
            Key=f'graphs/{sentence_hash}_nodes.gpickle',
            Body=graph_bytes,
            ContentType='application/octet-stream'
        )
        
        print(f"Created graph with {G.number_of_nodes()} nodes")
        
        # Return original event data for next step
        return event
        
    except Exception as e:
        print(f"Error building graph nodes: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}
