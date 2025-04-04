"""
This module provides OpenAI integration for natural language to SQL translation.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional

from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o"

async def translate_nl_to_sql(
    prompt: str, 
    db_type: str,
    schema_info: str
) -> Dict[str, Any]:
    """
    Translate a natural language prompt to SQL using OpenAI's API.
    
    Args:
        prompt: The natural language query prompt
        db_type: Database type ('postgres' or 'mssql')
        schema_info: Information about the database schema for context
        
    Returns:
        Dict containing the translated SQL query and an explanation
        
    Raises:
        Exception: If translation fails after retries
    """
    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured. Using fallback response.")
        return generate_fallback_response(prompt, db_type)
    
    # Construct the system message with schema information and database context
    system_message = f"""You are an expert in converting natural language queries to SQL for {db_type.upper()}.
Your task is to translate natural language descriptions into valid {db_type.upper()} SQL code.

DATABASE SCHEMA INFORMATION:
{schema_info}

INSTRUCTIONS:
1. Convert the user's natural language query to a valid SQL query for {db_type.upper()}.
2. Ensure the SQL is syntactically correct for {db_type.upper()}.
3. Use proper SQL injection prevention practices - don't concatenate user inputs.
4. Include proper table aliases when joining tables.
5. Return results in the following JSON format:
   {{
     "sql": "The SQL query that can be directly executed",
     "explanation": "A brief explanation of the SQL query and how it addresses the request"
   }}
"""

    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Send the request to OpenAI API
            response = openai_client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Lower temperature for more deterministic results
                response_format={"type": "json_object"}
            )
            
            # Extract and parse the response
            result = json.loads(response.choices[0].message.content)
            
            # Validate response structure
            if "sql" not in result or "explanation" not in result:
                raise ValueError("Incomplete response from OpenAI API")
                
            return result
            
        except Exception as e:
            logger.error(f"Error in OpenAI API call (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Exponential backoff
            else:
                # If all retries fail, return a fallback response
                logger.error(f"Failed to translate after {max_retries} attempts: {str(e)}")
                return generate_fallback_response(prompt, db_type)

def generate_fallback_response(prompt: str, db_type: str) -> Dict[str, Any]:
    """Generate a fallback response when OpenAI translation fails."""
    # Create a basic SELECT * query based on keyword matching
    # This is a very simplistic fallback that should only be used when the OpenAI API fails
    
    # Extract potential table names from the prompt (very naive approach)
    lower_prompt = prompt.lower()
    
    potential_tables = []
    common_tables = ["parcels", "properties", "sales"]
    
    for table in common_tables:
        if table in lower_prompt:
            potential_tables.append(table)
    
    if not potential_tables:
        potential_tables = ["parcels"]  # Default to parcels if no table is detected
    
    table_name = potential_tables[0]
    
    # Determine if we need to limit results
    limit_clause = "LIMIT 10"  # Default limit
    if "all" in lower_prompt:
        limit_clause = ""
    
    # Construct a simple SQL query
    sql = f"SELECT * FROM {table_name}"
    
    # Add WHERE clause for common filtering patterns (very basic implementation)
    if "where" in lower_prompt:
        if "city" in lower_prompt:
            sql += " WHERE city = '[CITY_NAME]'"
        elif "state" in lower_prompt:
            sql += " WHERE state = '[STATE_NAME]'"
        elif "value" in lower_prompt:
            if "greater" in lower_prompt or "more" in lower_prompt:
                sql += " WHERE total_value > [VALUE]"
            elif "less" in lower_prompt:
                sql += " WHERE total_value < [VALUE]"
    
    # Add the limit clause if needed
    if limit_clause:
        sql += f" {limit_clause}"
    
    # Add a semicolon to end the query
    sql += ";"
    
    return {
        "sql": sql,
        "explanation": "This is a fallback query based on keyword matching. The query may need manual adjustments."
    }