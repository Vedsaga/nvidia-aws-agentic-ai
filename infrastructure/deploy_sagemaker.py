#!/usr/bin/env python3
"""
SageMaker Deployment Script for Kāraka RAG System
Deploys NVIDIA NIM models (Nemotron and Embedding) to SageMaker endpoints
"""

import boto3
import time
import sys
import os
from botocore.exceptions import ClientError

# Configuration
NEMOTRON_MODEL_NAME = 'nemotron-karaka-model'
EMBEDDING_MODEL_NAME = 'embedding-karaka-model'
NEMOTRON_ENDPOINT_CONFIG = 'nemotron-karaka-config'
EMBEDDING_ENDPOINT_CONFIG = 'embedding-karaka-config'
NEMOTRON_ENDPOINT_NAME = 'nemotron-karaka-endpoint'
EMBEDDING_ENDPOINT_NAME = 'embedding-karaka-endpoint'
INSTANCE_TYPE = 'ml.g5.xlarge'

# NVIDIA NIM container images
NEMOTRON_IMAGE = 'nvcr.io/nim/meta/llama-3.1-nemotron-nano-8b-instruct:1.0.0'
EMBEDDING_IMAGE = 'nvcr.io/nim/nvidia/nv-embedqa-e5-v5:1.0.0'


def get_execution_role():
    """Get or create SageMaker execution role"""
    iam = boto3.client('iam')
    role_name = 'KarakaRAGSageMakerRole'
    
    try:
        response = iam.get_role(RoleName=role_name)
        role_arn = response['Role']['Arn']
        print(f"✓ Using existing IAM role: {role_arn}")
        return role_arn
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print(f"Creating IAM role: {role_name}")
            
            # Trust policy for SageMaker
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "sagemaker.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            }
            
            # Create role
            response = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=str(trust_policy),
                Description='Execution role for Kāraka RAG SageMaker endpoints'
            )
            role_arn = response['Role']['Arn']
            
            # Attach policies
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/AmazonSageMakerFullAccess'
            )
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess'
            )
            
            print(f"✓ Created IAM role: {role_arn}")
            print("  Waiting 10 seconds for role propagation...")
            time.sleep(10)
            
            return role_arn
        else:
            raise


def create_model(sagemaker, model_name, image_uri, role_arn):
    """Create SageMaker model"""
    try:
        # Check if model already exists
        try:
            sagemaker.describe_model(ModelName=model_name)
            print(f"✓ Model {model_name} already exists")
            return
        except ClientError as e:
            if e.response['Error']['Code'] != 'ValidationException':
                raise
        
        # Create model
        print(f"Creating model: {model_name}")
        sagemaker.create_model(
            ModelName=model_name,
            PrimaryContainer={
                'Image': image_uri,
                'Mode': 'SingleModel'
            },
            ExecutionRoleArn=role_arn
        )
        print(f"✓ Created model: {model_name}")
        
    except ClientError as e:
        print(f"✗ Error creating model {model_name}: {e}")
        raise


def create_endpoint_config(sagemaker, config_name, model_name, instance_type):
    """Create SageMaker endpoint configuration"""
    try:
        # Check if config already exists
        try:
            sagemaker.describe_endpoint_config(EndpointConfigName=config_name)
            print(f"✓ Endpoint config {config_name} already exists")
            return
        except ClientError as e:
            if e.response['Error']['Code'] != 'ValidationException':
                raise
        
        # Create endpoint config
        print(f"Creating endpoint config: {config_name}")
        sagemaker.create_endpoint_config(
            EndpointConfigName=config_name,
            ProductionVariants=[{
                'VariantName': 'AllTraffic',
                'ModelName': model_name,
                'InstanceType': instance_type,
                'InitialInstanceCount': 1,
                'InitialVariantWeight': 1.0
            }]
        )
        print(f"✓ Created endpoint config: {config_name}")
        
    except ClientError as e:
        print(f"✗ Error creating endpoint config {config_name}: {e}")
        raise


def create_endpoint(sagemaker, endpoint_name, config_name):
    """Create SageMaker endpoint"""
    try:
        # Check if endpoint already exists
        try:
            response = sagemaker.describe_endpoint(EndpointName=endpoint_name)
            status = response['EndpointStatus']
            
            if status == 'InService':
                print(f"✓ Endpoint {endpoint_name} already exists and is InService")
                return
            elif status in ['Creating', 'Updating']:
                print(f"⟳ Endpoint {endpoint_name} is {status}, waiting...")
                wait_for_endpoint(sagemaker, endpoint_name)
                return
            elif status == 'Failed':
                print(f"✗ Endpoint {endpoint_name} is in Failed state, deleting...")
                sagemaker.delete_endpoint(EndpointName=endpoint_name)
                time.sleep(5)
            
        except ClientError as e:
            if e.response['Error']['Code'] != 'ValidationException':
                raise
        
        # Create endpoint
        print(f"Creating endpoint: {endpoint_name}")
        sagemaker.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=config_name
        )
        print(f"✓ Endpoint creation initiated: {endpoint_name}")
        
        # Wait for endpoint to be in service
        wait_for_endpoint(sagemaker, endpoint_name)
        
    except ClientError as e:
        print(f"✗ Error creating endpoint {endpoint_name}: {e}")
        raise


def wait_for_endpoint(sagemaker, endpoint_name, timeout=1800):
    """Wait for endpoint to reach InService status"""
    print(f"⟳ Waiting for endpoint {endpoint_name} to be InService...")
    print("  This may take 10-15 minutes...")
    
    start_time = time.time()
    last_status = None
    
    while True:
        try:
            response = sagemaker.describe_endpoint(EndpointName=endpoint_name)
            status = response['EndpointStatus']
            
            if status != last_status:
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed}s] Status: {status}")
                last_status = status
            
            if status == 'InService':
                print(f"✓ Endpoint {endpoint_name} is InService")
                return
            elif status == 'Failed':
                failure_reason = response.get('FailureReason', 'Unknown')
                print(f"✗ Endpoint {endpoint_name} failed: {failure_reason}")
                sys.exit(1)
            
            if time.time() - start_time > timeout:
                print(f"✗ Timeout waiting for endpoint {endpoint_name}")
                sys.exit(1)
            
            time.sleep(30)
            
        except ClientError as e:
            print(f"✗ Error checking endpoint status: {e}")
            raise


def main():
    """Main deployment function"""
    print("=" * 60)
    print("Kāraka RAG System - SageMaker Deployment")
    print("=" * 60)
    print()
    
    # Get AWS region
    region = os.environ.get('AWS_REGION', 'us-east-1')
    print(f"AWS Region: {region}")
    print()
    
    # Initialize boto3 clients
    sagemaker = boto3.client('sagemaker', region_name=region)
    
    # Get execution role
    print("Step 1: IAM Role Setup")
    print("-" * 60)
    role_arn = get_execution_role()
    print()
    
    # Deploy Nemotron NIM
    print("Step 2: Deploy Nemotron NIM (llama-3.1-nemotron-nano-8b-v1)")
    print("-" * 60)
    create_model(sagemaker, NEMOTRON_MODEL_NAME, NEMOTRON_IMAGE, role_arn)
    create_endpoint_config(sagemaker, NEMOTRON_ENDPOINT_CONFIG, NEMOTRON_MODEL_NAME, INSTANCE_TYPE)
    create_endpoint(sagemaker, NEMOTRON_ENDPOINT_NAME, NEMOTRON_ENDPOINT_CONFIG)
    print()
    
    # Deploy Embedding NIM
    print("Step 3: Deploy Embedding NIM (nvidia-retrieval-embedding)")
    print("-" * 60)
    create_model(sagemaker, EMBEDDING_MODEL_NAME, EMBEDDING_IMAGE, role_arn)
    create_endpoint_config(sagemaker, EMBEDDING_ENDPOINT_CONFIG, EMBEDDING_MODEL_NAME, INSTANCE_TYPE)
    create_endpoint(sagemaker, EMBEDDING_ENDPOINT_NAME, EMBEDDING_ENDPOINT_CONFIG)
    print()
    
    # Output configuration
    print("=" * 60)
    print("Deployment Complete!")
    print("=" * 60)
    print()
    print("Add these to your .env file:")
    print()
    print(f"SAGEMAKER_NEMOTRON_ENDPOINT={NEMOTRON_ENDPOINT_NAME}")
    print(f"SAGEMAKER_EMBEDDING_ENDPOINT={EMBEDDING_ENDPOINT_NAME}")
    print(f"AWS_REGION={region}")
    print()
    print("Endpoint ARNs:")
    print(f"  Nemotron: arn:aws:sagemaker:{region}:*:endpoint/{NEMOTRON_ENDPOINT_NAME}")
    print(f"  Embedding: arn:aws:sagemaker:{region}:*:endpoint/{EMBEDDING_ENDPOINT_NAME}")
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
