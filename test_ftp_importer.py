"""
Test script for the FTP data importer.

This script tests the FTP data importer by importing data from sample CSV files
instead of connecting to the actual FTP server.
"""

import os
import logging
import tempfile
import shutil
import sys
from app_setup import db, app as flask_app
from app.ftp_data_importer import FTPDataImporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_files():
    """Create test directory with sample CSV files."""
    test_dir = tempfile.mkdtemp()
    
    # Create smaller test files
    account_data = """acct_id,file_as_name
1,"BENTON COUNTY"
2,"DEMO"
3,"ASIX"
14,"CRID #11"
18,"CRID #12"
19,"CRID 16"
20,"CRID 15"
25,"CRID 21"
501,"CITY OF BENTON CITY"
502,"CITY OF KENNEWICK"
"""
    
    images_data = """id,prop_id,year,image_path,image_nm,image_type
1,10855,2016,"\\ProVal\\0184\\10855a.jpg",10855a.jpg,PIC
2,10856,2016,"\\ProVal\\0184\\10856.jpg",10856.jpg,PIC
3,10856,2016,"\\ProVal\\0184\\10856a.jpg",10856a.jpg,PIC
4,10857,2016,"\\ProVal\\0184\\10857.jpg",10857.jpg,PIC
5,10857,2016,"\\ProVal\\0184\\10857a.jpg",10857a.jpg,PIC
"""
    
    # Write the smaller files
    with open(os.path.join(test_dir, 'account.csv'), 'w') as f:
        f.write(account_data)
    logger.info(f"Created test account data in {os.path.join(test_dir, 'account.csv')}")
    
    with open(os.path.join(test_dir, 'images.csv'), 'w') as f:
        f.write(images_data)
    logger.info(f"Created test images data in {os.path.join(test_dir, 'images.csv')}")
            
    return test_dir

class MockFTPImporter(FTPDataImporter):
    """Mock FTP importer that uses local files instead of FTP connection."""
    
    def __init__(self, test_dir):
        """
        Initialize with the test directory.
        
        Args:
            test_dir: Directory containing test files
        """
        super().__init__("dummy_host", "dummy_user", "dummy_password")
        self.test_dir = test_dir
        
    def connect(self):
        """
        Mock connection that returns a simple object instead of a real FTP connection.
        
        We need to return something that's not None to match the parent class's return type.
        """
        class MockFTP:
            def quit(self):
                pass
            def nlst(self):
                return ['account.csv', 'images.csv']
                
        logger.info("Mock FTP connection established")
        return MockFTP()
        
    def list_files(self):
        """List files in the test directory."""
        files = os.listdir(self.test_dir)
        logger.info(f"Found {len(files)} files in test directory: {files}")
        return files
        
    def download_file(self, remote_filename, local_filename=None):
        """
        Copy the file from the test directory instead of downloading.
        
        Args:
            remote_filename: Name of the file in the test directory
            local_filename: Name to save the file as
            
        Returns:
            Path to the copied file
        """
        source_path = os.path.join(self.test_dir, remote_filename)
        
        if local_filename is None:
            local_filename = os.path.join(tempfile.gettempdir(), remote_filename)
            
        if os.path.exists(source_path):
            shutil.copy(source_path, local_filename)
            logger.info(f"Copied {source_path} to {local_filename}")
            return local_filename
        else:
            logger.error(f"Source file {source_path} not found")
            raise FileNotFoundError(f"File {remote_filename} not found in test directory")

def test_import():
    """Test the FTP data importer with local files."""
    try:
        # Create test directory and files
        test_dir = create_test_files()
        logger.info(f"Created test directory: {test_dir}")
        
        # Create mock importer
        importer = MockFTPImporter(test_dir)
        
        # Run import within Flask application context
        with flask_app.app_context():
            # Import data
            results = importer.import_all_data()
            
            # Log results
            for data_type, count in results.items():
                logger.info(f"Imported {count} {data_type} records")
                
            # Verify import results
            if results.get('accounts', 0) > 0 and results.get('property_images', 0) > 0:
                logger.info("Test successful: Both account and property image data imported successfully")
            else:
                logger.error(f"Test failed: Import returned unexpected results: {results}")
                
        # Clean up test directory
        shutil.rmtree(test_dir)
        logger.info(f"Cleaned up test directory: {test_dir}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    results = test_import()
    
    # Exit with success code if import was successful
    if isinstance(results, dict) and "error" not in results:
        logger.info("FTP import test completed successfully")
        sys.exit(0)
    else:
        logger.error("FTP import test failed")
        sys.exit(1)