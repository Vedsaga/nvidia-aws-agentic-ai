import json
import os
import boto3
import pickle
import networkx as nx

# Boto3 clients
s3_client = boto3.client("s3")
dynamodb = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")

# Environment variables
KG_BUCKET = os.environ["KG_BUCKET"]
SENTENCES_TABLE = os.environ.get('SENTENCES_TABLE', 'Sentences')
EMBEDDING_LAMBDA = os.environ.get('EMBEDDING_LAMBDA_NAME', 'EmbeddingCall')

def lambda_handler(event, context):
    """
    Add Karaka edges to NetworkX graph
    Creates simple subject-verb-object relationships
    """
    
    try:
        text = event['text']
        sentence_hash = event['hash']
        job_id = event['job_id']
        
        print(f"Building graph edges for {sentence_hash}")
        
        # Load existing graph with nodes
        graph_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'graphs/{sentence_hash}_nodes.gpickle'
        )
        G = pickle.loads(graph_obj['Body'].read())
        
        # Load events with Karaka relationships
        events_obj = s3_client.get_object(
            Bucket=KG_BUCKET,
            Key=f'temp_kg/{sentence_hash}/events.json'
        )
        events_data = json.loads(events_obj['Body'].read())

        # Fetch sentence metadata for references
        document_ids = []
        try:
            sentence_item = dynamodb.get_item(
                TableName=SENTENCES_TABLE,
                Key={'sentence_hash': {'S': sentence_hash}}
            ).get('Item', {})
            document_ids = sentence_item.get('document_ids', {}).get('SS', [])
            if not document_ids:
                legacy_docs = sentence_item.get('documents', {}).get('SS', [])
                document_ids = legacy_docs or []
        except Exception as meta_err:
            print(f"Warning: unable to load sentence metadata: {meta_err}")
        
        instances = []
        if isinstance(events_data, dict):
            instances = events_data.get('event_instances', [])
        elif isinstance(events_data, list):
            instances = events_data

        # Add event nodes and kāraka edges
        for event_instance in instances:
            if not isinstance(event_instance, dict):
                continue

            instance_id = event_instance.get('instance_id') or event_instance.get('id')
            if not instance_id:
                continue

            event_node_id = f"event:{sentence_hash}:{instance_id}"
            if not G.has_node(event_node_id):
                G.add_node(
                    event_node_id,
                    node_type='event_instance',
                    kriya_concept=event_instance.get('kriyā_concept', ''),
                    surface_text=event_instance.get('surface_text', ''),
                    prayoga=event_instance.get('prayoga', ''),
                    sentence_hash=sentence_hash,
                    job_id=job_id,
                    document_ids=list(document_ids)
                )

            for link in event_instance.get('kāraka_links', []):
                if not isinstance(link, dict):
                    continue

                role = link.get('role', '')
                entity_text = link.get('entity', '')
                if not entity_text:
                    continue

                if not G.has_node(entity_text):
                    G.add_node(
                        entity_text,
                        node_type='entity',
                        sentence_hash=sentence_hash,
                        job_id=job_id,
                        document_ids=list(document_ids)
                    )

                G.add_edge(
                    event_node_id,
                    entity_text,
                    edge_type='karaka',
                    karaka_role=role,
                    reasoning=link.get('reasoning', ''),
                    sentence_hash=sentence_hash,
                    job_id=job_id,
                    document_ids=list(document_ids)
                )
        
        # Serialize complete graph
        graph_bytes = pickle.dumps(G)
        
        # Save to S3
        s3_client.put_object(
            Bucket=KG_BUCKET,
            Key=f'graphs/{sentence_hash}.gpickle',
            Body=graph_bytes,
            ContentType='application/octet-stream'
        )
        
        print(f"Created graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")

        # Kick off embedding persistence so sentence can be retrieved via vector search
        try:
            lambda_client.invoke(
                FunctionName=EMBEDDING_LAMBDA,
                InvocationType='Event',
                Payload=json.dumps({'text': text, 'hash': sentence_hash, 'job_id': job_id})
            )
        except Exception as embed_err:
            print(f"Warning: embedding invocation failed for {sentence_hash}: {embed_err}")
        
        # Update sentence status in DynamoDB
        dynamodb.update_item(
            TableName=SENTENCES_TABLE,
            Key={'sentence_hash': {'S': sentence_hash}},
            UpdateExpression='SET #status = :status, kg_status = :legacy_status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': {'S': 'KG_COMPLETE'},
                ':legacy_status': {'S': 'kg_done'}
            }
        )
        
        # Return original event data
        return event
        
    except Exception as e:
        print(f"Error building graph edges: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}
