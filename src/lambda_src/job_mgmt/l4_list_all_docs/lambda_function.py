import json
import os
import boto3

# Boto3 clients
dynamodb = boto3.client("dynamodb")

# Environment variables
JOBS_TABLE = os.environ["JOBS_TABLE"]

def lambda_handler(event, context):
    """
    GET /docs - List all documents
    """
    
    try:
        # Scan the jobs table for recent documents
        response = dynamodb.scan(
            TableName=JOBS_TABLE,
            Limit=20,
            Select='SPECIFIC_ATTRIBUTES',
            ProjectionExpression='job_id, filename, #status, preview_text, created_at',
            ExpressionAttributeNames={'#status': 'status'}
        )
        
        # Format response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'data': response.get('Items', []),
                'pagination': {
                    'total': response.get('Count', 0),
                    'limit': 20
                }
            })
        }
        
    except Exception as e:
        print(f"Error listing documents: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
