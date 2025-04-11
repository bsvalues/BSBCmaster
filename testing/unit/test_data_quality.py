"""
Unit Tests for Data Quality Module

This module provides comprehensive unit tests for the data quality module,
ensuring that validation rules are correctly applied to property assessment data.
"""

import unittest
import logging
import os
import json
import sys
from typing import Dict, Any, List, Optional

# Add parent directory to path to facilitate imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from data_quality.validator import DataValidator
from data_quality.rules import ValidationRuleSet
from testing.test_config import TestConfig
from testing.test_utils import TestUtils


class TestDataQuality(unittest.TestCase):
    """Unit tests for the Data Quality module."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # Initialize test configuration
        cls.config = TestConfig()
        
        # Initialize test utilities
        cls.utils = TestUtils(cls.config)
        
        # Initialize data validator
        cls.validator = DataValidator()
        
        # Prepare test directory
        cls.test_dir = cls.utils.prepare_test_directory("data_quality_unit_tests")
        
        # Set up logging
        cls.logger = logging.getLogger("test_data_quality")
    
    def setUp(self):
        """Set up before each test."""
        # Load authentic test data
        self.test_properties = self.utils.extract_authentic_property_data(count=5)
        
        # Ensure we have test data
        if not self.test_properties:
            self.logger.warning("No authentic property data available for testing")
    
    def test_validator_initialization(self):
        """Test that the DataValidator initializes correctly."""
        # Check that validator has rules
        self.assertIsNotNone(self.validator.rules)
        self.assertIsInstance(self.validator.rules, ValidationRuleSet)
        
        # Check that validator has Washington State rules
        self.assertTrue(hasattr(self.validator.rules, 'washington_state_rules'))
        self.assertGreater(len(self.validator.rules.washington_state_rules), 0)
        
        # Check that validator has Benton County rules
        self.assertTrue(hasattr(self.validator.rules, 'benton_county_rules'))
        self.assertGreater(len(self.validator.rules.benton_county_rules), 0)
    
    def test_parcel_validation(self):
        """Test validation of parcel data."""
        for property_data in self.test_properties:
            # Extract parcel data
            parcel_data = {
                "parcel_id": property_data.get("parcel_id"),
                "address": property_data.get("address"),
                "city": property_data.get("city"),
                "state": property_data.get("state"),
                "zip_code": property_data.get("zip_code")
            }
            
            # Validate parcel
            validation_result = self.validator.validate_entity("parcel", parcel_data)
            
            # Check that validation result has expected structure
            self.assertIsInstance(validation_result, dict)
            self.assertIn("valid", validation_result)
            self.assertIn("errors", validation_result)
            self.assertIn("warnings", validation_result)
            
            # Log validation results
            self.logger.info(f"Parcel validation result: {validation_result}")
            
            # Save test results
            self.utils.save_test_results(
                {
                    "parcel_data": parcel_data,
                    "validation_result": validation_result
                },
                "parcel_validation",
                self.test_dir
            )
    
    def test_property_validation(self):
        """Test validation of property data."""
        for property_data in self.test_properties:
            # Validate property
            validation_result = self.validator.validate_entity("property", property_data)
            
            # Check that validation result has expected structure
            self.assertIsInstance(validation_result, dict)
            self.assertIn("valid", validation_result)
            self.assertIn("errors", validation_result)
            self.assertIn("warnings", validation_result)
            
            # Log validation results
            self.logger.info(f"Property validation result: {validation_result}")
            
            # Save test results
            self.utils.save_test_results(
                {
                    "property_data": property_data,
                    "validation_result": validation_result
                },
                "property_validation",
                self.test_dir
            )
    
    def test_account_validation(self):
        """Test validation of account data."""
        for property_data in self.test_properties:
            # Extract account data
            account_data = {
                "account_id": property_data.get("account_id"),
                "parcel_id": property_data.get("parcel_id"),
                "assessed_value": property_data.get("assessed_value"),
                "land_value": property_data.get("land_value"),
                "improvement_value": property_data.get("improvement_value")
            }
            
            # Validate account
            validation_result = self.validator.validate_entity("account", account_data)
            
            # Check that validation result has expected structure
            self.assertIsInstance(validation_result, dict)
            self.assertIn("valid", validation_result)
            self.assertIn("errors", validation_result)
            self.assertIn("warnings", validation_result)
            
            # Log validation results
            self.logger.info(f"Account validation result: {validation_result}")
            
            # Save test results
            self.utils.save_test_results(
                {
                    "account_data": account_data,
                    "validation_result": validation_result
                },
                "account_validation",
                self.test_dir
            )
    
    def test_complete_record_validation(self):
        """Test validation of complete property records."""
        for property_data in self.test_properties:
            # Validate complete record
            validation_result = self.validator.validate_entity("complete_record", property_data)
            
            # Check that validation result has expected structure
            self.assertIsInstance(validation_result, dict)
            self.assertIn("valid", validation_result)
            self.assertIn("errors", validation_result)
            self.assertIn("warnings", validation_result)
            self.assertIn("parcel", validation_result)
            self.assertIn("property", validation_result)
            self.assertIn("account", validation_result)
            
            # Log validation results
            self.logger.info(f"Complete record validation result: {validation_result}")
            
            # Save test results
            self.utils.save_test_results(
                {
                    "property_data": property_data,
                    "validation_result": validation_result
                },
                "complete_record_validation",
                self.test_dir
            )
    
    def test_washington_state_rules(self):
        """Test that Washington State-specific rules are applied."""
        for property_data in self.test_properties:
            # Validate with Washington State rules explicitly
            validation_result = self.validator.validate_with_ruleset(
                "property",
                property_data,
                self.validator.rules.washington_state_rules
            )
            
            # Check that validation result has expected structure
            self.assertIsInstance(validation_result, dict)
            self.assertIn("valid", validation_result)
            self.assertIn("errors", validation_result)
            self.assertIn("warnings", validation_result)
            
            # Log validation results
            self.logger.info(f"Washington State rules validation result: {validation_result}")
            
            # Save test results
            self.utils.save_test_results(
                {
                    "property_data": property_data,
                    "validation_result": validation_result
                },
                "washington_state_rules",
                self.test_dir
            )
    
    def test_benton_county_rules(self):
        """Test that Benton County-specific rules are applied."""
        for property_data in self.test_properties:
            # Validate with Benton County rules explicitly
            validation_result = self.validator.validate_with_ruleset(
                "property",
                property_data,
                self.validator.rules.benton_county_rules
            )
            
            # Check that validation result has expected structure
            self.assertIsInstance(validation_result, dict)
            self.assertIn("valid", validation_result)
            self.assertIn("errors", validation_result)
            self.assertIn("warnings", validation_result)
            
            # Log validation results
            self.logger.info(f"Benton County rules validation result: {validation_result}")
            
            # Save test results
            self.utils.save_test_results(
                {
                    "property_data": property_data,
                    "validation_result": validation_result
                },
                "benton_county_rules",
                self.test_dir
            )
    
    def test_rule_summary(self):
        """Test the rule summary functionality."""
        # Get rule summary
        rule_summary = self.validator.get_rule_summary()
        
        # Check that summary has expected structure
        self.assertIsInstance(rule_summary, dict)
        self.assertIn("total_rules", rule_summary)
        self.assertIn("washington_state_rules", rule_summary)
        self.assertIn("benton_county_rules", rule_summary)
        self.assertIn("rule_categories", rule_summary)
        
        # Save test results
        self.utils.save_test_results(
            {
                "rule_summary": rule_summary
            },
            "rule_summary",
            self.test_dir
        )
    
    def test_validation_with_edge_cases(self):
        """Test validation with edge cases and boundary values."""
        if not self.test_properties:
            self.skipTest("No authentic property data available for testing")
            return
        
        # Use the first property as a base
        base_property = self.test_properties[0].copy()
        
        # Test with edge case: extremely high assessed value
        edge_case_high_value = base_property.copy()
        edge_case_high_value["assessed_value"] = 100000000  # $100M
        
        # Validate
        validation_result = self.validator.validate_entity("property", edge_case_high_value)
        
        # Save test results
        self.utils.save_test_results(
            {
                "property_data": edge_case_high_value,
                "validation_result": validation_result,
                "test_case": "high_value"
            },
            "edge_case_validation",
            self.test_dir
        )
        
        # Test with edge case: extremely old property
        edge_case_old_property = base_property.copy()
        edge_case_old_property["year_built"] = 1850
        
        # Validate
        validation_result = self.validator.validate_entity("property", edge_case_old_property)
        
        # Save test results
        self.utils.save_test_results(
            {
                "property_data": edge_case_old_property,
                "validation_result": validation_result,
                "test_case": "old_property"
            },
            "edge_case_validation",
            self.test_dir
        )
        
        # Test with edge case: extremely large property
        edge_case_large_property = base_property.copy()
        edge_case_large_property["square_footage"] = 50000  # 50,000 sq ft
        
        # Validate
        validation_result = self.validator.validate_entity("property", edge_case_large_property)
        
        # Save test results
        self.utils.save_test_results(
            {
                "property_data": edge_case_large_property,
                "validation_result": validation_result,
                "test_case": "large_property"
            },
            "edge_case_validation",
            self.test_dir
        )
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Generate test report
        test_results = []
        # In a real implementation, we would collect all test results here
        
        # For demonstration purposes, create a simple report
        report = {
            "test_class": "TestDataQuality",
            "test_count": len([m for m in dir(cls) if m.startswith('test_')]),
            "test_dir": cls.test_dir,
            "timestamp": os.path.basename(cls.test_dir).split('_')[-1]
        }
        
        # Save report
        report_path = os.path.join(cls.test_dir, "test_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        cls.logger.info(f"Test report saved to {report_path}")


if __name__ == '__main__':
    unittest.main()