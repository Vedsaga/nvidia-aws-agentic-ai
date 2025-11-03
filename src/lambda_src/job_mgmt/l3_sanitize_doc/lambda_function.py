import json
import os
import boto3
import re
import hashlib

# Boto3 clients
s3_client = boto3.client("s3")
dynamodb = boto3.client("dynamodb")
sfn_client = boto3.client("stepfunctions")
lambda_client = boto3.client("lambda")

# Environment variables
JOBS_TABLE = os.environ["JOBS_TABLE"]
VERIFIED_BUCKET = os.environ["VERIFIED_BUCKET"]
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]
LLM_LAMBDA = os.environ["LLM_CALL_LAMBDA_NAME"]
KG_BUCKET = os.environ["KG_BUCKET"]

def lambda_handler(event, context):
    """
    Sanitize document and start Step Functions processing
    """
    
    try:
        # Get input parameters
        job_id = event['job_id']
        s3_key = event['s3_key']
        s3_bucket = event['s3_bucket']
        
        print(f"Sanitizing document: job_id={job_id}, s3_key={s3_key}")
        
        # Read the uploaded file
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        text_content = response['Body'].read().decode('utf-8')
        
        # Split into sentences using LLM-based approach
        sentences = split_document_with_llm(text_content.strip(), job_id)
        
        # Create sentence list with hashes
        sentence_list = []
        for sentence in sentences:
            sentence_hash = hashlib.sha256(sentence.encode()).hexdigest()
            sentence_list.append({
                'text': sentence,
                'hash': sentence_hash,
                'job_id': job_id
            })
        
        # Save sentences to verified bucket
        sentences_s3_key = f'{job_id}/sentences.json'
        s3_client.put_object(
            Bucket=VERIFIED_BUCKET,
            Key=sentences_s3_key,
            Body=json.dumps(sentence_list),
            ContentType='application/json'
        )
        
        # Update job status and sentence count
        dynamodb.update_item(
            TableName=JOBS_TABLE,
            Key={'job_id': {'S': job_id}},
            UpdateExpression='SET #s = :stat, total_sentences = :count',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':stat': {'S': 'processing_kg'},
                ':count': {'N': str(len(sentence_list))}
            }
        )
        
        # Start Step Functions execution
        sfn_input = {
            'job_id': job_id,
            's3_path': sentences_s3_key
        }
        
        sfn_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps(sfn_input)
        )
        
        print(f"Successfully started Step Functions for job {job_id} with {len(sentence_list)} sentences")
        
    except Exception as e:
        print(f"Error in document sanitization: {str(e)}")
        # Update job status to error
        try:
            dynamodb.update_item(
                TableName=JOBS_TABLE,
                Key={'job_id': {'S': job_id}},
                UpdateExpression='SET #s = :stat, error_message = :err',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':stat': {'S': 'error'},
                    ':err': {'S': str(e)}
                }
            )
        except:
            pass
        raise

def split_document_with_llm(text_content, job_id):
    """
    Split document into sentences using LLM-based approach with fallback
    """
    try:
        # Check if text is too long for single LLM call (>4000 chars)
        if len(text_content) > 4000:
            return split_long_document(text_content, job_id)
        
        # Use LLM for sentence splitting
        sentences = call_llm_for_sentence_split(text_content, job_id)
        
        # Validate fidelity - joined sentences should match original
        if sentences and validate_sentence_fidelity(text_content, sentences):
            print(f"LLM sentence splitting successful: {len(sentences)} sentences")
            return sentences
        else:
            print("LLM sentence splitting failed fidelity check, using fallback")
            return fallback_sentence_split(text_content)
            
    except Exception as e:
        print(f"Error in LLM sentence splitting: {str(e)}, using fallback")
        return fallback_sentence_split(text_content)

def split_long_document(text_content, job_id):
    """
    Split long documents into chunks and process each chunk
    """
    # Split by paragraphs first
    paragraphs = text_content.split('\n\n')
    all_sentences = []
    
    for paragraph in paragraphs:
        if paragraph.strip():
            if len(paragraph) <= 4000:
                sentences = call_llm_for_sentence_split(paragraph.strip(), job_id)
                if sentences and validate_sentence_fidelity(paragraph.strip(), sentences):
                    all_sentences.extend(sentences)
                else:
                    all_sentences.extend(fallback_sentence_split(paragraph.strip()))
            else:
                # Chunk very long paragraphs
                chunks = chunk_text_safely(paragraph.strip(), 3500)
                for chunk in chunks:
                    sentences = call_llm_for_sentence_split(chunk, job_id)
                    if sentences and validate_sentence_fidelity(chunk, sentences):
                        all_sentences.extend(sentences)
                    else:
                        all_sentences.extend(fallback_sentence_split(chunk))
    
    return all_sentences

def call_llm_for_sentence_split(text, job_id):
    """
    Call LLM to split text into sentences
    """
    try:
        # Prepare LLM call payload
        payload = {
            'job_id': job_id,
            'sentence_hash': 'sentence_split_' + hashlib.sha256(text.encode()).hexdigest()[:16],
            'stage': 'sentence_split',
            'prompt_name': 'sentence_split_prompt.txt',
            'inputs': {
                'text': text
            }
        }
        
        # Invoke LLM Lambda
        response = lambda_client.invoke(
            FunctionName=LLM_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        # Parse LLM response
        llm_output = json.loads(response['Payload'].read())
        
        if 'choices' in llm_output and len(llm_output['choices']) > 0:
            content = llm_output['choices'][0]['message']['content']
            
            # Parse JSON response
            sentences = parse_sentence_json_response(content)
            return sentences
            
    except Exception as e:
        print(f"LLM call failed: {str(e)}")
        return None
    
    return None

def parse_sentence_json_response(content):
    """
    Parse LLM response to extract sentence array
    """
    try:
        # Remove code blocks if present
        content = re.sub(r"```(?:json)?", "", content)
        
        # Find JSON array
        start = content.find('[')
        end = content.rfind(']')
        
        if start != -1 and end != -1:
            json_str = content[start:end+1]
            sentences = json.loads(json_str)
            
            if isinstance(sentences, list):
                return [s for s in sentences if s.strip()]
                
    except Exception as e:
        print(f"Error parsing sentence JSON: {str(e)}")
    
    return None

def validate_sentence_fidelity(original_text, sentences):
    """
    Validate that joining sentences produces the original text
    """
    if not sentences:
        return False
    
    joined = ''.join(sentences)
    
    # Calculate similarity ratio
    if len(original_text) == 0:
        return len(joined) == 0
    
    # Allow for minor whitespace differences
    original_normalized = re.sub(r'\s+', ' ', original_text.strip())
    joined_normalized = re.sub(r'\s+', ' ', joined.strip())
    
    # Check if they're very similar (>95% match)
    similarity = len(set(original_normalized) & set(joined_normalized)) / len(set(original_normalized))
    
    return similarity > 0.95 and abs(len(original_normalized) - len(joined_normalized)) < 10

def chunk_text_safely(text, max_size):
    """
    Split text at safe boundaries (paragraphs > lines > sentence ends)
    """
    if len(text) <= max_size:
        return [text]
    
    chunks = []
    
    # Try splitting by paragraphs first
    paragraphs = text.split('\n\n')
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk + paragraph) <= max_size:
            current_chunk += paragraph + '\n\n'
        else:
            if current_chunk:
                chunks.append(current_chunk.rstrip())
                current_chunk = paragraph + '\n\n'
            else:
                # Paragraph too long, split by sentences
                sentences = fallback_sentence_split(paragraph)
                temp_chunk = ""
                for sentence in sentences:
                    if len(temp_chunk + sentence) <= max_size:
                        temp_chunk += sentence
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk)
                        temp_chunk = sentence
                if temp_chunk:
                    current_chunk = temp_chunk + '\n\n'
    
    if current_chunk:
        chunks.append(current_chunk.rstrip())
    
    return chunks

def fallback_sentence_split(text):
    """
    Fallback regex-based sentence splitting
    """
    # Enhanced regex that handles abbreviations better
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text.strip())
    
    # Clean up sentences
    cleaned_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:
            # Ensure sentence ends with proper punctuation and space
            if not sentence.endswith(('.', '!', '?')):
                sentence += '.'
            if not sentence.endswith(' '):
                sentence += ' '
            cleaned_sentences.append(sentence)
    
    return cleaned_sentences