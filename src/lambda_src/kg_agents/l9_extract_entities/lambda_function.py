"""
L9: Extract Entities with GSSR
Implements full GSSR flow for D1 entity extraction
"""
import json
import os
import boto3
import sys

# Add shared utilities to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from json_schemas import D1_SCHEMA, validate_schema
from fidelity_validator import validate_d1_fidelity
from gssr_utils import check_consensus, parse_llm_json_response

# Boto3 clients
s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")
dynamodb = boto3.client("dynamodb")

# Environment variables
LLM_LAMBDA = os.environ["LLM_CALL_LAMBDA_NAME"]
SCORER_LAMBDA = os.environ["SCORER_LAMBDA_NAME"]
KG_BUCKET = os.environ["KG_BUCKET"]
SENTENCES_TABLE = os.environ.get("SENTENCES_TABLE", "Sentences")

MAX_ATTEMPTS = 5
STAGE = "D1_Entities"


def get_sentence_attempts(sentence_hash):
    """Get current d1_attempts from Sentences table"""
    try:
        response = dynamodb.get_item(
            TableName=SENTENCES_TABLE,
            Key={'sentence_hash': {'S': sentence_hash}}
        )
        if 'Item' in response:
            return int(response['Item'].get('d1_attempts', {'N': '0'})['N'])
        return 0
    except Exception as e:
        print(f"Error getting attempts: {e}")
        return 0


def update_sentence_result(sentence_hash, job_id, best_score, attempts, needs_review, failure_reason=None):
    """Update Sentences table with GSSR results"""
    try:
        update_expr = "SET d1_attempts = :att, best_score = :score, needs_review = :review, #st = :status"
        expr_values = {
            ':att': {'N': str(attempts)},
            ':score': {'N': str(best_score)},
            ':review': {'BOOL': needs_review},
            ':status': {'S': 'KG_IN_PROGRESS'}
        }
        expr_names = {'#st': 'status'}
        
        if failure_reason:
            update_expr += ", failure_reason = :reason"
            expr_values[':reason'] = {'S': failure_reason}
        
        dynamodb.update_item(
            TableName=SENTENCES_TABLE,
            Key={'sentence_hash': {'S': sentence_hash}},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names
        )
    except Exception as e:
        print(f"Error updating sentence: {e}")


def call_llm(sentence, sentence_hash, job_id, temperature, attempt, generation):
    """Call LLM with specified temperature"""
    payload = {
        'job_id': job_id,
        'sentence_hash': sentence_hash,
        'stage': STAGE,
        'prompt_name': 'D1_entity_extraction.txt',
        'temperature': temperature,
        'attempt_number': attempt,
        'generation_index': generation,
        'inputs': {'SENTENCE_HERE': sentence}
    }
    
    response = lambda_client.invoke(
        FunctionName=LLM_LAMBDA,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    return json.loads(response['Payload'].read())


def call_scorer(sentence, json1, json2, json3, sentence_hash, job_id, temperature):
    """Call scorer Lambda"""
    payload = {
        'sentence': sentence,
        'json1': json1,
        'json2': json2,
        'json3': json3,
        'stage': STAGE,
        'temperature': temperature,
        'sentence_hash': sentence_hash,
        'job_id': job_id
    }
    
    response = lambda_client.invoke(
        FunctionName=SCORER_LAMBDA,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    return json.loads(response['Payload'].read())


def save_to_s3(sentence_hash, data):
    """Save best JSON to S3"""
    s3_client.put_object(
        Bucket=KG_BUCKET,
        Key=f'temp_kg/{sentence_hash}/entities.json',
        Body=json.dumps(data),
        ContentType='application/json'
    )


def lambda_handler(event, context):
    """
    Extract entities with GSSR
    Input: {'text': ..., 'hash': ..., 'job_id': ...}
    """
    
    try:
        text = event['text']
        sentence_hash = event['hash']
        job_id = event['job_id']
        
        # Get current attempts
        current_attempts = get_sentence_attempts(sentence_hash)
        
        if current_attempts >= MAX_ATTEMPTS:
            print(f"Max attempts reached for {sentence_hash}")
            return event
        
        # Phase 1: Generate 3 JSONs (temp=0.6, sequential)
        print(f"Phase 1: Generating 3 JSONs for {sentence_hash}")
        raw_jsons = []
        for i in range(3):
            llm_response = call_llm(text, sentence_hash, job_id, 0.6, current_attempts + 1, i + 1)
            
            # Extract content from LLM response
            content = ""
            if 'choices' in llm_response and len(llm_response['choices']) > 0:
                content = llm_response['choices'][0].get('message', {}).get('content', '')
            
            # Parse JSON from response
            parsed = parse_llm_json_response(content)
            if parsed:
                raw_jsons.append(parsed)
            else:
                print(f"Failed to parse JSON from generation {i+1}")
                raw_jsons.append({'entities': []})
        
        # Phase 2: Fidelity check each JSON
        print(f"Phase 2: Fidelity check")
        valid_jsons = []
        for i, json_data in enumerate(raw_jsons):
            # Schema validation
            is_valid_schema, schema_error = validate_schema(json_data, D1_SCHEMA)
            if not is_valid_schema:
                print(f"JSON {i+1} failed schema validation: {schema_error}")
                valid_jsons.append({'entities': []})
                continue
            
            # Fidelity validation
            is_valid_fidelity, fidelity_errors = validate_d1_fidelity(json_data, text)
            if not is_valid_fidelity:
                print(f"JSON {i+1} failed fidelity check: {fidelity_errors}")
                # For now, use as-is (correction prompt can be added later)
            
            valid_jsons.append(json_data)
        
        # Phase 2a: Consensus check
        print(f"Phase 2a: Consensus check")
        if check_consensus(valid_jsons[0], valid_jsons[1], valid_jsons[2]):
            print("Consensus achieved! Score=100")
            best_json = valid_jsons[0]
            best_score = 100
            update_sentence_result(sentence_hash, job_id, best_score, current_attempts + 1, False)
            save_to_s3(sentence_hash, best_json)
            return event
        
        # Phase 3: Scoring Pass 1 (temp=0.0)
        print(f"Phase 3: Scoring Pass 1")
        scorer_result1 = call_scorer(text, valid_jsons[0], valid_jsons[1], valid_jsons[2], 
                                     sentence_hash, job_id, 0.0)
        scores_pass1 = scorer_result1.get('scores', [0, 0, 0])
        print(f"Pass 1 scores: {scores_pass1}")
        
        if all(s < 70 for s in scores_pass1):
            print("All scores < 70 in Pass 1, retrying...")
            update_sentence_result(sentence_hash, job_id, max(scores_pass1), current_attempts + 1, 
                                 True, "Low scores in Pass 1")
            return {'status': 'retry', 'stage': STAGE, **event}
        
        # Phase 4: Scoring Pass 2 (temp=0.3)
        print(f"Phase 4: Scoring Pass 2")
        scorer_result2 = call_scorer(text, valid_jsons[0], valid_jsons[1], valid_jsons[2],
                                     sentence_hash, job_id, 0.3)
        scores_pass2 = scorer_result2.get('scores', [0, 0, 0])
        print(f"Pass 2 scores: {scores_pass2}")
        
        if all(s < 70 for s in scores_pass2):
            if current_attempts + 1 < MAX_ATTEMPTS:
                print("All scores < 70 in Pass 2, retrying...")
                update_sentence_result(sentence_hash, job_id, max(scores_pass2), current_attempts + 1,
                                     True, "Low scores in Pass 2")
                return {'status': 'retry', 'stage': STAGE, **event}
            else:
                print("Max attempts reached, using best available")
        
        # Phase 5: Select best (average of pass1 + pass2)
        print(f"Phase 5: Selecting best")
        combined = [(s1 + s2) / 2 for s1, s2 in zip(scores_pass1, scores_pass2)]
        best_idx = combined.index(max(combined))
        best_json = valid_jsons[best_idx]
        best_score = combined[best_idx]
        
        print(f"Best score: {best_score} (JSON {best_idx + 1})")
        
        needs_review = best_score < 70
        update_sentence_result(sentence_hash, job_id, best_score, current_attempts + 1, needs_review)
        save_to_s3(sentence_hash, best_json)
        
        return event
        
    except Exception as e:
        print(f"Error in entity extraction: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'error': str(e), **event}
