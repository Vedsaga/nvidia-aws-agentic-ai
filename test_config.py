#!/usr/bin/env python3
"""Simple test script for config module."""
import sys
sys.path.insert(0, '.')

try:
    from src.config import Config
    print("✓ Config module imported successfully")
    print(f"✓ Kāraka types: {Config.KARAKA_TYPES}")
    print(f"✓ Confidence threshold: {Config.CONFIDENCE_THRESHOLD}")
    print(f"✓ Entity similarity threshold: {Config.ENTITY_SIMILARITY_THRESHOLD}")
    print(f"✓ AWS Region: {Config.AWS_REGION}")
    print(f"✓ S3 Bucket: {Config.S3_BUCKET}")
    print(f"✓ SageMaker Nemotron Endpoint: {Config.SAGEMAKER_NEMOTRON_ENDPOINT}")
    print(f"✓ SageMaker Embedding Endpoint: {Config.SAGEMAKER_EMBEDDING_ENDPOINT}")
    print(f"✓ Neo4j URI: {Config.NEO4J_URI}")
    print("\n✓ All configuration loaded successfully!")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
