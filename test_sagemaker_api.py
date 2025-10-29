#!/usr/bin/env python3
"""
Test SageMaker API to understand what's available
"""
import boto3
import sagemaker
import sys

def test_sagemaker_api():
    """Test what SageMaker APIs are available"""
    print("Testing SageMaker API availability...")
    print("=" * 60)
    
    # Test basic SageMaker client
    try:
        sm_client = boto3.client('sagemaker')
        print("✓ SageMaker client created")
    except Exception as e:
        print(f"✗ SageMaker client error: {e}")
        return
    
    # Test SageMaker session
    try:
        import sagemaker
        session = sagemaker.Session()
        print(f"✓ SageMaker session created")
        print(f"  Region: {session.boto_region_name}")
        print(f"  Default bucket: {session.default_bucket()}")
    except Exception as e:
        print(f"✗ SageMaker session error: {e}")
    
    # Test JumpStart availability
    print("\nTesting JumpStart APIs...")
    print("-" * 40)
    
    try:
        from sagemaker import jumpstart
        print("✓ sagemaker.jumpstart module available")
        
        # Test different JumpStart APIs
        try:
            from sagemaker.jumpstart.model import JumpStartModel
            print("✓ JumpStartModel class available")
        except ImportError as e:
            print(f"✗ JumpStartModel not available: {e}")
        
        try:
            from sagemaker.jumpstart import utils as js_utils
            print("✓ sagemaker.jumpstart.utils available")
            
            # Check what functions are available
            available_functions = [attr for attr in dir(js_utils) if not attr.startswith('_')]
            print(f"  Available functions: {available_functions}")
            
            # Try the function that was failing
            if hasattr(js_utils, 'list_jumpstart_models'):
                print("✓ list_jumpstart_models function exists")
            else:
                print("✗ list_jumpstart_models function NOT found")
                
        except ImportError as e:
            print(f"✗ sagemaker.jumpstart.utils not available: {e}")
            
    except ImportError as e:
        print(f"✗ sagemaker.jumpstart not available: {e}")
    
    # Check SageMaker version
    print(f"\nSageMaker SDK version: {sagemaker.__version__}")
    
    # Test model registry access
    print("\nTesting model registry access...")
    print("-" * 40)
    
    try:
        # List model packages (this should work)
        response = sm_client.list_model_packages(MaxResults=5)
        print(f"✓ Can list model packages: {len(response.get('ModelPackageSummaryList', []))} found")
    except Exception as e:
        print(f"✗ Cannot list model packages: {e}")

if __name__ == '__main__':
    test_sagemaker_api()