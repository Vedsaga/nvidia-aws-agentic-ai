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
    Extract entities from sentence using LLM
    Input: SFN Map item {'text': ..., 'hash': ..., 'job_id': ...}
    """
    
    try:
        # Get data from SFN Map item
        text = event['text']
        sentence_hash = event['hash']
        job_id = event['job_id']
        
        # Prepare LLM call payload
        payload = {
            'job_id': job_id,
            'sentence_hash': sentence_hash,
            'stage': 'D1_Entities',
            'prompt_name': 'entity_prompt.txt',
            'inputs': {'SENTENCE_HERE': text}
        }
        
        # Invoke LLM Lambda
        response = lambda_client.invoke(
            FunctionName=LLM_LAMBDA,
            Payload=json.dumps(payload)
        )
        
        # Parse LLM response
        llm_output = json.loads(response['Payload'].read())
        
        # Save result to S3
        s3_client.put_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/entities.json',
            Body=json.dumps(llm_output),
            ContentType='application/json'
        )
        
        return {'status': 'success'}
        
    except Exception as e:
        print(f"Error extracting entities: {str(e)}")
        return {'status': 'error', 'error': str(e)}
