"""
Data Quality Agent for Benton County Assessor's Office MCP

This module implements the Data Quality Agent, which is responsible for
validating property data against Washington State Department of Revenue
standards and Benton County regulations.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from data_quality.validator import DataValidator
from data_quality.rules import WashingtonStateStandards, BentonCountyRules

from ..agent import Agent, AgentType, AgentStatus, AgentCapability
from ..message import Message, MessageType, MessagePriority
from ..task import Task, TaskStatus, TaskPriority

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataQualityAgent(Agent):
    """
    Data Quality Agent for the MCP system.
    
    This agent is responsible for validating property assessment data against
    Washington State Department of Revenue standards and Benton County regulations.
    It detects data anomalies, validates field formats, and ensures data consistency
    across records.
    """
    
    def __init__(self, agent_id: Optional[str] = None,
                name: str = "Data Quality Agent",
                description: str = "Validates property assessment data against Washington State standards",
                use_benton_rules: bool = True):
        """
        Initialize the Data Quality Agent.
        
        Args:
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Human-readable name for the agent
            description: Detailed description of the agent's purpose
            use_benton_rules: Whether to use Benton County specific rules
        """
        # Initialize base agent
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.DATA_QUALITY,
            name=name,
            description=description,
            capabilities=[
                AgentCapability.DATA_VALIDATION,
                AgentCapability.ANOMALY_DETECTION,
                AgentCapability.DATA_ENHANCEMENT
            ]
        )
        
        # Initialize data validator
        self.validator = DataValidator(use_benton_rules=use_benton_rules)
        self.use_benton_rules = use_benton_rules
        
        # Statistics for tracking validation activities
        self.validation_stats = {
            "parcel_validations": 0,
            "property_validations": 0,
            "account_validations": 0,
            "complete_record_validations": 0,
            "validation_errors": 0,
            "validation_warnings": 0,
            "anomalies_detected": 0
        }
        
        # Register message handlers
        self.register_message_handler(MessageType.VALIDATION_REQUEST.value, self._handle_validation_request)
        self.register_message_handler(MessageType.DATA_REQUEST.value, self._handle_data_request)
        
        # Register task handlers
        self.register_task_handler("validate_entity", self._handle_validate_entity_task)
        self.register_task_handler("validate_complete_record", self._handle_validate_complete_record_task)
        self.register_task_handler("detect_anomalies", self._handle_detect_anomalies_task)
        self.register_task_handler("enhance_data", self._handle_enhance_data_task)
        
        logger.info(f"Data Quality Agent initialized with {'Benton County' if use_benton_rules else 'Washington State'} rules")
    
    def _handle_validation_request(self, message: Message) -> Dict[str, Any]:
        """
        Handle a validation request message.
        
        Args:
            message: The validation request message
            
        Returns:
            dict: Validation response
        """
        content = message.content
        entity_type = content.get("entity_type")
        data = content.get("data", {})
        
        if not entity_type or not data:
            logger.warning(f"Invalid validation request: missing entity_type or data")
            return {
                "status": "error",
                "error": "Missing entity_type or data"
            }
        
        # Perform validation based on entity type
        try:
            if entity_type == "parcel":
                result = self.validator.validate_parcel(data)
                self.validation_stats["parcel_validations"] += 1
            elif entity_type == "property":
                result = self.validator.validate_property(data)
                self.validation_stats["property_validations"] += 1
            elif entity_type == "account":
                result = self.validator.validate_account(data)
                self.validation_stats["account_validations"] += 1
            elif entity_type == "complete_record":
                overall_valid, results = self.validator.validate_complete_record(data)
                result_dict = {}
                for key, validation_result in results.items():
                    result_dict[key] = validation_result.to_dict()
                self.validation_stats["complete_record_validations"] += 1
                return {
                    "status": "success",
                    "overall_valid": overall_valid,
                    "results": result_dict
                }
            else:
                logger.warning(f"Unknown entity type: {entity_type}")
                return {
                    "status": "error",
                    "error": f"Unknown entity type: {entity_type}"
                }
            
            # Track validation errors
            if not result.valid:
                self.validation_stats["validation_errors"] += len(result.errors)
            
            # Return validation result
            return {
                "status": "success",
                "validation_result": result.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error validating {entity_type}: {str(e)}")
            return {
                "status": "error",
                "error": f"Validation error: {str(e)}"
            }
    
    def _handle_data_request(self, message: Message) -> Dict[str, Any]:
        """
        Handle a data request message.
        
        Args:
            message: The data request message
            
        Returns:
            dict: Data response
        """
        content = message.content
        request_type = content.get("request_type")
        
        if request_type == "validation_rules":
            # Return validation rules information
            rules = self.validator.rules
            
            if self.use_benton_rules:
                rules_type = "Benton County Rules"
            else:
                rules_type = "Washington State Standards"
            
            return {
                "status": "success",
                "data": {
                    "rules_type": rules_type,
                    "required_fields": rules.required_fields,
                    "allowed_values": {
                        entity_type: {
                            field: values["values"] for field, values in entity_rules.items()
                        } for entity_type, entity_rules in rules.allowed_values.items()
                    },
                    "value_ranges": {
                        entity_type: {
                            field: {
                                key: value for key, value in ranges.items() if key != "message"
                            } for field, ranges in entity_rules.items()
                        } for entity_type, entity_rules in rules.value_ranges.items()
                    }
                }
            }
        elif request_type == "validation_stats":
            # Return validation statistics
            return {
                "status": "success",
                "data": self.validation_stats
            }
        else:
            logger.warning(f"Unknown data request type: {request_type}")
            return {
                "status": "error",
                "error": f"Unknown data request type: {request_type}"
            }
    
    def _handle_validate_entity_task(self, task: Task) -> Dict[str, Any]:
        """
        Handle a validate entity task.
        
        Args:
            task: The validate entity task
            
        Returns:
            dict: Task result
        """
        parameters = task.parameters
        entity_type = parameters.get("entity_type")
        data = parameters.get("data", {})
        
        if not entity_type or not data:
            logger.warning(f"Invalid validate entity task: missing entity_type or data")
            return {
                "status": "error",
                "error": "Missing entity_type or data"
            }
        
        # Perform validation based on entity type
        try:
            if entity_type == "parcel":
                result = self.validator.validate_parcel(data)
                self.validation_stats["parcel_validations"] += 1
            elif entity_type == "property":
                result = self.validator.validate_property(data)
                self.validation_stats["property_validations"] += 1
            elif entity_type == "account":
                result = self.validator.validate_account(data)
                self.validation_stats["account_validations"] += 1
            else:
                logger.warning(f"Unknown entity type: {entity_type}")
                return {
                    "status": "error",
                    "error": f"Unknown entity type: {entity_type}"
                }
            
            # Track validation errors
            if not result.valid:
                self.validation_stats["validation_errors"] += len(result.errors)
            
            # Return validation result
            return {
                "status": "success",
                "entity_type": entity_type,
                "validation_result": result.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error validating {entity_type}: {str(e)}")
            return {
                "status": "error",
                "error": f"Validation error: {str(e)}"
            }
    
    def _handle_validate_complete_record_task(self, task: Task) -> Dict[str, Any]:
        """
        Handle a validate complete record task.
        
        Args:
            task: The validate complete record task
            
        Returns:
            dict: Task result
        """
        parameters = task.parameters
        record = parameters.get("record", {})
        
        if not record:
            logger.warning(f"Invalid validate complete record task: missing record")
            return {
                "status": "error",
                "error": "Missing record data"
            }
        
        # Validate complete record
        try:
            overall_valid, results = self.validator.validate_complete_record(record)
            self.validation_stats["complete_record_validations"] += 1
            
            # Track validation errors
            for entity_type, result in results.items():
                if not result.valid:
                    self.validation_stats["validation_errors"] += len(result.errors)
            
            # Convert validation results to dictionaries
            result_dict = {}
            for entity_type, result in results.items():
                result_dict[entity_type] = result.to_dict()
            
            # Return validation result
            return {
                "status": "success",
                "overall_valid": overall_valid,
                "validation_results": result_dict
            }
            
        except Exception as e:
            logger.error(f"Error validating complete record: {str(e)}")
            return {
                "status": "error",
                "error": f"Validation error: {str(e)}"
            }
    
    def _handle_detect_anomalies_task(self, task: Task) -> Dict[str, Any]:
        """
        Handle a detect anomalies task.
        
        Args:
            task: The detect anomalies task
            
        Returns:
            dict: Task result with detected anomalies
        """
        parameters = task.parameters
        data = parameters.get("data", {})
        entity_type = parameters.get("entity_type")
        
        if not data or not entity_type:
            logger.warning(f"Invalid detect anomalies task: missing data or entity_type")
            return {
                "status": "error",
                "error": "Missing data or entity_type"
            }
        
        # Detect anomalies based on entity type
        try:
            anomalies = []
            
            # Basic anomaly detection for parcels
            if entity_type == "parcel":
                # Detect unusually high or low land values
                if "land_value" in data and data["land_value"] is not None:
                    land_value = float(data["land_value"])
                    if land_value > 1000000:  # Land value > $1M
                        anomalies.append({
                            "field": "land_value",
                            "value": land_value,
                            "anomaly_type": "high_value",
                            "description": f"Unusually high land value: ${land_value:,.2f}"
                        })
                    elif land_value < 1000:  # Land value < $1K
                        anomalies.append({
                            "field": "land_value",
                            "value": land_value,
                            "anomaly_type": "low_value",
                            "description": f"Unusually low land value: ${land_value:,.2f}"
                        })
                
                # Detect unusually high improvement to land value ratio
                if ("land_value" in data and data["land_value"] is not None and
                    "improvement_value" in data and data["improvement_value"] is not None):
                    land_value = float(data["land_value"])
                    improvement_value = float(data["improvement_value"])
                    
                    if land_value > 0:
                        ratio = improvement_value / land_value
                        if ratio > 10:  # Improvement value > 10x land value
                            anomalies.append({
                                "field": "improvement_value",
                                "value": improvement_value,
                                "anomaly_type": "high_improvement_ratio",
                                "description": f"Unusually high improvement to land value ratio: {ratio:.2f}"
                            })
            
            # Basic anomaly detection for properties
            elif entity_type == "property":
                # Detect unusually large or small square footage
                if "square_footage" in data and data["square_footage"] is not None:
                    sqft = float(data["square_footage"])
                    if sqft > 10000:  # Square footage > 10,000 sq ft
                        anomalies.append({
                            "field": "square_footage",
                            "value": sqft,
                            "anomaly_type": "large_size",
                            "description": f"Unusually large property: {sqft:,.2f} sq ft"
                        })
                    elif sqft < 500:  # Square footage < 500 sq ft
                        anomalies.append({
                            "field": "square_footage",
                            "value": sqft,
                            "anomaly_type": "small_size",
                            "description": f"Unusually small property: {sqft:,.2f} sq ft"
                        })
                
                # Detect unusually old properties
                if "year_built" in data and data["year_built"] is not None:
                    year_built = int(data["year_built"])
                    current_year = datetime.now().year
                    age = current_year - year_built
                    
                    if age > 100:  # Property older than 100 years
                        anomalies.append({
                            "field": "year_built",
                            "value": year_built,
                            "anomaly_type": "very_old",
                            "description": f"Very old property: built in {year_built} ({age} years old)"
                        })
                    elif year_built > current_year:  # Future year
                        anomalies.append({
                            "field": "year_built",
                            "value": year_built,
                            "anomaly_type": "future_date",
                            "description": f"Invalid future build year: {year_built}"
                        })
            
            # Basic anomaly detection for accounts
            elif entity_type == "account":
                # Detect unusually high or low assessed values
                if "assessed_value" in data and data["assessed_value"] is not None:
                    assessed_value = float(data["assessed_value"])
                    if assessed_value > 2000000:  # Assessed value > $2M
                        anomalies.append({
                            "field": "assessed_value",
                            "value": assessed_value,
                            "anomaly_type": "high_value",
                            "description": f"Unusually high assessed value: ${assessed_value:,.2f}"
                        })
                    elif assessed_value < 10000:  # Assessed value < $10K
                        anomalies.append({
                            "field": "assessed_value",
                            "value": assessed_value,
                            "anomaly_type": "low_value",
                            "description": f"Unusually low assessed value: ${assessed_value:,.2f}"
                        })
                
                # Detect unusually low tax rate
                if ("assessed_value" in data and data["assessed_value"] is not None and
                    "tax_amount" in data and data["tax_amount"] is not None):
                    assessed_value = float(data["assessed_value"])
                    tax_amount = float(data["tax_amount"])
                    
                    if assessed_value > 0:
                        tax_rate = (tax_amount / assessed_value) * 1000  # Mill rate
                        if tax_rate < 5:  # Mill rate < 5 (unusually low)
                            anomalies.append({
                                "field": "tax_amount",
                                "value": tax_amount,
                                "anomaly_type": "low_tax_rate",
                                "description": f"Unusually low tax rate: {tax_rate:.2f} mills"
                            })
            else:
                logger.warning(f"Unknown entity type for anomaly detection: {entity_type}")
                return {
                    "status": "error",
                    "error": f"Unknown entity type: {entity_type}"
                }
            
            # Update anomaly statistics
            self.validation_stats["anomalies_detected"] += len(anomalies)
            
            # Return detected anomalies
            return {
                "status": "success",
                "entity_type": entity_type,
                "anomalies": anomalies,
                "anomaly_count": len(anomalies)
            }
            
        except Exception as e:
            logger.error(f"Error detecting anomalies for {entity_type}: {str(e)}")
            return {
                "status": "error",
                "error": f"Anomaly detection error: {str(e)}"
            }
    
    def _handle_enhance_data_task(self, task: Task) -> Dict[str, Any]:
        """
        Handle an enhance data task.
        
        Args:
            task: The enhance data task
            
        Returns:
            dict: Task result with enhanced data
        """
        parameters = task.parameters
        data = parameters.get("data", {})
        entity_type = parameters.get("entity_type")
        
        if not data or not entity_type:
            logger.warning(f"Invalid enhance data task: missing data or entity_type")
            return {
                "status": "error",
                "error": "Missing data or entity_type"
            }
        
        # Enhance data based on entity type
        try:
            enhanced_data = data.copy()
            enhancements = []
            
            # Basic data enhancement for parcels
            if entity_type == "parcel":
                # Calculate total value if missing
                if ("total_value" not in enhanced_data or enhanced_data["total_value"] is None or enhanced_data["total_value"] == 0) and \
                   "land_value" in enhanced_data and enhanced_data["land_value"] is not None and \
                   "improvement_value" in enhanced_data and enhanced_data["improvement_value"] is not None:
                    land_value = float(enhanced_data["land_value"])
                    improvement_value = float(enhanced_data["improvement_value"])
                    enhanced_data["total_value"] = land_value + improvement_value
                    enhancements.append({
                        "field": "total_value",
                        "original": None,
                        "enhanced": enhanced_data["total_value"],
                        "description": "Calculated total value from land and improvement values"
                    })
                
                # Ensure state is WA for Benton County
                if ("city" in enhanced_data and enhanced_data["city"] in 
                    ["Kennewick", "Richland", "Pasco", "West Richland", "Prosser", "Benton City"]) and \
                   ("state" not in enhanced_data or enhanced_data["state"] is None or enhanced_data["state"] == ""):
                    enhanced_data["state"] = "WA"
                    enhancements.append({
                        "field": "state",
                        "original": None,
                        "enhanced": "WA",
                        "description": "Added WA state for Benton County city"
                    })
            
            # Basic data enhancement for properties
            elif entity_type == "property":
                # Calculate bedrooms/bathrooms ratio
                if "bedrooms" in enhanced_data and enhanced_data["bedrooms"] is not None and \
                   "bathrooms" in enhanced_data and enhanced_data["bathrooms"] is not None and \
                   enhanced_data["bedrooms"] > 0:
                    br_ratio = float(enhanced_data["bathrooms"]) / float(enhanced_data["bedrooms"])
                    enhanced_data["br_ratio"] = round(br_ratio, 2)
                    enhancements.append({
                        "field": "br_ratio",
                        "original": None,
                        "enhanced": enhanced_data["br_ratio"],
                        "description": "Added bathrooms to bedrooms ratio"
                    })
                
                # Calculate age of property
                if "year_built" in enhanced_data and enhanced_data["year_built"] is not None:
                    year_built = int(enhanced_data["year_built"])
                    current_year = datetime.now().year
                    age = max(0, current_year - year_built)  # Ensure non-negative
                    enhanced_data["property_age"] = age
                    enhancements.append({
                        "field": "property_age",
                        "original": None,
                        "enhanced": age,
                        "description": f"Added property age based on year built"
                    })
            
            # Basic data enhancement for accounts
            elif entity_type == "account":
                # Calculate tax rate if missing
                if ("tax_rate" not in enhanced_data or enhanced_data["tax_rate"] is None) and \
                   "assessed_value" in enhanced_data and enhanced_data["assessed_value"] is not None and \
                   "tax_amount" in enhanced_data and enhanced_data["tax_amount"] is not None and \
                   float(enhanced_data["assessed_value"]) > 0:
                    assessed_value = float(enhanced_data["assessed_value"])
                    tax_amount = float(enhanced_data["tax_amount"])
                    tax_rate = (tax_amount / assessed_value) * 1000  # Mill rate
                    enhanced_data["tax_rate"] = round(tax_rate, 2)
                    enhancements.append({
                        "field": "tax_rate",
                        "original": None,
                        "enhanced": enhanced_data["tax_rate"],
                        "description": "Calculated tax rate (mills) from assessed value and tax amount"
                    })
                
                # Ensure property city matches mailing city if property city is missing
                if ("property_city" not in enhanced_data or enhanced_data["property_city"] is None or enhanced_data["property_city"] == "") and \
                   "mailing_city" in enhanced_data and enhanced_data["mailing_city"] is not None and enhanced_data["mailing_city"] != "":
                    enhanced_data["property_city"] = enhanced_data["mailing_city"]
                    enhancements.append({
                        "field": "property_city",
                        "original": None,
                        "enhanced": enhanced_data["property_city"],
                        "description": "Used mailing city as property city"
                    })
            else:
                logger.warning(f"Unknown entity type for data enhancement: {entity_type}")
                return {
                    "status": "error",
                    "error": f"Unknown entity type: {entity_type}"
                }
            
            # Return enhanced data
            return {
                "status": "success",
                "entity_type": entity_type,
                "enhanced_data": enhanced_data,
                "enhancements": enhancements,
                "enhancement_count": len(enhancements)
            }
            
        except Exception as e:
            logger.error(f"Error enhancing data for {entity_type}: {str(e)}")
            return {
                "status": "error",
                "error": f"Data enhancement error: {str(e)}"
            }
    
    def validate_entity(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an entity using the data validator.
        
        Args:
            entity_type: Type of entity ('parcel', 'property', 'account')
            data: Entity data
            
        Returns:
            dict: Validation result
        """
        try:
            if entity_type == "parcel":
                result = self.validator.validate_parcel(data)
                self.validation_stats["parcel_validations"] += 1
            elif entity_type == "property":
                result = self.validator.validate_property(data)
                self.validation_stats["property_validations"] += 1
            elif entity_type == "account":
                result = self.validator.validate_account(data)
                self.validation_stats["account_validations"] += 1
            else:
                logger.warning(f"Unknown entity type: {entity_type}")
                return {
                    "status": "error",
                    "error": f"Unknown entity type: {entity_type}"
                }
            
            # Track validation errors
            if not result.valid:
                self.validation_stats["validation_errors"] += len(result.errors)
            
            # Return validation result
            return {
                "status": "success",
                "validation_result": result.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error validating {entity_type}: {str(e)}")
            return {
                "status": "error",
                "error": f"Validation error: {str(e)}"
            }
    
    def validate_complete_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a complete record consisting of parcel, property, and account data.
        
        Args:
            record: Complete record data
            
        Returns:
            dict: Validation result
        """
        try:
            overall_valid, results = self.validator.validate_complete_record(record)
            self.validation_stats["complete_record_validations"] += 1
            
            # Track validation errors
            for entity_type, result in results.items():
                if not result.valid:
                    self.validation_stats["validation_errors"] += len(result.errors)
            
            # Convert validation results to dictionaries
            result_dict = {}
            for entity_type, result in results.items():
                result_dict[entity_type] = result.to_dict()
            
            # Return validation result
            return {
                "status": "success",
                "overall_valid": overall_valid,
                "validation_results": result_dict
            }
            
        except Exception as e:
            logger.error(f"Error validating complete record: {str(e)}")
            return {
                "status": "error",
                "error": f"Validation error: {str(e)}"
            }
    
    def get_validation_rules(self) -> Dict[str, Any]:
        """
        Get the validation rules being used by the agent.
        
        Returns:
            dict: Validation rules information
        """
        rules = self.validator.rules
        
        if self.use_benton_rules:
            rules_type = "Benton County Rules"
        else:
            rules_type = "Washington State Standards"
        
        return {
            "rules_type": rules_type,
            "required_fields": rules.required_fields,
            "allowed_values": {
                entity_type: {
                    field: values.get("values", []) for field, values in entity_rules.items()
                } for entity_type, entity_rules in rules.allowed_values.items()
            },
            "value_ranges": {
                entity_type: {
                    field: {
                        key: value for key, value in ranges.items() if key != "message"
                    } for field, ranges in entity_rules.items()
                } for entity_type, entity_rules in rules.value_ranges.items()
            }
        }
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics for the agent.
        
        Returns:
            dict: Validation statistics
        """
        return self.validation_stats