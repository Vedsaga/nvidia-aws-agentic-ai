#!/usr/bin/env python3
import boto3

dynamodb = boto3.client('dynamodb')

# Check specific sentence hashes from test-success
hashes = [
    "91bd286c2c84eb7c865f8356c35b0d01f92b9d5dc1571026fb192762d1b19a83",  # Hanuman carries mountain
    "e619101d0b11ebc3f83e06346713030cff374ba6450d728ba7ea0eedf8600e40"   # Lakshmana fights bravely
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
        print(f"{text[:50]}... | Status: {kg_status}")
    else:
        print(f"Hash {hash_val[:16]}... not found in table")
