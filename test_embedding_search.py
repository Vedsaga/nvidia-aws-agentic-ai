#!/usr/bin/env python3
import boto3
import numpy as np
import json

# Get embedding endpoint
ssm = boto3.client('ssm')
endpoint_name = ssm.get_parameter(Name='/nvidia-aws-agentic-ai/embedding-endpoint')['Parameter']['Value']

# Create embedding for query
runtime = boto3.client('sagemaker-runtime')
query = "Who eats mango?"

response = runtime.invoke_endpoint(
    EndpointName=endpoint_name,
    ContentType='application/json',
    Body=json.dumps({'text': query})
)

query_embedding = np.frombuffer(response['Body'].read(), dtype=np.float32)
print(f"Query embedding shape: {query_embedding.shape}")

# List available embeddings
s3 = boto3.client('s3')
bucket = 'knowledge-graph-151534200269-us-east-1'

try:
    # Try to list embeddings
    response = s3.list_objects_v2(Bucket=bucket, Prefix='embeddings/')
    if 'Contents' in response:
        print(f"\nFound {len(response['Contents'])} embeddings")
        
        # Calculate similarity with each
        similarities = []
        for obj in response['Contents']:
            if obj['Key'].endswith('.npy'):
                sent_hash = obj['Key'].split('/')[-1].replace('.npy', '')
                
                # Download embedding
                emb_obj = s3.get_object(Bucket=bucket, Key=obj['Key'])
                sent_embedding = np.frombuffer(emb_obj['Body'].read(), dtype=np.float32)
                
                # Cosine similarity
                similarity = np.dot(query_embedding, sent_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(sent_embedding)
                )
                
                similarities.append((sent_hash, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        print("\nTop 5 similar sentences:")
        for sent_hash, sim in similarities[:5]:
            print(f"  {sent_hash}: {sim:.4f}")
            
            # Get sentence text from DynamoDB
            dynamodb = boto3.client('dynamodb')
            try:
                item = dynamodb.get_item(
                    TableName='Sentences',
                    Key={'sentence_hash': {'S': sent_hash}}
                )
                if 'Item' in item:
                    text = item['Item'].get('text', {}).get('S', 'N/A')
                    print(f"    Text: {text}")
            except Exception as e:
                print(f"    Error getting text: {e}")
    else:
        print("No embeddings found")
except Exception as e:
    print(f"Error: {e}")
