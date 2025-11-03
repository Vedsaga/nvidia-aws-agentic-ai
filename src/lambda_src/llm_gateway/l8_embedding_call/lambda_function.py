import json
import os
import boto3
import requests
import numpy as np

# Boto3 clients
s3_client = boto3.client("s3")

# Environment variables
KG_BUCKET = os.environ["KG_BUCKET"]
EMBED_ENDPOINT = "http://your-nvidia-embedding-endpoint-here"  # TODO: Update with actual endpoint

def lambda_handler(event, context):
    """
    Generate embeddings for text
    Input: {'text': str, 'hash': str, 'job_id': str}
    """
    
    try:
        text = event['text']
        sentence_hash = event['hash']
        
        # Make embedding API call
        # TODO: Update with actual NVIDIA embedding API format
        response = requests.post(
            EMBED_ENDPOINT,
            json={'text': text},
            timeout=60
        )
        
        if response.status_code == 200:
            embedding_data = response.json()
            # Assuming the API returns {'embedding': [float, float, ...]}
            embedding_vector = embedding_data.get('embedding', [])
            
            # Convert to numpy array and save as .npy file
            np_array = np.array(embedding_vector, dtype=np.float32)
            
            # Save to S3
            s3_client.put_object(
                Bucket=KG_BUCKET,
                Key=f'embeddings/{sentence_hash}.npy',
                Body=np_array.tobytes(),
                ContentType='application/octet-stream'
            )
            
            return {'status': 'success'}
        else:
            raise Exception(f"Embedding API failed: {response.status_code} {response.text}")
            
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return {'status': 'error', 'error': str(e)}
