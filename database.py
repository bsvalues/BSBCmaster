import os
import datetime
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# Initialize the Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS

# Configure the app settings
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the SQLAlchemy extension
db = SQLAlchemy(app)

# Define routes
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
    # Check database connection
    db_healthy = True
    try:
        # Execute a simple query
        db.session.execute('SELECT 1')
    except Exception as e:
        db_healthy = False
    
    return jsonify({
        'status': 'success' if db_healthy else 'error',
        'message': 'API is running',
        'database_status': {
            'postgres': db_healthy
        }
    })

@app.route('/api/parcels')
def get_parcels():
    """Get a list of parcels with optional filtering."""
    try:
        # Get query parameters for filtering
        city = request.args.get('city')
        state = request.args.get('state')
        min_value = request.args.get('min_value', type=float)
        max_value = request.args.get('max_value', type=float)
        
        # Start with base query
        query = Parcel.query
        
        # Apply filters if provided
        if city:
            query = query.filter(Parcel.city == city)
        if state:
            query = query.filter(Parcel.state == state)
        if min_value:
            query = query.filter(Parcel.total_value >= min_value)
        if max_value:
            query = query.filter(Parcel.total_value <= max_value)
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Execute paginated query
        paginated = query.paginate(page=page, per_page=per_page)
        
        # Format results
        results = []
        for parcel in paginated.items:
            results.append({
                'id': parcel.id,
                'parcel_id': parcel.parcel_id,
                'address': parcel.address,
                'city': parcel.city,
                'state': parcel.state,
                'zip_code': parcel.zip_code,
                'total_value': float(parcel.total_value),
                'assessment_year': parcel.assessment_year,
                'latitude': parcel.latitude,
                'longitude': parcel.longitude
            })
        
        # Return response with pagination metadata
        return jsonify({
            'status': 'success',
            'data': results,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_items': paginated.total,
                'total_pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/parcels/<int:parcel_id>')
def get_parcel(parcel_id):
    """Get detailed information about a specific parcel."""
    try:
        # Get the parcel by ID
        parcel = Parcel.query.get_or_404(parcel_id)
        
        # Format property details
        property_details = []
        for prop in parcel.property_details:
            property_details.append({
                'id': prop.id,
                'property_type': prop.property_type,
                'year_built': prop.year_built,
                'square_footage': prop.square_footage,
                'bedrooms': prop.bedrooms,
                'bathrooms': prop.bathrooms,
                'lot_size': prop.lot_size,
                'lot_size_unit': prop.lot_size_unit,
                'condition': prop.condition,
                'quality': prop.quality,
                'tax_district': prop.tax_district,
                'zoning': prop.zoning
            })
        
        # Format sales history
        sales_history = []
        for sale in parcel.sales:
            sales_history.append({
                'id': sale.id,
                'sale_date': sale.sale_date.isoformat(),
                'sale_price': float(sale.sale_price),
                'sale_type': sale.sale_type,
                'transaction_id': sale.transaction_id,
                'buyer_name': sale.buyer_name,
                'seller_name': sale.seller_name,
                'financing_type': sale.financing_type
            })
        
        # Sort sales by date (newest first)
        sales_history.sort(key=lambda x: x['sale_date'], reverse=True)
        
        # Assemble the full parcel data
        result = {
            'id': parcel.id,
            'parcel_id': parcel.parcel_id,
            'address': parcel.address,
            'city': parcel.city,
            'state': parcel.state,
            'zip_code': parcel.zip_code,
            'land_value': float(parcel.land_value),
            'improvement_value': float(parcel.improvement_value),
            'total_value': float(parcel.total_value),
            'assessment_year': parcel.assessment_year,
            'latitude': parcel.latitude,
            'longitude': parcel.longitude,
            'property_details': property_details,
            'sales_history': sales_history,
            'created_at': parcel.created_at.isoformat(),
            'updated_at': parcel.updated_at.isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/schema')
def get_schema():
    """Get database schema details for parcels, properties, and sales tables."""
    try:
        schema = {
            'parcels': {
                'name': 'parcels',
                'description': 'Real estate parcel information (main assessment record)',
                'columns': [
                    {'name': 'id', 'type': 'integer', 'primary_key': True},
                    {'name': 'parcel_id', 'type': 'string', 'unique': True},
                    {'name': 'address', 'type': 'string'},
                    {'name': 'city', 'type': 'string'},
                    {'name': 'state', 'type': 'string'},
                    {'name': 'zip_code', 'type': 'string'},
                    {'name': 'land_value', 'type': 'numeric'},
                    {'name': 'improvement_value', 'type': 'numeric'},
                    {'name': 'total_value', 'type': 'numeric'},
                    {'name': 'assessment_year', 'type': 'integer'},
                    {'name': 'latitude', 'type': 'float'},
                    {'name': 'longitude', 'type': 'float'},
                    {'name': 'created_at', 'type': 'datetime'},
                    {'name': 'updated_at', 'type': 'datetime'}
                ],
                'relationships': [
                    {'name': 'property_details', 'target': 'properties', 'type': 'one-to-many'},
                    {'name': 'sales', 'target': 'sales', 'type': 'one-to-many'}
                ]
            },
            'properties': {
                'name': 'properties',
                'description': 'Physical property characteristics',
                'columns': [
                    {'name': 'id', 'type': 'integer', 'primary_key': True},
                    {'name': 'parcel_id', 'type': 'integer', 'foreign_key': 'parcels.id'},
                    {'name': 'property_type', 'type': 'string'},
                    {'name': 'year_built', 'type': 'integer'},
                    {'name': 'square_footage', 'type': 'integer'},
                    {'name': 'bedrooms', 'type': 'integer'},
                    {'name': 'bathrooms', 'type': 'float'},
                    {'name': 'lot_size', 'type': 'float'},
                    {'name': 'lot_size_unit', 'type': 'string'},
                    {'name': 'stories', 'type': 'float'},
                    {'name': 'condition', 'type': 'string'},
                    {'name': 'quality', 'type': 'string'},
                    {'name': 'tax_district', 'type': 'string'},
                    {'name': 'zoning', 'type': 'string'},
                    {'name': 'created_at', 'type': 'datetime'},
                    {'name': 'updated_at', 'type': 'datetime'}
                ],
                'relationships': [
                    {'name': 'parcel', 'target': 'parcels', 'type': 'many-to-one'}
                ]
            },
            'sales': {
                'name': 'sales',
                'description': 'Property sale transaction history',
                'columns': [
                    {'name': 'id', 'type': 'integer', 'primary_key': True},
                    {'name': 'parcel_id', 'type': 'integer', 'foreign_key': 'parcels.id'},
                    {'name': 'sale_date', 'type': 'date'},
                    {'name': 'sale_price', 'type': 'numeric'},
                    {'name': 'sale_type', 'type': 'string'},
                    {'name': 'transaction_id', 'type': 'string'},
                    {'name': 'buyer_name', 'type': 'string'},
                    {'name': 'seller_name', 'type': 'string'},
                    {'name': 'financing_type', 'type': 'string'},
                    {'name': 'created_at', 'type': 'datetime'},
                    {'name': 'updated_at', 'type': 'datetime'}
                ],
                'relationships': [
                    {'name': 'parcel', 'target': 'parcels', 'type': 'many-to-one'}
                ]
            }
        }
        
        return jsonify({
            'status': 'success',
            'schema': schema
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Model definitions
class Parcel(db.Model):
    """Real estate parcel information (main assessment record)."""
    __tablename__ = 'parcels'
    
    id = db.Column(db.Integer, primary_key=True)
    parcel_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    
    # Assessment values
    land_value = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    improvement_value = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total_value = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    assessment_year = db.Column(db.Integer, nullable=False)
    
    # Geographic info
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    property_details = db.relationship('Property', backref='parcel', lazy=True, cascade="all, delete-orphan")
    sales = db.relationship('Sale', backref='parcel', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Parcel {self.parcel_id} at {self.address}>"

class Property(db.Model):
    """Physical property characteristics."""
    __tablename__ = 'properties'
    
    id = db.Column(db.Integer, primary_key=True)
    parcel_id = db.Column(db.Integer, db.ForeignKey('parcels.id'), nullable=False)
    
    # Property characteristics
    property_type = db.Column(db.String(50), nullable=False)
    year_built = db.Column(db.Integer, nullable=True)
    square_footage = db.Column(db.Integer, nullable=True)
    bedrooms = db.Column(db.Integer, nullable=True)
    bathrooms = db.Column(db.Float, nullable=True)
    lot_size = db.Column(db.Float, nullable=True)
    lot_size_unit = db.Column(db.String(20), nullable=True)
    stories = db.Column(db.Float, nullable=True)
    condition = db.Column(db.String(50), nullable=True)
    quality = db.Column(db.String(50), nullable=True)
    
    # Tax info
    tax_district = db.Column(db.String(50), nullable=True)
    zoning = db.Column(db.String(50), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<Property {self.id} - {self.property_type} {self.square_footage}sqft>"

class Sale(db.Model):
    """Property sale transaction history."""
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    parcel_id = db.Column(db.Integer, db.ForeignKey('parcels.id'), nullable=False)
    
    # Transaction details
    sale_date = db.Column(db.Date, nullable=False)
    sale_price = db.Column(db.Numeric(12, 2), nullable=False)
    sale_type = db.Column(db.String(50), nullable=True)
    transaction_id = db.Column(db.String(50), nullable=True)
    
    # Buyer/Seller info
    buyer_name = db.Column(db.String(255), nullable=True)
    seller_name = db.Column(db.String(255), nullable=True)
    
    # Financing
    financing_type = db.Column(db.String(50), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<Sale {self.id} - ${self.sale_price} on {self.sale_date}>"

# Create the database tables if they don't exist
with app.app_context():
    db.create_all()
    print("Database tables created successfully")