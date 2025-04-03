"""
This file provides a WSGI adapter for our Flask application.
It allows running the Flask application with Gunicorn.
"""

from main import app

# For Gunicorn
application = app