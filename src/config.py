"""
Configuration module for Kāraka Graph RAG System.
Loads environment variables and provides centralized configuration.
"""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration class for the Kāraka RAG system."""
    
    # AWS Configuration
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID: str = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY: str = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    
    # S3 Configuration
    S3_BUCKET: str = os.getenv('S3_BUCKET', 'karaka-rag-jobs')
    S3_REGION: str = os.getenv('S3_REGION', 'us-east-1')
    
    # SageMaker Endpoints
    SAGEMAKER_NEMOTRON_ENDPOINT: str = os.getenv('SAGEMAKER_NEMOTRON_ENDPOINT', 'nemotron-karaka-endpoint')
    SAGEMAKER_EMBEDDING_ENDPOINT: str = os.getenv('SAGEMAKER_EMBEDDING_ENDPOINT', 'embedding-karaka-endpoint')
    
    # Neo4j Configuration
    NEO4J_URI: str = os.getenv('NEO4J_URI', 'neo4j+s://localhost:7687')
    NEO4J_USERNAME: str = os.getenv('NEO4J_USERNAME', 'neo4j')
    NEO4J_PASSWORD: str = os.getenv('NEO4J_PASSWORD', '')
    NEO4J_DATABASE: str = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    # Kāraka Configuration
    CONFIDENCE_THRESHOLD: float = float(os.getenv('CONFIDENCE_THRESHOLD', '0.8'))
    ENTITY_SIMILARITY_THRESHOLD: float = float(os.getenv('ENTITY_SIMILARITY_THRESHOLD', '0.85'))
    
    # Kāraka Types
    KARAKA_TYPES: List[str] = os.getenv('KARAKA_TYPES', 'KARTA,KARMA,KARANA,SAMPRADANA,ADHIKARANA,APADANA').split(',')
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that required configuration values are set.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        required_fields = [
            ('AWS_REGION', cls.AWS_REGION),
            ('S3_BUCKET', cls.S3_BUCKET),
            ('SAGEMAKER_NEMOTRON_ENDPOINT', cls.SAGEMAKER_NEMOTRON_ENDPOINT),
            ('SAGEMAKER_EMBEDDING_ENDPOINT', cls.SAGEMAKER_EMBEDDING_ENDPOINT),
            ('NEO4J_URI', cls.NEO4J_URI),
            ('NEO4J_USERNAME', cls.NEO4J_USERNAME),
            ('NEO4J_PASSWORD', cls.NEO4J_PASSWORD),
        ]
        
        missing = []
        for field_name, field_value in required_fields:
            if not field_value:
                missing.append(field_name)
        
        if missing:
            print(f"Missing required configuration: {', '.join(missing)}")
            return False
        
        return True
    
    @classmethod
    def get_aws_credentials(cls) -> dict:
        """
        Get AWS credentials as a dictionary.
        
        Returns:
            dict: AWS credentials
        """
        return {
            'region_name': cls.AWS_REGION,
            'aws_access_key_id': cls.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': cls.AWS_SECRET_ACCESS_KEY,
        }
    
    @classmethod
    def get_neo4j_config(cls) -> dict:
        """
        Get Neo4j configuration as a dictionary.
        
        Returns:
            dict: Neo4j connection parameters
        """
        return {
            'uri': cls.NEO4J_URI,
            'username': cls.NEO4J_USERNAME,
            'password': cls.NEO4J_PASSWORD,
            'database': cls.NEO4J_DATABASE,
        }
