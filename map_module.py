"""
Property Map Module for MCP Assessor Agent API

This module provides advanced functionality to visualize property data on a map,
including GeoJSON conversion, property filtering, clustering, and statistical analysis.
"""

import json
import os
import logging
import statistics
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from sqlalchemy import text, func, desc, or_, and_
from sqlalchemy.exc import SQLAlchemyError
from flask import jsonify, request, current_app, Response

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

# Cache for property data with 30-minute expiration
PROPERTY_CACHE = {
    'data': None,
    'timestamp': None,
    'expiration': 30 * 60  # 30 minutes in seconds
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
    property_types: Optional[List[str]] = None,
    use_cache: bool = True,
    limit: int = 10000  # Increased limit for better data coverage
) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    """
    Get property data for mapping with advanced filtering options.
    
    Args:
        data_source: The data source table ('accounts', 'improvements', etc.)
        value_filter: Filter properties by value range ('all', '0-100000', etc.)
        city: Filter properties by city
        property_types: List of property types to include (e.g. ['Residential', 'Commercial'])
        use_cache: Whether to use cached data if available
        limit: Maximum number of properties to return
        
    Returns:
        Tuple containing:
        - Statistics dictionary with count, average, median, min, max values
        - Map boundaries dictionary
        - List of property data dictionaries with coordinates for mapping
    """
    # Check cache first if enabled
    if use_cache and PROPERTY_CACHE['data'] is not None and PROPERTY_CACHE['timestamp'] is not None:
        current_time = datetime.now()
        cache_age = (current_time - PROPERTY_CACHE['timestamp']).total_seconds()
        
        if cache_age < PROPERTY_CACHE['expiration']:
            logger.info(f"Using cached property data (age: {cache_age:.1f} seconds)")
            
            # Apply filters to cached data for improved performance
            cached_stats, cached_bounds, cached_properties = PROPERTY_CACHE['data']
            
            # Filter properties based on criteria
            filtered_properties = []
            filtered_values = []
            
            for prop in cached_properties:
                # Skip properties with missing required data
                if not prop.get('latitude') or not prop.get('longitude'):
                    continue
                
                # Apply value filter
                if value_filter != 'all':
                    if '-' in value_filter:
                        min_val, max_val = map(float, value_filter.split('-'))
                        if not prop.get('assessed_value') or prop['assessed_value'] < min_val or prop['assessed_value'] > max_val:
                            continue
                    elif value_filter.endswith('+'):
                        min_val = float(value_filter.rstrip('+'))
                        if not prop.get('assessed_value') or prop['assessed_value'] < min_val:
                            continue
                
                # Apply city filter
                if city and city != 'all' and prop.get('property_city') != city:
                    continue
                
                # Apply property type filter
                if property_types and prop.get('property_type') not in property_types:
                    continue
                
                filtered_properties.append(prop)
                if prop.get('assessed_value'):
                    filtered_values.append(float(prop['assessed_value']))
            
            # Recalculate statistics and boundaries for filtered data
            filtered_stats = calculate_property_statistics(filtered_values)
            filtered_bounds = calculate_map_boundaries(filtered_properties)
            
            return filtered_stats, filtered_bounds, filtered_properties
    
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
                    latitude,
                    legal_description,
                    tax_amount,
                    tax_status
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
                    latitude,
                    legal_description,
                    tax_amount,
                    tax_status
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
        
        # Add property type filter
        if property_types and len(property_types) > 0:
            type_conditions = ", ".join([f"'{t}'" for t in property_types])
            base_query += f" AND property_type IN ({type_conditions})"
        
        # Complete the query with order and limit
        complete_query = base_query + f" ORDER BY assessed_value DESC LIMIT {limit}"
        
        # Execute the query
        result = db_session.execute(text(complete_query))
        properties = []
        
        # Extract property values for statistics calculation
        property_values = []
        
        # Process query results
        for row in result:
            # Convert SQLAlchemy Row to dictionary with float conversion for decimal values
            property_data = {
                'account_id': row.account_id,
                'owner_name': row.owner_name,
                'property_address': row.property_address,
                'property_city': row.property_city,
                'assessed_value': float(row.assessed_value) if row.assessed_value else None,
                'property_type': row.property_type,
                'longitude': float(row.longitude) if row.longitude else None,
                'latitude': float(row.latitude) if row.latitude else None,
                'legal_description': row.legal_description,
                'tax_amount': float(row.tax_amount) if row.tax_amount else None,
                'tax_status': row.tax_status
            }
            properties.append(property_data)
            
            # Add property value for statistics if available
            if row.assessed_value:
                property_values.append(float(row.assessed_value))
        
        # Calculate statistics
        stats = calculate_property_statistics(property_values)
        
        # Calculate map boundaries based on data
        bounds = calculate_map_boundaries(properties)
        
        # Update cache with new data
        PROPERTY_CACHE['data'] = (stats, bounds, properties)
        PROPERTY_CACHE['timestamp'] = datetime.now()
        
        logger.info(f"Loaded {len(properties)} properties from database and updated cache")
        
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
                id,
                account_id,
                image_url,
                image_path,
                image_type,
                image_date,
                file_format
            FROM property_images
            WHERE account_id = :account_id
        """)
        
        result = db_session.execute(query, {'account_id': account_id})
        
        images = []
        for row in result:
            image_data = {
                'image_id': row.id,
                'account_id': row.account_id,
                'image_url': row.image_url,
                'image_path': row.image_path,
                'image_type': row.image_type,
                'image_date': row.image_date.isoformat() if hasattr(row.image_date, 'isoformat') else row.image_date,
                'file_format': row.file_format
            }
            images.append(image_data)
        
        return images
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving property images: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error retrieving property images: {str(e)}")
        return []

def convert_to_geojson(properties: List[Dict[str, Any]], include_extended_data: bool = True) -> Dict[str, Any]:
    """
    Convert a list of property dictionaries to GeoJSON format with enhanced property data.
    
    Args:
        properties: List of property dictionaries with latitude and longitude
        include_extended_data: Whether to include extended property data
        
    Returns:
        GeoJSON dictionary
    """
    features = []
    
    for prop in properties:
        # Skip properties without coordinates
        if not prop.get('latitude') or not prop.get('longitude'):
            continue
            
        # Create base property data
        property_data = {
            'account_id': prop.get('account_id', ''),
            'owner_name': prop.get('owner_name', ''),
            'property_address': prop.get('property_address', ''),
            'property_city': prop.get('property_city', ''),
            'assessed_value': prop.get('assessed_value', 0),
            'property_type': prop.get('property_type', 'unknown')
        }
        
        # Add extended data if requested
        if include_extended_data:
            additional_data = {
                'legal_description': prop.get('legal_description', ''),
                'tax_amount': prop.get('tax_amount', 0),
                'tax_status': prop.get('tax_status', '')
            }
            property_data.update(additional_data)
        
        # Create GeoJSON feature
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [prop['longitude'], prop['latitude']]
            },
            'properties': property_data
        }
        features.append(feature)
    
    # Create GeoJSON structure
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return geojson

def generate_clusters(properties: List[Dict[str, Any]], grid_size: float = 0.01) -> Dict[str, Any]:
    """
    Generate property clusters based on geographic proximity.
    
    Args:
        properties: List of property dictionaries with latitude and longitude
        grid_size: Size of the grid cell for clustering (in degrees)
        
    Returns:
        GeoJSON structure with clusters
    """
    # Group properties by grid cell
    grid_cells = {}
    
    for prop in properties:
        # Skip properties without coordinates
        if not prop.get('latitude') or not prop.get('longitude'):
            continue
        
        # Calculate grid cell
        lat_cell = int(prop['latitude'] / grid_size)
        lng_cell = int(prop['longitude'] / grid_size)
        cell_key = f"{lat_cell}_{lng_cell}"
        
        # Add property to grid cell
        if cell_key not in grid_cells:
            grid_cells[cell_key] = []
        grid_cells[cell_key].append(prop)
    
    # Create cluster features
    features = []
    
    for cell_key, cell_properties in grid_cells.items():
        # Skip cells with no properties
        if not cell_properties:
            continue
        
        # Calculate cluster center
        total_lat = sum(prop['latitude'] for prop in cell_properties)
        total_lng = sum(prop['longitude'] for prop in cell_properties)
        center_lat = total_lat / len(cell_properties)
        center_lng = total_lng / len(cell_properties)
        
        # Calculate value statistics
        values = [prop.get('assessed_value', 0) for prop in cell_properties if prop.get('assessed_value')]
        avg_value = sum(values) / len(values) if values else 0
        
        # Count property types
        property_types = {}
        for prop in cell_properties:
            prop_type = prop.get('property_type', 'unknown')
            property_types[prop_type] = property_types.get(prop_type, 0) + 1
        
        # Find dominant property type
        dominant_type = max(property_types.items(), key=lambda x: x[1])[0] if property_types else 'unknown'
        
        # Create cluster feature
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [center_lng, center_lat]
            },
            'properties': {
                'point_count': len(cell_properties),
                'point_count_abbreviated': f"{len(cell_properties)}",
                'avg_value': avg_value,
                'dominant_type': dominant_type,
                'property_types': property_types
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
    
    # Convert to float to avoid decimal + float issues
    max_lat = float(max(latitudes))
    min_lat = float(min(latitudes))
    max_lng = float(max(longitudes))
    min_lng = float(min(longitudes))
    
    return {
        'north': max_lat + buffer,
        'south': min_lat - buffer,
        'east': max_lng + buffer,
        'west': min_lng - buffer
    }

# API endpoint handlers (to be imported in main.py)

def get_map_data():
    """Handle GET request for map data with filtering."""
    data_source = request.args.get('data_source', 'accounts')
    value_filter = request.args.get('value_filter', 'all')
    city = request.args.get('city', None)
    clustering = request.args.get('clustering', 'false').lower() == 'true'
    grid_size = float(request.args.get('grid_size', '0.01'))
    
    # Get property types if provided
    property_types_param = request.args.get('property_types', None)
    property_types = property_types_param.split(',') if property_types_param else None
    
    # Get property data with filters
    stats, bounds, properties = get_property_data(
        data_source=data_source,
        value_filter=value_filter,
        city=city,
        property_types=property_types
    )
    
    # Generate response based on clustering option
    if clustering and len(properties) > 20:
        # Generate clusters for better performance with large datasets
        geojson = generate_clusters(properties, grid_size)
        response_type = 'clusters'
    else:
        # Convert to regular GeoJSON for small datasets
        geojson = convert_to_geojson(properties)
        response_type = 'points'
    
    # Return JSON response
    return jsonify({
        'status': 'success',
        'data_source': data_source,
        'response_type': response_type,
        'filters': {
            'value': value_filter,
            'city': city,
            'property_types': property_types
        },
        'statistics': stats,
        'bounds': bounds,
        'geojson': geojson,
        'property_count': len(properties)
    })

def get_map_clusters():
    """Handle GET request for property clusters."""
    data_source = request.args.get('data_source', 'accounts')
    value_filter = request.args.get('value_filter', 'all')
    city = request.args.get('city', None)
    grid_size = float(request.args.get('grid_size', '0.01'))
    
    # Get property types if provided
    property_types_param = request.args.get('property_types', None)
    property_types = property_types_param.split(',') if property_types_param else None
    
    # Get property data with filters
    stats, bounds, properties = get_property_data(
        data_source=data_source,
        value_filter=value_filter,
        city=city,
        property_types=property_types
    )
    
    # Generate clusters
    clusters = generate_clusters(properties, grid_size)
    
    # Return JSON response
    return jsonify({
        'status': 'success',
        'data_source': data_source,
        'filters': {
            'value': value_filter,
            'city': city,
            'property_types': property_types
        },
        'statistics': stats,
        'bounds': bounds,
        'clusters': clusters,
        'property_count': len(properties)
    })

def get_property_types():
    """Handle GET request for available property types."""
    try:
        db_session = get_db_connection()
        
        # Query distinct property types
        query = text("""
            SELECT DISTINCT property_type 
            FROM accounts 
            WHERE property_type IS NOT NULL AND property_type != ''
            ORDER BY property_type
        """)
        
        result = db_session.execute(query)
        property_types = [row[0] for row in result]
        
        return jsonify({
            'status': 'success',
            'property_types': property_types
        })
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving property types: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving property types',
            'property_types': []
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error retrieving property types: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving property types',
            'property_types': []
        }), 500

def get_cities():
    """Handle GET request for available cities."""
    cities = get_cities_list()
    
    return jsonify({
        'status': 'success',
        'cities': cities
    })

def get_property_images_for_map(account_id=None):
    """Handle GET request for property images by account ID."""
    if not account_id:
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

def get_value_ranges():
    """Handle GET request for property value ranges."""
    try:
        db_session = get_db_connection()
        
        # Query min and max values
        query = text("""
            SELECT 
                MIN(assessed_value) as min_value, 
                MAX(assessed_value) as max_value 
            FROM accounts 
            WHERE assessed_value IS NOT NULL
        """)
        
        result = db_session.execute(query).fetchone()
        
        if result and result.min_value is not None and result.max_value is not None:
            min_value = float(result.min_value)
            max_value = float(result.max_value)
            
            # Create value ranges
            range_count = 5
            step = (max_value - min_value) / range_count
            
            ranges = []
            for i in range(range_count):
                range_min = min_value + i * step
                range_max = min_value + (i + 1) * step
                
                # Format the range
                if i == 0:
                    ranges.append({
                        'label': f'Under ${int(range_max):,}',
                        'value': f'0-{int(range_max)}'
                    })
                elif i == range_count - 1:
                    ranges.append({
                        'label': f'Over ${int(range_min):,}',
                        'value': f'{int(range_min)}+'
                    })
                else:
                    ranges.append({
                        'label': f'${int(range_min):,} - ${int(range_max):,}',
                        'value': f'{int(range_min)}-{int(range_max)}'
                    })
            
            return jsonify({
                'status': 'success',
                'value_ranges': ranges,
                'min_value': min_value,
                'max_value': max_value
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No property values found',
                'value_ranges': []
            }), 404
            
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving value ranges: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving value ranges',
            'value_ranges': []
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error retrieving value ranges: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving value ranges',
            'value_ranges': []
        }), 500