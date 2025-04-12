"""
Data Validation Agent for Benton County Assessor's Office AI Platform

This module implements a specialized AI agent that validates property assessment data
against Washington State standards and ensures data quality.
"""

import os
import re
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime

from core.message import Message, CommandMessage, ResponseMessage, ErrorMessage
from mcp.agent import Agent


class DataValidationAgent(Agent):
    """
    AI agent specialized in data validation for property assessments.
    
    This agent validates property data against Washington State standards,
    checks for data consistency and completeness, identifies anomalies
    in assessment data, and generates data quality reports.
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        """
        Initialize the Data Validation Agent.
        
        Args:
            agent_id: Unique identifier for this agent
            config: Agent configuration
        """
        super().__init__(agent_id, config)
        
        self.logger = logging.getLogger(f"data_validation_agent.{agent_id}")
        self.validation_rules = self._load_validation_rules()
        self.data_schema = self._load_data_schema()
        self.validation_stats = {
            "validated_properties": 0,
            "validation_errors": 0,
            "anomalies_detected": 0,
            "reports_generated": 0
        }
        
        # Register message handlers
        self.register_handler("validate_property", self._handle_validate_property)
        self.register_handler("validate_batch", self._handle_validate_batch)
        self.register_handler("generate_report", self._handle_generate_report)
        
        self.logger.info(f"Data Validation Agent {agent_id} initialized with {len(self.validation_rules)} rules")
    
    def _handle_validate_property(self, message: Message) -> None:
        """
        Handle a property validation request.
        
        Args:
            message: Property validation request message
        """
        if not isinstance(message, CommandMessage):
            return
        
        self.logger.info("Received property validation request")
        
        params = message.payload.get("parameters", {})
        property_data = params.get("property_data")
        validation_level = params.get("validation_level", "standard")
        
        if not property_data:
            self._send_error_response(
                message,
                "MISSING_PROPERTY_DATA",
                "Property data is required for validation"
            )
            return
        
        try:
            # Validate property data
            validation_result = self.validate_property(property_data, validation_level)
            
            # Update statistics
            self.validation_stats["validated_properties"] += 1
            if not validation_result["valid"]:
                self.validation_stats["validation_errors"] += 1
            if validation_result.get("anomalies", []):
                self.validation_stats["anomalies_detected"] += len(validation_result.get("anomalies", []))
            
            # Send response
            response = ResponseMessage(
                source_agent_id=self.agent_id,
                target_agent_id=message.source_agent_id,
                status="success",
                result=validation_result,
                original_message_id=message.message_id,
                correlation_id=message.correlation_id
            )
            self.send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error validating property: {str(e)}")
            self._send_error_response(
                message,
                "VALIDATION_ERROR",
                f"Error validating property: {str(e)}"
            )
    
    def _handle_validate_batch(self, message: Message) -> None:
        """
        Handle a batch validation request.
        
        Args:
            message: Batch validation request message
        """
        if not isinstance(message, CommandMessage):
            return
        
        self.logger.info("Received batch validation request")
        
        params = message.payload.get("parameters", {})
        properties = params.get("properties", [])
        validation_level = params.get("validation_level", "standard")
        
        if not properties:
            self._send_error_response(
                message,
                "MISSING_PROPERTIES",
                "Properties list is required for batch validation"
            )
            return
        
        try:
            # Validate properties in batch
            results = []
            valid_count = 0
            error_count = 0
            anomaly_count = 0
            
            for property_data in properties:
                result = self.validate_property(property_data, validation_level)
                results.append(result)
                
                if result["valid"]:
                    valid_count += 1
                else:
                    error_count += 1
                    
                anomaly_count += len(result.get("anomalies", []))
            
            # Update statistics
            self.validation_stats["validated_properties"] += len(properties)
            self.validation_stats["validation_errors"] += error_count
            self.validation_stats["anomalies_detected"] += anomaly_count
            
            # Send response
            response = ResponseMessage(
                source_agent_id=self.agent_id,
                target_agent_id=message.source_agent_id,
                status="success",
                result={
                    "batch_size": len(properties),
                    "valid_count": valid_count,
                    "error_count": error_count,
                    "anomaly_count": anomaly_count,
                    "results": results
                },
                original_message_id=message.message_id,
                correlation_id=message.correlation_id
            )
            self.send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error in batch validation: {str(e)}")
            self._send_error_response(
                message,
                "BATCH_VALIDATION_ERROR",
                f"Error in batch validation: {str(e)}"
            )
    
    def _handle_generate_report(self, message: Message) -> None:
        """
        Handle a report generation request.
        
        Args:
            message: Report generation request message
        """
        if not isinstance(message, CommandMessage):
            return
        
        self.logger.info("Received report generation request")
        
        params = message.payload.get("parameters", {})
        report_type = params.get("report_type", "data_quality")
        data_source = params.get("data_source", "recent")
        filter_criteria = params.get("filter_criteria", {})
        
        try:
            # Generate report
            report = self.generate_report(report_type, data_source, filter_criteria)
            
            # Update statistics
            self.validation_stats["reports_generated"] += 1
            
            # Send response
            response = ResponseMessage(
                source_agent_id=self.agent_id,
                target_agent_id=message.source_agent_id,
                status="success",
                result=report,
                original_message_id=message.message_id,
                correlation_id=message.correlation_id
            )
            self.send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            self._send_error_response(
                message,
                "REPORT_GENERATION_ERROR",
                f"Error generating report: {str(e)}"
            )
    
    def validate_property(self, property_data: Dict[str, Any], validation_level: str = "standard") -> Dict[str, Any]:
        """
        Validate property data against Washington State standards.
        
        Args:
            property_data: Property data to validate
            validation_level: Validation level (basic, standard, strict)
            
        Returns:
            Validation result
        """
        self.logger.info(f"Validating property {property_data.get('property_id', 'unknown')} at {validation_level} level")
        
        # Initialize result
        result = {
            "property_id": property_data.get("property_id", "unknown"),
            "validation_level": validation_level,
            "valid": True,
            "validation_timestamp": datetime.now().isoformat(),
            "errors": [],
            "warnings": [],
            "anomalies": []
        }
        
        # Schema validation
        if not self._validate_schema(property_data, result):
            result["valid"] = False
        
        # Apply validation rules based on level
        rule_sets = self._get_rule_set_for_level(validation_level)
        for rule_set, rules in rule_sets.items():
            for rule in rules:
                if not self._apply_validation_rule(property_data, rule, result):
                    if rule.get("severity") == "error":
                        result["valid"] = False
        
        # Check for anomalies
        self._check_for_anomalies(property_data, result)
        
        # Add validation summary
        result["summary"] = {
            "error_count": len(result["errors"]),
            "warning_count": len(result["warnings"]),
            "anomaly_count": len(result["anomalies"])
        }
        
        return result
    
    def generate_report(
        self, 
        report_type: str = "data_quality", 
        data_source: str = "recent",
        filter_criteria: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate a data quality report.
        
        Args:
            report_type: Report type (data_quality, compliance, anomaly)
            data_source: Data source (recent, all, custom)
            filter_criteria: Filter criteria for data selection
            
        Returns:
            Generated report
        """
        filter_criteria = filter_criteria or {}
        self.logger.info(f"Generating {report_type} report from {data_source} data")
        
        # Initialize report
        report = {
            "report_id": str(uuid.uuid4()),
            "report_type": report_type,
            "data_source": data_source,
            "filter_criteria": filter_criteria,
            "generation_timestamp": datetime.now().isoformat(),
            "summary": {},
            "details": {}
        }
        
        # Generate report based on type
        if report_type == "data_quality":
            self._generate_data_quality_report(report)
        elif report_type == "compliance":
            self._generate_compliance_report(report)
        elif report_type == "anomaly":
            self._generate_anomaly_report(report)
        else:
            self.logger.warning(f"Unknown report type: {report_type}")
            report["error"] = f"Unknown report type: {report_type}"
        
        return report
    
    def _load_validation_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load validation rules from configuration or default rules.
        
        Returns:
            Validation rules by category
        """
        # Check if rules file exists in config
        rules_file = self.config.get("rules_file")
        if rules_file and os.path.exists(rules_file):
            try:
                with open(rules_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading rules from {rules_file}: {str(e)}")
        
        # Default rules
        return {
            "identifiers": [
                {
                    "id": "valid_parcel_number",
                    "description": "Parcel number must be valid",
                    "severity": "error",
                    "check": "parcel_number_format"
                },
                {
                    "id": "valid_property_id",
                    "description": "Property ID must be valid",
                    "severity": "error",
                    "check": "property_id_format"
                }
            ],
            "addresses": [
                {
                    "id": "address_required",
                    "description": "Property must have an address",
                    "severity": "error",
                    "check": "address_presence"
                },
                {
                    "id": "address_format",
                    "description": "Address must be properly formatted",
                    "severity": "warning",
                    "check": "address_format"
                },
                {
                    "id": "valid_zip_code",
                    "description": "ZIP code must be valid for Washington State",
                    "severity": "warning",
                    "check": "zip_code_format"
                }
            ],
            "valuation": [
                {
                    "id": "positive_value",
                    "description": "Assessment value must be positive",
                    "severity": "error",
                    "check": "positive_value"
                },
                {
                    "id": "reasonable_value",
                    "description": "Assessment value must be within reasonable range",
                    "severity": "warning",
                    "check": "value_range"
                },
                {
                    "id": "value_change_limit",
                    "description": "Value change from previous assessment should be within limits",
                    "severity": "warning",
                    "check": "value_change"
                }
            ],
            "classifications": [
                {
                    "id": "valid_property_type",
                    "description": "Property type must be valid",
                    "severity": "error",
                    "check": "property_type_enum"
                },
                {
                    "id": "valid_zoning",
                    "description": "Zoning must be valid for Washington State",
                    "severity": "warning",
                    "check": "zoning_enum"
                }
            ],
            "dates": [
                {
                    "id": "valid_assessment_date",
                    "description": "Assessment date must be valid",
                    "severity": "error",
                    "check": "assessment_date_format"
                },
                {
                    "id": "assessment_date_not_future",
                    "description": "Assessment date must not be in the future",
                    "severity": "error",
                    "check": "assessment_date_range"
                }
            ]
        }
    
    def _load_data_schema(self) -> Dict[str, Any]:
        """
        Load data schema from configuration or default schema.
        
        Returns:
            Data schema
        """
        # Check if schema file exists in config
        schema_file = self.config.get("schema_file")
        if schema_file and os.path.exists(schema_file):
            try:
                with open(schema_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading schema from {schema_file}: {str(e)}")
        
        # Default schema
        return {
            "type": "object",
            "required": [
                "property_id",
                "parcel_number",
                "address",
                "property_type",
                "assessment_value",
                "assessment_date"
            ],
            "properties": {
                "property_id": {
                    "type": "string",
                    "pattern": "^[A-Z]{2}-\\d{6,8}$"
                },
                "parcel_number": {
                    "type": "string",
                    "pattern": "^\\d{2}-\\d{2}-\\d{2}-\\d{4}-\\d{3}$"
                },
                "address": {
                    "type": "object",
                    "required": ["street", "city", "state", "zip"],
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string", "enum": ["WA"]},
                        "zip": {"type": "string", "pattern": "^\\d{5}(-\\d{4})?$"}
                    }
                },
                "property_type": {
                    "type": "string",
                    "enum": ["Residential", "Commercial", "Agricultural", "Industrial", "Public"]
                },
                "assessment_value": {
                    "type": "number",
                    "minimum": 0
                },
                "assessment_date": {
                    "type": "string",
                    "format": "date"
                }
            }
        }
    
    def _validate_schema(self, property_data: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """
        Validate property data against schema.
        
        Args:
            property_data: Property data to validate
            result: Validation result to update
            
        Returns:
            True if valid, False if invalid
        """
        # Check required fields
        for field in self.data_schema.get("required", []):
            if field not in property_data:
                result["errors"].append({
                    "code": "MISSING_REQUIRED_FIELD",
                    "field": field,
                    "message": f"Required field '{field}' is missing"
                })
                return False
        
        # Check field types and formats
        for field, field_schema in self.data_schema.get("properties", {}).items():
            if field in property_data:
                # Type check
                field_type = field_schema.get("type")
                if field_type == "string" and not isinstance(property_data[field], str):
                    result["errors"].append({
                        "code": "INVALID_TYPE",
                        "field": field,
                        "message": f"Field '{field}' must be a string"
                    })
                elif field_type == "number" and not isinstance(property_data[field], (int, float)):
                    result["errors"].append({
                        "code": "INVALID_TYPE",
                        "field": field,
                        "message": f"Field '{field}' must be a number"
                    })
                elif field_type == "object" and not isinstance(property_data[field], dict):
                    result["errors"].append({
                        "code": "INVALID_TYPE",
                        "field": field,
                        "message": f"Field '{field}' must be an object"
                    })
                
                # Pattern check
                if field_type == "string" and "pattern" in field_schema and isinstance(property_data[field], str):
                    pattern = field_schema["pattern"]
                    if not re.match(pattern, property_data[field]):
                        result["errors"].append({
                            "code": "INVALID_FORMAT",
                            "field": field,
                            "message": f"Field '{field}' does not match required format"
                        })
                
                # Enum check
                if field_type == "string" and "enum" in field_schema and isinstance(property_data[field], str):
                    allowed_values = field_schema["enum"]
                    if property_data[field] not in allowed_values:
                        result["errors"].append({
                            "code": "INVALID_ENUM_VALUE",
                            "field": field,
                            "message": f"Field '{field}' must be one of: {', '.join(allowed_values)}"
                        })
                
                # Number constraints
                if field_type == "number" and isinstance(property_data[field], (int, float)):
                    if "minimum" in field_schema and property_data[field] < field_schema["minimum"]:
                        result["errors"].append({
                            "code": "VALUE_TOO_LOW",
                            "field": field,
                            "message": f"Field '{field}' must be at least {field_schema['minimum']}"
                        })
                    if "maximum" in field_schema and property_data[field] > field_schema["maximum"]:
                        result["errors"].append({
                            "code": "VALUE_TOO_HIGH",
                            "field": field,
                            "message": f"Field '{field}' must be at most {field_schema['maximum']}"
                        })
                
                # Nested object validation
                if field_type == "object" and isinstance(property_data[field], dict):
                    for sub_field in field_schema.get("required", []):
                        if sub_field not in property_data[field]:
                            result["errors"].append({
                                "code": "MISSING_REQUIRED_SUBFIELD",
                                "field": f"{field}.{sub_field}",
                                "message": f"Required subfield '{sub_field}' is missing from '{field}'"
                            })
        
        return len(result["errors"]) == 0
    
    def _get_rule_set_for_level(self, validation_level: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get the rule sets to apply for a specific validation level.
        
        Args:
            validation_level: Validation level (basic, standard, strict)
            
        Returns:
            Rule sets to apply
        """
        if validation_level == "basic":
            # Basic validation: only critical rules
            return {
                "identifiers": self.validation_rules.get("identifiers", []),
                "valuation": [r for r in self.validation_rules.get("valuation", []) if r.get("severity") == "error"]
            }
        elif validation_level == "strict":
            # Strict validation: all rules
            return self.validation_rules
        else:
            # Standard validation: all error rules and some warnings
            result = {}
            for category, rules in self.validation_rules.items():
                result[category] = [r for r in rules if r.get("severity") == "error" or category in ["identifiers", "valuation", "classifications"]]
            return result
    
    def _apply_validation_rule(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """
        Apply a validation rule to property data.
        
        Args:
            property_data: Property data to validate
            rule: Validation rule to apply
            result: Validation result to update
            
        Returns:
            True if valid, False if invalid
        """
        rule_id = rule.get("id", "unknown")
        check_type = rule.get("check", "")
        
        # Apply the appropriate check based on check type
        valid = True
        
        if check_type == "parcel_number_format":
            valid = self._check_parcel_number(property_data, rule, result)
        elif check_type == "property_id_format":
            valid = self._check_property_id(property_data, rule, result)
        elif check_type == "address_presence":
            valid = self._check_address_presence(property_data, rule, result)
        elif check_type == "address_format":
            valid = self._check_address_format(property_data, rule, result)
        elif check_type == "zip_code_format":
            valid = self._check_zip_code(property_data, rule, result)
        elif check_type == "positive_value":
            valid = self._check_positive_value(property_data, rule, result)
        elif check_type == "value_range":
            valid = self._check_value_range(property_data, rule, result)
        elif check_type == "value_change":
            valid = self._check_value_change(property_data, rule, result)
        elif check_type == "property_type_enum":
            valid = self._check_property_type(property_data, rule, result)
        elif check_type == "zoning_enum":
            valid = self._check_zoning(property_data, rule, result)
        elif check_type == "assessment_date_format":
            valid = self._check_assessment_date_format(property_data, rule, result)
        elif check_type == "assessment_date_range":
            valid = self._check_assessment_date_range(property_data, rule, result)
        else:
            self.logger.warning(f"Unknown check type: {check_type}")
            # Add warning for unknown check
            result["warnings"].append({
                "code": "UNKNOWN_CHECK_TYPE",
                "rule": rule_id,
                "message": f"Unknown check type: {check_type}"
            })
        
        return valid
    
    def _check_parcel_number(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if parcel number is valid."""
        parcel_number = property_data.get("parcel_number")
        if not parcel_number:
            self._add_validation_issue(result, rule, "parcel_number", "Parcel number is missing")
            return False
        
        # Check format (example: 12-34-56-7890-123)
        if not re.match(r"^\d{2}-\d{2}-\d{2}-\d{4}-\d{3}$", parcel_number):
            self._add_validation_issue(result, rule, "parcel_number", f"Invalid parcel number format: {parcel_number}")
            return False
        
        return True
    
    def _check_property_id(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if property ID is valid."""
        property_id = property_data.get("property_id")
        if not property_id:
            self._add_validation_issue(result, rule, "property_id", "Property ID is missing")
            return False
        
        # Check format (example: WA-123456)
        if not re.match(r"^[A-Z]{2}-\d{6,8}$", property_id):
            self._add_validation_issue(result, rule, "property_id", f"Invalid property ID format: {property_id}")
            return False
        
        return True
    
    def _check_address_presence(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if address is present."""
        address = property_data.get("address")
        if not address:
            self._add_validation_issue(result, rule, "address", "Address is missing")
            return False
        
        return True
    
    def _check_address_format(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if address is properly formatted."""
        address = property_data.get("address")
        if not address:
            return False
        
        if not isinstance(address, dict):
            self._add_validation_issue(result, rule, "address", "Address must be an object")
            return False
        
        # Check required fields
        for field in ["street", "city", "state", "zip"]:
            if field not in address:
                self._add_validation_issue(result, rule, f"address.{field}", f"Address {field} is missing")
                return False
        
        # Check state is WA
        if address.get("state") != "WA":
            self._add_validation_issue(result, rule, "address.state", f"State must be WA, got: {address.get('state')}")
            return False
        
        return True
    
    def _check_zip_code(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if ZIP code is valid."""
        address = property_data.get("address")
        if not address or not isinstance(address, dict):
            return False
        
        zip_code = address.get("zip")
        if not zip_code:
            self._add_validation_issue(result, rule, "address.zip", "ZIP code is missing")
            return False
        
        # Check format
        if not re.match(r"^\d{5}(-\d{4})?$", zip_code):
            self._add_validation_issue(result, rule, "address.zip", f"Invalid ZIP code format: {zip_code}")
            return False
        
        # Check WA ZIP code range (98001-99403)
        zip_prefix = int(zip_code[:5])
        if not (98001 <= zip_prefix <= 99403):
            self._add_validation_issue(result, rule, "address.zip", f"ZIP code {zip_code} is not in Washington State range")
            return False
        
        return True
    
    def _check_positive_value(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if assessment value is positive."""
        value = property_data.get("assessment_value")
        if value is None:
            self._add_validation_issue(result, rule, "assessment_value", "Assessment value is missing")
            return False
        
        if not isinstance(value, (int, float)):
            self._add_validation_issue(result, rule, "assessment_value", f"Assessment value must be a number, got: {type(value).__name__}")
            return False
        
        if value <= 0:
            self._add_validation_issue(result, rule, "assessment_value", f"Assessment value must be positive, got: {value}")
            return False
        
        return True
    
    def _check_value_range(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if assessment value is within reasonable range."""
        value = property_data.get("assessment_value")
        if value is None or not isinstance(value, (int, float)):
            return False
        
        property_type = property_data.get("property_type")
        
        # Define reasonable range based on property type
        min_value = 0
        max_value = float('inf')
        
        if property_type == "Residential":
            min_value = 5000
            max_value = 10000000  # $10M
        elif property_type == "Commercial":
            min_value = 10000
            max_value = 100000000  # $100M
        elif property_type == "Agricultural":
            min_value = 1000
            max_value = 50000000  # $50M
        elif property_type == "Industrial":
            min_value = 20000
            max_value = 200000000  # $200M
        
        if value < min_value:
            self._add_validation_issue(result, rule, "assessment_value", f"Assessment value {value} is below minimum {min_value} for {property_type} property")
            return False
        
        if value > max_value:
            self._add_validation_issue(result, rule, "assessment_value", f"Assessment value {value} is above maximum {max_value} for {property_type} property")
            return False
        
        return True
    
    def _check_value_change(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if value change from previous assessment is reasonable."""
        value = property_data.get("assessment_value")
        previous_value = property_data.get("previous_assessment_value")
        
        if value is None or previous_value is None:
            return True  # Skip if previous value not available
        
        if not isinstance(value, (int, float)) or not isinstance(previous_value, (int, float)):
            return True
        
        # Calculate percentage change
        if previous_value == 0:
            percent_change = float('inf')
        else:
            percent_change = abs((value - previous_value) / previous_value * 100)
        
        # Check if change is within reasonable limits (30% by default)
        max_change = self.config.get("max_value_change_percent", 30)
        
        if percent_change > max_change:
            self._add_validation_issue(
                result, 
                rule, 
                "assessment_value", 
                f"Assessment value changed by {percent_change:.2f}% (from {previous_value} to {value}), which exceeds the maximum allowed change of {max_change}%"
            )
            return False
        
        return True
    
    def _check_property_type(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if property type is valid."""
        property_type = property_data.get("property_type")
        if property_type is None:
            self._add_validation_issue(result, rule, "property_type", "Property type is missing")
            return False
        
        valid_types = ["Residential", "Commercial", "Agricultural", "Industrial", "Public"]
        
        if property_type not in valid_types:
            self._add_validation_issue(
                result, 
                rule, 
                "property_type", 
                f"Property type '{property_type}' is not valid. Must be one of: {', '.join(valid_types)}"
            )
            return False
        
        return True
    
    def _check_zoning(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if zoning is valid."""
        zoning = property_data.get("zoning")
        if zoning is None:
            return True  # Zoning may be optional
        
        valid_zones = [
            "R1", "R2", "R3", "R4",  # Residential
            "C1", "C2", "C3",        # Commercial
            "I1", "I2", "I3",        # Industrial
            "A1", "A2",              # Agricultural
            "PF", "PS"               # Public Facilities, Public Space
        ]
        
        if zoning not in valid_zones:
            self._add_validation_issue(
                result, 
                rule, 
                "zoning", 
                f"Zoning '{zoning}' is not valid. Must be one of: {', '.join(valid_zones)}"
            )
            return False
        
        return True
    
    def _check_assessment_date_format(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if assessment date is properly formatted."""
        date_str = property_data.get("assessment_date")
        if date_str is None:
            self._add_validation_issue(result, rule, "assessment_date", "Assessment date is missing")
            return False
        
        if not isinstance(date_str, str):
            self._add_validation_issue(
                result, 
                rule, 
                "assessment_date", 
                f"Assessment date must be a string, got: {type(date_str).__name__}"
            )
            return False
        
        # Check ISO format (YYYY-MM-DD)
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            self._add_validation_issue(
                result, 
                rule, 
                "assessment_date", 
                f"Assessment date must be in ISO format (YYYY-MM-DD), got: {date_str}"
            )
            return False
        
        # Check if date is valid
        try:
            year, month, day = map(int, date_str.split("-"))
            datetime(year, month, day)
        except ValueError:
            self._add_validation_issue(
                result, 
                rule, 
                "assessment_date", 
                f"Invalid date: {date_str}"
            )
            return False
        
        return True
    
    def _check_assessment_date_range(self, property_data: Dict[str, Any], rule: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Check if assessment date is within valid range."""
        date_str = property_data.get("assessment_date")
        if date_str is None or not isinstance(date_str, str):
            return False
        
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return False
        
        try:
            # Parse date
            assessment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            
            # Check if date is not in the future
            if assessment_date > today:
                self._add_validation_issue(
                    result, 
                    rule, 
                    "assessment_date", 
                    f"Assessment date {date_str} is in the future"
                )
                return False
            
            # Check if date is not too old (more than 10 years ago)
            min_date = datetime(today.year - 10, 1, 1).date()
            if assessment_date < min_date:
                self._add_validation_issue(
                    result, 
                    rule, 
                    "assessment_date", 
                    f"Assessment date {date_str} is more than 10 years old"
                )
                return False
            
        except ValueError:
            return False
        
        return True
    
    def _check_for_anomalies(self, property_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Check for anomalies in property data.
        
        Args:
            property_data: Property data to check
            result: Validation result to update
        """
        # Check for unusually high or low values
        value = property_data.get("assessment_value")
        if value is not None and isinstance(value, (int, float)):
            property_type = property_data.get("property_type")
            
            if property_type == "Residential":
                if value > 5000000:  # $5M
                    result["anomalies"].append({
                        "code": "HIGH_RESIDENTIAL_VALUE",
                        "field": "assessment_value",
                        "message": f"Unusually high value {value} for residential property"
                    })
                elif value < 50000:  # $50K
                    result["anomalies"].append({
                        "code": "LOW_RESIDENTIAL_VALUE",
                        "field": "assessment_value",
                        "message": f"Unusually low value {value} for residential property"
                    })
            elif property_type == "Commercial":
                if value > 50000000:  # $50M
                    result["anomalies"].append({
                        "code": "HIGH_COMMERCIAL_VALUE",
                        "field": "assessment_value",
                        "message": f"Unusually high value {value} for commercial property"
                    })
                elif value < 100000:  # $100K
                    result["anomalies"].append({
                        "code": "LOW_COMMERCIAL_VALUE",
                        "field": "assessment_value",
                        "message": f"Unusually low value {value} for commercial property"
                    })
        
        # Check for large change from previous assessment
        previous_value = property_data.get("previous_assessment_value")
        if value is not None and previous_value is not None:
            if previous_value > 0:
                percent_change = abs((value - previous_value) / previous_value * 100)
                if percent_change > 100:  # 100%
                    result["anomalies"].append({
                        "code": "LARGE_VALUE_CHANGE",
                        "field": "assessment_value",
                        "message": f"Value changed by {percent_change:.2f}% from {previous_value} to {value}"
                    })
        
        # Check for mismatched property type and zoning
        property_type = property_data.get("property_type")
        zoning = property_data.get("zoning")
        if property_type and zoning:
            # Residential property with non-residential zoning
            if property_type == "Residential" and not zoning.startswith("R"):
                result["anomalies"].append({
                    "code": "MISMATCHED_ZONING",
                    "field": "zoning",
                    "message": f"Residential property has non-residential zoning: {zoning}"
                })
            # Commercial property with non-commercial zoning
            elif property_type == "Commercial" and not zoning.startswith("C"):
                result["anomalies"].append({
                    "code": "MISMATCHED_ZONING",
                    "field": "zoning",
                    "message": f"Commercial property has non-commercial zoning: {zoning}"
                })
    
    def _add_validation_issue(self, result: Dict[str, Any], rule: Dict[str, Any], field: str, message: str) -> None:
        """
        Add a validation issue to the result.
        
        Args:
            result: Validation result to update
            rule: Validation rule
            field: Field with issue
            message: Issue message
        """
        severity = rule.get("severity", "warning")
        issue = {
            "code": rule.get("id", "VALIDATION_ERROR"),
            "field": field,
            "message": message
        }
        
        if severity == "error":
            result["errors"].append(issue)
        else:
            result["warnings"].append(issue)
    
    def _generate_data_quality_report(self, report: Dict[str, Any]) -> None:
        """
        Generate a data quality report.
        
        Args:
            report: Report to update
        """
        # Set summary data
        report["summary"] = {
            "validation_stats": self.validation_stats,
            "data_quality": {
                "error_rate": self._calculate_error_rate(),
                "completeness": self._calculate_completeness(),
                "consistency": self._calculate_consistency()
            }
        }
        
        # Set details
        report["details"] = {
            "error_distribution": self._get_error_distribution(),
            "field_quality": self._get_field_quality_metrics(),
            "recommendations": self._generate_data_quality_recommendations()
        }
    
    def _generate_compliance_report(self, report: Dict[str, Any]) -> None:
        """
        Generate a compliance report.
        
        Args:
            report: Report to update
        """
        # Set summary data
        report["summary"] = {
            "compliance_rate": self._calculate_compliance_rate(),
            "critical_issues": self._count_critical_compliance_issues(),
            "compliance_by_category": self._get_compliance_by_category()
        }
        
        # Set details
        report["details"] = {
            "non_compliant_properties": self._get_non_compliant_properties(),
            "compliance_trends": self._get_compliance_trends(),
            "recommendations": self._generate_compliance_recommendations()
        }
    
    def _generate_anomaly_report(self, report: Dict[str, Any]) -> None:
        """
        Generate an anomaly report.
        
        Args:
            report: Report to update
        """
        # Set summary data
        report["summary"] = {
            "total_anomalies": self.validation_stats["anomalies_detected"],
            "anomaly_rate": self._calculate_anomaly_rate(),
            "anomaly_categories": self._get_anomaly_categories()
        }
        
        # Set details
        report["details"] = {
            "anomaly_properties": self._get_anomaly_properties(),
            "anomaly_patterns": self._get_anomaly_patterns(),
            "recommendations": self._generate_anomaly_recommendations()
        }
    
    def _calculate_error_rate(self) -> float:
        """Calculate the error rate."""
        if self.validation_stats["validated_properties"] == 0:
            return 0.0
        
        return self.validation_stats["validation_errors"] / self.validation_stats["validated_properties"]
    
    def _calculate_completeness(self) -> float:
        """Calculate data completeness (placeholder)."""
        return 0.95  # 95% complete
    
    def _calculate_consistency(self) -> float:
        """Calculate data consistency (placeholder)."""
        return 0.92  # 92% consistent
    
    def _calculate_compliance_rate(self) -> float:
        """Calculate compliance rate (placeholder)."""
        if self.validation_stats["validated_properties"] == 0:
            return 1.0
        
        return 1.0 - (self.validation_stats["validation_errors"] / self.validation_stats["validated_properties"])
    
    def _count_critical_compliance_issues(self) -> int:
        """Count critical compliance issues (placeholder)."""
        return int(self.validation_stats["validation_errors"] * 0.3)  # 30% of errors are critical
    
    def _calculate_anomaly_rate(self) -> float:
        """Calculate anomaly rate."""
        if self.validation_stats["validated_properties"] == 0:
            return 0.0
        
        return self.validation_stats["anomalies_detected"] / self.validation_stats["validated_properties"]
    
    def _get_error_distribution(self) -> Dict[str, int]:
        """Get error distribution (placeholder)."""
        return {
            "missing_data": int(self.validation_stats["validation_errors"] * 0.4),
            "invalid_format": int(self.validation_stats["validation_errors"] * 0.3),
            "value_range": int(self.validation_stats["validation_errors"] * 0.2),
            "consistency": int(self.validation_stats["validation_errors"] * 0.1)
        }
    
    def _get_field_quality_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get field quality metrics (placeholder)."""
        return {
            "property_id": {"completeness": 1.0, "validity": 0.98},
            "address": {"completeness": 0.99, "validity": 0.95},
            "assessment_value": {"completeness": 1.0, "validity": 0.97},
            "property_type": {"completeness": 1.0, "validity": 0.99}
        }
    
    def _get_compliance_by_category(self) -> Dict[str, float]:
        """Get compliance by category (placeholder)."""
        return {
            "identifiers": 0.98,
            "addresses": 0.95,
            "valuation": 0.92,
            "classifications": 0.97,
            "dates": 0.99
        }
    
    def _get_non_compliant_properties(self) -> List[str]:
        """Get non-compliant properties (placeholder)."""
        return ["WA-123456", "WA-234567", "WA-345678"]
    
    def _get_compliance_trends(self) -> Dict[str, List[float]]:
        """Get compliance trends (placeholder)."""
        return {
            "months": ["Jan", "Feb", "Mar", "Apr", "May"],
            "compliance_rates": [0.91, 0.92, 0.94, 0.93, 0.95]
        }
    
    def _get_anomaly_categories(self) -> Dict[str, int]:
        """Get anomaly categories (placeholder)."""
        return {
            "value_outliers": int(self.validation_stats["anomalies_detected"] * 0.6),
            "classification_mismatches": int(self.validation_stats["anomalies_detected"] * 0.3),
            "temporal_anomalies": int(self.validation_stats["anomalies_detected"] * 0.1)
        }
    
    def _get_anomaly_properties(self) -> List[str]:
        """Get properties with anomalies (placeholder)."""
        return ["WA-123456", "WA-234567", "WA-345678"]
    
    def _get_anomaly_patterns(self) -> List[Dict[str, Any]]:
        """Get anomaly patterns (placeholder)."""
        return [
            {
                "pattern": "Residential properties with high values",
                "count": int(self.validation_stats["anomalies_detected"] * 0.4),
                "average_deviation": "120%"
            },
            {
                "pattern": "Large value changes in short time",
                "count": int(self.validation_stats["anomalies_detected"] * 0.3),
                "average_deviation": "85%"
            }
        ]
    
    def _generate_data_quality_recommendations(self) -> List[Dict[str, str]]:
        """Generate data quality recommendations (placeholder)."""
        return [
            {
                "priority": "high",
                "recommendation": "Address missing address data which accounts for 40% of errors"
            },
            {
                "priority": "medium",
                "recommendation": "Standardize property type classifications across the database"
            }
        ]
    
    def _generate_compliance_recommendations(self) -> List[Dict[str, str]]:
        """Generate compliance recommendations (placeholder)."""
        return [
            {
                "priority": "high",
                "recommendation": "Rectify valuation documentation for commercial properties"
            },
            {
                "priority": "medium",
                "recommendation": "Update zoning information to match current Washington State codes"
            }
        ]
    
    def _generate_anomaly_recommendations(self) -> List[Dict[str, str]]:
        """Generate anomaly recommendations (placeholder)."""
        return [
            {
                "priority": "high",
                "recommendation": "Review high-value residential properties for potential classification errors"
            },
            {
                "priority": "medium",
                "recommendation": "Investigate properties with large value changes for potential data entry errors"
            }
        ]
    
    def _send_error_response(self, message: Message, error_code: str, error_message: str) -> None:
        """
        Send an error response message.
        
        Args:
            message: Original message
            error_code: Error code
            error_message: Error message
        """
        error = ErrorMessage(
            source_agent_id=self.agent_id,
            target_agent_id=message.source_agent_id,
            error_code=error_code,
            error_message=error_message,
            correlation_id=message.correlation_id
        )
        
        self.send_message(error)
        self.logger.warning(f"Sent error response: {error_code} - {error_message}")


def create_data_validation_agent(agent_id: str, config_path: Optional[str] = None) -> DataValidationAgent:
    """
    Create a Data Validation Agent with the specified configuration.
    
    Args:
        agent_id: Agent ID
        config_path: Path to configuration file
        
    Returns:
        Configured Data Validation Agent
    """
    if config_path and os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        config = {
            "rules_file": None,
            "schema_file": None,
            "max_value_change_percent": 30,
            "log_level": "info"
        }
    
    return DataValidationAgent(agent_id, config)