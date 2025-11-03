import json
import os
import boto3
import requests
import numpy as np

# Boto3 clients
s3_client = boto3.client("s3")

# Environment variables
KG_BUCKET = os.environ["KG_BUCKET"]
EMBED_ENDPOINT = os.environ.get('EMBED_ENDPOINT', 'http://ac5f3892aa1654ccbb5e6e97382f31f8-582704769.us-east-1.elb.amazonaws.com:80')

def lambda_handler(event, context):
    """
    Generate embeddings for text
    Input: {'text': str, 'hash': str, 'job_id': str}
    """
    
    try:
        text = event['text']
        sentence_hash = event['hash']
        
        # Make embedding API call using OpenAI-compatible format
        response = requests.post(
            f"{EMBED_ENDPOINT}/v1/embeddings",
            json={
                'model': 'nvidia/llama-3.2-nv-embedqa-1b-v2',
                'input': text,
                'input_type': 'passage'
            },
            timeout=60
        )
        
        if response.status_code == 200:
            embedding_data = response.json()
            # Extract embedding from OpenAI-compatible response
            embedding_vector = embedding_data['data'][0]['embedding']
            
            # Convert to numpy array and save as .npy file
            np_array = np.array(embedding_vector, dtype=np.float32)
            
            # Save to S3
            s3_client.put_object(
                Bucket=KG_BUCKET,
                Key=f'embeddings/{sentence_hash}.npy',
                Body=np_array.tobytes(),
                ContentType='application/octet-stream'
            )
            
            # Return original event data for next step
            return event
        else:
            raise Exception(f"Embedding API failed: {response.status_code} {response.text}")
            
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return {'status': 'error', 'error': str(e)}
