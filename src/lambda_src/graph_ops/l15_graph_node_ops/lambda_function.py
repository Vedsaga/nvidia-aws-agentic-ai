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
    Build NetworkX graph nodes from entities
    Simple node creation for Karaka KG
    """
    
    try:
        text = event['text']
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
        
        # Parse entities from LLM response
        entities = parse_entities(entities_data)
        
        # Add entity nodes
        for entity in entities:
            G.add_node(entity, 
                      node_type='entity',
                      sentence_hash=sentence_hash,
                      sentence_text=text,
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
        
        # Return original event data for next step
        return event
        
    except Exception as e:
        print(f"Error building graph nodes: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}

def parse_entities(llm_response):
    """Extract entity list from LLM response"""
    entities = []
    try:
        if 'choices' in llm_response and len(llm_response['choices']) > 0:
            content = llm_response['choices'][0]['message']['content']
            # Try to parse JSON
            data = parse_json_from_content(content)
            if data:
                if 'entities' in data:
                    entities = [e['text'] if isinstance(e, dict) else e for e in data['entities']]
                elif isinstance(data, list):
                    entities = [e['text'] if isinstance(e, dict) else e for e in data]
    except Exception as e:
        print(f"Error parsing entities: {e}")
    return entities

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
