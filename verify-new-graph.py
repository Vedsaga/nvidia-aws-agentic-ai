#!/usr/bin/env python3
import boto3
import pickle
import networkx as nx

s3 = boto3.client('s3')
bucket = "knowledge-graph-151534200269-us-east-1"

# Download and inspect a graph from test-working
hash_val = "21a938d7efe32b0e9ce42fb8d3b6bc66836d0583c7fe9248297c23da17348670"
key = f"graphs/{hash_val}.gpickle"

print(f"Downloading graph: {key}")
response = s3.get_object(Bucket=bucket, Key=key)
G = pickle.loads(response['Body'].read())

print(f"\n=== Graph for: Draupadi cooks food ===")
print(f"Nodes: {G.number_of_nodes()}")
print(f"Edges: {G.number_of_edges()}")

print(f"\nNode details:")
for node, data in G.nodes(data=True):
    print(f"  - {node}: {data}")

print(f"\nEdge details:")
for source, target, data in G.edges(data=True):
    print(f"  - {source} -> {target}: {data}")

# Check sentence status
dynamodb = boto3.client('dynamodb')
response = dynamodb.get_item(
    TableName='Sentences',
    Key={'sentence_hash': {'S': hash_val}}
)

if 'Item' in response:
    item = response['Item']
    text = item.get('text', {}).get('S', 'N/A')
    kg_status = item.get('kg_status', {}).get('S', 'N/A')
    print(f"\n=== Sentence Status ===")
    print(f"Text: {text}")
    print(f"Status: {kg_status}")
