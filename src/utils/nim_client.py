"""
NIM Client for interacting with NVIDIA Inference Microservices on AWS SageMaker.
Provides methods for text generation (Nemotron) and embeddings.
"""
import json
import time
import random
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
import logging

from src.config import Config

logger = logging.getLogger(__name__)


class NIMClient:
    """Client for calling NVIDIA NIMs deployed on AWS SageMaker."""
    
    def __init__(
        self,
        nemotron_endpoint: Optional[str] = None,
        embedding_endpoint: Optional[str] = None,
        region_name: Optional[str] = None,
        max_retries: int = 3
    ):
        """
        Initialize NIM client with SageMaker runtime.
        
        Args:
            nemotron_endpoint: SageMaker endpoint name for Nemotron NIM
            embedding_endpoint: SageMaker endpoint name for Embedding NIM
            region_name: AWS region name
            max_retries: Maximum number of retry attempts for throttling
        """
        self.nemotron_endpoint = nemotron_endpoint or Config.SAGEMAKER_NEMOTRON_ENDPOINT
        self.embedding_endpoint = embedding_endpoint or Config.SAGEMAKER_EMBEDDING_ENDPOINT
        self.max_retries = max_retries
        
        # Initialize SageMaker runtime client
        self.sagemaker_runtime = boto3.client(
            'sagemaker-runtime',
            region_name=region_name or Config.AWS_REGION,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY or None
        )
        
        logger.info(f"Initialized NIM client with endpoints: {self.nemotron_endpoint}, {self.embedding_endpoint}")
    
    def call_nemotron(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """
        Call Nemotron NIM for text generation with retry logic.
        
        Args:
            prompt: Input text prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Nucleus sampling parameter
            
        Returns:
            str: Generated text response
            
        Raises:
            Exception: If all retry attempts fail
        """
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
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for text using Embedding NIM with retry logic.
        
        Args:
            text: Input text to embed
            
        Returns:
            List[float]: Embedding vector (typically 768 dimensions)
            
        Raises:
            Exception: If all retry attempts fail
        """
        payload = {
            "input": text
        }
        
        response = self._invoke_with_retry(
            endpoint_name=self.embedding_endpoint,
            payload=payload,
            operation="embedding"
        )
        
        # Parse embedding response
        # Expected format: {"embedding": [0.1, 0.2, ...]} or {"data": [{"embedding": [...]}]}
        if isinstance(response, dict):
            if "embedding" in response:
                return response["embedding"]
            elif "data" in response and len(response["data"]) > 0:
                return response["data"][0].get("embedding", [])
        
        raise ValueError(f"Unexpected embedding response format: {response}")
    
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
