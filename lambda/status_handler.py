"""Lambda handler for job status retrieval."""

import json
import boto3
from src.config import Config


s3_client = boto3.client('s3')
config = Config()


def lambda_handler(event, context):
    """
    Retrieve job status.
    
    Path parameter: job_id
    """
    try:
        # Extract job_id from path parameters
        job_id = event.get('pathParameters', {}).get('job_id')
        
        if not job_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "error": "job_id is required"
                })
            }
        
        # Retrieve status from S3
        key = f"jobs/{job_id}/status.json"
        
        try:
            response = s3_client.get_object(Bucket=config.s3_bucket, Key=key)
            status = json.loads(response['Body'].read().decode('utf-8'))
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps(status)
            }
            
        except s3_client.exceptions.NoSuchKey:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "error": "Job not found"
                })
            }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": str(e)
            })
        }
