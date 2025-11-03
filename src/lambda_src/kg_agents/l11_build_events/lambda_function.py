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
    Build Karaka events from sentence
    Combines entities and kriya to form event instances with 6 Karaka roles
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
        
        # Parse entities and verb from LLM responses
        entities = parse_entities(entities_data)
        verb = parse_verb(kriya_data)
        
        # Extract Karaka relationships using LLM
        payload = {
            'job_id': job_id,
            'sentence_hash': sentence_hash,
            'stage': 'D2b_Karakas',
            'prompt_name': 'karak_prompt.txt',
            'inputs': {
                'SENTENCE_HERE': text,
                'ENTITIES': json.dumps(entities),
                'VERB': verb
            }
        }
        
        response = lambda_client.invoke(
            FunctionName=LLM_LAMBDA,
            Payload=json.dumps(payload)
        )
        
        llm_output = json.loads(response['Payload'].read())
        karakas = parse_karakas(llm_output)
        
        # Build Karaka event with 6 roles
        events = [{
            'sentence': text,
            'entities': entities,
            'verb': verb,
            'karakas': karakas
        }]
        
        # Save events
        s3_client.put_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/events.json',
            Body=json.dumps(events),
            ContentType='application/json'
        )
        
        # Return original event data for next step
        return event
        
    except Exception as e:
        print(f"Error building events: {str(e)}")
        return {'status': 'error', 'error': str(e)}

def parse_entities(llm_response):
    """Extract entity list from LLM response"""
    try:
        if 'choices' in llm_response:
            content = llm_response['choices'][0]['message']['content']
            # Try to parse JSON
            import re
            content = re.sub(r'```(?:json)?', '', content)
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                data = json.loads(content[start:end+1])
                return data.get('entities', [])
    except Exception as e:
        print(f"Error parsing entities: {e}")
    return []

def parse_verb(llm_response):
    """Extract verb from LLM response"""
    try:
        if 'choices' in llm_response:
            content = llm_response['choices'][0]['message']['content']
            # Try to parse JSON
            import re
            content = re.sub(r'```(?:json)?', '', content)
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                data = json.loads(content[start:end+1])
                return data.get('verb', '')
    except Exception as e:
        print(f"Error parsing verb: {e}")
    return ''

def parse_karakas(llm_response):
    """Extract karaka relationships from LLM response"""
    try:
        if 'choices' in llm_response:
            content = llm_response['choices'][0]['message']['content']
            # Try to parse JSON
            import re
            content = re.sub(r'```(?:json)?', '', content)
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                data = json.loads(content[start:end+1])
                return data.get('karakas', [])
    except Exception as e:
        print(f"Error parsing karakas: {e}")
    return []
