#!/usr/bin/env python3
"""
Test Bedrock availability and models
"""
import boto3
import json
import os

def test_bedrock():
    """Test Bedrock access and list available models"""
    region = os.environ.get('AWS_REGION', 'us-east-1')
    
    print(f"Testing Bedrock in region: {region}")
    print("-" * 60)
    
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        
        # List foundation models
        print("\nAvailable Foundation Models:")
        response = bedrock.list_foundation_models()
        
        for model in response['modelSummaries']:
            model_id = model['modelId']
            model_name = model['modelName']
            provider = model['providerName']
            
            # Filter for text generation models
            if 'TEXT' in model.get('outputModalities', []):
                print(f"  ✓ {provider}: {model_name}")
                print(f"    ID: {model_id}")
        
        # Test a simple inference
        print("\n" + "=" * 60)
        print("Testing Inference with Claude 3 Haiku...")
        print("=" * 60)
        
        test_prompt = "What is 2+2? Answer in one word."
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [{
                "role": "user",
                "content": test_prompt
            }]
        })
        
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=body
        )
        
        result = json.loads(response['body'].read())
        answer = result['content'][0]['text']
        
        print(f"\nPrompt: {test_prompt}")
        print(f"Response: {answer}")
        print("\n✓ Bedrock is working!")
        
        print("\n" + "=" * 60)
        print("Recommended Configuration:")
        print("=" * 60)
        print("\nAdd to your .env file:")
        print("BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0")
        print("BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0")
        print("\nBedrock advantages:")
        print("  ✓ No instance management")
        print("  ✓ Pay per token (within 10K limit)")
        print("  ✓ No marketplace subscription needed")
        print("  ✓ Instant availability")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nBedrock may not be available in this account.")
        print("Falling back to SageMaker deployment...")
        return False

if __name__ == '__main__':
    test_bedrock()
