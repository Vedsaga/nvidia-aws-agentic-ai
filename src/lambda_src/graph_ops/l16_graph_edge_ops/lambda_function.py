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
    Add edges to NetworkX graph from KG extraction results
    Creates edges for Karaka links, relations, and attributes
    """
    
    try:
        sentence_hash = event['hash']
        job_id = event['job_id']
        
        print(f"Building graph edges for {sentence_hash}")
        
        # Load existing graph with nodes
        graph_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'graphs/{sentence_hash}_nodes.gpickle'
        )
        G = pickle.loads(graph_obj['Body'].read())
        
        # Load events for Karaka links
        events_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/events.json'
        )
        events_data = json.loads(events_obj['Body'].read())
        
        # Load relations
        relations_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/relations.json'
        )
        relations_data = json.loads(relations_obj['Body'].read())
        
        # Load attributes
        attributes_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/attributes.json'
        )
        attributes_data = json.loads(attributes_obj['Body'].read())
        
        # Add Karaka edges from events
        if 'choices' in events_data and len(events_data['choices']) > 0:
            content = events_data['choices'][0]['message']['content']
            events_json = parse_json_from_content(content)
            if events_json and 'event_instances' in events_json:
                for event in events_json['event_instances']:
                    event_id = event['instance_id']
                    if 'kāraka_links' in event or 'karaka_links' in event:
                        links = event.get('kāraka_links') or event.get('karaka_links', [])
                        for link in links:
                            entity = link['entity']
                            role = link['role']
                            # Add edge from event to entity with Karaka role
                            if G.has_node(event_id) and G.has_node(entity):
                                G.add_edge(event_id, entity,
                                          edge_type='karaka',
                                          role=role,
                                          reasoning=link.get('reasoning', ''))
        
        # Add relation edges
        if 'choices' in relations_data and len(relations_data['choices']) > 0:
            content = relations_data['choices'][0]['message']['content']
            relations_json = parse_json_from_content(content)
            if relations_json and 'relations' in relations_json:
                for relation in relations_json['relations']:
                    source = relation['source_node']
                    target = relation['target_node']
                    if G.has_node(source) and G.has_node(target):
                        G.add_edge(source, target,
                                  edge_type='relation',
                                  relation_type=relation['relation_type'],
                                  preposition=relation.get('preposition'),
                                  reasoning=relation.get('reasoning', ''))
        
        # Add attribute edges
        if 'choices' in attributes_data and len(attributes_data['choices']) > 0:
            content = attributes_data['choices'][0]['message']['content']
            attributes_json = parse_json_from_content(content)
            if attributes_json and 'attributes' in attributes_json:
                for attr in attributes_json['attributes']:
                    target = attr['target_node']
                    # Create attribute node
                    attr_node_id = f"{target}_attr_{attr['value']}"
                    G.add_node(attr_node_id,
                              node_type='attribute',
                              value=attr['value'],
                              attribute_type=attr['attribute_type'])
                    # Add edge from target to attribute
                    if G.has_node(target):
                        G.add_edge(target, attr_node_id,
                                  edge_type='attribute',
                                  reasoning=attr.get('reasoning', ''))
        
        # Serialize complete graph
        graph_bytes = pickle.dumps(G)
        
        # Save to S3 (overwrite with complete graph)
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
        
        return {
            'status': 'success',
            'nodes_count': G.number_of_nodes(),
            'edges_count': G.number_of_edges()
        }
        
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
