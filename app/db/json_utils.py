"""
JSON Utilities

This module provides utilities for working with JSON data.
"""

import json
import decimal
import datetime
from typing import Any, Dict, List, Optional, Union

class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles Decimal, datetime, and other non-JSON serializable types.
    """
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        elif isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        return super().default(o)

def json_serialize(data: Any) -> str:
    """
    Serialize data to JSON string, handling special types like Decimal.
    
    Args:
        data: Data to serialize
        
    Returns:
        JSON string
    """
    return json.dumps(data, cls=CustomJSONEncoder)

def sanitize_for_json(data: Any) -> Any:
    """
    Sanitize data for JSON serialization.
    
    Args:
        data: Data to sanitize
        
    Returns:
        Sanitized data
    """
    if isinstance(data, decimal.Decimal):
        return float(data)
    elif isinstance(data, (datetime.datetime, datetime.date)):
        return data.isoformat()
    elif isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    elif isinstance(data, dict):
        return {key: sanitize_for_json(value) for key, value in data.items()}
    elif hasattr(data, '__dict__'):
        # Convert objects to dictionaries
        return sanitize_for_json(data.__dict__)
    else:
        return data