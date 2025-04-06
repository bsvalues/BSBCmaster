"""
Import Property Assessment Data from Attached Assets

This script imports property assessment data from the attached_assets directory
into the MCP Assessor Agent API database. It handles importing CSV files and
setting up the necessary database tables.
"""

import os
import sys
import logging
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text
from app_setup import app, db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_csv_to_db(csv_path, table_name, chunk_size=5000, if_exists='replace'):
    """
    Import a CSV file into the database.
    
    Args:
        csv_path: Path to the CSV file
        table_name: Name of the database table to import into
        chunk_size: Number of rows to process at a time
        if_exists: What to do if the table exists ('replace', 'append', 'fail')
        
    Returns:
        Number of rows imported
    """
    logger.info(f"Importing {csv_path} to {table_name} table")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return 0
    
    try:
        # Get the database URL from the Flask app config
        database_url = app.config['SQLALCHEMY_DATABASE_URI']
        
        # Create a SQLAlchemy engine
        engine = create_engine(database_url)
        
        # Try different encodings for the CSV file
        encodings = ['utf-8', 'latin1', 'cp1252', 'ISO-8859-1']
        successful_encoding = None
        
        for encoding in encodings:
            try:
                # Try to read the first few rows to test the encoding
                test_df = pd.read_csv(csv_path, nrows=5, encoding=encoding)
                successful_encoding = encoding
                logger.info(f"Successfully read CSV with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                logger.warning(f"Failed to read CSV with encoding: {encoding}")
        
        if successful_encoding is None:
            logger.error("Failed to read CSV with any of the attempted encodings")
            return 0
            
        # Read and import the CSV file in chunks
        total_rows = 0
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size, encoding=successful_encoding):
            # Convert column names to lowercase
            chunk.columns = [col.lower() for col in chunk.columns]
            
            # Write the chunk to the database
            chunk.to_sql(
                name=table_name,
                con=engine,
                if_exists='append' if total_rows > 0 else if_exists,
                index=False
            )
            
            total_rows += len(chunk)
            logger.info(f"Imported {total_rows} rows to {table_name}")
        
        logger.info(f"Successfully imported {total_rows} rows from {csv_path} to {table_name}")
        return total_rows
    
    except Exception as e:
        logger.error(f"Error importing {csv_path}: {str(e)}")
        return 0

def import_account_data(filename='account.csv'):
    """
    Import account data from the attached_assets directory.
    
    Args:
        filename: Name of the account CSV file
        
    Returns:
        Number of rows imported
    """
    csv_path = os.path.join('attached_assets', filename)
    
    try:
        # Get the database URL from the Flask app config
        database_url = app.config['SQLALCHEMY_DATABASE_URI']
        
        # Create a SQLAlchemy engine
        engine = create_engine(database_url)
        
        # Empty the accounts table first
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE accounts RESTART IDENTITY"))
            conn.commit()
        
        # Read the CSV file
        logger.info(f"Importing {csv_path} to accounts table")
        
        if not os.path.exists(csv_path):
            logger.error(f"File not found: {csv_path}")
            return 0
        
        # Try different encodings for the CSV file
        encodings = ['utf-8', 'latin1', 'cp1252', 'ISO-8859-1']
        successful_encoding = None
        
        for encoding in encodings:
            try:
                # Try to read the first few rows to test the encoding
                test_df = pd.read_csv(csv_path, nrows=5, encoding=encoding)
                successful_encoding = encoding
                logger.info(f"Successfully read CSV with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                logger.warning(f"Failed to read CSV with encoding: {encoding}")
        
        if successful_encoding is None:
            logger.error("Failed to read CSV with any of the attempted encodings")
            return 0
            
        # Read CSV in chunks
        total_rows = 0
        chunk_size = 5000
        
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size, encoding=successful_encoding):
            # Convert column names to lowercase
            chunk.columns = [col.lower() for col in chunk.columns]
            
            # Map the CSV columns to our model columns
            # We'll use acct_id as account_id and file_as_name as owner_name
            mapped_chunk = pd.DataFrame()
            
            if 'acct_id' in chunk.columns:
                mapped_chunk['account_id'] = chunk['acct_id'].astype(str)
            
            if 'file_as_name' in chunk.columns:
                mapped_chunk['owner_name'] = chunk['file_as_name']
                
            # Add other columns from the CSV if they exist
            for col in chunk.columns:
                if col not in ['acct_id', 'file_as_name']:
                    mapped_chunk[col] = chunk[col]
            
            # Add current timestamp
            mapped_chunk['created_at'] = datetime.utcnow()
            mapped_chunk['updated_at'] = datetime.utcnow()
            
            # Write the chunk to the database
            mapped_chunk.to_sql(
                name='accounts',
                con=engine,
                if_exists='append',
                index=False
            )
            
            total_rows += len(chunk)
            logger.info(f"Imported {total_rows} rows to accounts")
        
        logger.info(f"Successfully imported {total_rows} rows from {csv_path} to accounts")
        return total_rows
    
    except Exception as e:
        logger.error(f"Error importing {csv_path}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def import_improvement_data(filename='ftp_dl_imprv.csv'):
    """
    Import property improvement data from the attached_assets directory
    and create corresponding Parcel and Property records.
    
    Args:
        filename: Name of the improvements CSV file
        
    Returns:
        Dictionary with counts of parcels and properties created
    """
    from models import Parcel, Property
    
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
            # Process each row and create corresponding records
            for _, row in df.iterrows():
                prop_id = str(row.get('prop_id', ''))
                imprv_id = str(row.get('imprv_id', ''))
                imprv_desc = row.get('imprv_desc', '')
                imprv_val = row.get('imprv_val', 0)
                living_area = row.get('living_area', None)
                primary_use_cd = row.get('primary_use_cd', '')
                stories = row.get('stories', None)
                actual_year_built = row.get('actual_year_built', None)
                
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
                
                # Update parcel improvement value
                parcel = db.session.query(Parcel).filter_by(id=created_parcels[prop_id]).first()
                if parcel and imprv_val:
                    try:
                        imprv_val_float = float(imprv_val)
                        parcel.improvement_value += imprv_val_float
                        parcel.total_value += imprv_val_float
                    except (ValueError, TypeError):
                        pass
            
            # Commit all changes
            db.session.commit()
            
            logger.info(f"Created {len(created_parcels)} parcels and {created_properties} properties")
            return {'parcels': len(created_parcels), 'properties': created_properties}
    
    except Exception as e:
        logger.error(f"Error importing improvements: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {'parcels': 0, 'properties': 0}

def import_images_data(filename='images.csv'):
    """
    Import property images data from the attached_assets directory.
    
    Args:
        filename: Name of the images CSV file
        
    Returns:
        Number of rows imported
    """
    csv_path = os.path.join('attached_assets', filename)
    
    try:
        # Get the database URL from the Flask app config
        database_url = app.config['SQLALCHEMY_DATABASE_URI']
        
        # Create a SQLAlchemy engine
        engine = create_engine(database_url)
        
        # Empty the property_images table first
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE property_images RESTART IDENTITY"))
            conn.commit()
        
        # Read the CSV file
        logger.info(f"Importing {csv_path} to property_images table")
        
        if not os.path.exists(csv_path):
            logger.error(f"File not found: {csv_path}")
            return 0
        
        # Try different encodings for the CSV file
        encodings = ['utf-8', 'latin1', 'cp1252', 'ISO-8859-1']
        successful_encoding = None
        
        for encoding in encodings:
            try:
                # Try to read the first few rows to test the encoding
                test_df = pd.read_csv(csv_path, nrows=5, encoding=encoding)
                successful_encoding = encoding
                logger.info(f"Successfully read CSV with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                logger.warning(f"Failed to read CSV with encoding: {encoding}")
        
        if successful_encoding is None:
            logger.error("Failed to read CSV with any of the attempted encodings")
            return 0
            
        # Read CSV in chunks
        total_rows = 0
        chunk_size = 1000
        
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size, encoding=successful_encoding):
            # Convert column names to lowercase
            chunk.columns = [col.lower() for col in chunk.columns]
            
            # Map the CSV columns to our model columns
            mapped_chunk = pd.DataFrame()
            
            # Map common column names to our model
            column_mapping = {
                'property_id': 'property_id',
                'acct_id': 'account_id',
                'image_url': 'image_url',
                'image_path': 'image_path',
                'image_type': 'image_type',
                'image_date': 'image_date',
                'width': 'width',
                'height': 'height',
                'file_size': 'file_size',
                'file_format': 'file_format'
            }
            
            # Apply mapping for columns that exist
            for csv_col, model_col in column_mapping.items():
                if csv_col in chunk.columns:
                    mapped_chunk[model_col] = chunk[csv_col]
                    if csv_col == 'acct_id':
                        mapped_chunk[model_col] = mapped_chunk[model_col].astype(str)
            
            # Add any other columns from the CSV
            for col in chunk.columns:
                if col not in column_mapping.keys() and col not in mapped_chunk.columns:
                    mapped_chunk[col] = chunk[col]
            
            # Make sure property_id is always set
            if 'property_id' not in mapped_chunk.columns and 'acct_id' in mapped_chunk.columns:
                mapped_chunk['property_id'] = mapped_chunk['account_id']
            
            # Add current timestamp
            mapped_chunk['created_at'] = datetime.utcnow()
            mapped_chunk['updated_at'] = datetime.utcnow()
            
            # Write the chunk to the database
            mapped_chunk.to_sql(
                name='property_images',
                con=engine,
                if_exists='append',
                index=False
            )
            
            total_rows += len(chunk)
            logger.info(f"Imported {total_rows} rows to property_images")
        
        logger.info(f"Successfully imported {total_rows} rows from {csv_path} to property_images")
        return total_rows
    
    except Exception as e:
        logger.error(f"Error importing {csv_path}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def import_all_data():
    """
    Import all available data from the attached_assets directory.
    
    Returns:
        Dictionary mapping data types to row counts
    """
    with app.app_context():
        results = {
            'accounts': import_account_data(),
            'ftp_accounts': import_account_data(filename='ftp_dl_account.csv'),
            'improvements': import_improvement_data(),
            'property_images': import_images_data()
        }
        
        logger.info(f"Import results: {results}")
        return results

if __name__ == "__main__":
    """Main entry point for the script."""
    import_all_data()