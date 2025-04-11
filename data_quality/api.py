"""
API Module for Data Quality and Compliance

This module provides FastAPI endpoints for accessing data quality and compliance
validation functionality.
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field

from .validator import DataValidator, ValidationResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(prefix="/api/v1/data-quality", tags=["Data Quality"])

# Create data validator instance
validator = DataValidator(use_benton_rules=True)

# Define Pydantic models for API
class ValidationError(BaseModel):
    """Validation error model."""
    field: str
    message: str

class ValidationResponse(BaseModel):
    """Validation response model."""
    valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    timestamp: str

class ValidationRequest(BaseModel):
    """Validation request model."""
    entity_type: str
    data: Dict[str, Any]

class CompleteRecordRequest(BaseModel):
    """Complete record validation request model."""
    parcel: Optional[Dict[str, Any]] = None
    property: Optional[Dict[str, Any]] = None
    account: Optional[Dict[str, Any]] = None

class CompleteRecordResponse(BaseModel):
    """Complete record validation response model."""
    overall_valid: bool
    results: Dict[str, ValidationResponse]


@router.post(
    "/validate",
    response_model=ValidationResponse,
    summary="Validate a single entity",
    description="Validate a single entity (parcel, property, account) against Washington State "
                "Department of Revenue standards and Benton County regulations."
)
async def validate_entity(request: ValidationRequest):
    """
    Validate a single entity.
    
    Args:
        request: ValidationRequest object containing entity_type and data
        
    Returns:
        ValidationResponse object containing validation results
    """
    if request.entity_type not in ["parcel", "property", "account"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entity type. Must be one of: parcel, property, account."
        )
    
    try:
        result = validator.validate_entity(request.data, request.entity_type)
        return ValidationResponse(
            valid=result.valid,
            errors=[ValidationError(field=err["field"], message=err["message"]) for err in result.errors],
            timestamp=result.timestamp
        )
    except Exception as e:
        logger.error(f"Error validating {request.entity_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation error: {str(e)}"
        )


@router.post(
    "/validate/parcel",
    response_model=ValidationResponse,
    summary="Validate parcel data",
    description="Validate parcel data against Washington State Department of Revenue "
                "standards and Benton County regulations."
)
async def validate_parcel(data: Dict[str, Any]):
    """
    Validate parcel data.
    
    Args:
        data: Dictionary containing parcel data
        
    Returns:
        ValidationResponse object containing validation results
    """
    try:
        result = validator.validate_parcel(data)
        return ValidationResponse(
            valid=result.valid,
            errors=[ValidationError(field=err["field"], message=err["message"]) for err in result.errors],
            timestamp=result.timestamp
        )
    except Exception as e:
        logger.error(f"Error validating parcel: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation error: {str(e)}"
        )


@router.post(
    "/validate/property",
    response_model=ValidationResponse,
    summary="Validate property data",
    description="Validate property data against Washington State Department of Revenue "
                "standards and Benton County regulations."
)
async def validate_property(data: Dict[str, Any]):
    """
    Validate property data.
    
    Args:
        data: Dictionary containing property data
        
    Returns:
        ValidationResponse object containing validation results
    """
    try:
        result = validator.validate_property(data)
        return ValidationResponse(
            valid=result.valid,
            errors=[ValidationError(field=err["field"], message=err["message"]) for err in result.errors],
            timestamp=result.timestamp
        )
    except Exception as e:
        logger.error(f"Error validating property: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation error: {str(e)}"
        )


@router.post(
    "/validate/account",
    response_model=ValidationResponse,
    summary="Validate account data",
    description="Validate account data against Washington State Department of Revenue "
                "standards and Benton County regulations."
)
async def validate_account(data: Dict[str, Any]):
    """
    Validate account data.
    
    Args:
        data: Dictionary containing account data
        
    Returns:
        ValidationResponse object containing validation results
    """
    try:
        result = validator.validate_account(data)
        return ValidationResponse(
            valid=result.valid,
            errors=[ValidationError(field=err["field"], message=err["message"]) for err in result.errors],
            timestamp=result.timestamp
        )
    except Exception as e:
        logger.error(f"Error validating account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation error: {str(e)}"
        )


@router.post(
    "/validate/complete-record",
    response_model=CompleteRecordResponse,
    summary="Validate a complete record",
    description="Validate a complete record containing parcel, property, and account data "
                "against Washington State Department of Revenue standards and Benton County regulations."
)
async def validate_complete_record(request: CompleteRecordRequest):
    """
    Validate a complete record.
    
    Args:
        request: CompleteRecordRequest object containing parcel, property, and account data
        
    Returns:
        CompleteRecordResponse object containing validation results
    """
    try:
        record = request.dict(exclude_none=True)
        overall_valid, results = validator.validate_complete_record(record)
        
        # Convert ValidationResult objects to ValidationResponse models
        response_results = {}
        for entity_type, result in results.items():
            response_results[entity_type] = ValidationResponse(
                valid=result.valid,
                errors=[ValidationError(field=err["field"], message=err["message"]) for err in result.errors],
                timestamp=result.timestamp
            )
        
        return CompleteRecordResponse(
            overall_valid=overall_valid,
            results=response_results
        )
    except Exception as e:
        logger.error(f"Error validating complete record: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation error: {str(e)}"
        )


@router.get(
    "/rules/summary",
    response_model=Dict[str, Any],
    summary="Get validation rules summary",
    description="Get a summary of the validation rules being applied."
)
async def get_rules_summary():
    """
    Get a summary of the validation rules being applied.
    
    Returns:
        Dictionary containing validation rules summary
    """
    try:
        # Get rules from validator
        rules = validator.rules
        
        # Extract rule summaries
        summary = {
            "rules_type": "Benton County Rules" if isinstance(rules, validator.rules.__class__) else "Washington State Standards",
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
        
        return summary
    except Exception as e:
        logger.error(f"Error getting rules summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )