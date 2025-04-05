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
    return import_csv_to_db(csv_path, 'accounts')

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
    return import_csv_to_db(csv_path, 'property_images')

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