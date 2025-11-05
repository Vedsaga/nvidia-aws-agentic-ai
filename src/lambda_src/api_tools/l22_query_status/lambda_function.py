import json
import os
import boto3

dynamodb = boto3.client('dynamodb')
QUERIES_TABLE = os.environ.get('QUERIES_TABLE', 'Queries')

def lambda_handler(event, context):
    """Get query status and answer if ready"""
    try:
        query_id = event.get('pathParameters', {}).get('query_id')
        
        if not query_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps({'error': 'query_id is required'})
            }
        
        response = dynamodb.get_item(
            TableName=QUERIES_TABLE,
            Key={'query_id': {'S': query_id}}
        )
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps({'error': 'Query not found'})
            }
        
        item = response['Item']
        status = item.get('status', {}).get('S', 'unknown')
        answer = item.get('answer', {}).get('S', '')
        references = item.get('references', {}).get('S', '[]')
        
        result = {
            'query_id': query_id,
            'question': item.get('question', {}).get('S', ''),
            'status': status
        }
        
        if status == 'completed':
            result['answer'] = answer
            result['references'] = json.loads(references)
        elif status == 'error':
            result['error'] = item.get('error', {}).get('S', 'Unknown error')
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({'error': str(e)})
        }
