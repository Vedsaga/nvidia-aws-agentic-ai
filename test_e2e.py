#!/usr/bin/env python3
"""
End-to-End Testing Script for Kāraka RAG System
Tests all aspects of the system including ingestion, querying, and graph visualization
"""

import os
import sys
import json
import time
import base64
import requests
from typing import Dict, List, Any

# Load environment variables
from dotenv import load_dotenv
# Load .env.personal first, then .env (so .env can override if needed)
load_dotenv('.env.personal')
load_dotenv('.env', override=True)

API_BASE_URL = os.getenv('API_GATEWAY_URL')
if not API_BASE_URL:
    # Try alternative environment variable names
    API_BASE_URL = os.getenv('API_URL')
    if not API_BASE_URL:
        print("ERROR: API_GATEWAY_URL not set in .env or .env.personal")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Looking for .env file...")
        sys.exit(1)

print(f"Using API URL: {API_BASE_URL}")

# Test configuration
TEST_DATA_DIR = 'data'
RAMAYANA_FILE = f'{TEST_DATA_DIR}/ramayana_sample.txt'
MAHABHARATA_FILE = f'{TEST_DATA_DIR}/mahabharata_sample.txt'
TEST_QUERIES_FILE = f'{TEST_DATA_DIR}/test_queries.json'

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class E2ETestRunner:
    def __init__(self):
        self.api_url = API_BASE_URL
        self.test_results = []
        self.uploaded_docs = {}
        
    def log_success(self, message: str):
        print(f"{GREEN}✓ {message}{RESET}")
        self.test_results.append(('PASS', message))
    
    def log_failure(self, message: str):
        print(f"{RED}✗ {message}{RESET}")
        self.test_results.append(('FAIL', message))
    
    def log_info(self, message: str):
        print(f"{BLUE}ℹ {message}{RESET}")
    
    def log_warning(self, message: str):
        print(f"{YELLOW}⚠ {message}{RESET}")

    
    def upload_document(self, file_path: str, doc_name: str) -> Dict[str, Any]:
        """Upload a document and return job info"""
        self.log_info(f"Uploading {doc_name}...")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Encode content
        encoded_content = base64.b64encode(content.encode()).decode()
        
        payload = {
            'document_name': doc_name,
            'content': encoded_content
        }
        
        try:
            response = requests.post(
                f'{self.api_url}/ingest',
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log_success(f"Document uploaded: {doc_name} (job_id: {result.get('job_id')})")
                return result
            else:
                self.log_failure(f"Upload failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.log_failure(f"Upload error: {str(e)}")
            return None
    
    def wait_for_job_completion(self, job_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Poll job status until completion"""
        self.log_info(f"Waiting for job {job_id} to complete...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f'{self.api_url}/ingest/status/{job_id}',
                    timeout=10
                )
                
                if response.status_code == 200:
                    status = response.json()
                    
                    if status.get('status') == 'completed':
                        self.log_success(f"Job completed: {status.get('percentage', 0):.1f}%")
                        return status
                    elif status.get('status') == 'failed':
                        self.log_failure(f"Job failed: {status.get('error', 'Unknown error')}")
                        return status
                    else:
                        percentage = status.get('percentage', 0)
                        print(f"  Progress: {percentage:.1f}%", end='\r')
                        time.sleep(2)
                else:
                    self.log_warning(f"Status check failed: {response.status_code}")
                    time.sleep(2)
            except Exception as e:
                self.log_warning(f"Status check error: {str(e)}")
                time.sleep(2)
        
        self.log_failure(f"Job timeout after {timeout}s")
        return None
    
    def verify_job_statistics(self, status: Dict[str, Any], doc_name: str):
        """Verify job completion statistics"""
        stats = status.get('statistics', {})
        success = stats.get('success', 0)
        errors = stats.get('errors', 0)
        skipped = stats.get('skipped', 0)
        
        self.log_info(f"Statistics for {doc_name}:")
        print(f"  Success: {success}, Errors: {errors}, Skipped: {skipped}")
        
        if success > 0:
            self.log_success(f"Successfully processed {success} lines")
        
        if errors > 0:
            self.log_warning(f"Encountered {errors} errors")

    
    def get_graph_data(self) -> Dict[str, Any]:
        """Retrieve graph visualization data"""
        try:
            response = requests.get(
                f'{self.api_url}/graph',
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log_failure(f"Graph retrieval failed: {response.status_code}")
                return None
        except Exception as e:
            self.log_failure(f"Graph retrieval error: {str(e)}")
            return None
    
    def verify_graph_structure(self, graph_data: Dict[str, Any]):
        """Verify graph structure and relationships"""
        self.log_info("Verifying graph structure...")
        
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        # Count node types
        entity_nodes = [n for n in nodes if n.get('type') == 'Entity']
        action_nodes = [n for n in nodes if n.get('type') == 'Action']
        
        self.log_info(f"Graph contains {len(entity_nodes)} entities and {len(action_nodes)} actions")
        
        if len(entity_nodes) > 0:
            self.log_success(f"Found {len(entity_nodes)} Entity nodes")
        else:
            self.log_failure("No Entity nodes found")
        
        if len(action_nodes) > 0:
            self.log_success(f"Found {len(action_nodes)} Action nodes")
        else:
            self.log_failure("No Action nodes found")
        
        # Verify Action nodes have required fields
        for action in action_nodes[:5]:  # Check first 5
            if 'line_number' in action:
                self.log_success(f"Action node has line_number: {action.get('label')}")
            else:
                self.log_failure(f"Action node missing line_number: {action.get('id')}")
            
            # Verify NO sentence text in action nodes
            if 'text' not in action and 'sentence' not in action:
                self.log_success(f"Action node correctly has NO sentence text")
            else:
                self.log_failure(f"Action node incorrectly contains sentence text")
        
        # Verify Entity nodes are reused
        entity_names = [e.get('label') for e in entity_nodes]
        unique_entities = set(entity_names)
        
        if len(unique_entities) < len(entity_names):
            self.log_warning(f"Possible duplicate entities detected")
        else:
            self.log_success(f"All {len(unique_entities)} entities are unique")
        
        # Verify relationship directions (Action -> Entity)
        karaka_types = ['KARTA', 'KARMA', 'KARANA', 'SAMPRADANA', 'ADHIKARANA', 'APADANA']
        karaka_edges = [e for e in edges if e.get('label') in karaka_types]
        
        self.log_info(f"Found {len(karaka_edges)} Kāraka relationships")
        
        if len(karaka_edges) > 0:
            self.log_success(f"Graph has {len(karaka_edges)} Kāraka relationships")
        else:
            self.log_failure("No Kāraka relationships found")
        
        # Verify relationship direction (from Action to Entity)
        for edge in karaka_edges[:5]:  # Check first 5
            from_node = next((n for n in nodes if n.get('id') == edge.get('from')), None)
            to_node = next((n for n in nodes if n.get('id') == edge.get('to')), None)
            
            if from_node and to_node:
                if from_node.get('type') == 'Action' and to_node.get('type') == 'Entity':
                    self.log_success(f"Relationship correctly points FROM Action TO Entity: {edge.get('label')}")
                else:
                    self.log_failure(f"Relationship direction incorrect: {from_node.get('type')} -> {to_node.get('type')}")
        
        # Verify Kāraka types are labeled
        found_karakas = set(e.get('label') for e in karaka_edges)
        self.log_info(f"Found Kāraka types: {', '.join(found_karakas)}")
        
        for karaka in found_karakas:
            if karaka in karaka_types:
                self.log_success(f"Kāraka relationship labeled: {karaka}")

    
    def test_query(self, question: str, expected_karaka: str = None, document_filter: str = None) -> Dict[str, Any]:
        """Test a query and return results"""
        self.log_info(f"Testing query: {question}")
        
        payload = {
            'question': question,
            'min_confidence': 0.7
        }
        
        if document_filter:
            payload['document_filter'] = document_filter
        
        try:
            response = requests.post(
                f'{self.api_url}/query',
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', '')
                sources = result.get('sources', [])
                
                self.log_success(f"Query successful: {answer[:100]}...")
                
                # Verify sources have line_text
                if sources:
                    for source in sources[:3]:
                        if 'text' in source or 'line_text' in source:
                            self.log_success(f"Source includes line text from S3")
                        else:
                            self.log_failure(f"Source missing line text")
                        
                        if 'confidence' in source:
                            self.log_success(f"Source includes confidence: {source.get('confidence')}")
                        
                        if 'document_id' in source or 'document_name' in source:
                            self.log_success(f"Source includes document reference")
                
                # Verify Kāraka information
                karakas = result.get('karakas', {})
                if karakas:
                    target = karakas.get('target_karaka')
                    if target:
                        self.log_success(f"Query identified target Kāraka: {target}")
                        if expected_karaka and target == expected_karaka:
                            self.log_success(f"Target Kāraka matches expected: {expected_karaka}")
                
                return result
            else:
                self.log_failure(f"Query failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.log_failure(f"Query error: {str(e)}")
            return None
    
    def test_multi_verb_lines(self):
        """Test that multi-verb lines create multiple action nodes"""
        self.log_info("Testing multi-verb line handling...")
        
        # Upload a test document with multi-verb lines
        test_content = "She called the team and scheduled a meeting.\nHe arrived early and prepared the room."
        encoded = base64.b64encode(test_content.encode()).decode()
        
        payload = {
            'document_name': 'multi_verb_test.txt',
            'content': encoded
        }
        
        try:
            response = requests.post(
                f'{self.api_url}/ingest',
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('job_id')
                
                # Wait for completion
                status = self.wait_for_job_completion(job_id, timeout=60)
                
                if status and status.get('status') == 'completed':
                    # Check if multiple actions were created
                    results = status.get('results', [])
                    
                    for line_result in results:
                        actions = line_result.get('actions', [])
                        if len(actions) > 1:
                            self.log_success(f"Multi-verb line created {len(actions)} action nodes")
                            
                            # Verify action_sequence
                            for i, action in enumerate(actions):
                                if action.get('action_sequence') == i:
                                    self.log_success(f"Action has correct action_sequence: {i}")
                        elif len(actions) == 1:
                            self.log_info(f"Line created 1 action node")
        except Exception as e:
            self.log_warning(f"Multi-verb test error: {str(e)}")

    
    def test_entity_resolution(self, graph_data: Dict[str, Any]):
        """Test that entities are resolved across documents"""
        self.log_info("Testing entity resolution across documents...")
        
        nodes = graph_data.get('nodes', [])
        entity_nodes = [n for n in nodes if n.get('type') == 'Entity']
        
        # Look for entities that appear in multiple documents
        multi_doc_entities = []
        for entity in entity_nodes:
            doc_ids = entity.get('document_ids', [])
            if len(doc_ids) > 1:
                multi_doc_entities.append(entity)
        
        if multi_doc_entities:
            self.log_success(f"Found {len(multi_doc_entities)} entities appearing in multiple documents")
            for entity in multi_doc_entities[:3]:
                self.log_info(f"  {entity.get('label')} appears in {len(entity.get('document_ids', []))} documents")
        else:
            self.log_info("No entities found in multiple documents (may be expected if documents don't share entities)")
        
        # Check for entities with aliases
        entities_with_aliases = [e for e in entity_nodes if len(e.get('aliases', [])) > 1]
        if entities_with_aliases:
            self.log_success(f"Found {len(entities_with_aliases)} entities with multiple aliases")
            for entity in entities_with_aliases[:3]:
                aliases = entity.get('aliases', [])
                self.log_info(f"  {entity.get('label')} has aliases: {', '.join(aliases[:3])}")
    
    def test_document_filtering(self):
        """Test document filtering in queries"""
        self.log_info("Testing document filtering...")
        
        # Query with document filter
        result = self.test_query(
            "Who gave bow to Rama?",
            document_filter="ramayana"
        )
        
        if result:
            sources = result.get('sources', [])
            if sources:
                # Verify all sources are from the filtered document
                all_from_doc = all(
                    'ramayana' in source.get('document_name', '').lower() or
                    'ramayana' in source.get('document_id', '').lower()
                    for source in sources
                )
                
                if all_from_doc:
                    self.log_success("Document filtering works correctly")
                else:
                    self.log_failure("Document filtering returned results from other documents")
    
    def run_all_tests(self):
        """Run complete end-to-end test suite"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Kāraka RAG System - End-to-End Tests{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        # Test 1: Upload Ramayana
        print(f"\n{YELLOW}Test 1: Upload Ramayana Document{RESET}")
        ramayana_result = self.upload_document(RAMAYANA_FILE, 'ramayana_sample.txt')
        if ramayana_result:
            ramayana_job_id = ramayana_result.get('job_id')
            ramayana_status = self.wait_for_job_completion(ramayana_job_id)
            if ramayana_status:
                self.verify_job_statistics(ramayana_status, 'Ramayana')
                self.uploaded_docs['ramayana'] = ramayana_result.get('document_id')
        
        # Test 2: Verify graph after first upload
        print(f"\n{YELLOW}Test 2: Verify Graph Structure (After Ramayana){RESET}")
        graph_data = self.get_graph_data()
        if graph_data:
            self.verify_graph_structure(graph_data)
        
        # Test 3: Upload Mahabharata
        print(f"\n{YELLOW}Test 3: Upload Mahabharata Document{RESET}")
        mahabharata_result = self.upload_document(MAHABHARATA_FILE, 'mahabharata_sample.txt')
        if mahabharata_result:
            mahabharata_job_id = mahabharata_result.get('job_id')
            mahabharata_status = self.wait_for_job_completion(mahabharata_job_id)
            if mahabharata_status:
                self.verify_job_statistics(mahabharata_status, 'Mahabharata')
                self.uploaded_docs['mahabharata'] = mahabharata_result.get('document_id')
        
        # Test 4: Verify graph expansion
        print(f"\n{YELLOW}Test 4: Verify Graph Expansion (After Both Documents){RESET}")
        graph_data = self.get_graph_data()
        if graph_data:
            self.verify_graph_structure(graph_data)
            self.test_entity_resolution(graph_data)
        
        # Test 5: Test queries from test_queries.json
        print(f"\n{YELLOW}Test 5: Test Queries{RESET}")
        try:
            with open(TEST_QUERIES_FILE, 'r') as f:
                test_queries = json.load(f)
            
            for query_data in test_queries.get('queries', [])[:6]:  # Test first 6
                question = query_data.get('question')
                expected_karaka = query_data.get('expected_karaka')
                doc_filter = query_data.get('document_filter')
                
                self.test_query(question, expected_karaka, doc_filter)
                time.sleep(1)  # Brief pause between queries
        except Exception as e:
            self.log_failure(f"Failed to load test queries: {str(e)}")
        
        # Test 6: Document filtering
        print(f"\n{YELLOW}Test 6: Document Filtering{RESET}")
        self.test_document_filtering()
        
        # Test 7: Multi-verb lines
        print(f"\n{YELLOW}Test 7: Multi-Verb Line Handling{RESET}")
        self.test_multi_verb_lines()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Test Summary{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        passed = sum(1 for status, _ in self.test_results if status == 'PASS')
        failed = sum(1 for status, _ in self.test_results if status == 'FAIL')
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"{GREEN}Passed: {passed}{RESET}")
        print(f"{RED}Failed: {failed}{RESET}")
        
        if failed > 0:
            print(f"\n{RED}Failed Tests:{RESET}")
            for status, message in self.test_results:
                if status == 'FAIL':
                    print(f"  {RED}✗ {message}{RESET}")
        
        print(f"\n{BLUE}{'='*60}{RESET}\n")
        
        return failed == 0

if __name__ == '__main__':
    runner = E2ETestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)
