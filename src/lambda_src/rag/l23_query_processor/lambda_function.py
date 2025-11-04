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
JOBS_TABLE = os.environ.get('JOBS_TABLE', 'DocumentJobs')
LLM_LAMBDA = os.environ['LLM_CALL_LAMBDA_NAME']
RETRIEVE_LAMBDA = os.environ.get('RETRIEVE_LAMBDA')

ROLE_LABELS = {
    'Agent': 'Agent (Kartā)',
    'Object': 'Object (Karma)',
    'Instrument': 'Instrument (Karaṇa)',
    'Recipient': 'Recipient (Sampradāna)',
    'Source': 'Source (Apādāna)',
    'Location': 'Location (Adhikaraṇa)'
}


def format_edge_label(edge_attrs):
    """Generate human readable label for a KG edge"""
    role = edge_attrs.get('karaka_role')
    if role:
        return ROLE_LABELS.get(role, role)
    return edge_attrs.get('edge_type', 'related')

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

            sentence_text = (
                sent.get('original_sentence', {}).get('S')
                or sent.get('text', {}).get('S', 'Text not available')
            )
            doc_id = sent.get('job_id', {}).get('S', '')
            doc_filename = ''
            if doc_id:
                try:
                    job_resp = dynamodb.get_item(
                        TableName=JOBS_TABLE,
                        Key={'job_id': {'S': doc_id}}
                    )
                    if 'Item' in job_resp:
                        doc_filename = job_resp['Item'].get('filename', {}).get('S', '')
                except Exception as meta_err:
                    print(f"Warning: unable to load job metadata for {doc_id}: {meta_err}")

            kg_snippet = None
            entity_names = []
            relations = []

            # Load graph to extract KG snippet
            try:
                graph_obj = s3.get_object(Bucket=KG_BUCKET, Key=f'graphs/{sent_hash}.gpickle')
                G = pickle.loads(graph_obj['Body'].read())

                kg_nodes = []
                for node_id, attrs in G.nodes(data=True):
                    node_type = attrs.get('node_type', '').lower()
                    if node_type == 'event_instance':
                        display_label = attrs.get('surface_text') or attrs.get('kriya_concept') or node_id
                        display_type = 'EVENT'
                    else:
                        display_label = node_id
                        entity_type = attrs.get('entity_type') or attrs.get('node_type') or 'ENTITY'
                        display_type = entity_type.upper()
                    kg_nodes.append({
                        'id': node_id,
                        'label': display_label,
                        'type': display_type
                    })
                    if node_type != 'event_instance':
                        entity_names.append(display_label)

                def format_edge_label(edge_attrs):
                    role = edge_attrs.get('karaka_role')
                    if not role:
                        return edge_attrs.get('edge_type', 'related')
                    mapping = {
                        'Agent': 'Agent (Kartā)',
                        'Object': 'Object (Karma)',
                        'Instrument': 'Instrument (Karaṇa)',
                        'Recipient': 'Recipient (Sampradāna)',
                        'Source': 'Source (Apādāna)',
                        'Location': 'Location (Adhikaraṇa)'
                    }
                    return mapping.get(role, role)

                kg_edges = []
                for source, target, edge_attrs in G.edges(data=True):
                    label = format_edge_label(edge_attrs)
                    kg_edges.append({
                        'source': source,
                        'target': target,
                        'label': label
                    })
                    relations.append(f"{source}-{label}->{target}")

                kg_snippet = {'nodes': kg_nodes, 'edges': kg_edges}

            except Exception as e:
                print(f"Error loading graph for {sent_hash}: {e}")
                import traceback
                traceback.print_exc()

            references.append({
                'sentence_text': sentence_text,
                'sentence_hash': sent_hash,
                'doc_id': doc_id,
                'doc_filename': doc_filename,
                'llm_calls_for_sentence': None,
                'kg_snippet': kg_snippet
            })

            context_entry = [f"Sentence: {sentence_text}"]
            if entity_names:
                context_entry.append(f"Entities: {', '.join(entity_names)}")
            if relations:
                context_entry.append(f"Relations: {', '.join(relations)}")
            context_parts.append('\n'.join(context_entry))
        
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
        
        return {
            'status': 'completed',
            'query_id': query_id,
            'answer': answer,
            'references': references
        }
        
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
