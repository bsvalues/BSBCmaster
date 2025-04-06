"""
Property Statistics API

This module provides API endpoints for property statistics and analytics.
"""

import logging
import sys
import os

# Add parent directory to path to import property_statistics
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from flask import jsonify
from property_statistics import generate_all_statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_property_statistics():
    """
    API endpoint to get comprehensive property statistics.
    
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