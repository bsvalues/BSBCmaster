"""
Supabase Setup Testing Script

This script is used to test the setup of Supabase database schema and the ability 
to interact with the Supabase database through the client integration.
"""

import os
import logging
import sys
import json
import datetime
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Supabase client
from app.db.supabase_client import get_supabase_client, is_connected

def execute_schema_sql():
    """
    Execute the SQL schema script on Supabase.
    
    This will create all the necessary tables in the Supabase database.
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot execute schema SQL: Supabase client not initialized")
        return False
    
    try:
        # Read the schema SQL file
        schema_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'supabase_schema.sql')
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Break the SQL file into individual statements
        statements = schema_sql.split(';')
        executed_count = 0
        
        # Execute each statement
        for statement in statements:
            # Skip empty statements
            if not statement.strip() or statement.strip() == '':
                continue
            
            # Execute the statement
            logger.info(f"Executing SQL: {statement[:100]}...")
            try:
                # We need to use raw SQL execution through a stored procedure or RPC in Supabase
                # Let's use the rpc endpoint to execute SQL
                response = supabase.rpc('execute_sql', {'sql': statement}).execute()
                
                if hasattr(response, 'error') and response.error:
                    logger.error(f"Error executing SQL statement: {response.error}")
                    logger.error(f"Statement: {statement}")
                else:
                    executed_count += 1
                    logger.info("SQL executed successfully")
            except Exception as e:
                logger.error(f"Exception executing SQL statement: {str(e)}")
                logger.error(f"Statement: {statement}")
        
        logger.info(f"Executed {executed_count} SQL statements")
        return True
        
    except Exception as e:
        logger.error(f"Exception executing schema SQL: {str(e)}")
        return False

def test_create_user():
    """Test creating a user in Supabase."""
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot test create user: Supabase client not initialized")
        return False
    
    try:
        # Create a test user using the auth API
        from app.auth.supabase_auth import signup_user
        
        # Generate unique username and email
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        username = f"testuser_{timestamp}"
        email = f"test_{timestamp}@example.com"
        password = f"Test123_{timestamp}"
        
        success, message, user_data = signup_user(
            username=username,
            email=email,
            password=password,
            full_name="Test User",
            roles=["user"]
        )
        
        if success:
            logger.info(f"User created successfully: {message}")
            logger.info(f"User data: {json.dumps(user_data, indent=2)}")
            return True
        else:
            logger.error(f"Failed to create user: {message}")
            return False
            
    except Exception as e:
        logger.error(f"Exception testing create user: {str(e)}")
        return False

def test_crud_operations():
    """Test CRUD operations on Supabase tables."""
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot test CRUD operations: Supabase client not initialized")
        return False
    
    try:
        # Test creating a parcel
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        parcel_id = f"test_parcel_{timestamp}"
        parcel_data = {
            "parcel_id": parcel_id,
            "address": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "zip_code": "12345",
            "land_value": 100000,
            "improvement_value": 150000,
            "total_value": 250000,
            "assessment_year": 2024,
            "latitude": 47.6062,
            "longitude": -122.3321
        }
        
        # Insert parcel
        logger.info("Creating test parcel")
        response = supabase.table("parcels").insert(parcel_data).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error creating parcel: {response.error}")
            return False
        
        # Get the created parcel ID
        created_parcel = response.data[0] if response.data else None
        if not created_parcel:
            logger.error("Failed to get created parcel data")
            return False
        
        parcel_supabase_id = created_parcel.get('id')
        logger.info(f"Created parcel with ID: {parcel_supabase_id}")
        
        # Test reading the parcel
        logger.info("Reading test parcel")
        read_response = supabase.table("parcels").select("*").eq("id", parcel_supabase_id).execute()
        
        if hasattr(read_response, 'error') and read_response.error:
            logger.error(f"Error reading parcel: {read_response.error}")
            return False
        
        read_parcel = read_response.data[0] if read_response.data else None
        if not read_parcel:
            logger.error("Failed to read created parcel")
            return False
        
        logger.info(f"Read parcel: {json.dumps(read_parcel, indent=2)}")
        
        # Test updating the parcel
        logger.info("Updating test parcel")
        update_data = {
            "address": "456 Updated St",
            "total_value": 300000
        }
        
        update_response = supabase.table("parcels").update(update_data).eq("id", parcel_supabase_id).execute()
        
        if hasattr(update_response, 'error') and update_response.error:
            logger.error(f"Error updating parcel: {update_response.error}")
            return False
        
        updated_parcel = update_response.data[0] if update_response.data else None
        if not updated_parcel:
            logger.error("Failed to get updated parcel data")
            return False
        
        logger.info(f"Updated parcel: {json.dumps(updated_parcel, indent=2)}")
        
        # Test creating a property related to the parcel
        logger.info("Creating test property")
        property_data = {
            "parcel_id": parcel_supabase_id,
            "property_type": "Residential",
            "year_built": 2000,
            "square_footage": 2000,
            "bedrooms": 3,
            "bathrooms": 2.5,
            "lot_size": 0.25,
            "lot_size_unit": "acres",
            "stories": 2,
            "condition": "Good",
            "quality": "Average",
            "tax_district": "Test District",
            "zoning": "R1"
        }
        
        property_response = supabase.table("properties").insert(property_data).execute()
        
        if hasattr(property_response, 'error') and property_response.error:
            logger.error(f"Error creating property: {property_response.error}")
            return False
        
        created_property = property_response.data[0] if property_response.data else None
        if not created_property:
            logger.error("Failed to get created property data")
            return False
        
        property_supabase_id = created_property.get('id')
        logger.info(f"Created property with ID: {property_supabase_id}")
        
        # Test deleting the property
        logger.info("Deleting test property")
        delete_property_response = supabase.table("properties").delete().eq("id", property_supabase_id).execute()
        
        if hasattr(delete_property_response, 'error') and delete_property_response.error:
            logger.error(f"Error deleting property: {delete_property_response.error}")
            return False
        
        logger.info("Property deleted successfully")
        
        # Test deleting the parcel
        logger.info("Deleting test parcel")
        delete_parcel_response = supabase.table("parcels").delete().eq("id", parcel_supabase_id).execute()
        
        if hasattr(delete_parcel_response, 'error') and delete_parcel_response.error:
            logger.error(f"Error deleting parcel: {delete_parcel_response.error}")
            return False
        
        logger.info("Parcel deleted successfully")
        
        logger.info("CRUD operations test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Exception testing CRUD operations: {str(e)}")
        return False

def main():
    """Main function to test Supabase setup."""
    logger.info("Testing Supabase setup")
    
    # Check Supabase connection
    if not is_connected():
        logger.error("Supabase client not initialized")
        return False
    
    logger.info("Supabase client initialized successfully")
    
    # Create account tables?
    create_tables = input("Do you want to create database tables in Supabase? (y/n): ")
    if create_tables.lower() == 'y':
        # Execute schema SQL
        logger.info("Executing schema SQL")
        if not execute_schema_sql():
            logger.error("Failed to execute schema SQL")
    
    # Test creating a user
    logger.info("Testing user creation")
    create_user = input("Do you want to test creating a user? (y/n): ")
    if create_user.lower() == 'y':
        if not test_create_user():
            logger.error("Failed to test creating a user")
    
    # Test CRUD operations
    logger.info("Testing CRUD operations")
    test_crud = input("Do you want to test CRUD operations? (y/n): ")
    if test_crud.lower() == 'y':
        if not test_crud_operations():
            logger.error("Failed to test CRUD operations")
    
    logger.info("Supabase setup testing completed")
    return True

if __name__ == "__main__":
    main()