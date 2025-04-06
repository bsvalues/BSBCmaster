"""
Import a Single Batch of Improvements Data

This script imports just a single batch of improvements data to test the functionality
without encountering timeout issues.
"""

import os
import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine
from decimal import Decimal
from app_setup import app, db, create_tables
from models import Parcel, Property

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_single_batch(filename='ftp_dl_imprv.csv', batch_size=50):
    """
    Import just one batch of improvements data.
    
    Args:
        filename: Name of the improvements CSV file
        batch_size: Number of records to process
        
    Returns:
        Dictionary with counts of parcels and properties created
    """
    csv_path = os.path.join('attached_assets', filename)
    logger.info(f"Importing a single batch of {batch_size} improvements from {csv_path}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return {'parcels': 0, 'properties': 0}
    
    try:
        # Get database connection
        database_url = app.config['SQLALCHEMY_DATABASE_URI']
        engine = create_engine(database_url)
        
        # Use Latin1 encoding directly 
        df = pd.read_csv(csv_path, encoding='latin1', nrows=batch_size)
        logger.info(f"Read {len(df)} rows from {csv_path}")
        
        # Convert column names to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Track created parcels to avoid duplicates
        created_parcels = {}
        created_properties = 0
        
        with app.app_context():
            # Clear existing parcels and properties
            db.session.query(Property).delete()
            db.session.query(Parcel).delete()
            db.session.commit()
            logger.info("Cleared existing parcel and property records")
            
            # Create all parcels first, then all properties
            # This approach reduces the number of DB operations
            
            # Step 1: Create all unique parcels
            parcel_objects = {}
            for _, row in df.iterrows():
                prop_id = str(row.get('prop_id', ''))
                if not prop_id or prop_id == 'nan' or prop_id in parcel_objects:
                    continue
                    
                # Create a new parcel
                parcel = Parcel(
                    parcel_id=prop_id,
                    address=f"Property {prop_id}",  # Placeholder
                    city="Unknown",                # Placeholder
                    state="WA",                    # Assuming Washington state
                    zip_code="99999",              # Placeholder
                    land_value=0,
                    improvement_value=0,
                    total_value=0,
                    assessment_year=datetime.now().year
                )
                parcel_objects[prop_id] = parcel
                db.session.add(parcel)
            
            # Commit all parcels
            db.session.commit()
            logger.info(f"Created {len(parcel_objects)} parcels")
            
            # Step 2: Get IDs for all parcels
            for prop_id, parcel in parcel_objects.items():
                created_parcels[prop_id] = parcel.id
            
            # Step 3: Create properties and update parcel values
            properties_to_add = []
            for _, row in df.iterrows():
                prop_id = str(row.get('prop_id', ''))
                if not prop_id or prop_id == 'nan' or prop_id not in created_parcels:
                    continue
                
                # Process improvement values
                try:
                    imprv_val = Decimal(str(row.get('imprv_val'))) if pd.notna(row.get('imprv_val')) else Decimal('0')
                except (ValueError, TypeError):
                    imprv_val = Decimal('0')
                    
                # Handle numeric values safely
                try:
                    living_area = int(float(row.get('living_area'))) if pd.notna(row.get('living_area')) else None
                    # Cap square footage
                    if living_area and (living_area < 0 or living_area > 100000):
                        living_area = None
                except (ValueError, TypeError):
                    living_area = None
                    
                primary_use_cd = str(row.get('primary_use_cd', ''))
                
                try:
                    stories = float(row.get('stories')) if pd.notna(row.get('stories')) else None
                    # Cap stories
                    if stories and (stories < 0 or stories > 100):
                        stories = None
                except (ValueError, TypeError):
                    stories = None
                    
                try:
                    actual_year_built = int(float(row.get('actual_year_built'))) if pd.notna(row.get('actual_year_built')) else None
                    # Validate year
                    if actual_year_built and (actual_year_built < 1800 or actual_year_built > 2100):
                        actual_year_built = None
                except (ValueError, TypeError):
                    actual_year_built = None
                
                # Determine property type
                property_type = "Unknown"
                if primary_use_cd == '81':
                    property_type = "Residential"
                elif primary_use_cd == '83':
                    property_type = "Commercial"
                
                # Create property
                property = Property(
                    parcel_id=created_parcels[prop_id],
                    property_type=property_type,
                    year_built=actual_year_built,
                    square_footage=living_area,
                    stories=stories
                )
                properties_to_add.append(property)
                
                # Update parcel improvement value
                if imprv_val > 0:
                    parcel = parcel_objects[prop_id]
                    parcel.improvement_value += imprv_val
                    parcel.total_value += imprv_val
            
            # Add all properties at once
            if properties_to_add:
                db.session.add_all(properties_to_add)
                created_properties = len(properties_to_add)
            
            # Commit all changes
            db.session.commit()
            
            logger.info(f"Created {len(created_parcels)} parcels and {created_properties} properties")
            return {'parcels': len(created_parcels), 'properties': created_properties}
    
    except Exception as e:
        logger.error(f"Error importing improvements: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {'parcels': 0, 'properties': 0}

if __name__ == "__main__":
    with app.app_context():
        # Ensure tables exist
        create_tables()
        # Import a small batch of improvements data
        results = import_single_batch(batch_size=50)
        logger.info(f"Import completed: {results}")
        
        # Check if it was successful
        if results['parcels'] > 0 and results['properties'] > 0:
            logger.info("SUCCESS: Import worked correctly!")
        else:
            logger.error("FAILED: Import did not create any records!")