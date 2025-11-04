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
                    docs = set(item.get('document_ids', {}).get('SS', []))
                    legacy_docs = item.get('documents', {}).get('SS', [])
                    if not docs and legacy_docs:
                        docs.update(legacy_docs)

                    already_processed_for_job = job_id in docs
                    docs.add(job_id)

                    status_value = item.get('status', {}).get('S')
                    legacy_status = item.get('kg_status', {}).get('S')

                    reset_for_new_job = not already_processed_for_job

                    update_clauses = [
                        'document_ids = :docs',
                        'job_id = :job',
                        'original_sentence = if_not_exists(original_sentence, :text)',
                        'text = if_not_exists(text, :text)'
                    ]
                    expr_values = {
                        ':docs': {'SS': sorted(docs)},
                        ':job': {'S': job_id},
                        ':text': {'S': sentence_text}
                    }
                    expr_names = {}
                    remove_fields = []

                    if reset_for_new_job:
                        update_clauses.extend([
                            '#status = :pending',
                            'kg_status = :legacy_pending',
                            'best_score = :zero',
                            'needs_review = :false',
                            'attempts_count = :zero',
                            'd1_attempts = :zero',
                            'd2a_attempts = :zero',
                            'd2b_attempts = :zero'
                        ])
                        expr_names['#status'] = 'status'
                        expr_values.update({
                            ':pending': {'S': 'KG_PENDING'},
                            ':legacy_pending': {'S': 'pending'},
                            ':zero': {'N': '0'},
                            ':false': {'BOOL': False}
                        })
                        remove_fields.extend(['failure_reason', 'scorer_feedback'])

                    update_expression = 'SET ' + ', '.join(update_clauses)
                    if remove_fields:
                        update_expression += ' REMOVE ' + ', '.join(remove_fields)

                    update_args = {
                        'TableName': SENTENCES_TABLE,
                        'Key': {'sentence_hash': {'S': sentence_hash}},
                        'UpdateExpression': update_expression,
                        'ExpressionAttributeValues': expr_values
                    }
                    if expr_names:
                        update_args['ExpressionAttributeNames'] = expr_names

                    dynamodb.update_item(**update_args)

                    should_process = reset_for_new_job or not (status_value == 'KG_COMPLETE' or legacy_status == 'kg_done')
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