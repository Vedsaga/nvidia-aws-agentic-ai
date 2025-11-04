"""
Shared AWS client initialization for local and production environments
Import this in Lambda functions instead of directly using boto3
"""
import os
import boto3

def get_endpoint_url():
    """Get endpoint URL for LocalStack if running locally"""
    if os.environ.get('AWS_SAM_LOCAL'):
        # Running in SAM local - use LocalStack
        return 'http://host.docker.internal:4566'
    return None

# Initialize clients with conditional endpoint
_endpoint = get_endpoint_url()

s3_client = boto3.client('s3', endpoint_url=_endpoint)
dynamodb_client = boto3.client('dynamodb', endpoint_url=_endpoint)
dynamodb_resource = boto3.resource('dynamodb', endpoint_url=_endpoint)
lambda_client = boto3.client('lambda', endpoint_url=_endpoint)
stepfunctions_client = boto3.client('stepfunctions', endpoint_url=_endpoint)

# For backward compatibility
dynamodb = dynamodb_client
