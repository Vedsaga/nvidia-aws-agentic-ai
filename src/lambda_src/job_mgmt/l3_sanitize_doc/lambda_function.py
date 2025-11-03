import json
import os
import boto3
import re
import hashlib

# Boto3 clients
s3_client = boto3.client("s3")
dynamodb = boto3.client("dynamodb")
sfn_client = boto3.client("stepfunctions")

# Environment variables
JOBS_TABLE = os.environ["JOBS_TABLE"]
VERIFIED_BUCKET = os.environ["VERIFIED_BUCKET"]
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]

def lambda_handler(event, context):
    """
    Sanitize document and start Step Functions processing
    """
    
    try:
        # Get input parameters
        job_id = event['job_id']
        s3_key = event['s3_key']
        s3_bucket = event['s3_bucket']
        
        print(f"Sanitizing document: job_id={job_id}, s3_key={s3_key}")
        
        # Read the uploaded file
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        text_content = response['Body'].read().decode('utf-8')
        
        # Split into sentences using regex
        sentences = re.split(r'(?<=[.!?])\s+', text_content.strip())
        sentences = [s.strip() for s in sentences if s.strip()]  # Remove empty sentences
        
        # Create sentence list with hashes
        sentence_list = []
        for sentence in sentences:
            sentence_hash = hashlib.sha256(sentence.encode()).hexdigest()
            sentence_list.append({
                'text': sentence,
                'hash': sentence_hash,
                'job_id': job_id
            })
        
        # Save sentences to verified bucket
        sentences_s3_key = f'{job_id}/sentences.json'
        s3_client.put_object(
            Bucket=VERIFIED_BUCKET,
            Key=sentences_s3_key,
            Body=json.dumps(sentence_list),
            ContentType='application/json'
        )
        
        # Update job status and sentence count
        dynamodb.update_item(
            TableName=JOBS_TABLE,
            Key={'job_id': {'S': job_id}},
            UpdateExpression='SET #s = :stat, total_sentences = :count',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':stat': {'S': 'processing_kg'},
                ':count': {'N': str(len(sentence_list))}
            }
        )
        
        # Start Step Functions execution
        sfn_input = {
            'job_id': job_id,
            's3_path': sentences_s3_key
        }
        
        sfn_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps(sfn_input)
        )
        
        print(f"Successfully started Step Functions for job {job_id} with {len(sentence_list)} sentences")
        
    except Exception as e:
        print(f"Error in document sanitization: {str(e)}")
        # Update job status to error
        try:
            dynamodb.update_item(
                TableName=JOBS_TABLE,
                Key={'job_id': {'S': job_id}},
                UpdateExpression='SET #s = :stat, error_message = :err',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':stat': {'S': 'error'},
                    ':err': {'S': str(e)}
                }
            )
        except:
            pass
        raise
