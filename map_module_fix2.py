"""
Map Module

This module provides functionality for the property map view in the MCP Assessor Agent API.
It handles generating GeoJSON data for the map and caching the results.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from flask import jsonify
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base  # Import the correct base

# Use relative import to work with both main.py and run_app.py entry points
from app_setup import engine, Base
from models import Account

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define cache
MAP_DATA_CACHE: Dict[str, Any] = {}
CACHE_TIMESTAMP: Optional[datetime] = None
CACHE_LIFETIME = timedelta(minutes=10)

def get_property_bounds(properties: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate the bounding box for a set of properties.
    
    Args:
        properties: List of property dictionaries with latitude and longitude
        
    Returns:
        Dictionary with north, south, east, west coordinates
    """
    if not properties:
        # Default to Benton County area if no properties
        return {
            "north": 46.4,
            "south": 46.1,
            "east": -119.1,
            "west": -119.5
        }
    
    # Initialize with first property
    first_valid = next((p for p in properties if 'coordinates' in p.get('geometry', {})), None)
    
    if not first_valid:
        # Default bounds if no valid properties
        return {
            "north": 46.4,
            "south": 46.1,
            "east": -119.1,
            "west": -119.5
        }
    
    # Start with coordinates from the first valid property
    lng, lat = first_valid['geometry']['coordinates']
    
    bounds = {
        "north": lat,
        "south": lat,
        "east": lng,
        "west": lng
    }
    
    # Update bounds with remaining properties
    for prop in properties:
        if 'geometry' in prop and 'coordinates' in prop['geometry']:
            lng, lat = prop['geometry']['coordinates']
            
            bounds["north"] = max(bounds["north"], lat)
            bounds["south"] = min(bounds["south"], lat)
            bounds["east"] = max(bounds["east"], lng)
            bounds["west"] = min(bounds["west"], lng)
    
    # Add some padding (5%)
    lat_padding = (bounds["north"] - bounds["south"]) * 0.05
    lng_padding = (bounds["east"] - bounds["west"]) * 0.05
    
    bounds["north"] += lat_padding
    bounds["south"] -= lat_padding
    bounds["east"] += lng_padding
    bounds["west"] -= lng_padding
    
    return bounds

def property_to_geojson(account: Account) -> Dict[str, Any]:
    """
    Convert an Account object to a GeoJSON feature.
    
    Args:
        account: Account database object
        
    Returns:
        GeoJSON feature dictionary
    """
    # Check if account has lat/lon
    if not account.latitude or not account.longitude:
        return None
    
    # Create GeoJSON feature
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [account.longitude, account.latitude]
        },
        "properties": {
            "account_id": account.id,
            "property_type": account.property_type,
            "property_address": account.address,
            "property_city": account.city,
            "owner_name": account.owner_name,
            "legal_description": account.legal_description,
            "assessed_value": account.assessed_value,
            "tax_amount": account.tax_amount,
            "tax_status": account.tax_status,
        }
    }
    
    return feature

def get_map_data(limit: int = 100, use_cache: bool = True) -> Dict[str, Any]:
    """
    Get property data for the map view in GeoJSON format.
    
    Args:
        limit: Maximum number of properties to return
        use_cache: Whether to use cached data if available
        
    Returns:
        Dictionary with GeoJSON data and bounds
    """
    global MAP_DATA_CACHE, CACHE_TIMESTAMP
    
    # Check cache if enabled
    if use_cache and CACHE_TIMESTAMP and datetime.now() - CACHE_TIMESTAMP < CACHE_LIFETIME:
        logger.info("Using cached map data")
        return MAP_DATA_CACHE
    
    try:
        # Query database for accounts with coordinates
        accounts = Account.query.filter(
            Account.latitude.isnot(None),
            Account.longitude.isnot(None)
        ).limit(limit).all()
        
        # Create GeoJSON features
        features = []
        for account in accounts:
            feature = property_to_geojson(account)
            if feature:
                features.append(feature)
        
        # Create GeoJSON object
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Calculate bounds
        bounds = get_property_bounds(features)
        
        # Create response
        result = {
            "geojson": geojson,
            "bounds": bounds,
            "count": len(features)
        }
        
        # Update cache
        MAP_DATA_CACHE = result
        CACHE_TIMESTAMP = datetime.now()
        
        logger.info(f"Loaded {len(features)} properties from database and updated cache")
        
        return result
    except Exception as e:
        logger.error(f"Error fetching map data: {str(e)}")
        # Return empty data
        return {
            "geojson": {"type": "FeatureCollection", "features": []},
            "bounds": get_property_bounds([]),
            "count": 0,
            "error": str(e)
        }

def clear_cache() -> None:
    """Clear the map data cache."""
    global MAP_DATA_CACHE, CACHE_TIMESTAMP
    MAP_DATA_CACHE = {}
    CACHE_TIMESTAMP = None
    logger.info("Map data cache cleared")