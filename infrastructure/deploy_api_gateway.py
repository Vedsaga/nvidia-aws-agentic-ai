#!/usr/bin/env python3
"""
API Gateway Deployment Script for Kāraka RAG System
Creates REST API with Lambda integrations for ingestion, query, status, and graph endpoints
"""

import boto3
import json
import time
import sys
import os
from botocore.exceptions import ClientError

# Configuration
API_NAME = 'karaka-rag-api'
STAGE_NAME = 'prod'


def get_lambda_arns(lambda_client, region, account_id):
    """Get Lambda function ARNs"""
    functions = {
        'ingestion': f'arn:aws:lambda:{region}:{account_id}:function:karaka-ingestion-handler',
        'status': f'arn:aws:lambda:{region}:{account_id}:function:karaka-status-handler',
        'query': f'arn:aws:lambda:{region}:{account_id}:function:karaka-query-handler',
        'graph': f'arn:aws:lambda:{region}:{account_id}:function:karaka-graph-handler'
    }
    
    # Verify functions exist
    for name, arn in functions.items():
        try:
            lambda_client.get_function(FunctionName=f'karaka-{name}-handler')
            print(f"✓ Found Lambda function: karaka-{name}-handler")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"✗ Lambda function not found: karaka-{name}-handler")
                print(f"  Please deploy Lambda functions first")
                sys.exit(1)
            raise
    
    return functions


def create_rest_api(apigw):
    """Create or get REST API"""
    try:
        # Check if API already exists
        response = apigw.get_rest_apis(limit=500)
        for api in response['items']:
            if api['name'] == API_NAME:
                api_id = api['id']
                print(f"✓ Found existing API: {API_NAME} (ID: {api_id})")
                return api_id
        
        # Create new API
        print(f"Creating REST API: {API_NAME}")
        response = apigw.create_rest_api(
            name=API_NAME,
            description='Kāraka Graph RAG System API',
            endpointConfiguration={'types': ['REGIONAL']}
        )
        api_id = response['id']
        print(f"✓ Created REST API: {api_id}")
        return api_id
        
    except ClientError as e:
        print(f"✗ Error creating REST API: {e}")
        raise


def get_root_resource(apigw, api_id):
    """Get root resource ID"""
    response = apigw.get_resources(restApiId=api_id)
    for resource in response['items']:
        if resource['path'] == '/':
            return resource['id']
    raise Exception("Root resource not found")


def create_resource(apigw, api_id, parent_id, path_part):
    """Create API resource"""
    try:
        # Check if resource already exists
        response = apigw.get_resources(restApiId=api_id)
        for resource in response['items']:
            if resource.get('pathPart') == path_part and resource['parentId'] == parent_id:
                print(f"✓ Resource /{path_part} already exists")
                return resource['id']
        
        # Create resource
        print(f"Creating resource: /{path_part}")
        response = apigw.create_resource(
            restApiId=api_id,
            parentId=parent_id,
            pathPart=path_part
        )
        print(f"✓ Created resource: /{path_part}")
        return response['id']
        
    except ClientError as e:
        print(f"✗ Error creating resource /{path_part}: {e}")
        raise


def add_cors_options(apigw, api_id, resource_id):
    """Add OPTIONS method for CORS preflight"""
    try:
        # Check if OPTIONS method exists
        try:
            apigw.get_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS'
            )
            print(f"  ✓ OPTIONS method already exists")
            return
        except ClientError as e:
            if e.response['Error']['Code'] != 'NotFoundException':
                raise
        
        # Create OPTIONS method
        apigw.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE'
        )
        
        # Add mock integration
        apigw.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            requestTemplates={
                'application/json': '{"statusCode": 200}'
            }
        )
        
        # Add method response
        apigw.put_method_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True
            },
            responseModels={'application/json': 'Empty'}
        )
        
        # Add integration response
        apigw.put_integration_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                'method.response.header.Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            },
            responseTemplates={'application/json': ''}
        )
        
        print(f"  ✓ Added OPTIONS method for CORS")
        
    except ClientError as e:
        print(f"  ✗ Error adding CORS OPTIONS: {e}")
        raise


def create_lambda_integration(apigw, lambda_client, api_id, resource_id, http_method, lambda_arn, region):
    """Create Lambda integration for a method"""
    try:
        # Check if method exists
        try:
            apigw.get_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod=http_method
            )
            print(f"  ✓ {http_method} method already exists")
            return
        except ClientError as e:
            if e.response['Error']['Code'] != 'NotFoundException':
                raise
        
        # Create method
        apigw.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            authorizationType='NONE'
        )
        
        # Create Lambda integration
        uri = f'arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
        apigw.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=uri
        )
        
        # Add Lambda permission
        function_name = lambda_arn.split(':')[-1]
        statement_id = f'apigateway-{api_id}-{resource_id}-{http_method}'
        
        try:
            lambda_client.add_permission(
                FunctionName=function_name,
                StatementId=statement_id,
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f'arn:aws:execute-api:{region}:*:{api_id}/*/{http_method}/*'
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceConflictException':
                raise
        
        print(f"  ✓ Created {http_method} method with Lambda integration")
        
    except ClientError as e:
        print(f"  ✗ Error creating {http_method} method: {e}")
        raise


def deploy_api(apigw, api_id, stage_name):
    """Deploy API to stage"""
    try:
        print(f"Deploying API to stage: {stage_name}")
        apigw.create_deployment(
            restApiId=api_id,
            stageName=stage_name,
            description=f'Deployment to {stage_name} stage'
        )
        print(f"✓ Deployed API to {stage_name} stage")
        
    except ClientError as e:
        print(f"✗ Error deploying API: {e}")
        raise


def main():
    """Main deployment function"""
    print("=" * 60)
    print("Kāraka RAG System - API Gateway Deployment")
    print("=" * 60)
    print()
    
    # Get AWS configuration
    region = os.environ.get('AWS_REGION', 'us-east-1')
    print(f"AWS Region: {region}")
    
    # Get account ID
    sts = boto3.client('sts', region_name=region)
    account_id = sts.get_caller_identity()['Account']
    print(f"AWS Account: {account_id}")
    print()
    
    # Initialize clients
    apigw = boto3.client('apigateway', region_name=region)
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Get Lambda ARNs
    print("Step 1: Verify Lambda Functions")
    print("-" * 60)
    lambda_arns = get_lambda_arns(lambda_client, region, account_id)
    print()
    
    # Create REST API
    print("Step 2: Create REST API")
    print("-" * 60)
    api_id = create_rest_api(apigw)
    root_id = get_root_resource(apigw, api_id)
    print()
    
    # Create /ingest resource
    print("Step 3: Create /ingest Endpoint")
    print("-" * 60)
    ingest_id = create_resource(apigw, api_id, root_id, 'ingest')
    create_lambda_integration(apigw, lambda_client, api_id, ingest_id, 'POST', lambda_arns['ingestion'], region)
    add_cors_options(apigw, api_id, ingest_id)
    print()
    
    # Create /ingest/status resource
    print("Step 4: Create /ingest/status/{job_id} Endpoint")
    print("-" * 60)
    status_parent_id = create_resource(apigw, api_id, ingest_id, 'status')
    status_id = create_resource(apigw, api_id, status_parent_id, '{job_id}')
    create_lambda_integration(apigw, lambda_client, api_id, status_id, 'GET', lambda_arns['status'], region)
    add_cors_options(apigw, api_id, status_id)
    print()
    
    # Create /query resource
    print("Step 5: Create /query Endpoint")
    print("-" * 60)
    query_id = create_resource(apigw, api_id, root_id, 'query')
    create_lambda_integration(apigw, lambda_client, api_id, query_id, 'POST', lambda_arns['query'], region)
    add_cors_options(apigw, api_id, query_id)
    print()
    
    # Create /graph resource
    print("Step 6: Create /graph Endpoint")
    print("-" * 60)
    graph_id = create_resource(apigw, api_id, root_id, 'graph')
    create_lambda_integration(apigw, lambda_client, api_id, graph_id, 'GET', lambda_arns['graph'], region)
    add_cors_options(apigw, api_id, graph_id)
    print()
    
    # Deploy API
    print("Step 7: Deploy API")
    print("-" * 60)
    deploy_api(apigw, api_id, STAGE_NAME)
    print()
    
    # Output configuration
    print("=" * 60)
    print("Deployment Complete!")
    print("=" * 60)
    print()
    api_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/{STAGE_NAME}"
    print(f"API Gateway URL: {api_url}")
    print()
    print("Endpoints:")
    print(f"  POST   {api_url}/ingest")
    print(f"  GET    {api_url}/ingest/status/{{job_id}}")
    print(f"  POST   {api_url}/query")
    print(f"  GET    {api_url}/graph")
    print()
    print("Add this to your .env file:")
    print()
    print(f"API_GATEWAY_URL={api_url}")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Deployment failed: {e}")
        sys.exit(1)
