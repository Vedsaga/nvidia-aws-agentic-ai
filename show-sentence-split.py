#!/usr/bin/env python3
"""
Show sentence splitting output for a job
"""
import requests
import json
import sys

API_BASE = "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod"

def show_sentence_split(job_id):
    """Show how the document was split into sentences"""
    
    # Get job status
    print(f"Fetching job details for: {job_id}\n")
    response = requests.get(f"{API_BASE}/status/{job_id}")
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return
    
    job_data = response.json()
    
    print("=" * 60)
    print("JOB INFORMATION")
    print("=" * 60)
    print(f"Job ID: {job_data.get('job_id')}")
    print(f"Filename: {job_data.get('filename')}")
    print(f"Status: {job_data.get('status')}")
    print(f"Total Sentences: {job_data.get('total_sentences')}")
    print(f"Completed: {job_data.get('completed_sentences')}")
    print(f"LLM Calls: {job_data.get('llm_calls_made')}")
    print()
    
    # Get processing chain to see sentence details
    print("=" * 60)
    print("SENTENCE SPLIT OUTPUT")
    print("=" * 60)
    
    response = requests.get(f"{API_BASE}/processing-chain/{job_id}")
    
    if response.status_code != 200:
        print(f"Error fetching processing chain: {response.status_code}")
        return
    
    chain_data = response.json()
    
    if 'data' not in chain_data or not chain_data['data']:
        print("No processing data available yet.")
        print("\nNote: The document may still be processing.")
        print("Try again in a few seconds.")
        return
    
    # Group by sentence
    sentences = {}
    for log in chain_data['data']:
        sentence_hash = log.get('sentence_hash')
        if sentence_hash and sentence_hash not in sentences:
            sentences[sentence_hash] = {
                'text': log.get('sentence_text', 'N/A'),
                'hash': sentence_hash,
                'stages': []
            }
        if sentence_hash:
            sentences[sentence_hash]['stages'].append(log.get('stage'))
    
    if not sentences:
        print("No sentence data found in processing chain.")
        return
    
    print(f"\nFound {len(sentences)} sentences:\n")
    
    for idx, (hash_val, data) in enumerate(sentences.items(), 1):
        print(f"Sentence {idx}:")
        print(f"  Text: {data['text']}")
        print(f"  Hash: {hash_val[:16]}...")
        print(f"  Processed Stages: {len(data['stages'])}")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 show-sentence-split.py <job_id>")
        print("\nExample:")
        print("  python3 show-sentence-split.py d110a076-d160-464a-854b-8a7a4435e78d")
        sys.exit(1)
    
    job_id = sys.argv[1]
    show_sentence_split(job_id)
