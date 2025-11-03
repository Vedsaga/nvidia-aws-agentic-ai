import json
import os
import boto3
import requests
import uuid
import time

# Boto3 clients
s3_client = boto3.client("s3")
dynamodb = boto3.client("dynamodb")

# Environment variables
LOG_TABLE = os.environ['LLM_CALL_LOG_TABLE']
KG_BUCKET = os.environ['KG_BUCKET']
GENERATE_ENDPOINT = os.environ.get('GENERATE_ENDPOINT', 'http://a72a7b27168ef4f2f825fe7aae9ce8ed-2069339664.us-east-1.elb.amazonaws.com:80')

def lambda_handler(event, context):
    """
    LLM Gateway - handles all LLM calls with logging
    Input: {
        'job_id': str,
        'sentence_hash': str,
        'stage': str,
        'prompt_name': str,
        'inputs': dict
    }
    """
    
    try:
        # Parse input
        job_id = event['job_id']
        sentence_hash = event['sentence_hash']
        stage = event['stage']
        prompt_name = event['prompt_name']
        inputs_dict = event['inputs']
        
        # Generate call ID and start timing
        call_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Load prompt template from S3
        try:
            prompt_response = s3_client.get_object(
                Bucket=KG_BUCKET,
                Key=f'prompts/{prompt_name}'
            )
            prompt_template = prompt_response['Body'].read().decode('utf-8')
        except Exception as e:
            print(f"Error loading prompt {prompt_name}: {str(e)}")
            raise
        
        # Format prompt with inputs
        formatted_prompt = prompt_template.format(**inputs_dict)
        
        # Log request
        dynamodb.put_item(
            TableName=LOG_TABLE,
            Item={
                'call_id': {'S': call_id},
                'timestamp': {'N': str(int(start_time * 1000))},
                'job_id': {'S': job_id},
                'sentence_hash': {'S': sentence_hash},
                'stage': {'S': stage},
                'prompt_template': {'S': prompt_name},
                'status': {'S': 'pending'}
            }
        )
        
        # Make HTTP call to LLM endpoint using OpenAI-compatible format
        response = requests.post(
            f"{GENERATE_ENDPOINT}/v1/chat/completions",
            json={
                'model': 'nvidia/llama-3.1-nemotron-nano-8b-v1',
                'messages': [{'role': 'user', 'content': formatted_prompt}],
                'max_tokens': 2000,
                'temperature': 0.1
            },
            timeout=300
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Log successful response
            dynamodb.update_item(
                TableName=LOG_TABLE,
                Key={
                    'call_id': {'S': call_id},
                    'timestamp': {'N': str(int(start_time * 1000))}
                },
                UpdateExpression='SET #status = :status, response_json = :resp, latency_ms = :lat',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': {'S': 'success'},
                    ':resp': {'S': json.dumps(response_data)},
                    ':lat': {'N': str(latency_ms)}
                }
            )
            
            return response_data
        else:
            # Log error response
            dynamodb.update_item(
                TableName=LOG_TABLE,
                Key={
                    'call_id': {'S': call_id},
                    'timestamp': {'N': str(int(start_time * 1000))}
                },
                UpdateExpression='SET #status = :status, error_msg = :err, latency_ms = :lat',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': {'S': 'error'},
                    ':err': {'S': f"HTTP {response.status_code}: {response.text}"},
                    ':lat': {'N': str(latency_ms)}
                }
            )
            raise Exception(f"LLM call failed: {response.status_code} {response.text}")
            
    except Exception as e:
        print(f"Error in LLM call: {str(e)}")
        # Log error if we have the call_id
        if 'call_id' in locals():
            try:
                dynamodb.update_item(
                    TableName=LOG_TABLE,
                    Key={
                        'call_id': {'S': call_id},
                        'timestamp': {'N': str(int(start_time * 1000))}
                    },
                    UpdateExpression='SET #status = :status, error_msg = :err',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': {'S': 'error'},
                        ':err': {'S': str(e)}
                    }
                )
            except:
                pass
        raise
