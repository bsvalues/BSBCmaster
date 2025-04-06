"""
Validate the Improvements CSV File

This script reads and validates the improvements CSV file without importing it to the database.
"""

import os
import logging
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_csv(filename='ftp_dl_imprv.csv', sample_size=100):
    """
    Validate the improvements CSV file.
    
    Args:
        filename: Name of the improvements CSV file
        sample_size: Number of records to validate
        
    Returns:
        Dictionary with validation results
    """
    csv_path = os.path.join('attached_assets', filename)
    logger.info(f"Validating {sample_size} rows from {csv_path}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return {'valid': False, 'error': 'File not found'}
    
    try:
        # Use Latin1 encoding directly 
        df = pd.read_csv(csv_path, encoding='latin1', nrows=sample_size)
        logger.info(f"Read {len(df)} rows from {csv_path}")
        
        # Convert column names to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Get all column names
        columns = list(df.columns)
        logger.info(f"Columns: {columns}")
        
        # Check for required columns
        required_columns = ['prop_id', 'imprv_id', 'imprv_desc', 'imprv_val']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            logger.warning(f"Missing required columns: {missing_columns}")
        
        # Sample data
        sample_data = []
        for i, row in df.head(10).iterrows():
            sample_row = {}
            for col in columns:
                sample_row[col] = row.get(col, '')
            sample_data.append(sample_row)
            
        logger.info(f"Sample data: {sample_data}")
        
        # Validate numeric values
        numeric_issues = []
        numeric_columns = ['imprv_val', 'living_area', 'stories', 'actual_year_built']
        
        for col in numeric_columns:
            if col in columns:
                non_numeric = df[~pd.to_numeric(df[col], errors='coerce').notna()][col].count()
                if non_numeric > 0:
                    numeric_issues.append(f"{col}: {non_numeric} non-numeric values")
        
        if numeric_issues:
            logger.warning(f"Numeric validation issues: {numeric_issues}")
        
        return {
            'valid': True,
            'row_count': len(df),
            'columns': columns,
            'missing_columns': missing_columns,
            'numeric_issues': numeric_issues,
            'sample_data': sample_data
        }
        
    except Exception as e:
        logger.error(f"Error validating CSV: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {'valid': False, 'error': str(e)}

if __name__ == "__main__":
    # Validate the CSV
    results = validate_csv(sample_size=100)
    logger.info(f"Validation results: {results['valid']}")
    
    if 'valid' in results and results['valid']:
        logger.info(f"CSV is valid with {results['row_count']} rows")
        if 'missing_columns' in results and results['missing_columns']:
            logger.warning(f"Missing columns: {results['missing_columns']}")
        if 'numeric_issues' in results and results['numeric_issues']:
            logger.warning(f"Numeric issues: {results['numeric_issues']}")
    else:
        logger.error(f"CSV validation failed: {results.get('error', 'Unknown error')}")