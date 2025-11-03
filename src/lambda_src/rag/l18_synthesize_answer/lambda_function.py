import json
import os
import boto3
import time

# Boto3 clients
s3_client = boto3.client("s3")
dynamodb = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")

# Environment variables
RETRIEVE_LAMBDA = os.environ["RETRIEVE_LAMBDA"]
KG_BUCKET = os.environ["KG_BUCKET"]
LLM_LAMBDA = os.environ["LLM_CALL_LAMBDA_NAME"]
SENTENCES_TABLE = os.environ["SENTENCES_TABLE"]

def lambda_handler(event, context):
    """
    POST /query - Synthesize answer using RAG
    """
    
    try:
        # Parse request body
        body = json.loads(event['body'])
        query = body['query']
        doc_ids = body.get('doc_ids', [])
        
        # Invoke retrieval Lambda
        retrieve_payload = {
            'query': query,
            'doc_ids': doc_ids
        }
        
        retrieve_response = lambda_client.invoke(
            FunctionName=RETRIEVE_LAMBDA,
            Payload=json.dumps(retrieve_payload)
        )
        
        retrieve_result = json.loads(retrieve_response['Payload'].read())
        relevant_hashes = retrieve_result.get('hashes', [])
        
        # Build context from retrieved sentences
        context_parts = []
        references = []
        
        for sentence_hash in relevant_hashes[:3]:  # Top 3 results
            try:
                # Get sentence text from DynamoDB
                sentence_response = dynamodb.get_item(
                    TableName=SENTENCES_TABLE,
                    Key={'sentence_hash': {'S': sentence_hash}}
                )
                
                if 'Item' in sentence_response:
                    sentence_text = sentence_response['Item'].get('text', {}).get('S', '')
                    
                    # Get KG data from S3
                    try:
                        entities_obj = s3_client.get_object(
                            Bucket=KG_BUCKET,
                            Key=f'temp_kg/{sentence_hash}/entities.json'
                        )
                        entities_data = json.loads(entities_obj['Body'].read())
                        
                        events_obj = s3_client.get_object(
                            Bucket=KG_BUCKET,
                            Key=f'temp_kg/{sentence_hash}/events.json'
                        )
                        events_data = json.loads(events_obj['Body'].read())
                        
                        # Build context entry
                        context_entry = f"Text: {sentence_text}\nEntities: {json.dumps(entities_data)}\nEvents: {json.dumps(events_data)}"
                        context_parts.append(context_entry)
                        
                        references.append({
                            'sentence_hash': sentence_hash,
                            'text': sentence_text
                        })
                        
                    except Exception as kg_error:
                        print(f"Error loading KG data for {sentence_hash}: {str(kg_error)}")
                        # Fallback to just text
                        context_parts.append(f"Text: {sentence_text}")
                        references.append({
                            'sentence_hash': sentence_hash,
                            'text': sentence_text
                        })
                        
            except Exception as sentence_error:
                print(f"Error loading sentence {sentence_hash}: {str(sentence_error)}")
                continue
        
        # Format prompt for answer synthesis
        context_text = "\n\n".join(context_parts)
        
        # Invoke LLM for answer synthesis
        llm_payload = {
            'job_id': 'query_' + str(int(time.time())),
            'sentence_hash': 'query',
            'stage': 'RAG_Synthesis',
            'prompt_name': 'answer_synthesizer_prompt.txt',
            'inputs': {
                'QUERY': query,
                'CONTEXT': context_text
            }
        }
        
        llm_response = lambda_client.invoke(
            FunctionName=LLM_LAMBDA,
            Payload=json.dumps(llm_payload)
        )
        
        llm_result = json.loads(llm_response['Payload'].read())
        
        # Format final response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'answer': llm_result.get('generated_text', 'No answer generated'),
                'references': references,
                'query': query
            })
        }
        
    except Exception as e:
        print(f"Error synthesizing answer: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
