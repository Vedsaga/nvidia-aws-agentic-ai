#!/usr/bin/env python3
import boto3
import pickle
import networkx as nx

s3 = boto3.client('s3')
bucket = "knowledge-graph-151534200269-us-east-1"

# Download and inspect a graph
hash_val = "91bd286c2c84eb7c865f8356c35b0d01f92b9d5dc1571026fb192762d1b19a83"
key = f"graphs/{hash_val}.gpickle"

print(f"Downloading graph: {key}")
response = s3.get_object(Bucket=bucket, Key=key)
G = pickle.loads(response['Body'].read())

print(f"\n=== Graph for: Hanuman carries mountain ===")
print(f"Nodes: {G.number_of_nodes()}")
print(f"Edges: {G.number_of_edges()}")

print(f"\nNode details:")
for node, data in G.nodes(data=True):
    print(f"  - {node}: {data}")

print(f"\nEdge details:")
for source, target, data in G.edges(data=True):
    print(f"  - {source} -> {target}: {data}")

# Check embedding
print(f"\n=== Checking embedding ===")
try:
    emb_response = s3.get_object(Bucket=bucket, Key=f"embeddings/{hash_val}.npy")
    emb_size = len(emb_response['Body'].read())
    print(f"Embedding file size: {emb_size} bytes")
    print(f"Vector dimension: {emb_size // 4} (assuming float32)")
except Exception as e:
    print(f"Error: {e}")
