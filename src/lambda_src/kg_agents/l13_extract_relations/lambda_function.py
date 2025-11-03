import json
import os
import boto3

# Boto3 clients
s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")

# Environment variables
LLM_LAMBDA = os.environ["LLM_CALL_LAMBDA_NAME"]
KG_BUCKET = os.environ["KG_BUCKET"]

def lambda_handler(event, context):
    """
    Extract Karaka relations (edges) from events
    Creates subject-verb-object relationships
    """
    
    try:
        text = event['text']
        sentence_hash = event['hash']
        job_id = event['job_id']
        
        # Load events from L11
        events_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/events.json'
        )
        events_data = json.loads(events_obj['Body'].read())
        
        # Build simple Karaka relations
        relations = []
        for event in events_data:
            entities = event.get('entities', [])
            verb = event.get('verb', '')
            
            # Create relations between entities via verb
            if len(entities) >= 2 and verb:
                relation = {
                    'source': entities[0],
                    'relation': verb,
                    'target': entities[1],
                    'sentence': text
                }
                relations.append(relation)
            elif len(entities) == 1 and verb:
                # Single entity with action
                relation = {
                    'source': entities[0],
                    'relation': verb,
                    'target': None,
                    'sentence': text
                }
                relations.append(relation)
        
        # Save relations
        s3_client.put_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/relations.json',
            Body=json.dumps(relations),
            ContentType='application/json'
        )
        
        # Return original event data for next step
        return event
        
    except Exception as e:
        print(f"Error extracting relations: {str(e)}")
        return {'status': 'error', 'error': str(e)}
