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
PARSED_TABLE = os.environ.get('LLM_CALL_PARSED_TABLE')
KG_BUCKET = os.environ['KG_BUCKET']
GENERATE_ENDPOINT = os.environ.get('GENERATE_ENDPOINT', '')
NVIDIA_API_KEY = os.environ.get('NVIDIA_MODEL_GENERATE', '')

# Determine if using local EKS or NVIDIA cloud
USE_NVIDIA_CLOUD = not GENERATE_ENDPOINT or GENERATE_ENDPOINT == 'https://integrate.api.nvidia.com'
if USE_NVIDIA_CLOUD:
    GENERATE_ENDPOINT = 'https://integrate.api.nvidia.com'
    if not NVIDIA_API_KEY:
        raise ValueError("NVIDIA_MODEL_GENERATE environment variable required for NVIDIA cloud endpoint")

def lambda_handler(event, context):
    """
    LLM Gateway - handles all LLM calls with logging
    Input: {
        'job_id': str,
        'sentence_hash': str,
        'stage': str,
        'prompt_name': str,
        'inputs': dict,
        'temperature': float (optional, default 0.6),
        'attempt_number': int (optional),
        'generation_index': int (optional)
    }
    """
    
    try:
        # Parse input
        job_id = event['job_id']
        sentence_hash = event['sentence_hash']
        stage = event['stage']
        prompt_name = event['prompt_name']
        inputs_dict = event['inputs']
        temperature = event.get('temperature', 0.6)
        attempt_number = event.get('attempt_number', 1)
        generation_index = event.get('generation_index', 1)

        # Generate call ID and start timing
        call_id = str(uuid.uuid4())
        start_time = time.time()
        timestamp_ms = str(int(start_time * 1000))
        
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
        
        # Format prompt with inputs using safe replacement
        formatted_prompt = prompt_template
        for key, value in inputs_dict.items():
            placeholder = '{' + key + '}'
            formatted_prompt = formatted_prompt.replace(placeholder, str(value))
        
        # Prepare request payload
        request_payload = {
            'model': 'nvidia/llama-3.1-nemotron-nano-8b-v1',
            'messages': [{'role': 'user', 'content': formatted_prompt}],
            'max_tokens': 12000,
            'temperature': temperature
        }
        
        # Log request with enhanced metadata
        dynamodb.put_item(
            TableName=LOG_TABLE,
            Item={
                'call_id': {'S': call_id},
                'timestamp': {'N': timestamp_ms},
                'job_id': {'S': job_id},
                'sentence_hash': {'S': sentence_hash},
                'pipeline_stage': {'S': stage},
                'stage': {'S': stage},
                'prompt_template': {'S': prompt_name},
                'temperature': {'N': str(temperature)},
                'attempt_number': {'N': str(attempt_number)},
                'generation_index': {'N': str(generation_index)},
                'raw_request': {'S': json.dumps(request_payload)},
                'status': {'S': 'pending'}
            }
        )
        
        # Make HTTP call using OpenAI-compatible format
        headers = {'Content-Type': 'application/json'}
        if USE_NVIDIA_CLOUD:
            headers['Authorization'] = f'Bearer {NVIDIA_API_KEY}'
        
        response = requests.post(
            f"{GENERATE_ENDPOINT}/v1/chat/completions",
            json=request_payload,
            headers=headers,
            timeout=300
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        latency_str = str(latency_ms)
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Extract content from response
            raw_response = ""
            extracted_json = ""
            extracted_reasoning = ""
            
            try:
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    raw_response = response_data['choices'][0].get('message', {}).get('content', '')
                    
                    # Try to parse JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                    if json_match:
                        extracted_json = json_match.group(0)
                        # Reasoning is text before JSON
                        json_start = raw_response.find('{')
                        if json_start > 0:
                            extracted_reasoning = raw_response[:json_start].strip()
            except Exception as e:
                print(f"Error extracting JSON/reasoning: {e}")
            
            # Log successful response with enhanced fields
            dynamodb.update_item(
                TableName=LOG_TABLE,
                Key={
                    'call_id': {'S': call_id},
                    'timestamp': {'N': timestamp_ms}
                },
                UpdateExpression='SET #status = :status, response_json = :resp, latency_ms = :lat, raw_response = :raw, extracted_json = :ejson, extracted_reasoning = :reas',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': {'S': 'success'},
                    ':resp': {'S': json.dumps(response_data)},
                    ':lat': {'N': latency_str},
                    ':raw': {'S': raw_response},
                    ':ejson': {'S': extracted_json},
                    ':reas': {'S': extracted_reasoning}
                }
            )

            if PARSED_TABLE:
                parsed_item = {
                    'call_id': {'S': call_id},
                    'timestamp': {'N': timestamp_ms},
                    'sentence_hash': {'S': sentence_hash},
                    'pipeline_stage': {'S': stage},
                    'attempt_number': {'N': str(attempt_number)},
                    'generation_index': {'N': str(generation_index)}
                }
                if job_id:
                    parsed_item['job_id'] = {'S': job_id}
                if extracted_json:
                    parsed_item['extracted_json'] = {'S': extracted_json}
                if extracted_reasoning:
                    parsed_item['extracted_reasoning'] = {'S': extracted_reasoning}
                try:
                    dynamodb.put_item(TableName=PARSED_TABLE, Item=parsed_item)
                except Exception as parse_err:
                    print(f"Warning: failed to store parsed output for {call_id}: {parse_err}")
            
            return response_data
        else:
            # Log error response
            dynamodb.update_item(
                TableName=LOG_TABLE,
                Key={
                    'call_id': {'S': call_id},
                    'timestamp': {'N': timestamp_ms}
                },
                UpdateExpression='SET #status = :status, error_msg = :err, latency_ms = :lat',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': {'S': 'error'},
                    ':err': {'S': f"HTTP {response.status_code}: {response.text}"},
                    ':lat': {'N': latency_str}
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
                        'timestamp': {'N': timestamp_ms}
                    },
                    UpdateExpression='SET #status = :status, error_msg = :err',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': {'S': 'error'},
                        ':err': {'S': str(e)}
                    }
                )
            except Exception:
                pass
        raise
