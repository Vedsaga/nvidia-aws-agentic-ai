#!/usr/bin/env python3
import boto3
import json

sfn = boto3.client('stepfunctions')

# Get latest execution
response = sfn.list_executions(
    stateMachineArn='arn:aws:states:us-east-1:151534200269:stateMachine:KarakaKGProcessing',
    maxResults=1
)

if response['executions']:
    exec_arn = response['executions'][0]['executionArn']
    print(f"Checking execution: {exec_arn}\n")
    
    # Get execution history
    history = sfn.get_execution_history(
        executionArn=exec_arn,
        maxResults=100,
        reverseOrder=True
    )
    
    print("=== Recent Events ===")
    for event in history['events'][:20]:
        event_type = event['type']
        timestamp = event['timestamp']
        
        print(f"\n{timestamp} - {event_type}")
        
        if 'TaskFailed' in event_type:
            details = event.get('taskFailedEventDetails', {})
            print(f"  Error: {details.get('error', 'N/A')}")
            print(f"  Cause: {details.get('cause', 'N/A')}")
        
        if 'LambdaFunctionFailed' in event_type:
            details = event.get('lambdaFunctionFailedEventDetails', {})
            print(f"  Error: {details.get('error', 'N/A')}")
            print(f"  Cause: {details.get('cause', 'N/A')}")
        
        if 'MapIterationSucceeded' in event_type or 'MapIterationFailed' in event_type:
            details = event.get('mapIterationSucceededEventDetails') or event.get('mapIterationFailedEventDetails', {})
            print(f"  Details: {json.dumps(details, indent=2)}")
    
    # Get final output
    details = sfn.describe_execution(executionArn=exec_arn)
    if 'output' in details:
        print(f"\n=== Final Output ===")
        output = json.loads(details['output'])
        print(json.dumps(output, indent=2))
