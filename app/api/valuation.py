"""
Valuation API for Benton County Assessor's Office AI Platform

This module provides the FastAPI routes for property valuation services.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from mcp.agents.valuation.agent import ValuationAgent
from mcp.message import Message, MessageType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("valuation_api")

# Create router
router = APIRouter(
    prefix="/api/v1/valuation",
    tags=["valuation"],
    responses={404: {"description": "Not found"}}
)

# Initialize valuation agent
valuation_agent = ValuationAgent()

# Pydantic models for request/response data
class ValuationRequest(BaseModel):
    """Request model for property valuation."""
    property_id: int = Field(..., description="ID of the property to valuate")
    methodology: str = Field("all", description="Valuation methodology to use (cost, market, income, or all)")
    valuation_date: Optional[str] = Field(None, description="Date for valuation (defaults to current date)")

class ValuationResponse(BaseModel):
    """Response model for property valuation."""
    success: bool = Field(..., description="Whether the valuation was successful")
    property_id: int = Field(..., description="ID of the property that was valuated")
    valuation_date: str = Field(..., description="Date of the valuation")
    results: Dict[str, Any] = Field(..., description="Valuation results by methodology")
    metadata: Dict[str, Any] = Field(..., description="Metadata about the valuation")
    error: Optional[str] = Field(None, description="Error message if valuation failed")

class TrendAnalysisRequest(BaseModel):
    """Request model for property value trend analysis."""
    property_id: int = Field(..., description="ID of the property to analyze")
    years: int = Field(3, description="Number of years to include in the analysis")

class TrendAnalysisResponse(BaseModel):
    """Response model for property value trend analysis."""
    success: bool = Field(..., description="Whether the analysis was successful")
    property_id: int = Field(..., description="ID of the property that was analyzed")
    current_value: float = Field(..., description="Current estimated value of the property")
    trend_data: List[Dict[str, Any]] = Field(..., description="Trend data points")
    metadata: Dict[str, Any] = Field(..., description="Metadata about the analysis")
    error: Optional[str] = Field(None, description="Error message if analysis failed")

class ComparativeAnalysisRequest(BaseModel):
    """Request model for comparative property analysis."""
    property_id: int = Field(..., description="ID of the subject property")
    comparison_property_ids: Optional[List[int]] = Field(None, description="IDs of properties to compare with")

class ComparativeAnalysisResponse(BaseModel):
    """Response model for comparative property analysis."""
    success: bool = Field(..., description="Whether the analysis was successful")
    property_id: int = Field(..., description="ID of the subject property")
    subject_property: Dict[str, Any] = Field(..., description="Details of the subject property")
    comparison_properties: List[Dict[str, Any]] = Field(..., description="Details of the comparison properties")
    metrics: Dict[str, Any] = Field(..., description="Comparison metrics")
    metadata: Dict[str, Any] = Field(..., description="Metadata about the analysis")
    error: Optional[str] = Field(None, description="Error message if analysis failed")


@router.post("/valuate", response_model=ValuationResponse)
def valuate_property(property_id: int, methodology: str = "all", valuation_date: Optional[str] = None):
    """
    Valuate a property using the specified methodology.
    
    Args:
        request: Valuation request parameters
        
    Returns:
        Valuation results
    """
    try:
        logger.info(f"Received valuation request for property {property_id}")
        
        # Create valuation request message
        message = Message(
            from_agent_id="api_client",
            to_agent_id=valuation_agent.agent_id,
            message_type=MessageType.VALUATION_REQUEST,
            content={
                "property_id": property_id,
                "methodology": methodology,
                "valuation_date": valuation_date or datetime.now().strftime("%Y-%m-%d")
            }
        )
        
        # Process the message directly (synchronous for API)
        valuation_agent._handle_valuation_request(message)
        
        # Extract results from the latest response message
        # In a real implementation, this would use async messaging or callbacks
        # Here we directly access the response for simplicity
        response_calls = valuation_agent.send_message.call_args_list
        if not response_calls:
            raise HTTPException(status_code=500, detail="No response from valuation agent")
        
        args, kwargs = response_calls[-1]
        response_payload = kwargs.get("payload", {})
        
        return response_payload
    
    except Exception as e:
        logger.error(f"Error processing valuation request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trend-analysis", response_model=TrendAnalysisResponse)
def analyze_trends(property_id: int, years: int = 3):
    """
    Analyze property value trends.
    
    Args:
        request: Trend analysis request parameters
        
    Returns:
        Trend analysis results
    """
    try:
        logger.info(f"Received trend analysis request for property {property_id}")
        
        # Create trend analysis request message
        message = Message(
            from_agent_id="api_client",
            to_agent_id=valuation_agent.agent_id,
            message_type=MessageType.TREND_ANALYSIS_REQUEST,
            content={
                "property_id": property_id,
                "years": years
            }
        )
        
        # Process the message directly (synchronous for API)
        valuation_agent._handle_trend_analysis_request(message)
        
        # Extract results from the latest response message
        response_calls = valuation_agent.send_message.call_args_list
        if not response_calls:
            raise HTTPException(status_code=500, detail="No response from valuation agent")
        
        args, kwargs = response_calls[-1]
        response_payload = kwargs.get("payload", {})
        
        return response_payload
    
    except Exception as e:
        logger.error(f"Error processing trend analysis request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comparative-analysis", response_model=ComparativeAnalysisResponse)
def analyze_comparatives(property_id: int, comparison_property_ids: Optional[List[int]] = None):
    """
    Perform comparative property analysis.
    
    Args:
        request: Comparative analysis request parameters
        
    Returns:
        Comparative analysis results
    """
    try:
        logger.info(f"Received comparative analysis request for property {property_id}")
        
        # Create comparative analysis request message
        message = Message(
            from_agent_id="api_client",
            to_agent_id=valuation_agent.agent_id,
            message_type=MessageType.COMPARATIVE_ANALYSIS_REQUEST,
            content={
                "property_id": property_id,
                "comparison_property_ids": comparison_property_ids
            }
        )
        
        # Process the message directly (synchronous for API)
        valuation_agent._handle_comparative_analysis_request(message)
        
        # Extract results from the latest response message
        response_calls = valuation_agent.send_message.call_args_list
        if not response_calls:
            raise HTTPException(status_code=500, detail="No response from valuation agent")
        
        args, kwargs = response_calls[-1]
        response_payload = kwargs.get("payload", {})
        
        return response_payload
    
    except Exception as e:
        logger.error(f"Error processing comparative analysis request: {e}")
        raise HTTPException(status_code=500, detail=str(e))