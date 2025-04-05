"""
This module provides data validation utilities for the API.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQL injection patterns to detect
SQL_INJECTION_PATTERNS = [
    r'(?i)\b(DROP|DELETE|UPDATE|INSERT|ALTER)\b.*\b(TABLE|DATABASE|SCHEMA|VIEW|INDEX|USER)\b',
    r'(?i);\s*\b(DROP|DELETE|UPDATE|INSERT|ALTER)\b',
    r'(?i)--',
    r'(?i)\/\*.*\*\/',
    r'(?i)\bUNION\b.+\bSELECT\b',
    r'(?i)\bOR\b.+\b=\b.+\b--',
    r'(?i)\bEXEC\b.+\bsp_\w+\b',
    r'(?i)\bXP_\w+\b',
]

# Keywords for dangerous operations
DANGEROUS_KEYWORDS = {
    'write_operations': [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE', 
        'GRANT', 'REVOKE', 'SET'
    ],
    'system_operations': [
        'SHUTDOWN', 'RESTART', 'KILL', 'XP_CMDSHELL', 'SP_CONFIGURE', 'SP_EXECUTESQL',
        'LOAD_FILE', 'OUTFILE', 'DUMPFILE', 'UTL_FILE', 'UTL_HTTP', 'DBMS_'
    ],
    'information_disclosure': [
        'VERSION()', 'USER()', 'DATABASE()', 'SCHEMA()', 'BENCHMARK',
        'PG_SLEEP', 'SLEEP', 'CURRENT_USER', 'SYSTEM_USER', 'HOST_NAME',
        'pg_', 'information_schema', 'sys.', 'mysql.'
    ]
}


def validate_query(query: str, security_level: str = "medium") -> Dict[str, Any]:
    """
    Validate a SQL query for security concerns.
    
    Args:
        query: SQL query to validate
        security_level: Security level ('high', 'medium', 'low', 'none')
        
    Returns:
        Dictionary containing validation result:
            - is_safe: Boolean indicating whether the query is safe
            - reason: Reason for failure if not safe
    """
    query = query.strip()
    
    # Skip validation for 'none' security level
    if security_level == "none":
        return {"is_safe": True}
    
    # Check for basic SQL injection patterns (all security levels)
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, query):
            reason = f"Query contains potential SQL injection pattern: {pattern}"
            logger.warning(f"SQL validation failed: {reason}")
            return {"is_safe": False, "reason": reason}
    
    # Check for write operations (medium and high security)
    if security_level in ["medium", "high"]:
        for keyword in DANGEROUS_KEYWORDS["write_operations"]:
            if re.search(rf'\b{keyword}\b', query, re.IGNORECASE):
                reason = f"Query contains write operation: {keyword}"
                logger.warning(f"SQL validation failed: {reason}")
                return {"is_safe": False, "reason": reason}
    
    # Check for system operations and information disclosure (high security only)
    if security_level == "high":
        # System operations
        for keyword in DANGEROUS_KEYWORDS["system_operations"]:
            if re.search(rf'\b{keyword}\b', query, re.IGNORECASE):
                reason = f"Query contains system operation: {keyword}"
                logger.warning(f"SQL validation failed: {reason}")
                return {"is_safe": False, "reason": reason}
        
        # Information disclosure
        for keyword in DANGEROUS_KEYWORDS["information_disclosure"]:
            if re.search(rf'\b{keyword}\b', query, re.IGNORECASE):
                reason = f"Query contains potential information disclosure: {keyword}"
                logger.warning(f"SQL validation failed: {reason}")
                return {"is_safe": False, "reason": reason}
    
    # Check query structure for common issues (all security levels)
    # 1. No query provided
    if not query:
        return {"is_safe": False, "reason": "Empty query provided"}
    
    # 2. Simple validation that the query looks like a SELECT statement
    if not query.lstrip().upper().startswith("SELECT"):
        reason = "Query must start with SELECT"
        logger.warning(f"SQL validation failed: {reason}")
        return {"is_safe": False, "reason": reason}
    
    # All checks passed
    return {"is_safe": True}


def validate_query_parameters(params: Union[List[Any], Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate query parameters for security concerns.
    
    Args:
        params: Query parameters (list or dict)
        
    Returns:
        Dictionary containing validation result:
            - is_valid: Boolean indicating whether the parameters are valid
            - reason: Reason for failure if not valid
    """
    if params is None:
        return {"is_valid": True}
    
    # Check parameter types
    if not isinstance(params, (list, dict)):
        return {
            "is_valid": False,
            "reason": f"Parameters must be a list or dictionary, got {type(params).__name__}"
        }
    
    # For dictionary parameters
    if isinstance(params, dict):
        # Check all parameter names
        for key in params.keys():
            # Only allow alphanumeric and underscore in parameter names
            if not re.match(r'^[a-zA-Z0-9_]+$', str(key)):
                return {
                    "is_valid": False,
                    "reason": f"Invalid parameter name: {key}. Only alphanumeric and underscore are allowed."
                }
            
            # Check parameter values
            param_value = params[key]
            validation_result = validate_parameter_value(param_value)
            if not validation_result["is_valid"]:
                return validation_result
    
    # For list parameters
    elif isinstance(params, list):
        # Check each parameter value
        for i, param_value in enumerate(params):
            validation_result = validate_parameter_value(param_value)
            if not validation_result["is_valid"]:
                return validation_result
    
    # All checks passed
    return {"is_valid": True}


def validate_parameter_value(value: Any) -> Dict[str, Any]:
    """
    Validate an individual parameter value.
    
    Args:
        value: Parameter value to validate
        
    Returns:
        Dictionary containing validation result:
            - is_valid: Boolean indicating whether the value is valid
            - reason: Reason for failure if not valid
    """
    # Allow None values
    if value is None:
        return {"is_valid": True}
    
    # Check for allowed primitive types
    if isinstance(value, (str, int, float, bool)):
        # For strings, perform additional validation
        if isinstance(value, str):
            # Check for potential SQL injection in string values
            for pattern in SQL_INJECTION_PATTERNS:
                if re.search(pattern, value):
                    return {
                        "is_valid": False,
                        "reason": f"Parameter value contains potential SQL injection pattern: {pattern}"
                    }
            
            # Check for excessively long strings (potential DoS)
            if len(value) > 1000000:  # 1MB limit
                return {
                    "is_valid": False,
                    "reason": f"Parameter value is too long: {len(value)} characters"
                }
                
        # Numeric value within reasonable limits
        if isinstance(value, (int, float)):
            if abs(value) > 1e20:  # Arbitrary large number limit
                return {
                    "is_valid": False,
                    "reason": f"Parameter value is too large: {value}"
                }
                
        return {"is_valid": True}
    
    # Check for date/datetime objects
    if hasattr(value, 'isoformat'):  # datetime-like objects
        return {"is_valid": True}
    
    # Disallow complex types that could lead to injection
    return {
        "is_valid": False,
        "reason": f"Unsupported parameter type: {type(value).__name__}"
    }