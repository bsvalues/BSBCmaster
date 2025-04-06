"""
Import Improvements Data in Segments

This script extends the minimal import approach to process a larger dataset
by dividing it into segments and importing each segment separately.
"""

import os
import logging
import sys
import time
from datetime import datetime
import pandas as pd
from decimal import Decimal
from app_setup import app, db, create_tables
from models import Parcel, Property

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_segment(df, commit_every=5):
    """
    Import a segment of improvements data.
    
    Args:
        df: DataFrame segment to import
        commit_every: Number of records to process before committing
        
    Returns:
        Dictionary with counts of parcels and properties created
    """
    parcels_created = 0
    properties_created = 0
    
    try:
        with app.app_context():
            # Process each record
            records_processed = 0
            
            for _, row in df.iterrows():
                # Create parcel first
                prop_id = str(row.get('prop_id', ''))
                if not prop_id or prop_id == 'nan':
                    continue
                
                # Check if parcel already exists
                existing_parcel = db.session.query(Parcel).filter_by(parcel_id=prop_id).first()
                
                if not existing_parcel:
                    # Create a new parcel
                    parcel = Parcel(
                        parcel_id=prop_id,
                        address=f"Property {prop_id}",
                        city="Unknown",
                        state="WA",
                        zip_code="99999",
                        land_value=0,
                        improvement_value=0,
                        total_value=0,
                        assessment_year=datetime.now().year
                    )
                    db.session.add(parcel)
                    db.session.flush()  # Get ID without committing
                    parcels_created += 1
                    parcel_id = parcel.id
                else:
                    parcel_id = existing_parcel.id
                
                # Now create property
                try:
                    # Process values carefully
                    property_type = "Unknown"
                    primary_use_cd = str(row.get('primary_use_cd', ''))
                    if primary_use_cd == '81':
                        property_type = "Residential"
                    elif primary_use_cd == '83':
                        property_type = "Commercial"
                    
                    # Optional fields with validation
                    try:
                        living_area = int(float(row.get('living_area'))) if pd.notna(row.get('living_area')) else None
                        if living_area and (living_area < 0 or living_area > 100000):
                            living_area = None
                    except (ValueError, TypeError):
                        living_area = None
                        
                    try:
                        stories = float(row.get('stories')) if pd.notna(row.get('stories')) else None
                        if stories and (stories < 0 or stories > 100):
                            stories = None
                    except (ValueError, TypeError):
                        stories = None
                        
                    try:
                        actual_year_built = int(float(row.get('actual_year_built'))) if pd.notna(row.get('actual_year_built')) else None
                        if actual_year_built and (actual_year_built < 1800 or actual_year_built > 2100):
                            actual_year_built = None
                    except (ValueError, TypeError):
                        actual_year_built = None
                    
                    # Create property with validated fields
                    property = Property(
                        parcel_id=parcel_id,
                        property_type=property_type,
                        year_built=actual_year_built,
                        square_footage=living_area,
                        stories=stories
                    )
                    db.session.add(property)
                    properties_created += 1
                    
                    # Process improvement value
                    try:
                        imprv_val = Decimal(str(row.get('imprv_val'))) if pd.notna(row.get('imprv_val')) else Decimal('0')
                        if imprv_val > 0:
                            parcel = db.session.get(Parcel, parcel_id)
                            if parcel:
                                parcel.improvement_value += imprv_val
                                parcel.total_value += imprv_val
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Skipping improvement value: {str(e)}")
                
                except Exception as e:
                    logger.warning(f"Error creating property: {str(e)}")
                    continue
                
                # Commit every N records to avoid timeouts
                records_processed += 1
                if records_processed % commit_every == 0:
                    db.session.commit()
                    logger.info(f"Committed {records_processed} records")
            
            # Final commit for any remaining records
            db.session.commit()
            
            return {'parcels': parcels_created, 'properties': properties_created}
    
    except Exception as e:
        logger.error(f"Error importing segment: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        return {'parcels': 0, 'properties': 0}

def import_in_segments(filename='ftp_dl_imprv.csv', segment_size=20, num_segments=5, clear_existing=True):
    """
    Import improvements data in segments.
    
    Args:
        filename: Name of the improvements CSV file
        segment_size: Number of records per segment
        num_segments: Number of segments to process
        clear_existing: Whether to clear existing data
        
    Returns:
        Dictionary with counts of parcels and properties created
    """
    start_time = time.time()
    csv_path = os.path.join('attached_assets', filename)
    logger.info(f"Importing in segments from {csv_path}")
    logger.info(f"Parameters: segment_size={segment_size}, num_segments={num_segments}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return {'parcels': 0, 'properties': 0}
    
    # Clear existing data if requested
    if clear_existing:
        try:
            with app.app_context():
                db.session.query(Property).delete()
                db.session.query(Parcel).delete()
                db.session.commit()
                logger.info("Cleared existing parcel and property records")
        except Exception as e:
            logger.error(f"Failed to clear data: {str(e)}")
            return {'parcels': 0, 'properties': 0}
    
    # Process segments
    total_rows = segment_size * num_segments
    total_parcels = 0
    total_properties = 0
    segments_processed = 0
    
    try:
        for i in range(num_segments):
            segment_start = time.time()
            skip_rows = i * segment_size
            
            # Read the segment
            df = pd.read_csv(csv_path, skiprows=range(1, skip_rows + 1), nrows=segment_size, 
                           header=0, encoding='latin1')
            
            if len(df) == 0:
                logger.info(f"No more rows to read at segment {i+1}")
                break
                
            # Convert column names to lowercase
            df.columns = [col.lower() for col in df.columns]
            
            logger.info(f"Processing segment {i+1} of {num_segments} ({len(df)} rows)")
            
            # Import this segment
            results = import_segment(df, commit_every=5)
            
            total_parcels += results['parcels']
            total_properties += results['properties']
            segments_processed += 1
            
            segment_time = time.time() - segment_start
            logger.info(f"Segment {i+1}: Created {results['parcels']} parcels and {results['properties']} properties " +
                       f"(took {segment_time:.2f}s)")
            
            # Small delay between segments
            time.sleep(0.5)
        
        total_time = time.time() - start_time
        logger.info(f"Import complete: processed {segments_processed} segments in {total_time:.2f}s")
        logger.info(f"Created {total_parcels} parcels and {total_properties} properties")
        
        return {'parcels': total_parcels, 'properties': total_properties}
    
    except Exception as e:
        logger.error(f"Error importing improvements: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {'parcels': total_parcels, 'properties': total_properties}

if __name__ == "__main__":
    with app.app_context():
        # Ensure tables exist
        create_tables()
        
        # Default parameters
        segment_size = 20  # Default: 20 records per segment
        num_segments = 5   # Default: process 5 segments
        
        # Parse command line arguments
        if len(sys.argv) > 1:
            try:
                num_segments = int(sys.argv[1])
                logger.info(f"Using command line argument: {num_segments} segments")
            except ValueError:
                pass
                
        if len(sys.argv) > 2:
            try:
                segment_size = int(sys.argv[2])
                logger.info(f"Using command line argument: {segment_size} records per segment")
            except ValueError:
                pass
        
        # Run the segmented import
        results = import_in_segments(
            segment_size=segment_size,
            num_segments=num_segments
        )
        
        logger.info(f"Import completed: {results}")
        
        # Check if it was successful
        if results['parcels'] > 0 and results['properties'] > 0:
            logger.info("SUCCESS: Import worked correctly!")
        else:
            logger.error("FAILED: Import did not create any records!")