"""
Unit Tests for Valuation Agent

This module contains unit tests for the Valuation Agent component
of the Benton County Assessor's Office AI Platform.
"""

import unittest
import logging
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime

from mcp.agents.valuation.agent import ValuationAgent
from mcp.message import Message, MessageType

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestValuationAgent(unittest.TestCase):
    """Test suite for the Valuation Agent."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock for app_setup.db
        self.db_patcher = patch('app_setup.db')
        self.mock_db = self.db_patcher.start()
        
        # Configure the mock database
        self.mock_engine = MagicMock()
        self.mock_connection = MagicMock()
        self.mock_engine.connect.return_value.__enter__.return_value = self.mock_connection
        self.mock_db.engine = self.mock_engine
        
        # Create the agent instance
        self.agent = ValuationAgent(agent_id="test_valuation_agent")
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.db_patcher.stop()
    
    def test_init(self):
        """Test initialization of the Valuation Agent."""
        self.assertEqual(self.agent.agent_id, "test_valuation_agent")
        self.assertIsNotNone(self.agent.metadata)
        self.assertIn("cost_approach", self.agent.metadata["capabilities"])
        self.assertIn("market_comparison", self.agent.metadata["capabilities"])
        self.assertIn("income_approach", self.agent.metadata["capabilities"])
    
    def test_load_reference_data(self):
        """Test loading of reference data."""
        # Check that reference data was loaded during initialization
        self.assertIsNotNone(self.agent._cost_tables)
        self.assertIsNotNone(self.agent._depreciation_tables)
        self.assertIsNotNone(self.agent._market_adjustment_factors)
        self.assertIsNotNone(self.agent._cap_rates)
        
        # Check specific values
        self.assertIn("Residential", self.agent._cost_tables)
        self.assertIn("Commercial", self.agent._cost_tables)
        self.assertIn("Agricultural", self.agent._cost_tables)
        
        self.assertIn("0-5", self.agent._depreciation_tables)
        self.assertIn("41+", self.agent._depreciation_tables)
        
        self.assertIn("Richland", self.agent._market_adjustment_factors)
        self.assertIn("default", self.agent._market_adjustment_factors)
        
        self.assertIn("Residential", self.agent._cap_rates)
        self.assertIn("default", self.agent._cap_rates)
    
    @patch('mcp.agents.valuation.agent.ValuationAgent.send_message')
    def test_handle_valuation_request_property_not_found(self, mock_send_message):
        """Test handling of valuation request when property is not found."""
        # Create a message with a non-existent property
        message = MagicMock()
        message.source_agent_id = "test_sender"
        message.message_id = "test_message_id"
        message.content = {
            "property_id": 999999,  # Non-existent property
            "methodology": "all"
        }
        # Mock the create_response method
        response = MagicMock()
        message.create_response.return_value = response
        
        # Configure the mock to return None for property query
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        self.mock_connection.execute.return_value = mock_result
        
        # Call the handler
        self.agent._handle_valuation_request(message)
        
        # Check that send_message was called with response message
        mock_send_message.assert_called_once()
        response_message = mock_send_message.call_args[0][0]
        
        # Check that the message was created using message.create_response
        message.create_response.assert_called_once()
    
    @patch('mcp.agents.valuation.agent.ValuationAgent._calculate_cost_approach')
    @patch('mcp.agents.valuation.agent.ValuationAgent.send_message')
    def test_handle_valuation_request_cost_approach(self, mock_send_message, mock_calculate_cost):
        """Test handling of valuation request using cost approach."""
        # Create a message requesting cost approach valuation
        message = MagicMock()
        message.source_agent_id = "test_sender"
        message.message_id = "test_message_id"
        message.content = {
            "property_id": 1,
            "methodology": "cost"
        }
        # Mock the create_response method
        response = MagicMock()
        message.create_response.return_value = response
        
        # Mock the cost approach calculation to return a predefined value
        mock_calculate_cost.return_value = {
            "total_value": 350000,
            "details": {
                "replacement_cost": 400000,
                "depreciation_rate": 0.15,
                "depreciation_amount": 60000,
                "depreciated_cost": 340000,
                "location_factor": 1.1,
                "adjusted_cost": 374000,
                "land_value": 75000
            }
        }
        
        # Configure the mock to return a property
        mock_result = MagicMock()
        property_row = MagicMock()
        property_row._mapping = {
            "id": 1,
            "account_id": 1,
            "property_type": "Residential",
            "living_area": 2000,
            "bedrooms": 3,
            "bathrooms": 2,
            "year_built": 2000,
            "quality": "Good",
            "city": "Richland"
        }
        
        mock_result.fetchone.return_value = property_row
        self.mock_connection.execute.return_value = mock_result
        
        # Call the handler
        self.agent._handle_valuation_request(message)
        
        # Check that calculation was called with property details
        mock_calculate_cost.assert_called_once()
        
        # Check that send_message was called with response message
        mock_send_message.assert_called_once()
        response_message = mock_send_message.call_args[0][0]
        
        # Check that the message was created using message.create_response
        message.create_response.assert_called_once()
        
        # Verify proper arguments were passed to create_response
        args, kwargs = message.create_response.call_args
        content = kwargs.get("content", {})
        self.assertTrue(content.get("success", False))
        self.assertEqual(content.get("property_id"), 1)
        self.assertIn("cost_approach", content.get("results", {}))
        self.assertEqual(content.get("results", {}).get("cost_approach", {}).get("total_value"), 350000)
    
    def test_calculate_cost_approach(self):
        """Test calculation of property value using cost approach."""
        # Create sample property details
        property_details = {
            "property_type": "Residential",
            "quality": "Good",
            "living_area": 2000,
            "year_built": 2010,
            "city": "Richland"
        }
        
        # Calculate value
        result = self.agent._calculate_cost_approach(property_details)
        
        # Check result structure
        self.assertIn("total_value", result)
        self.assertIn("details", result)
        self.assertIn("replacement_cost", result["details"])
        self.assertIn("depreciation_rate", result["details"])
        self.assertIn("depreciation_amount", result["details"])
        self.assertIn("depreciated_cost", result["details"])
        self.assertIn("location_factor", result["details"])
        self.assertIn("adjusted_cost", result["details"])
        self.assertIn("land_value", result["details"])
        
        # Check that the result is positive
        self.assertGreater(result["total_value"], 0)
        
        # Test with different property type
        property_details["property_type"] = "Commercial"
        result = self.agent._calculate_cost_approach(property_details)
        self.assertGreater(result["total_value"], 0)
        
        # Test with different quality
        property_details["quality"] = "Excellent"
        result = self.agent._calculate_cost_approach(property_details)
        self.assertGreater(result["total_value"], 0)
        
        # Test with different city
        property_details["city"] = "Kennewick"
        result = self.agent._calculate_cost_approach(property_details)
        self.assertGreater(result["total_value"], 0)
        
        # Test with very old building (high depreciation)
        property_details["year_built"] = 1960
        result = self.agent._calculate_cost_approach(property_details)
        self.assertGreater(result["total_value"], 0)
        
        # Test with invalid property type (should default to Residential)
        property_details["property_type"] = "Invalid"
        result = self.agent._calculate_cost_approach(property_details)
        self.assertGreater(result["total_value"], 0)
    
    @patch('mcp.agents.valuation.agent.ValuationAgent._calculate_cost_approach')
    @patch('mcp.agents.valuation.agent.ValuationAgent.send_message')
    def test_handle_trend_analysis_request(self, mock_send_message, mock_calculate_cost):
        """Test handling of trend analysis request."""
        # Create a message requesting trend analysis
        message = MagicMock()
        message.source_agent_id = "test_sender"
        message.message_id = "test_message_id"
        message.content = {
            "property_id": 1,
            "years": 3
        }
        # Mock the create_response method
        response = MagicMock()
        message.create_response.return_value = response
        
        # Mock the cost approach calculation to return a predefined value
        mock_calculate_cost.return_value = {
            "total_value": 350000,
            "details": {}
        }
        
        # Configure the mock to return a property
        mock_result = MagicMock()
        property_row = MagicMock()
        property_row._mapping = {
            "id": 1,
            "account_id": 1,
            "property_type": "Residential",
            "living_area": 2000,
            "bedrooms": 3,
            "bathrooms": 2,
            "year_built": 2000,
            "quality": "Good",
            "city": "Richland"
        }
        
        mock_result.fetchone.return_value = property_row
        self.mock_connection.execute.return_value = mock_result
        
        # Call the handler
        self.agent._handle_trend_analysis_request(message)
        
        # Check that send_message was called with response message
        mock_send_message.assert_called_once()
        response_message = mock_send_message.call_args[0][0]
        
        # Check that the message was created using message.create_response
        message.create_response.assert_called_once()
        
        # Verify proper arguments were passed to create_response
        args, kwargs = message.create_response.call_args
        content = kwargs.get("content", {})
        self.assertTrue(content.get("success", False))
        self.assertEqual(content.get("property_id"), 1)
        self.assertIn("trend_data", content)
        self.assertIsInstance(content.get("trend_data"), list)
        
        # Check that the trend data covers the requested years
        trend_data = content.get("trend_data", [])
        years_covered = len(set(item["year"] for item in trend_data))
        self.assertGreaterEqual(years_covered, 3)
    
    def test_generate_trend_data(self):
        """Test generation of trend data."""
        # Create sample property details
        property_details = {
            "property_type": "Residential",
            "city": "Richland"
        }
        
        # Generate trend data
        current_value = 350000
        years = 3
        trend_data = self.agent._generate_trend_data(property_details, current_value, years)
        
        # Check result structure
        self.assertIsInstance(trend_data, list)
        self.assertEqual(len(trend_data), years * 2)  # Past and future values
        
        # Check that each data point has the required fields
        for point in trend_data:
            self.assertIn("year", point)
            self.assertIn("value", point)
            self.assertIn("growth_rate", point)
            
            # Check that values are reasonable
            self.assertGreater(point["value"], 0)
            self.assertGreater(point["growth_rate"], 0)
        
        # Check that values increase over time
        years = [point["year"] for point in trend_data]
        values = [point["value"] for point in trend_data]
        
        self.assertEqual(years, sorted(years))
        
        # Check that nearby years have reasonable differences
        for i in range(1, len(values)):
            # Allow for decreasing values in past years (reverse growth)
            if years[i] < datetime.now().year:
                continue
            
            # Future years should have increasing values
            self.assertGreaterEqual(values[i], values[i-1])
    
    @patch('mcp.agents.valuation.agent.ValuationAgent._calculate_cost_approach')
    @patch('mcp.agents.valuation.agent.ValuationAgent.send_message')
    def test_handle_comparative_analysis_request(self, mock_send_message, mock_calculate_cost):
        """Test handling of comparative analysis request."""
        # Create a message requesting comparative analysis
        message = MagicMock()
        message.source_agent_id = "test_sender"
        message.message_id = "test_message_id"
        message.content = {
            "property_id": 1,
            "comparison_property_ids": [2, 3]
        }
        # Mock the create_response method
        response = MagicMock()
        message.create_response.return_value = response
        
        # Mock the cost approach calculation to return predefined values
        mock_calculate_cost.side_effect = [
            {"total_value": 350000, "details": {}},  # Subject property
            {"total_value": 330000, "details": {}},  # Comp 1
            {"total_value": 370000, "details": {}}   # Comp 2
        ]
        
        # Subject property query result
        subject_result = MagicMock()
        subject_row = MagicMock()
        subject_row._mapping = {
            "id": 1,
            "account_id": 1,
            "property_type": "Residential",
            "living_area": 2000,
            "bedrooms": 3,
            "bathrooms": 2,
            "year_built": 2000,
            "quality": "Good",
            "city": "Richland",
            "address": "123 Main St"
        }
        subject_result.fetchone.return_value = subject_row
        
        # Comp 1 property query result
        comp1_result = MagicMock()
        comp1_row = MagicMock()
        comp1_row._mapping = {
            "id": 2,
            "account_id": 2,
            "property_type": "Residential",
            "living_area": 1900,
            "bedrooms": 3,
            "bathrooms": 2,
            "year_built": 2002,
            "quality": "Good",
            "city": "Richland",
            "address": "456 Oak St"
        }
        comp1_result.fetchone.return_value = comp1_row
        
        # Comp 2 property query result
        comp2_result = MagicMock()
        comp2_row = MagicMock()
        comp2_row._mapping = {
            "id": 3,
            "account_id": 3,
            "property_type": "Residential",
            "living_area": 2100,
            "bedrooms": 4,
            "bathrooms": 2,
            "year_built": 1998,
            "quality": "Good",
            "city": "Richland",
            "address": "789 Pine St"
        }
        comp2_result.fetchone.return_value = comp2_row
        
        # Configure mock connection to return different results for different queries
        self.mock_connection.execute.side_effect = [subject_result, comp1_result, comp2_result]
        
        # Call the handler
        self.agent._handle_comparative_analysis_request(message)
        
        # Check that send_message was called with response message
        mock_send_message.assert_called_once()
        response_message = mock_send_message.call_args[0][0]
        
        # Check that the message was created using message.create_response
        message.create_response.assert_called_once()
        
        # Verify proper arguments were passed to create_response
        args, kwargs = message.create_response.call_args
        content = kwargs.get("content", {})
        self.assertTrue(content.get("success", False))
        self.assertEqual(content.get("property_id"), 1)
        self.assertIn("subject_property", content)
        self.assertIn("comparison_properties", content)
        self.assertIn("metrics", content)
        
        # Check comparison properties
        self.assertEqual(len(content.get("comparison_properties", [])), 2)
        
        # Check metrics
        metrics = content.get("metrics", {})
        self.assertIn("comparison_count", metrics)
        self.assertIn("subject_value", metrics)
        self.assertIn("average_comp_value", metrics)
        self.assertEqual(metrics.get("comparison_count"), 2)
    
    def test_calculate_comparison_metrics(self):
        """Test calculation of comparison metrics."""
        # Create sample properties
        subject_property = {
            "id": 1,
            "living_area": 2000,
            "bedrooms": 3,
            "bathrooms": 2,
            "year_built": 2000,
            "city": "Richland"
        }
        
        comparison_properties = [
            {
                "id": 2,
                "living_area": 1900,
                "bedrooms": 3,
                "bathrooms": 2,
                "year_built": 2002,
                "city": "Richland",
                "calculated_value": 330000
            },
            {
                "id": 3,
                "living_area": 2100,
                "bedrooms": 4,
                "bathrooms": 2,
                "year_built": 1998,
                "city": "Richland",
                "calculated_value": 370000
            }
        ]
        
        subject_value = 350000
        
        # Calculate metrics
        result = self.agent._calculate_comparison_metrics(subject_property, subject_value, comparison_properties)
        
        # Check result structure
        self.assertIn("comparison_count", result)
        self.assertIn("subject_value", result)
        self.assertIn("subject_value_per_sqft", result)
        self.assertIn("average_comp_value", result)
        self.assertIn("median_comp_value", result)
        self.assertIn("min_comp_value", result)
        self.assertIn("max_comp_value", result)
        self.assertIn("percentile_rank", result)
        
        # Check values
        self.assertEqual(result["comparison_count"], 2)
        self.assertEqual(result["subject_value"], 350000)
        self.assertEqual(result["subject_value_per_sqft"], 350000 / 2000)
        self.assertEqual(result["average_comp_value"], (330000 + 370000) / 2)
        # For even-length lists, median is the value at index length//2 which is 370000 for our test
        self.assertEqual(result["median_comp_value"], 370000)
        self.assertEqual(result["min_comp_value"], 330000)
        self.assertEqual(result["max_comp_value"], 370000)
        
        # Test with empty comparison properties
        result = self.agent._calculate_comparison_metrics(subject_property, subject_value, [])
        self.assertIn("error", result)


if __name__ == '__main__':
    unittest.main()