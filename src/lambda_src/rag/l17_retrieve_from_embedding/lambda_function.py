import json
import os
import boto3
import numpy as np

# Boto3 clients
s3_client = boto3.client("s3")
dynamodb = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")

# Environment variables
KG_BUCKET = os.environ["KG_BUCKET"]

def lambda_handler(event, context):
    """
    Retrieve relevant sentences using embedding similarity
    Input: {'query': str, 'doc_ids': [str]}
    Output: {'hashes': [str]}
    """
    
    try:
        query = event['query']
        doc_ids = event.get('doc_ids', [])
        
        # Generate query embedding using l8_embedding_call
        embedding_payload = {
            'text': query,
            'hash': 'query_temp',
            'job_id': 'query'
        }
        
        embedding_response = lambda_client.invoke(
            FunctionName='EmbeddingCall',  # Function name from CDK
            Payload=json.dumps(embedding_payload)
        )
        
        # Get query vector (this is a simplified approach)
        # In production, you'd want to use a proper vector database like FAISS
        
        # List all embedding files in S3
        embeddings_response = s3_client.list_objects_v2(
            Bucket=KG_BUCKET,
            Prefix='embeddings/'
        )
        
        similarities = []
        
        # Calculate similarities (MVP approach - not scalable)
        for obj in embeddings_response.get('Contents', [])[:100]:  # Limit for demo
            try:
                embedding_key = obj['Key']
                sentence_hash = embedding_key.split('/')[-1].replace('.npy', '')
                
                # Load embedding vector
                embedding_obj = s3_client.get_object(Bucket=KG_BUCKET, Key=embedding_key)
                embedding_bytes = embedding_obj['Body'].read()
                embedding_vector = np.frombuffer(embedding_bytes, dtype=np.float32)
                
                # Check if sentence belongs to requested documents
                if doc_ids:
                    sentence_response = dynamodb.get_item(
                        TableName='Sentences',
                        Key={'sentence_hash': {'S': sentence_hash}}
                    )
                    
                    if 'Item' in sentence_response:
                        item = sentence_response['Item']
                        sentence_docs = item.get('document_ids', {}).get('SS', [])
                        if not sentence_docs:
                            sentence_docs = item.get('documents', {}).get('SS', [])  # Legacy fallback
                        if not any(doc_id in sentence_docs for doc_id in doc_ids):
                            continue
                
                # Calculate similarity (placeholder - would use actual query vector)
                # For now, return random selection
                similarities.append({
                    'hash': sentence_hash,
                    'similarity': np.random.random()  # Placeholder
                })
                
            except Exception as e:
                print(f"Error processing embedding {embedding_key}: {str(e)}")
                continue
        
        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        top_hashes = [item['hash'] for item in similarities[:3]]
        
        return {'hashes': top_hashes}
        
    except Exception as e:
        print(f"Error retrieving embeddings: {str(e)}")
        return {'hashes': []}
