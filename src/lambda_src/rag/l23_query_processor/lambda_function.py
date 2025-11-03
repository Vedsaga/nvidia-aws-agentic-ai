import json
import os
import boto3
import pickle

s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')
lambda_client = boto3.client('lambda')

KG_BUCKET = os.environ['KG_BUCKET']
QUERIES_TABLE = os.environ.get('QUERIES_TABLE', 'Queries')
SENTENCES_TABLE = os.environ.get('SENTENCES_TABLE', 'Sentences')
LLM_LAMBDA = os.environ['LLM_CALL_LAMBDA_NAME']
RETRIEVE_LAMBDA = os.environ.get('RETRIEVE_LAMBDA')

def lambda_handler(event, context):
    """Process query: find relevant sentences, build context, generate answer"""
    try:
        query_id = event['query_id']
        question = event['question']
        
        # 1. Use L17 retrieve lambda to get relevant sentences via embeddings
        print(f"Calling retrieve lambda: {RETRIEVE_LAMBDA}")
        retrieve_response = lambda_client.invoke(
            FunctionName=RETRIEVE_LAMBDA,
            Payload=json.dumps({'query': question, 'doc_ids': []})
        )
        
        retrieve_result = json.loads(retrieve_response['Payload'].read())
        print(f"Retrieve result: {retrieve_result}")
        relevant_hashes = retrieve_result.get('hashes', [])[:3]
        print(f"Relevant hashes: {relevant_hashes}")
        
        if not relevant_hashes:
            # Fallback: get any completed sentences
            print("No hashes from retrieve, using fallback")
            sentences = scan_all_sentences()
            relevant_hashes = [s['sentence_hash']['S'] for s in sentences[:3] if s.get('kg_status', {}).get('S') == 'completed']
            print(f"Fallback hashes: {relevant_hashes}")
        
        # 2. Build context with KG from retrieved sentences
        references = []
        context_parts = []
        
        for sent_hash in relevant_hashes:
            print(f"Processing hash: {sent_hash}")
            # Get sentence from DynamoDB
            sent_response = dynamodb.get_item(
                TableName=SENTENCES_TABLE,
                Key={'sentence_hash': {'S': sent_hash}}
            )
            
            if 'Item' not in sent_response:
                print(f"No item found for {sent_hash}")
                continue
                
            sent = sent_response['Item']
            sent_text = sent['sentence_text']['S']
            print(f"Sentence text: {sent_text}")
            
            # Load graph
            try:
                graph_obj = s3.get_object(Bucket=KG_BUCKET, Key=f'graphs/{sent_hash}.gpickle')
                G = pickle.loads(graph_obj['Body'].read())
                
                nodes = [{'id': n, **G.nodes[n]} for n in G.nodes()]
                edges = [{'source': e[0], 'target': e[1], **e[2]} for e in G.edges(data=True)]
                print(f"Found {len(nodes)} nodes, {len(edges)} edges")
                
                references.append({
                    'sentence_text': sent_text,
                    'sentence_hash': sent_hash,
                    'doc_id': sent.get('job_id', {}).get('S', ''),
                    'kg_snippet': {'nodes': nodes, 'edges': edges}
                })
                
                context_parts.append(f"Sentence: {sent_text}\nEntities: {', '.join([n['id'] for n in nodes])}")
            except Exception as e:
                print(f"Error loading graph for {sent_hash}: {e}")
                pass
        
        print(f"Built {len(references)} references")
        
        context = "\n\n".join(context_parts)
        
        # 3. Call LLM to generate answer
        payload = {
            'job_id': query_id,
            'sentence_hash': 'query',
            'stage': 'Answer',
            'prompt_name': 'answer_synthesizer_prompt.txt',
            'inputs': {'QUERY': question, 'CONTEXT': context}
        }
        
        response = lambda_client.invoke(
            FunctionName=LLM_LAMBDA,
            Payload=json.dumps(payload)
        )
        
        llm_output = json.loads(response['Payload'].read())
        answer = extract_answer(llm_output)
        
        # 4. Update DynamoDB with answer
        dynamodb.update_item(
            TableName=QUERIES_TABLE,
            Key={'query_id': {'S': query_id}},
            UpdateExpression='SET #status = :status, answer = :answer, #refs = :refs',
            ExpressionAttributeNames={'#status': 'status', '#refs': 'references'},
            ExpressionAttributeValues={
                ':status': {'S': 'completed'},
                ':answer': {'S': answer},
                ':refs': {'S': json.dumps(references)}
            }
        )
        
        return {'status': 'completed', 'query_id': query_id}
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        dynamodb.update_item(
            TableName=QUERIES_TABLE,
            Key={'query_id': {'S': query_id}},
            UpdateExpression='SET #status = :status, error = :error',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': {'S': 'error'},
                ':error': {'S': str(e)}
            }
        )
        
        return {'status': 'error', 'error': str(e)}

def scan_all_sentences():
    """Scan all sentences from DynamoDB"""
    items = []
    response = dynamodb.scan(TableName=SENTENCES_TABLE, Limit=100)
    items.extend(response.get('Items', []))
    return items

def extract_answer(llm_response):
    """Extract answer from LLM response"""
    try:
        if 'choices' in llm_response:
            return llm_response['choices'][0]['message']['content']
    except:
        pass
    return "Unable to generate answer"
