#!/usr/bin/env python3
"""Deploy SageMaker endpoints for Nemotron and Embedding NIMs."""

import boto3
import time
import sys
from datetime import datetime


def create_endpoint(client, model_name, endpoint_name, instance_type='ml.g5.xlarge'):
    """Create SageMaker endpoint."""
    print(f"Creating endpoint: {endpoint_name}")
    
    # Create endpoint config
    config_name = f"{endpoint_name}-config-{int(time.time())}"
    
    try:
        client.create_endpoint_config(
            EndpointConfigName=config_name,
            ProductionVariants=[{
                'VariantName': 'AllTraffic',
                'ModelName': model_name,
                'InstanceType': instance_type,
                'InitialInstanceCount': 1
            }]
        )
        print(f"Created endpoint config: {config_name}")
    except Exception as e:
        print(f"Error creating endpoint config: {e}")
        return None
    
    # Create endpoint
    try:
        client.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=config_name
        )
        print(f"Creating endpoint {endpoint_name}...")
    except client.exceptions.ResourceInUse:
        print(f"Endpoint {endpoint_name} already exists")
        return endpoint_name
    except Exception as e:
        print(f"Error creating endpoint: {e}")
        return None
    
    # Wait for endpoint
    print("Waiting for endpoint to be InService (this may take 5-10 minutes)...")
    waiter = client.get_waiter('endpoint_in_service')
    
    try:
        waiter.wait(
            EndpointName=endpoint_name,
            WaiterConfig={'Delay': 30, 'MaxAttempts': 40}
        )
        print(f"Endpoint {endpoint_name} is InService")
        return endpoint_name
    except Exception as e:
        print(f"Error waiting for endpoint: {e}")
        return None


def main():
    """Deploy SageMaker endpoints."""
    client = boto3.client('sagemaker')
    
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    
    # Nemotron endpoint
    nemotron_model = "llama-3.1-nemotron-nano-8b-v1"
    nemotron_endpoint = f"nemotron-{timestamp}"
    
    print("\n=== Deploying Nemotron NIM ===")
    print(f"Model: {nemotron_model}")
    
    # Note: Assumes model already exists in SageMaker
    # In production, you would create the model first
    
    result_nemotron = create_endpoint(
        client,
        nemotron_model,
        nemotron_endpoint,
        instance_type='ml.g5.xlarge'
    )
    
    # Embedding endpoint
    embedding_model = "nvidia-retrieval-embedding"
    embedding_endpoint = f"embedding-{timestamp}"
    
    print("\n=== Deploying Embedding NIM ===")
    print(f"Model: {embedding_model}")
    
    result_embedding = create_endpoint(
        client,
        embedding_model,
        embedding_endpoint,
        instance_type='ml.g5.xlarge'
    )
    
    # Output results
    print("\n=== Deployment Summary ===")
    if result_nemotron:
        print(f"Nemotron Endpoint: {result_nemotron}")
        print(f"  Add to .env: NEMOTRON_ENDPOINT={result_nemotron}")
    else:
        print("Nemotron deployment failed")
    
    if result_embedding:
        print(f"Embedding Endpoint: {result_embedding}")
        print(f"  Add to .env: EMBEDDING_ENDPOINT={result_embedding}")
    else:
        print("Embedding deployment failed")
    
    if result_nemotron and result_embedding:
        print("\n✓ All endpoints deployed successfully")
        return 0
    else:
        print("\n✗ Some endpoints failed to deploy")
        return 1


if __name__ == '__main__':
    sys.exit(main())
