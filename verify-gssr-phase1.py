#!/usr/bin/env python3
"""Verify GSSR Phase 1 Implementation"""

import boto3
import json
import os
from datetime import datetime

dynamodb = boto3.client('dynamodb', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

SENTENCES_TABLE = 'Sentences'
LLM_LOG_TABLE = 'LLMCallLog'

print("=== GSSR Phase 1 Verification ===\n")

# 1. Check Sentences table schema
print("1. Checking Sentences table schema...")
try:
    response = dynamodb.describe_table(TableName=SENTENCES_TABLE)
    attrs = {attr['AttributeName']: attr['AttributeType'] 
             for attr in response['Table']['AttributeDefinitions']}
    print(f"   ✓ Table exists: {SENTENCES_TABLE}")
    print(f"   Attributes: {list(attrs.keys())}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Check for GSSR fields by scanning a recent item
try:
    scan_response = dynamodb.scan(
        TableName=SENTENCES_TABLE,
        Limit=1
    )
    if scan_response['Items']:
        item = scan_response['Items'][0]
        gssr_fields = ['d1_attempts', 'd2a_attempts', 'd2b_attempts', 
                       'best_score', 'needs_review', 'failure_reason']
        found_fields = [f for f in gssr_fields if f in item]
        print(f"   GSSR fields found: {found_fields}")
        if len(found_fields) == len(gssr_fields):
            print("   ✓ All GSSR fields present")
        else:
            missing = set(gssr_fields) - set(found_fields)
            print(f"   ⚠ Missing fields: {missing}")
    else:
        print("   ⚠ No items in table to check schema")
except Exception as e:
    print(f"   ✗ Error scanning: {e}")

print()

# 2. Check LLMCallLog table schema
print("2. Checking LLMCallLog table schema...")
try:
    response = dynamodb.describe_table(TableName=LLM_LOG_TABLE)
    print(f"   ✓ Table exists: {LLM_LOG_TABLE}")
    
    # Check for enhanced fields
    scan_response = dynamodb.scan(
        TableName=LLM_LOG_TABLE,
        Limit=1
    )
    if scan_response['Items']:
        item = scan_response['Items'][0]
        enhanced_fields = ['pipeline_stage', 'temperature', 'attempt_number', 
                          'generation_index', 'raw_request', 'raw_response',
                          'extracted_json', 'extracted_reasoning']
        found_fields = [f for f in enhanced_fields if f in item]
        print(f"   Enhanced fields found: {found_fields}")
        if len(found_fields) == len(enhanced_fields):
            print("   ✓ All enhanced fields present")
        else:
            missing = set(enhanced_fields) - set(found_fields)
            print(f"   ⚠ Missing fields: {missing}")
    else:
        print("   ⚠ No items in table to check schema")
except Exception as e:
    print(f"   ✗ Error: {e}")

print()

# 3. Check for shared utilities
print("3. Checking shared utilities...")
utils = [
    'src/lambda_src/shared/json_schemas.py',
    'src/lambda_src/shared/fidelity_validator.py',
    'src/lambda_src/shared/gssr_utils.py'
]
for util in utils:
    if os.path.exists(util):
        print(f"   ✓ {util}")
        # Check content
        with open(util) as f:
            content = f.read()
            if 'def ' in content:
                funcs = [line.split('def ')[1].split('(')[0] 
                        for line in content.split('\n') if line.strip().startswith('def ')]
                print(f"      Functions: {', '.join(funcs)}")
    else:
        print(f"   ✗ Missing: {util}")

print()

# 4. Check scorer lambda
print("4. Checking scorer lambda...")
scorer_path = 'src/lambda_src/kg_agents/l24_score_extractions/lambda_function.py'
if os.path.exists(scorer_path):
    print(f"   ✓ {scorer_path}")
    with open(scorer_path) as f:
        content = f.read()
        if 'scorer.txt' in content:
            print("   ✓ Uses scorer.txt prompt")
        if 'temperature' in content:
            print("   ✓ Accepts temperature parameter")
else:
    print(f"   ✗ Missing: {scorer_path}")

print()

# 5. Check extraction lambdas for GSSR
print("5. Checking extraction lambdas for GSSR implementation...")
extraction_lambdas = [
    'src/lambda_src/kg_agents/l9_extract_entities/lambda_function.py',
    'src/lambda_src/kg_agents/l10_extract_kriya/lambda_function.py',
    'src/lambda_src/kg_agents/l11_build_events/lambda_function.py'
]

for lambda_path in extraction_lambdas:
    if os.path.exists(lambda_path):
        print(f"   Checking {lambda_path.split('/')[-2]}...")
        with open(lambda_path) as f:
            content = f.read()
            checks = {
                'Generate 3 JSONs': 'range(3)' in content or 'for i in range(3)' in content,
                'Fidelity check': 'fidelity' in content.lower(),
                'Consensus check': 'consensus' in content.lower(),
                'Scorer call': 'call_scorer' in content or 'SCORER_LAMBDA' in content,
                'Temperature 0.6': '0.6' in content,
                'Retry logic': 'attempts' in content.lower()
            }
            for check, passed in checks.items():
                status = "✓" if passed else "✗"
                print(f"      {status} {check}")
    else:
        print(f"   ✗ Missing: {lambda_path}")

print()

# 6. Check LLM gateway for temperature support
print("6. Checking LLM gateway...")
llm_path = 'src/lambda_src/llm_gateway/l7_llm_call/lambda_function.py'
if os.path.exists(llm_path):
    print(f"   ✓ {llm_path}")
    with open(llm_path) as f:
        content = f.read()
        checks = {
            'Accepts temperature': 'temperature' in content,
            'Reads from event': "event.get('temperature'" in content,
            'Logs raw request': 'raw_request' in content,
            'Logs raw response': 'raw_response' in content,
            'Logs attempt_number': 'attempt_number' in content,
            'Logs generation_index': 'generation_index' in content
        }
        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"      {status} {check}")
else:
    print(f"   ✗ Missing: {llm_path}")

print()
print("=== Verification Complete ===")
