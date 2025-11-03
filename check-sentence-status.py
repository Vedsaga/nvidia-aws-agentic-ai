#!/usr/bin/env python3
import boto3

dynamodb = boto3.client('dynamodb')

# Check specific sentence hashes from test-final
hashes = [
    "8671235c9ad3dc5fc8e628a9ac313eb3a26a30995374508707dc4a157061375b",  # Arjuna shoots arrow
    "8597772b6639221e5f07cfc8b81241cec45d8b86ee7f44027f3364984fe9f44d"   # Bhima lifts mountain
]

for hash_val in hashes:
    response = dynamodb.get_item(
        TableName='Sentences',
        Key={'sentence_hash': {'S': hash_val}}
    )
    
    if 'Item' in response:
        item = response['Item']
        text = item.get('text', {}).get('S', 'N/A')
        kg_status = item.get('kg_status', {}).get('S', 'N/A')
        print(f"{text[:40]}... | Status: {kg_status}")
    else:
        print(f"Hash {hash_val[:16]}... not found in table")
