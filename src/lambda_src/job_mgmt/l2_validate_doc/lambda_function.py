import json
import os
import boto3

# Boto3 clients
dynamodb = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")

# Environment variables
JOBS_TABLE = os.environ["JOBS_TABLE"]
SANITIZE_LAMBDA_NAME = os.environ["SANITIZE_LAMBDA_NAME"]

def lambda_handler(event, context):
    """
    S3 trigger - validate uploaded document and invoke sanitization
    """
    
    print(f"L2 ValidateDoc triggered. Event: {json.dumps(event)}")
    
    try:
        # Parse S3 event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        # Extract job_id from S3 key (format: job_id/filename.txt)
        # Handle both formats: "job_id/filename.txt" and "job_id.txt"
        if '/' in key:
            job_id = key.split('/')[0]
        else:
            # If no slash, the key itself might be the job_id with extension
            job_id = key.rsplit('.', 1)[0]
        
        print(f"Processing document upload: bucket={bucket}, key={key}, job_id={job_id}")
        
        # Update job status to validating
        print(f"Updating job {job_id} status to 'validating'")
        dynamodb.update_item(
            TableName=JOBS_TABLE,
            Key={'job_id': {'S': job_id}},
            UpdateExpression='SET #s = :stat',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':stat': {'S': 'validating'}}
        )
        print(f"Job {job_id} status updated successfully")
        
        # Invoke sanitization Lambda asynchronously
        print(f"Invoking sanitization lambda: {SANITIZE_LAMBDA_NAME}")
        response = lambda_client.invoke(
            FunctionName=SANITIZE_LAMBDA_NAME,
            InvocationType='Event',
            Payload=json.dumps({
                'job_id': job_id,
                's3_key': key,
                's3_bucket': bucket
            })
        )
        print(f"Sanitization lambda invoked. Response: {response['StatusCode']}")
        
        print(f"Successfully triggered sanitization for job {job_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Processing started', 'job_id': job_id})
        }
        
    except Exception as e:
        print(f"Error in document validation: {str(e)}")
        # Update job status to error if possible
        try:
            if 'job_id' in locals():
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
