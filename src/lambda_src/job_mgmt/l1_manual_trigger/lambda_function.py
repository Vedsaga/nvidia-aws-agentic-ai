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
    Manual trigger for document processing - bypasses S3 trigger
    """
    
    try:
        # Get job_id from path parameters
        job_id = event['pathParameters']['job_id']
        
        print(f"Manual trigger for job_id: {job_id}")
        
        # Get job details from DynamoDB
        response = dynamodb.get_item(
            TableName=JOBS_TABLE,
            Key={'job_id': {'S': job_id}}
        )
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST'
                },
                'body': json.dumps({'error': 'Job not found'})
            }
        
        job_item = response['Item']
        s3_key = job_item['s3_raw_key']['S']
        
        # Update job status to validating
        dynamodb.update_item(
            TableName=JOBS_TABLE,
            Key={'job_id': {'S': job_id}},
            UpdateExpression='SET #s = :stat',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':stat': {'S': 'validating'}}
        )
        
        # Invoke sanitization Lambda asynchronously
        lambda_client.invoke(
            FunctionName=SANITIZE_LAMBDA_NAME,
            InvocationType='Event',
            Payload=json.dumps({
                'job_id': job_id,
                's3_key': s3_key,
                's3_bucket': os.environ.get('RAW_BUCKET', 'raw-documents-151534200269-us-east-1')
            })
        )
        
        print(f"Successfully triggered processing for job {job_id}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'message': 'Processing triggered successfully',
                'job_id': job_id,
                'status': 'validating'
            })
        }
        
    except Exception as e:
        print(f"Error in manual trigger: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({'error': str(e)})
        }