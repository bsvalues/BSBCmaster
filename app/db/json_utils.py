"""
JSON Utilities for Database Operations

This module provides utilities for handling special data types in JSON serialization,
particularly for database operations that need to convert between SQL and JSON formats.
"""

import decimal
import datetime
import json
from typing import Any, Dict, List, Union

def encode_decimal_datetime(data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Encode Decimal and datetime objects in a dictionary or list of dictionaries to make them JSON serializable.
    
    Args:
        data: Dictionary or list of dictionaries potentially containing Decimal or datetime objects
        
    Returns:
        Dictionary or list of dictionaries with Decimal and datetime objects converted to strings
    """
    if isinstance(data, list):
        return [encode_decimal_datetime(item) for item in data]
    
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        if isinstance(value, decimal.Decimal):
            # Convert Decimal to float for JSON serialization
            result[key] = float(value)
        elif isinstance(value, datetime.datetime):
            # Convert datetime to ISO format string
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            # Recursively process nested dictionaries
            result[key] = encode_decimal_datetime(value)
        elif isinstance(value, list):
            # Recursively process lists of items
            result[key] = [encode_decimal_datetime(item) if isinstance(item, dict) else item for item in value]
        else:
            # Keep other values as they are
            result[key] = value
    
    return result

class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles Decimal and datetime objects.
    
    Use this with json.dumps:
    json.dumps(data, cls=CustomJSONEncoder)
    """
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)

def json_dumps(data: Any) -> str:
    """
    Convert Python object to JSON string with proper handling of Decimal and datetime.
    
    Args:
        data: Python object to serialize
        
    Returns:
        JSON string
    """
    return json.dumps(data, cls=CustomJSONEncoder)

def json_loads(json_str: str) -> Any:
    """
    Parse JSON string to Python object.
    
    Args:
        json_str: JSON string to parse
        
    Returns:
        Python object
    """
    return json.loads(json_str)