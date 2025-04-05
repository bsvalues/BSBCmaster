"""
API endpoints for querying imported assessment data.
"""

import os
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from sqlalchemy import select, func, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import api_key_auth
from app_setup import app, db
from models import Account, PropertyImage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

@router.get("/imported-data/accounts")
async def get_accounts(
    limit: int = Query(100, description="Maximum number of accounts to return"),
    offset: int = Query(0, description="Number of accounts to skip"),
    search: str = Query(None, description="Search term for account names"),
    _: bool = Depends(api_key_auth)
):
    """
    Get a list of imported accounts.
    
    Args:
        limit: Maximum number of accounts to return
        offset: Number of accounts to skip
        search: Search term for account names
        
    Returns:
        Dict: List of accounts and total count
    """
    try:
        with app.app_context():
            # Base query
            query = select(Account)
            count_query = select(func.count()).select_from(Account)
            
            # Apply search filter if provided
            if search:
                search_term = f"%{search}%"
                query = query.filter(Account.owner_name.ilike(search_term))
                count_query = count_query.filter(Account.owner_name.ilike(search_term))
            
            # Get total count
            total_count = db.session.execute(count_query).scalar()
            
            # Apply pagination
            query = query.order_by(Account.id).limit(limit).offset(offset)
            
            # Execute query
            accounts = db.session.execute(query).scalars().all()
            
            # Convert to dictionaries
            accounts_data = []
            for account in accounts:
                accounts_data.append({
                    "id": account.id,
                    "account_id": account.account_id,
                    "owner_name": account.owner_name,
                    "property_address": account.property_address,
                    "property_city": account.property_city,
                    "mailing_address": account.mailing_address,
                    "mailing_city": account.mailing_city,
                    "mailing_state": account.mailing_state,
                    "mailing_zip": account.mailing_zip,
                    "assessment_year": account.assessment_year,
                    "assessed_value": float(account.assessed_value) if account.assessed_value else None,
                    "tax_amount": float(account.tax_amount) if account.tax_amount else None,
                    "tax_status": account.tax_status
                })
            
            return {
                "accounts": accounts_data,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
    
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving accounts: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving accounts: {str(e)}"
        )

@router.get("/imported-data/accounts/{account_id}")
async def get_account(
    account_id: str,
    _: bool = Depends(api_key_auth)
):
    """
    Get details for a specific account.
    
    Args:
        account_id: The account ID to retrieve
        
    Returns:
        Dict: Account details
    """
    try:
        with app.app_context():
            # Query the account
            account = db.session.query(Account).filter(Account.account_id == account_id).first()
            
            if not account:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=f"Account not found: {account_id}"
                )
            
            # Convert to dictionary
            return {
                "id": account.id,
                "account_id": account.account_id,
                "owner_name": account.owner_name,
                "property_address": account.property_address,
                "property_city": account.property_city,
                "legal_description": account.legal_description,
                "mailing_address": account.mailing_address,
                "mailing_city": account.mailing_city,
                "mailing_state": account.mailing_state,
                "mailing_zip": account.mailing_zip,
                "assessment_year": account.assessment_year,
                "assessed_value": float(account.assessed_value) if account.assessed_value else None,
                "tax_amount": float(account.tax_amount) if account.tax_amount else None,
                "tax_status": account.tax_status,
                "created_at": account.created_at.isoformat() if account.created_at else None,
                "updated_at": account.updated_at.isoformat() if account.updated_at else None
            }
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving account: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving account: {str(e)}"
        )

@router.get("/imported-data/property-images")
async def get_property_images(
    limit: int = Query(100, description="Maximum number of images to return"),
    offset: int = Query(0, description="Number of images to skip"),
    property_id: str = Query(None, description="Filter by property ID"),
    image_type: str = Query(None, description="Filter by image type"),
    _: bool = Depends(api_key_auth)
):
    """
    Get a list of property images.
    
    Args:
        limit: Maximum number of images to return
        offset: Number of images to skip
        property_id: Filter by property ID
        image_type: Filter by image type
        
    Returns:
        Dict: List of property images and total count
    """
    try:
        with app.app_context():
            # Base query
            query = select(PropertyImage)
            count_query = select(func.count()).select_from(PropertyImage)
            
            # Apply filters if provided
            if property_id:
                query = query.filter(PropertyImage.property_id == property_id)
                count_query = count_query.filter(PropertyImage.property_id == property_id)
            
            if image_type:
                query = query.filter(PropertyImage.image_type == image_type)
                count_query = count_query.filter(PropertyImage.image_type == image_type)
            
            # Get total count
            total_count = db.session.execute(count_query).scalar()
            
            # Apply pagination
            query = query.order_by(PropertyImage.id).limit(limit).offset(offset)
            
            # Execute query
            images = db.session.execute(query).scalars().all()
            
            # Convert to dictionaries
            images_data = []
            for image in images:
                images_data.append({
                    "id": image.id,
                    "property_id": image.property_id,
                    "account_id": image.account_id,
                    "image_url": image.image_url,
                    "image_path": image.image_path,
                    "image_type": image.image_type,
                    "image_date": image.image_date.isoformat() if image.image_date else None,
                    "width": image.width,
                    "height": image.height,
                    "file_size": image.file_size,
                    "file_format": image.file_format
                })
            
            return {
                "property_images": images_data,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
    
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving property images: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving property images: {str(e)}"
        )

@router.get("/imported-data/improvements")
async def get_improvements(
    limit: int = Query(100, description="Maximum number of improvements to return"),
    offset: int = Query(0, description="Number of improvements to skip"),
    property_id: str = Query(None, description="Filter by property ID"),
    _: bool = Depends(api_key_auth)
):
    """
    Get a list of property improvements.
    
    Args:
        limit: Maximum number of improvements to return
        offset: Number of improvements to skip
        property_id: Filter by property ID
        
    Returns:
        Dict: List of property improvements and total count
    """
    try:
        with app.app_context():
            # Use raw SQL query since we don't have a model for improvements
            query = text("""
                SELECT * FROM improvements
                WHERE (:property_id IS NULL OR prop_id = :property_id)
                ORDER BY imprv_id
                LIMIT :limit OFFSET :offset
            """)
            
            count_query = text("""
                SELECT COUNT(*) FROM improvements
                WHERE (:property_id IS NULL OR prop_id = :property_id)
            """)
            
            # Execute queries
            improvements = db.session.execute(
                query, 
                {"property_id": property_id, "limit": limit, "offset": offset}
            ).fetchall()
            
            total_count = db.session.execute(
                count_query,
                {"property_id": property_id}
            ).scalar()
            
            # Convert to dictionaries
            improvements_data = []
            for row in improvements:
                improvements_data.append({
                    "property_id": row.prop_id,
                    "improvement_id": row.imprv_id,
                    "description": row.imprv_desc,
                    "value": float(row.imprv_val) if row.imprv_val else None,
                    "living_area": row.living_area,
                    "primary_use_code": row.primary_use_cd,
                    "stories": row.stories,
                    "year_built": row.actual_year_built
                })
            
            return {
                "improvements": improvements_data,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
    
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving improvements: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving improvements: {str(e)}"
        )