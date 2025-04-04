"""
This script populates the database with sample data for the MCP Assessor Agent API.
"""

from datetime import datetime, date
import random
from database import app, db, Parcel, Property, Sale

# Sample data for parcels
SAMPLE_PARCELS = [
    {
        "parcel_id": "ABC-12345",
        "address": "123 Main St",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62701",
        "land_value": 120000.00,
        "improvement_value": 230000.00,
        "total_value": 350000.00,
        "assessment_year": 2024,
        "latitude": 39.799999,
        "longitude": -89.650002
    },
    {
        "parcel_id": "XYZ-67890",
        "address": "456 Oak Ave",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62702",
        "land_value": 150000.00,
        "improvement_value": 400000.00,
        "total_value": 550000.00,
        "assessment_year": 2024,
        "latitude": 39.781467,
        "longitude": -89.644661
    },
    {
        "parcel_id": "DEF-54321",
        "address": "789 Pine Rd",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62703",
        "land_value": 95000.00,
        "improvement_value": 185000.00,
        "total_value": 280000.00,
        "assessment_year": 2024,
        "latitude": 39.767365,
        "longitude": -89.692307
    },
    {
        "parcel_id": "GHI-13579",
        "address": "101 Cedar Ln",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62704",
        "land_value": 200000.00,
        "improvement_value": 550000.00,
        "total_value": 750000.00,
        "assessment_year": 2024,
        "latitude": 39.807877,
        "longitude": -89.702125
    },
    {
        "parcel_id": "JKL-24680",
        "address": "222 Maple Blvd",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62704",
        "land_value": 180000.00,
        "improvement_value": 320000.00,
        "total_value": 500000.00,
        "assessment_year": 2024,
        "latitude": 39.815208,
        "longitude": -89.673439
    }
]

# Sample property types and conditions
PROPERTY_TYPES = ["Single Family", "Multi-Family", "Condominium", "Commercial", "Vacant Land"]
PROPERTY_CONDITIONS = ["Excellent", "Good", "Average", "Fair", "Poor"]
PROPERTY_QUALITIES = ["Luxury", "High", "Above Average", "Average", "Below Average", "Low"]
ZONING_TYPES = ["R-1", "R-2", "R-3", "C-1", "C-2", "I-1", "AGR"]

# Sample sale types and financing
SALE_TYPES = ["Standard", "Foreclosure", "Short Sale", "New Construction", "Estate Sale"]
FINANCING_TYPES = ["Conventional", "FHA", "VA", "Cash", "Owner Financing"]


def seed_database(force=False):
    """Seed the database with sample data."""
    with app.app_context():
        # Check if we already have data
        if Parcel.query.count() > 0 and not force:
            print("Database already has data. Skipping seed.")
            return
            
        # Clear existing data if force is True and data exists
        if force and Parcel.query.count() > 0:
            print("Forcing reseed. Clearing existing data...")
            db.session.query(Sale).delete()
            db.session.query(Property).delete()
            db.session.query(Parcel).delete()
            db.session.commit()
        
        print("Seeding database with sample data...")
        
        # Create parcels
        parcels = []
        for parcel_data in SAMPLE_PARCELS:
            parcel = Parcel(**parcel_data)
            db.session.add(parcel)
            parcels.append(parcel)
        
        # Commit to get IDs
        db.session.commit()
        
        # Create properties for each parcel
        for parcel in parcels:
            property_data = {
                "parcel_id": parcel.id,
                "property_type": random.choice(PROPERTY_TYPES),
                "year_built": random.randint(1950, 2023),
                "square_footage": random.randint(1000, 5000),
                "bedrooms": random.randint(2, 5),
                "bathrooms": random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]),
                "lot_size": round(random.uniform(0.1, 2.0), 2),
                "lot_size_unit": "acres",
                "stories": random.choice([1.0, 1.5, 2.0, 2.5, 3.0]),
                "condition": random.choice(PROPERTY_CONDITIONS),
                "quality": random.choice(PROPERTY_QUALITIES),
                "tax_district": f"District {random.randint(1, 5)}",
                "zoning": random.choice(ZONING_TYPES)
            }
            
            # Skip bedrooms/bathrooms for vacant land
            if property_data["property_type"] == "Vacant Land":
                property_data["bedrooms"] = None
                property_data["bathrooms"] = None
                property_data["square_footage"] = None
                property_data["stories"] = None
            
            property_instance = Property(**property_data)
            db.session.add(property_instance)
        
        # Commit to get IDs
        db.session.commit()
        
        # Create sales history for each parcel
        for parcel in parcels:
            # Generate 1-3 sales per parcel
            for _ in range(random.randint(1, 3)):
                # Generate a random date in the past 10 years
                years_ago = random.randint(0, 10)
                months_ago = random.randint(0, 11)
                day = random.randint(1, 28)  # Avoid month boundary issues
                sale_date = date(2024 - years_ago, 12 - months_ago, day)
                
                # Adjust price based on age of sale
                price_factor = 1.0 - (years_ago * 0.02) - (months_ago * 0.001)  # Prices decrease with age
                
                # Convert Decimal to float for operations and then back to Decimal for database
                total_value = float(parcel.total_value)
                adjusted_price = total_value * price_factor * random.uniform(0.9, 1.1)
                
                sale_data = {
                    "parcel_id": parcel.id,
                    "sale_date": sale_date,
                    "sale_price": round(adjusted_price, 2),
                    "sale_type": random.choice(SALE_TYPES),
                    "transaction_id": f"TX-{random.randint(10000, 99999)}",
                    "buyer_name": f"Buyer {random.randint(100, 999)}",
                    "seller_name": f"Seller {random.randint(100, 999)}",
                    "financing_type": random.choice(FINANCING_TYPES)
                }
                
                sale = Sale(**sale_data)
                db.session.add(sale)
        
        # Final commit
        db.session.commit()
        
        # Report counts
        print(f"Created {len(parcels)} parcels")
        print(f"Created {Property.query.count()} property records")
        print(f"Created {Sale.query.count()} sale records")
        print("Database seeding complete!")


if __name__ == "__main__":
    import sys
    force = len(sys.argv) > 1 and sys.argv[1] == "--force"
    seed_database(force=force)