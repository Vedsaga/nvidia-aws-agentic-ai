import json
import os
import boto3
import pickle
import numpy as np

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
        
        # 1. Get relevant sentences using embedding similarity
        print(f"Finding sentences for: {question}")
        
        # Generate query embedding
        embedding_response = generate_query_embedding(question)
        if embedding_response is None:
            print("Failed to generate query embedding, falling back to keyword search")
            relevant_items = keyword_search(question)
        else:
            query_vector = embedding_response
            relevant_items = embedding_search(query_vector)
        
        relevant_hashes = [h for h, _ in relevant_items]
        print(f"Relevant hashes: {relevant_hashes}")
        
        # 2. Build context with KG from retrieved sentences
        references = []
        context_parts = []
        
        for sent_hash, sent in relevant_items:
            print(f"Processing hash: {sent_hash}")

            sentence_status = sent.get('status', {}).get('S', '') or sent.get('kg_status', {}).get('S', '')
            print(f"Sentence status: {sentence_status}")
            
            # Load graph to get sentence text and KG
            try:
                graph_obj = s3.get_object(Bucket=KG_BUCKET, Key=f'graphs/{sent_hash}.gpickle')
                G = pickle.loads(graph_obj['Body'].read())
                
                # Extract sentence text from graph nodes (all nodes have sentence_text)
                sent_text = ''
                if G.number_of_nodes() > 0:
                    first_node = list(G.nodes(data=True))[0]
                    sent_text = first_node[1].get('sentence_text', '')
                
                print(f"Sentence text from graph: {sent_text}")
                
                nodes = [{'id': n, **G.nodes[n]} for n in G.nodes()]
                edges = [{'source': e[0], 'target': e[1], **e[2]} for e in G.edges(data=True)]
                print(f"Found {len(nodes)} nodes, {len(edges)} edges")
                
                # Extract job_id from graph nodes
                job_id = ''
                if G.number_of_nodes() > 0:
                    first_node = list(G.nodes(data=True))[0]
                    job_id = first_node[1].get('job_id', '')
                
                references.append({
                    'sentence_text': sent_text,
                    'sentence_hash': sent_hash,
                    'doc_id': job_id,
                    'kg_snippet': {'nodes': nodes, 'edges': edges}
                })
                
                # Build context with entities and relationships
                entity_names = [n['id'] for n in nodes]
                relations = [f"{e['source']}-{e.get('relation', 'related')}->{e['target']}" for e in edges]
                
                context_parts.append(
                    f"Sentence: {sent_text}\n"
                    f"Entities: {', '.join(entity_names)}\n"
                    f"Relations: {', '.join(relations)}"
                )
                
            except Exception as e:
                print(f"Error loading graph for {sent_hash}: {e}")
                import traceback
                traceback.print_exc()
                
                # Try to get text from DynamoDB as fallback
                sent_text = (
                    sent.get('original_sentence', {}).get('S')
                    or sent.get('text', {}).get('S', 'Text not available')
                )
                
                references.append({
                    'sentence_text': sent_text,
                    'sentence_hash': sent_hash,
                    'doc_id': sent.get('job_id', {}).get('S', ''),
                    'kg_snippet': None
                })
                context_parts.append(f"Sentence: {sent_text}")
        
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
            UpdateExpression='SET #status = :status, #err = :error',
            ExpressionAttributeNames={'#status': 'status', '#err': 'error'},
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

def generate_query_embedding(query_text):
    """Generate embedding for query"""
    import requests
    
    embed_endpoint = os.environ.get('EMBED_ENDPOINT')
    if not embed_endpoint:
        print("EMBED_ENDPOINT not configured")
        return None
    
    try:
        response = requests.post(
            f"{embed_endpoint}/v1/embeddings",
            json={
                'model': 'nvidia/llama-3.2-nv-embedqa-1b-v2',
                'input': query_text,
                'input_type': 'query'
            },
            timeout=30
        )
        
        if response.status_code == 200:
            embedding_data = response.json()
            return np.array(embedding_data['data'][0]['embedding'], dtype=np.float32)
    except Exception as e:
        print(f"Error generating query embedding: {e}")
    
    return None

def embedding_search(query_vector):
    """Search for similar sentences using embeddings"""
    similarities = []
    
    try:
        # List all embeddings
        response = s3.list_objects_v2(Bucket=KG_BUCKET, Prefix='embeddings/')
        
        for obj in response.get('Contents', []):
            if not obj['Key'].endswith('.npy'):
                continue
                
            sent_hash = obj['Key'].split('/')[-1].replace('.npy', '')
            
            try:
                # Load embedding
                emb_obj = s3.get_object(Bucket=KG_BUCKET, Key=obj['Key'])
                sent_vector = np.frombuffer(emb_obj['Body'].read(), dtype=np.float32)
                
                # Cosine similarity
                similarity = np.dot(query_vector, sent_vector) / (
                    np.linalg.norm(query_vector) * np.linalg.norm(sent_vector)
                )
                
                # Get sentence from DynamoDB
                sent_response = dynamodb.get_item(
                    TableName=SENTENCES_TABLE,
                    Key={'sentence_hash': {'S': sent_hash}}
                )
                
                if 'Item' in sent_response:
                    item = sent_response['Item']
                    status_value = item.get('status', {}).get('S')
                    legacy_status = item.get('kg_status', {}).get('S')
                    if status_value != 'KG_COMPLETE' and legacy_status != 'kg_done':
                        continue
                    similarities.append((similarity, sent_hash, item))
            except Exception as e:
                print(f"Error processing {sent_hash}: {e}")
                continue
        
        # Sort by similarity
        similarities.sort(reverse=True, key=lambda x: x[0])
        return [(h, s) for _, h, s in similarities[:3]]
        
    except Exception as e:
        print(f"Error in embedding search: {e}")
        return []

def keyword_search(question):
    """Fallback keyword search"""
    sentences = scan_all_sentences()
    keywords = question.lower().split()
    scored = []
    
    for sent in sentences:
        status_value = sent.get('status', {}).get('S')
        legacy_status = sent.get('kg_status', {}).get('S')
        if status_value != 'KG_COMPLETE' and legacy_status != 'kg_done':
            continue

        sent_text = sent.get('original_sentence', {}).get('S') or sent.get('text', {}).get('S', '')
        if not sent_text:
            continue
        
        sent_text_lower = sent_text.lower()
        score = sum(1 for kw in keywords if kw in sent_text_lower)
        if score > 0:
            scored.append((score, sent['sentence_hash']['S'], sent))
    
    scored.sort(reverse=True, key=lambda x: x[0])
    return [(h, s) for _, h, s in scored[:3]]

def extract_answer(llm_response):
    """Extract answer from LLM response"""
    try:
        if 'choices' in llm_response:
            return llm_response['choices'][0]['message']['content']
    except:
        pass
    return "Unable to generate answer"
