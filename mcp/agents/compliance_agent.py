"""
Compliance Agent for Benton County Assessor's Office MCP

This module implements the Compliance Agent, which is responsible for
ensuring property assessments comply with Washington State regulations
and Benton County assessment policies.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date

from ..agent import Agent, AgentType, AgentStatus, AgentCapability
from ..message import Message, MessageType, MessagePriority
from ..task import Task, TaskStatus, TaskPriority

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceAgent(Agent):
    """
    Compliance Agent for the MCP system.
    
    This agent is responsible for ensuring property assessments comply with
    Washington State Department of Revenue regulations and Benton County
    assessment policies. It checks for regulatory compliance, maintains audit
    trails, and enforces assessment policies.
    """
    
    def __init__(self, agent_id: Optional[str] = None,
                name: str = "Compliance Agent",
                description: str = "Ensures compliance with Washington State assessment regulations"):
        """
        Initialize the Compliance Agent.
        
        Args:
            agent_id: Unique identifier for the agent (generated if not provided)
            name: Human-readable name for the agent
            description: Detailed description of the agent's purpose
        """
        # Initialize base agent
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.COMPLIANCE,
            name=name,
            description=description,
            capabilities=[
                AgentCapability.REGULATION_CHECK,
                AgentCapability.AUDIT_TRAIL,
                AgentCapability.POLICY_ENFORCEMENT
            ]
        )
        
        # Initialize compliance rules and policies
        self._initialize_compliance_rules()
        
        # Statistics for tracking compliance activities
        self.compliance_stats = {
            "compliance_checks": 0,
            "regulation_violations": 0,
            "policy_violations": 0,
            "exemption_checks": 0,
            "audit_trail_entries": 0
        }
        
        # Register message handlers
        self.register_message_handler(MessageType.COMPLIANCE_CHECK.value, self._handle_compliance_check)
        self.register_message_handler(MessageType.DATA_REQUEST.value, self._handle_data_request)
        
        # Register task handlers
        self.register_task_handler("check_compliance", self._handle_check_compliance_task)
        self.register_task_handler("verify_exemption", self._handle_verify_exemption_task)
        self.register_task_handler("create_audit_record", self._handle_create_audit_record_task)
        self.register_task_handler("enforce_policy", self._handle_enforce_policy_task)
        
        logger.info("Compliance Agent initialized with Washington State regulations")
    
    def _initialize_compliance_rules(self):
        """Initialize compliance rules and regulations."""
        # Washington State assessment cycle rules
        self.assessment_cycle_rules = {
            "revaluation_cycle": 4,  # Years between full revaluations (up to 4 years in WA)
            "physical_inspection_cycle": 6,  # Years between physical inspections (up to 6 years in WA)
            "assessment_ratio": 100.0,  # Percentage of market value to assess at (100% in WA)
            "assessment_date": "1/1",  # Assessment date (January 1 in WA)
            "tax_status_date": "1/1"   # Tax status date (January 1 in WA)
        }
        
        # Property classification rules
        self.property_classifications = {
            "Residential": {
                "code": "R",
                "description": "Land and improvements used for residential purposes",
                "subclasses": ["Single Family", "Multi-Family", "Mobile Home", "Condominium"]
            },
            "Commercial": {
                "code": "C",
                "description": "Land and improvements used for commercial purposes",
                "subclasses": ["Retail", "Office", "Restaurant", "Hotel/Motel", "Mixed Use"]
            },
            "Industrial": {
                "code": "I",
                "description": "Land and improvements used for industrial purposes",
                "subclasses": ["Manufacturing", "Warehouse", "Food Processing"]
            },
            "Agricultural": {
                "code": "A",
                "description": "Land used primarily for agricultural purposes",
                "subclasses": ["Irrigated", "Dry Land", "Orchard", "Vineyard", "Rangeland"]
            },
            "Vacant Land": {
                "code": "V",
                "description": "Undeveloped land",
                "subclasses": ["Residential", "Commercial", "Industrial", "Agricultural"]
            },
            "Public": {
                "code": "P",
                "description": "Publicly owned property",
                "subclasses": ["Government", "School", "Park", "Utility"]
            }
        }
        
        # Exemption types and requirements
        self.exemption_types = {
            "Senior/Disabled": {
                "code": "SD",
                "description": "Property tax exemption for senior citizens and disabled persons",
                "requirements": {
                    "age": 61,  # Must be at least 61 years old, OR
                    "disabled": True,  # Must be disabled, AND
                    "income": 40000,  # Combined household income must be below $40,000, AND
                    "primary_residence": True  # Must be primary residence
                },
                "documents": ["Income Verification", "Disability Documentation", "Age Verification", "Residence Affidavit"]
            },
            "Nonprofit": {
                "code": "NP",
                "description": "Property tax exemption for qualifying nonprofit organizations",
                "requirements": {
                    "nonprofit_status": True,  # Must be a recognized nonprofit, AND
                    "qualifying_use": True  # Must be used for exempt purposes
                },
                "documents": ["501(c)(3) Documentation", "Use Verification", "Annual Report"]
            },
            "Agricultural": {
                "code": "AG",
                "description": "Current use valuation for agricultural land",
                "requirements": {
                    "min_size": 5,  # Minimum acreage, AND
                    "commercial_ag_use": True,  # Must be used for commercial agricultural production, AND
                    "income_requirement": True  # Must meet income requirements
                },
                "documents": ["Farm Income Records", "Land Use Verification", "Application Form"]
            },
            "Government": {
                "code": "GOV",
                "description": "Exemption for government-owned property",
                "requirements": {
                    "government_owned": True,  # Must be owned by a government entity, AND
                    "public_purpose": True  # Must be used for public purposes
                },
                "documents": ["Ownership Documentation", "Use Verification"]
            }
        }
        
        # Current mill rates for Benton County tax districts
        self.tax_districts = {
            "Kennewick": {
                "mill_rate": 11.23,
                "year": 2024,
                "components": {
                    "state": 2.65,
                    "county": 1.48,
                    "city": 2.10,
                    "school": 4.35,
                    "other": 0.65
                }
            },
            "Richland": {
                "mill_rate": 10.87,
                "year": 2024,
                "components": {
                    "state": 2.65,
                    "county": 1.48,
                    "city": 1.95,
                    "school": 4.12,
                    "other": 0.67
                }
            },
            "Pasco": {
                "mill_rate": 11.56,
                "year": 2024,
                "components": {
                    "state": 2.65,
                    "county": 1.48,
                    "city": 2.25,
                    "school": 4.45,
                    "other": 0.73
                }
            },
            "West Richland": {
                "mill_rate": 10.94,
                "year": 2024,
                "components": {
                    "state": 2.65,
                    "county": 1.48,
                    "city": 2.05,
                    "school": 4.12,
                    "other": 0.64
                }
            },
            "Prosser": {
                "mill_rate": 11.12,
                "year": 2024,
                "components": {
                    "state": 2.65,
                    "county": 1.48,
                    "city": 2.15,
                    "school": 4.22,
                    "other": 0.62
                }
            },
            "Benton City": {
                "mill_rate": 11.08,
                "year": 2024,
                "components": {
                    "state": 2.65,
                    "county": 1.48,
                    "city": 2.12,
                    "school": 4.20,
                    "other": 0.63
                }
            },
            "Unincorporated": {
                "mill_rate": 9.05,
                "year": 2024,
                "components": {
                    "state": 2.65,
                    "county": 1.48,
                    "city": 0.00,
                    "school": 4.22,
                    "other": 0.70
                }
            }
        }
        
        # Common compliance policies
        self.compliance_policies = {
            "valuation_uniformity": {
                "code": "VAL-UNI",
                "description": "Ensure uniform valuation across similar properties",
                "requirements": {
                    "coefficient_of_dispersion": 15.0,  # Max. allowed COD
                    "price_related_differential": [0.98, 1.03]  # Acceptable PRD range
                }
            },
            "new_construction": {
                "code": "NEW-CON",
                "description": "Capture new construction for assessment",
                "requirements": {
                    "deadline": "7/31",  # Deadline to assess new construction
                    "building_permit_tracking": True,  # Must track building permits
                    "physical_inspection": True  # Must physically inspect
                }
            },
            "appeals_process": {
                "code": "APP-PROC",
                "description": "Property tax appeals process",
                "requirements": {
                    "filing_deadline": "30 days",  # Days after value notice
                    "hearing_timeline": "90 days",  # Days to hold hearing
                    "evidence_deadline": "14 days"  # Days before hearing
                }
            },
            "data_quality": {
                "code": "DATA-QUAL",
                "description": "Maintain high quality assessment data",
                "requirements": {
                    "sales_validation": True,  # Must validate sales
                    "data_accuracy": 95.0,  # Minimum data accuracy percentage
                    "missing_data": 5.0  # Maximum percentage of missing data
                }
            }
        }
        
        # Audit trail requirements
        self.audit_requirements = {
            "value_changes": {
                "fields": ["assessed_value", "land_value", "improvement_value", "total_value"],
                "required_metadata": ["timestamp", "user_id", "reason_code", "previous_value"]
            },
            "classification_changes": {
                "fields": ["property_type", "property_class", "property_subclass"],
                "required_metadata": ["timestamp", "user_id", "reason_code", "previous_value"]
            },
            "exemption_changes": {
                "fields": ["exemption_type", "exemption_amount", "exemption_status"],
                "required_metadata": ["timestamp", "user_id", "reason_code", "previous_value", "documentation"]
            }
        }
        
        logger.info("Compliance rules and regulations initialized")
    
    def _handle_compliance_check(self, message: Message) -> Dict[str, Any]:
        """
        Handle a compliance check message.
        
        Args:
            message: The compliance check message
            
        Returns:
            dict: Compliance check response
        """
        content = message.content
        check_type = content.get("check_type")
        data = content.get("data", {})
        
        if not check_type or not data:
            logger.warning(f"Invalid compliance check: missing check_type or data")
            return {
                "status": "error",
                "error": "Missing check_type or data"
            }
        
        # Perform compliance check based on check type
        try:
            if check_type == "property_classification":
                result = self._check_property_classification(data)
            elif check_type == "exemption_eligibility":
                result = self._check_exemption_eligibility(data)
            elif check_type == "tax_calculation":
                result = self._check_tax_calculation(data)
            elif check_type == "assessment_cycle":
                result = self._check_assessment_cycle(data)
            else:
                logger.warning(f"Unknown compliance check type: {check_type}")
                return {
                    "status": "error",
                    "error": f"Unknown compliance check type: {check_type}"
                }
            
            # Update compliance statistics
            self.compliance_stats["compliance_checks"] += 1
            if not result["compliant"]:
                self.compliance_stats["regulation_violations"] += len(result["violations"])
            
            # Return compliance check result
            return {
                "status": "success",
                "check_type": check_type,
                "compliance_result": result
            }
            
        except Exception as e:
            logger.error(f"Error performing compliance check {check_type}: {str(e)}")
            return {
                "status": "error",
                "error": f"Compliance check error: {str(e)}"
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
        
        if request_type == "compliance_rules":
            # Return specific compliance rules based on sub-type
            sub_type = content.get("sub_type")
            
            if sub_type == "assessment_cycle":
                return {
                    "status": "success",
                    "data": self.assessment_cycle_rules
                }
            elif sub_type == "property_classifications":
                return {
                    "status": "success",
                    "data": self.property_classifications
                }
            elif sub_type == "exemption_types":
                return {
                    "status": "success",
                    "data": self.exemption_types
                }
            elif sub_type == "tax_districts":
                return {
                    "status": "success",
                    "data": self.tax_districts
                }
            elif sub_type == "compliance_policies":
                return {
                    "status": "success",
                    "data": self.compliance_policies
                }
            else:
                # Return all rules
                return {
                    "status": "success",
                    "data": {
                        "assessment_cycle_rules": self.assessment_cycle_rules,
                        "property_classifications": self.property_classifications,
                        "exemption_types": self.exemption_types,
                        "tax_districts": self.tax_districts,
                        "compliance_policies": self.compliance_policies,
                        "audit_requirements": self.audit_requirements
                    }
                }
        elif request_type == "compliance_stats":
            # Return compliance statistics
            return {
                "status": "success",
                "data": self.compliance_stats
            }
        else:
            logger.warning(f"Unknown data request type: {request_type}")
            return {
                "status": "error",
                "error": f"Unknown data request type: {request_type}"
            }
    
    def _handle_check_compliance_task(self, task: Task) -> Dict[str, Any]:
        """
        Handle a check compliance task.
        
        Args:
            task: The check compliance task
            
        Returns:
            dict: Task result
        """
        parameters = task.parameters
        check_type = parameters.get("check_type")
        data = parameters.get("data", {})
        
        if not check_type or not data:
            logger.warning(f"Invalid check compliance task: missing check_type or data")
            return {
                "status": "error",
                "error": "Missing check_type or data"
            }
        
        # Perform compliance check based on check type
        try:
            if check_type == "property_classification":
                result = self._check_property_classification(data)
            elif check_type == "exemption_eligibility":
                result = self._check_exemption_eligibility(data)
            elif check_type == "tax_calculation":
                result = self._check_tax_calculation(data)
            elif check_type == "assessment_cycle":
                result = self._check_assessment_cycle(data)
            else:
                logger.warning(f"Unknown compliance check type: {check_type}")
                return {
                    "status": "error",
                    "error": f"Unknown compliance check type: {check_type}"
                }
            
            # Update compliance statistics
            self.compliance_stats["compliance_checks"] += 1
            if not result["compliant"]:
                self.compliance_stats["regulation_violations"] += len(result["violations"])
            
            # Return compliance check result
            return {
                "status": "success",
                "check_type": check_type,
                "compliance_result": result
            }
            
        except Exception as e:
            logger.error(f"Error performing compliance check {check_type}: {str(e)}")
            return {
                "status": "error",
                "error": f"Compliance check error: {str(e)}"
            }
    
    def _handle_verify_exemption_task(self, task: Task) -> Dict[str, Any]:
        """
        Handle a verify exemption task.
        
        Args:
            task: The verify exemption task
            
        Returns:
            dict: Task result
        """
        parameters = task.parameters
        exemption_type = parameters.get("exemption_type")
        applicant_data = parameters.get("applicant_data", {})
        property_data = parameters.get("property_data", {})
        
        if not exemption_type or not applicant_data or not property_data:
            logger.warning(f"Invalid verify exemption task: missing required parameters")
            return {
                "status": "error",
                "error": "Missing exemption_type, applicant_data, or property_data"
            }
        
        # Verify exemption eligibility
        try:
            # Check if exemption type exists
            if exemption_type not in self.exemption_types:
                return {
                    "status": "error",
                    "error": f"Unknown exemption type: {exemption_type}"
                }
            
            # Get exemption requirements
            exemption_info = self.exemption_types[exemption_type]
            requirements = exemption_info["requirements"]
            
            # Check all requirements
            met_requirements = {}
            missing_requirements = {}
            
            for req_name, req_value in requirements.items():
                if req_name in applicant_data:
                    # For boolean requirements
                    if isinstance(req_value, bool):
                        met = applicant_data[req_name] == req_value
                    # For numeric requirements
                    elif isinstance(req_value, (int, float)):
                        # Age requirement (minimum age)
                        if req_name == "age":
                            met = int(applicant_data[req_name]) >= req_value
                        # Income requirement (maximum income)
                        elif req_name == "income":
                            met = float(applicant_data[req_name]) <= req_value
                        # Size requirement (minimum size)
                        elif req_name == "min_size":
                            met = float(applicant_data[req_name]) >= req_value
                        # Default numeric comparison
                        else:
                            met = float(applicant_data[req_name]) == req_value
                    else:
                        met = applicant_data[req_name] == req_value
                    
                    if met:
                        met_requirements[req_name] = applicant_data[req_name]
                    else:
                        missing_requirements[req_name] = {
                            "required": req_value,
                            "provided": applicant_data[req_name]
                        }
                else:
                    missing_requirements[req_name] = {
                        "required": req_value,
                        "provided": None
                    }
            
            # Check if all requirements are met
            eligible = len(missing_requirements) == 0
            
            # Update compliance statistics
            self.compliance_stats["exemption_checks"] += 1
            
            # Return verification result
            return {
                "status": "success",
                "exemption_type": exemption_type,
                "eligible": eligible,
                "met_requirements": met_requirements,
                "missing_requirements": missing_requirements,
                "required_documents": exemption_info["documents"]
            }
            
        except Exception as e:
            logger.error(f"Error verifying exemption {exemption_type}: {str(e)}")
            return {
                "status": "error",
                "error": f"Exemption verification error: {str(e)}"
            }
    
    def _handle_create_audit_record_task(self, task: Task) -> Dict[str, Any]:
        """
        Handle a create audit record task.
        
        Args:
            task: The create audit record task
            
        Returns:
            dict: Task result
        """
        parameters = task.parameters
        entity_type = parameters.get("entity_type")
        entity_id = parameters.get("entity_id")
        action = parameters.get("action")
        changes = parameters.get("changes", {})
        user_id = parameters.get("user_id")
        
        if not entity_type or not entity_id or not action or not user_id:
            logger.warning(f"Invalid create audit record task: missing required parameters")
            return {
                "status": "error",
                "error": "Missing entity_type, entity_id, action, or user_id"
            }
        
        # Create audit record
        try:
            # Generate audit record
            timestamp = datetime.utcnow().isoformat()
            audit_id = f"audit-{timestamp}-{entity_id}"
            
            audit_record = {
                "audit_id": audit_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "changes": changes,
                "user_id": user_id,
                "timestamp": timestamp
            }
            
            # Check for required metadata based on audit requirements
            if entity_type in self.audit_requirements:
                audit_req = self.audit_requirements[entity_type]
                
                # Check if any changed fields require specific metadata
                for field in changes.keys():
                    if field in audit_req["fields"]:
                        # Check for required metadata
                        for req_metadata in audit_req["required_metadata"]:
                            if req_metadata not in parameters:
                                logger.warning(f"Missing required metadata for audit: {req_metadata}")
                                return {
                                    "status": "error",
                                    "error": f"Missing required metadata for {entity_type} audit: {req_metadata}"
                                }
                            
                            # Add metadata to audit record
                            audit_record[req_metadata] = parameters[req_metadata]
            
            # In a real implementation, we would store this record in a database
            # For this prototype, we'll just log it
            logger.info(f"Created audit record: {audit_id}")
            
            # Update compliance statistics
            self.compliance_stats["audit_trail_entries"] += 1
            
            # Return audit record
            return {
                "status": "success",
                "audit_id": audit_id,
                "audit_record": audit_record
            }
            
        except Exception as e:
            logger.error(f"Error creating audit record: {str(e)}")
            return {
                "status": "error",
                "error": f"Audit record creation error: {str(e)}"
            }
    
    def _handle_enforce_policy_task(self, task: Task) -> Dict[str, Any]:
        """
        Handle an enforce policy task.
        
        Args:
            task: The enforce policy task
            
        Returns:
            dict: Task result
        """
        parameters = task.parameters
        policy_code = parameters.get("policy_code")
        entity_data = parameters.get("entity_data", {})
        
        if not policy_code or not entity_data:
            logger.warning(f"Invalid enforce policy task: missing policy_code or entity_data")
            return {
                "status": "error",
                "error": "Missing policy_code or entity_data"
            }
        
        # Find the policy
        policy = None
        for code, policy_info in self.compliance_policies.items():
            if policy_info["code"] == policy_code:
                policy = policy_info
                break
        
        if not policy:
            logger.warning(f"Unknown policy code: {policy_code}")
            return {
                "status": "error",
                "error": f"Unknown policy code: {policy_code}"
            }
        
        # Enforce policy
        try:
            requirements = policy["requirements"]
            violations = []
            
            # Check each requirement
            for req_name, req_value in requirements.items():
                if req_name in entity_data:
                    # For boolean requirements
                    if isinstance(req_value, bool):
                        compliant = entity_data[req_name] == req_value
                    # For numeric requirements
                    elif isinstance(req_value, (int, float)):
                        compliant = float(entity_data[req_name]) == req_value
                    # For range requirements
                    elif isinstance(req_value, list) and len(req_value) == 2:
                        value = float(entity_data[req_name])
                        compliant = req_value[0] <= value <= req_value[1]
                    else:
                        compliant = entity_data[req_name] == req_value
                    
                    if not compliant:
                        violations.append({
                            "requirement": req_name,
                            "expected": req_value,
                            "actual": entity_data[req_name],
                            "description": f"Value for {req_name} does not meet policy requirement"
                        })
                else:
                    violations.append({
                        "requirement": req_name,
                        "expected": req_value,
                        "actual": None,
                        "description": f"Required field {req_name} is missing"
                    })
            
            # Update compliance statistics
            self.compliance_stats["compliance_checks"] += 1
            if violations:
                self.compliance_stats["policy_violations"] += len(violations)
            
            # Return enforcement result
            return {
                "status": "success",
                "policy_code": policy_code,
                "policy_name": policy["description"],
                "compliant": len(violations) == 0,
                "violations": violations
            }
            
        except Exception as e:
            logger.error(f"Error enforcing policy {policy_code}: {str(e)}")
            return {
                "status": "error",
                "error": f"Policy enforcement error: {str(e)}"
            }
    
    def _check_property_classification(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a property is correctly classified.
        
        Args:
            data: Property data
            
        Returns:
            dict: Classification compliance result
        """
        property_type = data.get("property_type")
        property_subclass = data.get("property_subclass")
        
        # Check if property type exists
        if not property_type or property_type not in self.property_classifications:
            return {
                "compliant": False,
                "violations": [{
                    "field": "property_type",
                    "value": property_type,
                    "regulation": "Valid Property Classification Required",
                    "description": f"Property type '{property_type}' is not a valid classification"
                }]
            }
        
        # If subclass is provided, check if it's valid for the type
        violations = []
        if property_subclass:
            valid_subclasses = self.property_classifications[property_type]["subclasses"]
            if property_subclass not in valid_subclasses:
                violations.append({
                    "field": "property_subclass",
                    "value": property_subclass,
                    "regulation": "Valid Property Subclass Required",
                    "description": f"Property subclass '{property_subclass}' is not valid for type '{property_type}'"
                })
        
        # Check for required fields based on property type
        if property_type == "Residential":
            if "bedrooms" not in data or data["bedrooms"] is None:
                violations.append({
                    "field": "bedrooms",
                    "value": None,
                    "regulation": "Residential Property Fields Required",
                    "description": "Bedroom count is required for residential properties"
                })
            
            if "bathrooms" not in data or data["bathrooms"] is None:
                violations.append({
                    "field": "bathrooms",
                    "value": None,
                    "regulation": "Residential Property Fields Required",
                    "description": "Bathroom count is required for residential properties"
                })
        
        elif property_type == "Commercial":
            if "business_type" not in data or data["business_type"] is None:
                violations.append({
                    "field": "business_type",
                    "value": None,
                    "regulation": "Commercial Property Fields Required",
                    "description": "Business type is required for commercial properties"
                })
        
        elif property_type == "Agricultural":
            if "land_use" not in data or data["land_use"] is None:
                violations.append({
                    "field": "land_use",
                    "value": None,
                    "regulation": "Agricultural Property Fields Required",
                    "description": "Land use is required for agricultural properties"
                })
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations
        }
    
    def _check_exemption_eligibility(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if an exemption application meets eligibility requirements.
        
        Args:
            data: Exemption application data
            
        Returns:
            dict: Exemption compliance result
        """
        exemption_type = data.get("exemption_type")
        
        # Check if exemption type exists
        if not exemption_type or exemption_type not in self.exemption_types:
            return {
                "compliant": False,
                "violations": [{
                    "field": "exemption_type",
                    "value": exemption_type,
                    "regulation": "Valid Exemption Type Required",
                    "description": f"Exemption type '{exemption_type}' is not recognized"
                }]
            }
        
        # Get exemption requirements
        exemption_info = self.exemption_types[exemption_type]
        requirements = exemption_info["requirements"]
        
        # Check all requirements
        violations = []
        for req_name, req_value in requirements.items():
            if req_name not in data or data[req_name] is None:
                violations.append({
                    "field": req_name,
                    "value": None,
                    "regulation": f"{exemption_type} Exemption Requirements",
                    "description": f"Required field '{req_name}' is missing for {exemption_type} exemption"
                })
                continue
            
            # For boolean requirements
            if isinstance(req_value, bool):
                if data[req_name] != req_value:
                    violations.append({
                        "field": req_name,
                        "value": data[req_name],
                        "required": req_value,
                        "regulation": f"{exemption_type} Exemption Requirements",
                        "description": f"Field '{req_name}' must be {req_value} for {exemption_type} exemption"
                    })
            # For numeric requirements
            elif isinstance(req_value, (int, float)):
                # Age requirement (minimum age)
                if req_name == "age":
                    if int(data[req_name]) < req_value:
                        violations.append({
                            "field": req_name,
                            "value": data[req_name],
                            "required": f">= {req_value}",
                            "regulation": f"{exemption_type} Exemption Requirements",
                            "description": f"Age must be at least {req_value} for {exemption_type} exemption"
                        })
                # Income requirement (maximum income)
                elif req_name == "income":
                    if float(data[req_name]) > req_value:
                        violations.append({
                            "field": req_name,
                            "value": data[req_name],
                            "required": f"<= {req_value}",
                            "regulation": f"{exemption_type} Exemption Requirements",
                            "description": f"Income must be below ${req_value:,.2f} for {exemption_type} exemption"
                        })
                # Size requirement (minimum size)
                elif req_name == "min_size":
                    if float(data[req_name]) < req_value:
                        violations.append({
                            "field": req_name,
                            "value": data[req_name],
                            "required": f">= {req_value}",
                            "regulation": f"{exemption_type} Exemption Requirements",
                            "description": f"Size must be at least {req_value} acres for {exemption_type} exemption"
                        })
                # Default numeric comparison
                else:
                    if float(data[req_name]) != req_value:
                        violations.append({
                            "field": req_name,
                            "value": data[req_name],
                            "required": req_value,
                            "regulation": f"{exemption_type} Exemption Requirements",
                            "description": f"Field '{req_name}' must be {req_value} for {exemption_type} exemption"
                        })
        
        # Check for required documentation
        required_docs = exemption_info["documents"]
        provided_docs = data.get("documents", [])
        
        for doc in required_docs:
            if doc not in provided_docs:
                violations.append({
                    "field": "documents",
                    "value": provided_docs,
                    "required": doc,
                    "regulation": f"{exemption_type} Required Documentation",
                    "description": f"Required document '{doc}' is missing for {exemption_type} exemption"
                })
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations
        }
    
    def _check_tax_calculation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if tax calculations are correct.
        
        Args:
            data: Tax calculation data
            
        Returns:
            dict: Tax calculation compliance result
        """
        city = data.get("city")
        assessed_value = data.get("assessed_value")
        tax_amount = data.get("tax_amount")
        tax_year = data.get("tax_year", datetime.now().year)
        
        violations = []
        
        # Check if we have all required fields
        if not city:
            violations.append({
                "field": "city",
                "value": city,
                "regulation": "Valid Tax District Required",
                "description": "City/tax district is required for tax calculation validation"
            })
        
        if not assessed_value:
            violations.append({
                "field": "assessed_value",
                "value": assessed_value,
                "regulation": "Assessed Value Required",
                "description": "Assessed value is required for tax calculation validation"
            })
        
        if not tax_amount:
            violations.append({
                "field": "tax_amount",
                "value": tax_amount,
                "regulation": "Tax Amount Required",
                "description": "Tax amount is required for tax calculation validation"
            })
        
        # If we're missing required fields, return early
        if violations:
            return {
                "compliant": False,
                "violations": violations
            }
        
        # Check if city is in our tax districts
        if city not in self.tax_districts:
            if city == "":
                city = "Unincorporated"
            else:
                violations.append({
                    "field": "city",
                    "value": city,
                    "regulation": "Valid Tax District Required",
                    "description": f"'{city}' is not a recognized tax district in Benton County"
                })
                return {
                    "compliant": False,
                    "violations": violations
                }
        
        # Get mill rate for the tax district
        tax_district = self.tax_districts[city]
        mill_rate = tax_district["mill_rate"]
        
        # Check if tax year matches
        if tax_year != tax_district["year"]:
            violations.append({
                "field": "tax_year",
                "value": tax_year,
                "required": tax_district["year"],
                "regulation": "Current Tax Year Required",
                "description": f"Tax calculation is using outdated mill rate for {city}"
            })
        
        # Calculate expected tax amount
        expected_tax = (float(assessed_value) * mill_rate) / 1000
        actual_tax = float(tax_amount)
        
        # Allow for small rounding differences (up to $5)
        if abs(expected_tax - actual_tax) > 5:
            violations.append({
                "field": "tax_amount",
                "value": tax_amount,
                "expected": expected_tax,
                "regulation": "Accurate Tax Calculation Required",
                "description": f"Tax amount should be ${expected_tax:,.2f} based on assessed value of ${float(assessed_value):,.2f} and mill rate of {mill_rate}"
            })
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "calculation": {
                "mill_rate": mill_rate,
                "assessed_value": float(assessed_value),
                "expected_tax": expected_tax,
                "actual_tax": actual_tax,
                "difference": expected_tax - actual_tax
            }
        }
    
    def _check_assessment_cycle(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if assessment cycle requirements are met.
        
        Args:
            data: Assessment cycle data
            
        Returns:
            dict: Assessment cycle compliance result
        """
        last_revaluation = data.get("last_revaluation")
        last_inspection = data.get("last_inspection")
        current_year = datetime.now().year
        
        violations = []
        
        # Check if we have all required fields
        if not last_revaluation:
            violations.append({
                "field": "last_revaluation",
                "value": last_revaluation,
                "regulation": "Revaluation Records Required",
                "description": "Last revaluation date is required for assessment cycle validation"
            })
        
        if not last_inspection:
            violations.append({
                "field": "last_inspection",
                "value": last_inspection,
                "regulation": "Inspection Records Required",
                "description": "Last physical inspection date is required for assessment cycle validation"
            })
        
        # If we're missing required fields, return early
        if violations:
            return {
                "compliant": False,
                "violations": violations
            }
        
        # Get revaluation and inspection cycle requirements
        revaluation_cycle = self.assessment_cycle_rules["revaluation_cycle"]
        inspection_cycle = self.assessment_cycle_rules["physical_inspection_cycle"]
        
        # Check revaluation cycle compliance
        years_since_revaluation = current_year - int(last_revaluation)
        if years_since_revaluation > revaluation_cycle:
            violations.append({
                "field": "last_revaluation",
                "value": last_revaluation,
                "max_years": revaluation_cycle,
                "years_overdue": years_since_revaluation - revaluation_cycle,
                "regulation": "Revaluation Cycle Compliance",
                "description": f"Property is overdue for revaluation by {years_since_revaluation - revaluation_cycle} years"
            })
        
        # Check physical inspection cycle compliance
        years_since_inspection = current_year - int(last_inspection)
        if years_since_inspection > inspection_cycle:
            violations.append({
                "field": "last_inspection",
                "value": last_inspection,
                "max_years": inspection_cycle,
                "years_overdue": years_since_inspection - inspection_cycle,
                "regulation": "Physical Inspection Cycle Compliance",
                "description": f"Property is overdue for physical inspection by {years_since_inspection - inspection_cycle} years"
            })
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "cycle_info": {
                "revaluation_cycle": revaluation_cycle,
                "inspection_cycle": inspection_cycle,
                "years_since_revaluation": years_since_revaluation,
                "years_since_inspection": years_since_inspection,
                "next_revaluation_due": int(last_revaluation) + revaluation_cycle,
                "next_inspection_due": int(last_inspection) + inspection_cycle
            }
        }
    
    def check_compliance(self, check_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check compliance for a specific regulation or policy.
        
        Args:
            check_type: Type of compliance check
            data: Data to check
            
        Returns:
            dict: Compliance check result
        """
        try:
            if check_type == "property_classification":
                result = self._check_property_classification(data)
            elif check_type == "exemption_eligibility":
                result = self._check_exemption_eligibility(data)
            elif check_type == "tax_calculation":
                result = self._check_tax_calculation(data)
            elif check_type == "assessment_cycle":
                result = self._check_assessment_cycle(data)
            else:
                logger.warning(f"Unknown compliance check type: {check_type}")
                return {
                    "status": "error",
                    "error": f"Unknown compliance check type: {check_type}"
                }
            
            # Update compliance statistics
            self.compliance_stats["compliance_checks"] += 1
            if not result["compliant"]:
                self.compliance_stats["regulation_violations"] += len(result["violations"])
            
            # Return compliance check result
            return {
                "status": "success",
                "check_type": check_type,
                "compliance_result": result
            }
            
        except Exception as e:
            logger.error(f"Error performing compliance check {check_type}: {str(e)}")
            return {
                "status": "error",
                "error": f"Compliance check error: {str(e)}"
            }
    
    def verify_exemption(self, exemption_type: str, applicant_data: Dict[str, Any],
                       property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify eligibility for a specific exemption type.
        
        Args:
            exemption_type: Type of exemption
            applicant_data: Applicant data
            property_data: Property data
            
        Returns:
            dict: Exemption verification result
        """
        try:
            # Check if exemption type exists
            if exemption_type not in self.exemption_types:
                return {
                    "status": "error",
                    "error": f"Unknown exemption type: {exemption_type}"
                }
            
            # Get exemption requirements
            exemption_info = self.exemption_types[exemption_type]
            requirements = exemption_info["requirements"]
            
            # Check all requirements
            met_requirements = {}
            missing_requirements = {}
            
            for req_name, req_value in requirements.items():
                if req_name in applicant_data:
                    # For boolean requirements
                    if isinstance(req_value, bool):
                        met = applicant_data[req_name] == req_value
                    # For numeric requirements
                    elif isinstance(req_value, (int, float)):
                        # Age requirement (minimum age)
                        if req_name == "age":
                            met = int(applicant_data[req_name]) >= req_value
                        # Income requirement (maximum income)
                        elif req_name == "income":
                            met = float(applicant_data[req_name]) <= req_value
                        # Size requirement (minimum size)
                        elif req_name == "min_size":
                            met = float(applicant_data[req_name]) >= req_value
                        # Default numeric comparison
                        else:
                            met = float(applicant_data[req_name]) == req_value
                    else:
                        met = applicant_data[req_name] == req_value
                    
                    if met:
                        met_requirements[req_name] = applicant_data[req_name]
                    else:
                        missing_requirements[req_name] = {
                            "required": req_value,
                            "provided": applicant_data[req_name]
                        }
                else:
                    missing_requirements[req_name] = {
                        "required": req_value,
                        "provided": None
                    }
            
            # Check if all requirements are met
            eligible = len(missing_requirements) == 0
            
            # Update compliance statistics
            self.compliance_stats["exemption_checks"] += 1
            
            # Return verification result
            return {
                "status": "success",
                "exemption_type": exemption_type,
                "eligible": eligible,
                "met_requirements": met_requirements,
                "missing_requirements": missing_requirements,
                "required_documents": exemption_info["documents"]
            }
            
        except Exception as e:
            logger.error(f"Error verifying exemption {exemption_type}: {str(e)}")
            return {
                "status": "error",
                "error": f"Exemption verification error: {str(e)}"
            }
    
    def get_compliance_rules(self) -> Dict[str, Any]:
        """
        Get the compliance rules being used by the agent.
        
        Returns:
            dict: Compliance rules information
        """
        return {
            "assessment_cycle_rules": self.assessment_cycle_rules,
            "property_classifications": self.property_classifications,
            "exemption_types": self.exemption_types,
            "tax_districts": self.tax_districts,
            "compliance_policies": self.compliance_policies,
            "audit_requirements": self.audit_requirements
        }
    
    def get_compliance_stats(self) -> Dict[str, Any]:
        """
        Get compliance statistics for the agent.
        
        Returns:
            dict: Compliance statistics
        """
        return self.compliance_stats