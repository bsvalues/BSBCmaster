"""
Import Property Images from Attached Assets

This script only imports the property images data from the attached_assets directory
to fix export functionality. It's a focused version of import_attached_data.py.
"""

import os
import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from app_setup import app, db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        # Read a sample of the CSV to check columns
        sample = pd.read_csv(csv_path, nrows=5)
        logger.info(f"CSV columns: {sample.columns.tolist()}")
        
        # Read a smaller subset for testing
        # Adjust the limit as needed
        total_rows = 0
        chunk_size = 1000
        max_rows = 1000  # Limit to 1000 rows for initial testing
        
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
            
            # Make sure property_id is always set
            if 'property_id' not in mapped_chunk.columns:
                if 'account_id' in mapped_chunk.columns:
                    mapped_chunk['property_id'] = mapped_chunk['account_id']
                else:
                    # Generate a placeholder property_id if needed
                    mapped_chunk['property_id'] = [f"img_{i}" for i in range(len(chunk))]
            
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
            
            # Break after importing max_rows
            if total_rows >= max_rows:
                logger.info(f"Reached max rows limit ({max_rows})")
                break
        
        logger.info(f"Successfully imported {total_rows} rows from {csv_path} to property_images")
        return total_rows
    
    except Exception as e:
        logger.error(f"Error importing {csv_path}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

if __name__ == "__main__":
    """Main entry point for the script."""
    with app.app_context():
        result = import_images_data()
        logger.info(f"Import result: {result} rows")