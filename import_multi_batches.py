"""
Import Multiple Batches of Improvements Data

This script imports improvements data in multiple batches to avoid timeouts.
It uses the same optimized approach as the single batch import but processes
multiple batches in sequence.
"""

import os
import logging
import sys
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine
from decimal import Decimal
from app_setup import app, db, create_tables
from models import Parcel, Property

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_multi_batches(filename='ftp_dl_imprv.csv', batch_size=50, num_batches=5):
    """
    Import multiple batches of improvements data.
    
    Args:
        filename: Name of the improvements CSV file
        batch_size: Number of records per batch
        num_batches: Number of batches to process
        
    Returns:
        Dictionary with counts of parcels and properties created
    """
    csv_path = os.path.join('attached_assets', filename)
    logger.info(f"Importing {num_batches} batches of {batch_size} improvements from {csv_path}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return {'parcels': 0, 'properties': 0}
    
    try:
        # Get database connection
        database_url = app.config['SQLALCHEMY_DATABASE_URI']
        engine = create_engine(database_url)
        
        # Try to get total rows in CSV (faster method)
        try:
            with open(csv_path, 'r', encoding='latin1') as f:
                total_rows = sum(1 for _ in f) - 1  # Subtract header row
            logger.info(f"CSV contains approximately {total_rows} rows total")
        except Exception as e:
            logger.warning(f"Could not count total rows: {str(e)}")
        
        # Clear existing data
        with app.app_context():
            db.session.query(Property).delete()
            db.session.query(Parcel).delete()
            db.session.commit()
            logger.info("Cleared existing parcel and property records")
        
        # Process batches
        created_parcels = {}
        total_properties = 0
        
        # Use a generator to read the CSV in chunks
        chunks = pd.read_csv(csv_path, chunksize=batch_size, encoding='latin1')
        
        for batch_num, df in enumerate(chunks, 1):
            if batch_num > num_batches:
                break
                
            logger.info(f"Processing batch {batch_num} of {num_batches}...")
            
            # Convert column names to lowercase
            df.columns = [col.lower() for col in df.columns]
            
            # Track batch specific objects
            batch_parcels = {}
            batch_properties = 0
            
            with app.app_context():
                # STEP 1: Create all unique parcels for this batch
                for _, row in df.iterrows():
                    prop_id = str(row.get('prop_id', ''))
                    if not prop_id or prop_id == 'nan' or prop_id in created_parcels or prop_id in batch_parcels:
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
                    batch_parcels[prop_id] = parcel
                    db.session.add(parcel)
                
                # Commit parcels and get their IDs
                if batch_parcels:
                    db.session.commit()
                    # Update global tracking dictionary
                    for prop_id, parcel in batch_parcels.items():
                        created_parcels[prop_id] = parcel.id
                    
                    logger.info(f"Batch {batch_num}: Created {len(batch_parcels)} new parcels, total: {len(created_parcels)}")
                
                # STEP 2: Create properties and update improvement values
                properties = []
                for _, row in df.iterrows():
                    prop_id = str(row.get('prop_id', ''))
                    if not prop_id or prop_id == 'nan' or prop_id not in created_parcels:
                        continue
                    
                    # Process improvement values (using Decimal)
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
                    properties.append(property)
                    batch_properties += 1
                    
                    # Update parcel improvement value
                    if imprv_val > 0:
                        # Get the parcel (either from this batch or using its ID)
                        if prop_id in batch_parcels:
                            parcel = batch_parcels[prop_id]
                        else:
                            parcel = db.session.get(Parcel, created_parcels[prop_id])
                            
                        if parcel:
                            parcel.improvement_value += imprv_val
                            parcel.total_value += imprv_val
                
                # Add all properties and commit
                if properties:
                    db.session.add_all(properties)
                    db.session.commit()
                    total_properties += batch_properties
                    
                    logger.info(f"Batch {batch_num}: Created {batch_properties} properties, total: {total_properties}")
        
        logger.info(f"Multi-batch import complete: {len(created_parcels)} parcels, {total_properties} properties")
        return {'parcels': len(created_parcels), 'properties': total_properties}
    
    except Exception as e:
        logger.error(f"Error importing improvements: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {'parcels': 0, 'properties': 0}

if __name__ == "__main__":
    with app.app_context():
        # Ensure tables exist
        create_tables()
        
        # Import multiple batches
        batch_size = 50
        num_batches = 5
        
        if len(sys.argv) > 1:
            try:
                num_batches = int(sys.argv[1])
                logger.info(f"Using command line argument: {num_batches} batches")
            except ValueError:
                pass
                
        if len(sys.argv) > 2:
            try:
                batch_size = int(sys.argv[2])
                logger.info(f"Using command line argument: {batch_size} records per batch")
            except ValueError:
                pass
        
        results = import_multi_batches(batch_size=batch_size, num_batches=num_batches)
        logger.info(f"Import completed: {results}")
        
        # Check if it was successful
        if results['parcels'] > 0 and results['properties'] > 0:
            logger.info("SUCCESS: Import worked correctly!")
        else:
            logger.error("FAILED: Import did not create any records!")