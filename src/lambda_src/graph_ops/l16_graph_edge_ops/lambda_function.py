import json
import os
import boto3
import pickle
import networkx as nx

# Boto3 clients
s3_client = boto3.client("s3")

# Environment variables
KG_BUCKET = os.environ["KG_BUCKET"]

def lambda_handler(event, context):
    """
    Add Karaka edges to NetworkX graph
    Creates simple subject-verb-object relationships
    """
    
    try:
        text = event['text']
        sentence_hash = event['hash']
        job_id = event['job_id']
        
        print(f"Building graph edges for {sentence_hash}")
        
        # Load existing graph with nodes
        graph_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'graphs/{sentence_hash}_nodes.gpickle'
        )
        G = pickle.loads(graph_obj['Body'].read())
        
        # Load events with Karaka relationships
        events_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/events.json'
        )
        events_data = json.loads(events_obj['Body'].read())
        
        # Add edges from Karaka relationships
        for event in events_data:
            verb = event.get('verb', '')
            karakas = event.get('karakas', [])
            
            # Find Agent and Object for primary edge
            agent = None
            obj = None
            
            for karak in karakas:
                role = karak.get('role', '')
                entity = karak.get('entity', '')
                
                if role == 'Agent':
                    agent = entity
                elif role == 'Object':
                    obj = entity
            
            # Create primary edge: Agent -> Object with verb
            if agent and obj:
                if not G.has_node(agent):
                    G.add_node(agent, node_type='entity', sentence_hash=sentence_hash)
                if not G.has_node(obj):
                    G.add_node(obj, node_type='entity', sentence_hash=sentence_hash)
                
                G.add_edge(agent, obj,
                          edge_type='karaka',
                          relation=verb,
                          karaka_role='Agent->Object',
                          sentence=text,
                          sentence_hash=sentence_hash)
            
            # Add additional Karaka edges
            for karak in karakas:
                role = karak.get('role', '')
                entity = karak.get('entity', '')
                
                if role in ['Instrument', 'Recipient', 'Source', 'Location']:
                    # Connect to Agent if exists, otherwise to Object
                    source_node = agent if agent else obj
                    if source_node and entity:
                        if not G.has_node(entity):
                            G.add_node(entity, node_type='entity', sentence_hash=sentence_hash)
                        
                        G.add_edge(source_node, entity,
                                  edge_type='karaka',
                                  relation=verb,
                                  karaka_role=role,
                                  sentence=text,
                                  sentence_hash=sentence_hash)
        
        # Serialize complete graph
        graph_bytes = pickle.dumps(G)
        
        # Save to S3
        s3_client.put_object(
            Bucket=KG_BUCKET,
            Key=f'graphs/{sentence_hash}.gpickle',
            Body=graph_bytes,
            ContentType='application/octet-stream'
        )
        
        print(f"Created graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        
        # Update sentence status in DynamoDB
        dynamodb = boto3.client("dynamodb")
        dynamodb.update_item(
            TableName=os.environ.get('SENTENCES_TABLE', 'Sentences'),
            Key={'sentence_hash': {'S': sentence_hash}},
            UpdateExpression='SET kg_status = :status',
            ExpressionAttributeValues={':status': {'S': 'kg_done'}}
        )
        
        # Return original event data
        return event
        
    except Exception as e:
        print(f"Error building graph edges: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}

def parse_json_from_content(content):
    """Extract JSON from LLM response content"""
    import re
    try:
        # Remove code blocks
        content = re.sub(r'```(?:json)?', '', content)
        # Find JSON object or array
        start = content.find('[') if '[' in content else content.find('{')
        end = content.rfind(']') if ']' in content else content.rfind('}')
        if start != -1 and end != -1:
            json_str = content[start:end+1]
            return json.loads(json_str)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
    return None
