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
    Extract attributes from sentence using LLM
    """
    
    try:
        text = event['text']
        sentence_hash = event['hash']
        job_id = event['job_id']
        
        payload = {
            'job_id': job_id,
            'sentence_hash': sentence_hash,
            'stage': 'D6_Attributes',
            'prompt_name': 'attribute_prompt.txt',
            'inputs': {'SENTENCE_HERE': text}
        }
        
        response = lambda_client.invoke(
            FunctionName=LLM_LAMBDA,
            Payload=json.dumps(payload)
        )
        
        llm_output = json.loads(response['Payload'].read())
        
        s3_client.put_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/attributes.json',
            Body=json.dumps(llm_output),
            ContentType='application/json'
        )
        
        return {'status': 'success'}
        
    except Exception as e:
        print(f"Error extracting attributes: {str(e)}")
        return {'status': 'error', 'error': str(e)}
