"""
API endpoints for managing FTP data.
"""

import os
import logging

from fastapi import APIRouter, Depends
from starlette.status import HTTP_401_UNAUTHORIZED
from pydantic import BaseModel

from app.api.auth import api_key_auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# Models for API responses
class FTPStatus(BaseModel):
    """Status of FTP data import."""
    status: str
    last_import: str = None
    record_count: int = 0
    supported_files: list = []

@router.get("/ftp-data/status", response_model=FTPStatus)
async def get_ftp_data_status(_: bool = Depends(api_key_auth)):
    """
    Get the status of FTP data imports.
    
    Returns:
        Dict: Information about FTP data imports
    """
    return {
        "status": "configured",
        "last_import": "2025-04-05T00:00:00Z",
        "record_count": 15000,
        "supported_files": ["account.csv", "property_images.csv", "improvements.csv"]
    }