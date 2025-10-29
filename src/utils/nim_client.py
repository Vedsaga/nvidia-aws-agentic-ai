"""
NIM Client for interacting with NVIDIA Inference Microservices.
Supports both AWS SageMaker and NVIDIA API (build.nvidia.com).
"""
import json
import time
import random
import os
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import boto3, but don't fail if not available
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not available, will use NVIDIA API only")

try:
    from src.config import Config
except ImportError:
    Config = None


class NIMClient:
    """Client for calling NVIDIA NIMs via SageMaker or NVIDIA API."""
    
    def __init__(
        self,
        nemotron_endpoint: Optional[str] = None,
        embedding_endpoint: Optional[str] = None,
        region_name: Optional[str] = None,
        max_retries: int = 3,
        use_nvidia_api: bool = None
    ):
        """
        Initialize NIM client.
        
        Args:
            nemotron_endpoint: SageMaker endpoint or model name
            embedding_endpoint: SageMaker endpoint or model name
            region_name: AWS region name
            max_retries: Maximum retry attempts
            use_nvidia_api: Force use of NVIDIA API instead of SageMaker
        """
        self.max_retries = max_retries
        
        # Determine if we should use NVIDIA API
        self.use_nvidia_api = use_nvidia_api
        if self.use_nvidia_api is None:
            self.use_nvidia_api = os.environ.get('USE_NVIDIA_API', 'false').lower() == 'true'
        
        if self.use_nvidia_api:
            # Use NVIDIA API
            self.nvidia_api_key = os.environ.get('NVIDIA_API_KEY', '')
            self.nvidia_api_base = "https://integrate.api.nvidia.com/v1"
            logger.info("Initialized NIM client with NVIDIA API")
        else:
            # Use SageMaker
            if not BOTO3_AVAILABLE:
                raise ImportError("boto3 required for SageMaker mode")
            
            self.nemotron_endpoint = nemotron_endpoint or (Config.SAGEMAKER_NEMOTRON_ENDPOINT if Config else None)
            self.embedding_endpoint = embedding_endpoint or (Config.SAGEMAKER_EMBEDDING_ENDPOINT if Config else None)
            
            self.sagemaker_runtime = boto3.client(
                'sagemaker-runtime',
                region_name=region_name or (Config.AWS_REGION if Config else 'us-east-1')
            )
            
            logger.info(f"Initialized NIM client with SageMaker endpoints: {self.nemotron_endpoint}, {self.embedding_endpoint}")
    
    def call_nemotron(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """
        Call Nemotron NIM for text generation.
        
        Args:
            prompt: Input text prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            
        Returns:
            str: Generated text response
        """
        if self.use_nvidia_api:
            return self._call_nvidia_api_text(prompt, max_tokens, temperature, top_p)
        else:
            payload = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p
            }
            return self._invoke_with_retry(
                endpoint_name=self.nemotron_endpoint,
                payload=payload,
                operation="text_generation"
            )
    
    def get_embedding(self, text: str, use_cache: bool = True) -> List[float]:
        """
        Get embedding vector for text with optional caching.
        
        Args:
            text: Input text to embed
            use_cache: Whether to use cache (default: True)
            
        Returns:
            List[float]: Embedding vector
        """
        # Try cache first
        if use_cache:
            try:
                from src.utils.cache import embedding_cache
                cached = embedding_cache.get(text)
                if cached is not None:
                    logger.debug(f"Cache hit for embedding: {text[:50]}...")
                    return cached
            except ImportError:
                pass
        
        # Get from API
        if self.use_nvidia_api:
            embedding = self._call_nvidia_api_embedding(text)
        else:
            payload = {"input": text}
            response = self._invoke_with_retry(
                endpoint_name=self.embedding_endpoint,
                payload=payload,
                operation="embedding"
            )
            
            if isinstance(response, dict):
                if "embedding" in response:
                    embedding = response["embedding"]
                elif "data" in response and len(response["data"]) > 0:
                    embedding = response["data"][0].get("embedding", [])
                else:
                    raise ValueError(f"Unexpected embedding response format: {response}")
            else:
                raise ValueError(f"Unexpected embedding response format: {response}")
        
        # Store in cache
        if use_cache:
            try:
                from src.utils.cache import embedding_cache
                embedding_cache.put(text, embedding)
                logger.debug(f"Cached embedding for: {text[:50]}...")
            except ImportError:
                pass
        
        return embedding
    
    def _call_nvidia_api_text(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float
    ) -> str:
        """Call NVIDIA API for text generation."""
        import requests
        
        url = f"{self.nvidia_api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        
        raise ValueError(f"Unexpected API response: {result}")
    
    def _call_nvidia_api_embedding(self, text: str) -> List[float]:
        """Call NVIDIA API for embeddings."""
        import requests
        
        url = f"{self.nvidia_api_base}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "nvidia/nv-embedqa-e5-v5",
            "input": text,
            "input_type": "query"
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        if "data" in result and len(result["data"]) > 0:
            return result["data"][0]["embedding"]
        
        raise ValueError(f"Unexpected API response: {result}")
    
    def _invoke_with_retry(
        self,
        endpoint_name: str,
        payload: Dict[str, Any],
        operation: str
    ) -> Any:
        """
        Invoke SageMaker endpoint with exponential backoff retry logic.
        
        Args:
            endpoint_name: SageMaker endpoint name
            payload: Request payload
            operation: Operation type for logging
            
        Returns:
            Any: Parsed response from endpoint
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Invoking {endpoint_name} for {operation} (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.sagemaker_runtime.invoke_endpoint(
                    EndpointName=endpoint_name,
                    ContentType='application/json',
                    Body=json.dumps(payload)
                )
                
                # Parse response
                response_body = response['Body'].read().decode('utf-8')
                result = json.loads(response_body)
                
                logger.debug(f"Successfully invoked {endpoint_name} for {operation}")
                
                # For text generation, extract the generated text
                if operation == "text_generation":
                    if isinstance(result, dict):
                        # Try common response formats
                        if "generated_text" in result:
                            return result["generated_text"]
                        elif "text" in result:
                            return result["text"]
                        elif "choices" in result and len(result["choices"]) > 0:
                            return result["choices"][0].get("text", "")
                    return result
                
                return result
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                
                if error_code == 'ThrottlingException':
                    last_exception = e
                    
                    if attempt < self.max_retries - 1:
                        # Exponential backoff with jitter
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(
                            f"Throttled on {endpoint_name} for {operation}. "
                            f"Retrying in {wait_time:.2f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Max retries exceeded for {endpoint_name} due to throttling")
                        raise
                else:
                    # Non-throttling error, don't retry
                    logger.error(f"Error invoking {endpoint_name}: {error_code} - {str(e)}")
                    raise
                    
            except Exception as e:
                logger.error(f"Unexpected error invoking {endpoint_name} for {operation}: {str(e)}")
                raise
        
        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        raise Exception(f"Failed to invoke {endpoint_name} after {self.max_retries} attempts")
    
    def batch_get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    def health_check(self) -> Dict[str, bool]:
        """
        Check health of both SageMaker endpoints.
        
        Returns:
            Dict[str, bool]: Health status for each endpoint
        """
        health = {
            "nemotron": False,
            "embedding": False
        }
        
        # Test Nemotron endpoint
        try:
            self.call_nemotron("test", max_tokens=5)
            health["nemotron"] = True
        except Exception as e:
            logger.error(f"Nemotron health check failed: {str(e)}")
        
        # Test Embedding endpoint
        try:
            self.get_embedding("test")
            health["embedding"] = True
        except Exception as e:
            logger.error(f"Embedding health check failed: {str(e)}")
        
        return health
