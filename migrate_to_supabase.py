"""
Data Migration Script for Supabase

This script migrates data from the local PostgreSQL database to Supabase.
It uses SQLAlchemy to read data from the local database and the Supabase client to write data to Supabase.
"""

import os
import sys
import logging
import datetime
from typing import Dict, List, Any
import time

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from app_setup import db, app
from models import Parcel, Property, Sale, Account, PropertyImage
from app.db.supabase_client import (
    get_supabase_client,
    create_property,
    create_user
)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_admin_user():
    """Create an admin user in Supabase."""
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot create admin user: Supabase client not initialized")
        return False

    try:
        # Define admin user data
        admin_email = input("Enter admin email: ")
        admin_username = input("Enter admin username: ")
        admin_password = input("Enter admin password: ")
        admin_name = input("Enter admin full name: ")

        # Create user data
        user_data = {
            "username": admin_username,
            "email": admin_email,
            "full_name": admin_name,
            "password": admin_password,  # Will be hashed by the create_user function
            "roles": ["admin", "user"]
        }

        # Create the admin user
        from app.auth.supabase_auth import signup_user
        success, message, user = signup_user(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            full_name=admin_name,
            roles=["admin", "user"]
        )

        if success:
            logger.info(f"Admin user created successfully: {message}")
            return True
        else:
            logger.error(f"Failed to create admin user: {message}")
            return False

    except Exception as e:
        logger.error(f"Exception creating admin user: {str(e)}")
        return False

def migrate_parcels():
    """Migrate parcels from local database to Supabase."""
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot migrate parcels: Supabase client not initialized")
        return False

    try:
        with app.app_context():
            # Get all parcels from the local database
            parcels = Parcel.query.all()
            logger.info(f"Found {len(parcels)} parcels to migrate")

            # Create a mapping of local IDs to Supabase IDs
            id_mapping = {}

            # Insert parcels into Supabase
            for parcel in parcels:
                parcel_data = {
                    "parcel_id": parcel.parcel_id,
                    "address": parcel.address,
                    "city": parcel.city,
                    "state": parcel.state,
                    "zip_code": parcel.zip_code,
                    "land_value": float(parcel.land_value) if parcel.land_value else 0,
                    "improvement_value": float(parcel.improvement_value) if parcel.improvement_value else 0,
                    "total_value": float(parcel.total_value) if parcel.total_value else 0,
                    "assessment_year": parcel.assessment_year,
                    "latitude": parcel.latitude,
                    "longitude": parcel.longitude,
                    "created_at": parcel.created_at.isoformat() if parcel.created_at else datetime.datetime.utcnow().isoformat(),
                    "updated_at": parcel.updated_at.isoformat() if parcel.updated_at else datetime.datetime.utcnow().isoformat()
                }

                response = supabase.table("parcels").insert(parcel_data).execute()
                
                if hasattr(response, 'error') and response.error:
                    logger.error(f"Error inserting parcel {parcel.parcel_id}: {response.error}")
                    continue

                # Get the Supabase ID of the inserted parcel
                if response.data and len(response.data) > 0:
                    supabase_id = response.data[0].get('id')
                    id_mapping[parcel.id] = supabase_id
                    logger.info(f"Migrated parcel {parcel.parcel_id} (Local ID: {parcel.id}, Supabase ID: {supabase_id})")
                else:
                    logger.warning(f"No data returned for parcel {parcel.parcel_id}")

            logger.info(f"Migrated {len(id_mapping)} parcels successfully")
            return id_mapping

    except Exception as e:
        logger.error(f"Exception migrating parcels: {str(e)}")
        return {}

def migrate_properties(parcel_id_mapping):
    """Migrate properties from local database to Supabase."""
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot migrate properties: Supabase client not initialized")
        return False

    try:
        with app.app_context():
            # Get all properties from the local database
            properties = Property.query.all()
            logger.info(f"Found {len(properties)} properties to migrate")

            # Create a mapping of local IDs to Supabase IDs
            id_mapping = {}

            # Insert properties into Supabase
            for prop in properties:
                # Skip if the parcel ID is not in the mapping
                if prop.parcel_id not in parcel_id_mapping:
                    logger.warning(f"Skipping property {prop.id}: Parcel ID {prop.parcel_id} not found in mapping")
                    continue

                property_data = {
                    "parcel_id": parcel_id_mapping[prop.parcel_id],
                    "property_type": prop.property_type,
                    "year_built": prop.year_built,
                    "square_footage": prop.square_footage,
                    "bedrooms": prop.bedrooms,
                    "bathrooms": prop.bathrooms,
                    "lot_size": prop.lot_size,
                    "lot_size_unit": prop.lot_size_unit,
                    "stories": prop.stories,
                    "condition": prop.condition,
                    "quality": prop.quality,
                    "tax_district": prop.tax_district,
                    "zoning": prop.zoning,
                    "created_at": prop.created_at.isoformat() if prop.created_at else datetime.datetime.utcnow().isoformat(),
                    "updated_at": prop.updated_at.isoformat() if prop.updated_at else datetime.datetime.utcnow().isoformat()
                }

                response = supabase.table("properties").insert(property_data).execute()
                
                if hasattr(response, 'error') and response.error:
                    logger.error(f"Error inserting property {prop.id}: {response.error}")
                    continue

                # Get the Supabase ID of the inserted property
                if response.data and len(response.data) > 0:
                    supabase_id = response.data[0].get('id')
                    id_mapping[prop.id] = supabase_id
                    logger.info(f"Migrated property {prop.id} (Supabase ID: {supabase_id})")
                else:
                    logger.warning(f"No data returned for property {prop.id}")

            logger.info(f"Migrated {len(id_mapping)} properties successfully")
            return id_mapping

    except Exception as e:
        logger.error(f"Exception migrating properties: {str(e)}")
        return {}

def migrate_sales(parcel_id_mapping):
    """Migrate sales from local database to Supabase."""
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot migrate sales: Supabase client not initialized")
        return False

    try:
        with app.app_context():
            # Get all sales from the local database
            sales = Sale.query.all()
            logger.info(f"Found {len(sales)} sales to migrate")

            # Create a mapping of local IDs to Supabase IDs
            id_mapping = {}

            # Insert sales into Supabase
            for sale in sales:
                # Skip if the parcel ID is not in the mapping
                if sale.parcel_id not in parcel_id_mapping:
                    logger.warning(f"Skipping sale {sale.id}: Parcel ID {sale.parcel_id} not found in mapping")
                    continue

                sale_data = {
                    "parcel_id": parcel_id_mapping[sale.parcel_id],
                    "sale_date": sale.sale_date.isoformat() if sale.sale_date else None,
                    "sale_price": float(sale.sale_price) if sale.sale_price else 0,
                    "sale_type": sale.sale_type,
                    "transaction_id": sale.transaction_id,
                    "buyer_name": sale.buyer_name,
                    "seller_name": sale.seller_name,
                    "financing_type": sale.financing_type,
                    "created_at": sale.created_at.isoformat() if sale.created_at else datetime.datetime.utcnow().isoformat(),
                    "updated_at": sale.updated_at.isoformat() if sale.updated_at else datetime.datetime.utcnow().isoformat()
                }

                response = supabase.table("sales").insert(sale_data).execute()
                
                if hasattr(response, 'error') and response.error:
                    logger.error(f"Error inserting sale {sale.id}: {response.error}")
                    continue

                # Get the Supabase ID of the inserted sale
                if response.data and len(response.data) > 0:
                    supabase_id = response.data[0].get('id')
                    id_mapping[sale.id] = supabase_id
                    logger.info(f"Migrated sale {sale.id} (Supabase ID: {supabase_id})")
                else:
                    logger.warning(f"No data returned for sale {sale.id}")

            logger.info(f"Migrated {len(id_mapping)} sales successfully")
            return id_mapping

    except Exception as e:
        logger.error(f"Exception migrating sales: {str(e)}")
        return {}

def migrate_accounts():
    """Migrate accounts from local database to Supabase."""
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot migrate accounts: Supabase client not initialized")
        return False

    try:
        with app.app_context():
            # Get all accounts from the local database
            accounts = Account.query.all()
            logger.info(f"Found {len(accounts)} accounts to migrate")

            # Create a mapping of local IDs to Supabase IDs
            id_mapping = {}

            # Insert accounts into Supabase
            for account in accounts:
                account_data = {
                    "account_id": account.account_id,
                    "owner_name": account.owner_name,
                    "mailing_address": account.mailing_address,
                    "mailing_city": account.mailing_city,
                    "mailing_state": account.mailing_state,
                    "mailing_zip": account.mailing_zip,
                    "property_address": account.property_address,
                    "property_city": account.property_city,
                    "property_type": account.property_type,
                    "legal_description": account.legal_description,
                    "latitude": account.latitude,
                    "longitude": account.longitude,
                    "assessment_year": account.assessment_year,
                    "assessed_value": float(account.assessed_value) if account.assessed_value else None,
                    "tax_amount": float(account.tax_amount) if account.tax_amount else None,
                    "tax_status": account.tax_status,
                    "created_at": account.created_at.isoformat() if account.created_at else datetime.datetime.utcnow().isoformat(),
                    "updated_at": account.updated_at.isoformat() if account.updated_at else datetime.datetime.utcnow().isoformat()
                }

                response = supabase.table("accounts").insert(account_data).execute()
                
                if hasattr(response, 'error') and response.error:
                    logger.error(f"Error inserting account {account.account_id}: {response.error}")
                    continue

                # Get the Supabase ID of the inserted account
                if response.data and len(response.data) > 0:
                    supabase_id = response.data[0].get('id')
                    id_mapping[account.id] = supabase_id
                    logger.info(f"Migrated account {account.account_id} (Supabase ID: {supabase_id})")
                else:
                    logger.warning(f"No data returned for account {account.account_id}")

            logger.info(f"Migrated {len(id_mapping)} accounts successfully")
            return id_mapping

    except Exception as e:
        logger.error(f"Exception migrating accounts: {str(e)}")
        return {}

def migrate_property_images():
    """Migrate property images from local database to Supabase."""
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot migrate property images: Supabase client not initialized")
        return False

    try:
        with app.app_context():
            # Get all property images from the local database
            images = PropertyImage.query.all()
            logger.info(f"Found {len(images)} property images to migrate")

            # Create a mapping of local IDs to Supabase IDs
            id_mapping = {}

            # Insert property images into Supabase
            for image in images:
                image_data = {
                    "property_id": image.property_id,
                    "account_id": image.account_id,
                    "image_url": image.image_url,
                    "image_path": image.image_path,
                    "image_type": image.image_type,
                    "image_date": image.image_date.isoformat() if image.image_date else None,
                    "width": image.width,
                    "height": image.height,
                    "file_size": image.file_size,
                    "file_format": image.file_format,
                    "created_at": image.created_at.isoformat() if image.created_at else datetime.datetime.utcnow().isoformat(),
                    "updated_at": image.updated_at.isoformat() if image.updated_at else datetime.datetime.utcnow().isoformat()
                }

                response = supabase.table("property_images").insert(image_data).execute()
                
                if hasattr(response, 'error') and response.error:
                    logger.error(f"Error inserting property image {image.id}: {response.error}")
                    continue

                # Get the Supabase ID of the inserted property image
                if response.data and len(response.data) > 0:
                    supabase_id = response.data[0].get('id')
                    id_mapping[image.id] = supabase_id
                    logger.info(f"Migrated property image {image.id} (Supabase ID: {supabase_id})")
                else:
                    logger.warning(f"No data returned for property image {image.id}")

            logger.info(f"Migrated {len(id_mapping)} property images successfully")
            return id_mapping

    except Exception as e:
        logger.error(f"Exception migrating property images: {str(e)}")
        return {}

def main():
    """Main function to run the migration."""
    logger.info("Starting data migration to Supabase")
    
    # Check Supabase connection
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot migrate data: Supabase client not initialized")
        return False
    
    # Create admin user
    logger.info("Creating admin user")
    create_admin = input("Do you want to create an admin user? (y/n): ")
    if create_admin.lower() == 'y':
        if not create_admin_user():
            logger.error("Failed to create admin user")
            return False
    
    # Migrate parcels
    logger.info("Migrating parcels")
    parcel_id_mapping = migrate_parcels()
    if not parcel_id_mapping:
        logger.error("Failed to migrate parcels")
        return False
    
    # Migrate properties
    logger.info("Migrating properties")
    property_id_mapping = migrate_properties(parcel_id_mapping)
    if not property_id_mapping:
        logger.error("Failed to migrate properties")
        return False
    
    # Migrate sales
    logger.info("Migrating sales")
    sales_id_mapping = migrate_sales(parcel_id_mapping)
    if not sales_id_mapping:
        logger.error("Failed to migrate sales")
        return False
    
    # Migrate accounts
    logger.info("Migrating accounts")
    account_id_mapping = migrate_accounts()
    if not account_id_mapping:
        logger.error("Failed to migrate accounts")
        return False
    
    # Migrate property images
    logger.info("Migrating property images")
    property_image_id_mapping = migrate_property_images()
    if not property_image_id_mapping:
        logger.error("Failed to migrate property images")
        return False
    
    logger.info("Data migration completed successfully")
    return True

if __name__ == "__main__":
    main()