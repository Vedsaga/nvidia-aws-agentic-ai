import json
import os
import boto3
import time
import pickle

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
                    item = sentence_response['Item']
                    sentence_text = item.get('sentence_text', {}).get('S', '')
                    job_id = item.get('job_id', {}).get('S', '')
                    llm_calls = int(item.get('llm_calls_made', {}).get('N', '0'))
                    
                    # Get KG graph from S3
                    try:
                        graph_obj = s3_client.get_object(
                            Bucket=KG_BUCKET,
                            Key=f'graphs/{sentence_hash}.gpickle'
                        )
                        G = pickle.loads(graph_obj['Body'].read())
                        
                        # Build KG snippet
                        nodes = []
                        for node_id in G.nodes():
                            node_data = G.nodes[node_id]
                            nodes.append({
                                'id': node_id,
                                'label': node_id,
                                'type': node_data.get('node_type', 'entity').upper()
                            })
                        
                        edges = []
                        for source, target, edge_data in G.edges(data=True):
                            relation = edge_data.get('relation', '')
                            karaka_role = edge_data.get('karaka_role', '')
                            label = f"{karaka_role}" if karaka_role else relation
                            edges.append({
                                'source': source,
                                'target': target,
                                'label': label
                            })
                        
                        # Build context entry
                        entities_str = ', '.join([n['id'] for n in nodes])
                        relations_str = ', '.join([f"{e['source']} --[{e['label']}]--> {e['target']}" for e in edges])
                        context_entry = f"Sentence: {sentence_text}\nEntities: {entities_str}\nRelations: {relations_str}"
                        context_parts.append(context_entry)
                        
                        references.append({
                            'sentence_text': sentence_text,
                            'sentence_hash': sentence_hash,
                            'doc_id': job_id,
                            'llm_calls_for_sentence': llm_calls,
                            'kg_snippet': {
                                'nodes': nodes,
                                'edges': edges
                            }
                        })
                        
                    except Exception as kg_error:
                        print(f"Error loading KG data for {sentence_hash}: {str(kg_error)}")
                        # Fallback to just text
                        context_parts.append(f"Sentence: {sentence_text}")
                        references.append({
                            'sentence_text': sentence_text,
                            'sentence_hash': sentence_hash,
                            'doc_id': job_id,
                            'llm_calls_for_sentence': llm_calls
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
        
        # Extract answer from LLM response
        answer = "No answer generated"
        if 'choices' in llm_result:
            answer = llm_result['choices'][0]['message']['content']
        elif 'generated_text' in llm_result:
            answer = llm_result['generated_text']
        
        # Format final response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'answer': answer,
                'references': references
            })
        }
        
    except Exception as e:
        print(f"Error synthesizing answer: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
