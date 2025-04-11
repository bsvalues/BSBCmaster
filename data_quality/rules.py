"""
Washington State Department of Revenue and Benton County Property Assessment Rules

This module defines validation rules for property assessment data based on
Washington State Department of Revenue standards and Benton County regulations.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional, Union, Pattern

class PropertyRules:
    """Base class for property assessment validation rules."""
    
    def __init__(self):
        """Initialize base property rules."""
        self.required_fields = {}
        self.field_patterns = {}
        self.allowed_values = {}
        self.value_ranges = {}
        self.custom_validators = {}
        self.consistency_checks = {}
    
    def validate_field_existence(self, data: Dict[str, Any], entity_type: str) -> List[Dict[str, str]]:
        """Validate that all required fields exist."""
        errors = []
        required = self.required_fields.get(entity_type, {})
        
        for field, required_flag in required.items():
            if required_flag and (field not in data or data[field] is None or data[field] == ''):
                errors.append({
                    'field': field,
                    'message': f'{field} is required for {entity_type}'
                })
        
        return errors
    
    def validate_field_patterns(self, data: Dict[str, Any], entity_type: str) -> List[Dict[str, str]]:
        """Validate that fields match specified patterns."""
        errors = []
        patterns = self.field_patterns.get(entity_type, {})
        
        for field, pattern_info in patterns.items():
            if field in data and data[field]:
                pattern = pattern_info.get('pattern')
                message = pattern_info.get('message', f'{field} has invalid format')
                
                if isinstance(pattern, Pattern) and not pattern.match(str(data[field])):
                    errors.append({
                        'field': field,
                        'message': message
                    })
                elif isinstance(pattern, str) and not re.match(pattern, str(data[field])):
                    errors.append({
                        'field': field,
                        'message': message
                    })
        
        return errors
    
    def validate_allowed_values(self, data: Dict[str, Any], entity_type: str) -> List[Dict[str, str]]:
        """Validate that fields have allowed values."""
        errors = []
        allowed = self.allowed_values.get(entity_type, {})
        
        for field, value_info in allowed.items():
            if field in data and data[field] is not None:
                allowed_values = value_info.get('values', [])
                message = value_info.get('message', f'{field} has invalid value')
                
                if data[field] not in allowed_values:
                    errors.append({
                        'field': field,
                        'message': message
                    })
        
        return errors
    
    def validate_value_ranges(self, data: Dict[str, Any], entity_type: str) -> List[Dict[str, str]]:
        """Validate that numeric fields fall within specified ranges."""
        errors = []
        ranges = self.value_ranges.get(entity_type, {})
        
        for field, range_info in ranges.items():
            if field in data and data[field] is not None:
                try:
                    value = float(data[field])
                    
                    if 'min' in range_info and value < range_info['min']:
                        errors.append({
                            'field': field,
                            'message': range_info.get('message', f'{field} is below minimum value')
                        })
                    
                    if 'max' in range_info and value > range_info['max']:
                        errors.append({
                            'field': field,
                            'message': range_info.get('message', f'{field} exceeds maximum value')
                        })
                except (ValueError, TypeError):
                    errors.append({
                        'field': field,
                        'message': f'{field} must be a valid number'
                    })
        
        return errors
    
    def apply_custom_validators(self, data: Dict[str, Any], entity_type: str) -> List[Dict[str, str]]:
        """Apply custom validation functions."""
        errors = []
        validators = self.custom_validators.get(entity_type, {})
        
        for field, validator_info in validators.items():
            validator_func = validator_info.get('validator')
            message = validator_info.get('message', f'{field} validation failed')
            
            if field in data and validator_func and not validator_func(data[field], data):
                errors.append({
                    'field': field,
                    'message': message
                })
        
        return errors
    
    def check_consistency(self, data: Dict[str, Any], entity_type: str) -> List[Dict[str, str]]:
        """Validate consistency between fields."""
        errors = []
        checks = self.consistency_checks.get(entity_type, [])
        
        for check_info in checks:
            check_func = check_info.get('validator')
            message = check_info.get('message', 'Consistency check failed')
            
            if check_func and not check_func(data):
                errors.append({
                    'field': check_info.get('fields', ['consistency']),
                    'message': message
                })
        
        return errors
    
    def validate(self, data: Dict[str, Any], entity_type: str) -> List[Dict[str, str]]:
        """
        Validate entity data against all applicable rules.
        
        Args:
            data: Dictionary with entity data
            entity_type: Type of entity ('parcel', 'property', 'account')
            
        Returns:
            List of validation error dictionaries
        """
        all_errors = []
        
        # Apply all validation types
        all_errors.extend(self.validate_field_existence(data, entity_type))
        all_errors.extend(self.validate_field_patterns(data, entity_type))
        all_errors.extend(self.validate_allowed_values(data, entity_type))
        all_errors.extend(self.validate_value_ranges(data, entity_type))
        all_errors.extend(self.apply_custom_validators(data, entity_type))
        all_errors.extend(self.check_consistency(data, entity_type))
        
        return all_errors


class WashingtonStateStandards(PropertyRules):
    """
    Washington State Department of Revenue property assessment standards.
    
    These standards are based on the Washington Administrative Code (WAC)
    and Department of Revenue guidelines for property assessment.
    """
    
    def __init__(self):
        """Initialize with Washington State standards."""
        super().__init__()
        
        # Configure required fields for each entity type
        self.required_fields = {
            'parcel': {
                'parcel_id': True,
                'address': True,
                'city': True,
                'state': True,
                'zip_code': True,
                'land_value': True,
                'total_value': True,
                'assessment_year': True
            },
            'property': {
                'property_type': True,
                'square_footage': False,
                'lot_size': False
            },
            'account': {
                'account_id': True,
                'owner_name': True,
                'mailing_address': True,
                'assessed_value': True,
                'tax_amount': False
            }
        }
        
        # Configure field patterns
        self.field_patterns = {
            'parcel': {
                'parcel_id': {
                    'pattern': re.compile(r'^\d{8}-\d{4}$'),
                    'message': 'Parcel ID must follow the format ########-####'
                },
                'zip_code': {
                    'pattern': re.compile(r'^\d{5}(-\d{4})?$'),
                    'message': 'ZIP code must be in the format 99999 or 99999-9999'
                }
            },
            'account': {
                'email': {
                    'pattern': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
                    'message': 'Email must be in a valid format'
                }
            }
        }
        
        # Configure allowed values
        self.allowed_values = {
            'parcel': {
                'state': {
                    'values': ['WA'],
                    'message': 'State must be WA for Washington State'
                }
            },
            'property': {
                'property_type': {
                    'values': [
                        'Residential', 'Commercial', 'Industrial', 'Agricultural',
                        'Multifamily', 'Vacant Land', 'Mixed Use', 'Public'
                    ],
                    'message': 'Property type must be a valid category per WA State standards'
                },
                'quality': {
                    'values': ['Low', 'Fair', 'Average', 'Good', 'Very Good', 'Excellent'],
                    'message': 'Quality must be a standard classification'
                },
                'condition': {
                    'values': ['Poor', 'Fair', 'Average', 'Good', 'Very Good', 'Excellent'],
                    'message': 'Condition must be a standard classification'
                }
            }
        }
        
        # Configure value ranges
        current_year = datetime.now().year
        self.value_ranges = {
            'parcel': {
                'land_value': {
                    'min': 0,
                    'message': 'Land value must be non-negative'
                },
                'improvement_value': {
                    'min': 0,
                    'message': 'Improvement value must be non-negative'
                },
                'total_value': {
                    'min': 0,
                    'message': 'Total value must be non-negative'
                },
                'assessment_year': {
                    'min': 1980,
                    'max': current_year + 1,  # Allow for next year's assessments
                    'message': f'Assessment year must be between 1980 and {current_year + 1}'
                },
                'latitude': {
                    'min': 45.0,
                    'max': 49.0,
                    'message': 'Latitude must be within Washington State bounds'
                },
                'longitude': {
                    'min': -124.8,
                    'max': -116.9,
                    'message': 'Longitude must be within Washington State bounds'
                }
            },
            'property': {
                'year_built': {
                    'min': 1800,
                    'max': current_year,
                    'message': f'Year built must be between 1800 and {current_year}'
                },
                'square_footage': {
                    'min': 0,
                    'message': 'Square footage must be non-negative'
                },
                'bedrooms': {
                    'min': 0,
                    'message': 'Bedrooms must be non-negative'
                },
                'bathrooms': {
                    'min': 0,
                    'message': 'Bathrooms must be non-negative'
                }
            },
            'account': {
                'assessed_value': {
                    'min': 0,
                    'message': 'Assessed value must be non-negative'
                },
                'tax_amount': {
                    'min': 0,
                    'message': 'Tax amount must be non-negative'
                }
            }
        }
        
        # Configure custom validators
        def validate_total_value(value, data):
            """Validate that total value equals land value plus improvement value."""
            if 'land_value' in data and 'improvement_value' in data:
                land = float(data['land_value']) if data['land_value'] is not None else 0
                improvement = float(data['improvement_value']) if data['improvement_value'] is not None else 0
                total = float(value) if value is not None else 0
                
                # Allow for small rounding differences
                return abs(land + improvement - total) < 1.0
            return True
        
        self.custom_validators = {
            'parcel': {
                'total_value': {
                    'validator': validate_total_value,
                    'message': 'Total value must equal land value plus improvement value'
                }
            }
        }
        
        # Configure consistency checks
        def check_value_consistency(data):
            """Check that assessed_value matches total_value when both exist."""
            if 'total_value' in data and 'assessed_value' in data:
                if data['total_value'] is not None and data['assessed_value'] is not None:
                    total = float(data['total_value'])
                    assessed = float(data['assessed_value'])
                    
                    # Allow for small rounding differences
                    return abs(total - assessed) < 1.0
            return True
        
        self.consistency_checks = {
            'parcel': [
                {
                    'validator': check_value_consistency,
                    'message': 'Assessed value must match total value',
                    'fields': ['total_value', 'assessed_value']
                }
            ]
        }


class BentonCountyRules(WashingtonStateStandards):
    """
    Benton County specific property assessment rules.
    
    Extends Washington State standards with additional Benton County
    specific requirements and validation rules.
    """
    
    def __init__(self):
        """Initialize with Benton County specific rules."""
        super().__init__()
        
        # Add Benton County specific requirements
        
        # Benton County cities
        benton_cities = [
            'Kennewick', 'Richland', 'Pasco', 'West Richland', 
            'Prosser', 'Benton City', 'Plymouth', 'Paterson'
        ]
        
        self.allowed_values['parcel']['city'] = {
            'values': benton_cities,
            'message': 'City must be a valid Benton County municipality'
        }
        
        # Benton County has specific parcel ID format requirements
        self.field_patterns['parcel']['parcel_id'] = {
            'pattern': re.compile(r'^1-\d{7}-\d{3}-\d{4}-\d{2}$'),
            'message': 'Benton County parcel ID must follow the format 1-#######-###-####-##'
        }
        
        # Configure Benton County specific value ranges
        # Benton County latitude/longitude bounds
        self.value_ranges['parcel']['latitude'] = {
            'min': 45.7,
            'max': 46.5,
            'message': 'Latitude must be within Benton County bounds'
        }
        self.value_ranges['parcel']['longitude'] = {
            'min': -120.0,
            'max': -118.8,
            'message': 'Longitude must be within Benton County bounds'
        }
        
        # Add Benton County specific custom validators
        def validate_benton_tax_calculation(value, data):
            """
            Validate tax calculation based on Benton County mill rates.
            
            The default mill rate for Benton County is approximately 10.5 per $1000
            of assessed value, though this varies by location and exemptions.
            """
            if 'assessed_value' in data and data['assessed_value'] is not None:
                assessed_value = float(data['assessed_value'])
                tax_amount = float(value) if value is not None else 0
                
                # Estimated mill rate range (9.5 to 12.5 per $1000)
                min_tax = assessed_value * 0.0095  # 9.5 mills
                max_tax = assessed_value * 0.0125  # 12.5 mills
                
                # Tax should fall within this range unless there are exemptions
                return min_tax <= tax_amount <= max_tax or tax_amount == 0
            return True
        
        # Initialize the account custom validators if not present
        if 'account' not in self.custom_validators:
            self.custom_validators['account'] = {}
        
        self.custom_validators['account']['tax_amount'] = {
            'validator': validate_benton_tax_calculation,
            'message': 'Tax amount does not align with Benton County mill rates'
        }
        
        # Add specific exemption validation (simplified version)
        def validate_exemptions(data):
            """Validate that exemptions are properly applied."""
            # This is a placeholder for a more complex exemption validation
            # In a real implementation, this would check specific exemption types
            # such as senior/disabled, non-profit, government, etc.
            
            if 'exemption_code' in data and data['exemption_code']:
                if 'tax_amount' in data and 'assessed_value' in data:
                    # Different exemption codes would have different validation logic
                    pass
            
            return True
        
        self.consistency_checks['account'] = [
            {
                'validator': validate_exemptions,
                'message': 'Exemption validation failed',
                'fields': ['exemption_code', 'tax_amount', 'assessed_value']
            }
        ]