"""
Optimized Import of Improvements Data

This script implements a highly optimized version of the improvements data import process
to avoid timeouts and other issues. It uses batched processing and connection pooling
to improve performance.
"""

import os
import logging
import sys
import time
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from decimal import Decimal
from app_setup import app, db, create_tables
from models import Parcel, Property

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_improvements_optimized(filename='ftp_dl_imprv.csv', batch_size=100, max_batches=10, 
                                 clear_existing=True, commit_frequency=50):
    """
    Import improvements data with optimized performance.
    
    Args:
        filename: Name of the improvements CSV file
        batch_size: Number of records to read at a time from CSV
        max_batches: Maximum number of batches to process (None for all)
        clear_existing: Whether to clear existing data before import
        commit_frequency: How often to commit within a batch
        
    Returns:
        Dictionary with counts of parcels and properties created
    """
    start_time = time.time()
    csv_path = os.path.join('attached_assets', filename)
    logger.info(f"Optimized import from {csv_path}")
    logger.info(f"Parameters: batch_size={batch_size}, max_batches={max_batches}, commit_frequency={commit_frequency}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return {'parcels': 0, 'properties': 0}
    
    try:
        # Get database connection
        database_url = app.config['SQLALCHEMY_DATABASE_URI']
        engine = create_engine(database_url, pool_size=5, max_overflow=10)
        
        # Try to get total rows in CSV
        try:
            with open(csv_path, 'r', encoding='latin1') as f:
                total_rows = sum(1 for _ in f) - 1  # Subtract header row
            logger.info(f"CSV contains approximately {total_rows} rows total")
        except Exception as e:
            logger.warning(f"Could not count total rows: {str(e)}")
            total_rows = "unknown"
        
        # Clear existing data if requested
        if clear_existing:
            with app.app_context():
                try:
                    # Use raw SQL for faster deletion
                    with engine.connect() as conn:
                        conn.execute(text("DELETE FROM properties"))
                        conn.execute(text("DELETE FROM parcels"))
                        conn.commit()
                    logger.info("Cleared existing parcel and property records")
                except Exception as e:
                    logger.error(f"Failed to clear existing data: {str(e)}")
                    if 'SQLAlchemy' in str(e):
                        # Fallback to SQLAlchemy ORM deletion
                        db.session.query(Property).delete()
                        db.session.query(Parcel).delete()
                        db.session.commit()
                        logger.info("Cleared existing parcel and property records (using ORM)")
        
        # Track created objects
        created_parcels = {}
        total_properties = 0
        batches_processed = 0
        rows_processed = 0
        
        # Use a generator to read the CSV in chunks
        chunks = pd.read_csv(csv_path, chunksize=batch_size, encoding='latin1')
        
        for batch_num, df in enumerate(chunks, 1):
            batch_start_time = time.time()
            
            if max_batches is not None and batch_num > max_batches:
                logger.info(f"Reached maximum batch limit ({max_batches})")
                break
                
            logger.info(f"Processing batch {batch_num}" + 
                       (f" of {max_batches}" if max_batches else ""))
            
            # Convert column names to lowercase
            df.columns = [col.lower() for col in df.columns]
            
            # Track batch specific objects
            batch_parcels = {}
            batch_properties = 0
            
            with app.app_context():
                # STEP 1: Create all unique parcels for this batch
                parcels_to_add = []
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
                    parcels_to_add.append(parcel)
                
                # Add parcels in bulk and commit
                if parcels_to_add:
                    db.session.bulk_save_objects(parcels_to_add)
                    db.session.commit()
                    
                    # Get IDs for new parcels (need to query since bulk_save doesn't set them)
                    for parcel in parcels_to_add:
                        # Query to get the ID
                        result = db.session.execute(
                            text("SELECT id FROM parcels WHERE parcel_id = :parcel_id"),
                            {"parcel_id": parcel.parcel_id}
                        ).fetchone()
                        if result:
                            created_parcels[parcel.parcel_id] = result[0]
                    
                    logger.info(f"Batch {batch_num}: Created {len(batch_parcels)} new parcels, " +
                                f"total: {len(created_parcels)}")
                
                # STEP 2: Create properties (process in smaller sub-batches)
                properties_to_add = []
                improvement_updates = {}
                
                for idx, row in df.iterrows():
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
                        if living_area and (living_area < 0 or living_area > 100000):
                            living_area = None
                    except (ValueError, TypeError):
                        living_area = None
                        
                    primary_use_cd = str(row.get('primary_use_cd', ''))
                    
                    try:
                        stories = float(row.get('stories')) if pd.notna(row.get('stories')) else None
                        if stories and (stories < 0 or stories > 100):
                            stories = None
                    except (ValueError, TypeError):
                        stories = None
                        
                    try:
                        actual_year_built = int(float(row.get('actual_year_built'))) if pd.notna(row.get('actual_year_built')) else None
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
                    batch_properties += 1
                    
                    # Track improvement value updates
                    if imprv_val > 0:
                        parcel_id = created_parcels[prop_id]
                        if parcel_id in improvement_updates:
                            improvement_updates[parcel_id] += imprv_val
                        else:
                            improvement_updates[parcel_id] = imprv_val
                    
                    # Commit in smaller groups to avoid timeouts
                    if len(properties_to_add) >= commit_frequency:
                        db.session.bulk_save_objects(properties_to_add)
                        properties_to_add = []
                        db.session.commit()
                
                # Add remaining properties
                if properties_to_add:
                    db.session.bulk_save_objects(properties_to_add)
                    db.session.commit()
                
                # Update improvement values
                if improvement_updates:
                    for parcel_id, value in improvement_updates.items():
                        db.session.execute(
                            text("UPDATE parcels SET improvement_value = improvement_value + :value, " +
                                "total_value = total_value + :value WHERE id = :id"),
                            {"value": value, "id": parcel_id}
                        )
                    db.session.commit()
                
                total_properties += batch_properties
                rows_processed += len(df)
                batches_processed += 1
                
                batch_time = time.time() - batch_start_time
                logger.info(f"Batch {batch_num}: Created {batch_properties} properties, " +
                           f"total: {total_properties} (took {batch_time:.2f}s)")
                
                # Progress report
                if total_rows != "unknown":
                    progress = min(100, (rows_processed / total_rows) * 100)
                    logger.info(f"Progress: {progress:.1f}% ({rows_processed}/{total_rows})")
        
        total_time = time.time() - start_time
        logger.info(f"Import complete: processed {batches_processed} batches, " +
                   f"{rows_processed} rows in {total_time:.2f}s")
        logger.info(f"Created {len(created_parcels)} parcels and {total_properties} properties")
        
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
        
        # Default parameters for the optimized import
        batch_size = 100  # Default 100 records per batch
        max_batches = 10  # Default 10 batches
        commit_frequency = 50  # Commit after every 50 records in a batch
        
        # Parse command line arguments
        if len(sys.argv) > 1:
            try:
                max_batches = int(sys.argv[1])
                logger.info(f"Using command line argument: {max_batches} batches")
            except ValueError:
                pass
                
        if len(sys.argv) > 2:
            try:
                batch_size = int(sys.argv[2])
                logger.info(f"Using command line argument: {batch_size} records per batch")
            except ValueError:
                pass
        
        if len(sys.argv) > 3:
            try:
                commit_frequency = int(sys.argv[3])
                logger.info(f"Using command line argument: commit every {commit_frequency} records")
            except ValueError:
                pass
        
        # Run the optimized import
        results = import_improvements_optimized(
            batch_size=batch_size,
            max_batches=max_batches,
            commit_frequency=commit_frequency
        )
        
        logger.info(f"Import completed: {results}")
        
        # Check if it was successful
        if results['parcels'] > 0 and results['properties'] > 0:
            logger.info("SUCCESS: Import worked correctly!")
        else:
            logger.error("FAILED: Import did not create any records!")