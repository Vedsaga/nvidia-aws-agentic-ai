"""Lambda handler for query processing."""

import json
import os
from src.config import Config
from src.graph.neo4j_client import Neo4jClient
from src.utils.nim_client import NIMClient
from src.query.decomposer import QueryDecomposer
from src.query.cypher_generator import CypherGenerator
from src.query.answer_synthesizer import AnswerSynthesizer


config = Config()
neo4j_client = Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password)
nim_client = NIMClient(config.aws_region, config.nemotron_endpoint, config.embedding_endpoint)

decomposer = QueryDecomposer(nim_client)
cypher_generator = CypherGenerator(neo4j_client, config.s3_bucket)
answer_synthesizer = AnswerSynthesizer(nim_client)


def lambda_handler(event, context):
    """
    Handle query requests.
    
    Event format:
    {
        "question": "Who killed Ravana?",
        "min_confidence": 0.5,
        "document_filter": "optional_document_id"
    }
    """
    try:
        # Parse request
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event
        
        question = body.get('question', '')
        min_confidence = body.get('min_confidence', 0.5)
        document_filter = body.get('document_filter')
        
        if not question:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "error": "Question is required"
                })
            }
        
        # Decompose query
        decomposition = decomposer.decompose(question)
        
        # Generate and execute Cypher query
        graph_results = cypher_generator.generate(
            decomposition,
            min_confidence=min_confidence,
            document_filter=document_filter
        )
        
        # Synthesize answer
        answer = answer_synthesizer.synthesize(
            question,
            graph_results,
            decomposition
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "question": question,
                "answer": answer["answer"],
                "sources": answer["sources"],
                "karakas": answer["karakas"],
                "confidence": answer["confidence"],
                "decomposition": decomposition
            })
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": str(e)
            })
        }
