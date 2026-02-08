from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from bson.objectid import ObjectId

# --- CONFIGURATION ---
app = Flask(__name__)
# CRITICAL FIX: This allows your HTML file (running in browser) to talk to this Python script
CORS(app) 

# Database Connection
URI = "mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary"
DB_NAME = "Data"

try:
    client = MongoClient(URI, server_api=ServerApi('1'))
    db = client[DB_NAME]
    user_logins = db['User_Logins'] 
    print(f"✅ CONNECTED TO: {DB_NAME}.User_Logins")
except Exception as e:
    print(f"❌ DATABASE CONNECTION FAILED: {e}")

# --- ROUTES ---

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "User Auth System Running"})

# 1. REGISTER (New User)
@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        print(f"📝 Received Registration Request: {data.get('email')}") # Debug print
        
        # Extract fields
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        phone = data.get('phone')

        # Basic Validation
        if not email or not password or not first_name or not last_name:
            return jsonify({'error': 'All fields are required.'}), 400

        # Check if user already exists
        if user_logins.find_one({'email': email}):
            return jsonify({'error': 'This email is already registered.'}), 409

        # Create User Document
        new_user = {
            'email': email,
            'password': generate_password_hash(password), # SECURITY: Hash the password
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            
            # System Fields (Automatic)
            'role': 'user',          # Default role
            'is_active': True,       # As requested
            'created_at': datetime.utcnow(),
            'last_login': None
        }

        result = user_logins.insert_one(new_user)
        print(f"✅ User Created: {result.inserted_id}")
        
        return jsonify({'message': 'Account created successfully!'}), 201

    except Exception as e:
        print(f"❌ Error in Register: {e}")
        return jsonify({'error': str(e)}), 500

# 2. LOGIN (Returning User)
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        print(f"🔑 Login Attempt: {email}") # Debug print

        if not email or not password:
            return jsonify({'error': 'Email and password required.'}), 400

        # Find user
        user = user_logins.find_one({'email': email})

        if not user:
            print("❌ User not found")
            return jsonify({'error': 'Incorrect email or password.'}), 401
        
        # Verify Password
        if not check_password_hash(user['password'], password):
            print("❌ Password incorrect")
            return jsonify({'error': 'Incorrect email or password.'}), 401
            
        # Update 'last_login' field
        user_logins.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.utcnow()}}
        )

        print("✅ Login Successful")
        return jsonify({
            'message': 'Login successful',
            'user': {
                'first_name': user['first_name'],
                'role': user['role']
            }
        }), 200

    except Exception as e:
        print(f"❌ Error in Login: {e}")
        return jsonify({'error': str(e)}), 500

# --- RUN SERVER ---
if __name__ == '__main__':
    # Force port 5000 to match the HTML file
    app.run(debug=True, port=5000)