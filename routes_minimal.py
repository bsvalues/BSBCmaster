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
        # Get property count
        property_count = db.session.query(func.count(Property.id)).scalar() or 0
        
        # Get average property value
        avg_value = db.session.query(func.avg(Account.assessed_value)).scalar() or 0
        
        # Get cities
        cities = db.session.query(Account.property_city).filter(Account.property_city != None).distinct().all()
        cities = [city[0] for city in cities if city[0]]
        
        # Get property types
        property_types = db.session.query(Account.property_type).filter(Account.property_type != None).distinct().all()
        property_types = [prop_type[0] for prop_type in property_types if prop_type[0]]
        
        # Get sample properties for table
        properties = db.session.query(Property, Account, Parcel)\
            .join(Parcel, Property.parcel_id == Parcel.id)\
            .outerjoin(Account, Parcel.parcel_id == Account.parcel_id)\
            .limit(20).all()
        
        property_list = []
        for prop, account, parcel in properties:
            property_list.append({
                'parcel_id': parcel.parcel_id if parcel else '',
                'address': parcel.address if parcel else '',
                'city': account.property_city if account else '',
                'property_type': account.property_type if account else '',
                'assessed_value': account.assessed_value if account else 0
            })
            
        return render_template(
            'statistics_dashboard_minimal.html',
            property_count=property_count,
            avg_value=f"{int(avg_value):,d}",
            city_count=len(cities),
            property_type_count=len(property_types),
            cities=cities,
            property_types=property_types,
            properties=property_list
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
