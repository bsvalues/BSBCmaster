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
        
        # Read and import the CSV file in chunks
        total_rows = 0
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
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
        
        # Read CSV in chunks
        total_rows = 0
        chunk_size = 5000
        
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
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
    Import property improvement data from the attached_assets directory.
    
    Args:
        filename: Name of the improvements CSV file
        
    Returns:
        Number of rows imported
    """
    csv_path = os.path.join('attached_assets', filename)
    return import_csv_to_db(csv_path, 'improvements')

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
        
        # Read CSV in chunks
        total_rows = 0
        chunk_size = 1000
        
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
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