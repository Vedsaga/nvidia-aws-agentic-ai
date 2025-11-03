import json
import os
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.client('dynamodb')
lambda_client = boto3.client('lambda')
QUERIES_TABLE = os.environ.get('QUERIES_TABLE', 'Queries')
QUERY_PROCESSOR_LAMBDA = os.environ.get('QUERY_PROCESSOR_LAMBDA')

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
        
        # Invoke query processor asynchronously
        lambda_client.invoke(
            FunctionName=QUERY_PROCESSOR_LAMBDA,
            InvocationType='Event',
            Payload=json.dumps({'query_id': query_id, 'question': question})
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
