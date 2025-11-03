#!/usr/bin/env python3
import boto3
import json
import os
from datetime import datetime

# Load environment
import subprocess
result = subprocess.run(['bash', '-c', 'source .env && env'], capture_output=True, text=True)
env_vars = {}
for line in result.stdout.split('\n'):
    if '=' in line and not line.startswith('#'):
        key, value = line.split('=', 1)
        env_vars[key] = value.strip('"')

print("Environment variables loaded:")
for key in ['AWS_ACCESS_KEY_ID', 'AWS_REGION']:
    print(f"  {key}: {env_vars.get(key, 'NOT SET')[:10]}...")

# Set up AWS session
try:
    session = boto3.Session(
        aws_access_key_id=env_vars.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=env_vars.get('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=env_vars.get('AWS_SESSION_TOKEN'),
        region_name=env_vars.get('AWS_REGION', 'us-east-1')
    )

    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table('DocumentJobs')
    
    print("\nScanning DocumentJobs table...")
    response = table.scan()
    
    if response['Items']:
        print(f"Found {len(response['Items'])} jobs:")
        for item in response['Items']:
            print(f"  Job ID: {item.get('job_id', 'N/A')}")
            print(f"  Status: {item.get('status', 'N/A')}")
            print(f"  Filename: {item.get('filename', 'N/A')}")
            print(f"  Created: {item.get('created_at', 'N/A')}")
            print(f"  Updated: {item.get('updated_at', 'N/A')}")
            print("  ---")
    else:
        print("No jobs found in DocumentJobs table")
        
except Exception as e:
    print(f"Error: {e}")
    print("This might be due to expired AWS credentials")