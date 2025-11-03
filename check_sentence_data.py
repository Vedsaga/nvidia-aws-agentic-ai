#!/usr/bin/env python3
import boto3
import pickle
import numpy as np

s3 = boto3.client('s3')
bucket = 'knowledge-graph-151534200269-us-east-1'
sent_hash = 'e8e902adacf4c1f83ccfaea24805be62755b766e8075c05588aab02f4384fe5c'

print(f"Checking data for sentence: {sent_hash}")
print()

# Check graph
try:
    graph_obj = s3.get_object(Bucket=bucket, Key=f'graphs/{sent_hash}.gpickle')
    G = pickle.loads(graph_obj['Body'].read())
    
    print(f"✓ Graph exists")
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    print()
    
    print("Node details:")
    for node in G.nodes(data=True):
        print(f"  {node}")
    print()
    
    print("Edge details:")
    for edge in G.edges(data=True):
        print(f"  {edge}")
    print()
    
except Exception as e:
    print(f"✗ Graph error: {e}")
    print()

# Check embedding
try:
    emb_obj = s3.get_object(Bucket=bucket, Key=f'embeddings/{sent_hash}.npy')
    embedding = np.frombuffer(emb_obj['Body'].read(), dtype=np.float32)
    
    print(f"✓ Embedding exists")
    print(f"  Shape: {embedding.shape}")
    print(f"  First 5 values: {embedding[:5]}")
    print()
    
except Exception as e:
    print(f"✗ Embedding error: {e}")
    print()

# Check DynamoDB
dynamodb = boto3.client('dynamodb')
try:
    item = dynamodb.get_item(
        TableName='Sentences',
        Key={'sentence_hash': {'S': sent_hash}}
    )
    
    if 'Item' in item:
        print(f"✓ DynamoDB record exists")
        print(f"  Fields: {list(item['Item'].keys())}")
        print(f"  Data: {item['Item']}")
    else:
        print(f"✗ No DynamoDB record")
        
except Exception as e:
    print(f"✗ DynamoDB error: {e}")
