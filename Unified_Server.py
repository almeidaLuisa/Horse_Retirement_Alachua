from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime

# --- CONFIGURATION ---
app = Flask(__name__)
# Allow CORS for all domains
CORS(app)

# Database Connection
URI = "mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary"
DB_NAME = "Data"

try:
    client = MongoClient(URI, server_api=ServerApi('1'))
    db = client[DB_NAME]
    
    # Collections
    user_logins = db['User_Logins']
    horse_collection = db['Horse_Tables']
    audit_collection = db['Audits']
    # RESTORED: Daily Obs Collection
    daily_obs_collection = db['DailyObs_Tables']
    
    print(f"✅ UNIFIED SERVER CONNECTED to {DB_NAME}")
except Exception as e:
    print(f"❌ DATABASE CONNECTION FAILED: {e}")

# --- HELPERS ---
def format_doc(doc):
    if not doc: return None
    doc['_id'] = str(doc['_id'])
    return doc

# --- ROOT ---
@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "Unified Horse Server is Running!"})


# ==========================================
#      SECTION 1: USER AUTHENTICATION
# ==========================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        phone = data.get('phone')

        if not email or not password or not first_name or not last_name:
            return jsonify({'error': 'All fields are required.'}), 400

        if user_logins.find_one({'email': email}):
            return jsonify({'error': 'This email is already registered.'}), 409

        new_user = {
            'email': email,
            'password': generate_password_hash(password),
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'role': 'user',
            'is_active': True,
            'created_at': datetime.utcnow(),
            'last_login': None
        }

        user_logins.insert_one(new_user)
        return jsonify({'message': 'Account created successfully!'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password required.'}), 400

        user = user_logins.find_one({'email': email})

        if not user or not check_password_hash(user['password'], password):
            return jsonify({'error': 'Incorrect email or password.'}), 401
            
        user_logins.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.utcnow()}}
        )

        return jsonify({
            'message': 'Login successful',
            'user': {
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'email': user['email'], 
                'role': user['role']
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    try:
        email = request.args.get('email')
        if not email: return jsonify({'error': 'Email is required'}), 400

        user = user_logins.find_one({'email': email})
        if not user: return jsonify({'error': 'User not found'}), 404

        user_profile = {
            'first_name': user.get('first_name', ''),
            'last_name': user.get('last_name', ''),
            'email': user.get('email', ''),
            'phone': user.get('phone', ''),
            'role': user.get('role', 'user'),
            'is_active': user.get('is_active', False),
            'created_at': user.get('created_at', '')
        }
        return jsonify(user_profile), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==========================================
#      SECTION 2: HORSE MANAGEMENT
# ==========================================

@app.route('/horses', methods=['GET'])
def get_horses():
    try:
        cursor = horse_collection.find().sort("Name", 1)
        horses = [format_doc(doc) for doc in cursor]
        return jsonify(horses), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==========================================
#      SECTION 2.5: AUDIT TRAIL
# ==========================================

@app.route('/api/audits', methods=['GET'])
def get_audits():
    try:
        cursor = audit_collection.find().sort("timestamp", -1).limit(50)
        audits = [format_doc(doc) for doc in cursor]
        return jsonify(audits), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==========================================
#      SECTION 3: DAILY OBS / TO-DO (RESTORED!)
# ==========================================

@app.route('/api/daily-obs', methods=['GET'])
def get_daily_obs():
    try:
        # Sort by date descending (newest first)
        cursor = daily_obs_collection.find().sort("date", -1)
        items = [format_doc(doc) for doc in cursor]
        return jsonify(items), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily-obs', methods=['POST'])
def add_daily_obs():
    try:
        data = request.json
        # Basic validation
        if not data.get('note'):
            return jsonify({'error': 'Note is required'}), 400

        # Prepare document
        new_item = {
            "note": data.get('note'),
            "is_observation": data.get('obs', False),
            "is_todo": data.get('todo', False),
            "status": data.get('status', 'pending'),
            "horse_id": data.get('horse_id', ''),
            "created_by": data.get('created_by', 'Anonymous'),
            "date": datetime.utcnow()
        }
        
        result = daily_obs_collection.insert_one(new_item)
        return jsonify({'message': 'Item added', 'id': str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily-obs/<id>', methods=['DELETE'])
def delete_daily_obs(id):
    try:
        result = daily_obs_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Item not found"}), 404
        return jsonify({"message": "Item Deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)