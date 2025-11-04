"""
L24: Score Extractions
Scores 3 JSON outputs using LLM with scorer prompt
"""
import json
import os
import boto3
import sys

# Add shared utilities to path
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from gssr_utils import parse_scorer_response

lambda_client = boto3.client('lambda')

LLM_CALL_LAMBDA_NAME = os.environ.get('LLM_CALL_LAMBDA_NAME')
KG_BUCKET = os.environ.get('KG_BUCKET')

s3_client = boto3.client('s3')


def load_prompt(prompt_name):
    """Load prompt template from S3"""
    try:
        response = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'prompts/{prompt_name}'
        )
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"Error loading prompt {prompt_name}: {e}")
        return None


def lambda_handler(event, context):
    """
    Input:
    {
        "sentence": "...",
        "json1": {...},
        "json2": {...},
        "json3": {...},
        "stage": "D1_Entities|D2a_Kriya|D2b_Karakas",
        "temperature": 0.0,
        "job_id": "...",
        "sentence_hash": "..."
    }
    
    Output:
    {
        "scores": [score1, score2, score3],
        "raw_response": "..."
    }
    """
    try:
        sentence = event['sentence']
        json1 = event['json1']
        json2 = event['json2']
        json3 = event['json3']
        stage = event.get('stage', 'Unknown')
        temperature = event.get('temperature', 0.0)
        job_id = event.get('job_id', 'unknown')
        sentence_hash = event.get('sentence_hash', 'unknown')
        
        # Load scorer prompt
        prompt_template = load_prompt('scorer.txt')
        if not prompt_template:
            return {
                'statusCode': 500,
                'scores': [0, 0, 0],
                'error': 'Failed to load scorer prompt'
            }
        
        # Format prompt with sentence and 3 JSONs
        formatted_prompt = prompt_template.replace('{{SENTENCE_HERE}}', sentence)
        formatted_prompt = formatted_prompt.replace('{{JSON_1}}', json.dumps(json1, indent=2))
        formatted_prompt = formatted_prompt.replace('{{JSON_2}}', json.dumps(json2, indent=2))
        formatted_prompt = formatted_prompt.replace('{{JSON_3}}', json.dumps(json3, indent=2))
        
        # Call LLM
        llm_payload = {
            'job_id': job_id,
            'sentence_hash': sentence_hash,
            'stage': f'Scorer_{stage}',
            'prompt_name': 'scorer.txt',
            'temperature': temperature,
            'inputs': {
                'formatted_prompt': formatted_prompt
            }
        }
        
        response = lambda_client.invoke(
            FunctionName=LLM_CALL_LAMBDA_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(llm_payload)
        )
        
        llm_output = json.loads(response['Payload'].read())
        
        # Parse scores from response
        raw_response = llm_output.get('response', '')
        scores = parse_scorer_response(raw_response)
        
        return {
            'statusCode': 200,
            'scores': scores,
            'raw_response': raw_response
        }
        
    except Exception as e:
        print(f"Error in scorer: {e}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'scores': [0, 0, 0],
            'error': str(e)
        }
