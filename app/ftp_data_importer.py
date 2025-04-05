"""
FTP Data Importer for MCP Assessor Agent API

This module provides functionality to import property assessment data from an FTP server.
It handles connecting to the FTP server, downloading files, and importing them into the database.
"""

import os
import ftplib
import logging
import tempfile
import csv
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from sqlalchemy import text
from app_setup import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FTPDataImporter:
    """Class to handle importing data from the FTP server."""
    
    def __init__(self, ftp_host: str, ftp_user: str, ftp_password: str, ftp_directory: str = '/'):
        """
        Initialize the FTP data importer.
        
        Args:
            ftp_host: FTP server hostname
            ftp_user: FTP username
            ftp_password: FTP password
            ftp_directory: Base directory on the FTP server
        """
        self.ftp_host = ftp_host
        self.ftp_user = ftp_user
        self.ftp_password = ftp_password
        self.ftp_directory = ftp_directory
        
    def connect(self) -> Any:
        """
        Connect to the FTP server.
        
        Returns:
            FTP connection object
        """
        try:
            # Connect to FTP server
            ftp = ftplib.FTP(self.ftp_host)
            ftp.login(user=self.ftp_user, passwd=self.ftp_password)
            
            # Change to the specified directory if needed
            if self.ftp_directory and self.ftp_directory != '/':
                ftp.cwd(self.ftp_directory)
                
            logger.info(f"Connected to FTP server: {self.ftp_host}")
            return ftp
            
        except ftplib.all_errors as e:
            logger.error(f"FTP connection error: {str(e)}")
            raise
            
    def list_files(self) -> List[str]:
        """
        List files available on the FTP server.
        
        Returns:
            List of filenames
        """
        try:
            ftp = self.connect()
            files = ftp.nlst()
            ftp.quit()
            
            logger.info(f"Found {len(files)} files on FTP server")
            return files
            
        except ftplib.all_errors as e:
            logger.error(f"Error listing FTP files: {str(e)}")
            raise
    
    def download_file(self, remote_filename: str, local_filename: Optional[str] = None) -> str:
        """
        Download a file from the FTP server.
        
        Args:
            remote_filename: Name of the file on the FTP server
            local_filename: Name to save the file as locally
            
        Returns:
            Path to the downloaded file
        """
        try:
            # If no local filename provided, use the remote filename
            if local_filename is None:
                local_filename = os.path.join(tempfile.gettempdir(), remote_filename)
                
            # Connect to FTP server
            ftp = self.connect()
            
            # Download the file
            with open(local_filename, 'wb') as local_file:
                ftp.retrbinary(f"RETR {remote_filename}", local_file.write)
                
            ftp.quit()
            
            logger.info(f"Downloaded {remote_filename} to {local_filename}")
            return local_filename
            
        except ftplib.all_errors as e:
            logger.error(f"Error downloading file {remote_filename}: {str(e)}")
            raise
    
    def import_csv_to_db(self, csv_path: str, table_name: str, 
                       chunk_size: int = 5000, if_exists: str = 'replace') -> int:
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
        try:
            # Read CSV file in chunks and import into database
            total_rows = 0
            
            for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
                # Convert column names to lowercase
                chunk.columns = [col.lower() for col in chunk.columns]
                
                # Replace spaces with underscores in column names
                chunk.columns = [col.replace(' ', '_') for col in chunk.columns]
                
                # Insert chunk into database
                chunk.to_sql(
                    name=table_name,
                    con=db.engine,
                    if_exists='replace' if total_rows == 0 and if_exists == 'replace' else 'append',
                    index=False
                )
                
                total_rows += len(chunk)
                logger.info(f"Imported {len(chunk)} rows into {table_name} (total: {total_rows})")
                
            logger.info(f"Completed import of {total_rows} rows into {table_name}")
            return total_rows
            
        except Exception as e:
            logger.error(f"Error importing CSV file {csv_path} to table {table_name}: {str(e)}")
            raise
    
    def import_account_data(self, filename: str = 'account.csv') -> int:
        """
        Import account data from the FTP server.
        
        Args:
            filename: Name of the account CSV file on the FTP server
            
        Returns:
            Number of rows imported
        """
        try:
            # Download the file
            local_path = self.download_file(filename)
            
            # Import the data
            rows_imported = self.import_csv_to_db(
                csv_path=local_path,
                table_name='accounts',
                if_exists='replace'
            )
            
            # Clean up temporary file
            os.remove(local_path)
            
            return rows_imported
            
        except Exception as e:
            logger.error(f"Error importing account data: {str(e)}")
            raise
    
    def import_images_data(self, filename: str = 'images.csv') -> int:
        """
        Import property images data from the FTP server.
        
        Args:
            filename: Name of the images CSV file on the FTP server
            
        Returns:
            Number of rows imported
        """
        try:
            # Download the file
            local_path = self.download_file(filename)
            
            # Import the data
            rows_imported = self.import_csv_to_db(
                csv_path=local_path,
                table_name='property_images',
                if_exists='replace'
            )
            
            # Clean up temporary file
            os.remove(local_path)
            
            return rows_imported
            
        except Exception as e:
            logger.error(f"Error importing property images data: {str(e)}")
            raise
    
    def import_all_data(self) -> Dict[str, int]:
        """
        Import all available data from the FTP server.
        
        Returns:
            Dictionary mapping data types to row counts
        """
        results = {}
        
        try:
            # Import account data
            results['accounts'] = self.import_account_data('account.csv')
        except Exception as e:
            logger.error(f"Failed to import account data: {str(e)}")
            results['accounts'] = 0
            
        try:
            # Import property images data
            results['property_images'] = self.import_images_data('images.csv')
        except Exception as e:
            logger.error(f"Failed to import property images data: {str(e)}")
            results['property_images'] = 0
            
        # Additional data types can be added here as needed
            
        return results

def import_ftp_data(ftp_host: str, ftp_user: str, ftp_password: str, 
                    ftp_directory: str = '/') -> Dict[str, int]:
    """
    Helper function to import data from the FTP server.
    
    Args:
        ftp_host: FTP server hostname
        ftp_user: FTP username
        ftp_password: FTP password
        ftp_directory: Base directory on the FTP server
        
    Returns:
        Dictionary mapping data types to row counts
    """
    importer = FTPDataImporter(ftp_host, ftp_user, ftp_password, ftp_directory)
    return importer.import_all_data()