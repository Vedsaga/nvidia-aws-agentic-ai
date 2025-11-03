import json
import os
import boto3

# Boto3 clients
s3_client = boto3.client("s3")

# Environment variables
VERIFIED_BUCKET = os.environ["VERIFIED_BUCKET"]

def lambda_handler(event, context):
    """
    Get sentences array from S3 for Step Functions processing
    Input: {'job_id': str, 's3_path': str}
    Output: {'sentences': [...]}
    """
    
    try:
        # Get s3_path from event
        s3_path = event['s3_path']
        
        # Read sentences file from S3
        response = s3_client.get_object(
            Bucket=VERIFIED_BUCKET,
            Key=s3_path
        )
        
        # Parse JSON data
        data = json.loads(response['Body'].read().decode('utf-8'))
        
        # Return sentences array for Step Functions Map state
        return {'sentences': data}
        
    except Exception as e:
        print(f"Error getting sentences from S3: {str(e)}")
        raise