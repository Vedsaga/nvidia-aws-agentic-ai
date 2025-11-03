#!/usr/bin/env python3
import boto3
import json
import time
import os
from datetime import datetime, timedelta

# Load environment
import subprocess
result = subprocess.run(['bash', '-c', 'source .env && env'], capture_output=True, text=True)
env_vars = {}
for line in result.stdout.split('\n'):
    if '=' in line:
        key, value = line.split('=', 1)
        env_vars[key] = value

# Set up AWS session
session = boto3.Session(
    aws_access_key_id=env_vars.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=env_vars.get('AWS_SECRET_ACCESS_KEY'),
    aws_session_token=env_vars.get('AWS_SESSION_TOKEN'),
    region_name=env_vars.get('AWS_REGION', 'us-east-1')
)

s3 = session.client('s3')
logs = session.client('logs')

# Test document
test_content = "This is a test document. Dr. Smith went to the store. He bought some items. The weather was nice."
test_filename = f"test-trigger-{int(time.time())}.txt"
bucket_name = "raw-documents-151534200269-us-east-1"

print(f"Uploading test document: {test_filename}")

# Upload to S3
s3.put_object(
    Bucket=bucket_name,
    Key=test_filename,
    Body=test_content.encode('utf-8'),
    ContentType='text/plain'
)

print("Document uploaded. Waiting 10 seconds for processing...")
time.sleep(10)

# Check CloudWatch logs
log_group_name = "/aws/lambda/ServerlessStack-ValidateDoc2962A8D4-UZL5IzMlb3B5"
try:
    # Get recent log streams
    streams = logs.describe_log_streams(
        logGroupName=log_group_name,
        orderBy='LastEventTime',
        descending=True,
        limit=3
    )
    
    print(f"Found {len(streams['logStreams'])} recent log streams")
    
    # Check recent events
    start_time = int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
    
    for stream in streams['logStreams']:
        stream_name = stream['logStreamName']
        print(f"\nChecking stream: {stream_name}")
        
        try:
            events = logs.get_log_events(
                logGroupName=log_group_name,
                logStreamName=stream_name,
                startTime=start_time
            )
            
            for event in events['events'][-10:]:  # Last 10 events
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                print(f"  {timestamp}: {event['message'].strip()}")
                
        except Exception as e:
            print(f"  Error reading stream: {e}")
            
except Exception as e:
    print(f"Error accessing CloudWatch logs: {e}")

print(f"\nTest completed. Check S3 bucket for processing results.")