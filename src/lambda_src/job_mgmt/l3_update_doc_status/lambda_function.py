import json
import os
import boto3

# Boto3 clients
dynamodb = boto3.client("dynamodb")

# Environment variables
JOBS_TABLE = os.environ["JOBS_TABLE"]
LLM_LOG_TABLE = os.environ["LLM_LOG_TABLE"]

def lambda_handler(event, context):
    """
    GET /docs/{job_id}/status - Get document processing status
    OR called from Step Function with action: mark_complete
    """
    
    try:
        # Check if called from Step Function
        if 'action' in event and event['action'] == 'mark_complete':
            job_id = event['job_id']
            
            # Update job status to completed
            dynamodb.update_item(
                TableName=JOBS_TABLE,
                Key={'job_id': {'S': job_id}},
                UpdateExpression='SET #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': {'S': 'completed'}}
            )
            
            print(f"Marked job {job_id} as completed")
            return {'status': 'completed', 'job_id': job_id}
        
        # Get job_id from path parameters (API Gateway call)
        job_id = event['pathParameters']['job_id']
        
        # Get document info
        doc_response = dynamodb.get_item(
            TableName=JOBS_TABLE,
            Key={'job_id': {'S': job_id}}
        )
        
        if 'Item' not in doc_response:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Document not found'})
            }
        
        doc_item = doc_response['Item']
        
        # Get LLM call count for this job
        llm_count_response = dynamodb.query(
            TableName=LLM_LOG_TABLE,
            IndexName='ByJobId',
            KeyConditionExpression='job_id = :jid',
            ExpressionAttributeValues={':jid': {'S': job_id}},
            Select='COUNT'
        )
        
        # Get completed sentences count
        # Note: This requires the sentences table to have a ByJobId GSI
        sentence_count_response = dynamodb.query(
            TableName='Sentences',  # Using table name directly since not in env
            IndexName='ByJobId',
            KeyConditionExpression='job_id = :jid',
            FilterExpression='(#status = :done) OR (#legacy_status = :legacy_done)',
            ExpressionAttributeNames={
                '#status': 'status',
                '#legacy_status': 'kg_status'
            },
            ExpressionAttributeValues={
                ':jid': {'S': job_id},
                ':done': {'S': 'KG_COMPLETE'},
                ':legacy_done': {'S': 'kg_done'}
            },
            Select='COUNT'
        )
        
        # Build response
        status_data = {
            'job_id': job_id,
            'filename': doc_item.get('filename', {}).get('S', ''),
            'status': doc_item.get('status', {}).get('S', ''),
            'total_sentences': int(doc_item.get('total_sentences', {}).get('N', '0')),
            'completed_sentences': sentence_count_response.get('Count', 0),
            'llm_calls_made': llm_count_response.get('Count', 0),
            'created_at': doc_item.get('created_at', {}).get('S', ''),
            'progress_percentage': 0
        }
        
        # Calculate progress
        if status_data['total_sentences'] > 0:
            status_data['progress_percentage'] = round(
                (status_data['completed_sentences'] / status_data['total_sentences']) * 100, 2
            )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps(status_data)
        }
        
    except Exception as e:
        print(f"Error getting document status: {str(e)}")
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
