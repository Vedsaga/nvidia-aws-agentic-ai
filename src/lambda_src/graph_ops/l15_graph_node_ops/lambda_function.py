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
    Build NetworkX graph nodes from KG extraction results
    Creates nodes for entities and event instances
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
        
        # Load events from L11
        events_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/events.json'
        )
        events_data = json.loads(events_obj['Body'].read())
        
        # Create directed graph
        G = nx.DiGraph()
        
        # Add entity nodes
        if 'choices' in entities_data and len(entities_data['choices']) > 0:
            content = entities_data['choices'][0]['message']['content']
            # Parse JSON from content
            entities_json = parse_json_from_content(content)
            if entities_json and 'entities' in entities_json:
                for entity in entities_json['entities']:
                    node_id = entity['text']
                    G.add_node(node_id, 
                              node_type='entity',
                              entity_type=entity['type'],
                              sentence_hash=sentence_hash,
                              job_id=job_id)
        
        # Add event instance nodes
        if 'choices' in events_data and len(events_data['choices']) > 0:
            content = events_data['choices'][0]['message']['content']
            events_json = parse_json_from_content(content)
            if events_json and 'event_instances' in events_json:
                for event in events_json['event_instances']:
                    node_id = event['instance_id']
                    G.add_node(node_id,
                              node_type='event_instance',
                              kriya_concept=event.get('kriya_concept'),
                              surface_text=event.get('surface_text'),
                              prayoga=event.get('prayoga'),
                              sentence_hash=sentence_hash,
                              job_id=job_id)
        
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
        
        return {
            'status': 'success',
            'nodes_count': G.number_of_nodes()
        }
        
    except Exception as e:
        print(f"Error building graph nodes: {str(e)}")
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
