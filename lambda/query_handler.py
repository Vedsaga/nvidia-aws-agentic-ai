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
    Handle query requests with input validation and security.
    
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
        
        question = body.get('question', '').strip()
        min_confidence = body.get('min_confidence', 0.5)
        document_filter = body.get('document_filter')
        
        # Input validation
        if not question:
            logger.warning("Question is missing from request")
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*')
                },
                "body": json.dumps({
                    "error": "Question is required"
                })
            }
        
        # Validate question length (prevent abuse)
        if len(question) > 500:
            logger.warning(f"Question too long: {len(question)} characters")
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*')
                },
                "body": json.dumps({
                    "error": "Question must be less than 500 characters"
                })
            }
        
        # Validate confidence range
        try:
            min_confidence = float(min_confidence)
            if not 0.0 <= min_confidence <= 1.0:
                raise ValueError("Confidence must be between 0 and 1")
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid confidence value: {min_confidence}")
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*')
                },
                "body": json.dumps({
                    "error": "min_confidence must be a number between 0 and 1"
                })
            }
        
        logger.info(f"Processing query: question='{question}', min_confidence={min_confidence}, document_filter={document_filter}")
        
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
                "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*'),
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY"
            },
            "body": json.dumps(response)
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*')
            },
            "body": json.dumps({
                "error": "Invalid request",
                "message": "Please check your input parameters"
            })
        }
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": os.getenv('ALLOWED_ORIGIN', '*')
            },
            "body": json.dumps({
                "error": "Internal server error",
                "message": "An error occurred while processing your query"
            })
        }
