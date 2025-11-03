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
        
        # Create/update sentence records in DynamoDB
        for sentence in data:
            sentence_hash = sentence['hash']
            sentence_text = sentence['text']
            
            try:
                # Check if sentence already exists
                existing = dynamodb.get_item(
                    TableName=SENTENCES_TABLE,
                    Key={'sentence_hash': {'S': sentence_hash}}
                )
                
                if 'Item' in existing:
                    # Sentence exists - check if already processed
                    if existing['Item'].get('kg_status', {}).get('S') == 'kg_done':
                        print(f"Sentence {sentence_hash} already processed, skipping")
                        continue
                    
                    # Update existing record to add this job_id to documents
                    docs = existing['Item'].get('documents', {}).get('SS', [])
                    if job_id not in docs:
                        docs.append(job_id)
                    
                    dynamodb.update_item(
                        TableName=SENTENCES_TABLE,
                        Key={'sentence_hash': {'S': sentence_hash}},
                        UpdateExpression='SET documents = :docs',
                        ExpressionAttributeValues={':docs': {'SS': docs}}
                    )
                else:
                    # Create new sentence record
                    dynamodb.put_item(
                        TableName=SENTENCES_TABLE,
                        Item={
                            'sentence_hash': {'S': sentence_hash},
                            'text': {'S': sentence_text},
                            'job_id': {'S': job_id},
                            'kg_status': {'S': 'pending'},
                            'documents': {'SS': [job_id]}
                        }
                    )
                    print(f"Created sentence record for {sentence_hash}")
                    
            except Exception as e:
                print(f"Error creating sentence record for {sentence_hash}: {e}")
                # Continue processing other sentences
        
        # Return sentences array for Step Functions Map state
        return {'sentences': data}
        
    except Exception as e:
        print(f"Error getting sentences from S3: {str(e)}")
        raise