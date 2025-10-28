"""Lambda handler for query processing."""

import json
import os
import logging
from src.config import Config
from src.graph.neo4j_client import Neo4jClient
from src.utils.nim_client import NIMClient
from src.query.decomposer import QueryDecomposer
from src.query.cypher_generator import CypherGenerator
from src.query.answer_synthesizer import AnswerSynthesizer

logger = logging.getLogger()
logger.setLevel(logging.INFO)

config = Config()
neo4j_client = Neo4jClient(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
nim_client = NIMClient(config.AWS_REGION, config.SAGEMAKER_NEMOTRON_ENDPOINT, config.SAGEMAKER_EMBEDDING_ENDPOINT)

decomposer = QueryDecomposer(nim_client)
cypher_generator = CypherGenerator(config.S3_BUCKET, config.AWS_REGION)
answer_synthesizer = AnswerSynthesizer(nim_client, cypher_generator)


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
        logger.info(f"Received query event: {json.dumps(event)}")
        
        # Parse request
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event
        
        question = body.get('question', '')
        min_confidence = body.get('min_confidence', 0.5)
        document_filter = body.get('document_filter')
        
        logger.info(f"Processing query: question='{question}', min_confidence={min_confidence}, document_filter={document_filter}")
        
        if not question:
            logger.warning("Question is missing from request")
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
        
        # Step 1: Decompose query to identify target Kāraka and constraints
        logger.info("Step 1: Decomposing query")
        decomposition = decomposer.decompose(question)
        logger.info(f"Query decomposition: {json.dumps(decomposition)}")
        
        # Step 2: Generate Cypher query (returns line_number, not sentence text)
        logger.info("Step 2: Generating Cypher query")
        cypher_query = cypher_generator.generate(
            decomposition,
            min_confidence=min_confidence,
            document_filter=document_filter
        )
        logger.info(f"Generated Cypher query: {cypher_query}")
        
        # Step 3: Execute Cypher query against Neo4j
        logger.info("Step 3: Executing Cypher query against Neo4j")
        graph_results = neo4j_client.execute_query(cypher_query)
        logger.info(f"Neo4j returned {len(graph_results)} results")
        
        # Step 4: Synthesize answer (retrieves line text from S3)
        logger.info("Step 4: Synthesizing answer")
        answer = answer_synthesizer.synthesize(
            question,
            graph_results,
            decomposition
        )
        logger.info(f"Answer synthesized with confidence: {answer['confidence']}")
        
        # Return answer with sources (including line_text) and Kāraka annotations
        response = {
            "question": question,
            "answer": answer["answer"],
            "sources": answer["sources"],
            "karakas": answer["karakas"],
            "confidence": answer["confidence"],
            "decomposition": decomposition
        }
        
        logger.info("Query processing completed successfully")
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(response)
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Invalid request",
                "details": str(e)
            })
        }
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Internal server error",
                "details": str(e)
            })
        }
