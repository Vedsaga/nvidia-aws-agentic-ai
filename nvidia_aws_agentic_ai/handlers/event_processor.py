import json
import boto3
from typing import Dict, Any


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main event processor - handles incoming events and routes them
    """
    print(f"Processing event: {json.dumps(event)}")
    
    try:
        # Extract event details
        event_type = event.get('detail-type', 'unknown')
        event_source = event.get('source', 'unknown')
        detail = event.get('detail', {})
        
        # Route based on event type
        if event_type == 'Document Upload':
            return handle_document_upload(detail)
        elif event_type == 'Query Request':
            return handle_query_request(detail)
        else:
            print(f"Unknown event type: {event_type}")
            return {'statusCode': 200, 'message': 'Event ignored'}
            
    except Exception as e:
        print(f"Error processing event: {str(e)}")
        raise


def handle_document_upload(detail: Dict[str, Any]) -> Dict[str, Any]:
    """Handle document upload events"""
    # Your document processing logic here
    return {'statusCode': 200, 'message': 'Document upload processed'}


def handle_query_request(detail: Dict[str, Any]) -> Dict[str, Any]:
    """Handle query request events"""
    # Your query processing logic here
    return {'statusCode': 200, 'message': 'Query request processed'}