"""
Fidelity validation utilities for GSSR
Checks that all extracted text exists in the original sentence
"""


def validate_d1_fidelity(entities_json, sentence):
    """
    Check all entity.text exists in sentence
    Returns: (is_valid, errors_list)
    """
    errors = []
    entities = entities_json.get('entities', [])
    
    for entity in entities:
        text = entity.get('text', '')
        if not text:
            errors.append("Empty entity text found")
            continue
            
        if text.lower() not in sentence.lower():
            errors.append(f"Entity '{text}' not found in sentence")
        elif text not in sentence:
            errors.append(f"Warning: Case mismatch for entity '{text}'")
    
    return len(errors) == 0, errors


def validate_d2a_fidelity(kriyas_json, sentence):
    """
    Check all kriya.surface_text exists in sentence
    Returns: (is_valid, errors_list)
    """
    errors = []
    kriyas = kriyas_json.get('kriyās', [])
    
    for kriya in kriyas:
        text = kriya.get('surface_text', '')
        if not text:
            errors.append("Empty kriya surface_text found")
            continue
            
        if text.lower() not in sentence.lower():
            errors.append(f"Kriya '{text}' not found in sentence")
        elif text not in sentence:
            errors.append(f"Warning: Case mismatch for kriya '{text}'")
    
    return len(errors) == 0, errors


def validate_d2b_fidelity(events_json, sentence, entities_json):
    """
    Check all entity references in kāraka_links exist in INPUT ENTITIES
    Returns: (is_valid, errors_list)
    """
    errors = []
    
    # Build list of valid entity texts from D1 output
    entity_texts = [e.get('text', '') for e in entities_json.get('entities', [])]
    
    events = events_json.get('event_instances', [])
    for event in events:
        event_id = event.get('event_id', 'unknown')
        
        # Check kriya reference
        kriya = event.get('kriyā', '')
        if not kriya:
            errors.append(f"Event {event_id}: Empty kriyā reference")
        
        # Check kāraka links
        for link in event.get('kāraka_links', []):
            entity = link.get('entity', '')
            if not entity:
                errors.append(f"Event {event_id}: Empty entity in kāraka link")
                continue
                
            if entity not in entity_texts:
                errors.append(f"Event {event_id}: Entity '{entity}' not in D1 output")
    
    return len(errors) == 0, errors
