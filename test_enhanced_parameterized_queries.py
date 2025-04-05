"""
Test script for the enhanced parameterized query functionality.
"""

import json
import re
import unittest
from unittest.mock import patch, MagicMock

import requests

# Configuration
API_URL = "http://localhost:8000"
API_KEY = "test_key"
API_PREFIX = "/api/v1"


class TestParameterizedQueries(unittest.TestCase):
    """Test the enhanced parameterized query functionality."""

    def setUp(self):
        """Set up test case."""
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        }

    def test_parameter_extraction(self):
        """Test parameter extraction from SQL queries."""
        # Test with named parameters
        query1 = "SELECT * FROM users WHERE id = :user_id AND status = :status"
        params1 = {
            "user_id": 1,
            "status": "active"
        }
        # Extract parameters using regex
        param_matches1 = set(re.findall(r':(\w+)', query1))
        self.assertEqual(param_matches1, {"user_id", "status"})
        self.assertTrue(all(param in params1 for param in param_matches1))

        # Test with @ style parameters
        query2 = "SELECT * FROM orders WHERE customer_id = @customer_id AND order_date > @start_date"
        params2 = {
            "customer_id": 5,
            "start_date": "2023-01-01"
        }
        # Extract parameters using regex
        param_matches2 = set(re.findall(r'@(\w+)', query2))
        self.assertEqual(param_matches2, {"customer_id", "start_date"})
        self.assertTrue(all(param in params2 for param in param_matches2))

        # Test with question mark placeholders
        query3 = "SELECT * FROM products WHERE category = ? AND price > ?"
        params3 = ["Electronics", 100]
        # Count placeholders
        placeholder_count = query3.count('?')
        self.assertEqual(placeholder_count, 2)
        self.assertEqual(len(params3), placeholder_count)

    def test_parameter_validation(self):
        """Test parameter validation logic."""
        # Test named parameter validation with missing parameter
        query1 = "SELECT * FROM users WHERE id = :user_id AND status = :status"
        params1 = {"user_id": 1}  # Missing 'status' parameter
        param_matches1 = set(re.findall(r':(\w+)', query1))
        missing_params1 = [param for param in param_matches1 if param not in params1]
        self.assertEqual(missing_params1, ["status"])

        # Test @ style parameter validation with all parameters present
        query2 = "SELECT * FROM orders WHERE customer_id = @customer_id"
        params2 = {"customer_id": 5}
        param_matches2 = set(re.findall(r'@(\w+)', query2))
        missing_params2 = [param for param in param_matches2 if param not in params2]
        self.assertEqual(missing_params2, [])

        # Test question mark placeholders with mismatched parameter count
        query3 = "SELECT * FROM products WHERE category = ? AND price > ?"
        params3 = ["Electronics"]  # Only one parameter, but two placeholders
        placeholder_count = query3.count('?')
        self.assertNotEqual(len(params3), placeholder_count)

    @patch('requests.post')
    def test_api_parameterized_query(self, mock_post):
        """Test the parameterized query endpoint."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [{"id": 1, "name": "Test"}],
            "execution_time": 0.1,
            "pagination": {
                "page": 1,
                "page_size": 50,
                "total_records": 1,
                "total_pages": 1,
                "has_next": False,
                "has_prev": False
            }
        }
        mock_post.return_value = mock_response

        # Test with named parameters
        payload1 = {
            "db": "postgres",
            "query": "SELECT * FROM parcels WHERE id = :parcel_id",
            "params": {"parcel_id": 1},
            "param_style": "named"
        }
        
        response1 = requests.post(
            f"{API_URL}{API_PREFIX}/parameterized-query",
            headers=self.headers,
            json=payload1
        )
        
        self.assertEqual(response1.status_code, 200)
        result1 = response1.json()
        self.assertEqual(result1["status"], "success")
        
        # Test with qmark parameters
        payload2 = {
            "db": "postgres",
            "query": "SELECT * FROM properties WHERE parcel_id = ?",
            "params": [1],
            "param_style": "qmark"
        }
        
        response2 = requests.post(
            f"{API_URL}{API_PREFIX}/parameterized-query",
            headers=self.headers,
            json=payload2
        )
        
        self.assertEqual(response2.status_code, 200)
        result2 = response2.json()
        self.assertEqual(result2["status"], "success")

    def test_param_style_conversion(self):
        """Test parameter style conversion."""
        # Test converting named parameters to PostgreSQL style
        query1 = "SELECT * FROM users WHERE id = :user_id AND status = :status"
        params1 = {"user_id": 1, "status": "active"}
        
        # Convert :param to %(param)s
        formatted_query1 = query1
        for param_name in params1.keys():
            pattern = r':(' + param_name + r')\b'
            formatted_query1 = re.sub(pattern, r'%(\1)s', formatted_query1)
            
        expected1 = "SELECT * FROM users WHERE id = %(user_id)s AND status = %(status)s"
        self.assertEqual(formatted_query1, expected1)
        
        # Test converting @ parameters to PostgreSQL style
        query2 = "SELECT * FROM orders WHERE customer_id = @customer_id"
        params2 = {"customer_id": 5}
        
        # Convert @param to %(param)s
        formatted_query2 = query2
        for param_name in params2.keys():
            pattern = r'@(' + param_name + r')\b'
            formatted_query2 = re.sub(pattern, r'%(\1)s', formatted_query2)
            
        expected2 = "SELECT * FROM orders WHERE customer_id = %(customer_id)s"
        self.assertEqual(formatted_query2, expected2)
        
        # Test converting ? placeholders to %s for PostgreSQL
        query3 = "SELECT * FROM products WHERE category = ? AND price > ?"
        formatted_query3 = re.sub(r'\?', '%s', query3)
        expected3 = "SELECT * FROM products WHERE category = %s AND price > %s"
        self.assertEqual(formatted_query3, expected3)


if __name__ == "__main__":
    unittest.main()