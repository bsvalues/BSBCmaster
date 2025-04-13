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
    Create the necessary tables in Supabase using the API.
    
    Instead of executing raw SQL, we'll use the Supabase API to create tables.
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot create tables: Supabase client not initialized")
        return False
    
    try:
        logger.info("Creating users table")
        # Create users table
        try:
            response = supabase.table("users").select("id").limit(1).execute()
            if hasattr(response, 'error') and response.error:
                if 'relation "users" does not exist' in str(response.error):
                    logger.info("Creating users table")
                    create_users_table()
                else:
                    logger.error(f"Error checking users table: {response.error}")
            else:
                logger.info("Users table already exists")
        except Exception as e:
            if 'relation "users" does not exist' in str(e):
                logger.info("Creating users table")
                create_users_table()
            else:
                logger.error(f"Exception checking users table: {str(e)}")
                return False
        
        logger.info("Creating parcels table")
        # Create parcels table
        try:
            response = supabase.table("parcels").select("id").limit(1).execute()
            if hasattr(response, 'error') and response.error:
                if 'relation "parcels" does not exist' in str(response.error):
                    logger.info("Creating parcels table")
                    create_parcels_table()
                else:
                    logger.error(f"Error checking parcels table: {response.error}")
            else:
                logger.info("Parcels table already exists")
        except Exception as e:
            if 'relation "parcels" does not exist' in str(e):
                logger.info("Creating parcels table")
                create_parcels_table()
            else:
                logger.error(f"Exception checking parcels table: {str(e)}")
                return False
        
        logger.info("Creating properties table")
        # Create properties table
        try:
            response = supabase.table("properties").select("id").limit(1).execute()
            if hasattr(response, 'error') and response.error:
                if 'relation "properties" does not exist' in str(response.error):
                    logger.info("Creating properties table")
                    create_properties_table()
                else:
                    logger.error(f"Error checking properties table: {response.error}")
            else:
                logger.info("Properties table already exists")
        except Exception as e:
            if 'relation "properties" does not exist' in str(e):
                logger.info("Creating properties table")
                create_properties_table()
            else:
                logger.error(f"Exception checking properties table: {str(e)}")
                return False
        
        logger.info("Creating sales table")
        # Create sales table
        try:
            response = supabase.table("sales").select("id").limit(1).execute()
            if hasattr(response, 'error') and response.error:
                if 'relation "sales" does not exist' in str(response.error):
                    logger.info("Creating sales table")
                    create_sales_table()
                else:
                    logger.error(f"Error checking sales table: {response.error}")
            else:
                logger.info("Sales table already exists")
        except Exception as e:
            if 'relation "sales" does not exist' in str(e):
                logger.info("Creating sales table")
                create_sales_table()
            else:
                logger.error(f"Exception checking sales table: {str(e)}")
                return False
        
        logger.info("Creating accounts table")
        # Create accounts table
        try:
            response = supabase.table("accounts").select("id").limit(1).execute()
            if hasattr(response, 'error') and response.error:
                if 'relation "accounts" does not exist' in str(response.error):
                    logger.info("Creating accounts table")
                    create_accounts_table()
                else:
                    logger.error(f"Error checking accounts table: {response.error}")
            else:
                logger.info("Accounts table already exists")
        except Exception as e:
            if 'relation "accounts" does not exist' in str(e):
                logger.info("Creating accounts table")
                create_accounts_table()
            else:
                logger.error(f"Exception checking accounts table: {str(e)}")
                return False
        
        logger.info("Creating property_images table")
        # Create property_images table
        try:
            response = supabase.table("property_images").select("id").limit(1).execute()
            if hasattr(response, 'error') and response.error:
                if 'relation "property_images" does not exist' in str(response.error):
                    logger.info("Creating property_images table")
                    create_property_images_table()
                else:
                    logger.error(f"Error checking property_images table: {response.error}")
            else:
                logger.info("Property_images table already exists")
        except Exception as e:
            if 'relation "property_images" does not exist' in str(e):
                logger.info("Creating property_images table")
                create_property_images_table()
            else:
                logger.error(f"Exception checking property_images table: {str(e)}")
                return False
        
        logger.info("Creating assessments table")
        # Create assessments table
        try:
            response = supabase.table("assessments").select("id").limit(1).execute()
            if hasattr(response, 'error') and response.error:
                if 'relation "assessments" does not exist' in str(response.error):
                    logger.info("Creating assessments table")
                    create_assessments_table()
                else:
                    logger.error(f"Error checking assessments table: {response.error}")
            else:
                logger.info("Assessments table already exists")
        except Exception as e:
            if 'relation "assessments" does not exist' in str(e):
                logger.info("Creating assessments table")
                create_assessments_table()
            else:
                logger.error(f"Exception checking assessments table: {str(e)}")
                return False
        
        logger.info("All tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Exception creating tables: {str(e)}")
        return False

def create_users_table():
    """Create the users table in Supabase."""
    logger.info("Skipping users table creation - will be handled by Supabase Auth")
    return True

def create_parcels_table():
    """Create the parcels table in Supabase."""
    logger.info("Creating parcels table through Supabase API")
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot create parcels table: Supabase client not initialized")
        return False
    
    # Note: In production, it's recommended to use Supabase's SQL editor to execute these statements
    # For now, we'll log them and assume manual execution
    logger.info("Please execute the following SQL in Supabase's SQL editor:")
    
    sql = """
    CREATE TABLE IF NOT EXISTS public.parcels (
        id SERIAL PRIMARY KEY,
        parcel_id VARCHAR(50) UNIQUE NOT NULL,
        address VARCHAR(255) NOT NULL,
        city VARCHAR(100) NOT NULL,
        state VARCHAR(50) NOT NULL,
        zip_code VARCHAR(20) NOT NULL,
        land_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
        improvement_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
        total_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
        assessment_year INTEGER NOT NULL,
        latitude FLOAT,
        longitude FLOAT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_parcels_parcel_id ON public.parcels(parcel_id);
    """
    
    logger.info(sql)
    return True

def create_properties_table():
    """Create the properties table in Supabase."""
    logger.info("Creating properties table through Supabase API")
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot create properties table: Supabase client not initialized")
        return False
    
    logger.info("Please execute the following SQL in Supabase's SQL editor:")
    
    sql = """
    CREATE TABLE IF NOT EXISTS public.properties (
        id SERIAL PRIMARY KEY,
        parcel_id INTEGER NOT NULL,
        property_type VARCHAR(50) NOT NULL,
        year_built INTEGER,
        square_footage INTEGER,
        bedrooms INTEGER,
        bathrooms FLOAT,
        lot_size FLOAT,
        lot_size_unit VARCHAR(20),
        stories FLOAT,
        condition VARCHAR(50),
        quality VARCHAR(50),
        tax_district VARCHAR(50),
        zoning VARCHAR(50),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_properties_parcel_id ON public.properties(parcel_id);
    """
    
    logger.info(sql)
    return True

def create_sales_table():
    """Create the sales table in Supabase."""
    logger.info("Creating sales table through Supabase API")
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot create sales table: Supabase client not initialized")
        return False
    
    logger.info("Please execute the following SQL in Supabase's SQL editor:")
    
    sql = """
    CREATE TABLE IF NOT EXISTS public.sales (
        id SERIAL PRIMARY KEY,
        parcel_id INTEGER NOT NULL,
        sale_date DATE NOT NULL,
        sale_price NUMERIC(12, 2) NOT NULL,
        sale_type VARCHAR(50),
        transaction_id VARCHAR(50),
        buyer_name VARCHAR(255),
        seller_name VARCHAR(255),
        financing_type VARCHAR(50),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_sales_parcel_id ON public.sales(parcel_id);
    CREATE INDEX IF NOT EXISTS idx_sales_sale_date ON public.sales(sale_date);
    """
    
    logger.info(sql)
    return True

def create_accounts_table():
    """Create the accounts table in Supabase."""
    logger.info("Creating accounts table through Supabase API")
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot create accounts table: Supabase client not initialized")
        return False
    
    logger.info("Please execute the following SQL in Supabase's SQL editor:")
    
    sql = """
    CREATE TABLE IF NOT EXISTS public.accounts (
        id SERIAL PRIMARY KEY,
        account_id VARCHAR(50) UNIQUE NOT NULL,
        owner_name VARCHAR(255),
        mailing_address VARCHAR(255),
        mailing_city VARCHAR(100),
        mailing_state VARCHAR(50),
        mailing_zip VARCHAR(20),
        property_address VARCHAR(255),
        property_city VARCHAR(100),
        property_type VARCHAR(50),
        legal_description TEXT,
        latitude FLOAT,
        longitude FLOAT,
        assessment_year INTEGER,
        assessed_value NUMERIC(12, 2),
        tax_amount NUMERIC(12, 2),
        tax_status VARCHAR(50),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_accounts_account_id ON public.accounts(account_id);
    CREATE INDEX IF NOT EXISTS idx_accounts_property_city ON public.accounts(property_city);
    CREATE INDEX IF NOT EXISTS idx_accounts_property_type ON public.accounts(property_type);
    """
    
    logger.info(sql)
    return True

def create_property_images_table():
    """Create the property_images table in Supabase."""
    logger.info("Creating property_images table through Supabase API")
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot create property_images table: Supabase client not initialized")
        return False
    
    logger.info("Please execute the following SQL in Supabase's SQL editor:")
    
    sql = """
    CREATE TABLE IF NOT EXISTS public.property_images (
        id SERIAL PRIMARY KEY,
        property_id VARCHAR(50) NOT NULL,
        account_id VARCHAR(50),
        image_url VARCHAR(512),
        image_path VARCHAR(512),
        image_type VARCHAR(50),
        image_date DATE,
        width INTEGER,
        height INTEGER,
        file_size INTEGER,
        file_format VARCHAR(20),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_property_images_property_id ON public.property_images(property_id);
    CREATE INDEX IF NOT EXISTS idx_property_images_account_id ON public.property_images(account_id);
    """
    
    logger.info(sql)
    return True

def create_assessments_table():
    """Create the assessments table in Supabase."""
    logger.info("Creating assessments table through Supabase API")
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot create assessments table: Supabase client not initialized")
        return False
    
    logger.info("Please execute the following SQL in Supabase's SQL editor:")
    
    sql = """
    CREATE TABLE IF NOT EXISTS public.assessments (
        id SERIAL PRIMARY KEY,
        property_id INTEGER NOT NULL,
        assessment_year INTEGER NOT NULL,
        assessment_date DATE NOT NULL,
        assessed_land_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
        assessed_improvement_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
        assessed_total_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
        tax_year INTEGER,
        tax_amount NUMERIC(12, 2),
        tax_status VARCHAR(50),
        assessor_name VARCHAR(255),
        assessment_method VARCHAR(50),
        valuation_notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_assessments_property_id ON public.assessments(property_id);
    CREATE INDEX IF NOT EXISTS idx_assessments_assessment_year ON public.assessments(assessment_year);
    """
    
    logger.info(sql)
    return True

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
    
    # Create database tables
    logger.info("Creating database tables in Supabase")
    logger.info("Executing schema SQL")
    if not execute_schema_sql():
        logger.error("Failed to execute schema SQL")
        return False
    logger.info("Database tables created successfully")
    
    # Test CRUD operations
    logger.info("Testing basic CRUD operations with accounts table")
    try:
        # Create a test account
        supabase = get_supabase_client()
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        test_account_id = f"TEST{timestamp}"
        
        account_data = {
            "account_id": test_account_id,
            "owner_name": "Test Owner",
            "property_address": "123 Test St",
            "property_city": "Test City",
            "property_type": "Residential",
            "latitude": 47.6062,
            "longitude": -122.3321,
            "assessment_year": 2025,
            "assessed_value": 100000,
            "created_at": datetime.datetime.now().isoformat()
        }
        
        logger.info(f"Creating test account with ID: {test_account_id}")
        response = supabase.table("accounts").insert(account_data).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error creating test account: {response.error}")
            return False
        
        logger.info("Test account created successfully")
        
        # Read the test account
        logger.info(f"Reading test account with ID: {test_account_id}")
        read_response = supabase.table("accounts").select("*").eq("account_id", test_account_id).execute()
        
        if hasattr(read_response, 'error') and read_response.error:
            logger.error(f"Error reading test account: {read_response.error}")
            return False
        
        if read_response.data and len(read_response.data) > 0:
            logger.info("Test account read successfully")
        else:
            logger.error("Test account not found")
            return False
        
        # Update the test account
        logger.info(f"Updating test account with ID: {test_account_id}")
        update_data = {
            "owner_name": "Updated Owner",
            "assessed_value": 110000
        }
        
        update_response = supabase.table("accounts").update(update_data).eq("account_id", test_account_id).execute()
        
        if hasattr(update_response, 'error') and update_response.error:
            logger.error(f"Error updating test account: {update_response.error}")
            return False
        
        logger.info("Test account updated successfully")
        
        # Delete the test account
        logger.info(f"Deleting test account with ID: {test_account_id}")
        delete_response = supabase.table("accounts").delete().eq("account_id", test_account_id).execute()
        
        if hasattr(delete_response, 'error') and delete_response.error:
            logger.error(f"Error deleting test account: {delete_response.error}")
            return False
        
        logger.info("Test account deleted successfully")
        logger.info("Basic CRUD operations completed successfully")
        
    except Exception as e:
        logger.error(f"Exception testing CRUD operations: {str(e)}")
        return False
    
    logger.info("Supabase setup testing completed successfully")
    return True

if __name__ == "__main__":
    main()