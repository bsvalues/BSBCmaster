"""
Incremental Import of All Property Assessment Data

This script allows importing all types of property assessment data
(accounts, improvements, images) in incremental steps. It provides a
unified interface for managing all data imports.
"""

import os
import logging
import sys
import time
from datetime import datetime
import pandas as pd
from decimal import Decimal
from app_setup import app, db, create_tables
from models import Parcel, Property, Account, PropertyImage
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Files to store current positions
POSITION_FILES = {
    'improvements': 'import_improvements_position.txt',
    'accounts': 'import_accounts_position.txt',
    'images': 'import_images_position.txt'
}

CSV_FILES = {
    'improvements': 'ftp_dl_imprv.csv',
    'accounts': 'account.csv',
    'images': 'images.csv'
}

def get_last_position(data_type):
    """Get the last import position from the tracking file."""
    position_file = POSITION_FILES.get(data_type, f'import_{data_type}_position.txt')
    if os.path.exists(position_file):
        try:
            with open(position_file, 'r') as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def save_position(data_type, position):
    """Save the current import position to the tracking file."""
    position_file = POSITION_FILES.get(data_type, f'import_{data_type}_position.txt')
    with open(position_file, 'w') as f:
        f.write(str(position))

def import_improvements(batch_size=10, commit_every=5):
    """
    Import improvements data incrementally, continuing from the last position.
    
    Args:
        batch_size: Number of records to process in this run
        commit_every: Number of records to process before committing
        
    Returns:
        Dictionary with counts of parcels and properties created
    """
    data_type = 'improvements'
    start_time = time.time()
    csv_path = os.path.join('attached_assets', CSV_FILES[data_type])
    
    # Get current position in file
    start_row = get_last_position(data_type)
    logger.info(f"Incremental import of {data_type} from {csv_path} starting at row {start_row+1}")
    logger.info(f"Parameters: batch_size={batch_size}, commit_every={commit_every}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return {'parcels': 0, 'properties': 0, 'total_processed': start_row}
    
    # Check if we've reached the end of the file
    try:
        with open(csv_path, 'r', encoding='latin1') as f:
            total_rows = sum(1 for _ in f) - 1  # Subtract header row
        
        if start_row >= total_rows:
            logger.info(f"Already processed all {total_rows} rows of {data_type}, nothing to do")
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
            logger.info(f"No more rows to read from {data_type}")
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
                save_position(data_type, new_position)
                
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
        logger.error(traceback.format_exc())
        return {'parcels': 0, 'properties': 0, 'total_processed': start_row}

def import_accounts(batch_size=20, commit_every=10):
    """
    Import account data incrementally.
    
    Args:
        batch_size: Number of records to process in this run
        commit_every: Number of records to process before committing
        
    Returns:
        Dictionary with count of accounts created
    """
    data_type = 'accounts'
    start_time = time.time()
    csv_path = os.path.join('attached_assets', CSV_FILES[data_type])
    
    # Get current position in file
    start_row = get_last_position(data_type)
    logger.info(f"Incremental import of {data_type} from {csv_path} starting at row {start_row+1}")
    logger.info(f"Parameters: batch_size={batch_size}, commit_every={commit_every}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return {'accounts': 0, 'total_processed': start_row}
    
    # Check if we've reached the end of the file
    try:
        with open(csv_path, 'r', encoding='latin1') as f:
            total_rows = sum(1 for _ in f) - 1  # Subtract header row
        
        if start_row >= total_rows:
            logger.info(f"Already processed all {total_rows} rows of {data_type}, nothing to do")
            return {'accounts': 0, 'total_processed': start_row}
            
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
            logger.info(f"No more rows to read from {data_type}")
            return {'accounts': 0, 'total_processed': start_row}
            
        logger.info(f"Read {len(df)} rows from {csv_path}")
        
        # Convert column names to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Process the batch
        accounts_created = 0
        records_processed = 0
        
        try:
            with app.app_context():
                # Process each record
                for _, row in df.iterrows():
                    # Map CSV columns to database fields
                    # The account.csv file has 'acct_id' and 'file_as_name'
                    account_id = str(row.get('acct_id', ''))
                    if not account_id or account_id == 'nan':
                        continue
                    
                    # Check if account already exists
                    existing_account = db.session.query(Account).filter_by(account_id=account_id).first()
                    
                    if not existing_account:
                        # Create a new account
                        account = Account(
                            account_id=account_id,
                            owner_name=str(row.get('file_as_name', '')) if pd.notna(row.get('file_as_name')) else "Unknown",
                            # Set other fields to defaults since they're not in the CSV
                            mailing_address=None,
                            mailing_city=None,
                            mailing_state=None,
                            mailing_zip=None
                        )
                        db.session.add(account)
                        accounts_created += 1
                    
                    # Increment counter and commit periodically
                    records_processed += 1
                    if records_processed % commit_every == 0:
                        db.session.commit()
                        logger.info(f"Committed {records_processed} records")
                
                # Final commit for any remaining records
                db.session.commit()
                
                # Update position
                new_position = start_row + records_processed
                save_position(data_type, new_position)
                
                total_time = time.time() - start_time
                logger.info(f"Batch complete: created {accounts_created} accounts in {total_time:.2f}s")
                logger.info(f"Position updated: {start_row} -> {new_position}")
                
                return {
                    'accounts': accounts_created,
                    'total_processed': new_position
                }
                
        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            logger.error(traceback.format_exc())
            try:
                db.session.rollback()
            except:
                pass
            return {'accounts': 0, 'total_processed': start_row}
    
    except Exception as e:
        logger.error(f"Error reading CSV: {str(e)}")
        logger.error(traceback.format_exc())
        return {'accounts': 0, 'total_processed': start_row}

def import_images(batch_size=20, commit_every=10):
    """
    Import property images data incrementally.
    
    Args:
        batch_size: Number of records to process in this run
        commit_every: Number of records to process before committing
        
    Returns:
        Dictionary with count of images created
    """
    data_type = 'images'
    start_time = time.time()
    csv_path = os.path.join('attached_assets', CSV_FILES[data_type])
    
    # Get current position in file
    start_row = get_last_position(data_type)
    logger.info(f"Incremental import of {data_type} from {csv_path} starting at row {start_row+1}")
    logger.info(f"Parameters: batch_size={batch_size}, commit_every={commit_every}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return {'images': 0, 'total_processed': start_row}
    
    # Check if we've reached the end of the file
    try:
        with open(csv_path, 'r', encoding='latin1') as f:
            total_rows = sum(1 for _ in f) - 1  # Subtract header row
        
        if start_row >= total_rows:
            logger.info(f"Already processed all {total_rows} rows of {data_type}, nothing to do")
            return {'images': 0, 'total_processed': start_row}
            
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
            logger.info(f"No more rows to read from {data_type}")
            return {'images': 0, 'total_processed': start_row}
            
        logger.info(f"Read {len(df)} rows from {csv_path}")
        
        # Convert column names to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Process the batch
        images_created = 0
        records_processed = 0
        
        try:
            with app.app_context():
                # Process each record
                for _, row in df.iterrows():
                    # The CSV has 'id', 'prop_id', 'year', 'image_path', 'image_nm', 'image_type'
                    image_id = str(row.get('id', ''))
                    property_id = str(row.get('prop_id', '')) if pd.notna(row.get('prop_id')) else None
                    
                    if not image_id or image_id == 'nan' or not property_id:
                        continue
                    
                    # Check if image already exists for this property and image type
                    existing_image = db.session.query(PropertyImage).filter(
                        PropertyImage.property_id == property_id,
                        PropertyImage.image_path.contains(str(row.get('image_nm', '')))
                    ).first()
                    
                    if not existing_image:
                        # Get image year and format as date if available
                        image_year = row.get('year') if pd.notna(row.get('year')) else None
                        image_date = None
                        if image_year:
                            try:
                                image_date = datetime.strptime(f"{int(image_year)}-01-01", "%Y-%m-%d").date()
                            except (ValueError, TypeError):
                                pass
                                
                        # Create a new property image
                        image = PropertyImage(
                            property_id=property_id,
                            image_path=str(row.get('image_path', '')) if pd.notna(row.get('image_path')) else None,
                            image_type=str(row.get('image_type', '')) if pd.notna(row.get('image_type')) else "Unknown",
                            image_date=image_date,
                            file_format=str(row.get('image_nm', '')).split('.')[-1] if pd.notna(row.get('image_nm')) else None
                        )
                        db.session.add(image)
                        images_created += 1
                    
                    # Increment counter and commit periodically
                    records_processed += 1
                    if records_processed % commit_every == 0:
                        db.session.commit()
                        logger.info(f"Committed {records_processed} records")
                
                # Final commit for any remaining records
                db.session.commit()
                
                # Update position
                new_position = start_row + records_processed
                save_position(data_type, new_position)
                
                total_time = time.time() - start_time
                logger.info(f"Batch complete: created {images_created} images in {total_time:.2f}s")
                logger.info(f"Position updated: {start_row} -> {new_position}")
                
                return {
                    'images': images_created,
                    'total_processed': new_position
                }
                
        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            logger.error(traceback.format_exc())
            try:
                db.session.rollback()
            except:
                pass
            return {'images': 0, 'total_processed': start_row}
    
    except Exception as e:
        logger.error(f"Error reading CSV: {str(e)}")
        logger.error(traceback.format_exc())
        return {'images': 0, 'total_processed': start_row}

def import_all_data(improvement_batch=10, account_batch=20, image_batch=20):
    """
    Import all types of data sequentially.
    
    Args:
        improvement_batch: Batch size for improvements
        account_batch: Batch size for accounts
        image_batch: Batch size for images
        
    Returns:
        Dictionary with counts of all data created
    """
    results = {
        'improvements': import_improvements(batch_size=improvement_batch),
        'accounts': import_accounts(batch_size=account_batch),
        'images': import_images(batch_size=image_batch)
    }
    
    return results

def reset_all_positions(clear_data=True):
    """Reset all import positions and optionally clear all data."""
    for data_type in POSITION_FILES:
        save_position(data_type, 0)
        logger.info(f"Reset {data_type} import position to 0")
    
    if clear_data:
        try:
            with app.app_context():
                db.session.query(PropertyImage).delete()
                db.session.query(Property).delete()
                db.session.query(Account).delete()
                db.session.query(Parcel).delete()
                db.session.commit()
                logger.info("Cleared all existing data")
        except Exception as e:
            logger.error(f"Failed to clear data: {str(e)}")

if __name__ == "__main__":
    with app.app_context():
        # Ensure tables exist
        create_tables()
        
        # Default parameters
        improvement_batch = 10
        account_batch = 20
        image_batch = 20
        import_type = 'all'  # Default to all
        
        # Parse command line arguments
        if len(sys.argv) > 1:
            import_type = sys.argv[1].lower()
            logger.info(f"Import type: {import_type}")
            
            if len(sys.argv) > 2:
                try:
                    if import_type == 'improvements':
                        improvement_batch = int(sys.argv[2])
                        logger.info(f"Using batch size: {improvement_batch} for improvements")
                    elif import_type == 'accounts':
                        account_batch = int(sys.argv[2])
                        logger.info(f"Using batch size: {account_batch} for accounts")
                    elif import_type == 'images':
                        image_batch = int(sys.argv[2])
                        logger.info(f"Using batch size: {image_batch} for images")
                    else:
                        # For 'all', use the value for all types
                        improvement_batch = account_batch = image_batch = int(sys.argv[2])
                        logger.info(f"Using batch size: {improvement_batch} for all data types")
                except ValueError:
                    pass
        
        # Check for reset command
        if import_type == 'reset':
            reset_all_positions(clear_data=True)
            logger.info("All import positions reset and data cleared")
            sys.exit(0)
        
        # Run the appropriate import
        if import_type == 'improvements':
            results = import_improvements(batch_size=improvement_batch)
            logger.info(f"Improvements import completed: {results}")
            if results['parcels'] > 0 or results['properties'] > 0:
                logger.info("SUCCESS: Improvements import worked correctly!")
            else:
                if results['total_processed'] > 0:
                    logger.info("No new records processed, may have reached the end of file")
                else:
                    logger.error("FAILED: Import did not create any records!")
        
        elif import_type == 'accounts':
            results = import_accounts(batch_size=account_batch)
            logger.info(f"Accounts import completed: {results}")
            if results['accounts'] > 0:
                logger.info("SUCCESS: Accounts import worked correctly!")
            else:
                if results['total_processed'] > 0:
                    logger.info("No new records processed, may have reached the end of file")
                else:
                    logger.error("FAILED: Import did not create any records!")
        
        elif import_type == 'images':
            results = import_images(batch_size=image_batch)
            logger.info(f"Images import completed: {results}")
            if results['images'] > 0:
                logger.info("SUCCESS: Images import worked correctly!")
            else:
                if results['total_processed'] > 0:
                    logger.info("No new records processed, may have reached the end of file")
                else:
                    logger.error("FAILED: Import did not create any records!")
        
        else:  # 'all' or any other value
            results = import_all_data(
                improvement_batch=improvement_batch,
                account_batch=account_batch,
                image_batch=image_batch
            )
            logger.info(f"All imports completed: {results}")
            
            # Check success for each type
            success = False
            
            if (results['improvements']['parcels'] > 0 or 
                results['improvements']['properties'] > 0 or
                results['accounts']['accounts'] > 0 or
                results['images']['images'] > 0):
                logger.info("SUCCESS: At least one import worked correctly!")
                success = True
                
            if not success:
                # Check if all are at end of file
                if (results['improvements']['total_processed'] > 0 and
                   results['accounts']['total_processed'] > 0 and
                   results['images']['total_processed'] > 0):
                    logger.info("No new records processed, may have reached the end of all files")
                else:
                    logger.error("FAILED: No imports created any records!")