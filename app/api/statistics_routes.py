"""
Statistics API Routes

This module provides API endpoints for property statistics data.
"""

import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from flask import Blueprint, jsonify, request
from app_setup import app, db
from models import Account, PropertyImage, Property, Parcel
from property_statistics import generate_all_statistics
from sqlalchemy import func

# Create blueprint
statistics_api = Blueprint('statistics_api', __name__)

@statistics_api.route('/api/statistics', methods=['GET'])
def get_statistics():
    """
    Get property statistics with optional filtering.
    
    Query parameters:
    - property_type: Filter by property type
    - city: Filter by city
    - year: Filter by assessment year
    
    Returns:
        JSON response with property statistics
    """
    try:
        # Generate statistics
        statistics = generate_all_statistics()
        
        if not statistics:
            return jsonify({
                'status': 'error',
                'message': 'No statistics available'
            }), 404
        
        return jsonify({
            'status': 'success',
            'statistics': statistics
        })
        
    except Exception as e:
        logger.error(f"Error generating property statistics: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to generate statistics: {str(e)}"
        }), 500

@statistics_api.route('/api/property-types', methods=['GET'])
def get_property_types():
    """
    Get list of available property types.
    
    Returns:
        JSON response with property types
    """
    try:
        with app.app_context():
            # Query distinct property types
            property_types = db.session.query(Account.property_type).filter(
                Account.property_type.isnot(None)
            ).distinct().all()
            
            # Extract values from result tuples
            property_types = [pt[0] for pt in property_types if pt[0]]
            
            return jsonify({
                'status': 'success',
                'property_types': property_types
            })
            
    except Exception as e:
        logger.error(f"Error fetching property types: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to fetch property types: {str(e)}"
        }), 500

@statistics_api.route('/api/cities', methods=['GET'])
def get_cities():
    """
    Get list of available cities.
    
    Returns:
        JSON response with cities
    """
    try:
        with app.app_context():
            # Query distinct cities
            cities = db.session.query(Account.property_city).filter(
                Account.property_city.isnot(None)
            ).distinct().all()
            
            # Extract values from result tuples
            cities = [c[0] for c in cities if c[0]]
            
            return jsonify({
                'status': 'success',
                'cities': cities
            })
            
    except Exception as e:
        logger.error(f"Error fetching cities: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to fetch cities: {str(e)}"
        }), 500

@statistics_api.route('/api/assessment-years', methods=['GET'])
def get_assessment_years():
    """
    Get list of available assessment years.
    
    Returns:
        JSON response with assessment years
    """
    try:
        with app.app_context():
            # Query distinct assessment years
            years = db.session.query(Account.assessment_year).filter(
                Account.assessment_year.isnot(None)
            ).distinct().all()
            
            # Extract values from result tuples
            years = [y[0] for y in years if y[0]]
            
            return jsonify({
                'status': 'success',
                'years': years
            })
            
    except Exception as e:
        logger.error(f"Error fetching assessment years: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to fetch assessment years: {str(e)}"
        }), 500

@statistics_api.route('/api/property-value-summary', methods=['GET'])
def get_property_value_summary():
    """
    Get summary statistics about property values.
    
    Returns:
        JSON response with property value summary
    """
    try:
        with app.app_context():
            # Get average, min, max values
            summary = db.session.query(
                func.avg(Account.assessed_value).label('avg_value'),
                func.min(Account.assessed_value).label('min_value'),
                func.max(Account.assessed_value).label('max_value'),
                func.count(Account.id).label('count')
            ).filter(Account.assessed_value.isnot(None)).first()
            
            # Format result
            result = {
                'avg_value': float(summary.avg_value) if summary.avg_value else 0,
                'min_value': float(summary.min_value) if summary.min_value else 0,
                'max_value': float(summary.max_value) if summary.max_value else 0,
                'count': summary.count or 0
            }
            
            return jsonify({
                'status': 'success',
                'summary': result
            })
            
    except Exception as e:
        logger.error(f"Error fetching property value summary: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to fetch property value summary: {str(e)}"
        }), 500