"""
Incremental Import of Improvements Data

This script allows importing improvements data in incremental steps.
It tracks the current position in the file and can be run multiple times
to continue importing from where it left off.
"""

import os
import logging
import sys
import time
from datetime import datetime
import pandas as pd
from decimal import Decimal
from app_setup import app, db, create_tables
from models import Parcel, Property

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File to store current position
POSITION_FILE = 'import_position.txt'

def get_last_position():
    """Get the last import position from the tracking file."""
    if os.path.exists(POSITION_FILE):
        try:
            with open(POSITION_FILE, 'r') as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def save_position(position):
    """Save the current import position to the tracking file."""
    with open(POSITION_FILE, 'w') as f:
        f.write(str(position))

def import_incremental(filename='ftp_dl_imprv.csv', batch_size=10, commit_every=5):
    """
    Import improvements data incrementally, continuing from the last position.
    
    Args:
        filename: Name of the improvements CSV file
        batch_size: Number of records to process in this run
        commit_every: Number of records to process before committing
        
    Returns:
        Dictionary with counts of parcels and properties created
    """
    start_time = time.time()
    csv_path = os.path.join('attached_assets', filename)
    
    # Get current position in file
    start_row = get_last_position()
    logger.info(f"Incremental import from {csv_path} starting at row {start_row+1}")
    logger.info(f"Parameters: batch_size={batch_size}, commit_every={commit_every}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return {'parcels': 0, 'properties': 0}
    
    # Check if we've reached the end of the file
    try:
        with open(csv_path, 'r', encoding='latin1') as f:
            total_rows = sum(1 for _ in f) - 1  # Subtract header row
        
        if start_row >= total_rows:
            logger.info(f"Already processed all {total_rows} rows, nothing to do")
            return {'parcels': 0, 'properties': 0, 'total_processed': start_row}
            
        rows_left = total_rows - start_row
        logger.info(f"CSV contains {total_rows} rows total, {rows_left} rows left to process")
        
        # Adjust batch size if needed
        if batch_size > rows_left:
            batch_size = rows_left
            logger.info(f"Adjusted batch size to {batch_size} (remaining rows)")
    
    except Exception as e:
        logger.warning(f"Could not determine total rows: {str(e)}")
    
    # Read the next batch
    try:
        # Read the batch starting from last position
        df = pd.read_csv(csv_path, skiprows=range(1, start_row + 1), nrows=batch_size, 
                       header=0, encoding='latin1')
        
        if len(df) == 0:
            logger.info("No more rows to read")
            return {'parcels': 0, 'properties': 0, 'total_processed': start_row}
            
        logger.info(f"Read {len(df)} rows from {csv_path}")
        
        # Convert column names to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Process the batch
        parcels_created = 0
        properties_created = 0
        records_processed = 0
        
        try:
            with app.app_context():
                # Process each record
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
                        db.session.flush()
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
                        
                        # Optional fields with validation
                        try:
                            living_area = int(float(row.get('living_area'))) if pd.notna(row.get('living_area')) else None
                            if living_area and (living_area < 0 or living_area > 100000):
                                living_area = None
                        except (ValueError, TypeError):
                            living_area = None
                            
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
                        
                        # Create property
                        property = Property(
                            parcel_id=parcel_id,
                            property_type=property_type,
                            year_built=actual_year_built,
                            square_footage=living_area,
                            stories=stories
                        )
                        db.session.add(property)
                        properties_created += 1
                        
                        # Process improvement value
                        try:
                            imprv_val = Decimal(str(row.get('imprv_val'))) if pd.notna(row.get('imprv_val')) else Decimal('0')
                            if imprv_val > 0:
                                parcel = db.session.get(Parcel, parcel_id)
                                if parcel:
                                    parcel.improvement_value += imprv_val
                                    parcel.total_value += imprv_val
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Skipping improvement value: {str(e)}")
                    
                    except Exception as e:
                        logger.warning(f"Error creating property: {str(e)}")
                        continue
                    
                    # Increment counter and commit periodically
                    records_processed += 1
                    if records_processed % commit_every == 0:
                        db.session.commit()
                        logger.info(f"Committed {records_processed} records")
                
                # Final commit for any remaining records
                db.session.commit()
                
                # Update position
                new_position = start_row + records_processed
                save_position(new_position)
                
                total_time = time.time() - start_time
                logger.info(f"Batch complete: created {parcels_created} parcels and {properties_created} properties in {total_time:.2f}s")
                logger.info(f"Position updated: {start_row} -> {new_position}")
                
                return {
                    'parcels': parcels_created, 
                    'properties': properties_created,
                    'total_processed': new_position
                }
                
        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
            return {'parcels': 0, 'properties': 0, 'total_processed': start_row}
    
    except Exception as e:
        logger.error(f"Error reading CSV: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {'parcels': 0, 'properties': 0, 'total_processed': start_row}

if __name__ == "__main__":
    with app.app_context():
        # Ensure tables exist
        create_tables()
        
        # Default parameters
        batch_size = 10  # Default: process 10 records at a time
        
        # Parse command line arguments
        if len(sys.argv) > 1:
            try:
                batch_size = int(sys.argv[1])
                logger.info(f"Using command line argument: batch_size={batch_size}")
            except ValueError:
                pass
        
        # Reset position if requested
        if len(sys.argv) > 2 and sys.argv[2].lower() == 'reset':
            logger.info("Resetting import position to 0")
            save_position(0)
            
            # Also clear data if resetting
            try:
                db.session.query(Property).delete()
                db.session.query(Parcel).delete()
                db.session.commit()
                logger.info("Cleared existing parcel and property records")
            except Exception as e:
                logger.error(f"Failed to clear data: {str(e)}")
        
        # Run the incremental import
        results = import_incremental(batch_size=batch_size)
        
        logger.info(f"Import completed: {results}")
        
        # Check if it was successful
        if results['parcels'] > 0 or results['properties'] > 0:
            logger.info("SUCCESS: Import worked correctly!")
        else:
            if results['total_processed'] > 0:
                logger.info("No new records processed, may have reached the end of file")
            else:
                logger.error("FAILED: Import did not create any records!")