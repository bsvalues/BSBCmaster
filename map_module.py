"""
Property Map Module for MCP Assessor Agent API

This module provides functionality to visualize property data on a map,
including GeoJSON conversion, property filtering, and statistics calculation.
"""

import json
import os
import logging
import statistics
from typing import Dict, List, Optional, Tuple, Union, Any
from sqlalchemy import text, func, desc
from sqlalchemy.exc import SQLAlchemyError
from flask import jsonify, request, current_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default map boundaries for Richland, WA area
DEFAULT_BOUNDS = {
    "north": 46.3507,
    "south": 46.2107,
    "east": -119.2087,
    "west": -119.3487
}

def get_db_connection():
    """Get a database connection from the Flask application context."""
    from main import db
    return db.session

def get_cities_list() -> List[str]:
    """
    Get a list of all cities from the accounts table.
    
    Returns:
        List[str]: List of city names
    """
    try:
        db_session = get_db_connection()
        
        # Query distinct cities from accounts table
        query = text("""
            SELECT DISTINCT property_city 
            FROM accounts 
            WHERE property_city IS NOT NULL AND property_city != ''
            ORDER BY property_city
        """)
        
        result = db_session.execute(query)
        cities = [row[0] for row in result]
        return cities
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving cities: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error retrieving cities: {str(e)}")
        return []

def get_property_data(
    data_source: str = 'accounts', 
    value_filter: str = 'all',
    city: Optional[str] = None,
    limit: int = 5000  # Limit the number of properties returned for performance
) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    """
    Get property data for mapping with filtering options.
    
    Args:
        data_source: The data source table ('accounts', 'improvements', etc.)
        value_filter: Filter properties by value range ('all', '0-100000', etc.)
        city: Filter properties by city
        limit: Maximum number of properties to return
        
    Returns:
        Tuple containing:
        - Statistics dictionary with count, average, median, min, max values
        - Map boundaries dictionary
        - List of property data dictionaries with coordinates for mapping
    """
    try:
        db_session = get_db_connection()
        
        # Build the base query depending on data source
        if data_source == 'accounts':
            base_query = """
                SELECT 
                    account_id,
                    owner_name,
                    property_address,
                    property_city,
                    assessed_value,
                    property_type,
                    longitude,
                    latitude
                FROM accounts
                WHERE 
                    latitude IS NOT NULL 
                    AND longitude IS NOT NULL
            """
        else:
            # Default to accounts if an unsupported data source is specified
            base_query = """
                SELECT 
                    account_id,
                    owner_name,
                    property_address,
                    property_city,
                    assessed_value,
                    property_type,
                    longitude,
                    latitude
                FROM accounts
                WHERE 
                    latitude IS NOT NULL 
                    AND longitude IS NOT NULL
            """
        
        # Add value filter
        if value_filter != 'all':
            if '-' in value_filter:
                min_val, max_val = value_filter.split('-')
                base_query += f" AND assessed_value >= {min_val} AND assessed_value <= {max_val}"
            elif value_filter.endswith('+'):
                min_val = value_filter.rstrip('+')
                base_query += f" AND assessed_value >= {min_val}"
        
        # Add city filter
        if city and city != 'all':
            base_query += f" AND property_city = '{city}'"
        
        # Complete the query with order and limit
        complete_query = base_query + f" ORDER BY assessed_value DESC LIMIT {limit}"
        
        # Execute the query
        result = db_session.execute(text(complete_query))
        properties = []
        
        # Extract property values for statistics calculation
        property_values = []
        
        # Process query results
        for row in result:
            # Convert SQLAlchemy Row to dictionary
            property_data = {
                'account_id': row.account_id,
                'owner_name': row.owner_name,
                'property_address': row.property_address,
                'property_city': row.property_city,
                'assessed_value': row.assessed_value,
                'property_type': row.property_type,
                'longitude': row.longitude,
                'latitude': row.latitude
            }
            properties.append(property_data)
            
            # Add property value for statistics if available
            if row.assessed_value:
                property_values.append(row.assessed_value)
        
        # Calculate statistics
        stats = calculate_property_statistics(property_values)
        
        # Calculate map boundaries based on data
        bounds = calculate_map_boundaries(properties)
        
        return stats, bounds, properties
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving property data: {str(e)}")
        return {}, DEFAULT_BOUNDS, []
    except Exception as e:
        logger.error(f"Unexpected error retrieving property data: {str(e)}")
        return {}, DEFAULT_BOUNDS, []

def get_property_images(account_id: str) -> List[Dict[str, Any]]:
    """
    Get images associated with a specific property.
    
    Args:
        account_id: The account ID to fetch images for
        
    Returns:
        List of property image dictionaries
    """
    try:
        db_session = get_db_connection()
        
        query = text("""
            SELECT 
                image_id,
                account_id,
                image_url,
                image_type,
                image_date,
                image_description
            FROM property_images
            WHERE account_id = :account_id
        """)
        
        result = db_session.execute(query, {'account_id': account_id})
        
        images = []
        for row in result:
            image_data = {
                'image_id': row.image_id,
                'account_id': row.account_id,
                'image_url': row.image_url,
                'image_type': row.image_type,
                'image_date': row.image_date.isoformat() if hasattr(row.image_date, 'isoformat') else row.image_date,
                'image_description': row.image_description
            }
            images.append(image_data)
        
        return images
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving property images: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error retrieving property images: {str(e)}")
        return []

def convert_to_geojson(properties: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert a list of property dictionaries to GeoJSON format.
    
    Args:
        properties: List of property dictionaries with latitude and longitude
        
    Returns:
        GeoJSON dictionary
    """
    features = []
    
    for prop in properties:
        # Skip properties without coordinates
        if not prop.get('latitude') or not prop.get('longitude'):
            continue
            
        # Create GeoJSON feature
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [prop['longitude'], prop['latitude']]
            },
            'properties': {
                'account_id': prop.get('account_id', ''),
                'owner_name': prop.get('owner_name', ''),
                'property_address': prop.get('property_address', ''),
                'property_city': prop.get('property_city', ''),
                'assessed_value': prop.get('assessed_value', 0),
                'property_type': prop.get('property_type', 'unknown')
            }
        }
        features.append(feature)
    
    # Create GeoJSON structure
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return geojson

def calculate_property_statistics(property_values: List[float]) -> Dict[str, Any]:
    """
    Calculate statistics for a list of property values.
    
    Args:
        property_values: List of property assessed values
        
    Returns:
        Dictionary with count, average, median, min, and max values
    """
    if not property_values:
        return {
            'count': 0,
            'average_value': 0,
            'median_value': 0,
            'min_value': 0,
            'max_value': 0
        }
    
    # Calculate statistics
    count = len(property_values)
    avg_value = sum(property_values) / count if count > 0 else 0
    
    # Sort values for median, min, max calculations
    sorted_values = sorted(property_values)
    median_value = statistics.median(sorted_values) if count > 0 else 0
    min_value = min(sorted_values) if count > 0 else 0
    max_value = max(sorted_values) if count > 0 else 0
    
    return {
        'count': count,
        'average_value': avg_value,
        'median_value': median_value,
        'min_value': min_value,
        'max_value': max_value
    }

def calculate_map_boundaries(properties: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate map boundaries based on property coordinates.
    
    Args:
        properties: List of property dictionaries with latitude and longitude
        
    Returns:
        Dictionary with north, south, east, and west boundary coordinates
    """
    if not properties:
        return DEFAULT_BOUNDS
    
    # Extract valid coordinates
    latitudes = []
    longitudes = []
    
    for prop in properties:
        if prop.get('latitude') and prop.get('longitude'):
            latitudes.append(prop['latitude'])
            longitudes.append(prop['longitude'])
    
    if not latitudes or not longitudes:
        return DEFAULT_BOUNDS
    
    # Calculate boundaries with a buffer
    buffer = 0.02  # About 2km buffer
    
    return {
        'north': max(latitudes) + buffer,
        'south': min(latitudes) - buffer,
        'east': max(longitudes) + buffer,
        'west': min(longitudes) - buffer
    }

# API endpoint handlers (to be imported in main.py)

def get_map_data():
    """Handle GET request for map data with filtering."""
    data_source = request.args.get('data_source', 'accounts')
    value_filter = request.args.get('value_filter', 'all')
    city = request.args.get('city', None)
    
    # Get property data with filters
    stats, bounds, properties = get_property_data(
        data_source=data_source,
        value_filter=value_filter,
        city=city
    )
    
    # Convert to GeoJSON for the map
    geojson = convert_to_geojson(properties)
    
    # Return JSON response
    return jsonify({
        'status': 'success',
        'data_source': data_source,
        'filters': {
            'value': value_filter,
            'city': city
        },
        'statistics': stats,
        'bounds': bounds,
        'geojson': geojson,
        'property_count': len(properties)
    })

def get_cities():
    """Handle GET request for available cities."""
    cities = get_cities_list()
    
    return jsonify({
        'status': 'success',
        'cities': cities
    })

def get_property_images_for_map():
    """Handle GET request for property images by account ID."""
    account_id = request.view_args.get('account_id')
    if not account_id:
        return jsonify({
            'status': 'error',
            'message': 'Account ID is required'
        }), 400
    
    images = get_property_images(account_id)
    
    return jsonify({
        'status': 'success',
        'account_id': account_id,
        'data': images
    })