import json
import os
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Lambda handler for retrieving job status from S3
    GET /ingest/status/{job_id}
    """
    try:
        # Parse job_id from path parameters
        job_id = event.get('pathParameters', {}).get('job_id')
        
        if not job_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Missing job_id parameter'})
            }
        
        # Read job status from S3
        bucket_name = os.environ['S3_BUCKET']
        key = f"jobs/{job_id}.json"
        
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=key)
            job_data = json.loads(response['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return {
                    'statusCode': 404,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'error': f'Job {job_id} not found'})
                }
            raise
        
        # Calculate progress percentage
        total_lines = job_data.get('total_lines', 0)
        processed = job_data.get('processed', 0)
        percentage = (processed / total_lines * 100) if total_lines > 0 else 0
        
        # Build response with progress and statistics
        response_data = {
            'job_id': job_data.get('job_id'),
            'document_id': job_data.get('document_id'),
            'document_name': job_data.get('document_name'),
            'status': job_data.get('status'),
            'progress': processed,
            'total': total_lines,
            'percentage': round(percentage, 2),
            'statistics': job_data.get('statistics', {
                'success': 0,
                'skipped': 0,
                'errors': 0
            }),
            'started_at': job_data.get('started_at'),
            'updated_at': job_data.get('updated_at'),
            'completed_at': job_data.get('completed_at')
        }
        
        # Include recent results if available (last 5 processed lines)
        if 'results' in job_data and len(job_data['results']) > 0:
            response_data['recent_results'] = job_data['results'][-5:]
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        print(f"Error retrieving job status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }
