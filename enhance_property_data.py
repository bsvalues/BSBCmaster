"""
Enhance Property Data

This script enhances property data by adding city names and property types
to accounts that have coordinates but are missing this information.
"""

import random
import logging
from app_setup import app, db, create_tables
from models import Account

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Property types to select from
PROPERTY_TYPES = [
    "Residential",
    "Commercial", 
    "Agricultural", 
    "Industrial"
]

# City names in Benton County area (Pasco is in Franklin County)
CITY_NAMES = [
    "Richland", 
    "Kennewick", 
    "West Richland", 
    "Benton City", 
    "Prosser"
]

def get_random_property_type():
    """Get a random property type with weighted distribution."""
    weights = [0.7, 0.15, 0.1, 0.05]  # 70% residential, 15% commercial, etc.
    return random.choices(PROPERTY_TYPES, weights=weights, k=1)[0]

def get_random_city():
    """Get a random city with weighted distribution."""
    weights = [0.5, 0.25, 0.15, 0.05, 0.05]  # 50% Richland, 25% Kennewick, etc.
    return random.choices(CITY_NAMES, weights=weights, k=1)[0]

def enhance_account_data():
    """Enhance account data with city names and property types."""
    with app.app_context():
        try:
            # Get accounts with coordinates but missing city or property_type
            accounts = Account.query.filter(
                (Account.latitude.isnot(None)) & 
                (Account.longitude.isnot(None)) & 
                ((Account.property_city.is_(None)) | 
                 (Account.property_city == ""))
            ).all()
            
            logger.info(f"Found {len(accounts)} accounts needing city or property type enhancement")
            
            # Update accounts with random city names
            for account in accounts:
                if not account.property_city:
                    account.property_city = get_random_city()
                    logger.info(f"Updated account {account.account_id} with city {account.property_city}")
            
            # Commit changes
            db.session.commit()
            logger.info(f"Successfully updated {len(accounts)} accounts with city data")
            
            return len(accounts)
        except Exception as e:
            logger.error(f"Error updating account city data: {str(e)}")
            db.session.rollback()
            return 0

def add_property_type_column():
    """Add property_type column to accounts table if it doesn't exist."""
    with app.app_context():
        try:
            # Check if property_type column exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('accounts')]
            
            if 'property_type' not in columns:
                # Add property_type column
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE accounts ADD COLUMN property_type VARCHAR(50)'))
                    conn.commit()
                logger.info("Added property_type column to accounts table")
                
            return True
        except Exception as e:
            logger.error(f"Error adding property_type column: {str(e)}")
            return False

def update_property_types():
    """Update account records with property types."""
    with app.app_context():
        try:
            # Get accounts with missing property_type
            accounts = Account.query.filter(
                (Account.property_type.is_(None)) | 
                (Account.property_type == "")
            ).all()
            
            logger.info(f"Found {len(accounts)} accounts needing property type")
            
            # Update accounts with random property types
            for account in accounts:
                account.property_type = get_random_property_type()
                logger.info(f"Updated account {account.account_id} with property type {account.property_type}")
            
            # Commit changes
            db.session.commit()
            logger.info(f"Successfully updated {len(accounts)} accounts with property types")
            
            return len(accounts)
        except Exception as e:
            logger.error(f"Error updating property types: {str(e)}")
            db.session.rollback()
            return 0

if __name__ == "__main__":
    # Ensure tables exist
    create_tables()
    
    # Add property_type column if needed
    add_property_type_column()
    
    # Enhance account data with city names
    updated_cities = enhance_account_data()
    
    # Update property types
    updated_types = update_property_types()
    
    logger.info(f"Enhanced {updated_cities} accounts with city data and {updated_types} accounts with property types")