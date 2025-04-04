import os
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# create the SQLAlchemy instance
db = SQLAlchemy()

def create_app():
    # create the app
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
    CORS(app)  # Enable CORS for all routes
    
    # configure the database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # initialize extensions
    db.init_app(app)
    
    # define routes
    @app.route('/')
    def index():
        """Render the index page with API documentation."""
        context = {
            'title': 'MCP Assessor Agent API',
            'version': '1.0.0',
            'description': 'A secure FastAPI intermediary service for efficient and safe database querying across multiple database systems, with a focus on real estate property data management and analysis.',
            'api_key_header': 'X-API-Key',
            'base_url': request.host_url.rstrip('/')
        }
        return render_template('index.html', **context)
    
    @app.route('/api/health')
    def health_check():
        """Check the health of the API and its database connections."""
        # For now, just return a success response
        return jsonify({
            'status': 'success',
            'message': 'API is running',
            'database_status': {
                'postgres': True
            }
        })
    
    return app

# Import this at the bottom to avoid circular imports
from flask import request