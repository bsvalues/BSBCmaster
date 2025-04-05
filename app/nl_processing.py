"""
Natural Language Processing Module for MCP Assessor Agent API

This module provides natural language processing utilities including
SQL to natural language conversion and NL query parsing capabilities.
"""

import logging
import re
import os
from typing import Dict, List, Any, Optional, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import OpenAI if available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not installed. Some NL features may be limited.")

def sql_to_natural_language(sql_query: str) -> str:
    """
    Convert a SQL query to a natural language explanation.
    
    Args:
        sql_query: The SQL query to convert
        
    Returns:
        A natural language explanation of the query
    """
    try:
        # Normalize whitespace
        sql = re.sub(r'\s+', ' ', sql_query.strip())
        
        # Extract basic components
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE)
        from_match = re.search(r'FROM\s+(.*?)(?:\s+WHERE|\s+GROUP BY|\s+ORDER BY|\s+LIMIT|\s*$)', sql, re.IGNORECASE)
        where_match = re.search(r'WHERE\s+(.*?)(?:\s+GROUP BY|\s+ORDER BY|\s+LIMIT|\s*$)', sql, re.IGNORECASE)
        group_by_match = re.search(r'GROUP BY\s+(.*?)(?:\s+ORDER BY|\s+LIMIT|\s*$)', sql, re.IGNORECASE)
        order_by_match = re.search(r'ORDER BY\s+(.*?)(?:\s+LIMIT|\s*$)', sql, re.IGNORECASE)
        limit_match = re.search(r'LIMIT\s+(\d+)', sql, re.IGNORECASE)
        
        # Parse components
        select_clause = select_match.group(1) if select_match else "*"
        from_clause = from_match.group(1) if from_match else ""
        where_clause = where_match.group(1) if where_match else ""
        group_by_clause = group_by_match.group(1) if group_by_match else ""
        order_by_clause = order_by_match.group(1) if order_by_match else ""
        limit_clause = limit_match.group(1) if limit_match else ""
        
        # Initialize explanation
        explanation = f"This query retrieves"
        
        # Handle aggregation functions
        aggregation_match = re.search(r'(COUNT|SUM|AVG|MIN|MAX)\s*\(\s*(.*?)\s*\)(?:\s+AS\s+(\w+))?', select_clause, re.IGNORECASE)
        if aggregation_match:
            agg_function = aggregation_match.group(1).upper()
            agg_column = aggregation_match.group(2)
            
            if agg_function == "COUNT":
                if agg_column == "*":
                    explanation += " the total number of records"
                else:
                    explanation += f" the count of {agg_column}"
            elif agg_function == "SUM":
                explanation += f" the sum of {agg_column} values"
            elif agg_function == "AVG":
                explanation += f" the average {agg_column}"
            elif agg_function == "MIN":
                explanation += f" the minimum {agg_column}"
            elif agg_function == "MAX":
                explanation += f" the maximum {agg_column}"
        else:
            if select_clause == "*":
                explanation += " all data"
            else:
                # Clean up the column list for readability
                columns = [col.strip().split(' AS ')[-1].strip() for col in select_clause.split(',')]
                explanation += f" the following data: {', '.join(columns)}"
        
        # Add FROM information
        if from_clause:
            # Extract table name and aliases
            tables = []
            for table_part in from_clause.split(','):
                table_info = table_part.strip().split(' AS ')
                if len(table_info) > 1:
                    tables.append(table_info[0].strip())
                else:
                    tables.append(table_part.strip())
            
            explanation += f" from the {', '.join(tables)} table"
            if len(tables) > 1:
                explanation += "s"
        
        # Add WHERE conditions in natural language
        if where_clause:
            conditions = []
            
            # Split on AND/OR operators, handling parentheses
            clause_parts = []
            current_part = ""
            paren_level = 0
            
            for char in where_clause:
                if char == '(':
                    paren_level += 1
                elif char == ')':
                    paren_level -= 1
                
                current_part += char
                
                # Only split at top-level AND/OR
                if paren_level == 0 and re.search(r'\bAND\b|\bOR\b', current_part, re.IGNORECASE):
                    operator = 'AND' if ' AND ' in current_part.upper() else 'OR'
                    parts = current_part.split(f' {operator} ', 1)
                    if parts[0].strip():
                        clause_parts.append(parts[0].strip())
                    current_part = parts[1].strip() if len(parts) > 1 else ""
            
            # Add the last part if any
            if current_part.strip():
                clause_parts.append(current_part.strip())
            
            # If we didn't split successfully, just use the whole where clause
            if not clause_parts:
                clause_parts = [where_clause]
            
            # Convert each condition to natural language
            for condition in clause_parts:
                # Handle various comparison operators
                condition = condition.strip()
                
                # Equal comparison
                eq_match = re.search(r'(\w+)\s*=\s*[\'"]?([\w\s-]+)[\'"]?', condition)
                if eq_match:
                    field = eq_match.group(1)
                    value = eq_match.group(2)
                    conditions.append(f"{field.replace('_', ' ')} is {value}")
                    continue
                
                # Not equal comparison
                neq_match = re.search(r'(\w+)\s*!=\s*[\'"]?([\w\s-]+)[\'"]?', condition)
                if neq_match:
                    field = neq_match.group(1)
                    value = neq_match.group(2)
                    conditions.append(f"{field.replace('_', ' ')} is not {value}")
                    continue
                
                # Greater than comparison
                gt_match = re.search(r'(\w+)\s*>\s*(\d+)', condition)
                if gt_match:
                    field = gt_match.group(1)
                    value = gt_match.group(2)
                    conditions.append(f"{field.replace('_', ' ')} is greater than {value}")
                    continue
                
                # Less than comparison
                lt_match = re.search(r'(\w+)\s*<\s*(\d+)', condition)
                if lt_match:
                    field = lt_match.group(1)
                    value = lt_match.group(2)
                    conditions.append(f"{field.replace('_', ' ')} is less than {value}")
                    continue
                
                # Greater than or equal comparison
                gte_match = re.search(r'(\w+)\s*>=\s*(\d+)', condition)
                if gte_match:
                    field = gte_match.group(1)
                    value = gte_match.group(2)
                    conditions.append(f"{field.replace('_', ' ')} is at least {value}")
                    continue
                
                # Less than or equal comparison
                lte_match = re.search(r'(\w+)\s*<=\s*(\d+)', condition)
                if lte_match:
                    field = lte_match.group(1)
                    value = lte_match.group(2)
                    conditions.append(f"{field.replace('_', ' ')} is at most {value}")
                    continue
                
                # LIKE comparison
                like_match = re.search(r'(\w+)\s+LIKE\s+[\'"]%(.+)%[\'"]', condition, re.IGNORECASE)
                if like_match:
                    field = like_match.group(1)
                    value = like_match.group(2)
                    conditions.append(f"{field.replace('_', ' ')} contains {value}")
                    continue
                
                # IN list comparison
                in_match = re.search(r'(\w+)\s+IN\s+\((.+)\)', condition, re.IGNORECASE)
                if in_match:
                    field = in_match.group(1)
                    values = in_match.group(2)
                    values_list = [v.strip().strip("'").strip('"') for v in values.split(',')]
                    values_str = ', '.join(values_list[:-1]) + f" or {values_list[-1]}" if len(values_list) > 1 else values_list[0]
                    conditions.append(f"{field.replace('_', ' ')} is one of: {values_str}")
                    continue
                
                # BETWEEN comparison
                between_match = re.search(r'(\w+)\s+BETWEEN\s+(\d+)\s+AND\s+(\d+)', condition, re.IGNORECASE)
                if between_match:
                    field = between_match.group(1)
                    min_val = between_match.group(2)
                    max_val = between_match.group(3)
                    conditions.append(f"{field.replace('_', ' ')} is between {min_val} and {max_val}")
                    continue
                
                # IS NULL comparison
                null_match = re.search(r'(\w+)\s+IS\s+NULL', condition, re.IGNORECASE)
                if null_match:
                    field = null_match.group(1)
                    conditions.append(f"{field.replace('_', ' ')} is not specified")
                    continue
                
                # IS NOT NULL comparison
                not_null_match = re.search(r'(\w+)\s+IS\s+NOT\s+NULL', condition, re.IGNORECASE)
                if not_null_match:
                    field = not_null_match.group(1)
                    conditions.append(f"{field.replace('_', ' ')} is specified")
                    continue
                
                # If we couldn't parse the condition, just include it as is
                conditions.append(condition)
            
            # Join conditions with proper language
            if conditions:
                conditions_text = ", ".join(conditions[:-1])
                if len(conditions) > 1:
                    conditions_text += f" and {conditions[-1]}"
                else:
                    conditions_text = conditions[0]
                
                explanation += f" where {conditions_text}"
        
        # Add GROUP BY information
        if group_by_clause:
            group_fields = [field.strip() for field in group_by_clause.split(',')]
            if len(group_fields) == 1:
                explanation += f", grouped by {group_fields[0].replace('_', ' ')}"
            else:
                explanation += f", grouped by {', '.join(group_fields[:-1]).replace('_', ' ')} and {group_fields[-1].replace('_', ' ')}"
        
        # Add ORDER BY information
        if order_by_clause:
            order_parts = order_by_clause.split(',')
            order_fields = []
            
            for part in order_parts:
                if " DESC" in part.upper():
                    field = part.replace(" DESC", "").replace(" desc", "").strip()
                    order_fields.append(f"{field.replace('_', ' ')} (descending)")
                elif " ASC" in part.upper():
                    field = part.replace(" ASC", "").replace(" asc", "").strip()
                    order_fields.append(f"{field.replace('_', ' ')} (ascending)")
                else:
                    order_fields.append(f"{part.strip().replace('_', ' ')} (ascending)")
            
            if len(order_fields) == 1:
                explanation += f", ordered by {order_fields[0]}"
            else:
                explanation += f", ordered by {', '.join(order_fields[:-1])} and {order_fields[-1]}"
        
        # Add LIMIT information
        if limit_clause:
            explanation += f", limited to {limit_clause} results"
        
        # Finalize the explanation
        explanation += "."
        
        # Clean up any double spaces or awkward punctuation
        explanation = re.sub(r'\s+', ' ', explanation)
        explanation = re.sub(r'\s+\.', '.', explanation)
        explanation = re.sub(r'\s+,', ',', explanation)
        
        return explanation
        
    except Exception as e:
        logger.warning(f"Error generating natural language from SQL: {str(e)}")
        return "This query retrieves data based on the specified criteria."

def extract_query_intent(nl_query: str) -> Dict[str, Any]:
    """
    Extract the intent and parameters from a natural language query.
    
    Args:
        nl_query: The natural language query
        
    Returns:
        Dictionary with extracted intent and parameters
    """
    intent = {
        "action": "retrieve",  # retrieve, count, aggregate
        "aggregation": None,  # sum, avg, min, max, count
        "table": "accounts",  # default table
        "fields": ["*"],  # fields to retrieve
        "conditions": [],  # where conditions
        "sorting": None,  # sort order
        "limit": 100,  # default limit
    }
    
    # Determine the action and aggregation
    if any(word in nl_query.lower() for word in ['count', 'how many']):
        intent["action"] = "aggregate"
        intent["aggregation"] = "count"
        intent["fields"] = ["COUNT(*)"]
    elif any(word in nl_query.lower() for word in ['average', 'avg']):
        intent["action"] = "aggregate"
        intent["aggregation"] = "avg"
    elif any(word in nl_query.lower() for word in ['sum', 'total']):
        intent["action"] = "aggregate"
        intent["aggregation"] = "sum"
    elif any(word in nl_query.lower() for word in ['minimum', 'min', 'smallest', 'lowest']):
        intent["action"] = "aggregate"
        intent["aggregation"] = "min"
    elif any(word in nl_query.lower() for word in ['maximum', 'max', 'largest', 'highest']):
        intent["action"] = "aggregate"
        intent["aggregation"] = "max"
    
    # Determine the table from keywords
    table_keywords = {
        'account': 'accounts',
        'accounts': 'accounts',
        'property': 'properties',
        'properties': 'properties',
        'sale': 'sales',
        'sales': 'sales',
        'parcel': 'parcels',
        'parcels': 'parcels',
        'image': 'property_images',
        'images': 'property_images',
        'improvement': 'improvements',
        'improvements': 'improvements'
    }
    
    for keyword, table_name in table_keywords.items():
        if keyword.lower() in nl_query.lower():
            intent["table"] = table_name
            break
    
    # Extract fields if specified
    fields_match = re.search(r'(show|display|get|retrieve|find|select)\s+([\w\s,]+)\s+from', nl_query, re.IGNORECASE)
    if fields_match:
        fields_text = fields_match.group(2).strip()
        if fields_text.lower() not in ['all', 'everything', 'records', 'data']:
            fields = [f.strip() for f in fields_text.split(',')]
            
            # Map common terms to field names
            field_mapping = {
                'name': 'owner_name',
                'owner': 'owner_name',
                'address': 'property_address',
                'city': 'property_city',
                'value': 'assessed_value',
                'price': 'sale_price',
                'date': 'sale_date',
                'year': 'assessment_year',
                'tax': 'tax_amount',
                'status': 'tax_status'
            }
            
            mapped_fields = []
            for field in fields:
                field_lower = field.lower()
                if field_lower in field_mapping:
                    mapped_fields.append(field_mapping[field_lower])
                else:
                    # Try to convert to snake_case and use as is
                    mapped_fields.append(field.lower().replace(' ', '_'))
            
            intent["fields"] = mapped_fields
    
    # Extract location conditions
    location_matches = re.findall(r"(in|at|from|located in|located at) ['\"]?([\w\s]+)['\"]?", nl_query, re.IGNORECASE)
    if location_matches:
        location = location_matches[0][1]
        if intent["table"] == 'accounts':
            intent["conditions"].append({
                "field": "property_city",
                "operator": "ILIKE",
                "value": f"%{location}%"
            })
        elif intent["table"] == 'properties':
            intent["conditions"].append({
                "field": "property_address",
                "operator": "ILIKE",
                "value": f"%{location}%"
            })
    
    # Extract owner conditions
    owner_matches = re.findall(r"(owned by|owned|owner|name is|named) ['\"]?([\w\s]+)['\"]?", nl_query, re.IGNORECASE)
    if owner_matches:
        owner = owner_matches[0][1]
        if intent["table"] in ['accounts', 'parcels']:
            intent["conditions"].append({
                "field": "owner_name",
                "operator": "ILIKE",
                "value": f"%{owner}%"
            })
    
    # Extract value conditions
    value_matches = re.findall(r"(value|worth|cost|price) (greater than|more than|over|above|less than|under|below) ['\"]?(\d+)['\"]?", nl_query, re.IGNORECASE)
    if value_matches:
        comparison = value_matches[0][1]
        value = value_matches[0][2]
        operator = '>' if any(x in comparison.lower() for x in ['greater', 'more', 'over', 'above']) else '<'
        
        value_column = 'assessed_value'
        if intent["table"] == 'properties':
            value_column = 'total_value'
        elif intent["table"] == 'sales':
            value_column = 'sale_price'
        
        intent["conditions"].append({
            "field": value_column,
            "operator": operator,
            "value": int(value)
        })
    
    # Extract date/time conditions
    year_matches = re.findall(r"(from|in|after|before|since|until) (year|the year) ['\"]?(\d{4})['\"]?", nl_query, re.IGNORECASE)
    if year_matches:
        comparison = year_matches[0][0].lower()
        year = year_matches[0][2]
        
        operator = '>=' if any(x in comparison for x in ['after', 'since']) else '<=' if any(x in comparison for x in ['before', 'until']) else '='
        
        date_column = 'assessment_year'
        if intent["table"] == 'properties':
            date_column = 'year_built'
        elif intent["table"] == 'sales':
            date_column = 'sale_date'
            intent["conditions"].append({
                "field": "EXTRACT(YEAR FROM sale_date)",
                "operator": operator,
                "value": int(year)
            })
        else:
            intent["conditions"].append({
                "field": date_column,
                "operator": operator,
                "value": int(year)
            })
    
    # Extract sorting preferences
    if 'newest' in nl_query.lower() or 'latest' in nl_query.lower() or 'recent' in nl_query.lower():
        if intent["table"] == 'sales':
            intent["sorting"] = {"field": "sale_date", "direction": "DESC"}
        elif intent["table"] == 'property_images':
            intent["sorting"] = {"field": "image_date", "direction": "DESC"}
        elif intent["table"] == 'properties':
            intent["sorting"] = {"field": "year_built", "direction": "DESC"}
        else:
            intent["sorting"] = {"field": "id", "direction": "DESC"}
    elif 'oldest' in nl_query.lower():
        if intent["table"] == 'sales':
            intent["sorting"] = {"field": "sale_date", "direction": "ASC"}
        elif intent["table"] == 'property_images':
            intent["sorting"] = {"field": "image_date", "direction": "ASC"}
        elif intent["table"] == 'properties':
            intent["sorting"] = {"field": "year_built", "direction": "ASC"}
        else:
            intent["sorting"] = {"field": "id", "direction": "ASC"}
    elif any(word in nl_query.lower() for word in ['expensive', 'highest value', 'most valuable']):
        if intent["table"] in ['accounts', 'parcels']:
            intent["sorting"] = {"field": "assessed_value", "direction": "DESC"}
        elif intent["table"] == 'sales':
            intent["sorting"] = {"field": "sale_price", "direction": "DESC"}
        elif intent["table"] == 'properties':
            intent["sorting"] = {"field": "total_value", "direction": "DESC"}
    
    # Extract limit
    limit_matches = re.findall(r"(limit|top|first) (\d+)", nl_query, re.IGNORECASE)
    if limit_matches:
        intent["limit"] = int(limit_matches[0][1])
    
    return intent


def nl_to_sql(nl_query: str, db_type: str = "postgres") -> Dict[str, Any]:
    """
    Convert a natural language query to SQL.
    
    Args:
        nl_query: The natural language query to convert
        db_type: The database type ('postgres' or 'mssql')
        
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - sql: Generated SQL query
            - explanation: Natural language explanation of the query
            - parameters: Optional dictionary of parameters for parameterized queries
    """
    try:
        # Get query intent
        intent = extract_query_intent(nl_query)
        
        # Build SQL query based on intent
        table = intent.get('table', 'accounts')
        
        # Determine fields to select
        fields = intent.get('fields', ['*'])
        if intent.get('action') == 'aggregate' and intent.get('aggregation'):
            agg_function = intent.get('aggregation', 'count').upper()
            
            # For count, use COUNT(*)
            if agg_function == 'COUNT':
                select_clause = f"COUNT(*)"
            else:
                # For other aggregations, use first non-* field or default to a common field
                agg_field = next((f for f in fields if f != '*'), None)
                if agg_field is None:
                    # Default field based on table
                    if table == 'accounts':
                        agg_field = 'assessed_value'
                    elif table == 'properties':
                        agg_field = 'total_value'
                    elif table == 'sales':
                        agg_field = 'sale_price'
                    else:
                        agg_field = 'id'
                
                select_clause = f"{agg_function}({agg_field})"
        else:
            # For non-aggregation queries, use the specified fields
            select_clause = ', '.join(fields)
        
        # Build the base query
        sql_query = f"SELECT {select_clause} FROM {table}"
        
        # Add WHERE conditions
        conditions = []
        for condition in intent.get('conditions', []):
            field = condition.get('field')
            operator = condition.get('operator', '=')
            value = condition.get('value')
            
            if operator == 'ILIKE':
                conditions.append(f"{field} ILIKE '{value}'")
            elif isinstance(value, str):
                conditions.append(f"{field} {operator} '{value}'")
            else:
                conditions.append(f"{field} {operator} {value}")
        
        if conditions:
            sql_query += " WHERE " + " AND ".join(conditions)
        
        # Add sorting
        sorting = intent.get('sorting')
        if sorting:
            sort_field = sorting.get('field')
            sort_dir = sorting.get('direction', 'ASC')
            sql_query += f" ORDER BY {sort_field} {sort_dir}"
        
        # Add LIMIT
        limit = intent.get('limit', 100)
        sql_query += f" LIMIT {limit}"
        
        # Try to use OpenAI for more advanced processing if available
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if OPENAI_AVAILABLE and openai_api_key:
            try:
                schema_info = """
                Tables:
                - accounts (account_id, owner_name, property_address, property_city, mailing_address, mailing_city, mailing_state, mailing_zip, legal_description, assessment_year, assessed_value, tax_amount, tax_status)
                - property_images (id, property_id, account_id, image_url, image_path, image_type, image_date, width, height, file_size, file_format)
                - properties (id, parcel_id, property_type, square_footage, bedrooms, bathrooms, year_built, stories)
                - parcels (id, parcel_id, land_value, improvement_value, total_value, land_use_code, zoning_code)
                - sales (id, parcel_id, sale_date, sale_price, sale_type, buyer_name, seller_name)
                """
                
                # Create a prompt for the OpenAI model
                prompt = f"""
                Convert the following natural language query to SQL for a PostgreSQL database. Return only valid SQL without explanations.
                
                The database schema is:
                {schema_info}
                
                Natural language query: {nl_query}
                
                SQL query:
                """
                
                # Initialize OpenAI client (new client style)
                client = OpenAI(api_key=openai_api_key)
                
                # Call OpenAI API using the new ChatCompletion endpoint
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",  # New model instead of text-davinci-003
                    messages=[
                        {"role": "system", "content": "You are a SQL expert who converts natural language to SQL queries."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.3,
                    top_p=1.0,
                    frequency_penalty=0.0,
                    presence_penalty=0.0
                )
                
                # Extract the SQL from the response
                generated_sql = response.choices[0].message.content.strip()
                
                # Add default LIMIT if not present
                if "LIMIT" not in generated_sql.upper():
                    generated_sql += " LIMIT 100"
                
                # Get natural language explanation
                explanation = sql_to_natural_language(generated_sql)
                
                return {
                    "status": "success",
                    "sql": generated_sql,
                    "explanation": explanation,
                    "parameters": {}
                }
            except Exception as e:
                logger.warning(f"Error using OpenAI API: {str(e)}, falling back to rule-based conversion")
        
        # If OpenAI is not available or fails, use the rule-based SQL
        explanation = sql_to_natural_language(sql_query)
        
        return {
            "status": "success",
            "sql": sql_query,
            "explanation": explanation,
            "parameters": {}
        }
        
    except Exception as e:
        logger.error(f"Error converting natural language to SQL: {str(e)}")
        return {
            "status": "error",
            "message": f"Error converting query: {str(e)}",
            "sql": None,
            "explanation": None
        }