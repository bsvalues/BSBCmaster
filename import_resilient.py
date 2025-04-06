"""
Resilient Import of Improvements Data

This script provides a fault-tolerant approach to importing improvements data
with connection retry logic and transaction management to handle database timeouts.
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

def execute_with_retry(func, max_retries=3, retry_delay=1):
    """
    Execute a function with retry logic.
    
    Args:
        func: Function to execute
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Result of the function or None if all retries failed
    """
    retries = 0
    last_error = None
    
    while retries < max_retries:
        try:
            return func()
        except Exception as e:
            retries += 1
            last_error = e
            logger.warning(f"Operation failed (attempt {retries}/{max_retries}): {str(e)}")
            if retries >= max_retries:
                logger.error(f"Maximum retries reached. Last error: {str(last_error)}")
                return None
            time.sleep(retry_delay)
    
    return None

def import_resilient(filename='ftp_dl_imprv.csv', batch_size=25, transaction_size=5, max_batches=2):
    """
    Import improvements data with resilient error handling.
    
    Args:
        filename: Name of the improvements CSV file
        batch_size: Number of records to process at once
        transaction_size: Number of records per transaction
        max_batches: Maximum number of batches to process
        
    Returns:
        Dictionary with counts of parcels and properties created
    """
    start_time = time.time()
    csv_path = os.path.join('attached_assets', filename)
    logger.info(f"Resilient import from {csv_path}")
    logger.info(f"Parameters: batch_size={batch_size}, transaction_size={transaction_size}, max_batches={max_batches}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return {'parcels': 0, 'properties': 0}
    
    # Clear existing data
    def clear_data():
        with app.app_context():
            try:
                db.session.query(Property).delete()
                db.session.query(Parcel).delete()
                db.session.commit()
                logger.info("Cleared existing parcel and property records")
                return True
            except Exception as e:
                logger.error(f"Failed to clear data: {str(e)}")
                db.session.rollback()
                return False
    
    if not execute_with_retry(clear_data):
        logger.error("Could not clear existing data, aborting import")
        return {'parcels': 0, 'properties': 0}
    
    # Track created objects
    created_parcels = {}
    total_properties = 0
    batches_processed = 0
    
    try:
        # Use a generator to read the CSV in chunks
        chunks = pd.read_csv(csv_path, chunksize=batch_size, encoding='latin1')
        
        for batch_num, df in enumerate(chunks, 1):
            if max_batches is not None and batch_num > max_batches:
                logger.info(f"Reached maximum batch limit ({max_batches})")
                break
                
            batch_start = time.time()
            logger.info(f"Processing batch {batch_num}" + 
                       (f" of {max_batches}" if max_batches else ""))
            
            # Convert column names to lowercase
            df.columns = [col.lower() for col in df.columns]
            
            # Step 1: Extract unique property IDs
            unique_prop_ids = set()
            for _, row in df.iterrows():
                prop_id = str(row.get('prop_id', ''))
                if prop_id and prop_id != 'nan':
                    unique_prop_ids.add(prop_id)
            
            # Step 2: Create parcels in smaller transactions
            parcels_created = 0
            prop_id_list = list(unique_prop_ids)
            
            # Process in smaller transactions
            for i in range(0, len(prop_id_list), transaction_size):
                transaction_prop_ids = prop_id_list[i:i+transaction_size]
                
                def create_parcels_transaction():
                    nonlocal parcels_created
                    
                    with app.app_context():
                        parcels_to_add = []
                        
                        for prop_id in transaction_prop_ids:
                            if prop_id in created_parcels:
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
                            parcels_to_add.append(parcel)
                        
                        if parcels_to_add:
                            db.session.add_all(parcels_to_add)
                            db.session.commit()
                            
                            # Get IDs
                            for parcel in parcels_to_add:
                                result = db.session.execute(
                                    text("SELECT id FROM parcels WHERE parcel_id = :parcel_id"),
                                    {"parcel_id": parcel.parcel_id}
                                ).fetchone()
                                if result:
                                    created_parcels[parcel.parcel_id] = result[0]
                            
                            parcels_created += len(parcels_to_add)
                            return True
                        return True  # Nothing to add is still a success
                
                # Execute with retry
                if not execute_with_retry(create_parcels_transaction):
                    logger.error(f"Failed to create parcels in transaction {i//transaction_size + 1}")
                    continue
            
            logger.info(f"Created {parcels_created} new parcels in batch {batch_num}, total: {len(created_parcels)}")
            
            # Step 3: Create properties in smaller transactions
            batch_properties = 0
            
            # Process dataframe in smaller groups
            for i in range(0, len(df), transaction_size):
                transaction_df = df.iloc[i:i+transaction_size]
                
                def create_properties_transaction():
                    nonlocal batch_properties
                    
                    with app.app_context():
                        properties_to_add = []
                        improvement_updates = {}
                        
                        for _, row in transaction_df.iterrows():
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
                            
                            # Track improvement values
                            if imprv_val > 0:
                                parcel_id = created_parcels[prop_id]
                                if parcel_id in improvement_updates:
                                    improvement_updates[parcel_id] += imprv_val
                                else:
                                    improvement_updates[parcel_id] = imprv_val
                        
                        # Add properties
                        if properties_to_add:
                            db.session.add_all(properties_to_add)
                            db.session.commit()
                            batch_properties += len(properties_to_add)
                        
                        # Update improvement values
                        if improvement_updates:
                            for parcel_id, value in improvement_updates.items():
                                db.session.execute(
                                    text("UPDATE parcels SET improvement_value = improvement_value + :value, " +
                                        "total_value = total_value + :value WHERE id = :id"),
                                    {"value": value, "id": parcel_id}
                                )
                            db.session.commit()
                        
                        return True
                
                # Execute with retry
                if not execute_with_retry(create_properties_transaction):
                    logger.error(f"Failed to create properties in transaction {i//transaction_size + 1}")
                    continue
            
            total_properties += batch_properties
            batches_processed += 1
            
            batch_time = time.time() - batch_start
            logger.info(f"Batch {batch_num}: Created {batch_properties} properties, " +
                       f"total: {total_properties} (took {batch_time:.2f}s)")
        
        total_time = time.time() - start_time
        logger.info(f"Import complete: processed {batches_processed} batches in {total_time:.2f}s")
        logger.info(f"Created {len(created_parcels)} parcels and {total_properties} properties")
        
        return {'parcels': len(created_parcels), 'properties': total_properties}
    
    except Exception as e:
        logger.error(f"Error importing improvements: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {'parcels': len(created_parcels), 'properties': total_properties}

if __name__ == "__main__":
    with app.app_context():
        # Ensure tables exist
        create_tables()
        
        # Default parameters
        batch_size = 25  # Default: 25 records per batch
        transaction_size = 5  # Default: 5 records per transaction
        max_batches = 2  # Default: 2 batches
        
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
                transaction_size = int(sys.argv[3])
                logger.info(f"Using command line argument: {transaction_size} records per transaction")
            except ValueError:
                pass
        
        # Run the resilient import
        results = import_resilient(
            batch_size=batch_size,
            transaction_size=transaction_size,
            max_batches=max_batches
        )
        
        logger.info(f"Import completed: {results}")
        
        # Check if it was successful
        if results['parcels'] > 0 and results['properties'] > 0:
            logger.info("SUCCESS: Import worked correctly!")
        else:
            logger.error("FAILED: Import did not create any records!")