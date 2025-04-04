import os
import time
import logging
import datetime
import psycopg2
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# create the SQLAlchemy instance
db = SQLAlchemy()

# Track application start time
START_TIME = time.time()

def create_app():
    # create the app
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
    CORS(app)  # Enable CORS for all routes
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # configure the database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Set jinja template options
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    
    # initialize extensions
    db.init_app(app)
    
    # define routes
    @app.route('/')
    def index():
        """Render the index page with API documentation."""
        return render_template('index.html')
    
    @app.route('/api/health')
    def health_check():
        """Check the health of the API and its database connections."""
        try:
            # Test database connection
            db_status = False
            db_error = None
            
            try:
                with app.app_context():
                    # Test SQLAlchemy connection
                    db.session.execute("SELECT 1")
                    db_status = True
            except Exception as e:
                db_error = str(e)
                app.logger.error(f"Database connection error: {e}")
            
            # Get database version
            db_version = None
            try:
                with app.app_context():
                    result = db.session.execute("SELECT version();").fetchone()
                    if result:
                        db_version = result[0]
            except Exception as e:
                app.logger.error(f"Error getting database version: {e}")
            
            # Calculate uptime
            uptime = time.time() - START_TIME
            
            return jsonify({
                'status': 'success',
                'message': 'API is running',
                'database_status': {
                    'postgres': db_status
                },
                'databases': [
                    {
                        'name': 'postgres',
                        'type': 'PostgreSQL',
                        'version': db_version,
                        'connected': db_status,
                        'error': db_error
                    }
                ],
                'api_version': '1.0.0',
                'uptime': uptime,
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
        
        except Exception as e:
            app.logger.error(f"Health check error: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Error during health check: {str(e)}',
                'database_status': {
                    'postgres': False
                },
                'timestamp': datetime.datetime.utcnow().isoformat()
            }), 500
    
    # Add error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', error=str(e), code=404), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', error=str(e), code=500), 500
    
    return app