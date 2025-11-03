#!/usr/bin/env python3
"""
Test script for manual document processing trigger
This bypasses S3 trigger issues by using API endpoints
"""
import requests
import json
import time

# API Gateway URL from deployment
API_BASE_URL = "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod"

def test_manual_processing():
    print("Testing manual document processing workflow...")
    
    # Step 1: Upload a document (get pre-signed URL)
    print("\n1. Requesting upload URL...")
    upload_response = requests.post(
        f"{API_BASE_URL}/upload",
        json={"filename": "test-manual.txt"},
        headers={"Content-Type": "application/json"}
    )
    
    if upload_response.status_code != 200:
        print(f"Upload request failed: {upload_response.text}")
        return
    
    upload_data = upload_response.json()
    job_id = upload_data["job_id"]
    presigned_url = upload_data["pre_signed_url"]
    
    print(f"Job ID: {job_id}")
    print(f"Upload URL received")
    
    # Step 2: Upload document content to S3
    print("\n2. Uploading document to S3...")
    test_content = "Dr. Smith reviewed the quarterly data. He found several errors in the analysis. The team worked late to fix the issues. Mr. Johnson approved the final report."
    
    s3_response = requests.put(
        presigned_url,
        data=test_content,
        headers={"Content-Type": "text/plain"}
    )
    
    if s3_response.status_code != 200:
        print(f"S3 upload failed: {s3_response.status_code}")
        return
    
    print("Document uploaded to S3 successfully")
    
    # Step 3: Manually trigger processing (bypass S3 trigger)
    print("\n3. Manually triggering processing...")
    trigger_response = requests.post(
        f"{API_BASE_URL}/trigger/{job_id}",
        headers={"Content-Type": "application/json"}
    )
    
    if trigger_response.status_code != 200:
        print(f"Manual trigger failed: {trigger_response.text}")
        return
    
    trigger_data = trigger_response.json()
    print(f"Processing triggered: {trigger_data['message']}")
    
    # Step 4: Check processing status
    print("\n4. Monitoring processing status...")
    for i in range(10):  # Check for up to 50 seconds
        time.sleep(5)
        
        status_response = requests.get(f"{API_BASE_URL}/status/{job_id}")
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"Status check {i+1}: {status_data.get('status', 'unknown')}")
            
            if status_data.get('status') in ['completed', 'error']:
                break
        else:
            print(f"Status check failed: {status_response.status_code}")
    
    print(f"\nManual trigger test completed for job: {job_id}")
    print(f"You can check the full processing chain at: {API_BASE_URL}/processing-chain/{job_id}")

if __name__ == "__main__":
    test_manual_processing()