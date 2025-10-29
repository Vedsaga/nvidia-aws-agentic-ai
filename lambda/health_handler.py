"""Lambda handler for system health checks and monitoring."""

import json
import os
import logging
from datetime import datetime
from src.config import Config
from src.graph.neo4j_client import Neo4jClient
from src.utils.nim_client import NIMClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

config = Config()


def lambda_handler(event, context):
    """
    Health check endpoint for monitoring system status.
    
    Returns:
        Health status of all components
    """
    try:
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "components": {}
        }
        
        # Check Neo4j connectivity
        try:
            neo4j_client = Neo4jClient(
                config.NEO4J_URI,
                config.NEO4J_USERNAME,
                config.NEO4J_PASSWORD
            )
            neo4j_client.driver.verify_connectivity()
            health_status["components"]["neo4j"] = {
                "status": "healthy",
                "uri": config.NEO4J_URI.split('@')[-1] if '@' in config.NEO4J_URI else config.NEO4J_URI
            }
            neo4j_client.close()
        except Exception as e:
            logger.error(f"Neo4j health check failed: {str(e)}")
            health_status["components"]["neo4j"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check SageMaker endpoints
        try:
            nim_client = NIMClient(
                config.AWS_REGION,
                config.SAGEMAKER_NEMOTRON_ENDPOINT,
                config.SAGEMAKER_EMBEDDING_ENDPOINT
            )
            
            # Test Nemotron endpoint
            try:
                nim_client.call_nemotron("health check", max_tokens=5)
                health_status["components"]["nemotron"] = {
                    "status": "healthy",
                    "endpoint": config.SAGEMAKER_NEMOTRON_ENDPOINT
                }
            except Exception as e:
                logger.error(f"Nemotron health check failed: {str(e)}")
                health_status["components"]["nemotron"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
            
            # Test Embedding endpoint
            try:
                nim_client.get_embedding("health check")
                health_status["components"]["embedding"] = {
                    "status": "healthy",
                    "endpoint": config.SAGEMAKER_EMBEDDING_ENDPOINT
                }
            except Exception as e:
                logger.error(f"Embedding health check failed: {str(e)}")
                health_status["components"]["embedding"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
                
        except Exception as e:
            logger.error(f"SageMaker health check failed: {str(e)}")
            health_status["components"]["sagemaker"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check S3 bucket
        try:
            import boto3
            s3_client = boto3.client('s3', region_name=config.AWS_REGION)
            s3_client.head_bucket(Bucket=config.S3_BUCKET)
            health_status["components"]["s3"] = {
                "status": "healthy",
                "bucket": config.S3_BUCKET
            }
        except Exception as e:
            logger.error(f"S3 health check failed: {str(e)}")
            health_status["components"]["s3"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Add system info
        health_status["system"] = {
            "lambda_function": context.function_name if context else "unknown",
            "memory_limit_mb": context.memory_limit_in_mb if context else "unknown",
            "aws_region": config.AWS_REGION
        }
        
        # Determine HTTP status code
        status_code = 200 if health_status["status"] == "healthy" else 503
        
        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*'),
                "Cache-Control": "no-cache, no-store, must-revalidate"
            },
            "body": json.dumps(health_status, indent=2)
        }
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*')
            },
            "body": json.dumps({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        }
