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
                "required": ["canonical_form", "surface_text", "prayoga", "is_copula"],
                "properties": {
                    "canonical_form": {"type": "string"},
                    "surface_text": {"type": "string"},
                    "prayoga": {"type": "string"},
                    "is_copula": {"type": "boolean"}
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
                "required": ["instance_id", "kriyā_concept", "surface_text", "prayoga", "kāraka_links"],
                "properties": {
                    "instance_id": {"type": "string"},
                    "kriyā_concept": {"type": "string"},
                    "surface_text": {"type": "string"},
                    "prayoga": {"type": "string"},
                    "kāraka_links": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["role", "entity", "reasoning"],
                            "properties": {
                                "role": {"type": "string"},
                                "entity": {"type": "string"},
                                "reasoning": {"type": "string"}
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
