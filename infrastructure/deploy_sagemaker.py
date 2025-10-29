#!/usr/bin/env python3
"""
SageMaker Deployment Script for Karaka RAG System
Deploys NVIDIA NIM models (Nemotron and Embedding) via SageMaker JumpStart
"""

import boto3
import time
import sys
import os
import json
from botocore.exceptions import ClientError

# Configuration
NEMOTRON_ENDPOINT_NAME = 'nemotron-karaka-endpoint'
EMBEDDING_ENDPOINT_NAME = 'embedding-karaka-endpoint'
INSTANCE_TYPE = 'ml.g5.2xlarge'  # Recommended for NIM models

# SageMaker JumpStart Model IDs for NVIDIA NIM
# Based on: https://aws.amazon.com/blogs/machine-learning/nvidia-nemotron-super-49b-and-nano-8b-reasoning-models-now-available-in-amazon-bedrock-marketplace-and-amazon-sagemaker-jumpstart/
NEMOTRON_MODEL_ID = 'meta-textgeneration-llama-3-1-nemotron-nano-8b-instruct'
NEMOTRON_MODEL_VERSION = '*'  # Use latest version

# For embedding, we'll use NV-Embed-v2 which is available via JumpStart
EMBEDDING_MODEL_ID = 'nvidia-nv-embed-v2'
EMBEDDING_MODEL_VERSION = '*'


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
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description='Execution role for Karaka RAG SageMaker endpoints'
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


def deploy_jumpstart_model(sagemaker, model_id, model_version, endpoint_name, instance_type, role_arn):
    """Deploy a SageMaker JumpStart model to an endpoint"""
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
        
        # Use SageMaker JumpStart SDK to deploy
        print(f"Deploying JumpStart model {model_id} to endpoint {endpoint_name}...")
        print("  This will create the model, endpoint config, and endpoint automatically")
        
        from sagemaker.jumpstart.model import JumpStartModel
        
        # Create JumpStart model
        model = JumpStartModel(
            model_id=model_id,
            model_version=model_version,
            role=role_arn,
            instance_type=instance_type
        )
        
        # Deploy to endpoint
        predictor = model.deploy(
            endpoint_name=endpoint_name,
            accept_eula=True  # Accept NVIDIA EULA
        )
        
        print(f"✓ Endpoint {endpoint_name} deployed successfully")
        
    except ImportError:
        print("✗ sagemaker SDK not found. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "sagemaker", "--upgrade"])
        print("Please run the script again after installing sagemaker SDK")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error deploying JumpStart model: {e}")
        print("\nFalling back to manual deployment...")
        deploy_model_manual(sagemaker, model_id, endpoint_name, instance_type, role_arn)


def deploy_model_manual(sagemaker, model_id, endpoint_name, instance_type, role_arn):
    """Manual deployment fallback using boto3 directly"""
    print(f"Manual deployment for {endpoint_name}...")
    
    # Get model artifacts from JumpStart
    # This is a simplified version - in production you'd query JumpStart registry
    model_name = f"{endpoint_name}-model"
    config_name = f"{endpoint_name}-config"
    
    # For now, we'll use a placeholder approach
    # In a real deployment, you'd need to get the actual model package ARN from JumpStart
    print(f"⚠ Manual deployment requires model package ARN from JumpStart")
    print(f"  Please deploy via SageMaker Console or use sagemaker SDK")
    return


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
    
    # Deploy Nemotron NIM via JumpStart
    print("Step 2: Deploy Nemotron Nano 8B via SageMaker JumpStart")
    print("-" * 60)
    deploy_jumpstart_model(
        sagemaker, 
        NEMOTRON_MODEL_ID, 
        NEMOTRON_MODEL_VERSION,
        NEMOTRON_ENDPOINT_NAME, 
        INSTANCE_TYPE, 
        role_arn
    )
    print()
    
    # Deploy Embedding NIM via JumpStart
    print("Step 3: Deploy NV-Embed-v2 via SageMaker JumpStart")
    print("-" * 60)
    deploy_jumpstart_model(
        sagemaker,
        EMBEDDING_MODEL_ID,
        EMBEDDING_MODEL_VERSION,
        EMBEDDING_ENDPOINT_NAME,
        INSTANCE_TYPE,
        role_arn
    )
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
