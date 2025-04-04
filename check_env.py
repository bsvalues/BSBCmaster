#!/usr/bin/env python3
"""
This script checks if required environment variables are set.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define required environment variables
REQUIRED_VARS = [
    "DATABASE_URL",
    "PGPORT",
    "PGUSER", 
    "PGPASSWORD",
    "PGDATABASE",
    "PGHOST",
    "API_KEY",
    "OPENAI_API_KEY"
]

def check_environment():
    """Check if required environment variables are set."""
    missing = []
    for var in REQUIRED_VARS:
        value = os.environ.get(var)
        if not value:
            missing.append(var)
        else:
            # Show first and last 4 characters of value with * in between for secrets
            masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "****"
            print(f"{var} is set: {masked_value}")
    
    if missing:
        print("\nWARNING: The following environment variables are not set:")
        for var in missing:
            print(f"  - {var}")
        print("\nPlease set these variables in your .env file or environment.")
    else:
        print("\nAll required environment variables are set!")

if __name__ == "__main__":
    check_environment()