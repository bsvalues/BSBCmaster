"""
This file provides a WSGI adapter for our Flask application.
It allows running the Flask application with Gunicorn.
"""

# Import database and models to ensure tables are created
from database import app, db

# Import seed script to populate database
import seed_database
seed_database.seed_database()

# For Gunicorn
application = app