"""
Import Improvements Data Script

This script specifically focuses on importing the improvements data from
the attached_assets directory to populate the parcels and properties tables.
"""

import os
import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine
from app_setup import app, db, create_tables
from models import Parcel, Property

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_improvements(filename='ftp_dl_imprv.csv'):
    """
    Import improvements data to create parcels and properties.
    
    Args:
        filename: Name of the improvements CSV file
        
    Returns:
        Dictionary with counts of parcels and properties created
    """
    csv_path = os.path.join('attached_assets', filename)
    logger.info(f"Importing improvements data from {csv_path}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return {'parcels': 0, 'properties': 0}
    
    try:
        # Get database connection
        database_url = app.config['SQLALCHEMY_DATABASE_URI']
        engine = create_engine(database_url)
        
        # Try different encodings for the CSV file
        encodings = ['utf-8', 'latin1', 'cp1252', 'ISO-8859-1']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(csv_path, encoding=encoding)
                logger.info(f"Successfully read CSV with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                logger.warning(f"Failed to read CSV with encoding: {encoding}")
        
        if df is None:
            logger.error("Failed to read CSV with any of the attempted encodings")
            return {'parcels': 0, 'properties': 0}
            
        logger.info(f"Read {len(df)} rows from {csv_path}")
        
        # Convert column names to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Track created parcels to avoid duplicates
        created_parcels = {}
        created_properties = 0
        
        with app.app_context():
            # Clear existing parcels and properties if specified
            db.session.query(Property).delete()
            db.session.query(Parcel).delete()
            db.session.commit()
            logger.info("Cleared existing parcel and property records")
            
            # Process each row and create corresponding records
            for _, row in df.iterrows():
                prop_id = str(row.get('prop_id', ''))
                imprv_id = str(row.get('imprv_id', ''))
                imprv_desc = row.get('imprv_desc', '')
                try:
                    imprv_val = float(row.get('imprv_val')) if pd.notna(row.get('imprv_val')) else 0
                except (ValueError, TypeError):
                    imprv_val = 0
                # Handle numeric values safely
                try:
                    living_area = float(row.get('living_area')) if pd.notna(row.get('living_area')) else None
                except (ValueError, TypeError):
                    living_area = None
                    
                primary_use_cd = str(row.get('primary_use_cd', ''))
                
                try:
                    stories = float(row.get('stories')) if pd.notna(row.get('stories')) else None
                except (ValueError, TypeError):
                    stories = None
                    
                try:
                    actual_year_built = int(float(row.get('actual_year_built'))) if pd.notna(row.get('actual_year_built')) else None
                    # Validate year is in a reasonable range
                    if actual_year_built and (actual_year_built < 1800 or actual_year_built > 2100):
                        actual_year_built = None
                except (ValueError, TypeError):
                    actual_year_built = None
                
                # Skip rows with missing prop_id
                if not prop_id:
                    continue
                
                # Create or get parcel
                if prop_id not in created_parcels:
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
                    db.session.add(parcel)
                    db.session.flush()  # Flush to get the ID
                    created_parcels[prop_id] = parcel.id
                    
                # Create a property record linked to the parcel
                property_type = "Unknown"
                if primary_use_cd == '81':
                    property_type = "Residential"
                elif primary_use_cd == '83':
                    property_type = "Commercial"
                
                property = Property(
                    parcel_id=created_parcels[prop_id],
                    property_type=property_type,
                    year_built=actual_year_built if actual_year_built else None,
                    square_footage=living_area if living_area else None,
                    stories=stories if stories else None
                )
                db.session.add(property)
                created_properties += 1
                
                # Update parcel improvement value (directly via the already fetched parcel object)
                if prop_id in created_parcels and imprv_val > 0:
                    parcel = db.session.query(Parcel).get(created_parcels[prop_id])
                    if parcel:
                        parcel.improvement_value += imprv_val
                        parcel.total_value += imprv_val
                
                # Commit every 1000 records to avoid large transactions
                if created_properties % 1000 == 0:
                    db.session.commit()
                    logger.info(f"Processed {created_properties} records...")
            
            # Commit final changes
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
        # Import improvements data
        results = import_improvements()
        logger.info(f"Import completed: {results}")