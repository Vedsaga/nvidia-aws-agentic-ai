#!/usr/bin/env python3
import boto3
import json
import time

# Check KG extraction status
s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')
sfn = boto3.client('stepfunctions')

kg_bucket = "knowledge-graph-151534200269-us-east-1"

print("=== Checking KG Extraction Status ===\n")

# Check sentences table
print("1. Checking Sentences table...")
response = dynamodb.scan(
    TableName='Sentences',
    Limit=5
)

if response['Items']:
    for item in response['Items']:
        sentence_hash = item['sentence_hash']['S']
        text = item.get('text', {}).get('S', 'N/A')
        kg_status = item.get('kg_status', {}).get('S', 'N/A')
        print(f"  - {text[:50]}... | Status: {kg_status}")
else:
    print("  No sentences found")

# Check S3 for graphs
print("\n2. Checking S3 for graph files...")
try:
    response = s3.list_objects_v2(Bucket=kg_bucket, Prefix='graphs/', MaxKeys=10)
    if 'Contents' in response:
        print(f"  Found {len(response['Contents'])} graph files:")
        for obj in response['Contents']:
            print(f"    - {obj['Key']} ({obj['Size']} bytes)")
    else:
        print("  No graph files found")
except Exception as e:
    print(f"  Error: {e}")

# Check S3 for embeddings
print("\n3. Checking S3 for embeddings...")
try:
    response = s3.list_objects_v2(Bucket=kg_bucket, Prefix='embeddings/', MaxKeys=10)
    if 'Contents' in response:
        print(f"  Found {len(response['Contents'])} embedding files:")
        for obj in response['Contents']:
            print(f"    - {obj['Key']} ({obj['Size']} bytes)")
    else:
        print("  No embedding files found")
except Exception as e:
    print(f"  Error: {e}")

# Check Step Functions executions
print("\n4. Checking recent Step Function executions...")
try:
    response = sfn.list_executions(
        stateMachineArn='arn:aws:states:us-east-1:151534200269:stateMachine:KarakaKGProcessing',
        maxResults=3
    )
    if response['executions']:
        for exec in response['executions']:
            print(f"  - {exec['name']}")
            print(f"    Status: {exec['status']}")
            print(f"    Started: {exec['startDate']}")
            if exec['status'] == 'FAILED':
                # Get execution details
                details = sfn.describe_execution(executionArn=exec['executionArn'])
                print(f"    Error: {details.get('error', 'N/A')}")
    else:
        print("  No executions found")
except Exception as e:
    print(f"  Error: {e}")

print("\n=== Check Complete ===")
