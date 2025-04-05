"""
Test script for Natural Language Processing functionality
"""

import json
import requests

# Define the base URL
BASE_URL = "http://localhost:5000"

def test_nl_to_sql():
    """Test the natural language to SQL conversion endpoint."""
    print("Testing NL to SQL conversion...")
    
    # Test queries
    test_queries = [
        "Show me all accounts in Richland",
        "Find properties worth more than 300000",
        "How many accounts are owned by Smith?",
        "What's the average assessed value for properties in Kennewick?",
        "List the 10 most expensive properties",
        "Get all accounts with tax status 'Paid'"
    ]
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        
        # Get the debug info (intent extraction)
        try:
            from app.nl_processing import extract_query_intent
            intent = extract_query_intent(query)
            print("\nExtracted intent:")
            print(json.dumps(intent, indent=2))
        except Exception as e:
            print(f"Error extracting intent: {str(e)}")
        
        # Call the function directly instead of making HTTP request
        try:
            from app.nl_processing import nl_to_sql
            result = nl_to_sql(query, "postgres")
            
            if result["status"] == "success":
                print("\nGenerated SQL:")
                print(result.get("sql", "No SQL returned"))
                
                print("\nExplanation:")
                print(result.get("explanation", "No explanation provided"))
            else:
                print(f"NL to SQL conversion failed: {result.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"Error converting NL to SQL: {str(e)}")
            
        print("-" * 50)

def test_sql_to_nl():
    """Test the SQL to natural language conversion."""
    print("Testing SQL to natural language conversion...")
    
    # Test SQL queries
    test_sql_queries = [
        "SELECT * FROM accounts WHERE property_city = 'Richland' LIMIT 10",
        "SELECT owner_name, assessed_value FROM accounts WHERE assessed_value > 300000 ORDER BY assessed_value DESC",
        "SELECT COUNT(*) FROM accounts WHERE owner_name LIKE '%Smith%'",
        "SELECT AVG(assessed_value) FROM accounts WHERE property_city = 'Kennewick'",
        "SELECT account_id, owner_name, assessed_value FROM accounts ORDER BY assessed_value DESC LIMIT 10",
        "SELECT * FROM accounts WHERE tax_status = 'Paid'"
    ]
    
    for sql in test_sql_queries:
        print(f"\nTesting SQL: '{sql}'")
        
        # Get the natural language explanation directly
        from app.nl_processing import sql_to_natural_language
        
        try:
            explanation = sql_to_natural_language(sql)
            print("\nNatural language explanation:")
            print(explanation)
        except Exception as e:
            print(f"Error converting SQL to natural language: {str(e)}")
            
        print("-" * 50)

if __name__ == "__main__":
    print("=" * 50)
    print("NATURAL LANGUAGE PROCESSING TEST")
    print("=" * 50)
    
    test_nl_to_sql()
    print("\n\n")
    test_sql_to_nl()