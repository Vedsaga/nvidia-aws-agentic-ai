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
    Extract kriya (verb) from sentence using LLM
    Input: {'text': ..., 'hash': ..., 'job_id': ...}
    """
    
    try:
        text = event['text']
        sentence_hash = event['hash']
        job_id = event['job_id']
        
        payload = {
            'job_id': job_id,
            'sentence_hash': sentence_hash,
            'stage': 'D2a_Kriya',
            'prompt_name': 'kriya_concept_prompt.txt',
            'inputs': {'SENTENCE_HERE': text}
        }
        
        response = lambda_client.invoke(
            FunctionName=LLM_LAMBDA,
            Payload=json.dumps(payload)
        )
        
        llm_output = json.loads(response['Payload'].read())
        
        s3_client.put_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/kriya.json',
            Body=json.dumps(llm_output),
            ContentType='application/json'
        )
        
        # Return original event data for next step
        return event
        
    except Exception as e:
        print(f"Error extracting kriya: {str(e)}")
        return {'status': 'error', 'error': str(e)}
