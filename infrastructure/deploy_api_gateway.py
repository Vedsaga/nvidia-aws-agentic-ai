#!/usr/bin/env python3
"""Deploy API Gateway for Karaka RAG system."""

import boto3
import json
import sys


def create_api(client, api_name='karaka-rag-api'):
    """Create REST API."""
    try:
        response = client.create_rest_api(
            name=api_name,
            description='Karaka RAG System API',
            endpointConfiguration={'types': ['REGIONAL']}
        )
        api_id = response['id']
        print(f"Created API: {api_id}")
        return api_id
    except Exception as e:
        print(f"Error creating API: {e}")
        return None


def get_root_resource(client, api_id):
    """Get root resource ID."""
    response = client.get_resources(restApiId=api_id)
    for item in response['items']:
        if item['path'] == '/':
            return item['id']
    return None


def create_resource(client, api_id, parent_id, path_part):
    """Create API resource."""
    try:
        response = client.create_resource(
            restApiId=api_id,
            parentId=parent_id,
            pathPart=path_part
        )
        print(f"Created resource: /{path_part}")
        return response['id']
    except Exception as e:
        print(f"Error creating resource {path_part}: {e}")
        return None


def create_method(client, api_id, resource_id, http_method, lambda_arn):
    """Create API method with Lambda integration."""
    # Create method
    try:
        client.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            authorizationType='NONE'
        )
    except Exception as e:
        print(f"Error creating method: {e}")
        return False
    
    # Create integration
    try:
        client.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=f"arn:aws:apigateway:{boto3.session.Session().region_name}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
        )
    except Exception as e:
        print(f"Error creating integration: {e}")
        return False
    
    # Enable CORS
    try:
        client.put_method_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Origin': True
            }
        )
    except:
        pass
    
    return True


def enable_cors(client, api_id, resource_id):
    """Enable CORS for resource."""
    try:
        client.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE'
        )
        
        client.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            requestTemplates={'application/json': '{"statusCode": 200}'}
        )
        
        client.put_method_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True
            }
        )
        
        client.put_integration_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            }
        )
    except Exception as e:
        print(f"Warning: CORS setup issue: {e}")


def deploy_api(client, api_id, stage_name='prod'):
    """Deploy API to stage."""
    try:
        client.create_deployment(
            restApiId=api_id,
            stageName=stage_name,
            description='Production deployment'
        )
        print(f"Deployed API to stage: {stage_name}")
        return True
    except Exception as e:
        print(f"Error deploying API: {e}")
        return False


def main():
    """Deploy API Gateway."""
    if len(sys.argv) < 5:
        print("Usage: deploy_api_gateway.py <ingestion_lambda_arn> <query_lambda_arn> <status_lambda_arn> <graph_lambda_arn>")
        return 1
    
    ingestion_arn = sys.argv[1]
    query_arn = sys.argv[2]
    status_arn = sys.argv[3]
    graph_arn = sys.argv[4]
    
    client = boto3.client('apigateway')
    region = boto3.session.Session().region_name
    
    # Create API
    api_id = create_api(client)
    if not api_id:
        return 1
    
    root_id = get_root_resource(client, api_id)
    
    # Create /ingest resource
    ingest_id = create_resource(client, api_id, root_id, 'ingest')
    if ingest_id:
        create_method(client, api_id, ingest_id, 'POST', ingestion_arn)
        enable_cors(client, api_id, ingest_id)
        
        # Create /ingest/status resource
        status_resource_id = create_resource(client, api_id, ingest_id, 'status')
        if status_resource_id:
            # Create /ingest/status/{job_id} resource
            job_id_resource_id = create_resource(client, api_id, status_resource_id, '{job_id}')
            if job_id_resource_id:
                create_method(client, api_id, job_id_resource_id, 'GET', status_arn)
                enable_cors(client, api_id, job_id_resource_id)
    
    # Create /query resource
    query_id = create_resource(client, api_id, root_id, 'query')
    if query_id:
        create_method(client, api_id, query_id, 'POST', query_arn)
        enable_cors(client, api_id, query_id)
    
    # Create /graph resource
    graph_id = create_resource(client, api_id, root_id, 'graph')
    if graph_id:
        create_method(client, api_id, graph_id, 'GET', graph_arn)
        enable_cors(client, api_id, graph_id)
    
    # Deploy API
    if deploy_api(client, api_id):
        api_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/prod"
        print(f"\n=== API Gateway Deployed ===")
        print(f"API URL: {api_url}")
        print(f"\nEndpoints:")
        print(f"  POST {api_url}/ingest")
        print(f"  GET  {api_url}/ingest/status/{{job_id}}")
        print(f"  POST {api_url}/query")
        print(f"  GET  {api_url}/graph")
        print(f"\nAdd to .env: API_GATEWAY_URL={api_url}")
        return 0
    
    return 1


if __name__ == '__main__':
    sys.exit(main())
