"""
This script tests the parameterized query extraction functionality.
"""

import json
from app.db import parse_for_parameters

def test_parameter_extraction():
    """Test extraction of parameters from SQL queries."""
    
    # Test cases with different types of parameters
    test_cases = [
        # Basic string parameters
        {
            "query": "SELECT * FROM parcels WHERE city = 'Springfield'",
            "expected_params": ["Springfield"],
            "expected_query": "SELECT * FROM parcels WHERE city = %s"
        },
        # Multiple string parameters
        {
            "query": "SELECT * FROM parcels WHERE city = 'Springfield' AND state = 'IL'",
            "expected_params": ["Springfield", "IL"],
            "expected_query": "SELECT * FROM parcels WHERE city = %s AND state = %s"
        },
        # Numeric parameters
        {
            "query": "SELECT * FROM properties WHERE year_built > 2000 AND square_footage > 1500",
            "expected_params": [2000, 1500],
            "expected_query": "SELECT * FROM properties WHERE year_built > %s AND square_footage > %s"
        },
        # Mixed parameter types
        {
            "query": "SELECT * FROM parcels WHERE city = 'Springfield' AND total_value > 250000",
            "expected_params": ["Springfield", 250000],
            "expected_query": "SELECT * FROM parcels WHERE city = %s AND total_value > %s"
        },
        # Complex query with joins
        {
            "query": """
            SELECT p.parcel_id, p.address, s.sale_price, s.sale_date 
            FROM parcels p
            JOIN sales s ON p.id = s.parcel_id
            WHERE p.city = 'Springfield' AND s.sale_price > 300000
            ORDER BY s.sale_date DESC
            """,
            "expected_params": ["Springfield", 300000],
            "expected_query": """
            SELECT p.parcel_id, p.address, s.sale_price, s.sale_date 
            FROM parcels p
            JOIN sales s ON p.id = s.parcel_id
            WHERE p.city = %s AND s.sale_price > %s
            ORDER BY s.sale_date DESC
            """
        },
        # Query with decimal numbers
        {
            "query": "SELECT * FROM sales WHERE sale_price BETWEEN 250000.50 AND 500000.75",
            "expected_params": [250000.50, 500000.75],
            "expected_query": "SELECT * FROM sales WHERE sale_price BETWEEN %s AND %s"
        }
    ]
    
    # Run tests
    for i, test in enumerate(test_cases):
        print(f"\nTest case {i+1}:")
        print(f"Original query: {test['query']}")
        
        # Extract parameters
        parsed_query, params = parse_for_parameters(test["query"])
        
        print(f"Parsed query: {parsed_query}")
        print(f"Extracted parameters: {params}")
        
        # Validate parameter count
        if len(params) == len(test["expected_params"]):
            print(f"✓ Parameter count matches ({len(params)})")
        else:
            print(f"✗ Parameter count mismatch. Expected {len(test['expected_params'])}, got {len(params)}")
        
        # Validate parameter values (types can vary but values should match)
        for j, (expected, actual) in enumerate(zip(test["expected_params"], params)):
            expected_type = type(expected).__name__
            actual_type = type(actual).__name__
            
            # Note: Numeric types might differ (int vs float), that's acceptable
            if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                if abs(expected - actual) < 0.001:
                    print(f"✓ Parameter {j+1}: {actual} ({actual_type}) - value matches")
                else:
                    print(f"✗ Parameter {j+1}: {actual} ({actual_type}) - value mismatch, expected {expected}")
            else:
                if expected == actual:
                    print(f"✓ Parameter {j+1}: {actual} ({actual_type}) - value matches")
                else:
                    print(f"✗ Parameter {j+1}: {actual} ({actual_type}) - value mismatch, expected {expected}")
        
        # Check query format
        if parsed_query.strip() == test["expected_query"].strip():
            print("✓ Query transformation is correct")
        else:
            print("✗ Query transformation mismatch")
            print(f"Expected: {test['expected_query']}")

if __name__ == "__main__":
    test_parameter_extraction()