"""
Retirement Home for Horses Management System
Flask Backend - Authentication Module
Simple authentication with admin, editor, and viewer roles
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps
import re

# --- CONFIGURATION ---
app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your_secret_key_change_this_in_production'
app.config['JWT_EXPIRATION_HOURS'] = 24

# Database Connection - Using MongoDB
URI = "mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary"
DB_NAME = "Data"

# Permission levels
PERMISSION_LEVELS = {
    'admin': 3,      # Administrator (Paul)
    'editor': 2,     # Editor (Ann, Amy, Nicole)
    'viewer': 1      # Viewer (All other volunteers)
}

# MongoDB Connection
try:
    client = MongoClient(URI, server_api=ServerApi('1'))
    db = client[DB_NAME]
    
    # Collections
    users_collection = db['users']  # Passwords stored here
    user_tables_collection = db['User_Tables']  # User info (no password)
    user_logins_collection = db['User_Logins']  # Login history
    audits_collection = db['Audits']  # Audit trail
    
    # Create indexes
    users_collection.create_index('email', unique=True)
    user_logins_collection.create_index('user_id')
    user_logins_collection.create_index('timestamp')
    audits_collection.create_index('timestamp')
    audits_collection.create_index('user_id')
    
    print(f"✅ Connected to MongoDB Database: {DB_NAME}")
except Exception as e:
    print(f"❌ Database Connection Failed: {e}")
    raise

# --- HELPER FUNCTIONS ---

def log_audit(user_id, action, table_name, details=None):
    """Log changes to audit trail"""
    try:
        audit_doc = {
            'timestamp': datetime.utcnow(),
            'user_id': str(user_id) if user_id else None,
            'action': action,
            'table': table_name,
            'details': details
        }
        audits_collection.insert_one(audit_doc)
    except Exception as e:
        print(f"⚠️ Audit log error: {e}")

# --- HELPER FUNCTIONS ---

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password (minimum 6 characters)"""
    return len(password) >= 6

def verify_token(token):
    """Verify JWT token and return user data"""
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return data
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# --- DECORATORS ---

def token_required(f):
    """Decorator to check if user has valid token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            token = token.split(' ')[1] if ' ' in token else token
            user_data = verify_token(token)
            if not user_data:
                return jsonify({'error': 'Invalid or expired token'}), 401
            request.user_id = user_data['user_id']
            request.user_role = user_data['role']
        except:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated

def permission_required(required_level):
    """Decorator to check user permission level"""
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            user_role = request.user_role
            if PERMISSION_LEVELS.get(user_role, 0) < required_level:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# --- AUTHENTICATION ROUTES ---

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        phone = data.get('phone')
        
        # Validation
        if not email or not password or not name:
            return jsonify({'error': 'Email, password, and name are required'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if not validate_password(password):
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Check if user exists
        if users_collection.find_one({'email': email}):
            return jsonify({'error': 'Email already registered'}), 409
        
        # 1. Create password record in users collection
        user_password_doc = {
            'email': email,
            'password': generate_password_hash(password),
            'created_at': datetime.utcnow()
        }
        password_result = users_collection.insert_one(user_password_doc)
        user_id = password_result.inserted_id
        
        # 2. Create user info record in User_Tables (no password)
        user_info_doc = {
            '_id': user_id,
            'email': email,
            'name': name,
            'phone': phone,
            'role': 'viewer',  # Default role
            'is_admin': False,
            'can_edit': False,
            'can_view': True,
            'active': True,
            'created_at': datetime.utcnow(),
            'last_login': None
        }
        user_tables_collection.insert_one(user_info_doc)
        
        # 3. Log to audit trail
        log_audit(user_id, 'REGISTER', 'User_Tables', {'email': email, 'name': name})
        
        return jsonify({'message': 'User registered successfully', 'user_id': str(user_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        user = users_collection.find_one({'email': email})
        if not user or not check_password_hash(user['password'], password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        user_id = user['_id']
        
        # Get user info from User_Tables
        user_info = user_tables_collection.find_one({'_id': user_id})
        if not user_info or not user_info.get('active'):
            return jsonify({'error': 'User account is inactive'}), 403
        
        # 1. Log login to User_Logins collection
        login_record = {
            'user_id': user_id,
            'email': email,
            'timestamp': datetime.utcnow(),
            'ip_address': request.remote_addr
        }
        user_logins_collection.insert_one(login_record)
        
        # 2. Update last_login in User_Tables
        user_tables_collection.update_one(
            {'_id': user_id},
            {'$set': {'last_login': datetime.utcnow()}}
        )
        
        # 3. Log to audit trail
        log_audit(user_id, 'LOGIN', 'User_Logins', {'email': email})
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': str(user_id),
            'email': user_info['email'],
            'role': user_info['role'],
            'exp': datetime.utcnow() + timedelta(hours=app.config['JWT_EXPIRATION_HOURS'])
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user': {
                'id': str(user_id),
                'email': user_info['email'],
                'name': user_info['name'],
                'role': user_info['role']
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- UTILITY ROUTES ---

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200

@app.route('/', methods=['GET'])
def home():
    """Home endpoint"""
    return jsonify({
        'status': 'online',
        'message': 'Retirement Home for Horses Backend - Authentication Module',
        'version': '1.0.0'
    }), 200

# --- ERROR HANDLERS ---

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# --- RUN SERVER ---
if __name__ == '__main__':
    print("🚀 Starting Retirement Home for Horses Backend")
    print("📚 Authentication module running on http://localhost:5000")
    print("📋 Roles: admin (Paul), editor (Ann, Amy, Nicole), viewer (all others)")
    app.run(debug=True, host='0.0.0.0', port=5000)
