"""
MCP Assessor Agent API - FastAPI Application
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI(
    title="MCP Assessor Agent API",
    description="Property Assessment Data Query API",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include API routers
from app.api.auth import router as auth_router
from app.api.ftp_data import router as ftp_router
from app.api.imported_data import router as imported_data_router

app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(ftp_router, prefix="/api", tags=["ftp-data"])
app.include_router(imported_data_router, prefix="/api", tags=["imported-data"])

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}