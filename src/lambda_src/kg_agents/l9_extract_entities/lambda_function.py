"""
L9: Extract Entities with GSSR
Implements full GSSR flow for D1 entity extraction
"""
import json
import os
import boto3
import sys

# Import shared utilities from same directory
from json_schemas import D1_SCHEMA, validate_schema
from fidelity_validator import validate_d1_fidelity
from gssr_utils import check_consensus, parse_llm_json_response, extract_reasoning_block

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


def clean_event_payload(event):
    """Return a copy of the event without transient retry flags."""
    cleaned = dict(event)
    cleaned.pop('status', None)
    cleaned.pop('stage', None)
    return cleaned


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


def get_scorer_feedback(sentence_hash):
    """Get previous scorer feedback from Sentences table"""
    try:
        response = dynamodb.get_item(
            TableName=SENTENCES_TABLE,
            Key={'sentence_hash': {'S': sentence_hash}}
        )
        if 'Item' in response and 'scorer_feedback' in response['Item']:
            return response['Item']['scorer_feedback']['S']
        return None
    except Exception as e:
        print(f"Error getting scorer feedback: {e}")
        return None


def update_sentence_result(sentence_hash, job_id, best_score, attempts, needs_review, failure_reason=None):
    """Update Sentences table with GSSR results"""
    # Status enum values
    STATUS_KG_PENDING = 'KG_PENDING'
    STATUS_KG_IN_PROGRESS = 'KG_IN_PROGRESS'
    STATUS_KG_COMPLETE = 'KG_COMPLETE'
    STATUS_KG_FAILED = 'KG_FAILED'
    STATUS_NEEDS_REVIEW = 'NEEDS_REVIEW'
    
    try:
        # Determine status based on results
        # D1 should NOT set KG_COMPLETE - only mark as IN_PROGRESS so D2a/D2b can run
        if needs_review and attempts >= MAX_ATTEMPTS:
            status = STATUS_NEEDS_REVIEW
        else:
            status = STATUS_KG_IN_PROGRESS
            
        set_clauses = [
            "d1_attempts = :att",
            "best_score = :score",
            "needs_review = :review",
            "#st = :status",
            "attempts_count = :att"
        ]
        expr_values = {
            ':att': {'N': str(attempts)},
            ':score': {'N': str(best_score)},
            ':review': {'BOOL': needs_review},
            ':status': {'S': status}
        }
        expr_names = {'#st': 'status'}

        remove_fields = []
        if failure_reason:
            set_clauses.append("failure_reason = :reason")
            expr_values[':reason'] = {'S': failure_reason}
        else:
            remove_fields.append('failure_reason')

        update_expr = "SET " + ", ".join(set_clauses)
        if remove_fields:
            update_expr += " REMOVE " + ", ".join(remove_fields)

        dynamodb.update_item(
            TableName=SENTENCES_TABLE,
            Key={'sentence_hash': {'S': sentence_hash}},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names
        )
    except Exception as e:
        print(f"Error updating sentence: {e}")


def call_llm(sentence, sentence_hash, job_id, temperature, attempt, generation, scorer_feedback=None):
    """Call LLM with specified temperature and optional scorer feedback"""
    sentence_with_feedback = sentence
    if scorer_feedback and attempt > 1:
        sentence_with_feedback = f"{sentence}\n\nNOTE - Previous attempt feedback: {scorer_feedback[:300]}"
    
    payload = {
        'job_id': job_id,
        'sentence_hash': sentence_hash,
        'stage': STAGE,
        'prompt_name': 'D1_entity_extraction.txt',
        'temperature': temperature,
        'attempt_number': attempt,
        'generation_index': generation,
        'inputs': {'SENTENCE_HERE': sentence_with_feedback}
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
        
        # Check if already complete (dedup safety check)
        try:
            response = dynamodb.get_item(
                TableName=SENTENCES_TABLE,
                Key={'sentence_hash': {'S': sentence_hash}}
            )
            if 'Item' in response:
                status = response['Item'].get('status', {}).get('S', '')
                if status == 'KG_COMPLETE':
                    print(f"Sentence {sentence_hash} already complete, skipping")
                    return clean_event_payload(event)
        except:
            pass
        
        # Get current attempts
        current_attempts = get_sentence_attempts(sentence_hash)
        
        if current_attempts >= MAX_ATTEMPTS:
            print(f"Max attempts reached for {sentence_hash}")
            return clean_event_payload(event)
        
        # Get previous scorer feedback if this is a retry
        scorer_feedback = get_scorer_feedback(sentence_hash) if current_attempts > 0 else None
        if scorer_feedback:
            print(f"Using scorer feedback from previous attempt: {scorer_feedback[:100]}...")
        
        # Phase 1: Generate 3 JSONs (temp=0.6, sequential)
        print(f"Phase 1: Generating 3 JSONs for {sentence_hash}")
        generation_results = []
        for i in range(3):
            llm_response = call_llm(text, sentence_hash, job_id, 0.6, current_attempts + 1, i + 1, scorer_feedback)
            
            # Extract content from LLM response
            content = ""
            if 'choices' in llm_response and len(llm_response['choices']) > 0:
                content = llm_response['choices'][0].get('message', {}).get('content', '')
            
            # Parse JSON from response
            parsed = parse_llm_json_response(content)
            if parsed:
                json_payload = parsed
            else:
                print(f"Failed to parse JSON from generation {i+1}")
                json_payload = {'entities': []}

            generation_results.append({
                'json': json_payload,
                'content': content,
                'reasoning': extract_reasoning_block(content)
            })
        
        # Phase 2: Fidelity check each JSON with correction loop
        print(f"Phase 2: Fidelity check")
        for i, result in enumerate(generation_results):
            json_data = result['json']
            # Schema validation
            is_valid_schema, schema_error = validate_schema(json_data, D1_SCHEMA)
            if not is_valid_schema:
                print(f"JSON {i+1} failed schema validation: {schema_error}")
                result['json'] = {'entities': []}
                continue
            
            # Fidelity validation
            is_valid_fidelity, fidelity_errors = validate_d1_fidelity(json_data, text)
            if not is_valid_fidelity:
                print(f"JSON {i+1} failed fidelity check: {fidelity_errors}")
                # Try correction once
                correction_payload = {
                    'job_id': job_id,
                    'sentence_hash': sentence_hash,
                    'stage': f'{STAGE}_Correction',
                    'prompt_name': 'correction_prompt.txt',
                    'temperature': 0.3,
                    'attempt_number': current_attempts + 1,
                    'generation_index': i + 1,
                    'inputs': {
                        'SENTENCE_HERE': text,
                        'FAILED_JSON': json.dumps(json_data, indent=2),
                        'ORIGINAL_REASONING': result.get('reasoning', ''),
                        'ERROR_DESCRIPTIONS': '\n'.join(fidelity_errors)
                    }
                }
                try:
                    correction_response = lambda_client.invoke(
                        FunctionName=LLM_LAMBDA,
                        InvocationType='RequestResponse',
                        Payload=json.dumps(correction_payload)
                    )
                    corrected_llm = json.loads(correction_response['Payload'].read())
                    corrected_content = corrected_llm.get('choices', [{}])[0].get('message', {}).get('content', '')
                    corrected_json = parse_llm_json_response(corrected_content)
                    
                    # Validate corrected JSON
                    if corrected_json:
                        is_valid_corrected, _ = validate_d1_fidelity(corrected_json, text)
                        if is_valid_corrected:
                            print(f"JSON {i+1} corrected successfully")
                            json_data = corrected_json
                        else:
                            print(f"JSON {i+1} correction failed, using original")
                except Exception as e:
                    print(f"Correction error for JSON {i+1}: {e}")
            
            result['json'] = json_data

        valid_jsons = [result['json'] for result in generation_results]
        
        # Phase 2a: Consensus check
        print(f"Phase 2a: Consensus check")
        if check_consensus(valid_jsons[0], valid_jsons[1], valid_jsons[2]):
            print("Consensus achieved! Score=100")
            best_json = valid_jsons[0]
            best_score = 100
            update_sentence_result(sentence_hash, job_id, best_score, current_attempts + 1, False)
            save_to_s3(sentence_hash, best_json)
            return clean_event_payload(event)
        
        # Phase 3: Scoring Pass 1 (temp=0.0)
        print(f"Phase 3: Scoring Pass 1")
        scorer_result1 = call_scorer(text, valid_jsons[0], valid_jsons[1], valid_jsons[2], 
                                     sentence_hash, job_id, 0.0)
        scores_pass1 = scorer_result1.get('scores', [0, 0, 0])
        print(f"Pass 1 scores: {scores_pass1}")
        
        if all(s < 70 for s in scores_pass1):
            print("All scores < 70 in Pass 1, retrying...")
            # Store scorer feedback for next attempt
            scorer_feedback = f"Previous attempt {current_attempts + 1} scores: {scores_pass1}. Reasoning: {scorer_result1.get('raw_response', '')[:500]}"
            update_sentence_result(sentence_hash, job_id, max(scores_pass1), current_attempts + 1, 
                                 True, f"Low scores in Pass 1: {scores_pass1}")
            # Store feedback in DynamoDB for next retry
            try:
                dynamodb.update_item(
                    TableName=SENTENCES_TABLE,
                    Key={'sentence_hash': {'S': sentence_hash}},
                    UpdateExpression='SET scorer_feedback = :feedback',
                    ExpressionAttributeValues={':feedback': {'S': scorer_feedback}}
                )
            except Exception as err:
                print(f"Failed to persist scorer feedback: {err}")
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
                # Store scorer feedback
                scorer_feedback = f"Attempt {current_attempts + 1} - Pass1: {scores_pass1}, Pass2: {scores_pass2}. Feedback: {scorer_result2.get('raw_response', '')[:500]}"
                update_sentence_result(sentence_hash, job_id, max(scores_pass2), current_attempts + 1,
                                     True, f"Low scores in Pass 2: {scores_pass2}")
                try:
                    dynamodb.update_item(
                        TableName=SENTENCES_TABLE,
                        Key={'sentence_hash': {'S': sentence_hash}},
                        UpdateExpression='SET scorer_feedback = :feedback',
                        ExpressionAttributeValues={':feedback': {'S': scorer_feedback}}
                    )
                except Exception as err:
                    print(f"Failed to persist scorer feedback: {err}")
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
        failure_reason = None
        if needs_review and current_attempts + 1 >= MAX_ATTEMPTS:
            failure_reason = 'LOW_QUALITY_SCORES'
        update_sentence_result(sentence_hash, job_id, best_score, current_attempts + 1, needs_review, failure_reason)
        if not needs_review:
            try:
                dynamodb.update_item(
                    TableName=SENTENCES_TABLE,
                    Key={'sentence_hash': {'S': sentence_hash}},
                    UpdateExpression='REMOVE scorer_feedback'
                )
            except Exception as err:
                print(f"Failed to clear scorer feedback: {err}")
        save_to_s3(sentence_hash, best_json)
        
        return clean_event_payload(event)
        
    except Exception as e:
        print(f"Error in entity extraction: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'error': str(e), **event}

