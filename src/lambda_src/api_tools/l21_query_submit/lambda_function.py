import json
import os
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.client('dynamodb')
QUERIES_TABLE = os.environ.get('QUERIES_TABLE', 'Queries')

def lambda_handler(event, context):
    """Submit a query and return query_id for polling"""
    try:
        body = json.loads(event.get('body', '{}'))
        question = body.get('question', '').strip()
        
        if not question:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'question is required'})
            }
        
        query_id = str(uuid.uuid4())
        
        # Store query in DynamoDB
        dynamodb.put_item(
            TableName=QUERIES_TABLE,
            Item={
                'query_id': {'S': query_id},
                'question': {'S': question},
                'status': {'S': 'processing'},
                'created_at': {'S': datetime.utcnow().isoformat()},
                'answer': {'S': ''},
                'references': {'S': '[]'}
            }
        )
        
        # Trigger Step Function for query processing
        sfn = boto3.client('stepfunctions')
        sfn_arn = os.environ.get('QUERY_SFN_ARN')
        
        if sfn_arn:
            sfn.start_execution(
                stateMachineArn=sfn_arn,
                input=json.dumps({'query_id': query_id, 'question': question})
            )
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'query_id': query_id,
                'question': question,
                'status': 'processing'
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
