"""
Property Statistics Generator

This script generates summary statistics for property data based on property types,
cities, and other attributes to provide insights for assessment analysis.
"""

import logging
import statistics
from decimal import Decimal
from collections import defaultdict
from app_setup import app, db
from models import Account, PropertyImage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_property_type_statistics():
    """
    Calculate summary statistics for each property type including count, 
    average value, median value, and value ranges.
    
    Returns:
        Dictionary with property type statistics
    """
    with app.app_context():
        try:
            # Get all accounts with property type and assessed value
            accounts = Account.query.filter(
                Account.property_type.isnot(None),
                Account.assessed_value.isnot(None)
            ).all()
            
            if not accounts:
                logger.warning("No accounts found with property type and assessed value")
                return {}
            
            # Group accounts by property type
            property_type_groups = defaultdict(list)
            for account in accounts:
                if account.property_type and account.assessed_value:
                    property_type_groups[account.property_type].append(float(account.assessed_value))
            
            # Calculate statistics for each property type
            property_stats = {}
            for prop_type, values in property_type_groups.items():
                if not values:
                    continue
                    
                count = len(values)
                avg_value = sum(values) / count if count > 0 else 0
                median_value = statistics.median(values) if count > 0 else 0
                min_value = min(values) if count > 0 else 0
                max_value = max(values) if count > 0 else 0
                
                property_stats[prop_type] = {
                    'count': count,
                    'average_value': avg_value,
                    'median_value': median_value,
                    'min_value': min_value,
                    'max_value': max_value
                }
            
            logger.info(f"Generated statistics for {len(property_stats)} property types")
            return property_stats
            
        except Exception as e:
            logger.error(f"Error calculating property type statistics: {str(e)}")
            return {}

def calculate_city_statistics():
    """
    Calculate property statistics for each city including count, average value,
    median value, and property type distribution.
    
    Returns:
        Dictionary with city statistics
    """
    with app.app_context():
        try:
            # Get all accounts with city and assessed value
            accounts = Account.query.filter(
                Account.property_city.isnot(None),
                Account.assessed_value.isnot(None)
            ).all()
            
            if not accounts:
                logger.warning("No accounts found with property city and assessed value")
                return {}
            
            # Group accounts by city
            city_groups = defaultdict(list)
            city_property_types = defaultdict(lambda: defaultdict(int))
            
            for account in accounts:
                if account.property_city and account.assessed_value:
                    city_groups[account.property_city].append(float(account.assessed_value))
                    
                    # Track property type counts for each city
                    if account.property_type:
                        city_property_types[account.property_city][account.property_type] += 1
            
            # Calculate statistics for each city
            city_stats = {}
            for city, values in city_groups.items():
                if not values:
                    continue
                    
                count = len(values)
                avg_value = sum(values) / count if count > 0 else 0
                median_value = statistics.median(values) if count > 0 else 0
                min_value = min(values) if count > 0 else 0
                max_value = max(values) if count > 0 else 0
                
                # Get property type distribution
                type_distribution = city_property_types[city]
                
                city_stats[city] = {
                    'count': count,
                    'average_value': avg_value,
                    'median_value': median_value,
                    'min_value': min_value,
                    'max_value': max_value,
                    'property_types': dict(type_distribution)
                }
            
            logger.info(f"Generated statistics for {len(city_stats)} cities")
            return city_stats
            
        except Exception as e:
            logger.error(f"Error calculating city statistics: {str(e)}")
            return {}

def calculate_value_distribution():
    """
    Calculate the distribution of assessed values across different price ranges.
    
    Returns:
        Dictionary with value range distributions
    """
    with app.app_context():
        try:
            # Define value ranges
            ranges = [
                (0, 100000),
                (100000, 250000),
                (250000, 500000),
                (500000, 1000000),
                (1000000, float('inf'))
            ]
            
            range_labels = [
                "Under $100K",
                "$100K - $250K",
                "$250K - $500K",
                "$500K - $1M",
                "Over $1M"
            ]
            
            # Get all accounts with assessed value
            accounts = Account.query.filter(
                Account.assessed_value.isnot(None)
            ).all()
            
            if not accounts:
                logger.warning("No accounts found with assessed value")
                return {}
            
            # Count properties in each value range
            range_counts = [0] * len(ranges)
            
            for account in accounts:
                if account.assessed_value:
                    value = float(account.assessed_value)
                    for i, (min_val, max_val) in enumerate(ranges):
                        if min_val <= value < max_val or (i == len(ranges) - 1 and value >= min_val):
                            range_counts[i] += 1
                            break
            
            # Create distribution dictionary
            distribution = {}
            for i, label in enumerate(range_labels):
                distribution[label] = range_counts[i]
            
            logger.info(f"Generated value distribution across {len(ranges)} price ranges")
            return distribution
            
        except Exception as e:
            logger.error(f"Error calculating value distribution: {str(e)}")
            return {}

def get_image_statistics():
    """
    Calculate statistics related to property images, such as counts by property type
    and availability percentages.
    
    Returns:
        Dictionary with image statistics
    """
    with app.app_context():
        try:
            # Get count of properties with images
            image_query = db.session.query(PropertyImage.account_id.distinct()).count()
            
            # Get total count of properties
            account_count = Account.query.count()
            
            # Calculate percentage of properties with images
            image_percentage = (image_query / account_count * 100) if account_count > 0 else 0
            
            # Get image counts by property type
            accounts_with_images = db.session.query(Account.property_type, 
                                                  db.func.count(Account.id).label('count'))\
                .join(PropertyImage, PropertyImage.account_id == Account.account_id)\
                .filter(Account.property_type.isnot(None))\
                .group_by(Account.property_type)\
                .all()
            
            # Convert to dictionary
            images_by_type = {prop_type: count for prop_type, count in accounts_with_images}
            
            # Get total images count
            total_images = PropertyImage.query.count()
            
            image_stats = {
                'total_properties': account_count,
                'properties_with_images': image_query,
                'image_availability_percentage': image_percentage,
                'total_images': total_images,
                'images_by_property_type': images_by_type
            }
            
            logger.info(f"Generated image statistics: {image_percentage:.1f}% of properties have images")
            return image_stats
            
        except Exception as e:
            logger.error(f"Error calculating image statistics: {str(e)}")
            return {}

def generate_all_statistics():
    """
    Generate all statistics and return a comprehensive statistics package.
    
    Returns:
        Dictionary with all statistics
    """
    with app.app_context():
        try:
            property_type_stats = calculate_property_type_statistics()
            city_stats = calculate_city_statistics()
            value_distribution = calculate_value_distribution()
            image_stats = get_image_statistics()
            
            all_stats = {
                'property_type_statistics': property_type_stats,
                'city_statistics': city_stats,
                'value_distribution': value_distribution,
                'image_statistics': image_stats,
                'data_summary': {
                    'total_properties': Account.query.count(),
                    'cities_count': len(city_stats),
                    'property_types_count': len(property_type_stats)
                }
            }
            
            logger.info("Generated comprehensive statistics package")
            return all_stats
            
        except Exception as e:
            logger.error(f"Error generating all statistics: {str(e)}")
            return {}

if __name__ == "__main__":
    # Generate all statistics
    all_stats = generate_all_statistics()
    
    # Print summary
    if all_stats:
        logger.info("=== Property Statistics Summary ===")
        logger.info(f"Total properties: {all_stats['data_summary']['total_properties']}")
        logger.info(f"Cities with data: {all_stats['data_summary']['cities_count']}")
        logger.info(f"Property types: {all_stats['data_summary']['property_types_count']}")
        
        # Print property type statistics
        logger.info("\n=== Property Type Statistics ===")
        for prop_type, stats in all_stats['property_type_statistics'].items():
            logger.info(f"{prop_type}: {stats['count']} properties, Avg value: ${stats['average_value']:,.2f}")
        
        # Print value distribution
        logger.info("\n=== Value Distribution ===")
        for range_label, count in all_stats['value_distribution'].items():
            logger.info(f"{range_label}: {count} properties")
    else:
        logger.warning("No statistics were generated")