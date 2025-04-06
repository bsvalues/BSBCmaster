"""
This module defines the database models for the MCP Assessor Agent API.
"""

import datetime
from sqlalchemy import Column, Integer, Float, String, ForeignKey, Numeric, Date, DateTime, Text
from sqlalchemy.orm import relationship
from app_setup import db

class Parcel(db.Model):
    """Real estate parcel information (main assessment record)."""
    __tablename__ = 'parcels'

    id = db.Column(db.Integer, primary_key=True)
    parcel_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)

    # Assessment values
    land_value = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    improvement_value = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total_value = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    assessment_year = db.Column(db.Integer, nullable=False)

    # Geographic coordinates
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    property_details = db.relationship('Property', backref='parcel', lazy=True, cascade="all, delete-orphan")
    sales = db.relationship('Sale', backref='parcel', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Parcel {self.parcel_id}: {self.address}, {self.city}, {self.state}>"


class Property(db.Model):
    """Physical property characteristics."""
    __tablename__ = 'properties'

    id = db.Column(db.Integer, primary_key=True)
    parcel_id = db.Column(db.Integer, db.ForeignKey('parcels.id'), nullable=False)

    # Property characteristics
    property_type = db.Column(db.String(50), nullable=False)
    year_built = db.Column(db.Integer, nullable=True)
    square_footage = db.Column(db.Integer, nullable=True)
    bedrooms = db.Column(db.Integer, nullable=True)
    bathrooms = db.Column(db.Float, nullable=True)
    lot_size = db.Column(db.Float, nullable=True)
    lot_size_unit = db.Column(db.String(20), nullable=True)
    stories = db.Column(db.Float, nullable=True)
    condition = db.Column(db.String(50), nullable=True)
    quality = db.Column(db.String(50), nullable=True)

    # Zoning and taxation
    tax_district = db.Column(db.String(50), nullable=True)
    zoning = db.Column(db.String(50), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Property {self.id} for Parcel {self.parcel_id}: {self.property_type}>"


class Sale(db.Model):
    """Property sale transaction history."""
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    parcel_id = db.Column(db.Integer, db.ForeignKey('parcels.id'), nullable=False)

    # Sale details
    sale_date = db.Column(db.Date, nullable=False)
    sale_price = db.Column(db.Numeric(12, 2), nullable=False)
    sale_type = db.Column(db.String(50), nullable=True)
    transaction_id = db.Column(db.String(50), nullable=True)

    # Buyer and seller
    buyer_name = db.Column(db.String(255), nullable=True)
    seller_name = db.Column(db.String(255), nullable=True)

    # Financing
    financing_type = db.Column(db.String(50), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Sale {self.id} for Parcel {self.parcel_id}: ${self.sale_price} on {self.sale_date}>"


class Account(db.Model):
    """Property assessment account information."""
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    owner_name = db.Column(db.String(255), nullable=True)
    mailing_address = db.Column(db.String(255), nullable=True)
    mailing_city = db.Column(db.String(100), nullable=True)
    mailing_state = db.Column(db.String(50), nullable=True)
    mailing_zip = db.Column(db.String(20), nullable=True)
    
    # Property details
    property_address = db.Column(db.String(255), nullable=True)
    property_city = db.Column(db.String(100), nullable=True)
    property_type = db.Column(db.String(50), nullable=True)
    legal_description = db.Column(db.Text, nullable=True)
    
    # Geographic coordinates
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Assessment details
    assessment_year = db.Column(db.Integer, nullable=True)
    assessed_value = db.Column(db.Numeric(12, 2), nullable=True)
    tax_amount = db.Column(db.Numeric(12, 2), nullable=True)
    tax_status = db.Column(db.String(50), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<Account {self.account_id}: {self.owner_name}, {self.property_address}>"


class PropertyImage(db.Model):
    """Property images and associated metadata."""
    __tablename__ = 'property_images'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.String(50), nullable=False, index=True)
    account_id = db.Column(db.String(50), nullable=True, index=True)
    
    # Image details
    image_url = db.Column(db.String(512), nullable=True)
    image_path = db.Column(db.String(512), nullable=True)
    image_type = db.Column(db.String(50), nullable=True)
    image_date = db.Column(db.Date, nullable=True)
    
    # Image metadata
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    file_size = db.Column(db.Integer, nullable=True)  # in bytes
    file_format = db.Column(db.String(20), nullable=True)  # e.g., "JPEG", "PNG"
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<PropertyImage {self.id} for Property {self.property_id}, Type: {self.image_type}>"