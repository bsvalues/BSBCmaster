"""
This module provides enhanced routes with minimalist design for the Benton County Assessor application.
"""

from flask import render_template, request, redirect, url_for, jsonify
import logging
from models import Property, Parcel, Account, PropertyImage
from sqlalchemy import func, cast, Integer, text
from sqlalchemy.exc import SQLAlchemyError
from app_setup import db

logger = logging.getLogger(__name__)

def index_minimal():
    """Render the minimalist index page."""
    return render_template('index_minimal.html')

def map_view_minimal():
    """Render the minimalist property map page."""
    try:
        return render_template('map_view_new.html', title="Property Map")
    except Exception as e:
        logger.error(f"Error rendering map view: {e}")
        return render_template('error.html', error=str(e))

def statistics_dashboard_minimal():
    """Render the minimalist statistics dashboard page."""
    try:
        # For the new version of the dashboard, we'll just send the title
        # All data is loaded via JavaScript through API endpoints
        return render_template(
            'statistics_dashboard_minimal_new.html',
            title="Property Statistics Dashboard"
        )
    except Exception as e:
        logger.error(f"Error rendering statistics dashboard: {e}")
        return render_template('error.html', error=str(e))

def statistics_redirect():
    """Redirect from /statistics to the minimalist statistics dashboard."""
    return redirect(url_for('statistics_dashboard_minimal'))

def register_minimalist_routes(app):
    """Register all minimalist design routes with the Flask application."""
    app.add_url_rule('/minimal', view_func=index_minimal)
    app.add_url_rule('/map-minimal', view_func=map_view_minimal)
    app.add_url_rule('/statistics-minimal', view_func=statistics_dashboard_minimal)
    app.add_url_rule('/statistics', view_func=statistics_redirect)
