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
from app_setup import app, db, Base
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
            "property_address": account.property_address,
            "property_city": account.property_city,
            "owner_name": account.owner_name,
            "legal_description": account.legal_description,
            "assessed_value": account.assessed_value,
            "tax_amount": account.tax_amount,
            "tax_status": account.tax_status,
        }
    }
    
    return feature

def get_map_data(limit: int = 500, use_cache: bool = True) -> Dict[str, Any]:
    """
    Get property data for the map view in GeoJSON format with enhanced filtering and visualization options.
    
    Args:
        limit: Maximum number of properties to return
        use_cache: Whether to use cached data if available
        
    Returns:
        Dictionary with GeoJSON data, statistics, and bounds
    """
    global MAP_DATA_CACHE, CACHE_TIMESTAMP
    
    # Get filter parameters from request if available
    from flask import request
    property_type = request.args.get('property_type', 'all')
    city = request.args.get('city', 'all')
    visualization_mode = request.args.get('visualization', 'markers')
    
    # Get value range filter if provided
    min_value = request.args.get('min_value', None)
    max_value = request.args.get('max_value', None)
    
    if min_value:
        try:
            min_value = float(min_value)
        except ValueError:
            min_value = None
    
    if max_value:
        try:
            max_value = float(max_value)
        except ValueError:
            max_value = None
    
    # Build cache key based on filter parameters
    cache_key = f"{property_type}_{city}_{min_value}_{max_value}_{visualization_mode}"
    
    # Check cache if enabled
    if use_cache and CACHE_TIMESTAMP and datetime.now() - CACHE_TIMESTAMP < CACHE_LIFETIME:
        if cache_key in MAP_DATA_CACHE:
            logger.info(f"Using cached map data for key: {cache_key}")
            return MAP_DATA_CACHE[cache_key]
    
    try:
        # Build query for accounts with coordinates
        query = Account.query.filter(
            Account.latitude.isnot(None),
            Account.longitude.isnot(None)
        )
        
        # Apply property type filter
        if property_type != 'all':
            query = query.filter(Account.property_type == property_type)
        
        # Apply city filter
        if city != 'all':
            query = query.filter(Account.property_city == city)
        
        # Apply value range filter
        if min_value is not None:
            query = query.filter(Account.assessed_value >= min_value)
        
        if max_value is not None:
            query = query.filter(Account.assessed_value <= max_value)
        
        # Get filtered accounts
        accounts = query.limit(limit).all()
        
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
        
        # Generate statistics for the filtered data
        stats = generate_map_statistics(features)
        
        # Create visualization-specific data
        visualization_data = {}
        
        if visualization_mode == 'heatmap':
            # Generate heatmap data
            heatmap_data = generate_heatmap_data(features)
            visualization_data['heatmap'] = heatmap_data
        elif visualization_mode == 'clusters':
            # Generate cluster data
            clusters = generate_clusters(features)
            visualization_data['clusters'] = clusters
        
        # Create response
        result = {
            "geojson": geojson,
            "bounds": bounds,
            "count": len(features),
            "statistics": stats,
            "visualization": visualization_mode,
            "visualization_data": visualization_data
        }
        
        # Update cache
        if not MAP_DATA_CACHE:
            MAP_DATA_CACHE = {}
        
        MAP_DATA_CACHE[cache_key] = result
        CACHE_TIMESTAMP = datetime.now()
        
        logger.info(f"Loaded {len(features)} properties from database and updated cache for key: {cache_key}")
        
        return result
    except Exception as e:
        logger.error(f"Error fetching map data: {str(e)}")
        # Return empty data
        return {
            "geojson": {"type": "FeatureCollection", "features": []},
            "bounds": get_property_bounds([]),
            "count": 0,
            "statistics": {},
            "error": str(e)
        }

def clear_cache() -> None:
    """Clear the map data cache."""
    global MAP_DATA_CACHE, CACHE_TIMESTAMP
    MAP_DATA_CACHE = {}
    CACHE_TIMESTAMP = None
    logger.info("Map data cache cleared")

def get_map_clusters():
    """Get property clusters for the map."""
    from flask import jsonify
    return jsonify({"clusters": []})

def get_property_types():
    """Get available property types."""
    from flask import jsonify
    
    with app.app_context():
        try:
            # Get distinct property types
            types = db.session.query(Account.property_type).filter(
                Account.property_type.isnot(None)
            ).distinct().all()
            
            return jsonify({
                "property_types": [t[0] for t in types if t[0]]
            })
        except Exception as e:
            logger.error(f"Error fetching property types: {str(e)}")
            return jsonify({
                "property_types": ["Residential", "Commercial", "Agricultural", "Industrial"]
            })

def get_cities():
    """Get available cities."""
    from flask import jsonify
    
    with app.app_context():
        try:
            # Get distinct cities
            cities = db.session.query(Account.property_city).filter(
                Account.property_city.isnot(None)
            ).distinct().all()
            
            return jsonify({
                "cities": [c[0] for c in cities if c[0]]
            })
        except Exception as e:
            logger.error(f"Error fetching cities: {str(e)}")
            # Only include cities in Benton County (Pasco is in Franklin County)
            return jsonify({
                "cities": ["Richland", "Kennewick", "West Richland", "Prosser", "Benton City"]
            })

def get_property_images_for_map(account_id):
    """Get property images for a specific account."""
    from flask import jsonify
    
    return jsonify({
        "images": []
    })

def generate_map_statistics(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate statistics for the filtered map data.
    
    Args:
        features: List of GeoJSON features with property data
        
    Returns:
        Dictionary with statistical summary
    """
    if not features:
        return {
            "count": 0,
            "property_types": {},
            "value_ranges": {},
            "cities": {}
        }
    
    # Initialize counters
    property_types = {}
    cities = {}
    value_ranges = {
        "Under $100K": 0,
        "$100K - $250K": 0,
        "$250K - $500K": 0,
        "$500K - $1M": 0,
        "Over $1M": 0
    }
    
    # Total and average values
    total_value = 0
    values = []
    
    # Process each feature
    for feature in features:
        props = feature.get("properties", {})
        
        # Property type statistics
        prop_type = props.get("property_type", "Unknown")
        if prop_type in property_types:
            property_types[prop_type] += 1
        else:
            property_types[prop_type] = 1
        
        # City statistics
        city = props.get("property_city", "Unknown")
        if city in cities:
            cities[city] += 1
        else:
            cities[city] = 1
        
        # Value statistics
        value = props.get("assessed_value", 0)
        if value:
            total_value += value
            values.append(value)
            
            # Value range categorization
            if value < 100000:
                value_ranges["Under $100K"] += 1
            elif value < 250000:
                value_ranges["$100K - $250K"] += 1
            elif value < 500000:
                value_ranges["$250K - $500K"] += 1
            elif value < 1000000:
                value_ranges["$500K - $1M"] += 1
            else:
                value_ranges["Over $1M"] += 1
    
    # Calculate median value
    median_value = 0
    if values:
        values.sort()
        mid = len(values) // 2
        if len(values) % 2 == 0:
            median_value = (values[mid-1] + values[mid]) / 2
        else:
            median_value = values[mid]
    
    # Compile statistics
    return {
        "count": len(features),
        "average_value": total_value / len(features) if features else 0,
        "median_value": median_value,
        "property_types": property_types,
        "value_ranges": value_ranges,
        "cities": cities
    }

def generate_heatmap_data(features: List[Dict[str, Any]]) -> List[List[float]]:
    """
    Generate heatmap data from property features.
    
    Args:
        features: List of GeoJSON features with property data
        
    Returns:
        List of [lat, lng, intensity] points for heatmap
    """
    if not features:
        return []
    
    heatmap_data = []
    
    # Process each feature
    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])
        
        if len(coords) >= 2:
            # Extract coordinates
            lng, lat = coords
            
            # Calculate intensity based on property value
            value = props.get("assessed_value", 0)
            
            # Normalize intensity (0-1 range)
            max_value = 1000000  # $1M reference point
            intensity = min(value / max_value, 1.0)
            
            # Add to heatmap data [lat, lng, intensity]
            heatmap_data.append([lat, lng, intensity])
    
    return heatmap_data

def generate_clusters(features: List[Dict[str, Any]], grid_size: float = 0.01) -> List[Dict[str, Any]]:
    """
    Generate clusters for property data based on geographical proximity.
    
    Args:
        features: List of GeoJSON features with property data
        grid_size: Size of the grid cells for clustering (in degrees)
        
    Returns:
        List of cluster objects
    """
    if not features:
        return []
    
    # Initialize clusters dictionary
    # Key is "lat_lng" grid cell, value is list of properties
    grid_clusters = {}
    
    # Process each feature
    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])
        
        if len(coords) >= 2:
            # Extract coordinates
            lng, lat = coords
            
            # Calculate grid cell
            lat_grid = int(lat / grid_size) * grid_size
            lng_grid = int(lng / grid_size) * grid_size
            
            # Create grid key
            grid_key = f"{lat_grid:.6f}_{lng_grid:.6f}"
            
            # Add to grid cell
            if grid_key not in grid_clusters:
                grid_clusters[grid_key] = []
            
            grid_clusters[grid_key].append({
                "id": props.get("account_id", ""),
                "lat": lat,
                "lng": lng,
                "value": props.get("assessed_value", 0),
                "property_type": props.get("property_type", "Unknown")
            })
    
    # Convert grid clusters to list
    clusters = []
    
    for grid_key, properties in grid_clusters.items():
        if len(properties) == 1:
            # Single property, no clustering needed
            continue
        
        # Calculate average position
        avg_lat = sum(prop["lat"] for prop in properties) / len(properties)
        avg_lng = sum(prop["lng"] for prop in properties) / len(properties)
        
        # Calculate total and average value
        total_value = sum(prop["value"] for prop in properties)
        avg_value = total_value / len(properties)
        
        # Count property types
        property_types = {}
        for prop in properties:
            prop_type = prop["property_type"]
            if prop_type in property_types:
                property_types[prop_type] += 1
            else:
                property_types[prop_type] = 1
        
        # Determine dominant property type
        dominant_type = max(property_types.items(), key=lambda x: x[1])[0]
        
        # Create cluster object
        cluster = {
            "position": [avg_lat, avg_lng],
            "count": len(properties),
            "average_value": avg_value,
            "total_value": total_value,
            "dominant_type": dominant_type,
            "property_types": property_types,
            "properties": properties
        }
        
        clusters.append(cluster)
    
    return clusters

def get_value_ranges():
    """Get property value ranges for filtering."""
    from flask import jsonify
    
    with app.app_context():
        try:
            # Get min and max values
            min_value = db.session.query(db.func.min(Account.assessed_value)).filter(
                Account.assessed_value.isnot(None)
            ).scalar()
            
            max_value = db.session.query(db.func.max(Account.assessed_value)).filter(
                Account.assessed_value.isnot(None)
            ).scalar()
            
            return jsonify({
                "min_value": float(min_value) if min_value else 0,
                "max_value": float(max_value) if max_value else 1000000
            })
        except Exception as e:
            logger.error(f"Error fetching value ranges: {str(e)}")
            return jsonify({
                "min_value": 0,
                "max_value": 1000000
            })