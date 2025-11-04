#!/usr/bin/env python3
"""
Update Lambda functions to use LocalStack endpoints when running locally
"""
import os
import sys

LAMBDA_WRAPPER = '''
import os
import boto3

# Check if running in SAM local environment
if os.environ.get('AWS_SAM_LOCAL'):
    # Point to LocalStack
    endpoint_url = 'http://host.docker.internal:4566'
    
    # Override boto3 clients to use LocalStack
    s3_client = boto3.client('s3', endpoint_url=endpoint_url)
    dynamodb = boto3.client('dynamodb', endpoint_url=endpoint_url)
    dynamodb_resource = boto3.resource('dynamodb', endpoint_url=endpoint_url)
    lambda_client = boto3.client('lambda', endpoint_url=endpoint_url)
else:
    # Production - use real AWS
    s3_client = boto3.client('s3')
    dynamodb = boto3.client('dynamodb')
    dynamodb_resource = boto3.resource('dynamodb')
    lambda_client = boto3.client('lambda')
'''

def add_local_support(lambda_dir):
    """Add LocalStack support to a Lambda function"""
    lambda_file = os.path.join(lambda_dir, 'lambda_function.py')
    
    if not os.path.exists(lambda_file):
        return
    
    with open(lambda_file, 'r') as f:
        content = f.read()
    
    # Check if already has local support
    if 'AWS_SAM_LOCAL' in content:
        print(f"✓ {lambda_dir} already has local support")
        return
    
    # Find boto3 client initialization
    if 'boto3.client' in content or 'boto3.resource' in content:
        print(f"Adding local support to {lambda_dir}")
        # This is a simplified approach - in practice you'd need more sophisticated parsing
        print(f"  Manual update needed for {lambda_file}")

if __name__ == '__main__':
    print("Scanning Lambda functions for local testing support...")
    print("")
    
    lambda_base = 'src/lambda_src'
    for root, dirs, files in os.walk(lambda_base):
        if 'lambda_function.py' in files:
            add_local_support(root)
    
    print("")
    print("Note: Lambda functions need manual updates to check AWS_SAM_LOCAL")
    print("See shared/local_aws_clients.py for the pattern")
