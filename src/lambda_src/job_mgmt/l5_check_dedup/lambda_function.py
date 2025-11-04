import json
import boto3
import os

dynamodb = boto3.client('dynamodb')

def lambda_handler(event, context):
    """
    Check if sentence is already processed (deduplication)
    Input: {'text': ..., 'hash': 'abc...', 'job_id': 'xyz...'}
    Output: {'status': 'KG_COMPLETE', 'kg_status': 'kg_done'} or
        {'status': 'KG_PENDING', 'kg_status': 'pending'}
    """
    
    sentence_hash = event['hash']
    job_id = event['job_id']
    
    try:
        # Check if sentence already exists and is processed
        response = dynamodb.get_item(
            TableName=os.environ['SENTENCES_TABLE'],
            Key={'sentence_hash': {'S': sentence_hash}}
        )
        
        if 'Item' in response:
            status_value = response['Item'].get('status', {}).get('S')
            legacy_status = response['Item'].get('kg_status', {}).get('S')
            if status_value == 'KG_COMPLETE' or legacy_status == 'kg_done':
                return {'status': 'KG_COMPLETE', 'kg_status': 'kg_done'}

        # Sentence not found or not complete - ensure baseline record exists
        item = {
            'sentence_hash': {'S': sentence_hash},
            'original_sentence': {'S': event['text']},
            'text': {'S': event['text']},  # Legacy key retained for backward compatibility
            'job_id': {'S': job_id},
            'document_ids': {'SS': [job_id]},
            'status': {'S': 'KG_PENDING'},
            'kg_status': {'S': 'pending'},  # Legacy mirror of status
            'best_score': {'N': '0'},
            'needs_review': {'BOOL': False},
            'attempts_count': {'N': '0'},
            'd1_attempts': {'N': '0'},
            'd2a_attempts': {'N': '0'},
            'd2b_attempts': {'N': '0'}
        }

        # failure_reason is optional; omit until needed

        dynamodb.put_item(
            TableName=os.environ['SENTENCES_TABLE'],
            Item=item
        )
        
        return {'status': 'KG_PENDING', 'kg_status': 'pending'}
        
    except Exception as e:
        print(f"Error in dedup check: {str(e)}")
        return {'status': 'KG_PENDING', 'kg_status': 'pending'}