from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime

# --- CONFIGURATION ---
app = Flask(__name__)
CORS(app)

# Database Connection (shared)
URI = "mongodb+srv://Horse_Python_DataEntry:iAvq68Uzt6Io1a1p@horsesanctuary.83r8ztp.mongodb.net/?appName=HorseSanctuary"
DB_NAME = "Data"

try:
    client = MongoClient(URI, server_api=ServerApi('1'))
    db = client[DB_NAME]
    user_logins = db['User_Logins']
    horse_collection = db['Horse_Tables']
    print(f"✅ CONNECTED TO: {DB_NAME} (User_Logins, Horse_Tables)")
except Exception as e:
    print(f"❌ DATABASE CONNECTION FAILED: {e}")


# --- HELPERS ---
def format_doc(doc):
    if not doc:
        return None
    doc['_id'] = str(doc['_id'])
    return doc


# --- ROOTS ---
@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "Unified Server Running"})


# --- USER AUTH ROUTES (preserve original endpoints) ---

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

        result = user_logins.insert_one(new_user)
        return jsonify({'message': 'Account created successfully!', 'id': str(result.inserted_id)}), 201

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
        if not user:
            return jsonify({'error': 'Incorrect email or password.'}), 401

        if not check_password_hash(user['password'], password):
            return jsonify({'error': 'Incorrect email or password.'}), 401

        user_logins.update_one({'_id': user['_id']}, {'$set': {'last_login': datetime.utcnow()}})

        return jsonify({
            'message': 'Login successful',
            'user': {
                'first_name': user['first_name'],
                'role': user['role']
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- HORSE ROUTES (preserve original endpoints) ---

@app.route('/horses', methods=['GET'])
def get_horses():
    try:
        cursor = horse_collection.find().sort("Name", 1)
        horses = [format_doc(doc) for doc in cursor]
        return jsonify(horses), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/horses', methods=['POST'])
def add_horse():
    try:
        data = request.json
        if not data.get('Name'):
            return jsonify({"error": "Horse Name is required"}), 400

        data['created_at'] = datetime.utcnow()
        data['active_status'] = True

        result = horse_collection.insert_one(data)
        return jsonify({"message": "Horse Added", "id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/horses/<id>', methods=['PUT'])
def update_horse(id):
    try:
        data = request.json
        if '_id' in data:
            del data['_id']
        data['last_updated'] = datetime.utcnow()

        result = horse_collection.update_one({"_id": ObjectId(id)}, {"$set": data})
        if result.matched_count == 0:
            return jsonify({"error": "Horse not found"}), 404
        return jsonify({"message": "Horse Updated Successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/horses/<id>', methods=['DELETE'])
def delete_horse(id):
    try:
        result = horse_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Horse not found"}), 404
        return jsonify({"message": "Horse Deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
