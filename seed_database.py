"""
This script seeds the database with sample data for testing purposes.
"""

import random
import datetime
import logging
from faker import Faker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Flask app and database connection
from app_setup import app, db
from models import Parcel, Property, Sale

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Faker
fake = Faker()

def create_sample_parcels(count=10):
    """Create sample parcel records."""
    logger.info(f"Creating {count} sample parcels...")
    parcels = []
    
    # List of cities for sample data
    cities = ["Seattle", "Portland", "San Francisco", "Los Angeles", "Chicago", 
              "New York", "Boston", "Austin", "Denver", "Miami"]
    
    # List of states for sample data
    states = ["WA", "OR", "CA", "IL", "NY", "MA", "TX", "CO", "FL"]
    
    for i in range(count):
        city = random.choice(cities)
        state = random.choice(states)
        
        parcel = Parcel(
            parcel_id=f"P{fake.unique.random_number(digits=8)}",
            address=fake.street_address(),
            city=city,
            state=state,
            zip_code=fake.zipcode(),
            land_value=round(random.uniform(50000, 500000), 2),
            improvement_value=round(random.uniform(100000, 1000000), 2),
            assessment_year=random.randint(2020, 2024),
            latitude=fake.latitude(),
            longitude=fake.longitude(),
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        
        # Calculate total value
        parcel.total_value = parcel.land_value + parcel.improvement_value
        
        parcels.append(parcel)
    
    # Add parcels to the database
    db.session.add_all(parcels)
    db.session.commit()
    
    logger.info(f"Created {len(parcels)} sample parcels.")
    return parcels

def create_sample_properties(parcels):
    """Create sample property records for the given parcels."""
    logger.info(f"Creating sample properties for {len(parcels)} parcels...")
    properties = []
    
    # List of property types for sample data
    property_types = ["Single Family", "Multi-Family", "Condominium", "Townhouse", 
                      "Apartment", "Commercial", "Industrial", "Vacant Land"]
    
    # List of conditions for sample data
    conditions = ["Excellent", "Good", "Average", "Fair", "Poor"]
    
    # List of quality ratings for sample data
    qualities = ["Luxury", "High", "Average", "Economy", "Low"]
    
    # List of zoning types for sample data
    zonings = ["Residential", "Commercial", "Industrial", "Mixed Use", "Agricultural"]
    
    for parcel in parcels:
        # Number of properties per parcel (1-3)
        num_properties = random.randint(1, 3)
        
        for _ in range(num_properties):
            property_type = random.choice(property_types)
            
            # Skip building details for vacant land
            if property_type == "Vacant Land":
                prop = Property(
                    parcel_id=parcel.id,
                    property_type=property_type,
                    lot_size=round(random.uniform(0.1, 10.0), 2),
                    lot_size_unit="acres",
                    condition=random.choice(conditions),
                    quality=random.choice(qualities),
                    tax_district=f"District {random.randint(1, 5)}",
                    zoning=random.choice(zonings),
                    created_at=datetime.datetime.utcnow(),
                    updated_at=datetime.datetime.utcnow()
                )
            else:
                prop = Property(
                    parcel_id=parcel.id,
                    property_type=property_type,
                    year_built=random.randint(1950, 2023),
                    square_footage=random.randint(1000, 5000),
                    bedrooms=random.randint(1, 6) if "Family" in property_type or "Condominium" in property_type else None,
                    bathrooms=round(random.uniform(1.0, 5.0), 1) if "Family" in property_type or "Condominium" in property_type else None,
                    lot_size=round(random.uniform(0.1, 1.0), 2),
                    lot_size_unit="acres",
                    stories=round(random.uniform(1.0, 3.0), 1) if "Family" in property_type else None,
                    condition=random.choice(conditions),
                    quality=random.choice(qualities),
                    tax_district=f"District {random.randint(1, 5)}",
                    zoning=random.choice(zonings),
                    created_at=datetime.datetime.utcnow(),
                    updated_at=datetime.datetime.utcnow()
                )
            
            properties.append(prop)
    
    # Add properties to the database
    db.session.add_all(properties)
    db.session.commit()
    
    logger.info(f"Created {len(properties)} sample properties.")
    return properties

def create_sample_sales(parcels):
    """Create sample sale records for the given parcels."""
    logger.info(f"Creating sample sales for {len(parcels)} parcels...")
    sales = []
    
    # List of sale types for sample data
    sale_types = ["Standard", "Foreclosure", "Short Sale", "New Construction", "Auction"]
    
    # List of financing types for sample data
    financing_types = ["Conventional", "FHA", "VA", "Cash", "Owner Financing"]
    
    for parcel in parcels:
        # Number of sales per parcel (1-5)
        num_sales = random.randint(1, 5)
        
        # Generate sales dates in chronological order
        sale_years = sorted(random.sample(range(2010, 2025), num_sales))
        
        for i, year in enumerate(sale_years):
            # Generate random sale date within the year
            sale_date = datetime.date(year, random.randint(1, 12), random.randint(1, 28))
            
            # Base price with some randomness
            base_price = round(random.uniform(200000, 800000), 2)
            
            # Increase price for later sales (appreciation)
            appreciation_factor = 1.0 + (i * 0.1)  # 10% appreciation per sale
            sale_price = round(base_price * appreciation_factor, 2)
            
            sale = Sale(
                parcel_id=parcel.id,
                sale_date=sale_date,
                sale_price=sale_price,
                sale_type=random.choice(sale_types),
                transaction_id=fake.uuid4(),
                buyer_name=fake.name(),
                seller_name=fake.name(),
                financing_type=random.choice(financing_types),
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow()
            )
            
            sales.append(sale)
    
    # Add sales to the database
    db.session.add_all(sales)
    db.session.commit()
    
    logger.info(f"Created {len(sales)} sample sales.")
    return sales

def seed_database():
    """Main function to seed the database."""
    logger.info("Starting database seeding...")
    
    with app.app_context():
        # Check if database is already seeded
        existing_count = db.session.query(Parcel).count()
        if existing_count > 0:
            logger.info(f"Database already contains {existing_count} parcels. Skipping seeding.")
            return
        
        try:
            # Create sample data
            parcels = create_sample_parcels(count=50)
            create_sample_properties(parcels)
            create_sample_sales(parcels)
            
            logger.info("Database seeding completed successfully.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error seeding database: {str(e)}")
            raise

if __name__ == "__main__":
    seed_database()