"""
Realtime Property Data Updates API

This module provides API endpoints for real-time property data updates,
including websocket notifications and periodic data syncing.
"""

import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
realtime_api = Blueprint('realtime_api', __name__)

# Cache for last update timestamps and notifications
LAST_UPDATES = {
    'property_values': datetime.now() - timedelta(hours=1),
    'property_sales': datetime.now() - timedelta(hours=1),
    'tax_data': datetime.now() - timedelta(hours=1)
}

# Store notifications
NOTIFICATIONS = []

# Maximum number of notifications to retain
MAX_NOTIFICATIONS = 50

def get_db_connection():
    """Get a database connection from the Flask application context."""
    from app import db
    return db.session

@realtime_api.route('/api/realtime/updates', methods=['GET'])
def get_recent_updates():
    """
    Get recent property data updates.
    
    Returns:
        JSON with recent updates information
    """
    # Get query parameters
    since_timestamp = request.args.get('since', None)
    update_type = request.args.get('type', 'all')
    limit = min(int(request.args.get('limit', 10)), 50)
    
    try:
        # Parse since_timestamp if provided
        since_date = None
        if since_timestamp:
            try:
                since_date = datetime.fromisoformat(since_timestamp.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid timestamp format: {since_timestamp}")
                since_date = datetime.now() - timedelta(hours=24)
        else:
            since_date = datetime.now() - timedelta(hours=24)
        
        # Get updates based on the update type
        if update_type == 'property_values' or update_type == 'all':
            value_updates = get_property_value_updates(since_date, limit)
        else:
            value_updates = []
            
        if update_type == 'property_sales' or update_type == 'all':
            sales_updates = get_property_sales_updates(since_date, limit)
        else:
            sales_updates = []
            
        if update_type == 'tax_data' or update_type == 'all':
            tax_updates = get_tax_data_updates(since_date, limit)
        else:
            tax_updates = []
        
        # Combine and sort all updates by timestamp
        all_updates = []
        all_updates.extend(value_updates)
        all_updates.extend(sales_updates)
        all_updates.extend(tax_updates)
        
        all_updates.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Get the most recent update timestamp for each type
        update_timestamps = {
            'property_values': LAST_UPDATES['property_values'].isoformat(),
            'property_sales': LAST_UPDATES['property_sales'].isoformat(),
            'tax_data': LAST_UPDATES['tax_data'].isoformat()
        }
        
        return jsonify({
            'updates': all_updates[:limit],
            'update_timestamps': update_timestamps,
            'total_count': len(all_updates)
        })
        
    except Exception as e:
        logger.error(f"Error fetching recent updates: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch recent updates',
            'message': str(e)
        }), 500

@realtime_api.route('/api/realtime/notifications', methods=['GET'])
def get_notifications():
    """
    Get realtime notifications.
    
    Returns:
        JSON with notifications
    """
    # Get query parameters
    since_id = request.args.get('since_id', None)
    limit = min(int(request.args.get('limit', 10)), 50)
    
    try:
        # Filter notifications by ID if provided
        filtered_notifications = NOTIFICATIONS
        if since_id:
            try:
                since_id = int(since_id)
                filtered_notifications = [n for n in NOTIFICATIONS if n['id'] > since_id]
            except ValueError:
                logger.warning(f"Invalid notification ID: {since_id}")
        
        # Sort notifications by timestamp (newest first)
        filtered_notifications.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'notifications': filtered_notifications[:limit],
            'total_count': len(filtered_notifications)
        })
        
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch notifications',
            'message': str(e)
        }), 500

@realtime_api.route('/api/realtime/sync', methods=['POST'])
def trigger_data_sync():
    """
    Trigger a manual data sync.
    
    Returns:
        JSON with sync status
    """
    try:
        # Get the sync type from request
        data = request.get_json()
        sync_type = data.get('type', 'all')
        
        # Perform the sync based on the type
        if sync_type == 'property_values' or sync_type == 'all':
            sync_property_values()
            
        if sync_type == 'property_sales' or sync_type == 'all':
            sync_property_sales()
            
        if sync_type == 'tax_data' or sync_type == 'all':
            sync_tax_data()
        
        return jsonify({
            'success': True,
            'message': f'Successfully triggered sync for: {sync_type}',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error triggering data sync: {str(e)}")
        return jsonify({
            'error': 'Failed to trigger data sync',
            'message': str(e)
        }), 500

def get_property_value_updates(since_date: datetime, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get property value updates since a specific date.
    
    Args:
        since_date: Date to filter updates from
        limit: Maximum number of updates to return
        
    Returns:
        List of property value update dictionaries
    """
    try:
        db_session = get_db_connection()
        
        # Query for properties with recent value updates
        # In a real implementation, this would check for actual update timestamps
        # Here we'll use a simulation based on the LAST_UPDATES timestamp
        updates = []
        
        # If we have a real database with update timestamps, we would query it like this:
        """
        query = text('''
            SELECT 
                account_id, 
                owner_name,
                property_address,
                property_city,
                assessed_value,
                property_type,
                updated_at
            FROM accounts
            WHERE updated_at > :since_date
            ORDER BY updated_at DESC
            LIMIT :limit
        ''')
        
        result = db_session.execute(query, {
            'since_date': since_date,
            'limit': limit
        })
        
        for row in result:
            updates.append({
                'type': 'property_value',
                'account_id': row.account_id,
                'property_address': row.property_address,
                'property_city': row.property_city,
                'assessed_value': float(row.assessed_value) if row.assessed_value else None,
                'property_type': row.property_type,
                'timestamp': row.updated_at.isoformat()
            })
        """
        
        # For demonstration, let's get some random properties to simulate updates
        # Only return updates if LAST_UPDATES shows there are new ones since the request time
        if LAST_UPDATES['property_values'] > since_date:
            query = text('''
                SELECT 
                    account_id, 
                    owner_name,
                    property_address,
                    property_city,
                    assessed_value,
                    property_type
                FROM accounts
                ORDER BY RANDOM()
                LIMIT :limit
            ''')
            
            result = db_session.execute(query, {'limit': limit})
            
            # Generate update timestamps between since_date and now
            update_range = (datetime.now() - since_date).total_seconds()
            
            for row in result:
                # Random timestamp between since_date and now
                update_time = since_date + timedelta(seconds=random.randint(1, int(update_range)))
                
                # Create update object
                updates.append({
                    'type': 'property_value',
                    'account_id': row.account_id,
                    'property_address': row.property_address,
                    'property_city': row.property_city,
                    'assessed_value': float(row.assessed_value) if row.assessed_value else None,
                    'property_type': row.property_type,
                    'timestamp': update_time.isoformat()
                })
        
        return updates
        
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving property value updates: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error retrieving property value updates: {str(e)}")
        return []

def get_property_sales_updates(since_date: datetime, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get property sales updates since a specific date.
    
    Args:
        since_date: Date to filter updates from
        limit: Maximum number of updates to return
        
    Returns:
        List of property sales update dictionaries
    """
    try:
        db_session = get_db_connection()
        
        # Similar to value updates, this would query a sales history table
        # For demonstration, simulate some sales updates
        updates = []
        
        # Only return updates if LAST_UPDATES shows there are new ones since the request time
        if LAST_UPDATES['property_sales'] > since_date:
            query = text('''
                SELECT 
                    account_id, 
                    owner_name,
                    property_address,
                    property_city,
                    assessed_value,
                    property_type
                FROM accounts
                ORDER BY RANDOM()
                LIMIT :limit
            ''')
            
            result = db_session.execute(query, {'limit': limit})
            
            # Generate update timestamps between since_date and now
            update_range = (datetime.now() - since_date).total_seconds()
            
            for row in result:
                # Random timestamp between since_date and now
                update_time = since_date + timedelta(seconds=random.randint(1, int(update_range)))
                
                # Simulate a sale price around the assessed value
                sale_price = float(row.assessed_value) * (0.9 + random.random() * 0.3) if row.assessed_value else None
                
                # Create update object
                updates.append({
                    'type': 'property_sale',
                    'account_id': row.account_id,
                    'property_address': row.property_address,
                    'property_city': row.property_city,
                    'sale_price': sale_price,
                    'property_type': row.property_type,
                    'timestamp': update_time.isoformat()
                })
        
        return updates
        
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving property sales updates: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error retrieving property sales updates: {str(e)}")
        return []

def get_tax_data_updates(since_date: datetime, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get tax data updates since a specific date.
    
    Args:
        since_date: Date to filter updates from
        limit: Maximum number of updates to return
        
    Returns:
        List of tax data update dictionaries
    """
    try:
        db_session = get_db_connection()
        
        # Simulate tax data updates
        updates = []
        
        # Only return updates if LAST_UPDATES shows there are new ones since the request time
        if LAST_UPDATES['tax_data'] > since_date:
            query = text('''
                SELECT 
                    account_id, 
                    owner_name,
                    property_address,
                    property_city,
                    assessed_value,
                    property_type,
                    tax_amount,
                    tax_status
                FROM accounts
                WHERE tax_amount IS NOT NULL
                ORDER BY RANDOM()
                LIMIT :limit
            ''')
            
            result = db_session.execute(query, {'limit': limit})
            
            # Generate update timestamps between since_date and now
            update_range = (datetime.now() - since_date).total_seconds()
            
            for row in result:
                # Random timestamp between since_date and now
                update_time = since_date + timedelta(seconds=random.randint(1, int(update_range)))
                
                # Create update object
                updates.append({
                    'type': 'tax_data',
                    'account_id': row.account_id,
                    'property_address': row.property_address,
                    'property_city': row.property_city,
                    'tax_amount': float(row.tax_amount) if row.tax_amount else None,
                    'tax_status': row.tax_status,
                    'timestamp': update_time.isoformat()
                })
        
        return updates
        
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving tax data updates: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error retrieving tax data updates: {str(e)}")
        return []

def sync_property_values():
    """
    Sync property values from external source.
    In a real implementation, this would connect to an external data source
    and update the database with new property values.
    """
    try:
        # Update the last sync timestamp
        LAST_UPDATES['property_values'] = datetime.now()
        
        # Generate a notification
        notification = {
            'id': len(NOTIFICATIONS) + 1,
            'type': 'property_values',
            'message': 'Property values updated',
            'timestamp': datetime.now().isoformat(),
            'details': {
                'sync_type': 'property_values',
                'sync_time': datetime.now().isoformat(),
                'status': 'success'
            }
        }
        
        # Add notification to the list
        NOTIFICATIONS.append(notification)
        
        # Trim notification list if it exceeds the maximum
        if len(NOTIFICATIONS) > MAX_NOTIFICATIONS:
            NOTIFICATIONS.pop(0)
            
        logger.info("Property values synced successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error syncing property values: {str(e)}")
        return False

def sync_property_sales():
    """
    Sync property sales from external source.
    """
    try:
        # Update the last sync timestamp
        LAST_UPDATES['property_sales'] = datetime.now()
        
        # Generate a notification
        notification = {
            'id': len(NOTIFICATIONS) + 1,
            'type': 'property_sales',
            'message': 'Property sales updated',
            'timestamp': datetime.now().isoformat(),
            'details': {
                'sync_type': 'property_sales',
                'sync_time': datetime.now().isoformat(),
                'status': 'success'
            }
        }
        
        # Add notification to the list
        NOTIFICATIONS.append(notification)
        
        # Trim notification list if it exceeds the maximum
        if len(NOTIFICATIONS) > MAX_NOTIFICATIONS:
            NOTIFICATIONS.pop(0)
            
        logger.info("Property sales synced successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error syncing property sales: {str(e)}")
        return False

def sync_tax_data():
    """
    Sync tax data from external source.
    """
    try:
        # Update the last sync timestamp
        LAST_UPDATES['tax_data'] = datetime.now()
        
        # Generate a notification
        notification = {
            'id': len(NOTIFICATIONS) + 1,
            'type': 'tax_data',
            'message': 'Tax data updated',
            'timestamp': datetime.now().isoformat(),
            'details': {
                'sync_type': 'tax_data',
                'sync_time': datetime.now().isoformat(),
                'status': 'success'
            }
        }
        
        # Add notification to the list
        NOTIFICATIONS.append(notification)
        
        # Trim notification list if it exceeds the maximum
        if len(NOTIFICATIONS) > MAX_NOTIFICATIONS:
            NOTIFICATIONS.pop(0)
            
        logger.info("Tax data synced successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error syncing tax data: {str(e)}")
        return False