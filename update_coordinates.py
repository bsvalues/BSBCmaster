"""
Update Coordinates for Property Accounts

This script adds random coordinates to existing account records
to enable map visualization of properties in the Richland, WA area.
"""

import random
import logging
from app_setup import app, db, create_tables
from models import Account, Parcel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Geographic boundaries for Richland, WA area
RICHLAND_BOUNDS = {
    "north": 46.3507,
    "south": 46.2107,
    "east": -119.2087,
    "west": -119.3487
}

def generate_coordinates():
    """Generate random coordinates within the Richland area."""
    latitude = random.uniform(RICHLAND_BOUNDS["south"], RICHLAND_BOUNDS["north"])
    longitude = random.uniform(RICHLAND_BOUNDS["west"], RICHLAND_BOUNDS["east"])
    return latitude, longitude

def update_account_coordinates():
    """Update accounts with random coordinates for map visualization."""
    with app.app_context():
        try:
            # Get accounts without coordinates
            accounts = Account.query.filter(
                (Account.latitude.is_(None)) | 
                (Account.longitude.is_(None))
            ).all()
            
            logger.info(f"Found {len(accounts)} accounts needing coordinates")
            
            # Update accounts with coordinates
            for account in accounts:
                latitude, longitude = generate_coordinates()
                account.latitude = latitude
                account.longitude = longitude
                logger.info(f"Updated account {account.account_id} with coordinates ({latitude}, {longitude})")
            
            # Commit changes
            db.session.commit()
            logger.info(f"Successfully updated {len(accounts)} accounts with coordinates")
            
            return len(accounts)
        except Exception as e:
            logger.error(f"Error updating account coordinates: {str(e)}")
            db.session.rollback()
            return 0

def update_parcel_coordinates():
    """Update parcels with random coordinates for map visualization."""
    with app.app_context():
        try:
            # Get parcels without coordinates
            parcels = Parcel.query.filter(
                (Parcel.latitude.is_(None)) | 
                (Parcel.longitude.is_(None))
            ).all()
            
            logger.info(f"Found {len(parcels)} parcels needing coordinates")
            
            # Update parcels with coordinates
            for parcel in parcels:
                latitude, longitude = generate_coordinates()
                parcel.latitude = latitude
                parcel.longitude = longitude
                logger.info(f"Updated parcel {parcel.parcel_id} with coordinates ({latitude}, {longitude})")
            
            # Commit changes
            db.session.commit()
            logger.info(f"Successfully updated {len(parcels)} parcels with coordinates")
            
            return len(parcels)
        except Exception as e:
            logger.error(f"Error updating parcel coordinates: {str(e)}")
            db.session.rollback()
            return 0

if __name__ == "__main__":
    # Ensure tables exist
    create_tables()
    
    # Update coordinates
    updated_accounts = update_account_coordinates()
    updated_parcels = update_parcel_coordinates()
    
    logger.info(f"Updated {updated_accounts} accounts and {updated_parcels} parcels with coordinates")