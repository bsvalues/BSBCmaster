"""
Data Validator Module for Benton County Assessor's Office

This module provides validation functionality for property assessment data
based on the rules defined in the rules module.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from .rules import PropertyRules, WashingtonStateStandards, BentonCountyRules

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationResult:
    """Class to represent validation results."""
    
    def __init__(self, valid: bool = True, errors: Optional[List[Dict[str, str]]] = None):
        """
        Initialize validation result.
        
        Args:
            valid: Whether the validation passed
            errors: List of validation errors
        """
        self.valid = valid
        self.errors = errors if errors is not None else []
        self.timestamp = datetime.utcnow().isoformat()
    
    def add_error(self, field: str, message: str):
        """
        Add an error to the validation result.
        
        Args:
            field: Name of the field with the error
            message: Error message
        """
        self.errors.append({
            'field': field,
            'message': message
        })
        self.valid = False
    
    def add_errors(self, errors: List[Dict[str, str]]):
        """
        Add multiple errors to the validation result.
        
        Args:
            errors: List of error dictionaries
        """
        if errors:
            self.errors.extend(errors)
            self.valid = False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert validation result to a dictionary.
        
        Returns:
            Dictionary representation of the validation result
        """
        return {
            'valid': self.valid,
            'errors': self.errors,
            'timestamp': self.timestamp
        }
    
    def to_json(self) -> str:
        """
        Convert validation result to JSON.
        
        Returns:
            JSON string representation of the validation result
        """
        return json.dumps(self.to_dict())
    
    def __bool__(self) -> bool:
        """Return True if validation passed, False otherwise."""
        return self.valid
    
    def __str__(self) -> str:
        """Return string representation of the validation result."""
        if self.valid:
            return "Validation passed"
        else:
            return f"Validation failed with {len(self.errors)} errors"


class DataValidator:
    """
    Data validator for property assessment data.
    
    This class provides methods to validate property assessment data against
    Washington State Department of Revenue standards and Benton County regulations.
    """
    
    def __init__(self, use_benton_rules: bool = True):
        """
        Initialize the data validator.
        
        Args:
            use_benton_rules: Whether to use Benton County specific rules
                              in addition to Washington State standards
        """
        if use_benton_rules:
            self.rules = BentonCountyRules()
            logger.info("Using Benton County specific rules for validation")
        else:
            self.rules = WashingtonStateStandards()
            logger.info("Using Washington State standards for validation")
    
    def validate_entity(self, data: Dict[str, Any], entity_type: str) -> ValidationResult:
        """
        Validate an entity against appropriate rules.
        
        Args:
            data: Dictionary containing entity data
            entity_type: Type of entity ('parcel', 'property', 'account')
            
        Returns:
            ValidationResult object containing validation results
        """
        if entity_type not in ['parcel', 'property', 'account']:
            result = ValidationResult(valid=False)
            result.add_error('entity_type', f'Unknown entity type: {entity_type}')
            return result
        
        try:
            # Apply all validation rules
            errors = self.rules.validate(data, entity_type)
            
            # Create validation result
            result = ValidationResult(valid=len(errors) == 0)
            result.add_errors(errors)
            
            return result
        except Exception as e:
            logger.error(f"Error validating {entity_type}: {str(e)}")
            result = ValidationResult(valid=False)
            result.add_error('validation', f'Validation error: {str(e)}')
            return result
    
    def validate_parcel(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate parcel data.
        
        Args:
            data: Dictionary containing parcel data
            
        Returns:
            ValidationResult object containing validation results
        """
        return self.validate_entity(data, 'parcel')
    
    def validate_property(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate property data.
        
        Args:
            data: Dictionary containing property data
            
        Returns:
            ValidationResult object containing validation results
        """
        return self.validate_entity(data, 'property')
    
    def validate_account(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate account data.
        
        Args:
            data: Dictionary containing account data
            
        Returns:
            ValidationResult object containing validation results
        """
        return self.validate_entity(data, 'account')
    
    def validate_all(self, data: Dict[str, Dict[str, Any]]) -> Dict[str, ValidationResult]:
        """
        Validate multiple entity types at once.
        
        Args:
            data: Dictionary mapping entity types to entity data
            
        Returns:
            Dictionary mapping entity types to ValidationResult objects
        """
        results = {}
        
        for entity_type, entity_data in data.items():
            if entity_type in ['parcel', 'property', 'account']:
                results[entity_type] = self.validate_entity(entity_data, entity_type)
            else:
                result = ValidationResult(valid=False)
                result.add_error('entity_type', f'Unknown entity type: {entity_type}')
                results[entity_type] = result
        
        return results
    
    def validate_complete_record(self, record: Dict[str, Any]) -> Tuple[bool, Dict[str, ValidationResult]]:
        """
        Validate a complete record containing parcel, property, and account data.
        
        Args:
            record: Dictionary containing 'parcel', 'property', and 'account' keys
            
        Returns:
            Tuple of (overall_valid, validation_results)
        """
        results = {}
        overall_valid = True
        
        # Validate each entity type if present
        for entity_type in ['parcel', 'property', 'account']:
            if entity_type in record:
                result = self.validate_entity(record[entity_type], entity_type)
                results[entity_type] = result
                if not result:
                    overall_valid = False
        
        # Check for missing required entity types
        for entity_type in ['parcel', 'property', 'account']:
            if entity_type not in record:
                result = ValidationResult(valid=False)
                result.add_error('missing', f'Missing {entity_type} data')
                results[entity_type] = result
                overall_valid = False
        
        # Apply cross-entity validation
        cross_entity_result = self._validate_cross_entity(record)
        results['cross_entity'] = cross_entity_result
        if not cross_entity_result:
            overall_valid = False
        
        return overall_valid, results
    
    def _validate_cross_entity(self, record: Dict[str, Any]) -> ValidationResult:
        """
        Validate relationships between different entity types.
        
        Args:
            record: Dictionary containing 'parcel', 'property', and 'account' keys
            
        Returns:
            ValidationResult for cross-entity validation
        """
        result = ValidationResult()
        
        # Check if parcel and account have matching property addresses
        if 'parcel' in record and 'account' in record:
            parcel_data = record['parcel']
            account_data = record['account']
            
            if 'address' in parcel_data and 'property_address' in account_data:
                parcel_address = parcel_data['address']
                account_address = account_data['property_address']
                
                if parcel_address and account_address and parcel_address != account_address:
                    result.add_error(
                        'address_consistency',
                        'Parcel address does not match account property address'
                    )
        
        # Check if parcel_id references match
        if 'parcel' in record and 'property' in record:
            parcel_data = record['parcel']
            property_data = record['property']
            
            if 'parcel_id' in parcel_data and 'parcel_id' in property_data:
                parcel_id = parcel_data['parcel_id']
                property_parcel_id = property_data['parcel_id']
                
                if parcel_id and property_parcel_id and parcel_id != property_parcel_id:
                    result.add_error(
                        'parcel_id_consistency',
                        'Property parcel_id does not match parcel identifier'
                    )
        
        # Check if assessed values match
        if 'parcel' in record and 'account' in record:
            parcel_data = record['parcel']
            account_data = record['account']
            
            if 'total_value' in parcel_data and 'assessed_value' in account_data:
                parcel_value = parcel_data['total_value']
                account_value = account_data['assessed_value']
                
                if parcel_value is not None and account_value is not None:
                    try:
                        parcel_value = float(parcel_value)
                        account_value = float(account_value)
                        
                        # Allow for small rounding differences
                        if abs(parcel_value - account_value) > 1.0:
                            result.add_error(
                                'value_consistency',
                                'Parcel total value does not match account assessed value'
                            )
                    except (ValueError, TypeError):
                        result.add_error(
                            'value_format',
                            'Unable to compare parcel total value and account assessed value'
                        )
        
        return result