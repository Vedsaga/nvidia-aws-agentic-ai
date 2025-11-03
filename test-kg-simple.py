#!/usr/bin/env python3
import boto3
import json
import time

# Test simple KG extraction
s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')

# Upload test file
test_content = "Rama teaches Sita. Sita learns quickly."
bucket = "raw-documents-151534200269-us-east-1"
key = "test-kg-simple.txt"

print(f"Uploading test file to s3://{bucket}/{key}")
s3.put_object(Bucket=bucket, Key=key, Body=test_content)

print("Waiting for processing...")
time.sleep(5)

# Invoke manual trigger
print("Invoking manual trigger...")
response = lambda_client.invoke(
    FunctionName='ServerlessStack-ManualTriggerF0018E07-Vblmtsbs6hax',
    Payload=json.dumps({
        'bucket': bucket,
        'key': key
    })
)

result = json.loads(response['Payload'].read())
print(f"Manual trigger result: {json.dumps(result, indent=2)}")

if 'execution_arn' in result:
    print(f"\nStep Function execution started: {result['execution_arn']}")
    print("Check AWS Console for execution status")
