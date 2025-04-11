"""
Test Module for Data Quality and Compliance

This module provides tests for the data quality and compliance validation functionality.
"""

import unittest
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from .validator import DataValidator, ValidationResult
from .rules import PropertyRules, WashingtonStateStandards, BentonCountyRules


class DataValidatorTests(unittest.TestCase):
    """Test cases for data quality validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.wa_validator = DataValidator(use_benton_rules=False)
        self.benton_validator = DataValidator(use_benton_rules=True)
        
        # Create valid test data
        self.valid_parcel = {
            'parcel_id': '12345678-1234',
            'address': '123 Main St',
            'city': 'Richland',
            'state': 'WA',
            'zip_code': '99352',
            'land_value': 100000,
            'improvement_value': 200000,
            'total_value': 300000,
            'assessment_year': 2024,
            'latitude': 46.2,
            'longitude': -119.2
        }
        
        self.valid_property = {
            'property_type': 'Residential',
            'year_built': 2000,
            'square_footage': 2500,
            'bedrooms': 3,
            'bathrooms': 2.5,
            'lot_size': 8000,
            'lot_size_unit': 'sq ft',
            'stories': 2,
            'condition': 'Good',
            'quality': 'Good'
        }
        
        self.valid_account = {
            'account_id': 'ACC-12345',
            'owner_name': 'John Doe',
            'mailing_address': '123 Main St',
            'mailing_city': 'Richland',
            'mailing_state': 'WA',
            'mailing_zip': '99352',
            'property_address': '123 Main St',
            'assessed_value': 300000,
            'tax_amount': 3150
        }
    
    def test_valid_parcel(self):
        """Test validation of a valid parcel."""
        result = self.wa_validator.validate_parcel(self.valid_parcel)
        self.assertTrue(result.valid, f"Expected valid parcel but got errors: {result.errors}")
        self.assertEqual(len(result.errors), 0)
    
    def test_invalid_parcel(self):
        """Test validation of an invalid parcel."""
        # Missing required fields
        invalid_parcel = self.valid_parcel.copy()
        invalid_parcel.pop('parcel_id')
        invalid_parcel.pop('address')
        
        result = self.wa_validator.validate_parcel(invalid_parcel)
        self.assertFalse(result.valid)
        self.assertGreaterEqual(len(result.errors), 2)
        
        # Field with pattern error
        invalid_parcel = self.valid_parcel.copy()
        invalid_parcel['parcel_id'] = 'invalid-id'
        
        result = self.wa_validator.validate_parcel(invalid_parcel)
        self.assertFalse(result.valid)
        
        # Value range error
        invalid_parcel = self.valid_parcel.copy()
        invalid_parcel['land_value'] = -1000
        
        result = self.wa_validator.validate_parcel(invalid_parcel)
        self.assertFalse(result.valid)
    
    def test_valid_property(self):
        """Test validation of a valid property."""
        result = self.wa_validator.validate_property(self.valid_property)
        self.assertTrue(result.valid, f"Expected valid property but got errors: {result.errors}")
        self.assertEqual(len(result.errors), 0)
    
    def test_invalid_property(self):
        """Test validation of an invalid property."""
        # Missing required field
        invalid_property = self.valid_property.copy()
        invalid_property.pop('property_type')
        
        result = self.wa_validator.validate_property(invalid_property)
        self.assertFalse(result.valid)
        
        # Invalid property type
        invalid_property = self.valid_property.copy()
        invalid_property['property_type'] = 'InvalidType'
        
        result = self.wa_validator.validate_property(invalid_property)
        self.assertFalse(result.valid)
        
        # Value range error
        invalid_property = self.valid_property.copy()
        invalid_property['year_built'] = 1700
        
        result = self.wa_validator.validate_property(invalid_property)
        self.assertFalse(result.valid)
    
    def test_valid_account(self):
        """Test validation of a valid account."""
        result = self.wa_validator.validate_account(self.valid_account)
        self.assertTrue(result.valid, f"Expected valid account but got errors: {result.errors}")
        self.assertEqual(len(result.errors), 0)
    
    def test_invalid_account(self):
        """Test validation of an invalid account."""
        # Missing required fields
        invalid_account = self.valid_account.copy()
        invalid_account.pop('account_id')
        invalid_account.pop('owner_name')
        
        result = self.wa_validator.validate_account(invalid_account)
        self.assertFalse(result.valid)
        self.assertGreaterEqual(len(result.errors), 2)
        
        # Value range error
        invalid_account = self.valid_account.copy()
        invalid_account['assessed_value'] = -1000
        
        result = self.wa_validator.validate_account(invalid_account)
        self.assertFalse(result.valid)
    
    def test_complete_record_validation(self):
        """Test validation of a complete record."""
        # Create a valid complete record
        valid_record = {
            'parcel': self.valid_parcel,
            'property': self.valid_property,
            'account': self.valid_account
        }
        
        overall_valid, results = self.wa_validator.validate_complete_record(valid_record)
        self.assertTrue(overall_valid, "Expected valid complete record")
        self.assertTrue(results['parcel'].valid)
        self.assertTrue(results['property'].valid)
        self.assertTrue(results['account'].valid)
        self.assertTrue(results['cross_entity'].valid)
        
        # Create an invalid complete record with inconsistent addresses
        invalid_record = valid_record.copy()
        invalid_record['account'] = self.valid_account.copy()
        invalid_record['account']['property_address'] = 'Different Address'
        
        overall_valid, results = self.wa_validator.validate_complete_record(invalid_record)
        self.assertFalse(overall_valid, "Expected invalid complete record")
        self.assertTrue(results['parcel'].valid)
        self.assertTrue(results['property'].valid)
        self.assertTrue(results['account'].valid)
        self.assertFalse(results['cross_entity'].valid)
    
    def test_benton_county_rules(self):
        """Test Benton County specific validation rules."""
        # Create data that would be valid for WA but invalid for Benton
        benton_invalid_parcel = self.valid_parcel.copy()
        benton_invalid_parcel['parcel_id'] = '12345678-1234'  # Valid for WA but not Benton
        
        # Valid for WA
        wa_result = self.wa_validator.validate_parcel(benton_invalid_parcel)
        self.assertTrue(wa_result.valid, "Expected valid parcel for WA state")
        
        # Invalid for Benton
        benton_result = self.benton_validator.validate_parcel(benton_invalid_parcel)
        self.assertFalse(benton_result.valid, "Expected invalid parcel for Benton County")
        
        # Create a valid Benton County parcel
        benton_valid_parcel = self.valid_parcel.copy()
        benton_valid_parcel['parcel_id'] = '1-1234567-123-1234-12'
        
        benton_result = self.benton_validator.validate_parcel(benton_valid_parcel)
        self.assertTrue(benton_result.valid, 
                        f"Expected valid Benton County parcel but got errors: {benton_result.errors}")


def run_tests():
    """Run the data quality validation tests."""
    unittest.main(module='data_quality.tests')