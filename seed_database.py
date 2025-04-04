"""
This script seeds the database with sample data for testing purposes.
"""

import os
import logging
import random
import datetime
from decimal import Decimal

from flask import Flask
from database import app, db, Parcel, Property, Sale

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def create_sample_parcels(count=10):
    """Create sample parcel records."""
    logger.info(f"Creating {count} sample parcels")
    
    # Lists for generating sample data
    cities = ["Springfield", "Riverside", "Oakridge", "Maplewood", "Pine Valley", "Cedar Hills"]
    states = ["CA", "NY", "TX", "FL", "WA", "IL"]
    street_types = ["St", "Ave", "Blvd", "Dr", "Ln", "Rd", "Way", "Pl"]
    
    parcels = []
    for i in range(1, count + 1):
        street_number = random.randint(100, 9999)
        street_name = random.choice(["Main", "Oak", "Pine", "Maple", "Cedar", "Elm", "Washington", "Park", "Lake", "River"])
        street_type = random.choice(street_types)
        address = f"{street_number} {street_name} {street_type}"
        
        city = random.choice(cities)
        state = random.choice(states)
        zip_code = f"{random.randint(10000, 99999)}"
        
        land_value = Decimal(random.randint(5000, 500000))
        improvement_value = Decimal(random.randint(10000, 1000000))
        total_value = land_value + improvement_value
        
        assessment_year = random.choice([2022, 2023, 2024])
        
        # Generate a unique parcel ID
        parcel_id = f"{state[:2]}-{city[:3]}-{zip_code[:5]}-{i:03d}"
        
        # Create latitude and longitude (simplified for demo)
        latitude = 37.0 + (random.random() * 5)
        longitude = -122.0 - (random.random() * 5)
        
        # Create the parcel record
        parcel = Parcel(
            parcel_id=parcel_id,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            land_value=land_value,
            improvement_value=improvement_value,
            total_value=total_value,
            assessment_year=assessment_year,
            latitude=latitude,
            longitude=longitude
        )
        
        parcels.append(parcel)
    
    # Add all parcels to the database
    db.session.add_all(parcels)
    db.session.commit()
    
    return parcels

def create_sample_properties(parcels):
    """Create sample property records for the given parcels."""
    logger.info(f"Creating properties for {len(parcels)} parcels")
    
    property_types = ["Single Family", "Multi-Family", "Condominium", "Townhouse", "Commercial", "Industrial", "Vacant Land"]
    conditions = ["Excellent", "Good", "Average", "Fair", "Poor"]
    qualities = ["Luxury", "High", "Average", "Low", "Very Low"]
    tax_districts = ["Central", "North", "South", "East", "West"]
    zoning_types = ["Residential", "Commercial", "Industrial", "Agricultural", "Mixed-Use"]
    
    properties = []
    for parcel in parcels:
        # Determine property type
        property_type = random.choice(property_types)
        
        # Generate property attributes based on type
        if property_type == "Vacant Land":
            year_built = None
            square_footage = None
            bedrooms = None
            bathrooms = None
            stories = None
        else:
            current_year = datetime.datetime.now().year
            year_built = random.randint(1950, current_year - 1)
            
            if property_type in ["Single Family", "Multi-Family", "Condominium", "Townhouse"]:
                square_footage = random.randint(800, 5000)
                bedrooms = random.randint(1, 6)
                bathrooms = random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0])
                stories = random.choice([1.0, 1.5, 2.0, 2.5, 3.0])
            else:  # Commercial or Industrial
                square_footage = random.randint(2000, 50000)
                bedrooms = None
                bathrooms = random.randint(1, 10)
                stories = random.randint(1, 5)
        
        # Common attributes
        lot_size = random.uniform(0.1, 10.0)
        lot_size_unit = "acres"
        condition = random.choice(conditions)
        quality = random.choice(qualities)
        tax_district = random.choice(tax_districts)
        zoning = random.choice(zoning_types)
        
        # Create the property record
        property_record = Property(
            parcel_id=parcel.id,
            property_type=property_type,
            year_built=year_built,
            square_footage=square_footage,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            lot_size=lot_size,
            lot_size_unit=lot_size_unit,
            stories=stories,
            condition=condition,
            quality=quality,
            tax_district=tax_district,
            zoning=zoning
        )
        
        properties.append(property_record)
    
    # Add all properties to the database
    db.session.add_all(properties)
    db.session.commit()
    
    return properties

def create_sample_sales(parcels):
    """Create sample sale records for the given parcels."""
    logger.info(f"Creating sales history for {len(parcels)} parcels")
    
    sale_types = ["Standard", "Foreclosure", "Short Sale", "Auction", "New Construction"]
    financing_types = ["Conventional", "FHA", "VA", "Cash", "Seller Financing", "USDA", "Other"]
    
    sales = []
    for parcel in parcels:
        # Generate 1-3 sales per parcel
        num_sales = random.randint(1, 3)
        
        # Start with a base sale date 5-15 years ago
        current_date = datetime.datetime.now().date()
        years_back = random.randint(5, 15)
        base_sale_date = current_date.replace(year=current_date.year - years_back)
        
        for i in range(num_sales):
            # For multiple sales, each subsequent sale happens 2-5 years after the previous
            if i > 0:
                years_forward = random.randint(2, 5)
                base_sale_date = base_sale_date.replace(year=base_sale_date.year + years_forward)
                
                # Don't create future sales
                if base_sale_date > current_date:
                    break
            
            # Adjust the sale date by a random number of days
            days_adjustment = random.randint(-180, 180)
            sale_date = base_sale_date + datetime.timedelta(days=days_adjustment)
            
            # Make sure the sale date isn't in the future
            if sale_date > current_date:
                sale_date = current_date - datetime.timedelta(days=random.randint(1, 30))
            
            # Generate sale price (related to the total value but with some variance)
            base_price = float(parcel.total_value)
            variance_factor = random.uniform(0.8, 1.2)  # 80% to 120% of the assessed value
            sale_price = Decimal(base_price * variance_factor).quantize(Decimal('0.01'))
            
            # Set other sale attributes
            sale_type = random.choice(sale_types)
            transaction_id = f"TX-{parcel.parcel_id}-{sale_date.year}{sale_date.month:02d}{sale_date.day:02d}"
            
            # Generate random names for buyer and seller
            first_names = ["John", "Jane", "Michael", "Emily", "David", "Sarah", "James", "Jennifer", "Robert", "Linda"]
            last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Taylor", "Anderson"]
            
            buyer_name = f"{random.choice(first_names)} {random.choice(last_names)}"
            seller_name = f"{random.choice(first_names)} {random.choice(last_names)}"
            
            # Ensure buyer and seller are different
            while seller_name == buyer_name:
                seller_name = f"{random.choice(first_names)} {random.choice(last_names)}"
            
            financing_type = random.choice(financing_types)
            
            # Create the sale record
            sale = Sale(
                parcel_id=parcel.id,
                sale_date=sale_date,
                sale_price=sale_price,
                sale_type=sale_type,
                transaction_id=transaction_id,
                buyer_name=buyer_name,
                seller_name=seller_name,
                financing_type=financing_type
            )
            
            sales.append(sale)
    
    # Add all sales to the database
    db.session.add_all(sales)
    db.session.commit()
    
    return sales

def seed_database():
    """Main function to seed the database."""
    with app.app_context():
        try:
            # Check if database is already seeded
            existing_count = Parcel.query.count()
            if existing_count > 0:
                logger.info(f"Database already contains {existing_count} parcels")
                user_input = input("Do you want to add more sample data? (y/n): ")
                if user_input.lower() != 'y':
                    logger.info("Database seeding cancelled")
                    return
            
            # Create sample data - adjust counts as needed
            parcels = create_sample_parcels(count=20)
            properties = create_sample_properties(parcels)
            sales = create_sample_sales(parcels)
            
            logger.info(f"Created {len(parcels)} parcels")
            logger.info(f"Created {len(properties)} properties")
            logger.info(f"Created {len(sales)} sales")
            
            logger.info("Database seeding completed successfully")
            
        except Exception as e:
            logger.error(f"Error seeding database: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    seed_database()