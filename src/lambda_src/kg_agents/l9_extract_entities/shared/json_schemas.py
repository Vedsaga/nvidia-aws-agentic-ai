"""
JSON Schema definitions for D1, D2a, D2b outputs
"""

D1_SCHEMA = {
    "type": "object",
    "required": ["entities"],
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["text", "type"],
                "properties": {
                    "text": {"type": "string"},
                    "type": {"type": "string"},
                    "subtype": {"type": "string"}
                }
            }
        }
    }
}

D2A_SCHEMA = {
    "type": "object",
    "required": ["kriyās"],
    "properties": {
        "kriyās": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["surface_text", "lemma"],
                "properties": {
                    "surface_text": {"type": "string"},
                    "lemma": {"type": "string"},
                    "tense": {"type": "string"},
                    "aspect": {"type": "string"}
                }
            }
        }
    }
}

D2B_SCHEMA = {
    "type": "object",
    "required": ["event_instances"],
    "properties": {
        "event_instances": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["event_id", "kriyā", "kāraka_links"],
                "properties": {
                    "event_id": {"type": "string"},
                    "kriyā": {"type": "string"},
                    "kāraka_links": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["kāraka_role", "entity"],
                            "properties": {
                                "kāraka_role": {"type": "string"},
                                "entity": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    }
}


def validate_schema(data, schema):
    """
    Simple schema validation
    Returns: (is_valid, error_message)
    """
    try:
        # Check required fields at top level
        if "required" in schema:
            for field in schema["required"]:
                if field not in data:
                    return False, f"Missing required field: {field}"
        
        # Check properties
        if "properties" in schema:
            for key, prop_schema in schema["properties"].items():
                if key in data:
                    value = data[key]
                    
                    # Check type
                    if "type" in prop_schema:
                        expected_type = prop_schema["type"]
                        if expected_type == "array" and not isinstance(value, list):
                            return False, f"Field '{key}' must be an array"
                        elif expected_type == "object" and not isinstance(value, dict):
                            return False, f"Field '{key}' must be an object"
                        elif expected_type == "string" and not isinstance(value, str):
                            return False, f"Field '{key}' must be a string"
                        elif expected_type == "number" and not isinstance(value, (int, float)):
                            return False, f"Field '{key}' must be a number"
                    
                    # Check array items
                    if expected_type == "array" and "items" in prop_schema:
                        item_schema = prop_schema["items"]
                        for i, item in enumerate(value):
                            is_valid, error = validate_schema(item, item_schema)
                            if not is_valid:
                                return False, f"Array item {i} in '{key}': {error}"
        
        return True, None
    except Exception as e:
        return False, f"Validation error: {str(e)}"
