import json
import os
import boto3
import requests
import numpy as np

# Boto3 clients
s3_client = boto3.client("s3")

# Environment variables
KG_BUCKET = os.environ["KG_BUCKET"]
EMBED_ENDPOINT = os.environ.get('EMBED_ENDPOINT', '')
NVIDIA_API_KEY = os.environ.get('NVIDIA_MODEL_EMBADDING', '')

# Determine if using local EKS or NVIDIA cloud
USE_NVIDIA_CLOUD = not EMBED_ENDPOINT or EMBED_ENDPOINT == 'https://integrate.api.nvidia.com'
if USE_NVIDIA_CLOUD:
    EMBED_ENDPOINT = 'https://integrate.api.nvidia.com'
    if not NVIDIA_API_KEY:
        raise ValueError("NVIDIA_MODEL_EMBADDING environment variable required for NVIDIA cloud endpoint")

def lambda_handler(event, context):
    """
    Generate embeddings for text.
    Input: {'text': str, 'hash': str, 'job_id': str, 'store': bool?, 'return_vector': bool?}
    """

    try:
        text = event['text']
        sentence_hash = event['hash']
        store_embedding = event.get('store', True)
        return_vector = event.get('return_vector', False)

        # Make embedding API call using OpenAI-compatible format
        headers = {'Content-Type': 'application/json'}
        if USE_NVIDIA_CLOUD:
            headers['Authorization'] = f'Bearer {NVIDIA_API_KEY}'

        response = requests.post(
            f"{EMBED_ENDPOINT}/v1/embeddings",
            json={
                'model': 'nvidia/llama-3.2-nv-embedqa-1b-v2',
                'input': text,
                'input_type': 'passage'
            },
            headers=headers,
            timeout=60
        )

        if response.status_code == 200:
            embedding_data = response.json()
            # Extract embedding from OpenAI-compatible response
            embedding_vector = embedding_data['data'][0]['embedding']

            # Convert to numpy array for storage and optional return
            np_array = np.array(embedding_vector, dtype=np.float32)

            if store_embedding:
                s3_client.put_object(
                    Bucket=KG_BUCKET,
                    Key=f'embeddings/{sentence_hash}.npy',
                    Body=np_array.tobytes(),
                    ContentType='application/octet-stream'
                )

            result = dict(event)
            if return_vector:
                # Use list to keep response JSON serializable
                result['embedding'] = np_array.tolist()
            return result
        else:
            raise Exception(f"Embedding API failed: {response.status_code} {response.text}")

    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return {'status': 'error', 'error': str(e)}
