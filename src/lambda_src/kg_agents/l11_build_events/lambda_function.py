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
    Build events from sentence using LLM
    Requires entities and kriya from previous steps
    """
    
    try:
        text = event['text']
        sentence_hash = event['hash']
        job_id = event['job_id']
        
        # Load entities from L9
        entities_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/entities.json'
        )
        entities_data = json.loads(entities_obj['Body'].read())
        
        # Load kriya from L10
        kriya_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/kriya.json'
        )
        kriya_data = json.loads(kriya_obj['Body'].read())
        
        # Prepare inputs for event prompt
        payload = {
            'job_id': job_id,
            'sentence_hash': sentence_hash,
            'stage': 'D3_Events',
            'prompt_name': 'event_instance_prompt.txt',
            'inputs': {
                'SENTENCE_HERE': text,
                'ENTITY_LIST_JSON': json.dumps(entities_data, indent=2),
                'KRIYA_LIST_JSON': json.dumps(kriya_data, indent=2)
            }
        }
        
        response = lambda_client.invoke(
            FunctionName=LLM_LAMBDA,
            Payload=json.dumps(payload)
        )
        
        llm_output = json.loads(response['Payload'].read())
        
        s3_client.put_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/events.json',
            Body=json.dumps(llm_output),
            ContentType='application/json'
        )
        
        return {'status': 'success'}
        
    except Exception as e:
        print(f"Error building events: {str(e)}")
        return {'status': 'error', 'error': str(e)}
