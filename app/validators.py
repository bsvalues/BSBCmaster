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

def is_valid_sql_query(query: str) -> Dict[str, Any]:
    """
    Validate a SQL query for potential security issues.
    
    Args:
        query: SQL query string
        
    Returns:
        Dict with validation results:
            - valid: True if no issues found, False otherwise
            - issues: List of detected issues
            - severity: 'high', 'medium', 'low', or 'none'
    """
    issues = []
    severity = "none"
    
    # Check for SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, query):
            issues.append(f"Detected potentially harmful pattern: {pattern}")
            severity = "high"
    
    # Check for dangerous keywords
    for category, keywords in DANGEROUS_KEYWORDS.items():
        for keyword in keywords:
            if re.search(rf'\b{keyword}\b', query, re.IGNORECASE):
                issues.append(f"Detected potentially dangerous keyword: {keyword}")
                severity = max(severity, "medium")
    
    # Normalize whitespace for better pattern matching
    normalized_query = re.sub(r'\s+', ' ', query.strip())
    
    # Check for stacked queries (multiple statements)
    if re.search(r';[ \t\r\n]*[a-zA-Z]', normalized_query):
        issues.append("Multiple SQL statements detected")
        severity = max(severity, "high")
    
    # Check for unbalanced quotes or comments
    single_quotes = len(re.findall(r"'", query)) % 2
    double_quotes = len(re.findall(r'"', query)) % 2
    comment_start = len(re.findall(r'/\*', query))
    comment_end = len(re.findall(r'\*/', query))
    
    if single_quotes != 0:
        issues.append("Unbalanced single quotes")
        severity = max(severity, "medium")
    
    if double_quotes != 0:
        issues.append("Unbalanced double quotes")
        severity = max(severity, "medium")
    
    if comment_start != comment_end:
        issues.append("Unbalanced comment blocks")
        severity = max(severity, "medium")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "severity": severity
    }

def validate_natural_language_prompt(prompt: str) -> Dict[str, Any]:
    """
    Validate a natural language prompt for potential issues.
    
    Args:
        prompt: Natural language prompt string
        
    Returns:
        Dict with validation results:
            - valid: True if no issues found, False otherwise
            - issues: List of detected issues
            - severity: 'high', 'medium', 'low', or 'none'
    """
    issues = []
    severity = "none"
    
    # Check for empty or too short prompts
    if not prompt or len(prompt.strip()) < 5:
        issues.append("Prompt is too short")
        severity = "low"
    
    # Check for potential code injection
    if re.search(r'<script|<iframe|<img|<a\s+', prompt, re.IGNORECASE):
        issues.append("Potential HTML/JavaScript injection detected")
        severity = "high"
    
    # Check for SQL injection patterns (in case they're trying to trick the system)
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, prompt):
            issues.append("SQL patterns detected in natural language prompt")
            severity = "medium"
    
    # Check for prompts that are just SQL commands
    if re.search(r'^SELECT\s+|\bFROM\b|\bWHERE\b', prompt, re.IGNORECASE):
        issues.append("Prompt appears to be a SQL query instead of natural language")
        severity = "low"
    
    return {
        "valid": len(issues) == 0 or severity == "low",  # Allow low severity issues
        "issues": issues,
        "severity": severity
    }

def validate_pagination_params(page: int, page_size: int, max_page_size: int = 100) -> Dict[str, Any]:
    """
    Validate pagination parameters.
    
    Args:
        page: Page number
        page_size: Page size
        max_page_size: Maximum allowed page size
        
    Returns:
        Dict with validation results:
            - valid: True if no issues found, False otherwise
            - issues: List of detected issues
            - severity: 'high', 'medium', 'low', or 'none'
            - corrected_page: Corrected page number if needed
            - corrected_page_size: Corrected page size if needed
    """
    issues = []
    severity = "none"
    corrected_page = page
    corrected_page_size = page_size
    
    # Validate page number
    if page < 1:
        issues.append(f"Page number cannot be less than 1, using page=1 instead of {page}")
        corrected_page = 1
        severity = "low"
    
    # Validate page size
    if page_size < 1:
        issues.append(f"Page size cannot be less than 1, using page_size=10 instead of {page_size}")
        corrected_page_size = 10
        severity = "low"
    elif page_size > max_page_size:
        issues.append(f"Page size cannot exceed {max_page_size}, using page_size={max_page_size} instead of {page_size}")
        corrected_page_size = max_page_size
        severity = "low"
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "severity": severity,
        "corrected_page": corrected_page,
        "corrected_page_size": corrected_page_size
    }