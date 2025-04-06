"""
Minimal Improvements Data Import Script

This script performs a minimal import of improvements data, focusing only 
on the essential operations to ensure successful database insertion.
"""

import os
import logging
from datetime import datetime
import pandas as pd
from decimal import Decimal
from app_setup import app, db, create_tables
from models import Parcel, Property

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_minimal_sample(filename='ftp_dl_imprv.csv', sample_size=10):
    """
    Import a minimal sample of improvements data.
    
    Args:
        filename: Name of the improvements CSV file
        sample_size: Number of records to process
        
    Returns:
        Dictionary with counts of parcels and properties created
    """
    csv_path = os.path.join('attached_assets', filename)
    logger.info(f"Importing minimal sample of {sample_size} improvements from {csv_path}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return {'parcels': 0, 'properties': 0}
    
    try:
        # Read a minimal sample
        df = pd.read_csv(csv_path, nrows=sample_size, encoding='latin1')
        logger.info(f"Read {len(df)} rows from {csv_path}")
        
        # Convert column names to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        with app.app_context():
            # Clear existing data
            db.session.query(Property).delete()
            db.session.query(Parcel).delete()
            db.session.commit()
            logger.info("Cleared existing parcel and property records")
            
            # Process each row manually
            parcels_created = 0
            properties_created = 0
            
            for _, row in df.iterrows():
                # Create parcel first
                prop_id = str(row.get('prop_id', ''))
                if not prop_id or prop_id == 'nan':
                    continue
                
                # Check if parcel already exists
                existing_parcel = db.session.query(Parcel).filter_by(parcel_id=prop_id).first()
                
                if not existing_parcel:
                    # Create a new parcel
                    parcel = Parcel(
                        parcel_id=prop_id,
                        address=f"Property {prop_id}",
                        city="Unknown",
                        state="WA",
                        zip_code="99999",
                        land_value=0,
                        improvement_value=0,
                        total_value=0,
                        assessment_year=datetime.now().year
                    )
                    db.session.add(parcel)
                    db.session.flush()  # Get ID without committing
                    parcels_created += 1
                    parcel_id = parcel.id
                else:
                    parcel_id = existing_parcel.id
                
                # Now create property
                try:
                    # Process values carefully
                    property_type = "Unknown"
                    primary_use_cd = str(row.get('primary_use_cd', ''))
                    if primary_use_cd == '81':
                        property_type = "Residential"
                    elif primary_use_cd == '83':
                        property_type = "Commercial"
                    
                    # Create property with minimal fields to avoid errors
                    property = Property(
                        parcel_id=parcel_id,
                        property_type=property_type
                    )
                    db.session.add(property)
                    properties_created += 1
                    
                    # Process improvement value
                    try:
                        imprv_val = Decimal(str(row.get('imprv_val'))) if pd.notna(row.get('imprv_val')) else Decimal('0')
                        if imprv_val > 0:
                            parcel = db.session.query(Parcel).get(parcel_id)
                            if parcel:
                                parcel.improvement_value += imprv_val
                                parcel.total_value += imprv_val
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Skipping improvement value: {str(e)}")
                
                except Exception as e:
                    logger.warning(f"Error creating property: {str(e)}")
                    continue
            
            # Commit all changes
            db.session.commit()
            logger.info(f"Created {parcels_created} parcels and {properties_created} properties")
            
            return {'parcels': parcels_created, 'properties': properties_created}
    
    except Exception as e:
        logger.error(f"Error importing improvements: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {'parcels': 0, 'properties': 0}

if __name__ == "__main__":
    with app.app_context():
        # Ensure tables exist
        create_tables()
        
        # Import a minimal sample
        results = import_minimal_sample(sample_size=10)
        logger.info(f"Import completed: {results}")
        
        # Check if it was successful
        if results['parcels'] > 0 and results['properties'] > 0:
            logger.info("SUCCESS: Import worked correctly!")
        else:
            logger.error("FAILED: Import did not create any records!")