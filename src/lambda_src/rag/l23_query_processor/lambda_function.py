import json
import os
import boto3
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')
lambda_client = boto3.client('lambda')

KG_BUCKET = os.environ['KG_BUCKET']
QUERIES_TABLE = os.environ.get('QUERIES_TABLE', 'Queries')
SENTENCES_TABLE = os.environ.get('SENTENCES_TABLE', 'Sentences')
LLM_LAMBDA = os.environ['LLM_CALL_LAMBDA_NAME']

model = SentenceTransformer('all-MiniLM-L6-v2')

def lambda_handler(event, context):
    """Process query: find relevant sentences, build context, generate answer"""
    try:
        query_id = event['query_id']
        question = event['question']
        
        # 1. Embed question
        q_embedding = model.encode([question])[0]
        
        # 2. Find top 3 relevant sentences
        sentences = scan_all_sentences()
        scored = []
        
        for sent in sentences:
            sent_hash = sent['sentence_hash']['S']
            try:
                emb_obj = s3.get_object(Bucket=KG_BUCKET, Key=f'embeddings/{sent_hash}.npy')
                s_embedding = np.load(emb_obj['Body'])
                score = np.dot(q_embedding, s_embedding) / (np.linalg.norm(q_embedding) * np.linalg.norm(s_embedding))
                scored.append((score, sent))
            except:
                pass
        
        scored.sort(reverse=True, key=lambda x: x[0])
        top_sentences = scored[:3]
        
        # 3. Build context with KG
        references = []
        context_parts = []
        
        for score, sent in top_sentences:
            sent_hash = sent['sentence_hash']['S']
            sent_text = sent['sentence_text']['S']
            
            # Load graph
            try:
                graph_obj = s3.get_object(Bucket=KG_BUCKET, Key=f'graphs/{sent_hash}.gpickle')
                G = pickle.loads(graph_obj['Body'].read())
                
                nodes = [{'id': n, **G.nodes[n]} for n in G.nodes()]
                edges = [{'source': e[0], 'target': e[1], **e[2]} for e in G.edges(data=True)]
                
                references.append({
                    'sentence_text': sent_text,
                    'sentence_hash': sent_hash,
                    'doc_id': sent.get('job_id', {}).get('S', ''),
                    'kg_snippet': {'nodes': nodes, 'edges': edges}
                })
                
                context_parts.append(f"Sentence: {sent_text}\nEntities: {', '.join([n['id'] for n in nodes])}")
            except:
                pass
        
        context = "\n\n".join(context_parts)
        
        # 4. Call LLM to generate answer
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
        
        # 5. Update DynamoDB
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
