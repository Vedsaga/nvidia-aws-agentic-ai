import json
import boto3
import os

dynamodb = boto3.client('dynamodb')

def lambda_handler(event, context):
    """
    Check if sentence is already processed (deduplication)
    Input: {'text': ..., 'hash': 'abc...', 'job_id': 'xyz...'}
    Output: {'kg_status': 'kg_done'} or {'kg_status': 'pending'}
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
            # Sentence exists, check if KG processing is done
            if response['Item'].get('kg_status', {}).get('S') == 'kg_done':
                # Already processed, skip
                return {'kg_status': 'kg_done'}
        
        # Sentence not found or not done - create/update entry with all required fields
        dynamodb.put_item(
            TableName=os.environ['SENTENCES_TABLE'],
            Item={
                'sentence_hash': {'S': sentence_hash},
                'text': {'S': event['text']},
                'original_sentence': {'S': event['text']},  # Store original sentence
                'job_id': {'S': job_id},
                'document_ids': {'SS': [job_id]},  # Track all source documents
                'kg_status': {'S': 'pending'},
                'status': {'S': 'KG_PENDING'},  # Proper status enum
                'documents': {'SS': [job_id]},  # Keep for backward compatibility
                'd1_attempts': {'N': '0'},
                'd2a_attempts': {'N': '0'},
                'd2b_attempts': {'N': '0'},
                'needs_review': {'BOOL': False}
            }
        )
        
        return {'kg_status': 'pending'}
        
    except Exception as e:
        print(f"Error in dedup check: {str(e)}")
        # Default to pending if error
        return {'kg_status': 'pending'}