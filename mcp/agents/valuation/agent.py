"""
Valuation Agent for Benton County Assessor's Office AI Platform

This module implements the Valuation Agent, which is responsible for
estimating property values using various methodologies, including
cost approach, market comparison, and income approach.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from mcp.agent import Agent
from mcp.message import Message, MessageType
from models import Parcel, Property, Account, PropertyImage
from app_setup import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("valuation_agent")


class ValuationAgent(Agent):
    """
    Valuation Agent for property assessment.
    
    This agent implements various property valuation methodologies and
    serves requests for property value estimates, comparative analyses,
    and trend predictions.
    """
    
    def __init__(self, agent_id: str = "valuation_agent", **kwargs):
        """
        Initialize the Valuation Agent.
        
        Args:
            agent_id: Unique identifier for this agent
            **kwargs: Additional arguments to pass to the base Agent class
        """
        super().__init__(agent_id=agent_id, **kwargs)
        
        # Set agent metadata
        self.metadata = {
            "name": "Valuation Agent",
            "description": "Estimates property values using various methodologies",
            "version": "1.0.0",
            "capabilities": [
                "cost_approach",
                "market_comparison",
                "income_approach",
                "trend_analysis",
                "value_reconciliation"
            ]
        }
        
        # Reference data
        self._cost_tables = {}  # Construction cost tables by property type
        self._depreciation_tables = {}  # Depreciation rates by age and quality
        self._market_adjustment_factors = {}  # Market adjustment factors by location
        self._cap_rates = {}  # Capitalization rates by property type
        
        # Load reference data
        self._load_reference_data()
        
        # Message handlers
        self.register_message_handler(MessageType.VALUATION_REQUEST, self._handle_valuation_request)
        self.register_message_handler(MessageType.TREND_ANALYSIS_REQUEST, self._handle_trend_analysis_request)
        self.register_message_handler(MessageType.COMPARATIVE_ANALYSIS_REQUEST, self._handle_comparative_analysis_request)
        
        logger.info(f"Valuation Agent '{agent_id}' initialized")
    
    def _load_reference_data(self) -> None:
        """Load reference data for valuation calculations."""
        try:
            # Note: In a real implementation, this would load tables from files or database
            # For now, we'll use simplified reference data
            
            # Basic construction cost estimates per square foot by property type
            self._cost_tables = {
                "Residential": {
                    "Low": 125.0,   # Low quality, cost per square foot
                    "Average": 175.0,  # Average quality
                    "Good": 225.0,  # Good quality
                    "Excellent": 300.0  # Excellent quality
                },
                "Commercial": {
                    "Low": 150.0,
                    "Average": 200.0,
                    "Good": 275.0,
                    "Excellent": 350.0
                },
                "Agricultural": {
                    "Low": 75.0,
                    "Average": 125.0,
                    "Good": 175.0,
                    "Excellent": 225.0
                }
            }
            
            # Depreciation rates by age ranges and quality
            self._depreciation_tables = {
                "0-5": 0.05,    # 0-5 years: 5% depreciation
                "6-10": 0.10,   # 6-10 years: 10% depreciation
                "11-20": 0.20,  # 11-20 years: 20% depreciation
                "21-30": 0.30,  # 21-30 years: 30% depreciation
                "31-40": 0.40,  # 31-40 years: 40% depreciation
                "41+": 0.50     # 41+ years: 50% depreciation
            }
            
            # Location adjustment factors by city
            self._market_adjustment_factors = {
                "Richland": 1.15,        # Richland properties valued 15% higher
                "Kennewick": 1.05,       # Kennewick properties valued 5% higher
                "Pasco": 0.95,           # Pasco properties valued 5% lower
                "West Richland": 1.10,   # West Richland properties valued 10% higher
                "Prosser": 0.90,         # Prosser properties valued 10% lower
                "default": 1.00          # Default adjustment factor
            }
            
            # Capitalization rates by property type (for income approach)
            self._cap_rates = {
                "Residential": 0.06,     # 6% cap rate for residential
                "Commercial": 0.07,      # 7% cap rate for commercial
                "Agricultural": 0.05,    # 5% cap rate for agricultural
                "default": 0.06          # Default cap rate
            }
            
            logger.info("Reference data loaded successfully")
        
        except Exception as e:
            logger.error(f"Error loading reference data: {e}")
            # Initialize with empty data if loading fails
            self._cost_tables = {}
            self._depreciation_tables = {}
            self._market_adjustment_factors = {}
            self._cap_rates = {}
    
    def _handle_valuation_request(self, message: Message) -> None:
        """
        Handle a property valuation request.
        
        Args:
            message: Valuation request message
        """
        try:
            # Extract request data from message payload
            payload = message.payload
            property_id = payload.get("property_id")
            valuation_date = payload.get("valuation_date", datetime.now().strftime("%Y-%m-%d"))
            methodology = payload.get("methodology", "all")  # 'cost', 'market', 'income', or 'all'
            
            logger.info(f"Processing valuation request for property {property_id} using {methodology} approach")
            
            # Connect to database
            from app_setup import db
            
            # Get property details
            with db.engine.connect() as conn:
                property_details = {}
                
                # Query database for property
                # In a real implementation, you would use more extensive queries
                property_query = """
                    SELECT p.*, a.* 
                    FROM properties p
                    JOIN accounts a ON p.account_id = a.id
                    WHERE p.id = :property_id
                """
                
                result = conn.execute(property_query, {"property_id": property_id})
                row = result.fetchone()
                
                if not row:
                    # Property not found
                    # Create response using the response builder in Message class
                    response = message.create_response(
                        payload={
                            "success": False,
                            "error": f"Property with ID {property_id} not found",
                            "property_id": property_id,
                            "valuation_date": valuation_date,
                            "results": {},
                            "metadata": {}
                        }
                    )
                    # Send the response
                    self.send_message(response)
                    return
                
                # Extract property details from row
                property_details = dict(row._mapping)
                
                # Calculate value using requested methodology
                valuation_results = {}
                
                if methodology in ["cost", "all"]:
                    # Cost approach
                    cost_value = self._calculate_cost_approach(property_details)
                    valuation_results["cost_approach"] = cost_value
                
                if methodology in ["market", "all"]:
                    # Market comparison approach
                    market_value = self._calculate_market_approach(property_details, conn)
                    valuation_results["market_approach"] = market_value
                
                if methodology in ["income", "all"]:
                    # Income approach (for commercial properties)
                    if property_details.get("property_type") == "Commercial":
                        income_value = self._calculate_income_approach(property_details)
                        valuation_results["income_approach"] = income_value
                
                # Reconcile values if multiple approaches used
                if len(valuation_results) > 1:
                    reconciled_value = self._reconcile_values(valuation_results, property_details)
                    valuation_results["reconciled_value"] = reconciled_value
                
                # Prepare response
                response = {
                    "success": True,
                    "property_id": property_id,
                    "valuation_date": valuation_date,
                    "results": valuation_results,
                    "metadata": {
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                # Create response using the response builder in Message class
                response_message = message.create_response(payload=response)
                # Send the response
                self.send_message(response_message)
                
                logger.info(f"Valuation completed for property {property_id}")
        
        except Exception as e:
            logger.error(f"Error processing valuation request: {e}")
            
            # Create error response using Message's response builder
            error_response = message.create_response(
                payload={
                    "success": False,
                    "property_id": property_id,
                    "valuation_date": valuation_date,
                    "error": str(e),
                    "results": {},
                    "metadata": {}
                }
            )
            # Send the error response
            self.send_message(error_response)
    
    def _calculate_cost_approach(self, property_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate property value using the cost approach.
        
        Args:
            property_details: Property details from database
            
        Returns:
            Dictionary with cost approach valuation details
        """
        try:
            # Extract needed properties
            property_type = property_details.get("property_type", "Residential")
            quality = property_details.get("quality", "Average")
            square_feet = property_details.get("living_area", 0)
            year_built = property_details.get("year_built", 2000)
            city = property_details.get("city", "default")
            
            # Calculate base cost
            if property_type not in self._cost_tables:
                property_type = "Residential"  # Default to residential if type not found
            
            cost_table = self._cost_tables[property_type]
            
            if quality not in cost_table:
                quality = "Average"  # Default to average quality if not found
            
            base_cost_per_sqft = cost_table[quality]
            replacement_cost = base_cost_per_sqft * square_feet
            
            # Calculate depreciation
            current_year = datetime.now().year
            age = current_year - year_built
            
            # Determine depreciation rate based on age
            depreciation_rate = 0.0
            if age <= 5:
                depreciation_rate = self._depreciation_tables.get("0-5", 0.05)
            elif age <= 10:
                depreciation_rate = self._depreciation_tables.get("6-10", 0.10)
            elif age <= 20:
                depreciation_rate = self._depreciation_tables.get("11-20", 0.20)
            elif age <= 30:
                depreciation_rate = self._depreciation_tables.get("21-30", 0.30)
            elif age <= 40:
                depreciation_rate = self._depreciation_tables.get("31-40", 0.40)
            else:
                depreciation_rate = self._depreciation_tables.get("41+", 0.50)
            
            # Apply depreciation
            depreciation_amount = replacement_cost * depreciation_rate
            depreciated_cost = replacement_cost - depreciation_amount
            
            # Apply location adjustment
            location_factor = self._market_adjustment_factors.get(city, self._market_adjustment_factors["default"])
            adjusted_cost = depreciated_cost * location_factor
            
            # Land value (simplified - in a real implementation, land would be valued separately)
            land_value = property_details.get("land_value", square_feet * 10)  # Simplified land value calculation
            
            # Total value
            total_value = adjusted_cost + land_value
            
            return {
                "total_value": round(total_value, 2),
                "details": {
                    "replacement_cost": round(replacement_cost, 2),
                    "depreciation_rate": round(depreciation_rate, 2),
                    "depreciation_amount": round(depreciation_amount, 2),
                    "depreciated_cost": round(depreciated_cost, 2),
                    "location_factor": round(location_factor, 2),
                    "adjusted_cost": round(adjusted_cost, 2),
                    "land_value": round(land_value, 2)
                }
            }
        
        except Exception as e:
            logger.error(f"Error in cost approach calculation: {e}")
            return {
                "total_value": 0,
                "error": str(e)
            }
    
    def _calculate_market_approach(self, property_details: Dict[str, Any], conn) -> Dict[str, Any]:
        """
        Calculate property value using the market comparison approach.
        
        Args:
            property_details: Property details from database
            conn: Database connection
            
        Returns:
            Dictionary with market approach valuation details
        """
        try:
            # Extract needed properties
            property_type = property_details.get("property_type", "Residential")
            square_feet = property_details.get("living_area", 0)
            bedrooms = property_details.get("bedrooms", 0)
            bathrooms = property_details.get("bathrooms", 0)
            city = property_details.get("city", "default")
            property_id = property_details.get("id")
            
            # Find comparable properties
            # In a real implementation, this would use more sophisticated matching
            comp_query = """
                SELECT p.*, a.city, a.property_type
                FROM properties p
                JOIN accounts a ON p.account_id = a.id
                WHERE a.property_type = :property_type
                AND p.id != :property_id
                AND a.city = :city
                AND p.living_area BETWEEN :min_size AND :max_size
                LIMIT 5
            """
            
            # Define acceptable size range (±20%)
            min_size = max(1, int(square_feet * 0.8))
            max_size = int(square_feet * 1.2)
            
            result = conn.execute(
                comp_query, 
                {
                    "property_type": property_type,
                    "property_id": property_id,
                    "city": city,
                    "min_size": min_size,
                    "max_size": max_size
                }
            )
            
            comps = [dict(row._mapping) for row in result]
            
            # If not enough comps in the same city, try nearby cities
            if len(comps) < 3:
                broader_query = """
                    SELECT p.*, a.city, a.property_type
                    FROM properties p
                    JOIN accounts a ON p.account_id = a.id
                    WHERE a.property_type = :property_type
                    AND p.id != :property_id
                    AND p.living_area BETWEEN :min_size AND :max_size
                    LIMIT :limit
                """
                
                result = conn.execute(
                    broader_query,
                    {
                        "property_type": property_type,
                        "property_id": property_id,
                        "min_size": min_size,
                        "max_size": max_size,
                        "limit": 5 - len(comps)
                    }
                )
                
                more_comps = [dict(row._mapping) for row in result]
                comps.extend(more_comps)
            
            # If still no comps, use a fallback method
            if not comps:
                logger.warning(f"No comparable properties found for property {property_id}")
                # Use cost approach as fallback
                return {
                    "total_value": self._calculate_cost_approach(property_details)["total_value"],
                    "details": {
                        "method": "fallback_to_cost_approach",
                        "reason": "No comparable properties found"
                    }
                }
            
            # Calculate adjustments and values
            adjusted_values = []
            comp_details = []
            
            for comp in comps:
                # Size adjustment (value per square foot)
                comp_size = comp.get("living_area", 0)
                comp_value = comp.get("total_value", 0)
                
                if comp_size == 0 or comp_value == 0:
                    continue
                
                value_per_sqft = comp_value / comp_size
                
                # Bedroom adjustment
                comp_bedrooms = comp.get("bedrooms", 0)
                bedroom_diff = bedrooms - comp_bedrooms
                bedroom_adjustment = bedroom_diff * 5000  # $5000 per bedroom difference
                
                # Bathroom adjustment
                comp_bathrooms = comp.get("bathrooms", 0)
                bathroom_diff = bathrooms - comp_bathrooms
                bathroom_adjustment = bathroom_diff * 7500  # $7500 per bathroom difference
                
                # Location adjustment
                comp_city = comp.get("city", "default")
                subject_factor = self._market_adjustment_factors.get(city, self._market_adjustment_factors["default"])
                comp_factor = self._market_adjustment_factors.get(comp_city, self._market_adjustment_factors["default"])
                location_adjustment = (subject_factor / comp_factor - 1) * comp_value
                
                # Total adjustments
                total_adjustment = bedroom_adjustment + bathroom_adjustment + location_adjustment
                
                # Adjusted value
                adjusted_value = comp_value + total_adjustment
                adjusted_values.append(adjusted_value)
                
                # Save comp details for reporting
                comp_details.append({
                    "comp_id": comp.get("id"),
                    "comp_value": comp_value,
                    "comp_size": comp_size,
                    "value_per_sqft": value_per_sqft,
                    "bedroom_adjustment": bedroom_adjustment,
                    "bathroom_adjustment": bathroom_adjustment,
                    "location_adjustment": location_adjustment,
                    "total_adjustment": total_adjustment,
                    "adjusted_value": adjusted_value
                })
            
            # Calculate average of adjusted values
            if adjusted_values:
                average_value = sum(adjusted_values) / len(adjusted_values)
                median_value = sorted(adjusted_values)[len(adjusted_values) // 2]
                
                # Weight factors: more emphasis on median for stability
                weighted_value = (average_value * 0.4) + (median_value * 0.6)
                
                return {
                    "total_value": round(weighted_value, 2),
                    "details": {
                        "comparable_count": len(comps),
                        "average_value": round(average_value, 2),
                        "median_value": round(median_value, 2),
                        "comparable_properties": comp_details
                    }
                }
            else:
                # Fallback if no valid adjusted values
                return {
                    "total_value": self._calculate_cost_approach(property_details)["total_value"],
                    "details": {
                        "method": "fallback_to_cost_approach",
                        "reason": "No valid comparable properties found"
                    }
                }
        
        except Exception as e:
            logger.error(f"Error in market approach calculation: {e}")
            return {
                "total_value": 0,
                "error": str(e)
            }
    
    def _calculate_income_approach(self, property_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate property value using the income approach.
        
        Args:
            property_details: Property details from database
            
        Returns:
            Dictionary with income approach valuation details
        """
        try:
            # Extract needed properties
            property_type = property_details.get("property_type", "Commercial")
            square_feet = property_details.get("living_area", 0)
            city = property_details.get("city", "default")
            
            # Only applicable for commercial properties
            if property_type != "Commercial":
                return {
                    "total_value": 0,
                    "details": {
                        "reason": "Income approach only applicable for Commercial properties"
                    }
                }
            
            # Estimate rental income (simplified)
            # In a real implementation, this would use actual rental data or income records
            monthly_rent_per_sqft = 0.0
            
            # Base rent by city
            if city == "Richland":
                monthly_rent_per_sqft = 1.75
            elif city == "Kennewick":
                monthly_rent_per_sqft = 1.60
            elif city == "Pasco":
                monthly_rent_per_sqft = 1.40
            elif city == "West Richland":
                monthly_rent_per_sqft = 1.50
            else:
                monthly_rent_per_sqft = 1.25
            
            # Calculate annual gross income
            annual_rent_per_sqft = monthly_rent_per_sqft * 12
            gross_annual_income = annual_rent_per_sqft * square_feet
            
            # Apply vacancy and collection loss (7%)
            vacancy_loss = gross_annual_income * 0.07
            effective_gross_income = gross_annual_income - vacancy_loss
            
            # Operating expenses (40% of EGI for commercial properties)
            operating_expenses = effective_gross_income * 0.40
            
            # Net operating income (NOI)
            noi = effective_gross_income - operating_expenses
            
            # Apply capitalization rate
            cap_rate = self._cap_rates.get(property_type, self._cap_rates["default"])
            income_value = noi / cap_rate
            
            return {
                "total_value": round(income_value, 2),
                "details": {
                    "monthly_rent_per_sqft": round(monthly_rent_per_sqft, 2),
                    "annual_rent_per_sqft": round(annual_rent_per_sqft, 2),
                    "gross_annual_income": round(gross_annual_income, 2),
                    "vacancy_loss": round(vacancy_loss, 2),
                    "effective_gross_income": round(effective_gross_income, 2),
                    "operating_expenses": round(operating_expenses, 2),
                    "net_operating_income": round(noi, 2),
                    "cap_rate": round(cap_rate, 2)
                }
            }
        
        except Exception as e:
            logger.error(f"Error in income approach calculation: {e}")
            return {
                "total_value": 0,
                "error": str(e)
            }
    
    def _reconcile_values(self, valuation_results: Dict[str, Any], property_details: Dict[str, Any]) -> float:
        """
        Reconcile values from different approaches.
        
        Args:
            valuation_results: Results from different valuation approaches
            property_details: Property details from database
            
        Returns:
            Reconciled property value
        """
        try:
            property_type = property_details.get("property_type", "Residential")
            
            # Extract values from different approaches
            cost_value = valuation_results.get("cost_approach", {}).get("total_value", 0)
            market_value = valuation_results.get("market_approach", {}).get("total_value", 0)
            income_value = valuation_results.get("income_approach", {}).get("total_value", 0)
            
            # Define weights by property type
            weights = {
                "Residential": {
                    "cost_approach": 0.30,
                    "market_approach": 0.70,
                    "income_approach": 0.00
                },
                "Commercial": {
                    "cost_approach": 0.20,
                    "market_approach": 0.30,
                    "income_approach": 0.50
                },
                "Agricultural": {
                    "cost_approach": 0.40,
                    "market_approach": 0.50,
                    "income_approach": 0.10
                }
            }
            
            # Get weights for this property type
            property_weights = weights.get(property_type, weights["Residential"])
            
            # Calculate weighted value
            weighted_value = 0.0
            total_weight = 0.0
            
            if cost_value > 0:
                weight = property_weights["cost_approach"]
                weighted_value += cost_value * weight
                total_weight += weight
            
            if market_value > 0:
                weight = property_weights["market_approach"]
                weighted_value += market_value * weight
                total_weight += weight
            
            if income_value > 0:
                weight = property_weights["income_approach"]
                weighted_value += income_value * weight
                total_weight += weight
            
            # Avoid division by zero
            if total_weight > 0:
                reconciled_value = weighted_value / total_weight
            else:
                # Fallback if no valid values
                reconciled_value = max(cost_value, market_value, income_value)
                if reconciled_value == 0:
                    # If all approaches failed, use a simple square footage calculation
                    square_feet = property_details.get("living_area", 0)
                    reconciled_value = square_feet * 150  # Simple $150/sqft default
            
            return round(reconciled_value, 2)
        
        except Exception as e:
            logger.error(f"Error in value reconciliation: {e}")
            
            # Return highest value as fallback
            values = [
                valuation_results.get("cost_approach", {}).get("total_value", 0),
                valuation_results.get("market_approach", {}).get("total_value", 0),
                valuation_results.get("income_approach", {}).get("total_value", 0)
            ]
            
            highest_value = max(values)
            if highest_value > 0:
                return highest_value
            else:
                # Last resort fallback
                square_feet = property_details.get("living_area", 0)
                return square_feet * 150  # Simple $150/sqft default
    
    def _handle_trend_analysis_request(self, message: Message) -> None:
        """
        Handle a property value trend analysis request.
        
        Args:
            message: Trend analysis request message
        """
        try:
            # Extract request data from message payload
            payload = message.payload
            property_id = payload.get("property_id")
            years = payload.get("years", 3)  # Number of years to analyze
            
            logger.info(f"Processing trend analysis request for property {property_id}")
            
            # Connect to database
            from app_setup import db
            
            # Get property details
            with db.engine.connect() as conn:
                # Query database for property
                property_query = """
                    SELECT p.*, a.* 
                    FROM properties p
                    JOIN accounts a ON p.account_id = a.id
                    WHERE p.id = :property_id
                """
                
                result = conn.execute(property_query, {"property_id": property_id})
                row = result.fetchone()
                
                if not row:
                    # Property not found
                    self.send_message(
                        message_type=MessageType.TREND_ANALYSIS_RESPONSE,
                        target_agent_id=message.source_agent_id,
                        payload={
                            "success": False,
                            "error": f"Property with ID {property_id} not found",
                            "original_request": payload
                        },
                        correlation_id=message.message_id
                    )
                    return
                
                # Extract property details
                property_details = dict(row._mapping)
                
                # Calculate current value
                current_value = self._calculate_cost_approach(property_details)["total_value"]
                
                # Generate trend data
                trend_data = self._generate_trend_data(property_details, current_value, years)
                
                # Send response
                self.send_message(
                    message_type=MessageType.TREND_ANALYSIS_RESPONSE,
                    target_agent_id=message.source_agent_id,
                    payload={
                        "success": True,
                        "property_id": property_id,
                        "current_value": current_value,
                        "trend_data": trend_data,
                        "metadata": {
                            "agent_id": self.agent_id,
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    correlation_id=message.message_id
                )
                
                logger.info(f"Trend analysis completed for property {property_id}")
        
        except Exception as e:
            logger.error(f"Error processing trend analysis request: {e}")
            
            # Send error response
            self.send_message(
                message_type=MessageType.TREND_ANALYSIS_RESPONSE,
                target_agent_id=message.source_agent_id,
                payload={
                    "success": False,
                    "error": str(e),
                    "original_request": payload
                },
                correlation_id=message.message_id
            )
    
    def _generate_trend_data(self, property_details: Dict[str, Any], current_value: float, years: int) -> List[Dict[str, Any]]:
        """
        Generate property value trend data.
        
        Args:
            property_details: Property details from database
            current_value: Current property value
            years: Number of years to include
            
        Returns:
            List of trend data points
        """
        try:
            # Extract property details
            city = property_details.get("city", "default")
            property_type = property_details.get("property_type", "Residential")
            
            # Growth rates by city and property type
            growth_rates = {
                "Richland": {
                    "Residential": 0.045,  # 4.5% annual growth
                    "Commercial": 0.035,   # 3.5% annual growth
                    "Agricultural": 0.025  # 2.5% annual growth
                },
                "Kennewick": {
                    "Residential": 0.042,
                    "Commercial": 0.032,
                    "Agricultural": 0.022
                },
                "Pasco": {
                    "Residential": 0.038,
                    "Commercial": 0.028,
                    "Agricultural": 0.018
                },
                "West Richland": {
                    "Residential": 0.048,
                    "Commercial": 0.038,
                    "Agricultural": 0.028
                },
                "Prosser": {
                    "Residential": 0.032,
                    "Commercial": 0.022,
                    "Agricultural": 0.015
                },
                "default": {
                    "Residential": 0.040,
                    "Commercial": 0.030,
                    "Agricultural": 0.020
                }
            }
            
            # Get growth rate for this property
            city_rates = growth_rates.get(city, growth_rates["default"])
            annual_growth_rate = city_rates.get(property_type, city_rates["Residential"])
            
            # Calculate historical values (past values)
            current_year = datetime.now().year
            trend_data = []
            
            # Generate past values using the growth rate in reverse
            for i in range(years - 1, -1, -1):
                year = current_year - i
                discount_factor = 1 / ((1 + annual_growth_rate) ** i)
                past_value = current_value * discount_factor
                
                trend_data.append({
                    "year": year,
                    "value": round(past_value, 2),
                    "growth_rate": round(annual_growth_rate * 100, 2)
                })
            
            # Generate future projections
            for i in range(1, years + 1):
                year = current_year + i
                growth_factor = (1 + annual_growth_rate) ** i
                future_value = current_value * growth_factor
                
                trend_data.append({
                    "year": year,
                    "value": round(future_value, 2),
                    "growth_rate": round(annual_growth_rate * 100, 2)
                })
            
            return trend_data
        
        except Exception as e:
            logger.error(f"Error generating trend data: {e}")
            return []
    
    def _handle_comparative_analysis_request(self, message: Message) -> None:
        """
        Handle a comparative analysis request.
        
        Args:
            message: Comparative analysis request message
        """
        try:
            # Extract request data from message payload
            payload = message.payload
            property_id = payload.get("property_id")
            comparison_property_ids = payload.get("comparison_property_ids", [])
            
            logger.info(f"Processing comparative analysis request for property {property_id} compared to {len(comparison_property_ids)} properties")
            
            # Connect to database
            from app_setup import db
            
            with db.engine.connect() as conn:
                # Query database for subject property
                property_query = """
                    SELECT p.*, a.* 
                    FROM properties p
                    JOIN accounts a ON p.account_id = a.id
                    WHERE p.id = :property_id
                """
                
                result = conn.execute(property_query, {"property_id": property_id})
                row = result.fetchone()
                
                if not row:
                    # Property not found
                    self.send_message(
                        message_type=MessageType.COMPARATIVE_ANALYSIS_RESPONSE,
                        target_agent_id=message.source_agent_id,
                        payload={
                            "success": False,
                            "error": f"Property with ID {property_id} not found",
                            "original_request": payload
                        },
                        correlation_id=message.message_id
                    )
                    return
                
                # Extract subject property details
                subject_property = dict(row._mapping)
                
                # Calculate subject property value
                subject_value = self._calculate_cost_approach(subject_property)["total_value"]
                
                # If no comparison properties specified, find some
                if not comparison_property_ids:
                    # Find similar properties
                    property_type = subject_property.get("property_type", "Residential")
                    city = subject_property.get("city", "default")
                    square_feet = subject_property.get("living_area", 0)
                    
                    # Define acceptable size range (±20%)
                    min_size = max(1, int(square_feet * 0.8))
                    max_size = int(square_feet * 1.2)
                    
                    comp_query = """
                        SELECT p.id
                        FROM properties p
                        JOIN accounts a ON p.account_id = a.id
                        WHERE a.property_type = :property_type
                        AND p.id != :property_id
                        AND a.city = :city
                        AND p.living_area BETWEEN :min_size AND :max_size
                        LIMIT 5
                    """
                    
                    result = conn.execute(
                        comp_query, 
                        {
                            "property_type": property_type,
                            "property_id": property_id,
                            "city": city,
                            "min_size": min_size,
                            "max_size": max_size
                        }
                    )
                    
                    comparison_property_ids = [row[0] for row in result]
                
                # Query database for comparison properties
                comparison_properties = []
                
                for comp_id in comparison_property_ids:
                    result = conn.execute(property_query, {"property_id": comp_id})
                    row = result.fetchone()
                    
                    if row:
                        comp_property = dict(row._mapping)
                        # Calculate value
                        comp_value = self._calculate_cost_approach(comp_property)["total_value"]
                        
                        # Add value to property data
                        comp_property["calculated_value"] = comp_value
                        
                        comparison_properties.append(comp_property)
                
                # Prepare comparison metrics
                comparison_results = self._calculate_comparison_metrics(subject_property, subject_value, comparison_properties)
                
                # Send response
                self.send_message(
                    message_type=MessageType.COMPARATIVE_ANALYSIS_RESPONSE,
                    target_agent_id=message.source_agent_id,
                    payload={
                        "success": True,
                        "property_id": property_id,
                        "subject_property": {
                            "id": subject_property.get("id"),
                            "address": subject_property.get("address"),
                            "city": subject_property.get("city"),
                            "property_type": subject_property.get("property_type"),
                            "living_area": subject_property.get("living_area"),
                            "year_built": subject_property.get("year_built"),
                            "bedrooms": subject_property.get("bedrooms"),
                            "bathrooms": subject_property.get("bathrooms"),
                            "calculated_value": subject_value
                        },
                        "comparison_properties": [
                            {
                                "id": prop.get("id"),
                                "address": prop.get("address"),
                                "city": prop.get("city"),
                                "property_type": prop.get("property_type"),
                                "living_area": prop.get("living_area"),
                                "year_built": prop.get("year_built"),
                                "bedrooms": prop.get("bedrooms"),
                                "bathrooms": prop.get("bathrooms"),
                                "calculated_value": prop.get("calculated_value")
                            }
                            for prop in comparison_properties
                        ],
                        "metrics": comparison_results,
                        "metadata": {
                            "agent_id": self.agent_id,
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    correlation_id=message.message_id
                )
                
                logger.info(f"Comparative analysis completed for property {property_id}")
        
        except Exception as e:
            logger.error(f"Error processing comparative analysis request: {e}")
            
            # Send error response
            self.send_message(
                message_type=MessageType.COMPARATIVE_ANALYSIS_RESPONSE,
                target_agent_id=message.source_agent_id,
                payload={
                    "success": False,
                    "error": str(e),
                    "original_request": payload
                },
                correlation_id=message.message_id
            )
    
    def _calculate_comparison_metrics(self, subject_property: Dict[str, Any], subject_value: float, 
                                     comparison_properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate comparison metrics between subject property and comparables.
        
        Args:
            subject_property: Subject property details
            subject_value: Calculated value of subject property
            comparison_properties: List of comparable properties with calculated values
            
        Returns:
            Dictionary with comparison metrics
        """
        try:
            if not comparison_properties:
                return {
                    "error": "No comparable properties available for comparison"
                }
            
            # Extract subject property metrics
            subject_sqft = subject_property.get("living_area", 0)
            subject_value_per_sqft = subject_value / subject_sqft if subject_sqft > 0 else 0
            
            # Calculate comparison metrics
            comp_values = [prop.get("calculated_value", 0) for prop in comparison_properties]
            comp_sizes = [prop.get("living_area", 0) for prop in comparison_properties]
            comp_values_per_sqft = [
                prop.get("calculated_value", 0) / prop.get("living_area", 1) 
                for prop in comparison_properties
                if prop.get("living_area", 0) > 0
            ]
            
            # Calculate statistics
            avg_comp_value = sum(comp_values) / len(comp_values) if comp_values else 0
            median_comp_value = sorted(comp_values)[len(comp_values) // 2] if comp_values else 0
            min_comp_value = min(comp_values) if comp_values else 0
            max_comp_value = max(comp_values) if comp_values else 0
            
            avg_comp_size = sum(comp_sizes) / len(comp_sizes) if comp_sizes else 0
            
            avg_comp_value_per_sqft = sum(comp_values_per_sqft) / len(comp_values_per_sqft) if comp_values_per_sqft else 0
            median_comp_value_per_sqft = sorted(comp_values_per_sqft)[len(comp_values_per_sqft) // 2] if comp_values_per_sqft else 0
            
            # Calculate percentiles
            percentile_rank = 0
            if comp_values:
                values_below = sum(1 for value in comp_values if value < subject_value)
                percentile_rank = (values_below / len(comp_values)) * 100
            
            # Calculate percentage differences
            pct_diff_avg = ((subject_value - avg_comp_value) / avg_comp_value) * 100 if avg_comp_value > 0 else 0
            pct_diff_median = ((subject_value - median_comp_value) / median_comp_value) * 100 if median_comp_value > 0 else 0
            pct_diff_sqft = ((subject_value_per_sqft - avg_comp_value_per_sqft) / avg_comp_value_per_sqft) * 100 if avg_comp_value_per_sqft > 0 else 0
            
            return {
                "comparison_count": len(comparison_properties),
                "subject_value": round(subject_value, 2),
                "subject_value_per_sqft": round(subject_value_per_sqft, 2),
                "average_comp_value": round(avg_comp_value, 2),
                "median_comp_value": round(median_comp_value, 2),
                "min_comp_value": round(min_comp_value, 2),
                "max_comp_value": round(max_comp_value, 2),
                "average_comp_size": round(avg_comp_size, 2),
                "average_comp_value_per_sqft": round(avg_comp_value_per_sqft, 2),
                "median_comp_value_per_sqft": round(median_comp_value_per_sqft, 2),
                "percentile_rank": round(percentile_rank, 2),
                "percent_diff_from_average": round(pct_diff_avg, 2),
                "percent_diff_from_median": round(pct_diff_median, 2),
                "percent_diff_per_sqft": round(pct_diff_sqft, 2)
            }
        
        except Exception as e:
            logger.error(f"Error calculating comparison metrics: {e}")
            return {
                "error": str(e)
            }