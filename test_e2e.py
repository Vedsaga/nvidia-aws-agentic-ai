#!/usr/bin/env python3
"""
End-to-End Testing Script for Karaka RAG System

Usage:
    python test_e2e.py --mode local     # Test local deployment
    python test_e2e.py --mode server    # Test server deployment
"""

import os
import sys
import json
import time
import base64
import requests
import argparse
from typing import Dict, Any
from dotenv import load_dotenv

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class E2ETestRunner:
    def __init__(self, mode='local'):
        self.mode = mode
        self.load_config()
        self.test_results = []
        
    def load_config(self):
        if self.mode == 'local':
            load_dotenv('.env.local')
            load_dotenv('.env', override=True)
        else:
            load_dotenv('.env.vocareum')
            load_dotenv('.env', override=True)
        
        self.api_url = os.getenv('API_GATEWAY_URL') or os.getenv('API_URL')
        if not self.api_url:
            print(f"{RED}ERROR: API_GATEWAY_URL not set{RESET}")
            sys.exit(1)
        
        print(f"{BLUE}API URL: {self.api_url}{RESET}")
        print(f"{BLUE}Mode: {self.mode}{RESET}\n")
    
    def log_success(self, msg):
        print(f"{GREEN}✓ {msg}{RESET}")
        self.test_results.append(('PASS', msg))
    
    def log_failure(self, msg):
        print(f"{RED}✗ {msg}{RESET}")
        self.test_results.append(('FAIL', msg))
    
    def log_info(self, msg):
        print(f"{BLUE}ℹ {msg}{RESET}")
    
    def upload_document(self, file_path, doc_name):
        self.log_info(f"Uploading {doc_name}...")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        encoded = base64.b64encode(content.encode()).decode()
        
        try:
            response = requests.post(
                f'{self.api_url}/ingest',
                json={'document_name': doc_name, 'content': encoded},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log_success(f"Uploaded: {doc_name}")
                return result
            else:
                self.log_failure(f"Upload failed: {response.status_code}")
                return None
        except Exception as e:
            self.log_failure(f"Upload error: {e}")
            return None
    
    def wait_for_job(self, job_id, timeout=300):
        self.log_info(f"Waiting for job {job_id}...")
        
        start = time.time()
        while time.time() - start < timeout:
            try:
                response = requests.get(
                    f'{self.api_url}/ingest/status/{job_id}',
                    timeout=10
                )
                
                if response.status_code == 200:
                    status = response.json()
                    
                    if status.get('status') == 'completed':
                        self.log_success("Job completed")
                        return status
                    elif status.get('status') == 'failed':
                        self.log_failure("Job failed")
                        return status
                    else:
                        pct = status.get('percentage', 0)
                        print(f"  Progress: {pct:.1f}%", end='\r')
                        time.sleep(2)
            except Exception as e:
                self.log_info(f"Waiting... {e}")
                time.sleep(2)
        
        self.log_failure("Job timeout")
        return None
    
    def test_query(self, question, expected_karaka=None):
        self.log_info(f"Query: {question}")
        
        try:
            response = requests.post(
                f'{self.api_url}/query',
                json={'question': question, 'min_confidence': 0.7},
                headers={'Content-Type': 'application/json'},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', '')
                self.log_success(f"Answer: {answer[:80]}...")
                return result
            else:
                self.log_failure(f"Query failed: {response.status_code}")
                return None
        except Exception as e:
            self.log_failure(f"Query error: {e}")
            return None
    
    def get_graph(self):
        try:
            response = requests.get(f'{self.api_url}/graph', timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                self.log_failure(f"Graph failed: {response.status_code}")
                return None
        except Exception as e:
            self.log_failure(f"Graph error: {e}")
            return None
    
    def verify_graph(self, graph_data):
        self.log_info("Verifying graph...")
        
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        entities = [n for n in nodes if n.get('type') == 'Entity']
        actions = [n for n in nodes if n.get('type') == 'Action']
        
        if entities:
            self.log_success(f"Found {len(entities)} entities")
        else:
            self.log_failure("No entities found")
        
        if actions:
            self.log_success(f"Found {len(actions)} actions")
        else:
            self.log_failure("No actions found")
        
        karaka_types = ['KARTA', 'KARMA', 'KARANA', 'SAMPRADANA', 'ADHIKARANA', 'APADANA']
        karakas = [e for e in edges if e.get('label') in karaka_types]
        
        if karakas:
            self.log_success(f"Found {len(karakas)} Karaka relationships")
        else:
            self.log_failure("No Karaka relationships")
    
    def run_all_tests(self):
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Karaka RAG System - E2E Tests{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        test_dir = 'data'
        ramayana = f'{test_dir}/ramayana_sample.txt'
        mahabharata = f'{test_dir}/mahabharata_sample.txt'
        
        # Test 1: Upload
        print(f"\n{YELLOW}Test 1: Upload Documents{RESET}")
        if os.path.exists(ramayana):
            result = self.upload_document(ramayana, 'ramayana_sample.txt')
            if result:
                self.wait_for_job(result.get('job_id'))
        else:
            self.log_info(f"Skipping: {ramayana} not found")
        
        # Test 2: Graph
        print(f"\n{YELLOW}Test 2: Verify Graph{RESET}")
        graph = self.get_graph()
        if graph:
            self.verify_graph(graph)
        
        # Test 3: Upload second doc
        print(f"\n{YELLOW}Test 3: Upload Second Document{RESET}")
        if os.path.exists(mahabharata):
            result = self.upload_document(mahabharata, 'mahabharata_sample.txt')
            if result:
                self.wait_for_job(result.get('job_id'))
        else:
            self.log_info(f"Skipping: {mahabharata} not found")
        
        # Test 4: Queries
        print(f"\n{YELLOW}Test 4: Test Queries{RESET}")
        queries = [
            ("Who gave bow to Rama?", "KARTA"),
            ("What did Arjuna receive?", "KARMA"),
            ("Where did the battle take place?", "ADHIKARANA")
        ]
        
        for q, k in queries:
            self.test_query(q, k)
            time.sleep(1)
        
        self.print_summary()
    
    def print_summary(self):
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Test Summary{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        passed = sum(1 for s, _ in self.test_results if s == 'PASS')
        failed = sum(1 for s, _ in self.test_results if s == 'FAIL')
        total = len(self.test_results)
        
        print(f"Total: {total}")
        print(f"{GREEN}Passed: {passed}{RESET}")
        print(f"{RED}Failed: {failed}{RESET}\n")
        
        return failed == 0

def main():
    parser = argparse.ArgumentParser(description='E2E tests for Karaka RAG')
    parser.add_argument('--mode', choices=['local', 'server'], default='local',
                       help='Test mode')
    
    args = parser.parse_args()
    
    runner = E2ETestRunner(mode=args.mode)
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
