import json
import os
import boto3

# Boto3 clients
s3_client = boto3.client("s3")
dynamodb = boto3.client("dynamodb")

# Environment variables
VERIFIED_BUCKET = os.environ["VERIFIED_BUCKET"]
SENTENCES_TABLE = os.environ["SENTENCES_TABLE"]

def lambda_handler(event, context):
    """
    Get sentences array from S3 for Step Functions processing
    Also creates/updates sentence records in DynamoDB
    Input: {'job_id': str, 's3_path': str}
    Output: {'sentences': [...]}
    """
    
    try:
        job_id = event['job_id']
        s3_path = event['s3_path']
        
        # Read sentences file from S3
        response = s3_client.get_object(
            Bucket=VERIFIED_BUCKET,
            Key=s3_path
        )
        
        # Parse JSON data
        data = json.loads(response['Body'].read().decode('utf-8'))
        
        sentences_to_process = []

        # Create/update sentence records in DynamoDB
        for sentence in data:
            sentence_hash = sentence['hash']
            sentence_text = sentence['text']
            should_process = True
            
            try:
                # Check if sentence already exists
                existing = dynamodb.get_item(
                    TableName=SENTENCES_TABLE,
                    Key={'sentence_hash': {'S': sentence_hash}}
                )
                
                if 'Item' in existing:
                    item = existing['Item']
                    status_value = item.get('status', {}).get('S')
                    legacy_status = item.get('kg_status', {}).get('S')
                    if status_value == 'KG_COMPLETE' or legacy_status == 'kg_done':
                        print(f"Sentence {sentence_hash} already complete, skipping reprocessing")
                        should_process = False

                    docs = set(item.get('document_ids', {}).get('SS', []))
                    legacy_docs = item.get('documents', {}).get('SS', [])
                    if not docs and legacy_docs:
                        docs.update(legacy_docs)

                    docs.add(job_id)

                    dynamodb.update_item(
                        TableName=SENTENCES_TABLE,
                        Key={'sentence_hash': {'S': sentence_hash}},
                        UpdateExpression='SET document_ids = :docs, job_id = :job, original_sentence = if_not_exists(original_sentence, :text), text = if_not_exists(text, :text)',
                        ExpressionAttributeValues={
                            ':docs': {'SS': sorted(docs)},
                            ':job': {'S': job_id},
                            ':text': {'S': sentence_text}
                        }
                    )
                else:
                    dynamodb.put_item(
                        TableName=SENTENCES_TABLE,
                        Item={
                            'sentence_hash': {'S': sentence_hash},
                            'original_sentence': {'S': sentence_text},
                            'text': {'S': sentence_text},
                            'job_id': {'S': job_id},
                            'document_ids': {'SS': [job_id]},
                            'status': {'S': 'KG_PENDING'},
                            'kg_status': {'S': 'pending'},
                            'best_score': {'N': '0'},
                            'needs_review': {'BOOL': False},
                            'attempts_count': {'N': '0'},
                            'd1_attempts': {'N': '0'},
                            'd2a_attempts': {'N': '0'},
                            'd2b_attempts': {'N': '0'}
                        }
                    )
                    print(f"Created sentence record for {sentence_hash}")
                    
            except Exception as e:
                print(f"Error creating sentence record for {sentence_hash}: {e}")
                # Continue processing other sentences
            else:
                if should_process:
                    sentences_to_process.append(sentence)
        
        # Return sentences array for Step Functions Map state
        return {'sentences': sentences_to_process}
        
    except Exception as e:
        print(f"Error getting sentences from S3: {str(e)}")
        raise