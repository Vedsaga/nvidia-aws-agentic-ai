#!/usr/bin/env python3
"""
Kāraka RAG System - AWS Server Deployment
Consolidated deployment script with validation and configuration management

Usage:
    python deploy_server.py --env vocareum              # Deploy to Vocareum
    python deploy_server.py --env personal              # Deploy to personal AWS
    python deploy_server.py --env vocareum --destroy    # Cleanup resources
    python deploy_server.py --validate-only             # Only validate configuration
"""

import os
import sys
import json
import time
import boto3
import argparse
import subprocess
from pathlib import Path
from botocore.exceptions import ClientError
from dotenv import load_dotenv, set_key

# Colors for terminal output
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'

def print_header(msg):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}{msg}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")

def print_step(msg):
    print(f"{Colors.GREEN}▶ {msg}{Colors.NC}")

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.NC}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.NC}")

def error_exit(msg):
    print_error(msg)
    sys.exit(1)

################################################################################
# Configuration Validation
################################################################################

class ConfigValidator:
    """Validates AWS credentials and configuration"""
    
    def __init__(self, env_file):
        self.env_file = env_file
        self.config = {}
        self.issues = []
        
    def load_config(self):
        """Load configuration from env file"""
        print_step(f"Loading configuration from {self.env_file}")
        
        if not os.path.exists(self.env_file):
            error_exit(f"Environment file not found: {self.env_file}")
        
        load_dotenv(self.env_file)
        
        # Required AWS credentials
        required_keys = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_REGION'
        ]
        
        for key in required_keys:
            value = os.getenv(key)
            if not value:
                self.issues.append(f"Missing required key: {key}")
            self.config[key] = value
        
        # Optional but recommended
        self.config['AWS_SESSION_TOKEN'] = os.getenv('AWS_SESSION_TOKEN')
        self.config['ACCOUNT_ID'] = os.getenv('ACCOUNT_ID')
        
        print_success(f"Configuration loaded from {self.env_file}")
        
    def validate_aws_credentials(self):
        """Validate AWS credentials"""
        print_step("Validating AWS credentials...")
        
        try:
            sts = boto3.client('sts',
                aws_access_key_id=self.config['AWS_ACCESS_KEY_ID'],
                aws_secret_access_key=self.config['AWS_SECRET_ACCESS_KEY'],
                aws_session_token=self.config.get('AWS_SESSION_TOKEN'),
                region_name=self.config['AWS_REGION']
            )
            
            identity = sts.get_caller_identity()
            account_id = identity['Account']
            arn = identity['Arn']
            
            print_success(f"AWS credentials valid")
            print(f"  Account ID: {account_id}")
            print(f"  ARN: {arn}")
            
            self.config['VERIFIED_ACCOUNT_ID'] = account_id
            self.config['ARN'] = arn
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ExpiredToken':
                self.issues.append("AWS session token has expired")
                print_error("AWS session token has expired")
                print_warning("For Vocareum: Get fresh credentials from 'Cloud access' section")
            else:
                self.issues.append(f"AWS credentials invalid: {error_code}")
                print_error(f"AWS credentials invalid: {error_code}")
            return False
            
        except Exception as e:
            self.issues.append(f"Error validating credentials: {str(e)}")
            print_error(f"Error validating credentials: {str(e)}")
            return False
    
    def check_model_configuration(self):
        """Check if model names and hardware are configured"""
        print_step("Checking model configuration...")
        
        # Model endpoints (will be created during deployment)
        nemotron_endpoint = os.getenv('SAGEMAKER_NEMOTRON_ENDPOINT', 'nemotron-karaka-endpoint')
        embedding_endpoint = os.getenv('SAGEMAKER_EMBEDDING_ENDPOINT', 'embedding-karaka-endpoint')
        
        print_success(f"Nemotron endpoint: {nemotron_endpoint}")
        print_success(f"Embedding endpoint: {embedding_endpoint}")
        
        self.config['SAGEMAKER_NEMOTRON_ENDPOINT'] = nemotron_endpoint
        self.config['SAGEMAKER_EMBEDDING_ENDPOINT'] = embedding_endpoint
        
        # Instance type (hackathon approved)
        instance_type = os.getenv('SAGEMAKER_INSTANCE_TYPE', 'ml.g5.xlarge')
        print_success(f"Instance type: {instance_type}")
        self.config['SAGEMAKER_INSTANCE_TYPE'] = instance_type
        
        return True
    
    def check_existing_resources(self):
        """Check if resources already exist"""
        print_step("Checking existing AWS resources...")
        
        try:
            region = self.config['AWS_REGION']
            
            # Check SageMaker endpoints
            sagemaker = boto3.client('sagemaker', region_name=region)
            
            endpoints_exist = []
            for endpoint_name in [self.config['SAGEMAKER_NEMOTRON_ENDPOINT'], 
                                 self.config['SAGEMAKER_EMBEDDING_ENDPOINT']]:
                try:
                    response = sagemaker.describe_endpoint(EndpointName=endpoint_name)
                    status = response['EndpointStatus']
                    endpoints_exist.append(f"{endpoint_name} ({status})")
                except ClientError:
                    pass
            
            if endpoints_exist:
                print_warning("Existing SageMaker endpoints found:")
                for ep in endpoints_exist:
                    print(f"  • {ep}")
                self.config['HAS_EXISTING_ENDPOINTS'] = True
            else:
                print_success("No existing SageMaker endpoints")
                self.config['HAS_EXISTING_ENDPOINTS'] = False
            
            # Check Lambda functions
            lambda_client = boto3.client('lambda', region_name=region)
            functions_exist = []
            
            for func_name in ['karaka-ingestion-handler', 'karaka-query-handler', 
                            'karaka-graph-handler', 'karaka-status-handler']:
                try:
                    lambda_client.get_function(FunctionName=func_name)
                    functions_exist.append(func_name)
                except ClientError:
                    pass
            
            if functions_exist:
                print_warning(f"Existing Lambda functions: {len(functions_exist)}")
                self.config['HAS_EXISTING_FUNCTIONS'] = True
            else:
                print_success("No existing Lambda functions")
                self.config['HAS_EXISTING_FUNCTIONS'] = False
            
            return True
            
        except Exception as e:
            print_warning(f"Could not check existing resources: {e}")
            return True
    
    def validate(self):
        """Run all validations"""
        print_header("Configuration Validation")
        
        self.load_config()
        
        if not self.validate_aws_credentials():
            return False
        
        self.check_model_configuration()
        self.check_existing_resources()
        
        if self.issues:
            print_error("Validation failed with issues:")
            for issue in self.issues:
                print(f"  • {issue}")
            return False
        
        print_success("All validations passed!")
        return True

################################################################################
# Deployment Manager
################################################################################

class DeploymentManager:
    """Manages AWS resource deployment"""
    
    def __init__(self, config, env_file):
        self.config = config
        self.env_file = env_file
        self.region = config['AWS_REGION']
        self.account_id = config['VERIFIED_ACCOUNT_ID']
        
        # Initialize AWS clients
        session_kwargs = {
            'aws_access_key_id': config['AWS_ACCESS_KEY_ID'],
            'aws_secret_access_key': config['AWS_SECRET_ACCESS_KEY'],
            'region_name': self.region
        }
        if config.get('AWS_SESSION_TOKEN'):
            session_kwargs['aws_session_token'] = config['AWS_SESSION_TOKEN']
        
        self.sagemaker = boto3.client('sagemaker', **session_kwargs)
        self.lambda_client = boto3.client('lambda', **session_kwargs)
        self.s3 = boto3.client('s3', **session_kwargs)
        self.iam = boto3.client('iam', **session_kwargs)
        self.apigw = boto3.client('apigateway', **session_kwargs)
        self.ec2 = boto3.client('ec2', **session_kwargs)
        
    def update_env_file(self, key, value):
        """Update environment file with new value"""
        set_key(self.env_file, key, value)
        print_success(f"Updated {self.env_file}: {key}={value}")
    
    def deploy_sagemaker_endpoints(self):
        """Deploy SageMaker endpoints"""
        print_header("Step 1: Deploy SageMaker Endpoints")
        
        if self.config.get('HAS_EXISTING_ENDPOINTS'):
            print_warning("Endpoints already exist")
            response = input("Override and redeploy? (y/N): ")
            if response.lower() != 'y':
                print_warning("Skipping SageMaker deployment")
                return True
        
        print_step("Deploying SageMaker endpoints...")
        print_warning("This will take 15-20 minutes...")
        
        # Use existing deploy.sh script for SageMaker
        try:
            result = subprocess.run(
                ['bash', 'deploy.sh', '--env', os.path.basename(self.env_file).replace('.env.', ''), 
                 '--sagemaker-only'],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            if result.returncode == 0:
                print_success("SageMaker endpoints deployed")
                return True
            else:
                print_error(f"SageMaker deployment failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print_error("SageMaker deployment timed out")
            return False
        except Exception as e:
            print_error(f"SageMaker deployment error: {e}")
            return False
    
    def setup_s3_bucket(self):
        """Setup S3 bucket"""
        print_header("Step 2: Setup S3 Bucket")
        
        bucket_name = os.getenv('S3_BUCKET')
        if not bucket_name:
            bucket_name = f"karaka-rag-{int(time.time())}"
        
        print_step(f"Checking S3 bucket: {bucket_name}")
        
        try:
            self.s3.head_bucket(Bucket=bucket_name)
            print_success(f"S3 bucket exists: {bucket_name}")
        except ClientError:
            print_step(f"Creating S3 bucket: {bucket_name}")
            try:
                if self.region == 'us-east-1':
                    self.s3.create_bucket(Bucket=bucket_name)
                else:
                    self.s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                print_success(f"S3 bucket created: {bucket_name}")
            except ClientError as e:
                print_error(f"Failed to create S3 bucket: {e}")
                return False
        
        self.update_env_file('S3_BUCKET', bucket_name)
        self.config['S3_BUCKET'] = bucket_name
        return True
    
    def deploy_lambda_functions(self):
        """Deploy Lambda functions"""
        print_header("Step 3: Deploy Lambda Functions")
        
        # Package Lambda
        print_step("Packaging Lambda functions...")
        try:
            result = subprocess.run(
                ['bash', 'infrastructure/package_lambda.sh'],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode != 0:
                print_error(f"Lambda packaging failed: {result.stderr}")
                return False
            print_success("Lambda functions packaged")
        except Exception as e:
            print_error(f"Lambda packaging error: {e}")
            return False
        
        # Upload to S3
        print_step("Uploading Lambda package to S3...")
        try:
            self.s3.upload_file('lambda.zip', self.config['S3_BUCKET'], 'lambda/lambda.zip')
            print_success("Lambda package uploaded")
        except Exception as e:
            print_error(f"Lambda upload failed: {e}")
            return False
        
        # Deploy functions using existing script
        print_step("Deploying Lambda functions...")
        # This is handled by deploy.sh
        print_success("Lambda functions ready for deployment")
        return True
    
    def deploy_api_gateway(self):
        """Deploy API Gateway"""
        print_header("Step 4: Deploy API Gateway")
        
        print_step("Deploying API Gateway...")
        try:
            result = subprocess.run(
                ['python3', 'infrastructure/deploy_api_gateway.py'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print_success("API Gateway deployed")
                
                # Extract API URL from output
                for line in result.stdout.split('\n'):
                    if 'API_GATEWAY_URL=' in line:
                        api_url = line.split('=')[1].strip()
                        self.update_env_file('API_GATEWAY_URL', api_url)
                        self.config['API_GATEWAY_URL'] = api_url
                
                return True
            else:
                print_error(f"API Gateway deployment failed: {result.stderr}")
                return False
                
        except Exception as e:
            print_error(f"API Gateway deployment error: {e}")
            return False
    
    def deploy_neo4j(self):
        """Deploy Neo4j on EC2"""
        print_header("Step 5: Deploy Neo4j Database")
        
        print_step("Deploying Neo4j on EC2...")
        try:
            result = subprocess.run(
                ['bash', 'infrastructure/deploy_neo4j.sh'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print_success("Neo4j deployed")
                
                # Extract Neo4j URI from output
                for line in result.stdout.split('\n'):
                    if 'Bolt URL:' in line:
                        neo4j_uri = line.split('Bolt URL:')[1].strip()
                        self.update_env_file('NEO4J_URI', neo4j_uri)
                        self.config['NEO4J_URI'] = neo4j_uri
                
                return True
            else:
                print_error(f"Neo4j deployment failed: {result.stderr}")
                return False
                
        except Exception as e:
            print_error(f"Neo4j deployment error: {e}")
            return False
    
    def deploy_all(self):
        """Deploy all resources"""
        print_header("Kāraka RAG System - AWS Deployment")
        
        print(f"Environment: {os.path.basename(self.env_file)}")
        print(f"AWS Account: {self.account_id}")
        print(f"Region: {self.region}")
        print()
        
        # Deploy in order
        steps = [
            ("S3 Bucket", self.setup_s3_bucket),
            ("Lambda Functions", self.deploy_lambda_functions),
            ("API Gateway", self.deploy_api_gateway),
            ("Neo4j Database", self.deploy_neo4j),
            ("SageMaker Endpoints", self.deploy_sagemaker_endpoints),
        ]
        
        for step_name, step_func in steps:
            if not step_func():
                print_error(f"Deployment failed at: {step_name}")
                return False
        
        return True
    
    def display_summary(self):
        """Display deployment summary"""
        print_header("Deployment Complete!")
        
        print("Resources Deployed:")
        print(f"  ✓ S3 Bucket: {self.config.get('S3_BUCKET', 'N/A')}")
        print(f"  ✓ API Gateway: {self.config.get('API_GATEWAY_URL', 'N/A')}")
        print(f"  ✓ Neo4j: {self.config.get('NEO4J_URI', 'N/A')}")
        print(f"  ✓ SageMaker Endpoints:")
        print(f"    - Nemotron: {self.config['SAGEMAKER_NEMOTRON_ENDPOINT']}")
        print(f"    - Embedding: {self.config['SAGEMAKER_EMBEDDING_ENDPOINT']}")
        print()
        
        print("Configuration saved to:")
        print(f"  {self.env_file}")
        print()
        
        print("API Endpoints:")
        api_url = self.config.get('API_GATEWAY_URL', '')
        if api_url:
            print(f"  POST {api_url}/ingest")
            print(f"  GET  {api_url}/ingest/status/{{job_id}}")
            print(f"  POST {api_url}/query")
            print(f"  GET  {api_url}/graph")
            print(f"  GET  {api_url}/health")
        print()
        
        print("Next Steps:")
        print("  1. Test the deployment:")
        print(f"     curl {api_url}/health")
        print()
        print("  2. Update frontend .env with API_GATEWAY_URL")
        print()
        print("  3. For judges: All endpoints and credentials are in .env file")
        print()

################################################################################
# Cleanup Manager
################################################################################

class CleanupManager:
    """Manages resource cleanup"""
    
    def __init__(self, config):
        self.config = config
        self.region = config['AWS_REGION']
        
    def cleanup_all(self):
        """Cleanup all AWS resources"""
        print_header("Resource Cleanup")
        
        print("This will DELETE all deployed resources:")
        print("  - SageMaker Endpoints (2)")
        print("  - Lambda Functions (4)")
        print("  - API Gateway")
        print("  - Neo4j EC2 Instance")
        print("  - S3 Bucket (and all data)")
        print()
        
        confirm = input("Type 'DELETE' to confirm: ")
        if confirm != 'DELETE':
            print_warning("Cleanup cancelled")
            return
        
        # Use existing cleanup script
        try:
            result = subprocess.run(
                ['bash', 'deploy.sh', '--cleanup'],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                print_success("All resources cleaned up")
            else:
                print_error(f"Cleanup failed: {result.stderr}")
                
        except Exception as e:
            print_error(f"Cleanup error: {e}")

################################################################################
# Main
################################################################################

def main():
    parser = argparse.ArgumentParser(description='Deploy Kāraka RAG System to AWS')
    parser.add_argument('--env', choices=['vocareum', 'personal'], 
                       help='Environment to deploy to')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate configuration')
    parser.add_argument('--destroy', action='store_true',
                       help='Destroy all resources')
    
    args = parser.parse_args()
    
    # Determine environment file
    if args.env:
        env_file = f".env.{args.env}"
    else:
        # Try to detect from existing .env
        if os.path.exists('.env'):
            env_file = '.env'
        else:
            print_error("No environment specified and .env not found")
            print("Usage: python deploy_server.py --env [vocareum|personal]")
            sys.exit(1)
    
    # Validate configuration
    validator = ConfigValidator(env_file)
    if not validator.validate():
        sys.exit(1)
    
    if args.validate_only:
        print_success("Validation complete!")
        sys.exit(0)
    
    # Handle cleanup
    if args.destroy:
        cleanup = CleanupManager(validator.config)
        cleanup.cleanup_all()
        sys.exit(0)
    
    # Deploy
    deployer = DeploymentManager(validator.config, env_file)
    
    if deployer.deploy_all():
        deployer.display_summary()
        sys.exit(0)
    else:
        print_error("Deployment failed")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDeployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
