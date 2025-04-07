"""
Update Account Values

This script updates account records with sample assessed values based on 
property types and city locations. This provides more complete data for
property analytics and visualization.
"""

import random
import logging
from decimal import Decimal
from app_setup import app, db
from models import Account

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base values by property type (in USD)
PROPERTY_TYPE_BASE_VALUES = {
    'Residential': 250000,
    'Commercial': 500000,
    'Agricultural': 350000,
    'Industrial': 750000
}

# City value multipliers (relative to base value) - Benton County only
CITY_MULTIPLIERS = {
    'Richland': 1.2,
    'Kennewick': 1.0,
    'West Richland': 1.1,
    'Benton City': 0.8,
    'Prosser': 0.85
}

def get_property_base_value(property_type):
    """Get base property value based on property type."""
    base_value = PROPERTY_TYPE_BASE_VALUES.get(property_type)
    if not base_value:
        # Default to residential if type not found
        base_value = PROPERTY_TYPE_BASE_VALUES['Residential']
    
    # Add some variance (±20%)
    variance = random.uniform(0.8, 1.2)
    return base_value * variance

def get_city_multiplier(city):
    """Get value multiplier based on city."""
    multiplier = CITY_MULTIPLIERS.get(city)
    if not multiplier:
        # Default to 1.0 if city not found
        multiplier = 1.0
    
    # Add some variance (±10%)
    variance = random.uniform(0.9, 1.1)
    return multiplier * variance

def update_assessed_values():
    """Update account records with assessed values based on property type and city."""
    with app.app_context():
        try:
            # Get all accounts that have property type and city
            accounts = Account.query.filter(
                Account.property_type.isnot(None),
                Account.property_city.isnot(None)
            ).all()
            
            if not accounts:
                logger.warning("No accounts found with property type and city")
                return 0
            
            updated_count = 0
            
            # Update each account with an appropriate assessed value
            for account in accounts:
                # Calculate value based on property type and city
                base_value = get_property_base_value(account.property_type)
                city_multiplier = get_city_multiplier(account.property_city)
                assessed_value = base_value * city_multiplier
                
                # Round to nearest 100
                assessed_value = round(assessed_value / 100) * 100
                
                # Update account
                account.assessed_value = Decimal(str(assessed_value))
                
                # Calculate tax amount (roughly 1% of assessed value)
                tax_rate = random.uniform(0.009, 0.011)  # 0.9% to 1.1%
                tax_amount = assessed_value * tax_rate
                
                # Round to nearest 10
                tax_amount = round(tax_amount / 10) * 10
                account.tax_amount = Decimal(str(tax_amount))
                
                # Set tax status
                account.tax_status = 'Current'
                
                # Set assessment year
                account.assessment_year = 2024
                
                logger.info(f"Updated account {account.account_id}: {account.property_type} in {account.property_city}, " +
                          f"Value: ${assessed_value:,.2f}, Tax: ${tax_amount:,.2f}")
                updated_count += 1
            
            # Commit changes
            db.session.commit()
            logger.info(f"Successfully updated {updated_count} accounts with assessed values")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating assessed values: {str(e)}")
            db.session.rollback()
            return 0

if __name__ == "__main__":
    # Update assessed values
    updated_count = update_assessed_values()
    
    if updated_count > 0:
        logger.info(f"Updated {updated_count} accounts with realistic assessed values")
    else:
        logger.warning("No accounts were updated")